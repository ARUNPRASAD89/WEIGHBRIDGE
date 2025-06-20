from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QHBoxLayout, QVBoxLayout
)

class MaterialMaster(QWidget):
    def __init__(self):
        super().__init__()
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
        btn_layout.addWidget(QPushButton("Exit"))
        layout.addLayout(btn_layout)