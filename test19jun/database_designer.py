from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QComboBox, QListWidget, QPushButton,
    QVBoxLayout, QHBoxLayout, QGridLayout
)
from PyQt5.QtCore import Qt

class DatabaseDesigner(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Database Designer")
        self.setFixedSize(270, 330)

        layout = QVBoxLayout(self)
        top_grid = QGridLayout()
        top_grid.addWidget(QLabel("Table Name:"), 0, 0)
        top_grid.addWidget(QComboBox(), 0, 1)
        layout.addLayout(top_grid)

        layout.addWidget(QLabel("Fields:"))
        layout.addWidget(QListWidget())

        field_grid = QGridLayout()
        field_grid.addWidget(QLabel("Field Name:"), 0, 0)
        field_grid.addWidget(QLineEdit(), 0, 1)
        field_grid.addWidget(QLabel("Field Type:"), 1, 0)
        field_grid.addWidget(QComboBox(), 1, 1)
        field_grid.addWidget(QLabel("Field Size:"), 2, 0)
        field_grid.addWidget(QLineEdit(), 2, 1)
        field_grid.addWidget(QLabel("Caption:"), 3, 0)
        field_grid.addWidget(QLineEdit(), 3, 1)
        layout.addLayout(field_grid)

        btn_layout = QHBoxLayout()
        btn_insert = QPushButton("Insert")
        btn_remove = QPushButton("Remove")
        btn_formula = QPushButton("Formula")
        btn_formula.setEnabled(False)
        btn_exit = QPushButton("Exit")
        btn_layout.addWidget(btn_insert)
        btn_layout.addWidget(btn_remove)
        btn_layout.addWidget(btn_formula)
        btn_layout.addWidget(btn_exit)
        layout.addLayout(btn_layout)