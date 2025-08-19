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
from rate_chart_manager_window import RateChartManagerWindow
from backup_window import BackupWindow # <--- ADD THIS IMPORT

class AdministrationWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Administration")
        self.setMinimumSize(420, 500) # Increased height for new row

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
                border-radius: 8px; padding: 10px; font-family: Arial;
                font-size: 10pt; font-weight: bold; text-align: center;
            }}
            QPushButton:hover {{ background-color: {self.accent_color}; }}
            QPushButton:pressed {{ background-color: #d35400; }}
            QCheckBox {{ color: {self.text_color}; font-family: Arial; font-size: 10pt; spacing: 8px; }}
            QFrame {{ border: 1px solid {self.light_border_color}; border-radius: 8px; }}
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        header_layout = QHBoxLayout()
        self.lbl_title = QLabel("Administration Panel")
        self.lbl_title.setFont(QFont("Arial", 16, QFont.Bold))
        self.lbl_title.setStyleSheet(f"color: {self.primary_color};")
        header_layout.addWidget(self.lbl_title, alignment=Qt.AlignCenter)
        main_layout.addLayout(header_layout)

        grid_frame = QFrame()
        grid_layout = QGridLayout(grid_frame)
        grid_layout.setSpacing(15)
        grid_layout.setContentsMargins(15, 15, 15, 15)
        
        font = QFont("Arial", 10, QFont.Bold)

        # --- MODIFICATION: ADD THE NEW BUTTON INFO HERE ---
        button_info = [
            ("ticket_data_entry.png", "Ticket Data\nEntry Designer", self.open_ticket_data_entry_designer),
            ("ticket_print.png", "Ticket Print\nDesigner", self.open_ticket_entry_designer),
            ("database.png", "Database\nDesigner", self.open_database_designer),
            ("formula.png", "Formula Editor", self.open_formula_editor),
            ("user_manager.png", "User Manager", self.open_user_manager),
            ("company.png", "Company\nDetails", self.open_company_details),
            ("rate_chart.png", "Rate Chart\nManager", self.open_rate_chart_manager),
            ("backup.png", "Database\nBackup", self.open_backup_window), # <--- ADD THIS LINE
            ("exit.png", "Exit", self.close),
        ]

        # Dynamically create and place buttons, ensuring the last one is centered if odd
        num_buttons = len(button_info)
        for idx, (icon, label, slot) in enumerate(button_info):
            btn = QPushButton(label)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            btn.setMinimumHeight(70)
            btn.setFont(font)
            if slot: btn.clicked.connect(slot)
            
            row, col = divmod(idx, 2)
            if idx == num_buttons - 1 and num_buttons % 2 != 0:
                grid_layout.addWidget(btn, row, 0, 1, 2) # Span across 2 columns
            else:
                grid_layout.addWidget(btn, row, col)

        main_layout.addWidget(grid_frame)
        main_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

    def _open_child_window(self, window_class):
        self.hide()
        self.child_window = window_class(parent=self)
        self.child_window.show()

    def open_ticket_data_entry_designer(self): self._open_child_window(TicketDataEntryDesignerWindow)
    def open_ticket_entry_designer(self): self._open_child_window(TicketEntryDesignerWindow)
    def open_database_designer(self): self._open_child_window(DatabaseDesigner)
    def open_formula_editor(self): self._open_child_window(FormulaEditor)
    def open_user_manager(self): self._open_child_window(UserManager)
    def open_company_details(self): self._open_child_window(CompanyDetails)
    def open_rate_chart_manager(self): self._open_child_window(RateChartManagerWindow)

    # --- MODIFICATION: ADD THE NEW METHOD HERE ---
    def open_backup_window(self):
        self._open_child_window(BackupWindow)

    def close(self):
        parent = self.parent()
        if parent: parent.show()
        super().close()
