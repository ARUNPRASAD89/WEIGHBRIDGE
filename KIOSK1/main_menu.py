from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QDialog, QLabel,
    QHBoxLayout, QSpacerItem, QSizePolicy
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

from transaction_window import TransactionWindow
from main_menu_form import MainMenuForm

class MainMenu(QDialog):
    def __init__(self, permissions=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Mode")
        self.setMinimumSize(400, 300)

        self.permissions = permissions or {}
        # Store username from permissions, which should be set after login
        self.username = self.permissions.get('username', 'N/A')

        # --- COLOR PALETTE (inspired by AdministrationWindow) ---
        self.primary_color = "#3498db"   # Blue
        self.accent_color = "#f39c12"    # Orange
        self.bg_color = "#ecf0f1"       # Light Gray
        self.text_color = "#2c3e50"      # Dark Blue-Gray

        # --- APPLY STYLESHEET ---
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {self.bg_color};
            }}
            QLabel#title_label {{
                color: {self.primary_color};
                font-family: Arial;
                font-size: 18pt;
                font-weight: bold;
            }}
            QPushButton {{
                background-color: {self.primary_color};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 15px;
                font-family: Arial;
                font-size: 12pt;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.accent_color};
            }}
            QPushButton:pressed {{
                background-color: #d35400; /* Darker Orange */
            }}
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(25)
        main_layout.setAlignment(Qt.AlignCenter)

        # --- HEADER ---
        title_label = QLabel("Select Operating Mode", objectName="title_label")
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)

        # --- BUTTONS ---
        button_layout = QVBoxLayout()
        button_layout.setSpacing(15)

        self.touch_btn = QPushButton("Touch Mode")
        self.manual_btn = QPushButton("Manual Mode")

        # Set a consistent size for the buttons
        self.touch_btn.setMinimumSize(250, 60)
        self.manual_btn.setMinimumSize(250, 60)

        self.touch_btn.clicked.connect(self.open_touch_mode)
        self.manual_btn.clicked.connect(self.open_manual_mode)

        button_layout.addWidget(self.touch_btn)
        button_layout.addWidget(self.manual_btn)
        
        # This layout centers the button column horizontally
        h_layout = QHBoxLayout()
        h_layout.addStretch()
        h_layout.addLayout(button_layout)
        h_layout.addStretch()
        
        main_layout.addLayout(h_layout)
        main_layout.addStretch()

        self.tx_win = None
        self.manual_form = None

    def open_touch_mode(self):
        self.hide()
        # FIX: Removed the 'parent' argument which was causing the TypeError
        self.tx_win = TransactionWindow()
        self.tx_win.show()
        # Restore the connection to show this menu again when the transaction window is closed
        self.tx_win.destroyed.connect(self.show)

    def open_manual_mode(self):
        self.hide()
        self.manual_form = MainMenuForm(permissions=self.permissions, parent=self)
        self.manual_form.show()

    def closeEvent(self, event):
        """Ensure parent (login window) is shown when this window is closed."""
        parent = self.parent()
        if parent:
            parent.show()
        super().closeEvent(event)
