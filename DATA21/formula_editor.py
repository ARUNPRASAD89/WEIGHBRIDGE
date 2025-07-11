from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QComboBox, QPushButton, QHBoxLayout, QVBoxLayout,
    QGridLayout, QMessageBox, QDialog
)
from PyQt5.QtCore import Qt
from db_utils import execute_query, fetch_one, fetch_all

# Mandatory fields in tickets table
MANDATORY_FIELDS = [
    "TicketNumber", "VehicleNumber", "Date", "Time", "EmptyWeight", "LoadedWeight",
    "EmptyWeightDate", "EmptyWeightTime", "LoadWeightDate", "LoadWeightTime",
    "NetWeight", "Pending", "Closed", "Exported", "Shift", "Materialname",
    "SupplierName", "State"
]

def get_all_ticket_fields():
    """Fetch all fields from tickets table."""
    try:
        query = """
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = %s AND table_schema = 'public'
        """
        rows = fetch_all(query, ('tickets',))
        all_fields = [row['column_name'] for row in rows]
        return all_fields
    except Exception as e:
        print("DB error while fetching ticket fields:", e)
        return []

def get_non_mandatory_ticket_fields():
    """Fetch all fields from tickets, return only non-mandatory ones."""
    all_fields = get_all_ticket_fields()
    return [f for f in all_fields if f not in MANDATORY_FIELDS]

def get_saved_formulas():
    """Fetch all saved formulas from FormulaTable, return as list of dicts."""
    try:
        query = 'SELECT "FormulaId", "strFormulaName", "formulaList" FROM "FormulaTable"'
        formulas = fetch_all(query)
        return formulas
    except Exception as e:
        print("DB error while fetching formulas:", e)
        return []

# Standard operator symbols for formula editor
OPERATORS = ["+", "-", "*", "/", "%", "(", ")", ".", " "]

class FormulaLookupDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Search")
        self.setFixedSize(340, 100)
        layout = QGridLayout(self)
        layout.addWidget(QLabel("Look Up"), 0, 0, 1, 2)
        layout.addWidget(QLabel("By Id"), 1, 0)
        self.id_combo = QComboBox()
        layout.addWidget(self.id_combo, 1, 1)
        layout.addWidget(QLabel("By Name"), 2, 0)
        self.name_combo = QComboBox()
        layout.addWidget(self.name_combo, 2, 1)
        btn_row = QHBoxLayout()
        self.ok_btn = QPushButton("OK")
        self.exit_btn = QPushButton("Exit")
        btn_row.addWidget(self.ok_btn)
        btn_row.addWidget(self.exit_btn)
        layout.addLayout(btn_row, 3, 0, 1, 2)

        # Populate formulas
        self.formulas = get_saved_formulas()
        ids = [str(f.get("FormulaId", "")) for f in self.formulas]
        names = [f.get("strFormulaName", "") for f in self.formulas]
        self.id_combo.addItems(ids)
        self.name_combo.addItems(names)

        self.ok_btn.clicked.connect(self.accept)
        self.exit_btn.clicked.connect(self.reject)

    def get_selected_formula(self):
        idx = self.name_combo.currentIndex()
        if 0 <= idx < len(self.formulas):
            return self.formulas[idx]
        return None

class FormulaEditor(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Formula Editor")
        self.setFixedSize(500, 190)

        main_layout = QVBoxLayout(self)
        grid = QGridLayout()
        grid.addWidget(QLabel("Name:"), 0, 0)
        self.name_edit = QLineEdit()
        grid.addWidget(self.name_edit, 0, 1)
        self.lookup_btn = QPushButton("...")
        grid.addWidget(self.lookup_btn, 0, 2)

        grid.addWidget(QLabel("Field Name:"), 0, 3)
        self.field_combo = QComboBox()
        self.field_combo.addItems(get_non_mandatory_ticket_fields())
        grid.addWidget(self.field_combo, 0, 4)
        self.btn_insert_field = QPushButton("Insert")
        grid.addWidget(self.btn_insert_field, 0, 5)

        grid.addWidget(QLabel("Operator:"), 1, 0)
        self.operator_combo = QComboBox()
        self.operator_combo.addItems(OPERATORS)
        grid.addWidget(self.operator_combo, 1, 1)
        self.btn_insert_operator = QPushButton("Insert")
        grid.addWidget(self.btn_insert_operator, 1, 2)
        grid.addWidget(QLabel("Constant:"), 1, 3)
        self.constant_edit = QLineEdit()
        grid.addWidget(self.constant_edit, 1, 4)
        self.btn_insert_constant = QPushButton("Insert")
        grid.addWidget(self.btn_insert_constant, 1, 5)

        grid.addWidget(QLabel("Formula:"), 2, 0)
        self.formula_edit = QLineEdit()
        self.formula_edit.setReadOnly(True)
        grid.addWidget(self.formula_edit, 2, 1, 1, 4)
        self.btn_clear_formula = QPushButton("X")
        grid.addWidget(self.btn_clear_formula, 2, 5)
        main_layout.addLayout(grid)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.save_btn = QPushButton("Save")
        self.clear_btn = QPushButton("Clear")
        self.delete_btn = QPushButton("Delete")
        self.exit_btn = QPushButton("Exit")
        for btn in [self.save_btn, self.clear_btn, self.delete_btn, self.exit_btn]:
            btn_layout.addWidget(btn)
        main_layout.addLayout(btn_layout)

        # Connect buttons
        self.btn_insert_field.clicked.connect(self.insert_field)
        self.btn_insert_operator.clicked.connect(self.insert_operator)
        self.btn_insert_constant.clicked.connect(self.insert_constant)
        self.btn_clear_formula.clicked.connect(self.clear_formula)
        self.clear_btn.clicked.connect(self.clear_all)
        self.exit_btn.clicked.connect(self.close)
        self.lookup_btn.clicked.connect(self.show_lookup_dialog)
        self.save_btn.clicked.connect(self.save_formula)

    def insert_field(self):
        field = self.field_combo.currentText()
        if field:
            self.formula_edit.setText(self.formula_edit.text() + field)

    def insert_operator(self):
        op = self.operator_combo.currentText()
        if op:
            self.formula_edit.setText(self.formula_edit.text() + op)

    def insert_constant(self):
        const = self.constant_edit.text()
        if const:
            self.formula_edit.setText(self.formula_edit.text() + const)
            self.constant_edit.clear()

    def clear_formula(self):
        self.formula_edit.clear()

    def clear_all(self):
        self.name_edit.clear()
        self.formula_edit.clear()
        self.constant_edit.clear()
        self.field_combo.setCurrentIndex(0)
        self.operator_combo.setCurrentIndex(0)

    def save_formula(self):
        name = self.name_edit.text().strip()
        formula = self.formula_edit.text().strip()
        all_fields = get_all_ticket_fields()

        if not name:
            QMessageBox.warning(self, "Input Error", "Name cannot be empty.")
            return

        if name in all_fields:
            QMessageBox.warning(self, "Field Error", f"'{name}' already exists as a field in the tickets table.")
            return

        # Create the field in tickets table
        try:
            alter_query = f'ALTER TABLE "tickets" ADD COLUMN "{name}" integer'
            execute_query(alter_query)
        except Exception as e:
            # If field exists, show error (should not happen due to check above)
            QMessageBox.critical(self, "DB Error", f"Failed to add field '{name}' to tickets table: {e}")
            return

        # Save the formula in FormulaTable
        try:
            insert_query = 'INSERT INTO "FormulaTable" ("strFormulaName", "formulaList") VALUES (%s, %s)'
            execute_query(insert_query, (name, formula))
            QMessageBox.information(self, "Success", f"Field '{name}' created in tickets table and formula saved.")
        except Exception as e:
            QMessageBox.critical(self, "DB Error", f"Failed to save formula: {e}")

    def show_lookup_dialog(self):
        dlg = FormulaLookupDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            formula = dlg.get_selected_formula()
            if formula:
                self.name_edit.setText(formula.get("strFormulaName", ""))
                self.formula_edit.setText(formula.get("formulaList", ""))
