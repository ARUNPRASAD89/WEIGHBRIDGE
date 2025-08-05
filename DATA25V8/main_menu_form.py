from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSpacerItem, 
    QSizePolicy, QDialog, QMessageBox, QFrame, QGridLayout
)
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtCore import Qt, QSize
import traceback

from base_transaction_window import BaseTransactionWindow
from report_window_form import ReportWindowForm
from administration_window import AdministrationWindow
from configuration_window import ConfigurationWindow
from help_window import HelpWindow
from login_window import LoginWindow
from db_utils import get_user_permissions

class MainMenuForm(QDialog):
    def __init__(self, permissions=None, parent=None):
        super().__init__(parent)
        self.permissions = permissions or {}
        self.setWindowTitle("WeighBRIDGEMANUAL - Main Menu")
        self.setMinimumSize(600, 500)

        # --- COLOR PALETTE (inspired by AdministrationWindow) ---
        self.primary_color = "#3498db"   # Blue
        self.accent_color = "#f39c12"    # Orange
        self.bg_color = "#ecf0f1"       # Light Gray
        self.text_color = "#2c3e50"      # Dark Blue-Gray
        self.light_border_color = "#bdc3c7"

        # --- APPLY STYLESHEET ---
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {self.bg_color};
            }}
            QLabel {{
                color: {self.text_color};
                font-family: Arial;
            }}
            QPushButton {{
                background-color: {self.primary_color};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px;
                font-family: Arial;
                font-size: 11pt;
                font-weight: bold;
                text-align: center;
            }}
            QPushButton:hover {{
                background-color: {self.accent_color};
            }}
            QPushButton:pressed {{
                background-color: #d35400; /* Darker Orange */
            }}
            QPushButton:disabled {{
                background-color: #95a5a6;
                color: #bdc3c7;
            }}
            QFrame#banner {{
                background-color: white;
                border-bottom: 2px solid {self.light_border_color};
            }}
            QFrame#grid_frame {{
                border: none;
            }}
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(20)

        # --- BANNER ---
        banner = QFrame(objectName="banner")
        banner_layout = QVBoxLayout(banner)
        banner_label = QLabel(
            "<div style='padding:10px'><img src='truck_image.png' height='80'/><br>"
            "<span style='font-size:14pt; font-weight:bold; color:{self.primary_color};'>Engineered to take Loads off your mind</span></div>"
        )
        banner_label.setAlignment(Qt.AlignCenter)
        banner_layout.addWidget(banner_label)
        main_layout.addWidget(banner)

        # --- BUTTONS GRID ---
        grid_frame = QFrame(objectName="grid_frame")
        grid_layout = QGridLayout(grid_frame)
        grid_layout.setSpacing(15)
        
        self.buttons = {
            "Transactions": (QPushButton("Transactions"), self.open_ticket_window, True),
            "Reports": (QPushButton("Reports"), self.open_report_window, True),
            "Administration": (QPushButton("Administration"), self.open_administration_window, self.permissions.get('adminuser')),
            "Configuration": (QPushButton("Configuration"), self.open_configuration_window, self.permissions.get('adminuser')),
            "Help": (QPushButton("Help"), self.open_help_window, True),
            "Exit": (QPushButton("Exit"), self.close, True)
        }

        for idx, (text, (button, slot, enabled)) in enumerate(self.buttons.items()):
            button.setText(text)
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            button.setMinimumHeight(60)
            button.clicked.connect(slot)
            button.setEnabled(enabled)
            row, col = divmod(idx, 2)
            grid_layout.addWidget(button, row, col)

        main_layout.addWidget(grid_frame)
        main_layout.addStretch()

        # --- FOOTER ---
        footer_layout = QHBoxLayout()
        user_label = QLabel(f"Logged in as: <b>{self.permissions.get('username', 'ADMIN')}</b>")
        user_label.setFont(QFont("Arial", 10))
        user_label.setStyleSheet(f"color: {self.text_color}; padding: 5px;")
        footer_layout.addWidget(user_label, alignment=Qt.AlignRight)
        main_layout.addLayout(footer_layout)

    def _open_child_window(self, window_class, **kwargs):
        """Helper to hide current and show child window, passing permissions if needed."""
        try:
            self.hide()
            self.child_window = window_class(parent=self, **kwargs)
            self.child_window.show()
        except Exception:
            traceback.print_exc()
            QMessageBox.critical(self, "Error", "Could not open the window.")
            self.show() # Show main menu again on error

    def open_ticket_window(self):
        self._open_child_window(BaseTransactionWindow)

    def open_report_window(self):
        self._open_child_window(ReportWindowForm)

    def open_administration_window(self):
        self._open_child_window(AdministrationWindow)

    def open_configuration_window(self):
        self._open_child_window(ConfigurationWindow, permissions=self.permissions)

    def open_help_window(self):
        self._open_child_window(HelpWindow)

    def closeEvent(self, event):
        """Show the parent window when this one is closed."""
        parent = self.parent()
        if parent:
            parent.show()
        super().closeEvent(event)
