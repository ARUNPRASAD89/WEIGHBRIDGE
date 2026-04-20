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
        self.hide()
        self.child_window = window_class(parent=self)
        self.child_window.show()

    def open_whatsapp_manager(self):
        """
        --- CORRECTED AND ROBUST SOLUTION ---
        Launches the WhatsApp GUI as a separate process.
        This works for both development and the final installed application.
        """
        try:
            # This check correctly determines if the app is running from a PyInstaller bundle.
            if getattr(sys, 'frozen', False):
                # --- This block runs on the target PC after installation ---

                # 1. Get the directory of the CURRENTLY running executable (WeighbridgeApp.exe).
                #    Based on our installer, this will be 'C:\Program Files (x86)\WeighbridgeSuite\Kiosk'
                current_app_dir = os.path.dirname(sys.executable)
                
                # 2. Navigate to the correct folder where WhatsAppManager.exe was installed.
                #    Our installer puts it in 'C:\Program Files (x86)\WeighbridgeSuite\AdminTools'
                whatsapp_executable = os.path.join(current_app_dir, '..', 'AdminTools', 'WhatsAppManager.exe')
                
                # 3. Normalize the path to handle the '..' correctly (e.g., C:\A\B\..\C -> C:\A\C)
                whatsapp_executable = os.path.normpath(whatsapp_executable)

                if not os.path.exists(whatsapp_executable):
                    raise FileNotFoundError(f"The WhatsApp executable was not found at the expected location: {whatsapp_executable}")

                # 4. Launch the executable.
                subprocess.Popen([whatsapp_executable])

            else:
                # --- This block runs in your development environment (e.g., python main.py) ---
                python_executable = sys.executable
                # Corrected to point to the actual script name
                script_path = "whatsapp_gui.py"
                if not os.path.exists(script_path):
                     raise FileNotFoundError(f"The script '{script_path}' was not found in the project directory.")
                
                subprocess.Popen([python_executable, script_path])
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to launch WhatsApp Manager:\n\n{e}")


    def open_ticket_data_entry_designer(self): self._open_child_window(TicketDataEntryDesignerWindow)
    def open_ticket_entry_designer(self): self._open_child_window(TicketEntryDesignerWindow)
    def open_database_designer(self): self._open_child_window(DatabaseDesigner)
    def open_formula_editor(self): self._open_child_window(FormulaEditor)
    def open_user_manager(self): self._open_child_window(UserManager)
    def open_company_details(self): self._open_child_window(CompanyDetails)
    def open_rate_chart_manager(self): self._open_child_window(RateChartManagerWindow)
    def open_backup_window(self): self._open_child_window(BackupWindow)
    def open_whatsapp_template_designer(self): self._open_child_window(WhatsAppTemplateDesignerWindow)

    def close(self):
        parent = self.parent()
        if parent: parent.show()
        super().close()
