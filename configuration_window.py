from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QPushButton, QCheckBox, QSizePolicy
)
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtCore import Qt

class ConfigurationWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Configuration")
        self.setFixedSize(350, 380)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # Top - Grid of buttons with icons and labels
        grid = QGridLayout()
        grid.setSpacing(12)
        font = QFont("Arial", 10, QFont.Bold)

        # Button definitions: (icon_path, label)
        button_info = [
            ("material_master.png", "Material Master"),
            ("supplier_master.png", "Supplier Master"),
            ("shift_master.png", "Shift Master"),
            ("vehicle_master.png", "Vehicle Master"),
            ("comm_port.png", "Comm port\nSetting"),
            ("report_designer.png", "Report Designer"),
            ("delete_entities.png", "Delete Entities"),
            ("duplicate_ticket.png", "Duplicate Ticket"),
            ("help.png", "Help"),
        ]

        # For demonstration, use blank QIcon(); replace with QIcon("path") for real icons
        for idx, (icon, label) in enumerate(button_info):
            btn = QPushButton()
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            btn.setFixedSize(90, 55)
            btn.setText(label)
            btn.setFont(font)
            btn.setIcon(QIcon())  # To use icons, replace with QIcon(icon)
            btn.setIconSize(btn.size())
            btn.setStyleSheet("text-align:center;")
            row, col = divmod(idx, 3)
            grid.addWidget(btn, row, col)

        main_layout.addLayout(grid)

        # Lower checkboxes and Exit button
        self.pre_printed_cb = QCheckBox("Use Pre Printed Stationary For Ticket Printing")
        self.pre_printed_cb.setChecked(True)
        self.dos_print_cb = QCheckBox("Use DOS Print Option")

        main_layout.addWidget(self.pre_printed_cb)
        main_layout.addWidget(self.dos_print_cb)

        # Exit button
        self.exit_btn = QPushButton("Exit")
        self.exit_btn.setFixedWidth(65)
        self.exit_btn.setFont(QFont("Arial", 10, QFont.Bold))
        self.exit_btn.clicked.connect(self.close)
        main_layout.addWidget(self.exit_btn, alignment=Qt.AlignRight)