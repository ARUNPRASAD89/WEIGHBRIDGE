from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QHBoxLayout, QVBoxLayout,
    QListWidget, QGroupBox, QTimeEdit, QDialog, QComboBox, QMessageBox
)
from db_utils import execute_query, fetch_one, fetch_all

class ShiftMaster(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Shifts")
        self.setFixedSize(340, 370)
        layout = QVBoxLayout(self)

        # Shift List (Dropdown)
        list_label = QLabel("Shift List")
        layout.addWidget(list_label)
        self.shift_combo = QComboBox()
        self.shift_combo.setEditable(False)
        self.shift_combo.addItems(self.get_shift_names())
        self.shift_combo.currentTextChanged.connect(self.on_shift_changed)
        layout.addWidget(self.shift_combo)

        # Shift Name
        shift_name_layout = QHBoxLayout()
        shift_name_layout.addWidget(QLabel("Shift Name"))
        self.shift_name_edit = QLineEdit()
        shift_name_layout.addWidget(self.shift_name_edit)
        layout.addLayout(shift_name_layout)

        # Shift From
        shift_from_layout = QHBoxLayout()
        shift_from_layout.addWidget(QLabel("Shift From"))
        self.shift_from_edit = QTimeEdit()
        shift_from_layout.addWidget(self.shift_from_edit)
        layout.addLayout(shift_from_layout)

        # Shift To
        shift_to_layout = QHBoxLayout()
        shift_to_layout.addWidget(QLabel("Shift To"))
        self.shift_to_edit = QTimeEdit()
        shift_to_layout.addWidget(self.shift_to_edit)
        layout.addLayout(shift_to_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("Add")
        self.edit_btn = QPushButton("Edit")
        self.delete_btn = QPushButton("Delete")
        self.exit_btn = QPushButton("Exit")
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addWidget(self.exit_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        self.exit_btn.clicked.connect(self.exit_to_config)
        self.add_btn.clicked.connect(self.add_shift)
        self.edit_btn.clicked.connect(self.edit_shift)
        self.delete_btn.clicked.connect(self.delete_shift)

        # Load details if exists
        if self.shift_combo.count():
            self.on_shift_changed(self.shift_combo.currentText())

    def get_shift_names(self):
        rows = fetch_all("SELECT shiftname FROM shiftmaster ORDER BY shiftname")
        return [r["shiftname"] for r in rows]

    def on_shift_changed(self, shiftname):
        row = fetch_one("SELECT * FROM shiftmaster WHERE shiftname = %s", (shiftname,))
        if row:
            self.shift_name_edit.setText(row["shiftname"])
            if row["fromshift"]:
                self.shift_from_edit.setTime(row["fromshift"])
            if row["toshift"]:
                self.shift_to_edit.setTime(row["toshift"])
        else:
            self.shift_name_edit.clear()
            self.shift_from_edit.clear()
            self.shift_to_edit.clear()

    def add_shift(self):
        shiftname = self.shift_name_edit.text().strip()
        fromshift = self.shift_from_edit.time().toString("HH:mm:ss")
        toshift = self.shift_to_edit.time().toString("HH:mm:ss")
        if not shiftname:
            QMessageBox.warning(self, "Error", "Shift Name is required!")
            return
        try:
            query = """
                INSERT INTO shiftmaster (shiftname, fromshift, toshift)
                VALUES (%s, %s, %s)
                ON CONFLICT(shiftname) DO NOTHING
            """
            execute_query(query, (shiftname, fromshift, toshift))
            QMessageBox.information(self, "Success", f"Shift '{shiftname}' added.")
            self.shift_combo.clear()
            self.shift_combo.addItems(self.get_shift_names())
            self.on_shift_changed(shiftname)
        except Exception as e:
            QMessageBox.critical(self, "DB Error", f"Could not add shift:\n{e}")

    def edit_shift(self):
        shiftname = self.shift_name_edit.text().strip()
        fromshift = self.shift_from_edit.time().toString("HH:mm:ss")
        toshift = self.shift_to_edit.time().toString("HH:mm:ss")
        if not shiftname:
            QMessageBox.warning(self, "Error", "Shift Name required to edit!")
            return
        try:
            query = """
                UPDATE shiftmaster
                SET fromshift=%s, toshift=%s
                WHERE shiftname=%s
            """
            execute_query(query, (fromshift, toshift, shiftname))
            QMessageBox.information(self, "Success", f"Shift '{shiftname}' updated.")
            self.shift_combo.clear()
            self.shift_combo.addItems(self.get_shift_names())
            self.on_shift_changed(shiftname)
        except Exception as e:
            QMessageBox.critical(self, "DB Error", f"Could not update shift:\n{e}")

    def delete_shift(self):
        shiftname = self.shift_name_edit.text().strip()
        if not shiftname:
            QMessageBox.warning(self, "Error", "Shift Name required to delete!")
            return
        try:
            query = "DELETE FROM shiftmaster WHERE shiftname=%s"
            execute_query(query, (shiftname,))
            QMessageBox.information(self, "Deleted", f"Shift deleted.")
            self.shift_combo.clear()
            self.shift_combo.addItems(self.get_shift_names())
            self.shift_name_edit.clear()
            self.shift_from_edit.clear()
            self.shift_to_edit.clear()
        except Exception as e:
            QMessageBox.critical(self, "DB Error", f"Could not delete shift:\n{e}")

    def exit_to_config(self):
        self.close()
        parent = self.parent()
        if parent:
            parent.show()
