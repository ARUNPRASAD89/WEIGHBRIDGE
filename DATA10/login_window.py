from PyQt5.QtWidgets import (
    QWidget,QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QHBoxLayout
)
from main_menu import MainMenu
from db_utils import fetch_one

class LoginWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Weighbridge Login")
        self.setGeometry(100, 100, 300, 200)
        self.username = ""
        self.password = ""

        layout = QVBoxLayout()
        self.user_label = QLabel("Username:")
        self.user_input = QLineEdit()
        self.pass_label = QLabel("Password:")
        self.pass_input = QLineEdit()
        self.pass_input.setEchoMode(QLineEdit.Password)

        self.login_btn = QPushButton("Login")
        self.cancel_btn = QPushButton("Cancel")

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.login_btn)
        btn_layout.addWidget(self.cancel_btn)

        layout.addWidget(self.user_label)
        layout.addWidget(self.user_input)
        layout.addWidget(self.pass_label)
        layout.addWidget(self.pass_input)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        self.login_btn.clicked.connect(self.handle_login)
        self.cancel_btn.clicked.connect(self.reject)

    def handle_login(self):
        username = self.user_input.text()
        password = self.pass_input.text()
        # Query usermanagement table for credentials
        result = fetch_one(
            "SELECT * FROM usermanagement WHERE username = %s AND password = %s",
            (username, password)
        )
        if result:
            self.username = username
            self.password = password
            self.accept()
        else:
            QMessageBox.warning(self, "Login Failed", "Invalid credentials")

    def get_credentials(self):
        return self.username, self.password
