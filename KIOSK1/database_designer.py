from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QComboBox, QListWidget,
    QVBoxLayout, QHBoxLayout, QGridLayout, QDialog, QMessageBox
)
from PyQt5.QtCore import Qt

from db_utils import execute_query, fetch_one, fetch_all, get_new_connection

FIELD_TYPES = {
    "String": "character varying",
    "Number": "integer",
    "Date/Time": "date",
    "Time/Time": "time without time zone",
    "Double": "double precision",
    "True/False": "boolean"
}

class DatabaseDesigner(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Database Designer")
        self.setFixedSize(380, 340)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(7)

        # Table Name
        tn_layout = QHBoxLayout()
        tn_label = QLabel("Table Name:")
        tn_label.setFixedWidth(90)
        self.table_combo = QComboBox()
        self.table_combo.setFixedWidth(170)
        self.table_combo.addItems(["Tickets"]) # Only Tickets table is editable for dynamic fields
        tn_layout.addWidget(tn_label)
        tn_layout.addWidget(self.table_combo)
        tn_layout.addStretch(1)
        main_layout.addLayout(tn_layout)
        self.table_combo.currentTextChanged.connect(self.load_fields)

        # Fields list
        fields_label = QLabel("Non-Mandatory Fields in TableMaster:")
        main_layout.addWidget(fields_label)
        self.fields_list = QListWidget()
        self.fields_list.setFixedHeight(80)
        main_layout.addWidget(self.fields_list)
        self.fields_list.currentTextChanged.connect(self.load_field_details)

        # Field editing controls - aligned as per your requirements
        field_grid = QGridLayout()
        field_grid.setHorizontalSpacing(7)
        field_grid.setVerticalSpacing(7)

        field_grid.addWidget(QLabel("Field Name:"), 0, 0)
        self.field_name_edit = QLineEdit()
        field_grid.addWidget(self.field_name_edit, 0, 1)

        field_grid.addWidget(QLabel("Field Type:"), 1, 0)
        self.field_type_combo = QComboBox()
        self.field_type_combo.addItems(list(FIELD_TYPES.keys()))
        field_grid.addWidget(self.field_type_combo, 1, 1)

        field_grid.addWidget(QLabel("Field Size:"), 2, 0)
        self.field_size_edit = QLineEdit()
        field_grid.addWidget(self.field_size_edit, 2, 1)

        field_grid.addWidget(QLabel("Caption:"), 3, 0)
        self.caption_edit = QLineEdit()
        field_grid.addWidget(self.caption_edit, 3, 1)

        main_layout.addLayout(field_grid)

        # Buttons
        btn_row = QHBoxLayout()
        self.insert_btn = QPushButton("Insert")
        self.remove_btn = QPushButton("Remove")
        self.exit_btn = QPushButton("Exit")
        for btn in [self.insert_btn, self.remove_btn, self.exit_btn]:
            btn.setFixedWidth(100)
            btn_row.addWidget(btn)
        btn_row.addStretch(1)
        main_layout.addLayout(btn_row)

        self.insert_btn.clicked.connect(self.insert_field)
        self.remove_btn.clicked.connect(self.remove_field)
        self.exit_btn.clicked.connect(self.return_to_administration)

        self.load_fields()

    def load_fields(self):
        # Show only non-mandatory fields from tablemaster for Tickets
        table = self.table_combo.currentText()
        self.fields_list.clear()
        fields = fetch_all(
            "SELECT fieldname FROM tablemaster WHERE tablename=%s AND (mandatory = FALSE OR mandatory IS NULL) ORDER BY id",
            (table,)
        )
        for r in fields:
            self.fields_list.addItem(r["fieldname"])

    def load_field_details(self, fieldname):
        table = self.table_combo.currentText()
        if not table or not fieldname:
            return
        row = fetch_one(
            "SELECT fieldtype, fieldsize, fieldcaption FROM tablemaster WHERE tablename=%s AND fieldname=%s",
            (table, fieldname)
        )
        if row:
            self.field_name_edit.setText(fieldname)
            self.field_type_combo.setCurrentText(row["fieldtype"] or "")
            self.field_size_edit.setText(str(row["fieldsize"] or ""))
            self.caption_edit.setText(row["fieldcaption"] or "")

    def insert_field(self):
        table = self.table_combo.currentText()
        fieldname = self.field_name_edit.text().strip()
        fieldtype = self.field_type_combo.currentText()
        fieldsize = self.field_size_edit.text().strip()
        caption = self.caption_edit.text().strip()
        if not (table and fieldname and fieldtype and caption):
            QMessageBox.warning(self, "Input Error", "All field details required.")
            return

        # Insert into tablemaster with mandatory=False
        try:
            row = fetch_one(
                "SELECT id FROM tablemaster WHERE tablename=%s AND fieldname=%s",
                (table, fieldname)
            )
            if row:
                QMessageBox.warning(self, "Field Exists", "Field already exists. Remove it first to re-add.")
                return
            execute_query(
                "INSERT INTO tablemaster (tablename, fieldname, fieldcaption, fieldtype, fieldsize, mandatory) VALUES (%s,%s,%s,%s,%s,%s)",
                (table, fieldname, caption, fieldtype, int(fieldsize or 0), False)
            )
            # Add column to tickets table
            self.add_column_to_tickets(fieldname, fieldtype, fieldsize)
            QMessageBox.information(self, "Success", f"Field '{fieldname}' inserted to TableMaster and Tickets.")
            self.load_fields()
        except Exception as e:
            QMessageBox.warning(self, "DB Error", str(e))

    def add_column_to_tickets(self, fieldname, fieldtype, fieldsize):
        # Only add if not exists
        col_type = FIELD_TYPES.get(fieldtype, "character varying")
        if col_type == "character varying":
            # If string, use fieldsize
            if fieldsize and int(fieldsize) > 0:
                col_type = f"character varying({int(fieldsize)})"
        try:
            # Check if column exists
            exists = fetch_one("""
                SELECT 1 FROM information_schema.columns
                WHERE table_name='tickets' AND column_name=%s
            """, (fieldname,))
            if exists:
                return
            # Add column
            alter_stmt = f'ALTER TABLE tickets ADD COLUMN "{fieldname}" {col_type};'
            execute_query(alter_stmt)
        except Exception as e:
            QMessageBox.warning(self, "DB Error", f"Column add failed: {e}")

    def remove_field(self):
        table = self.table_combo.currentText()
        fieldname = self.field_name_edit.text().strip()
        if not (table and fieldname):
            QMessageBox.warning(self, "Input Error", "Table and Field Name required.")
            return
        try:
            # Remove from tablemaster
            execute_query(
                "DELETE FROM tablemaster WHERE tablename=%s AND fieldname=%s",
                (table, fieldname)
            )
            # Remove from tickets table
            self.remove_column_from_tickets(fieldname)
            QMessageBox.information(self, "Success", f"Field '{fieldname}' removed from TableMaster and Tickets.")
            self.load_fields()
        except Exception as e:
            QMessageBox.warning(self, "DB Error", str(e))

    def remove_column_from_tickets(self, fieldname):
        try:
            # Check if column exists
            exists = fetch_one("""
                SELECT 1 FROM information_schema.columns
                WHERE table_name='tickets' AND column_name=%s
            """, (fieldname,))
            if not exists:
                return
            alter_stmt = f'ALTER TABLE tickets DROP COLUMN "{fieldname}";'
            execute_query(alter_stmt)
        except Exception as e:
            QMessageBox.warning(self, "DB Error", f"Column remove failed: {e}")

    def return_to_administration(self):
        self.hide()
        parent = self.parent()
        if parent:
            parent.show()
