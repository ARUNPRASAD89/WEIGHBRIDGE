from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QPushButton, QCheckBox, QSizePolicy, 
    QDialog, QLabel, QFrame, QHBoxLayout, QSpacerItem
)
from PyQt5.QtGui import QFont, QIcon, QPalette, QColor
from PyQt5.QtCore import QSize, Qt

from ticket_data_entry_designer_window import TicketDataEntryDesignerWindow
from ticket_entry_designer_window import TicketEntryDesignerWindow
from company_details import CompanyDetails
from database_designer import DatabaseDesigner
from formula_editor import FormulaEditor
from user_manager import UserManager

class AdministrationWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        print("AdministrationWindow: __init__ called")
        self.setWindowTitle("Administration")
        self.setMinimumSize(420, 450)

        # --- COLOR PALETTE (inspired by BaseTransactionWindow) ---
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
                padding: 10px;
                font-family: Arial;
                font-size: 10pt;
                font-weight: bold;
                text-align: center;
            }}
            QPushButton:hover {{
                background-color: {self.accent_color};
            }}
            QPushButton:pressed {{
                background-color: #d35400; /* Darker Orange */
            }}
            QCheckBox {{
                color: {self.text_color};
                font-family: Arial;
                font-size: 10pt;
                spacing: 8px; /* Space between checkbox and text */
            }}
            QFrame {{
                border: 1px solid {self.light_border_color};
                border-radius: 8px;
            }}
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # --- HEADER ---
        header_layout = QHBoxLayout()
        self.lbl_title = QLabel("Administration Panel")
        self.lbl_title.setFont(QFont("Arial", 16, QFont.Bold))
        self.lbl_title.setStyleSheet(f"color: {self.primary_color};")
        header_layout.addWidget(self.lbl_title, alignment=Qt.AlignCenter)
        main_layout.addLayout(header_layout)

        # --- BUTTONS GRID in a Frame ---
        grid_frame = QFrame()
        grid_layout = QGridLayout(grid_frame)
        grid_layout.setSpacing(15)
        grid_layout.setContentsMargins(15, 15, 15, 15)
        
        font = QFont("Arial", 10, QFont.Bold)

        button_info = [
            ("ticket_data_entry.png", "Ticket Data\nEntry Designer", self.open_ticket_data_entry_designer),
            ("ticket_print.png", "Ticket Print\nDesigner", self.open_ticket_entry_designer),
            ("database.png", "Database\nDesigner", self.open_database_designer),
            ("formula.png", "Formula Editor", self.open_formula_editor),
            ("user_manager.png", "User Manager", self.open_user_manager),
            ("company.png", "Company\nDetails", self.open_company_details),
            ("help.png", "Help", None),
            ("exit.png", "Exit", self.close),
        ]

        for idx, (icon, label, slot) in enumerate(button_info):
            btn = QPushButton(label)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            btn.setMinimumHeight(70) # Set a minimum height for better look
            btn.setFont(font)
            # Assuming icons are in an 'icons' subdirectory
            # btn.setIcon(QIcon(f"icons/{icon}")) 
            # btn.setIconSize(QSize(32, 32))
            if slot:
                btn.clicked.connect(slot)
            
            row, col = divmod(idx, 2) # Using 2 columns for a cleaner look
            grid_layout.addWidget(btn, row, col)

        main_layout.addWidget(grid_frame)

        # --- SETTINGS CHECKBOXES in a Frame ---
        settings_frame = QFrame()
        settings_layout = QVBoxLayout(settings_frame)
        settings_layout.setSpacing(10)
        settings_layout.setContentsMargins(15, 10, 15, 10)

        self.duplicate_pass_cb = QCheckBox("Password For Duplicate Ticket")
        self.duplicate_pass_cb.setChecked(True)
        self.allow_zero_cb = QCheckBox("Allow Zero Weight Ticket")
        
        settings_layout.addWidget(self.duplicate_pass_cb)
        settings_layout.addWidget(self.allow_zero_cb)
        
        main_layout.addWidget(settings_frame)
        
        main_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        print("AdministrationWindow: END of __init__")

    def _open_child_window(self, window_class):
        """Helper to hide current and show child window."""
        self.hide()
        # The child window will be garbage collected if we don't hold a reference
        self.child_window = window_class(parent=self)
        self.child_window.show()

    def open_ticket_data_entry_designer(self):
        self._open_child_window(TicketDataEntryDesignerWindow)

    def open_ticket_entry_designer(self):
        self._open_child_window(TicketEntryDesignerWindow)

    def open_database_designer(self):
        self._open_child_window(DatabaseDesigner)

    def open_formula_editor(self):
        self._open_child_window(FormulaEditor)

    def open_user_manager(self):
        self._open_child_window(UserManager)

    def open_company_details(self):
        self._open_child_window(CompanyDetails)

    def close(self):
        # Overriding close to ensure parent is shown if it exists
        parent = self.parent()
        if parent:
            parent.show()
        super().close()
