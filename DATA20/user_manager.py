from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QCheckBox, QListWidget,
    QHBoxLayout, QVBoxLayout, QGridLayout, QGroupBox
)
from PyQt5.QtCore import Qt

class UserManager(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("User Manager")
        self.setFixedSize(540, 250)

        main_layout = QVBoxLayout(self)

        # Top section: User Details and Existing Users
        top_layout = QHBoxLayout()
        user_details = QGroupBox("User Details")
        ud_grid = QGridLayout()
        ud_grid.addWidget(QLabel("Name:"), 0, 0)
        ud_grid.addWidget(QLineEdit(), 0, 1)
        ud_grid.addWidget(QLabel("Password:"), 1, 0)
        ud_grid.addWidget(QLineEdit(), 1, 1)
        ud_grid.addWidget(QLabel("Confirm Password:"), 2, 0)
        ud_grid.addWidget(QLineEdit(), 2, 1)
        ud_grid.addWidget(QLabel("Administrator"), 3, 0)
        ud_grid.addWidget(QCheckBox(), 3, 1)
        user_details.setLayout(ud_grid)
        top_layout.addWidget(user_details)

        existing_users = QGroupBox("Existing Users")
        vbox = QVBoxLayout()
        vbox.addWidget(QListWidget())
        existing_users.setLayout(vbox)
        top_layout.addWidget(existing_users)

        main_layout.addLayout(top_layout)

        # Authorization section
        auth_layout = QHBoxLayout()
        auth_layout.addWidget(QLabel("The user is authorized to"))
        auth_layout.addWidget(QCheckBox("Print duplicate tickets"))
        auth_layout.addWidget(QCheckBox("Delete Entities"))
        auth_layout.addWidget(QCheckBox("Configure Vehicle Master"))
        main_layout.addLayout(auth_layout)

        # Bottom buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch(1)
        for txt in ["New", "Edit", "Delete", "Exit"]:
            btn_layout.addWidget(QPushButton(txt))
        main_layout.addLayout(btn_layout)