import sys
import subprocess
import os
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QGridLayout, QPushButton, QSizePolicy, 
    QLabel, QFrame, QHBoxLayout, QSpacerItem, QMessageBox
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

from ticket_data_entry_designer_window import TicketDataEntryDesignerWindow
from ticket_entry_designer_window import TicketEntryDesignerWindow
from company_details import CompanyDetails
from database_designer import DatabaseDesigner
from formula_editor import FormulaEditor
from user_manager import UserManager
from rate_chart_manager_window import RateChartManagerWindow
from backup_window import BackupWindow
from whatsapp_template_designer import WhatsAppTemplateDesignerWindow

class AdministrationWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Administration")
        self.setMinimumSize(420, 550)

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

        button_info = [
            ("ticket_data_entry.png", "Ticket Data\nEntry Designer", self.open_ticket_data_entry_designer),
            ("ticket_print.png", "Ticket Print\nDesigner", self.open_ticket_entry_designer),
            ("database.png", "Database\nDesigner", self.open_database_designer),
            ("formula.png", "Formula Editor", self.open_formula_editor),
            ("user_manager.png", "User Manager", self.open_user_manager),
            ("company.png", "Company\nDetails", self.open_company_details),
            ("rate_chart.png", "Rate Chart\nManager", self.open_rate_chart_manager),
            ("backup.png", "Database\nBackup", self.open_backup_window),
            ("whatsapp.png", "WhatsApp\nManager", self.open_whatsapp_manager),
            ("whatsapp_designer.png", "WhatsApp Template\nDesigner", self.open_whatsapp_template_designer),
            ("email.png", "Email\nManager", self.open_email_manager),
            ("exit.png", "Exit", self.close),
        ]

        num_buttons = len(button_info)
        for idx, (icon, label, slot) in enumerate(button_info):
            btn = QPushButton(label)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            btn.setMinimumHeight(70)
            btn.setFont(font)
            if slot: btn.clicked.connect(slot)
            
            row, col = divmod(idx, 2)
            if idx == num_buttons - 1 and num_buttons % 2 != 0:
                grid_layout.addWidget(btn, row, 0, 1, 2)
            else:
                grid_layout.addWidget(btn, row, col)

        main_layout.addWidget(grid_frame)
        main_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

    def _open_child_window(self, window_class):
        """Generic method to open child windows"""
        self.hide()
        self.child_window = window_class(parent=self)
        self.child_window.show()

    # ===== ALL WINDOW OPENERS USING LAZY IMPORTS =====
    
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
    
    def open_rate_chart_manager(self):
        self._open_child_window(RateChartManagerWindow)
    
    def open_backup_window(self):
        self._open_child_window(BackupWindow)
    
    def open_whatsapp_template_designer(self):
        self._open_child_window(WhatsAppTemplateDesignerWindow)

    def open_whatsapp_manager(self):
        """
        Launch WhatsApp Manager as separate process
        """
        try:
            if getattr(sys, 'frozen', False):
                # PyInstaller bundle
                current_app_dir = os.path.dirname(sys.executable)
                whatsapp_executable = os.path.join(current_app_dir, '..', 'AdminTools', 'WhatsAppManager.exe')
                whatsapp_executable = os.path.normpath(whatsapp_executable)

                if not os.path.exists(whatsapp_executable):
                    raise FileNotFoundError(f"WhatsApp executable not found: {whatsapp_executable}")

                subprocess.Popen([whatsapp_executable])
            else:
                # Development environment
                python_executable = sys.executable
                script_path = "whatsapp_gui.py"
                if not os.path.exists(script_path):
                    raise FileNotFoundError(f"Script '{script_path}' not found")
                
                subprocess.Popen([python_executable, script_path])
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to launch WhatsApp Manager:\n\n{e}")

    def open_email_manager(self):
        """
        Open Email Manager Window - LAZY IMPORT (No circular imports!)
        """
        try:
            from email_manager_window import EmailManagerWindow
            self._open_child_window(EmailManagerWindow)
        except ImportError as e:
            QMessageBox.critical(self, "Error", f"EmailManagerWindow import failed:\n\n{e}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open Email Manager:\n\n{e}")

    def close(self):
        parent = self.parent()
        if parent: 
            parent.show()
        super().close()
