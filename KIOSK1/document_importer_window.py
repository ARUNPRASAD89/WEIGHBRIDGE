import pandas as pd
import os
import re
import traceback
from db_utils import get_new_connection
from psycopg2 import extras, sql
import numpy as np

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QLabel,
    QFileDialog, QTextEdit, QMessageBox, QFrame, QSizePolicy, QListWidget,
    QListWidgetItem, QProgressDialog, QTableWidget, QTableWidgetItem
)
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QFont

# --- Data Grid Viewer Window (No changes) ---
class DataGridViewWindow(QDialog):
    def __init__(self, table_name, parent=None):
        super().__init__(parent); self.table_name = table_name; self.setWindowTitle(f"Viewing Table: {self.table_name}"); self.setGeometry(100, 100, 800, 600)
        main_layout = QVBoxLayout(self); self.table_widget = QTableWidget(); self.table_widget.setEditTriggers(QTableWidget.NoEditTriggers); main_layout.addWidget(self.table_widget)
        button_layout = QHBoxLayout(); self.exit_btn = QPushButton("Exit"); self.exit_btn.clicked.connect(self.close); button_layout.addStretch(); button_layout.addWidget(self.exit_btn); main_layout.addLayout(button_layout)
        self.load_data()
    def load_data(self):
        try:
            conn = get_new_connection(); query = sql.SQL("SELECT * FROM {table};").format(table=sql.Identifier(self.table_name)); df = pd.read_sql_query(query.as_string(conn), conn, coerce_float=False); conn.close()
            self.table_widget.setRowCount(len(df)); self.table_widget.setColumnCount(len(df.columns)); self.table_widget.setHorizontalHeaderLabels(df.columns)
            for i, row in df.iterrows():
                for j, col_name in enumerate(df.columns): self.table_widget.setItem(i, j, QTableWidgetItem(str(row[col_name]) if pd.notna(row[col_name]) else ""))
            self.table_widget.resizeColumnsToContents()
        except Exception as e: QMessageBox.critical(self, "Error Loading Data", f"Could not load data from table '{self.table_name}':\n{e}")
    def closeEvent(self, event):
        if parent := self.parent(): parent.show()
        super().closeEvent(event)

# --- Data Transformation and Matching Logic ---
class DataMatcher(QThread):
    log_message = pyqtSignal(str)
    match_finished = pyqtSignal(bool, str)
    def __init__(self, source_table_name):
        super().__init__(); self.source_table = source_table_name; self.target_table = "tickets_copy"; self.reference_table = "tickets"; self.conn = None
    def get_table_schema(self, table_name):
        query = "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = %s;"
        with self.conn.cursor() as cur: cur.execute(query, (table_name,)); return {row[0]: row[1] for row in cur.fetchall()}
    def create_target_table(self):
        self.log_message.emit(f"Creating target table '{self.target_table}'..."); query = sql.SQL("DROP TABLE IF EXISTS {target}; CREATE TABLE {target} (LIKE {reference} INCLUDING ALL);").format(target=sql.Identifier(self.target_table), reference=sql.Identifier(self.reference_table))
        with self.conn.cursor() as cur: cur.execute(query)
        self.conn.commit()

    def map_columns(self, source_schema, target_schema):
        self.log_message.emit("Attempting to map columns automatically...")
        mapping = {}
        available_source_cols = list(source_schema.keys())

        for target_col in sorted(target_schema.keys(), key=len, reverse=True):
            normalized_target = target_col.lower().replace("_", "")
            best_match = None

            for source_col in available_source_cols:
                normalized_source = source_col.lower().replace("_", "")
                
                if normalized_source == normalized_target: best_match = source_col; break
                if normalized_target.startswith(normalized_source): best_match = source_col; break
                if normalized_source.startswith(normalized_target): best_match = source_col; break

            if best_match:
                mapping[best_match] = target_col
                available_source_cols.remove(best_match)
                self.log_message.emit(f"  - Mapped source:'{best_match}' -> target:'{target_col}'")

        if not mapping: self.log_message.emit("Warning: No column mappings found. Ensure source file has a header row.")
        return mapping

    def run(self):
        try:
            self.conn = get_new_connection(); self.create_target_table()
            source_schema = self.get_table_schema(self.source_table); target_schema = self.get_table_schema(self.reference_table)
            column_mapping = self.map_columns(source_schema, target_schema)
            if not column_mapping: self.match_finished.emit(False, "Could not map any columns. Aborting."); return
            
            source_query = sql.SQL("SELECT * FROM {table};").format(table=sql.Identifier(self.source_table))
            source_df = pd.read_sql_query(source_query.as_string(self.conn), self.conn)

            target_df = pd.DataFrame(columns=target_schema.keys()); self.log_message.emit("Transforming data...")
            for source_col, target_col in column_mapping.items():
                target_type = target_schema[target_col]
                if 'timestamp' in target_type or 'date' in target_type: target_df[target_col] = pd.to_datetime(source_df[source_col], errors='coerce')
                elif 'integer' in target_type or 'numeric' in target_type: target_df[target_col] = pd.to_numeric(source_df[source_col], errors='coerce')
                else: target_df[target_col] = source_df[source_col]

            for col in target_schema.keys():
                if col not in target_df.columns: target_df[col] = None

            # --- FIX: Explicitly convert pandas NaT to None for the database ---
            df_prepared = target_df.astype(object).where(pd.notnull(target_df), None)
            
            self.log_message.emit(f"Inserting {len(df_prepared)} records into '{self.target_table}'..."); 
            data_to_insert = [tuple(row) for row in df_prepared.to_numpy()]
            
            with self.conn.cursor() as cur:
                cols_for_insert = sql.SQL(', ').join(map(sql.Identifier, df_prepared.columns)); 
                insert_sql = sql.SQL("INSERT INTO {table} ({cols}) VALUES %s").format(table=sql.Identifier(self.target_table), cols=cols_for_insert)
                extras.execute_values(cur, insert_sql, data_to_insert)
            self.conn.commit(); self.match_finished.emit(True, f"Successfully copied {len(data_to_insert)} records to '{self.target_table}'.")
        except Exception as e:
            if self.conn: self.conn.rollback()
            self.log_message.emit(f"Error during matching: {e}\n\n{traceback.format_exc()}"); self.match_finished.emit(False, "Data matching failed. Check logs.")
        finally:
            if self.conn and not self.conn.closed: self.conn.close()

# --- Importer Logic ---
class ImporterLogic(QThread):
    log_message = pyqtSignal(str)
    import_finished = pyqtSignal(bool, str)
    def __init__(self, filepath, table_name): super().__init__(); self.filepath=filepath; self.table_name=table_name; self.conn=None
    def _clean_col_name(self, col_name):
        col_name = str(col_name).strip(); col_name = re.sub(r'[\s\.\-\/]+', '_', col_name); col_name = re.sub(r'[^a-zA-Z0-9_]', '', col_name)
        if not col_name: return f"unnamed_col_{np.random.randint(1000)}"
        if col_name and col_name[0].isdigit(): col_name = '_' + col_name
        return col_name.lower()
    def _infer_sql_type(self, series):
        series = series.dropna();
        if series.empty: return 'TEXT'
        dtype = series.dtype
        if pd.api.types.is_integer_dtype(dtype): return 'BIGINT'
        if pd.api.types.is_float_dtype(dtype): return 'NUMERIC'
        if pd.api.types.is_datetime64_any_dtype(dtype): return 'TIMESTAMP'
        if dtype == object:
            try:
                if pd.to_numeric(series, errors='coerce').notna().all(): return 'NUMERIC'
                if pd.to_datetime(series, errors='coerce').notna().all(): return 'TIMESTAMP'
            except Exception: pass
        return 'TEXT'
    def run(self):
        try:
            self.conn = get_new_connection(); self.log_message.emit(f"Starting import from '{os.path.basename(self.filepath)}'...")
            df = pd.read_csv(self.filepath, sep=',', skipinitialspace=True, on_bad_lines='warn', header=0, encoding='utf-8')
            
            self.log_message.emit(f"Successfully read {len(df.columns)} columns and {len(df)} rows.")
            df.columns = [self._clean_col_name(col) for col in df.columns]
            df.dropna(axis=1, how='all', inplace=True)
            
            column_types = {col: self._infer_sql_type(df[col]) for col in df.columns}
            with self.conn.cursor() as cur:
                cols_with_types = ', '.join([f'"{name}" {dtype}' for name, dtype in column_types.items()])
                cur.execute(sql.SQL("DROP TABLE IF EXISTS {table};").format(table=sql.Identifier(self.table_name)))
                cur.execute(sql.SQL('CREATE TABLE {table} ({fields});').format(table=sql.Identifier(self.table_name), fields=sql.SQL(cols_with_types)))
                self.log_message.emit(f"Table '{self.table_name}' created successfully.")
                df_prepared = df.where(pd.notnull(df), None); data_to_insert = [tuple(row) for row in df_prepared.to_numpy()]
                cols_for_insert = sql.SQL(', ').join(map(sql.Identifier, df.columns))
                insert_sql = sql.SQL('INSERT INTO {table} ({cols}) VALUES %s').format(table=sql.Identifier(self.table_name), cols=cols_for_insert)
                extras.execute_values(cur, insert_sql, data_to_insert)
                cur.execute("INSERT INTO imported_tables_metadata (table_name) VALUES (%s) ON CONFLICT (table_name) DO NOTHING;", (self.table_name,))
            self.conn.commit(); self.import_finished.emit(True, f"Successfully imported data into '{self.table_name}'.")
        except Exception as e:
            if self.conn: self.conn.rollback()
            self.log_message.emit(f"Error: {e}\n{traceback.format_exc()}"); self.import_finished.emit(False, "Import failed.")
        finally:
            if self.conn and not self.conn.closed: self.conn.close()

# --- Main Window ---
class DocumentImporterWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent); self.setWindowTitle("Document Importer and Manager"); self.setMinimumSize(700, 650)
        main_layout = QVBoxLayout(self); main_layout.setContentsMargins(15, 15, 15, 15)
        importer_frame = QFrame(); importer_frame.setFrameShape(QFrame.StyledPanel); importer_layout = QVBoxLayout(importer_frame)
        importer_layout.addWidget(QLabel("<h3>Step 1: Import New Data</h3>"))
        file_layout = QHBoxLayout(); self.filepath_input = QLineEdit(); browse_btn = QPushButton("Browse..."); browse_btn.clicked.connect(self.browse_file)
        file_layout.addWidget(QLabel("Source File:")); file_layout.addWidget(self.filepath_input); file_layout.addWidget(browse_btn)
        importer_layout.addLayout(file_layout)
        table_layout = QHBoxLayout(); self.table_name_input = QLineEdit("historical_tickets")
        table_layout.addWidget(QLabel("New Table Name:")); table_layout.addWidget(self.table_name_input)
        importer_layout.addLayout(table_layout)
        self.import_btn = QPushButton("Start Import"); self.import_btn.clicked.connect(self.start_import)
        self.import_btn.setStyleSheet("background-color: #27ae60; font-size: 11pt; padding: 10px;")
        importer_layout.addWidget(self.import_btn); main_layout.addWidget(importer_frame)
        manager_frame = QFrame(); manager_frame.setFrameShape(QFrame.StyledPanel); manager_layout = QVBoxLayout(manager_frame)
        manager_layout.addWidget(QLabel("<h3>Step 2: Manage Imported Tables</h3>"))
        self.table_list_widget = QListWidget(); manager_layout.addWidget(self.table_list_widget)
        manager_buttons_layout = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh List"); self.refresh_btn.clicked.connect(self.populate_table_list)
        self.open_btn = QPushButton("Open Table"); self.open_btn.clicked.connect(self.open_selected_table); self.open_btn.setStyleSheet("background-color: #2980b9;")
        self.match_btn = QPushButton("Copy to Match"); self.match_btn.clicked.connect(self.start_matching); self.match_btn.setStyleSheet("background-color: #3498db;")
        self.delete_btn = QPushButton("Delete Selected Table"); self.delete_btn.clicked.connect(self.delete_selected_table); self.delete_btn.setStyleSheet("background-color: #c0392b;")
        manager_buttons_layout.addWidget(self.refresh_btn); manager_buttons_layout.addWidget(self.open_btn); manager_buttons_layout.addWidget(self.match_btn); manager_buttons_layout.addWidget(self.delete_btn)
        manager_layout.addLayout(manager_buttons_layout); main_layout.addWidget(manager_frame)
        self.log_display = QTextEdit(); self.log_display.setReadOnly(True); self.log_display.setMaximumHeight(100)
        main_layout.addWidget(QLabel("<h4>Activity Log")); main_layout.addWidget(self.log_display)
        self.exit_btn = QPushButton("Exit"); self.exit_btn.clicked.connect(self.close); main_layout.addWidget(self.exit_btn, alignment=Qt.AlignRight)
        self._initialize_database(); self.populate_table_list()
    def _initialize_database(self):
        try:
            conn = get_new_connection()
            with conn.cursor() as cur: cur.execute("CREATE TABLE IF NOT EXISTS imported_tables_metadata (table_name TEXT PRIMARY KEY);")
            conn.commit(); conn.close()
        except Exception as e: QMessageBox.critical(self, "DB Init Error", f"Could not create metadata table:\n{e}")
    def populate_table_list(self):
        self.table_list_widget.clear()
        try:
            conn = get_new_connection()
            with conn.cursor() as cur: cur.execute("SELECT table_name FROM imported_tables_metadata ORDER BY table_name;"); tables = cur.fetchall()
            conn.close()
            if tables:
                for table in tables: self.table_list_widget.addItem(QListWidgetItem(table[0]))
            else: self.table_list_widget.addItem(QListWidgetItem("No imported tables found."))
        except Exception: self.table_list_widget.addItem(QListWidgetItem("Metadata table not found."))
    def open_selected_table(self):
        selected_item = self.table_list_widget.currentItem()
        if not selected_item or "found" in selected_item.text(): QMessageBox.warning(self, "No Selection", "Please select a table to open."); return
        table_name = selected_item.text(); self.data_view_window = DataGridViewWindow(table_name, parent=self); self.hide(); self.data_view_window.show()
    def start_matching(self):
        selected_item = self.table_list_widget.currentItem()
        if not selected_item or "found" in selected_item.text(): QMessageBox.warning(self, "No Selection", "Please select a source table to match."); return
        source_table = selected_item.text()
        reply = QMessageBox.question(self, "Confirm Data Copy", f"This will copy data from <b>'{source_table}'</b> into <b>'tickets_copy'</b>, overwriting any existing data.<br><br>Proceed?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.set_buttons_enabled(False); self.log_display.clear(); self.matcher_thread = DataMatcher(source_table)
            self.matcher_thread.log_message.connect(self.log_display.append); self.matcher_thread.match_finished.connect(self.on_process_finished); self.matcher_thread.start()
    def delete_selected_table(self):
        selected_item = self.table_list_widget.currentItem()
        if not selected_item or "found" in selected_item.text(): QMessageBox.warning(self, "No Selection", "Please select a table to delete."); return
        table_name = selected_item.text()
        reply = QMessageBox.question(self, "Confirm Deletion", f"<b>Permanently delete '{table_name}'?</b>", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                conn = get_new_connection()
                with conn.cursor() as cur:
                    cur.execute(sql.SQL("DROP TABLE IF EXISTS {table};").format(table=sql.Identifier(table_name)))
                    cur.execute("DELETE FROM imported_tables_metadata WHERE table_name = %s;", (table_name,))
                conn.commit(); conn.close()
                QMessageBox.information(self, "Success", f"Table '{table_name}' deleted.")
                self.populate_table_list()
            except Exception as e: QMessageBox.critical(self, "Error", f"Failed to delete table:\n{e}")
    def start_import(self):
        filepath = self.filepath_input.text(); table_name = self.table_name_input.text().strip()
        if not (filepath and os.path.exists(filepath)): QMessageBox.warning(self, "Warning", "Please select a valid source file."); return
        if not (table_name and re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table_name)): QMessageBox.warning(self, "Warning", "Please enter a valid SQL table name."); return
        self.set_buttons_enabled(False); self.log_display.clear(); self.importer_thread = ImporterLogic(filepath, table_name)
        self.importer_thread.log_message.connect(self.log_display.append); self.importer_thread.import_finished.connect(self.on_process_finished)
        self.importer_thread.start()
    def on_process_finished(self, success, message):
        self.set_buttons_enabled(True); self.log_display.append(message)
        if success:
            QMessageBox.information(self, "Success", message); self.populate_table_list()
        else: QMessageBox.critical(self, "Failure", message)
    def set_buttons_enabled(self, enabled):
        self.import_btn.setEnabled(enabled); self.refresh_btn.setEnabled(enabled); self.open_btn.setEnabled(enabled); self.match_btn.setEnabled(enabled); self.delete_btn.setEnabled(enabled)
    def browse_file(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Select Data File", "", "Data Files (*.csv *.txt *.xlsx *.ods);;All Files (*)");
        if filepath: self.filepath_input.setText(filepath)
    def closeEvent(self, event):
     if parent := self.parent(): parent.show()
     super().closeEvent(event)
     
