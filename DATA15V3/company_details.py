from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, QGridLayout, QDialog
)
from PyQt5.QtCore import Qt

class CompanyDetails(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        label = QLabel("Company Details Window")
        layout.addWidget(label)
        self.exit_btn = QPushButton("Exit")
        layout.addWidget(self.exit_btn)
        self.exit_btn.clicked.connect(self.return_to_administration)

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
        self.ok_btn = QPushButton("OK")
        self.exit_btn = QPushButton("Exit")
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.exit_btn)

        main_layout = QVBoxLayout(self)
        main_layout.addLayout(grid)
        main_layout.addStretch(1)
        main_layout.addLayout(btn_layout)

        # Connect Exit to return to parent window
        self.exit_btn.clicked.connect(self.return_to_administration)

    def return_to_administration(self):
        self.hide()
        parent = self.parent()
        if parent:
            parent.show()
