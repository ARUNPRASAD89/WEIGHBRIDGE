from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QHBoxLayout, QVBoxLayout, QDialog
)

class MaterialMaster(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Material")
        self.setFixedSize(320, 140)

        layout = QVBoxLayout(self)

        # Material Code
        code_layout = QHBoxLayout()
        code_layout.addWidget(QLabel("Material Code:"))
        code_edit = QLineEdit()
        code_edit.setStyleSheet("background: black; color: white;")
        code_layout.addWidget(code_edit)
        code_layout.addWidget(QPushButton("..."))
        layout.addLayout(code_layout)

        # Material Name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Materialname"))
        name_edit = QLineEdit()
        name_edit.setStyleSheet("background: black; color: white;")
        name_layout.addWidget(name_edit)
        layout.addLayout(name_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(QPushButton("Add"))
        btn_layout.addWidget(QPushButton("Edit"))
        self.exit_btn = QPushButton("Exit")
        btn_layout.addWidget(self.exit_btn)
        layout.addLayout(btn_layout)

        self.exit_btn.clicked.connect(self.exit_to_config)

    def exit_to_config(self):
        self.close()
        parent = self.parent()
        if parent:
            parent.show()    
