from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QCheckBox, QListWidget,
    QHBoxLayout, QVBoxLayout, QGridLayout, QGroupBox, QDialog
)
from PyQt5.QtCore import Qt

class UserManager(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("User Manager")
        
        label = QLabel("User Manager Window")
        layout.addWidget(label)
        self.exit_btn = QPushButton("Exit")
        layout.addWidget(self.exit_btn)
        self.exit_btn.clicked.connect(self.return_to_administration)

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
        self.new_btn = QPushButton("New")
        self.edit_btn = QPushButton("Edit")
        self.delete_btn = QPushButton("Delete")
        self.exit_btn = QPushButton("Exit")
        for btn in [self.new_btn, self.edit_btn, self.delete_btn, self.exit_btn]:
            btn_layout.addWidget(btn)
        main_layout.addLayout(btn_layout)

        # Connect Exit to return to parent window
        self.exit_btn.clicked.connect(self.return_to_administration)

    def return_to_administration(self):
        self.hide()
        parent = self.parent()
        if parent:
            parent.show()
