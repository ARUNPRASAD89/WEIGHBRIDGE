from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QComboBox, QPushButton, QHBoxLayout, QVBoxLayout, QGridLayout, QDialog, QMessageBox
)
from PyQt5.QtCore import Qt

from db_utils import execute_query, fetch_one, fetch_all, get_new_connection

def load_nonmandatory_field_names():
    """
    Load field names from tablemaster where tablename='Tickets' and mandatory is False or NULL,
    inspired by TicketDataEntryDesignerWindow logic.
    """
    rows = fetch_all(
        "SELECT fieldname FROM tablemaster WHERE tablename='Tickets' AND (mandatory = FALSE OR mandatory IS NULL) ORDER BY id"
    )
    return [r["fieldname"] for r in rows]

def insert_formula(formulaname, formulalist):
    formulaid_row = fetch_one("SELECT COALESCE(MAX(formulaid), 0) + 1 AS nextid FROM formulatable")
    formulaid = formulaid_row["nextid"]
    execute_query(
        "INSERT INTO formulatable (formulaid, strformulaname, formulalist) VALUES (%s, %s, %s)",
        (formulaid, formulaname, formulalist)
    )

def insert_tablemaster_field(fieldcaption, fieldname, fieldsize=50, fieldtype='integer', mandatory=False, tablename='Tickets'):
    execute_query(
        "INSERT INTO tablemaster (fieldcaption, fieldname, fieldsize, fieldtype, mandatory, tablename) VALUES (%s, %s, %s, %s, %s, %s)",
        (fieldcaption, fieldname, fieldsize, fieldtype, mandatory, tablename)
    )

def add_field_to_tickets(fieldname, fieldtype='integer'):
    row = fetch_one(
        "SELECT column_name FROM information_schema.columns WHERE table_name='tickets' AND column_name=%s",
        (fieldname,)
    )
    if not row:
        alter_sql = f'ALTER TABLE tickets ADD COLUMN "{fieldname}" {fieldtype};'
        conn = get_new_connection()
        cur = conn.cursor()
        cur.execute(alter_sql)
        conn.commit()
        cur.close()
        conn.close()

def search_formula_by_id_name(formula_id=None, formula_name=None):
    if formula_id:
        rows = fetch_all("SELECT * FROM formulatable WHERE formulaid = %s", (formula_id,))
    elif formula_name:
        rows = fetch_all("SELECT * FROM formulatable WHERE strformulaname ILIKE %s", (f"%{formula_name}%",))
    else:
        rows = fetch_all("SELECT * FROM formulatable ORDER BY formulaid")
    return rows

class SearchDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Search")
        self.setFixedSize(300, 120)

        main_layout = QVBoxLayout(self)
        grid = QGridLayout()
        grid.addWidget(QLabel("By Id"), 0, 0)
        self.id_combo = QComboBox()
        self.id_combo.setEditable(True)
        grid.addWidget(self.id_combo, 0, 1)

        grid.addWidget(QLabel("By Name"), 1, 0)
        self.name_combo = QComboBox()
        self.name_combo.setEditable(True)
        grid.addWidget(self.name_combo, 1, 1)

        # Populate combos with existing formula ids and names
        formulas = fetch_all("SELECT formulaid, strformulaname FROM formulatable ORDER BY formulaid")
        self.id_combo.addItem("")
        self.name_combo.addItem("")
        for f in formulas:
            self.id_combo.addItem(str(f["formulaid"]))
            self.name_combo.addItem(f["strformulaname"])

        btn_layout = QHBoxLayout()
        self.ok_btn = QPushButton("OK")
        self.exit_btn = QPushButton("Exit")
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.exit_btn)

        main_layout.addLayout(grid)
        main_layout.addLayout(btn_layout)

        self.ok_btn.clicked.connect(self.perform_search)
        self.exit_btn.clicked.connect(self.close)

    def perform_search(self):
        formula_id = self.id_combo.currentText().strip()
        formula_name = self.name_combo.currentText().strip()
        result = search_formula_by_id_name(
            formula_id if formula_id else None,
            formula_name if formula_name else None
        )
        msg = ""
        if result:
            for r in result:
                msg += f"ID: {r['formulaid']}, Name: {r['strformulaname']}, Formula: {r['formulalist']}\n"
        else:
            msg = "No matching formula found."
        msg += "\nReferenced screenshot: ![image1](image1)"
        QMessageBox.information(self, "Search Result", msg)

class FormulaEditor(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Formula Editor")

        main_layout = QVBoxLayout(self)
        label = QLabel("Formula Editor Window")
        main_layout.addWidget(label)

        grid = QGridLayout()

        self.name_edit = QLineEdit()
        grid.addWidget(QLabel("Name:"), 0, 0)
        grid.addWidget(self.name_edit, 0, 1)

        self.search_btn = QPushButton("...")
        grid.addWidget(self.search_btn, 0, 2)
        self.search_btn.clicked.connect(self.open_search)

        self.field_combo = QComboBox()
        self.reload_field_combo()
        grid.addWidget(QLabel("Field Name:"), 0, 3)
        grid.addWidget(self.field_combo, 0, 4)
        self.insert_field_btn = QPushButton("Insert")
        grid.addWidget(self.insert_field_btn, 0, 5)

        self.operator_combo = QComboBox()
        self.operator_combo.addItems(['+', '-', '*', '/', '(', ')'])
        grid.addWidget(QLabel("Operator:"), 1, 0)
        grid.addWidget(self.operator_combo, 1, 1)
        self.insert_operator_btn = QPushButton("Insert")
        grid.addWidget(self.insert_operator_btn, 1, 2)

        self.constant_edit = QLineEdit()
        grid.addWidget(QLabel("Constant:"), 1, 3)
        grid.addWidget(self.constant_edit, 1, 4)
        self.insert_constant_btn = QPushButton("Insert")
        grid.addWidget(self.insert_constant_btn, 1, 5)

        self.formula_edit = QLineEdit()
        grid.addWidget(QLabel("Formula:"), 2, 0)
        grid.addWidget(self.formula_edit, 2, 1, 1, 4)
        self.x_btn = QPushButton("X")
        grid.addWidget(self.x_btn, 2, 5)

        main_layout.addLayout(grid)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.save_btn = QPushButton("Save")
        self.clear_btn = QPushButton("Clear")
        self.delete_btn = QPushButton("Delete")
        self.exit_btn2 = QPushButton("Exit")
        for btn in [self.save_btn, self.clear_btn, self.delete_btn, self.exit_btn2]:
            btn_layout.addWidget(btn)
        main_layout.addLayout(btn_layout)

        self.insert_field_btn.clicked.connect(self.insert_field)
        self.insert_operator_btn.clicked.connect(self.insert_operator)
        self.insert_constant_btn.clicked.connect(self.insert_constant)
        self.save_btn.clicked.connect(self.save_formula)
        self.clear_btn.clicked.connect(self.clear_formula)
        self.delete_btn.clicked.connect(self.delete_formula)
        self.exit_btn2.clicked.connect(self.return_to_administration)
        self.x_btn.clicked.connect(self.clear_formula_field)

    def reload_field_combo(self):
        """Load field names using the same logic as TicketDataEntryDesignerWindow."""
        self.field_combo.clear()
        for fieldname in load_nonmandatory_field_names():
            self.field_combo.addItem(fieldname)

    def open_search(self):
        dlg = SearchDialog(self)
        dlg.exec_()

    def insert_field(self):
        fieldname = self.field_combo.currentText()
        if fieldname:
            self.formula_edit.insert(fieldname)

    def insert_operator(self):
        op = self.operator_combo.currentText()
        if op:
            self.formula_edit.insert(op)

    def insert_constant(self):
        const = self.constant_edit.text()
        if const:
            self.formula_edit.insert(const)

    def save_formula(self):
        name = self.name_edit.text().strip()
        formula = self.formula_edit.text().strip()
        if not name or not formula:
            QMessageBox.warning(self, "Input Error", "Name and Formula cannot be empty.")
            return

        insert_formula(name, formula)
        insert_tablemaster_field(fieldcaption=name, fieldname=name, fieldsize=50, fieldtype='integer', mandatory=False, tablename='Tickets')
        add_field_to_tickets(name, fieldtype='integer')
        QMessageBox.information(self, "Saved", f"Formula '{name}' saved and field added to Tickets.")
        self.clear_formula()
        self.reload_field_combo()

    def delete_formula(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Input Error", "Please enter/select a formula name to delete.")
            return

        execute_query("DELETE FROM formulatable WHERE strformulaname = %s", (name,))
        execute_query("DELETE FROM tablemaster WHERE fieldname = %s AND tablename = 'Tickets'", (name,))
        row = fetch_one("SELECT column_name FROM information_schema.columns WHERE table_name='tickets' AND column_name=%s", (name,))
        if row:
            conn = get_new_connection()
            cur = conn.cursor()
            cur.execute(f'ALTER TABLE tickets DROP COLUMN "{name}";')
            conn.commit()
            cur.close()
            conn.close()
        QMessageBox.information(self, "Deleted", f"Formula and field '{name}' deleted from weighbridge system.")
        self.clear_formula()
        self.reload_field_combo()

    def clear_formula(self):
        self.name_edit.clear()
        self.formula_edit.clear()
        self.constant_edit.clear()

    def clear_formula_field(self):
        self.formula_edit.clear()

    def return_to_administration(self):
        self.hide()
        parent = self.parent()
        if parent:
            parent.show()
