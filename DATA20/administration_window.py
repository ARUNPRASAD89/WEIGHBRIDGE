from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QPushButton, QCheckBox, QSizePolicy, QHBoxLayout
)
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtCore import QSize

from ticket_data_entry_designer_window import TicketDataEntryDesignerWindow
from ticket_entry_designer_window import TicketEntryDesignerWindow
from company_details import CompanyDetails
from database_designer import DatabaseDesigner
from formula_editor import FormulaEditor
from user_manager import UserManager

class AdministrationWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Administration")
        self.setFixedSize(340, 380)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        grid = QGridLayout()
        grid.setSpacing(12)
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

        buttons = []
        for idx, (icon, label, slot) in enumerate(button_info):
            btn = QPushButton()
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            if idx < 6:
                btn.setFixedSize(80, 60)
            else:
                btn.setFixedSize(80, 48)
            btn.setText(label)
            btn.setFont(font)
            # Set icon if you have the file, otherwise leave blank or set a default
            # btn.setIcon(QIcon(icon))  # Uncomment if you have icon files
            btn.setIcon(QIcon())       # Safe default if you don't have icons
            btn.setIconSize(QSize(32, 32))
            btn.setStyleSheet("text-align:center;")
            if slot:
                btn.clicked.connect(slot)
            buttons.append(btn)
            row, col = divmod(idx, 3)
            grid.addWidget(btn, row, col)

        main_layout.addLayout(grid)

        self.duplicate_pass_cb = QCheckBox("Password For Duplicate Ticket")
        self.duplicate_pass_cb.setChecked(True)
        self.allow_zero_cb = QCheckBox("Allow Zero Weight Ticket")
        main_layout.addWidget(self.duplicate_pass_cb)
        main_layout.addWidget(self.allow_zero_cb)

    def open_ticket_data_entry_designer(self):
        self.hide()
        self.tded_window = TicketDataEntryDesignerWindow()
        self.tded_window.show()

    def open_ticket_entry_designer(self):
        self.hide()
        self.ted_window = TicketEntryDesignerWindow()
        self.ted_window.show()

    def open_database_designer(self):
        self.hide()
        self.db_window = DatabaseDesigner()
        self.db_window.show()

    def open_formula_editor(self):
        self.hide()
        self.fe_window = FormulaEditor()
        self.fe_window.show()

    def open_user_manager(self):
        self.hide()
        self.um_window = UserManager()
        self.um_window.show()

    def open_company_details(self):
        self.hide()
        self.cd_window = CompanyDetails()
        self.cd_window.show()