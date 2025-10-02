import sys
from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QListWidget, QVBoxLayout,
    QHBoxLayout, QTableWidget, QTableWidgetItem, QDialog, QMessageBox,
    QListWidgetItem, QGroupBox, QGridLayout, QComboBox, QFontDialog, QSpinBox,
    QDoubleSpinBox, QFrame, QSplitter, QSizePolicy, QScrollArea, QApplication,
    QFontComboBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from db_utils import execute_query, fetch_all, fetch_one


def get_ticket_fields():
    # This function remains the same
    try:
        query = "SELECT column_name FROM information_schema.columns WHERE table_name = 'tickets' ORDER BY ordinal_position;"
        rows = fetch_all(query)
        return [row['column_name'] for row in rows] if rows else []
    except Exception as e:
        QMessageBox.critical(None, "Database Error", f"Could not load fields from 'tickets' table.\nError: {e}")
        return []

class ReportDesigner(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Advanced Report Designer")
        self.resize(1400, 900)
        self.current_template_is_default = False

        # --- UI Construction ---
        root_splitter = QSplitter(Qt.Horizontal, self)
        
        # Left Panel: Template List
        self.template_group = self._create_template_selection_group()
        root_splitter.addWidget(self.template_group)

        # Center Panel: Scrollable area for all settings
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        center_container = QWidget()
        center_vbox = QVBoxLayout(center_container)
        
        self.page_layout_group = self._create_page_layout_group()
        self.field_group = self._create_field_editor_group()
        
        center_vbox.addWidget(self.page_layout_group)
        center_vbox.addWidget(self.field_group, 1) # Give field editor more space
        center_vbox.addStretch()
        scroll.setWidget(center_container)
        root_splitter.addWidget(scroll)

        # Right Panel: Actions
        self.action_panel = self._create_action_panel()
        root_splitter.addWidget(self.action_panel)

        root_splitter.setStretchFactor(0, 1) # Template list
        root_splitter.setStretchFactor(1, 4) # Main content
        root_splitter.setStretchFactor(2, 1) # Action panel

        dialog_layout = QHBoxLayout(self)
        dialog_layout.addWidget(root_splitter)
        
        # --- Final Setup ---
        self.setup_connections()
        self.load_template_names()
        self.set_a4_defaults()

    # --- UI Creation Methods ---

    def _create_template_selection_group(self):
        group = QGroupBox("Report Templates")
        layout = QVBoxLayout(group)
        self.template_list = QListWidget()
        layout.addWidget(self.template_list)
        return group

    def _create_page_layout_group(self):
        group = QGroupBox("Template & Page Layout")
        grid = QGridLayout(group)
        
        self.template_name_edit = QLineEdit(); self.template_name_edit.setPlaceholderText("Enter a unique template name")
        self.set_default_btn = QPushButton("Set as Default"); self.set_default_btn.setCheckable(True)
        
        self.pagewidth_edit = QDoubleSpinBox(); self.pagewidth_edit.setRange(50, 1000); self.pagewidth_edit.setSuffix(" mm")
        self.pageheight_edit = QDoubleSpinBox(); self.pageheight_edit.setRange(50, 1000); self.pageheight_edit.setSuffix(" mm")
        self.topmargin_edit = QDoubleSpinBox(); self.topmargin_edit.setRange(0, 100); self.topmargin_edit.setValue(10); self.topmargin_edit.setSuffix(" mm")
        self.leftmargin_edit = QDoubleSpinBox(); self.leftmargin_edit.setRange(0, 100); self.leftmargin_edit.setValue(10); self.leftmargin_edit.setSuffix(" mm")
        self.lineheight_edit = QDoubleSpinBox(); self.lineheight_edit.setRange(1, 50); self.lineheight_edit.setValue(7.0); self.lineheight_edit.setSuffix(" mm")

        self.header_font_family_combo = QFontComboBox(); self.header_font_family_combo.setCurrentFont(QFont("Arial"))
        self.header_font_size_edit = QSpinBox(); self.header_font_size_edit.setRange(5, 72); self.header_font_size_edit.setValue(10)
        self.detail_font_family_combo = QFontComboBox(); self.detail_font_family_combo.setCurrentFont(QFont("Arial"))
        self.detail_font_size_edit = QSpinBox(); self.detail_font_size_edit.setRange(5, 72); self.detail_font_size_edit.setValue(8)

        self.set_a4_btn = QPushButton("A4 Portrait"); self.set_a4_landscape_btn = QPushButton("A4 Landscape")

        grid.addWidget(QLabel("Template Name:"), 0, 0); grid.addWidget(self.template_name_edit, 0, 1, 1, 3)
        grid.addWidget(self.set_default_btn, 0, 4, 1, 2)
        grid.addWidget(QLabel("Page Width:"), 1, 0); grid.addWidget(self.pagewidth_edit, 1, 1);
        grid.addWidget(QLabel("Page Height:"), 1, 2); grid.addWidget(self.pageheight_edit, 1, 3);
        grid.addWidget(self.set_a4_btn, 1, 4); grid.addWidget(self.set_a4_landscape_btn, 1, 5)
        grid.addWidget(QLabel("Top Margin:"), 2, 0); grid.addWidget(self.topmargin_edit, 2, 1)
        grid.addWidget(QLabel("Left Margin:"), 2, 2); grid.addWidget(self.leftmargin_edit, 2, 3)
        grid.addWidget(QLabel("Line Height:"), 2, 4); grid.addWidget(self.lineheight_edit, 2, 5)
        grid.addWidget(QLabel("Header Font:"), 3, 0); grid.addWidget(self.header_font_family_combo, 3, 1, 1, 3);
        grid.addWidget(QLabel("Size:"), 3, 4); grid.addWidget(self.header_font_size_edit, 3, 5)
        grid.addWidget(QLabel("Detail Font:"), 4, 0); grid.addWidget(self.detail_font_family_combo, 4, 1, 1, 3)
        grid.addWidget(QLabel("Size:"), 4, 4); grid.addWidget(self.detail_font_size_edit, 4, 5)
        
        return group

    def _create_field_editor_group(self):
        group = QGroupBox("Field Layout (Columns)")
        layout = QHBoxLayout(group)

        # Available Fields
        available_group = QGroupBox("Available Fields")
        available_layout = QVBoxLayout(available_group)
        self.fields_list = QListWidget(); self.fields_list.addItems(get_ticket_fields())
        available_layout.addWidget(self.fields_list)
        layout.addWidget(available_group, 1)

        # Control Buttons
        buttons_vbox = QVBoxLayout(); buttons_vbox.addStretch()
        self.add_one_btn = QPushButton(">"); self.add_one_btn.setToolTip("Add selected field")
        self.remove_one_btn = QPushButton("<"); self.remove_one_btn.setToolTip("Remove selected field")
        buttons_vbox.addWidget(self.add_one_btn); buttons_vbox.addWidget(self.remove_one_btn)
        buttons_vbox.addStretch()
        layout.addLayout(buttons_vbox)

        # Selected Fields
        selected_group = QGroupBox("Fields in Report")
        selected_layout = QVBoxLayout(selected_group)
        self.field_table = QTableWidget(0, 4); self.field_table.setHorizontalHeaderLabels(["Field Name", "Caption", "Width (mm)", "Alignment"])
        self.field_table.horizontalHeader().setStretchLastSection(True)
        self.field_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.field_table.setSelectionMode(QTableWidget.SingleSelection)
        
        self.move_up_btn = QPushButton("Move Up ▲"); self.move_down_btn = QPushButton("Move Down ▼")
        move_layout = QHBoxLayout(); move_layout.addStretch(); move_layout.addWidget(self.move_up_btn); move_layout.addWidget(self.move_down_btn)
        selected_layout.addWidget(self.field_table)
        selected_layout.addLayout(move_layout)
        layout.addWidget(selected_group, 3)
        return group
    
    def _create_action_panel(self):
        panel = QFrame(); panel.setFrameShape(QFrame.StyledPanel)
        vbox = QVBoxLayout(panel)
        self.add_btn = QPushButton("✨ New"); self.save_btn = QPushButton("💾 Save"); self.delete_btn = QPushButton("🗑️ Delete"); self.exit_btn = QPushButton("Exit")
        vbox.addWidget(self.add_btn); vbox.addWidget(self.save_btn); vbox.addWidget(self.delete_btn); vbox.addStretch(); vbox.addWidget(self.exit_btn)
        return panel

    # --- Connections & Logic ---

    def setup_connections(self):
        self.exit_btn.clicked.connect(self.close)
        self.fields_list.itemDoubleClicked.connect(lambda item: self._add_field(item.text()))
        self.add_one_btn.clicked.connect(self.add_selected_field_from_list)
        self.remove_one_btn.clicked.connect(self.remove_selected_field_from_table)
        self.move_up_btn.clicked.connect(lambda: self._move_field(-1))
        self.move_down_btn.clicked.connect(lambda: self._move_field(1))
        self.save_btn.clicked.connect(self.save_report_template)
        self.add_btn.clicked.connect(self.add_new_template)
        self.delete_btn.clicked.connect(self.delete_report_template)
        self.template_list.itemClicked.connect(self.on_template_selected)
        self.set_default_btn.clicked.connect(self.on_set_default_clicked)
        self.set_a4_btn.clicked.connect(self.set_a4_defaults)
        self.set_a4_landscape_btn.clicked.connect(lambda: self.set_a4_defaults(landscape=True))

    def add_selected_field_from_list(self):
        if self.fields_list.currentItem():
            self._add_field(self.fields_list.currentItem().text())

    def remove_selected_field_from_table(self):
        if self.field_table.currentRow() >= 0:
            self.field_table.removeRow(self.field_table.currentRow())

    def _add_field(self, field_name):
        if not field_name: return
        for r in range(self.field_table.rowCount()):
            if self.field_table.item(r, 0) and self.field_table.item(r, 0).text() == field_name:
                QMessageBox.information(self, "Exists", f"Field '{field_name}' is already in the report.")
                return

        row = self.field_table.rowCount()
        self.field_table.insertRow(row)
        self.field_table.setItem(row, 0, QTableWidgetItem(field_name))
        self.field_table.setItem(row, 1, QTableWidgetItem(field_name.title()))
        
        width_spin = QDoubleSpinBox(); width_spin.setRange(5, 500); width_spin.setValue(40)
        self.field_table.setCellWidget(row, 2, width_spin)
        
        align_combo = QComboBox(); align_combo.addItems(["LEFT", "CENTER", "RIGHT"])
        self.field_table.setCellWidget(row, 3, align_combo)
        
        self.field_table.selectRow(row)

    def save_report_template(self):
        name = self.template_name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "Template Name is required.")
            return

        try:
            # Upsert the main template settings
            execute_query("""
                INSERT INTO ReportTemplate (reporttemplatename, "Default", pagewidth, pageheight, topmargin, leftmargin, headerfontsize, detailfontsize, lineheight, headerfontname, detailfontname)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (reporttemplatename) DO UPDATE SET
                    "Default" = EXCLUDED."Default", pagewidth = EXCLUDED.pagewidth, pageheight = EXCLUDED.pageheight, topmargin = EXCLUDED.topmargin, leftmargin = EXCLUDED.leftmargin,
                    headerfontsize = EXCLUDED.headerfontsize, detailfontsize = EXCLUDED.detailfontsize, lineheight = EXCLUDED.lineheight,
                    headerfontname = EXCLUDED.headerfontname, detailfontname = EXCLUDED.detailfontname;
            """, (
                name, self.set_default_btn.isChecked(), self.pagewidth_edit.value(), self.pageheight_edit.value(), self.topmargin_edit.value(),
                self.leftmargin_edit.value(), self.header_font_size_edit.value(), self.detail_font_size_edit.value(),
                self.lineheight_edit.value(), self.header_font_family_combo.currentFont().family(), self.detail_font_family_combo.currentFont().family()
            ))

            # Clear old details and save new ones
            execute_query("DELETE FROM ReportDetail WHERE reporttemplatename=%s", (name,))
            for r in range(self.field_table.rowCount()):
                execute_query("""
                    INSERT INTO ReportDetail (reporttemplatename, fieldname, fieldcaption, width, alignment)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    name, self.field_table.item(r, 0).text(), self.field_table.item(r, 1).text(),
                    self.field_table.cellWidget(r, 2).value(), self.field_table.cellWidget(r, 3).currentText()
                ))

            QMessageBox.information(self, "Saved", f"Template '{name}' saved successfully.")
            self.load_template_names() # Refresh list to show changes (like default status)
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Could not save template:\n{e}")

    def load_template_names(self):
        current = self.template_name_edit.text()
        self.template_list.clear()
        try:
            rows = fetch_all('SELECT reporttemplatename, "Default" FROM ReportTemplate ORDER BY reporttemplatename')
            item_to_select = None
            for r in rows:
                name, is_default = r["reporttemplatename"], r["Default"]
                text = f"{name} {'(Default)' if is_default else ''}"
                item = QListWidgetItem(text)
                item.setData(Qt.UserRole, name) # Store clean name
                self.template_list.addItem(item)
                if name == current:
                    item_to_select = item
            if item_to_select:
                self.template_list.setCurrentItem(item_to_select)
        except Exception as e:
            QMessageBox.critical(self, "DB Error", f"Could not load templates:\n{e}")
            
    def on_template_selected(self, item):
        if not item: return
        name = item.data(Qt.UserRole)
        self.load_template_data(name)

    def load_template_data(self, name):
        self.clear_all_fields()
        self.template_name_edit.setText(name)
        try:
            template_data = fetch_one("SELECT * FROM ReportTemplate WHERE reporttemplatename=%s", (name,))
            if not template_data: return

            self.set_default_btn.setChecked(template_data.get('Default', False))
            self.pagewidth_edit.setValue(template_data.get('pagewidth', 210))
            self.pageheight_edit.setValue(template_data.get('pageheight', 297))
            self.topmargin_edit.setValue(template_data.get('topmargin', 10))
            self.leftmargin_edit.setValue(template_data.get('leftmargin', 10))
            self.lineheight_edit.setValue(float(template_data.get('lineheight', 7.0)))
            self.header_font_size_edit.setValue(template_data.get('headerfontsize', 10))
            self.detail_font_size_edit.setValue(template_data.get('detailfontsize', 8))
            self.header_font_family_combo.setCurrentFont(QFont(template_data.get('headerfontname', 'Arial')))
            self.detail_font_family_combo.setCurrentFont(QFont(template_data.get('detailfontname', 'Arial')))
            
            detail_rows = fetch_all("SELECT * FROM ReportDetail WHERE reporttemplatename=%s ORDER BY id", (name,))
            self.field_table.setRowCount(0)
            for row_data in detail_rows:
                self._add_field(row_data['fieldname'])
                row_idx = self.field_table.rowCount() - 1
                self.field_table.item(row_idx, 1).setText(row_data['fieldcaption'])
                self.field_table.cellWidget(row_idx, 2).setValue(row_data.get('width', 40))
                self.field_table.cellWidget(row_idx, 3).setCurrentText(row_data.get('alignment', 'LEFT'))

        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Could not load template '{name}':\n{e}")

    def on_set_default_clicked(self, is_checked):
        name = self.template_name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "No Template", "Please enter a template name before setting it as default.")
            self.set_default_btn.setChecked(not is_checked)
            return
        
        try:
            # When setting a new default, unset the old one first
            if is_checked:
                execute_query('UPDATE ReportTemplate SET "Default" = FALSE WHERE "Default" = TRUE')
            
            # Update the current template's default status
            execute_query('UPDATE ReportTemplate SET "Default" = %s WHERE reporttemplatename = %s', (is_checked, name))
            self.save_report_template() # Save all changes along with default status
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Could not set default status.\n{e}")
            
    # --- Utility Methods ---
    
    def set_a4_defaults(self, landscape=False):
        if landscape:
            self.pagewidth_edit.setValue(297)
            self.pageheight_edit.setValue(210)
        else:
            self.pagewidth_edit.setValue(210)
            self.pageheight_edit.setValue(297)

    def _move_field(self, direction: int):
        row = self.field_table.currentRow()
        if row < 0: return
        target = row + direction
        if not (0 <= target < self.field_table.rowCount()): return

        # Take all items and widgets
        rowData = [(self.field_table.item(row, c).clone() if self.field_table.item(row, c) else None) for c in range(2)]
        rowWidgets = [(self.field_table.cellWidget(row, c), c) for c in [2, 3]]

        targetData = [(self.field_table.item(target, c).clone() if self.field_table.item(target, c) else None) for c in range(2)]
        targetWidgets = [(self.field_table.cellWidget(target, c), c) for c in [2, 3]]
        
        # Place target data in current row
        for c, item in enumerate(targetData): self.field_table.setItem(row, c, item)
        for w, c in targetWidgets: 
            if w: self.field_table.setCellWidget(row, c, w)

        # Place current data in target row
        for c, item in enumerate(rowData): self.field_table.setItem(target, c, item)
        for w, c in rowWidgets:
            if w: self.field_table.setCellWidget(target, c, w)
            
        self.field_table.selectRow(target)

    def add_new_template(self):
        self.clear_all_fields()
        self.template_list.clearSelection()
        self.template_name_edit.setFocus()

    def clear_all_fields(self):
        self.template_name_edit.clear()
        self.set_default_btn.setChecked(False)
        self.set_a4_defaults()
        self.topmargin_edit.setValue(10); self.leftmargin_edit.setValue(10)
        self.header_font_family_combo.setCurrentFont(QFont("Arial"))
        self.detail_font_family_combo.setCurrentFont(QFont("Arial"))
        self.header_font_size_edit.setValue(10); self.detail_font_size_edit.setValue(8)
        self.lineheight_edit.setValue(7.0)
        self.field_table.setRowCount(0)

    def delete_report_template(self):
        selected = self.template_list.currentItem()
        if not selected: return
        name = selected.data(Qt.UserRole)
        if QMessageBox.question(self, "Confirm Delete", f"Are you sure you want to permanently delete template '{name}'?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            try:
                execute_query("DELETE FROM ReportTemplate WHERE reporttemplatename=%s", (name,))
                # Related details are deleted via CASCADE constraint in DB
                self.load_template_names()
                self.add_new_template()
            except Exception as e:
                QMessageBox.critical(self, "DB Error", f"Could not delete template:\n{e}")

    def closeEvent(self, event):
        if self.parent(): self.parent().show()
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # You need a running database connection for the designer to work.
    # from db_utils import init_db
    # init_db(user="your_user", password="your_password", dbname="your_db")
    dlg = ReportDesigner()
    dlg.show()
    sys.exit(app.exec_())
