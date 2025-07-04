from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QComboBox, QPushButton, QHBoxLayout, QVBoxLayout, QGridLayout
)
from PyQt5.QtCore import Qt

class FormulaEditor(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Formula Editor")
        self.setFixedSize(500, 160)

        main_layout = QVBoxLayout(self)
        grid = QGridLayout()
        grid.addWidget(QLabel("Name:"), 0, 0)
        grid.addWidget(QLineEdit(), 0, 1)
        grid.addWidget(QPushButton("..."), 0, 2)
        grid.addWidget(QLabel("Field Name:"), 0, 3)
        grid.addWidget(QComboBox(), 0, 4)
        grid.addWidget(QPushButton("Insert"), 0, 5)

        grid.addWidget(QLabel("Operator:"), 1, 0)
        grid.addWidget(QComboBox(), 1, 1)
        grid.addWidget(QPushButton("Insert"), 1, 2)
        grid.addWidget(QLabel("Constant:"), 1, 3)
        grid.addWidget(QLineEdit(), 1, 4)
        grid.addWidget(QPushButton("Insert"), 1, 5)

        grid.addWidget(QLabel("Formula:"), 2, 0)
        grid.addWidget(QLineEdit(), 2, 1, 1, 4)
        grid.addWidget(QPushButton("X"), 2, 5)
        main_layout.addLayout(grid)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        for txt in ["Save", "Clear", "Delete", "Exit"]:
            btn_layout.addWidget(QPushButton(txt))
        main_layout.addLayout(btn_layout)