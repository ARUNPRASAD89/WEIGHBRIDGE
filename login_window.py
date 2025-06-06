from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
)
from main_menu import MainMenu

class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Weighbridge Login")
        self.setGeometry(100, 100, 300, 200)

        layout = QVBoxLayout()
        self.user_label = QLabel("Username:")
        self.user_input = QLineEdit()
        self.pass_label = QLabel("Password:")
        self.pass_input = QLineEdit()
        self.pass_input.setEchoMode(QLineEdit.Password)

        self.login_btn = QPushButton("Login")
        self.login_btn.clicked.connect(self.handle_login)

        layout.addWidget(self.user_label)
        layout.addWidget(self.user_input)
        layout.addWidget(self.pass_label)
        layout.addWidget(self.pass_input)
        layout.addWidget(self.login_btn)

        self.setLayout(layout)

    def handle_login(self):
        # Replace with real authentication and DB connection
        username = self.user_input.text()
        password = self.pass_input.text()
        if username == "admin" and password == "admin":
            self.hide()
            self.menu = MainMenu()
            self.menu.show()
        else:
            QMessageBox.warning(self, "Login Failed", "Invalid credentials")