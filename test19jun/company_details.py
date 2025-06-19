from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, QGridLayout
)
from PyQt5.QtCore import Qt

class CompanyDetails(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Company Details")
        self.setFixedSize(350, 320)

        grid = QGridLayout()
        labels = [
            "Name", "Address 1", "Address 2", "City",
            "PIN", "State", "Phone"
        ]
        self.edits = []
        for i, label in enumerate(labels):
            lbl = QLabel(label + ":")
            grid.addWidget(lbl, i, 0)
            edit = QLineEdit()
            if i in [0, 1, 3, 4, 5]:  # fields with yellow bg in image
                edit.setStyleSheet("background-color: #ffffcc;")
            grid.addWidget(edit, i, 1)
            self.edits.append(edit)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch(1)
        btn_ok = QPushButton("OK")
        btn_exit = QPushButton("Exit")
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_exit)

        main_layout = QVBoxLayout(self)
        main_layout.addLayout(grid)
        main_layout.addStretch(1)
        main_layout.addLayout(btn_layout)