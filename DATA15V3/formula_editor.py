from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QComboBox, QPushButton, QHBoxLayout, QVBoxLayout, QGridLayout, QDialog
)
from PyQt5.QtCore import Qt

class FormulaEditor(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Formula Editor")
        label = QLabel("Formula Editor Window")
        layout.addWidget(label)
        self.exit_btn = QPushButton("Exit")
        layout.addWidget(self.exit_btn)
        self.exit_btn.clicked.connect(self.return_to_administration)

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
        self.save_btn = QPushButton("Save")
        self.clear_btn = QPushButton("Clear")
        self.delete_btn = QPushButton("Delete")
        self.exit_btn = QPushButton("Exit")
        for btn in [self.save_btn, self.clear_btn, self.delete_btn, self.exit_btn]:
            btn_layout.addWidget(btn)
        main_layout.addLayout(btn_layout)

        # Connect Exit to return to parent window
        self.exit_btn.clicked.connect(self.return_to_administration)

    def return_to_administration(self):
        self.hide()
        parent = self.parent()
        if parent:
            parent.show()
