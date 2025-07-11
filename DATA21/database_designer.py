from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QComboBox, QListWidget, QPushButton,
    QVBoxLayout, QHBoxLayout, QGridLayout, QMessageBox, QApplication
)
from PyQt5.QtCore import Qt
import sys

# Import db_utils connection helpers
from db_utils import execute_query, fetch_one, fetch_all

# Import FormulaEditor dialog
from formula_editor import FormulaEditor

# Hardcoded mandatory fields for each table
TABLES = {
    "tickets": [
        "TicketNumber", "VehicleNumber", "Date", "Time", "EmptyWeight",
        "LoadedWeight", "EmptyWeightDate", "EmptyWeightTime", "LoadWeightDate",
        "LoadWeightTime", "NetWeight", "Pending", "Closed", "Exported", "Shift",
        "Materialname", "SupplierName", "State"
    ],
    "material": [
        "materialcode", "materialname", "materialdescription"
    ],
    "suppliers": [
        "suppliercode", "suppliername", "supplieraddress", "contactperson", "contactnumber"
    ]
}
PSQL_TYPES = [
    "integer",
    "character varying(50)",
    "character varying(2)",
    "date",
    "time without time zone",
    "Boolean"
]

def get_table_columns(table):
    try:
        query = """
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = %s AND table_schema = 'public'
        """
        rows = fetch_all(query, (table,))
        columns = [row['column_name'] for row in rows]
        return columns
    except Exception as e:
        print("Database error:", e)
        return []

class DatabaseDesigner(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Database Designer")
        self.setFixedSize(270, 330)

        layout = QVBoxLayout(self)
        top_grid = QGridLayout()
        top_grid.addWidget(QLabel("Table Name:"), 0, 0)
        self.table_combo = QComboBox()
        self.table_combo.addItems(["tickets", "suppliers", "material"])
        self.table_combo.currentTextChanged.connect(self.load_fields)
        top_grid.addWidget(self.table_combo, 0, 1)
        layout.addLayout(top_grid)

        layout.addWidget(QLabel("Fields:"))
        self.fields_list = QListWidget()
        layout.addWidget(self.fields_list)

        field_grid = QGridLayout()
        field_grid.addWidget(QLabel("Field Name:"), 0, 0)
        self.field_name = QLineEdit()
        field_grid.addWidget(self.field_name, 0, 1)
        field_grid.addWidget(QLabel("Field Type:"), 1, 0)
        self.field_type = QComboBox()
        self.field_type.addItems(PSQL_TYPES)
        field_grid.addWidget(self.field_type, 1, 1)
        field_grid.addWidget(QLabel("Field Size:"), 2, 0)
        self.field_size = QLineEdit()
        field_grid.addWidget(self.field_size, 2, 1)
        field_grid.addWidget(QLabel("Caption:"), 3, 0)
        self.field_caption = QLineEdit()
        field_grid.addWidget(self.field_caption, 3, 1)
        layout.addLayout(field_grid)

        btn_layout = QHBoxLayout()
        self.btn_insert = QPushButton("Insert")
        self.btn_remove = QPushButton("Remove")
        self.btn_formula = QPushButton("Formula")
        self.btn_formula.setEnabled(True)  # enable the button
        self.btn_exit = QPushButton("Exit")
        btn_layout.addWidget(self.btn_insert)
        btn_layout.addWidget(self.btn_remove)
        btn_layout.addWidget(self.btn_formula)
        btn_layout.addWidget(self.btn_exit)
        layout.addLayout(btn_layout)

        self.btn_insert.clicked.connect(self.insert_field)
        self.btn_remove.clicked.connect(self.remove_field)
        self.btn_exit.clicked.connect(self.close)
        self.btn_formula.clicked.connect(self.open_formula_editor)
        self.load_fields(self.table_combo.currentText())

    def load_fields(self, table_name):
        self.fields_list.clear()
        all_columns = get_table_columns(table_name)
        # Only show non-mandatory fields
        for col in all_columns:
            if col.lower() not in [f.lower() for f in TABLES[table_name]]:
                self.fields_list.addItem(col)

    def insert_field(self):
        table_name = self.table_combo.currentText()
        field = self.field_name.text().strip()
        ftype = self.field_type.currentText()
        fsize = self.field_size.text().strip()
        caption = self.field_caption.text().strip()

        if not field:
            QMessageBox.warning(self, "Input Error", "Field Name cannot be empty.")
            return

        if field.lower() in [f.lower() for f in TABLES[table_name]]:
            QMessageBox.warning(self, "Input Error", "Cannot add a mandatory field.")
            return

        current_columns = get_table_columns(table_name)
        if field.lower() in [c.lower() for c in current_columns]:
            QMessageBox.warning(self, "Input Error", "Field already exists in the table.")
            return

        # Compose type string
        type_sql = ftype
        if "character varying" in ftype:
            # Allow custom size if specified
            size = fsize if fsize.isdigit() else ftype.split("(")[-1].replace(")", "")
            type_sql = f"character varying({size})"

        try:
            query = f'ALTER TABLE "{table_name}" ADD COLUMN "{field}" {type_sql}'
            execute_query(query)
            self.load_fields(table_name)
            self.field_name.clear()
            self.field_size.clear()
            self.field_caption.clear()
            self.field_type.setCurrentIndex(0)
            QMessageBox.information(self, "Success", f"Field '{field}' added to table '{table_name}'.")
        except Exception as e:
            QMessageBox.critical(self, "DB Error", str(e))

    def remove_field(self):
        table_name = self.table_combo.currentText()
        selected = self.fields_list.currentItem()
        if not selected:
            QMessageBox.warning(self, "Selection Error", "No field selected.")
            return
        field = selected.text()

        # Protect mandatory fields (shouldn't show in list anyway)
        if field.lower() in [f.lower() for f in TABLES[table_name]]:
            QMessageBox.warning(self, "Error", "Cannot remove a mandatory field.")
            return

        try:
            query = f'ALTER TABLE "{table_name}" DROP COLUMN "{field}"'
            execute_query(query)
            self.load_fields(table_name)
            QMessageBox.information(self, "Success", f"Field '{field}' removed from table '{table_name}'.")
        except Exception as e:
            QMessageBox.critical(self, "DB Error", str(e))

    def open_formula_editor(self):
        self.formula_window = FormulaEditor()  # <-- No parent here, or use parent=None
        # Positioning code if desired
        parent_pos = self.pos()
        parent_size = self.size()
        new_x = parent_pos.x()
        new_y = parent_pos.y() + parent_size.height()
        self.formula_window.move(new_x, new_y)
        self.formula_window.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = DatabaseDesigner()
    w.show()
    sys.exit(app.exec_())
