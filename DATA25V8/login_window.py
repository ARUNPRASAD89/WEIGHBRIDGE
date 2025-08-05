from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, 
    QHBoxLayout, QFormLayout
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
from db_utils import fetch_one

class LoginWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Weighbridge Login")
        self.setMinimumSize(350, 250)
        self.username = ""

        # --- COLOR PALETTE (inspired by MainMenu) ---
        self.primary_color = "#3498db"
        self.accent_color = "#f39c12"
        self.bg_color = "#ecf0f1"
        self.text_color = "#2c3e50"

        # --- APPLY STYLESHEET ---
        self.setStyleSheet(f"""
            QDialog {{ background-color: {self.bg_color}; }}
            QLabel {{
                color: {self.text_color};
                font-family: Arial;
                font-size: 10pt;
            }}
            QLabel#title_label {{
                color: {self.primary_color};
                font-size: 16pt;
                font-weight: bold;
            }}
            QLineEdit {{
                padding: 8px;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                font-size: 10pt;
            }}
            QPushButton {{
                background-color: {self.primary_color};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px;
                font-size: 10pt;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {self.accent_color}; }}
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        main_layout.setAlignment(Qt.AlignCenter)

        # --- HEADER ---
        title_label = QLabel("User Login", objectName="title_label")
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)

        # --- FORM ---
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        self.user_input = QLineEdit()
        self.pass_input = QLineEdit()
        self.pass_input.setEchoMode(QLineEdit.Password)
        form_layout.addRow("Username:", self.user_input)
        form_layout.addRow("Password:", self.pass_input)
        main_layout.addLayout(form_layout)

        # --- BUTTONS ---
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        self.login_btn = QPushButton("Login")
        self.cancel_btn = QPushButton("Cancel")
        btn_layout.addWidget(self.login_btn)
        btn_layout.addWidget(self.cancel_btn)
        main_layout.addLayout(btn_layout)

        self.login_btn.clicked.connect(self.handle_login)
        self.cancel_btn.clicked.connect(self.reject)

    def handle_login(self):
        username = self.user_input.text().strip()
        password = self.pass_input.text()
        if not username or not password:
            QMessageBox.warning(self, "Input Error", "Username and password cannot be empty.")
            return

        result = fetch_one(
            "SELECT * FROM usermanagement WHERE username = %s AND password = %s",
            (username, password)
        )
        if result:
            self.username = username
            self.accept()
        else:
            QMessageBox.warning(self, "Login Failed", "Invalid credentials. Please try again.")

    def get_username(self):
        return self.username
