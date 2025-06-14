from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QPushButton, QCheckBox, QSizePolicy
)
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtCore import Qt, QSize

class AdministrationWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Administration")
        self.setFixedSize(340, 380)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        grid = QGridLayout()
        grid.setSpacing(12)
        font = QFont("Arial", 10, QFont.Bold)

        button_info = [
            ("ticket_data_entry.png", "Ticket Data\nEntry Designer"),
            ("ticket_print.png", "Ticket Print\nDesigner"),
            ("database.png", "Database\nDesigner"),
            ("formula.png", "Formula Editor"),
            ("user_manager.png", "User Manager"),
            ("company.png", "Company\nDetails"),
            ("help.png", "Help"),
            ("exit.png", "Exit"),
        ]

        buttons = []
        for idx, (icon, label) in enumerate(button_info):
            btn = QPushButton()
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            if idx < 6:
                btn.setFixedSize(80, 60)
            else:
                btn.setFixedSize(80, 48)
            btn.setText(label)
            btn.setFont(font)
            btn.setIcon(QIcon())  # Add QIcon(icon) if you have icon files
            btn.setIconSize(QSize(32, 32))  # <-- FIXED
            btn.setStyleSheet("text-align:center;")
            buttons.append(btn)
            row, col = divmod(idx, 3)
            grid.addWidget(btn, row, col)

        main_layout.addLayout(grid)

        self.duplicate_pass_cb = QCheckBox("Password For Duplicate Ticket")
        self.duplicate_pass_cb.setChecked(True)
        self.allow_zero_cb = QCheckBox("Allow Zero Weight Ticket")
        main_layout.addWidget(self.duplicate_pass_cb)
        main_layout.addWidget(self.allow_zero_cb)