from PyQt5.QtWidgets import (
    QWidget, QGroupBox, QVBoxLayout, QHBoxLayout, QGridLayout,
    QRadioButton, QLabel, QComboBox, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QSizePolicy
)
from PyQt5.QtCore import Qt

class ReportWindowForm(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Report Selection")
        self.setFixedSize(700, 420)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(6)

        # Top Section: Reports On
        top_layout = QHBoxLayout()
        reports_on_box = QGroupBox("Reports On")
        reports_on_layout = QVBoxLayout()
        self.material_radio = QRadioButton("Material")
        self.supplier_radio = QRadioButton("Supplier")
        self.ticket_radio = QRadioButton("Ticket")
        self.material_radio.setChecked(True)
        reports_on_layout.addWidget(self.material_radio)
        reports_on_layout.addWidget(self.supplier_radio)
        reports_on_layout.addWidget(self.ticket_radio)
        reports_on_box.setLayout(reports_on_layout)
        top_layout.addWidget(reports_on_box, alignment=Qt.AlignTop)

        # Selection Based On
        selection_layout = QVBoxLayout()
        selection_label = QLabel("Selection Based On")
        self.selection_combo = QComboBox()
        self.selection_combo.addItems(["Material Name", "Supplier Name", "Ticket Number"])
        selection_layout.addWidget(selection_label)
        selection_layout.addWidget(self.selection_combo)
        top_layout.addLayout(selection_layout)

        # Criteria Section
        criteria_layout = QGridLayout()
        criteria_group = QGroupBox("Criteria")
        self.all_radio = QRadioButton("All")
        self.all_radio.setChecked(True)
        self.from_radio = QRadioButton("From")
        where_label = QLabel("Where")
        self.where_field1 = QLineEdit()
        self.where_field2 = QLineEdit()
        self.or_btn = QPushButton("OR")
        self.and_btn = QPushButton("AND")
        self.build_btn = QPushButton("Build")
        self.clear_btn = QPushButton("Clear")
        self.from_field1 = QLineEdit()
        to_label = QLabel("To")
        self.from_field2 = QLineEdit()

        # Row 0: All/Where
        criteria_layout.addWidget(self.all_radio, 0, 0)
        criteria_layout.addWidget(where_label, 0, 1)
        criteria_layout.addWidget(self.where_field1, 0, 2)
        criteria_layout.addWidget(self.where_field2, 0, 3)
        criteria_layout.addWidget(self.or_btn, 0, 4)
        criteria_layout.addWidget(self.and_btn, 0, 5)
        criteria_layout.addWidget(self.build_btn, 0, 6)
        criteria_layout.addWidget(self.clear_btn, 0, 7)
        # Row 1: From/To
        criteria_layout.addWidget(self.from_radio, 1, 0)
        criteria_layout.addWidget(self.from_field1, 1, 1)
        criteria_layout.addWidget(to_label, 1, 2)
        criteria_layout.addWidget(self.from_field2, 1, 3)

        criteria_group.setLayout(criteria_layout)
        top_layout.addWidget(criteria_group)

        main_layout.addLayout(top_layout)

        # Table area (empty, just as visual per reference)
        self.table = QTableWidget(6, 3)
        self.table.setHorizontalHeaderLabels(["Column 1", "Column 2", "Column 3"])
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        main_layout.addWidget(self.table)

        # Bottom Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch(1)
        self.onscreen_btn = QPushButton("On Screen")
        self.print_btn = QPushButton("Print")
        self.exit_btn = QPushButton("Exit")
        btn_layout.addWidget(self.onscreen_btn)
        btn_layout.addWidget(self.print_btn)
        btn_layout.addWidget(self.exit_btn)
        main_layout.addLayout(btn_layout)