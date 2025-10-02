from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QHBoxLayout, QVBoxLayout, QDialog, QMessageBox
)
from db_utils import execute_query, fetch_one, fetch_all

class MaterialMaster(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Material")
        self.setFixedSize(420, 180)

        layout = QVBoxLayout(self)

        # Material Code
        code_layout = QHBoxLayout()
        code_layout.addWidget(QLabel("Material Code:"))
        self.code_edit = QLineEdit()
        self.code_edit.setStyleSheet("background: black; color: white;")
        code_layout.addWidget(self.code_edit)
        self.pick_btn = QPushButton("...")
        self.pick_btn.setToolTip("Pick existing material")
        code_layout.addWidget(self.pick_btn)
        layout.addLayout(code_layout)

        # Material Name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Material Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setStyleSheet("background: black; color: white;")
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)

        # Material Description
        desc_layout = QHBoxLayout()
        desc_layout.addWidget(QLabel("Description:"))
        self.desc_edit = QLineEdit()
        self.desc_edit.setStyleSheet("background: black; color: white;")
        desc_layout.addWidget(self.desc_edit)
        layout.addLayout(desc_layout)

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
        self.add_btn.clicked.connect(self.add_material)
        self.edit_btn.clicked.connect(self.edit_material)
        self.delete_btn.clicked.connect(self.delete_material)
        self.pick_btn.clicked.connect(self.pick_material_dialog)

    def exit_to_config(self):
        self.close()
        parent = self.parent()
        if parent:
            parent.show()

    def add_material(self):
        name = self.name_edit.text().strip()
        desc = self.desc_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "Material Name is required!")
            return
        # Insert, let DB generate code
        try:
            query = """
                INSERT INTO material (materialname, materialdescription)
                VALUES (%s, %s)
                ON CONFLICT(materialname) DO NOTHING
            """
            execute_query(query, (name, desc))
            QMessageBox.information(self, "Success", f"Material '{name}' added.")
            self.clear_fields()
        except Exception as e:
            QMessageBox.critical(self, "DB Error", f"Could not add material:\n{e}")

    def edit_material(self):
        code = self.code_edit.text().strip()
        name = self.name_edit.text().strip()
        desc = self.desc_edit.text().strip()
        if not code or not name:
            QMessageBox.warning(self, "Error", "Material Code and Name required to edit!")
            return
        try:
            query = """
                UPDATE material
                SET materialname=%s, materialdescription=%s
                WHERE materialcode=%s
            """
            execute_query(query, (name, desc, int(code)))
            QMessageBox.information(self, "Success", f"Material '{name}' updated.")
            self.clear_fields()
        except Exception as e:
            QMessageBox.critical(self, "DB Error", f"Could not update material:\n{e}")

    def delete_material(self):
        code = self.code_edit.text().strip()
        if not code:
            QMessageBox.warning(self, "Error", "Material Code required to delete!")
            return
        try:
            query = "DELETE FROM material WHERE materialcode=%s"
            execute_query(query, (int(code),))
            QMessageBox.information(self, "Deleted", f"Material deleted.")
            self.clear_fields()
        except Exception as e:
            QMessageBox.critical(self, "DB Error", f"Could not delete material:\n{e}")

    def pick_material_dialog(self):
        # Simple dialog to pick material by name or code
        materials = fetch_all("SELECT materialcode, materialname, materialdescription FROM material ORDER BY materialname")
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QListWidget, QHBoxLayout
        dlg = QDialog(self)
        dlg.setWindowTitle("Pick Material")
        dlg.setFixedSize(350, 350)
        vlayout = QVBoxLayout(dlg)
        listw = QListWidget()
        for m in materials:
            listw.addItem(f"{m['materialcode']}: {m['materialname']}")
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
                m = materials[idx]
                self.code_edit.setText(str(m['materialcode']))
                self.name_edit.setText(m['materialname'])
                self.desc_edit.setText(m.get('materialdescription', ''))
            dlg.accept()
        ok_btn.clicked.connect(pick)
        cancel_btn.clicked.connect(dlg.reject)
        dlg.exec_()

    def clear_fields(self):
        self.code_edit.clear()
        self.name_edit.clear()
        self.desc_edit.clear()
