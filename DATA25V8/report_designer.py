from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QListWidget, QVBoxLayout,
    QHBoxLayout, QCheckBox, QTableWidget, QTableWidgetItem, QDialog, QMessageBox, QListWidgetItem, QGroupBox, QApplication, QGridLayout, QSpacerItem, QSizePolicy
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from psycopg2 import InternalError
from db_utils import execute_query, fetch_all

def get_ticket_fields():
    return [
        "TicketNumber", "VehicleNumber", "Date", "Time", "EmptyWeight", "LoadedWeight",
        "EmptyWeightDate", "EmptyWeightTime", "LoadWeightDate", "LoadWeightTime",
        "NetWeight", "Pending", "Closed", "Exported", "Shift", "Materialname",
        "SupplierName", "State", "TEST", "EAMOUNT", "LAMOUNT", "TAMOUNT"
    ]

class ReportDesigner(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ticket Report Templates")
        self.setMinimumSize(850, 650)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # UI Setup is unchanged...
        template_group = QGroupBox("Select Template")
        template_group.setStyleSheet("font-weight: bold;")
        template_group_layout = QVBoxLayout(template_group)
        self.template_list = QListWidget()
        self.template_list.setStyleSheet("font-size: 14px; font-weight: normal;")
        template_group_layout.addWidget(self.template_list)
        template_group.setFixedWidth(200)
        main_layout.addWidget(template_group)
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(8)
        tn_layout = QHBoxLayout()
        tn_layout.addWidget(QLabel("Template Name:"))
        self.template_name_edit = QLineEdit()
        self.template_name_edit.setMinimumWidth(250)
        tn_layout.addWidget(self.template_name_edit)
        self.set_default_btn = QPushButton("Set as Default")
        self.set_default_btn.setFixedWidth(120)
        tn_layout.addWidget(self.set_default_btn)
        tn_layout.addStretch(1)
        center_layout.addLayout(tn_layout)
        header_group = QGroupBox("Page Header")
        header_layout = QVBoxLayout(header_group)
        ph_layout_top = QHBoxLayout()
        ph_layout_top.addStretch(1)
        self.without_lines_chk = QCheckBox("Without Lines")
        ph_layout_top.addWidget(self.without_lines_chk)
        header_layout.addLayout(ph_layout_top)
        self.header_edits = []
        for i in range(3):
            ph_layout = QHBoxLayout()
            edit = QLineEdit()
            edit.setPlaceholderText(f"Header Line {i+1}")
            ph_layout.addWidget(edit)
            font_btn = QPushButton("...")
            font_btn.setFixedSize(28, 28)
            ph_layout.addWidget(font_btn)
            header_layout.addLayout(ph_layout)
            self.header_edits.append(edit)
        center_layout.addWidget(header_group)
        field_group = QGroupBox("Field Selection")
        field_sel_layout = QHBoxLayout(field_group)
        self.fields_list = QListWidget()
        self.fields_list.addItems(get_ticket_fields())
        field_sel_layout.addWidget(self.fields_list, 1)
        arrow_layout = QVBoxLayout()
        arrow_layout.addStretch(1)
        self.add_one_btn, self.add_all_btn, self.remove_one_btn, self.remove_all_btn = QPushButton(">"), QPushButton(">>"), QPushButton("<"), QPushButton("<<")
        arrows = [self.add_one_btn, self.add_all_btn, self.remove_one_btn, self.remove_all_btn]
        for btn in arrows: btn.setFixedSize(40, 28); arrow_layout.addWidget(btn)
        arrow_layout.addStretch(1)
        field_sel_layout.addLayout(arrow_layout)
        table_and_buttons_layout = QVBoxLayout()
        self.field_table = QTableWidget(0, 2)
        self.field_table.setHorizontalHeaderLabels(["Field Name", "Caption"])
        self.field_table.horizontalHeader().setStretchLastSection(True)
        table_and_buttons_layout.addWidget(self.field_table)
        fc_layout = QHBoxLayout()
        fc_layout.addWidget(QLabel("Field Caption:"))
        self.field_caption_edit = QLineEdit()
        self.field_caption_edit.setMinimumWidth(200)
        fc_layout.addWidget(self.field_caption_edit)
        self.save_caption_btn = QPushButton("Save Caption")
        self.save_caption_btn.setFixedWidth(120)
        fc_layout.addWidget(self.save_caption_btn)
        table_and_buttons_layout.addLayout(fc_layout)
        field_sel_layout.addLayout(table_and_buttons_layout, 2)
        updown_layout = QVBoxLayout()
        updown_layout.addStretch(1)
        self.up_btn, self.down_btn = QPushButton("▲"), QPushButton("▼")
        self.up_btn.setFixedSize(40, 32); self.down_btn.setFixedSize(40, 32)
        updown_layout.addWidget(self.up_btn); updown_layout.addWidget(self.down_btn)
        updown_layout.addStretch(1)
        field_sel_layout.addLayout(updown_layout)
        center_layout.addWidget(field_group)
        footer_group = QGroupBox("Page Footer")
        footer_layout = QVBoxLayout(footer_group)
        self.footer_edits = []
        for i in range(2):
            pf_layout = QHBoxLayout()
            edit = QLineEdit()
            edit.setPlaceholderText(f"Footer Line {i+1}")
            pf_layout.addWidget(edit)
            font_btn = QPushButton("...")
            font_btn.setFixedSize(28, 28)
            pf_layout.addWidget(font_btn)
            footer_layout.addLayout(pf_layout)
            self.footer_edits.append(edit)
        center_layout.addWidget(footer_group)
        main_layout.addWidget(center_widget, 1)
        right_layout = QVBoxLayout()
        right_layout.setSpacing(10)
        op_btn_size = (80, 40)
        self.add_btn, self.save_btn, self.delete_btn, self.preview_btn, self.exit_btn = QPushButton("Add"), QPushButton("Save"), QPushButton("Delete"), QPushButton("Preview"), QPushButton("Exit")
        op_buttons = [self.add_btn, self.save_btn, self.delete_btn, self.preview_btn]
        for btn in op_buttons: btn.setFixedSize(*op_btn_size); right_layout.addWidget(btn)
        right_layout.addStretch(1)
        self.exit_btn.setFixedSize(*op_btn_size)
        right_layout.addWidget(self.exit_btn)
        main_layout.addLayout(right_layout)

        self.setLayout(main_layout)

        # Connections
        self.exit_btn.clicked.connect(self.close)
        self.save_caption_btn.clicked.connect(self.save_field_caption)
        self.up_btn.clicked.connect(self.move_field_up)
        self.down_btn.clicked.connect(self.move_field_down)
        self.fields_list.itemDoubleClicked.connect(self.add_field_to_table)
        self.add_one_btn.clicked.connect(self.add_selected_field)
        self.add_all_btn.clicked.connect(self.add_all_fields)
        self.remove_one_btn.clicked.connect(self.remove_selected_field)
        self.remove_all_btn.clicked.connect(self.remove_all_fields)
        self.save_btn.clicked.connect(self.save_report_template)
        self.add_btn.clicked.connect(self.add_new_template)
        self.delete_btn.clicked.connect(self.delete_report_template)
        self.preview_btn.clicked.connect(self.preview_report)
        self.template_list.itemClicked.connect(self.on_template_selected)
        self.set_default_btn.clicked.connect(self.set_template_as_default)
        self.field_table.itemClicked.connect(self.on_field_selected)

        self.load_template_names()

    def on_field_selected(self, item):
        # Unchanged
        row = item.row()
        caption_item = self.field_table.item(row, 1)
        if caption_item:
            self.field_caption_edit.setText(caption_item.text())

    def set_template_as_default(self):
        # Unchanged
        selected = self.template_list.currentItem()
        if not selected:
            QMessageBox.warning(self, "Error", "Please select a template to set as default.")
            return
        name = selected.text().replace(" (Default)", "")
        try:
            execute_query('UPDATE ReportTemplate SET "Default" = %s', (False,))
            execute_query('UPDATE ReportTemplate SET "Default" = %s WHERE reporttemplatename = %s', (True, name))
            QMessageBox.information(self, "Default Set", f"Template '{name}' is now the default.")
            self.load_template_names()
        except InternalError as e:
            QMessageBox.critical(self, "Database Transaction Error", f"Could not set default due to a transaction error:\n{e}\n\nPlease restart the application.")
        except Exception as e:
            QMessageBox.critical(self, "DB Error", f"Could not set default:\n{e}")

    def load_template_names(self):
        # Unchanged
        current_selection = self.template_list.currentItem().text().replace(" (Default)", "") if self.template_list.currentItem() else None
        self.template_list.clear()
        try:
            rows = fetch_all("SELECT reporttemplatename, \"Default\" FROM ReportTemplate ORDER BY reporttemplatename")
            for r in rows:
                item_text = r["reporttemplatename"]
                item = QListWidgetItem(item_text)
                if r["Default"]:
                    font = item.font()
                    font.setBold(True)
                    item.setText(f"{item_text} (Default)")
                    item.setFont(font)
                self.template_list.addItem(item)
                if item_text == current_selection:
                    self.template_list.setCurrentItem(item)
        except InternalError as e:
            QMessageBox.critical(self, "Database Transaction Error", f"Could not load templates due to a transaction error:\n{e}\n\nPlease restart the application.")
        except Exception as e:
            QMessageBox.critical(self, "DB Error", f"Could not load templates:\n{e}")

    def clear_all_fields(self):
        # Unchanged
        self.template_name_edit.clear()
        for edit in self.header_edits: edit.clear()
        for edit in self.footer_edits: edit.clear()
        self.without_lines_chk.setChecked(False)
        self.field_caption_edit.clear()
        self.field_table.setRowCount(0)

    def add_field_to_table(self, item): self._add_field(item.text())
    def add_selected_field(self):
        selected = self.fields_list.currentItem()
        if selected: self._add_field(selected.text())
    def add_all_fields(self):
        for i in range(self.fields_list.count()): self._add_field(self.fields_list.item(i).text())
    def remove_selected_field(self):
        row = self.field_table.currentRow()
        if row >= 0: self.field_table.removeRow(row)
    def remove_all_fields(self): self.field_table.setRowCount(0)

    def _add_field(self, fname):
        # Unchanged
        for row in range(self.field_table.rowCount()):
            if self.field_table.item(row, 0).text() == fname: return
        row_pos = self.field_table.rowCount()
        self.field_table.insertRow(row_pos)
        self.field_table.setItem(row_pos, 0, QTableWidgetItem(fname))
        self.field_table.setItem(row_pos, 1, QTableWidgetItem(fname))
        self.field_table.selectRow(row_pos)
        self.field_caption_edit.setText(fname)

    def save_field_caption(self):
        # Unchanged
        row = self.field_table.currentRow()
        caption = self.field_caption_edit.text().strip()
        if row >= 0 and caption: self.field_table.setItem(row, 1, QTableWidgetItem(caption))

    def move_field_up(self):
        # Unchanged
        row = self.field_table.currentRow()
        if row > 0:
            self.swap_field_rows(row, row - 1)
            self.field_table.selectRow(row - 1)
    def move_field_down(self):
        # Unchanged
        row = self.field_table.currentRow()
        if row >= 0 and row < self.field_table.rowCount() - 1:
            self.swap_field_rows(row, row + 1)
            self.field_table.selectRow(row + 1)
    def swap_field_rows(self, row1, row2):
        # Unchanged
        for col in range(self.field_table.columnCount()):
            item1, item2 = self.field_table.takeItem(row1, col), self.field_table.takeItem(row2, col)
            self.field_table.setItem(row1, col, item2)
            self.field_table.setItem(row2, col, item1)

    def add_new_template(self):
        # Unchanged
        self.clear_all_fields()
        self.template_list.clearSelection()
        self.template_name_edit.setFocus()

    def save_report_template(self):
        name = self.template_name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "Template Name is required.")
            return
        try:
            existing = fetch_all("SELECT reporttemplatename FROM ReportTemplate WHERE reporttemplatename = %s", (name,))
            if not existing:
                execute_query('INSERT INTO ReportTemplate (reporttemplatename, "Default") VALUES (%s, %s)', (name, False))
            
            execute_query("DELETE FROM ReportDetail WHERE reporttemplatename=%s", (name,))
            execute_query("DELETE FROM ReportDesigner WHERE reporttemplatename=%s", (name,))

            # --- MODIFICATION: Save fields without reportorder ---
            for row in range(self.field_table.rowCount()):
                fname = self.field_table.item(row, 0).text()
                caption = self.field_table.item(row, 1).text()
                # The 'reportorder' column is removed from the query
                query = "INSERT INTO ReportDetail (fieldname, fieldcaption, reporttemplatename) VALUES (%s, %s, %s)"
                execute_query(query, (fname, caption, name))

            for i, edit in enumerate(self.header_edits):
                if edit.text().strip(): execute_query("INSERT INTO ReportDesigner (section, sectioncaption, reporttemplatename) VALUES (%s, %s, %s)", (f"Header{i+1}", edit.text().strip(), name))
            for i, edit in enumerate(self.footer_edits):
                 if edit.text().strip(): execute_query("INSERT INTO ReportDesigner (section, sectioncaption, reporttemplatename) VALUES (%s, %s, %s)", (f"Footer{i+1}", edit.text().strip(), name))
            
            QMessageBox.information(self, "Saved", f"Template '{name}' saved successfully.")
            self.load_template_names()
        except InternalError as e:
            QMessageBox.critical(self, "Database Transaction Error", f"Could not save template due to a transaction error:\n{e}\n\nPlease restart the application.")
        except Exception as e:
            QMessageBox.critical(self, "DB Error", f"Could not save template:\n{e}")

    def delete_report_template(self):
        # Unchanged
        selected = self.template_list.currentItem()
        if not selected:
            QMessageBox.warning(self, "Error", "Please select a template to delete.")
            return
        name = selected.text().replace(" (Default)", "")
        reply = QMessageBox.question(self, "Confirm Delete", f"Are you sure you want to delete template '{name}'?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                execute_query("DELETE FROM ReportTemplate WHERE reporttemplatename=%s", (name,))
                QMessageBox.information(self, "Deleted", f"Template '{name}' deleted.")
                self.load_template_names()
                self.clear_all_fields()
            except InternalError as e:
                QMessageBox.critical(self, "Database Transaction Error", f"Could not delete template due to a transaction error:\n{e}\n\nPlease restart the application.")
            except Exception as e:
                QMessageBox.critical(self, "DB Error", f"Could not delete template:\n{e}")

    def preview_report(self):
        # Unchanged
        if self.field_table.rowCount() == 0:
            QMessageBox.information(self, "Preview", "No fields to preview.")
            return
        preview_text = f"--- Preview of '{self.template_name_edit.text()}' ---\n\n"
        headers = [edit.text() for edit in self.header_edits if edit.text()]
        if headers:
            preview_text += "\n".join(headers) + "\n" + "="*40 + "\n"
        for row in range(self.field_table.rowCount()):
            caption = self.field_table.item(row, 1).text()
            preview_text += f"{caption:<20}: [Sample Data]\n"
        footers = [edit.text() for edit in self.footer_edits if edit.text()]
        if footers:
            preview_text += "="*40 + "\n" + "\n".join(footers) + "\n"
        QMessageBox.information(self, "Report Preview", preview_text)

    def on_template_selected(self, item):
        # Unchanged
        name = item.text().replace(" (Default)", "")
        self.load_template(name)

    def load_template(self, name):
        self.clear_all_fields()
        self.template_name_edit.setText(name)
        try:
            # --- MODIFICATION: Load fields without ordering by reportorder ---
            # The 'ORDER BY' clause is removed
            rows = fetch_all("SELECT fieldname, fieldcaption FROM ReportDetail WHERE reporttemplatename=%s", (name,))
            self.field_table.setRowCount(len(rows))
            for i, row in enumerate(rows):
                self.field_table.setItem(i, 0, QTableWidgetItem(row["fieldname"]))
                self.field_table.setItem(i, 1, QTableWidgetItem(row["fieldcaption"]))
            
            sections = fetch_all("SELECT section, sectioncaption FROM ReportDesigner WHERE reporttemplatename=%s", (name,))
            for s in sections:
                if s["section"].startswith("Header"):
                    idx = int(s["section"][-1]) - 1
                    if 0 <= idx < len(self.header_edits): self.header_edits[idx].setText(s["sectioncaption"])
                elif s["section"].startswith("Footer"):
                    idx = int(s["section"][-1]) - 1
                    if 0 <= idx < len(self.footer_edits): self.footer_edits[idx].setText(s["sectioncaption"])
        except InternalError as e:
            if "current transaction is aborted" in str(e):
                QMessageBox.critical(self, "Database Transaction Error", 
                                     f"Could not load template '{name}' because the database connection is in an error state.\n\n"
                                     "Please restart the application to establish a new connection.")
            else:
                QMessageBox.critical(self, "Database Internal Error", f"An unexpected internal database error occurred while loading '{name}'.\nError: {e}")
        except Exception as e:
            QMessageBox.critical(self, "DB Error", f"Could not load template '{name}':\n{e}")
