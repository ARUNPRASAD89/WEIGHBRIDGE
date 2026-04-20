from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSpacerItem, 
    QSizePolicy, QDialog, QMessageBox, QFrame, QGridLayout
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
import traceback

# Assuming these files exist in your project
from administration_window import AdministrationWindow
from configuration_window import ConfigurationWindow
from report_window_form import ReportWindowForm
from base_transaction_window import BaseTransactionWindow
from help_window import HelpWindow

class MainMenuForm(QDialog):
    # MODIFIED: Added `transaction_window=None` to accept the new argument
    def __init__(self, permissions=None, parent=None, transaction_window=None):
        super().__init__(parent)
        self.permissions = permissions or {}
        # MODIFIED: Store the reference to the transaction window
        self.transaction_window = transaction_window
        
        self.setWindowTitle("WeighBRIDGE - Main Menu")
        self.setMinimumSize(600, 450)

        self.primary_color = "#3498db"
        self.accent_color = "#f39c12"
        self.bg_color = "#ecf0f1"
        self.text_color = "#2c3e50"
        self.light_border_color = "#bdc3c7"

        self.setStyleSheet(f"""
            QDialog {{ background-color: {self.bg_color}; }}
            QLabel {{ color: {self.text_color}; font-family: Arial; }}
            QPushButton {{
                background-color: {self.primary_color}; color: white; border: none;
                border-radius: 8px; padding: 12px; font-family: Arial;
                font-size: 11pt; font-weight: bold; text-align: center;
            }}
            QPushButton:hover {{ background-color: {self.accent_color}; }}
            QPushButton:disabled {{ background-color: #95a5a6; color: #bdc3c7; }}
            QFrame#grid_frame {{ border: none; }}
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        title_label = QLabel("Main Menu")
        title_label.setFont(QFont("Arial", 18, QFont.Bold))
        title_label.setStyleSheet(f"color: {self.primary_color};")
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)

        grid_frame = QFrame(objectName="grid_frame")
        grid_layout = QGridLayout(grid_frame)
        grid_layout.setSpacing(15)
        
        is_admin_user = self.permissions.get('is_admin', False)

        # MODIFIED: Changed the "Exit" button to "Return" and connected it to a new function
        self.buttons = {
            "Transactions": (QPushButton("Transactions"), self.open_ticket_window, True),
            "Reports": (QPushButton("Reports"), self.open_report_window, True),
            "Administration": (QPushButton("Administration"), self.open_administration_window, is_admin_user),
            "Configuration": (QPushButton("Configuration"), self.open_configuration_window, is_admin_user),
            "Help": (QPushButton("Help"), self.open_help_window, True),
            "Return": (QPushButton("Return to Transactions"), self.return_to_transactions, True)
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

        footer_layout = QHBoxLayout()
        user_label = QLabel(f"Logged in as: <b>{self.permissions.get('username', 'N/A')}</b>")
        footer_layout.addWidget(user_label, alignment=Qt.AlignRight)
        main_layout.addLayout(footer_layout)

    # NEW: Function to handle returning to the transaction screen
    def return_to_transactions(self):
        """Closes this menu and shows the transaction window again."""
        if self.transaction_window:
            self.transaction_window.show()
        self.close()

    def _open_child_window(self, window_class, **kwargs):
        try:
            self.hide()
            # Pass the parent reference correctly
            self.child_window = window_class(parent=self, **kwargs)
            self.child_window.show()
        except Exception:
            traceback.print_exc()
            QMessageBox.critical(self, "Error", "Could not open the window.")
            self.show()

    def open_ticket_window(self): self._open_child_window(BaseTransactionWindow)
    def open_report_window(self): self._open_child_window(ReportWindowForm)
    def open_administration_window(self): self._open_child_window(AdministrationWindow)
    def open_configuration_window(self): self._open_child_window(ConfigurationWindow, permissions=self.permissions)
    def open_help_window(self): self._open_child_window(HelpWindow)

    def closeEvent(self, event):
        # If this window is closed by any means (like the 'X' button), 
        # ensure the transaction window is shown again.
        if self.transaction_window and not self.transaction_window.isVisible():
             self.transaction_window.show()
        
        # This handles showing the parent if one was set, but our new logic is safer
        parent = self.parent()
        if parent and not self.transaction_window: 
            parent.show()
            
        super().closeEvent(event)
