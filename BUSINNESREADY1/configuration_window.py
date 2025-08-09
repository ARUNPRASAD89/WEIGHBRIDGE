from PyQt5.QtWidgets import (
    QWidget, QPushButton, QVBoxLayout, QApplication, QDialog, QGridLayout, 
    QFrame, QLabel, QSizePolicy
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

from material_master import MaterialMaster
from supplier_master import SupplierMaster
from shift_master import ShiftMaster
from vehicle_master import VehicleMaster
from comm_port_settings import CommPortSettings
from camera_port import CameraPortSettings
from report_designer import ReportDesigner
from delete_entities import DeleteEntities
from duplicate_ticket import DuplicateTicket
# --- IMPORT THE NEW IMPORTER WINDOW ---
from document_importer_window import DocumentImporterWindow

class ConfigurationWindow(QDialog):
    def __init__(self, parent=None, permissions=None):
        super().__init__(parent)
        self.permissions = permissions
        self.setWindowTitle("Configuration")
        self.setMinimumSize(400, 500) # Increased height for new buttons

        # --- STYLES ---
        self.primary_color = "#3498db"
        self.accent_color = "#f39c12"
        # --- FIX: Define all color attributes before using them ---
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
            QPushButton:disabled {{ background-color: #95a5a6; color: #bdc3c7; }}
            QFrame {{ border: 1px solid {self.light_border_color}; border-radius: 8px; }}
        """)


        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        header_label = QLabel("Configuration Panel")
        header_label.setFont(QFont("Arial", 16, QFont.Bold))
        header_label.setStyleSheet(f"color: {self.primary_color};")
        main_layout.addWidget(header_label, alignment=Qt.AlignCenter)

        grid_frame = QFrame()
        grid_layout = QGridLayout(grid_frame)
        grid_layout.setSpacing(15)
        grid_layout.setContentsMargins(15, 15, 15, 15)

        self.buttons = {
            "Material Master": (QPushButton("Material Master"), self.open_material_master),
            "Supplier Master": (QPushButton("Supplier Master"), self.open_supplier_master),
            "Shift Master": (QPushButton("Shift Master"), self.open_shift_master),
            "Vehicle Master": (QPushButton("Vehicle Master"), self.open_vehicle_master),
            "Comm Port Setting": (QPushButton("Comm Port Setting"), self.open_comm_port_settings),
            "Camera Port Settings": (QPushButton("Camera Port Settings"), self.open_camera_port_settings),
            "Document Importer": (QPushButton("Document Importer"), self.open_document_importer),
            "Report Designer": (QPushButton("Report Designer"), self.open_report_designer),
            "Delete Entities": (QPushButton("Delete Entities"), self.open_delete_entities),
            "Duplicate Ticket": (QPushButton("Duplicate Ticket"), self.open_duplicate_ticket)
        }

        # Dynamically place buttons in the grid
        sorted_buttons = sorted(self.buttons.keys())
        for idx, text in enumerate(sorted_buttons):
            button, slot = self.buttons[text]
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            button.setMinimumHeight(50)
            button.clicked.connect(slot)
            row, col = divmod(idx, 2)
            grid_layout.addWidget(button, row, col)
        
        main_layout.addWidget(grid_frame)
        main_layout.addStretch()

        self.exit_btn = QPushButton("Exit")
        self.exit_btn.clicked.connect(self.close)
        main_layout.addWidget(self.exit_btn)

        self._apply_permissions()

    def _apply_permissions(self):
        if not self.permissions:
            for button, _ in self.buttons.values():
                button.setEnabled(False)
            return

        is_admin = self.permissions.get('adminuser', False) or self.permissions.get('primaryuser', False)
        self.buttons["Material Master"][0].setEnabled(is_admin)
        self.buttons["Supplier Master"][0].setEnabled(is_admin)
        self.buttons["Shift Master"][0].setEnabled(is_admin)
        self.buttons["Comm Port Setting"][0].setEnabled(is_admin)
        self.buttons["Camera Port Settings"][0].setEnabled(is_admin)
        self.buttons["Report Designer"][0].setEnabled(is_admin)
        self.buttons["Document Importer"][0].setEnabled(is_admin)
        
        self.buttons["Vehicle Master"][0].setEnabled(self.permissions.get('vehiclemaster', False) or is_admin)
        self.buttons["Delete Entities"][0].setEnabled(self.permissions.get('deleterecords', False) or is_admin)
        self.buttons["Duplicate Ticket"][0].setEnabled(self.permissions.get('duplicateticket', False) or is_admin)

    def _open_child_window(self, window_class):
        self.hide()
        self.child_window = window_class(parent=self)
        self.child_window.show()

    def open_material_master(self): self._open_child_window(MaterialMaster)
    def open_supplier_master(self): self._open_child_window(SupplierMaster)
    def open_shift_master(self): self._open_child_window(ShiftMaster)
    def open_vehicle_master(self): self._open_child_window(VehicleMaster)
    def open_comm_port_settings(self): self._open_child_window(CommPortSettings)
    def open_report_designer(self): self._open_child_window(ReportDesigner)
    def open_delete_entities(self): self._open_child_window(DeleteEntities)
    def open_duplicate_ticket(self): self._open_child_window(DuplicateTicket)
    def open_camera_port_settings(self): self._open_child_window(CameraPortSettings)
    def open_document_importer(self): self._open_child_window(DocumentImporterWindow)

    def closeEvent(self, event):
        parent = self.parent()
        if parent:
            parent.show()
        super().closeEvent(event)


#After replacing the content of `configuration_window.py` with this corrected version, the `AttributeError` will be resolved, and your application should launch correctly.
