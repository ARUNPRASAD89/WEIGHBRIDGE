from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QHBoxLayout, QVBoxLayout, QDialog, QMessageBox
)
from db_utils import execute_query, fetch_one, fetch_all

class SupplierMaster(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Supplier")
        self.setFixedSize(400, 140)

        layout = QVBoxLayout(self)

        # Supplier Code (ID) field (QLineEdit, like material code)
        code_layout = QHBoxLayout()
        code_layout.addWidget(QLabel("Supplier Code:"))
        self.code_edit = QLineEdit()
        self.code_edit.setStyleSheet("background: black; color: white;")
        self.code_edit.setReadOnly(True)
        code_layout.addWidget(self.code_edit)
        self.pick_btn = QPushButton("...")
        self.pick_btn.setToolTip("Pick existing supplier")
        code_layout.addWidget(self.pick_btn)
        layout.addLayout(code_layout)

        # Supplier Name field
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Supplier Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setStyleSheet("background: black; color: white;")
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)

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

        # Connections
        self.exit_btn.clicked.connect(self.exit_to_config)
        self.add_btn.clicked.connect(self.add_supplier)
        self.edit_btn.clicked.connect(self.edit_supplier)
        self.delete_btn.clicked.connect(self.delete_supplier)
        self.pick_btn.clicked.connect(self.pick_supplier_dialog)

    def exit_to_config(self):
        self.close()
        parent = self.parent()
        if parent:
            parent.show()

    def add_supplier(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "Supplier Name is required!")
            return
        # Insert, let DB generate code
        try:
            query = """
                INSERT INTO suppliers (suppliername)
                VALUES (%s)
                ON CONFLICT(suppliername) DO NOTHING
                RETURNING suppliercode
            """
            result = fetch_one(query, (name,))
            if result and result.get("suppliercode"):
                self.code_edit.setText(str(result["suppliercode"]))
                QMessageBox.information(self, "Success", f"Supplier '{name}' added.")
                self.clear_fields()
            else:
                # Already exists, get code
                existing = fetch_one("SELECT suppliercode FROM suppliers WHERE suppliername=%s", (name,))
                if existing:
                    self.code_edit.setText(str(existing["suppliercode"]))
                QMessageBox.information(self, "Exists", f"Supplier '{name}' already exists.")
        except Exception as e:
            QMessageBox.critical(self, "DB Error", f"Could not add supplier:\n{e}")

    def edit_supplier(self):
        code = self.code_edit.text().strip()
        name = self.name_edit.text().strip()
        if not code or not name:
            QMessageBox.warning(self, "Error", "Supplier Code and Name required to edit!")
            return
        try:
            query = """
                UPDATE suppliers
                SET suppliername=%s
                WHERE suppliercode=%s
            """
            execute_query(query, (name, int(code)))
            QMessageBox.information(self, "Success", f"Supplier '{name}' updated.")
            self.clear_fields()
        except Exception as e:
            QMessageBox.critical(self, "DB Error", f"Could not update supplier:\n{e}")

    def delete_supplier(self):
        code = self.code_edit.text().strip()
        if not code:
            QMessageBox.warning(self, "Error", "Supplier Code required to delete!")
            return
        try:
            query = "DELETE FROM suppliers WHERE suppliercode=%s"
            execute_query(query, (int(code),))
            QMessageBox.information(self, "Deleted", f"Supplier deleted.")
            self.clear_fields()
        except Exception as e:
            QMessageBox.critical(self, "DB Error", f"Could not delete supplier:\n{e}")

    def pick_supplier_dialog(self):
        # Simple dialog to pick supplier by name or code
        suppliers = fetch_all("SELECT suppliercode, suppliername FROM suppliers ORDER BY suppliername")
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QListWidget, QHBoxLayout
        dlg = QDialog(self)
        dlg.setWindowTitle("Pick Supplier")
        dlg.setFixedSize(350, 350)
        vlayout = QVBoxLayout(dlg)
        listw = QListWidget()
        for s in suppliers:
            listw.addItem(f"{s['suppliercode']}: {s['suppliername']}")
        vlayout.addWidget(listw)
        hbox = QHBoxLayout()
        ok_btn = QPushButton("OK")
        cancel_btn = QPushButton("Cancel")
        hbox.addWidget(ok_btn)
        hbox.addWidget(cancel_btn)
        vlayout.addLayout(hbox)
        def pick():
            idx = listw.currentRow()
            if idx >= 0:
                s = suppliers[idx]
                self.code_edit.setText(str(s['suppliercode']))
                self.name_edit.setText(s['suppliername'])
            dlg.accept()
        ok_btn.clicked.connect(pick)
        cancel_btn.clicked.connect(dlg.reject)
        dlg.exec_()

    def clear_fields(self):
        self.code_edit.clear()
        self.name_edit.clear()
