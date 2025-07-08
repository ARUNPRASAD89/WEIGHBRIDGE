from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QListWidget, QVBoxLayout,
    QHBoxLayout, QGroupBox, QCheckBox, QTableWidget, QTableWidgetItem, QSplitter
)

class ReportDesigner(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ticket Report Templates")
        self.setFixedSize(600, 520)

        main_layout = QHBoxLayout(self)

        # Left: Template List
        template_list = QListWidget()
        template_list.addItems(["SSS", "Standard"])
        template_list.setFixedWidth(90)

        # Center: Details
        center_layout = QVBoxLayout()
        # Template Name
        tn_layout = QHBoxLayout()
        tn_layout.addWidget(QLabel("Template Name"))
        tn_layout.addWidget(QLineEdit())
        tn_layout.addWidget(QPushButton("Set as Default"))
        center_layout.addLayout(tn_layout)

        # Page Header
        center_layout.addWidget(QLabel("Page Header:"))
        for _ in range(3):
            ph_layout = QHBoxLayout()
            ph_layout.addWidget(QLineEdit())
            ph_layout.addWidget(QPushButton("Font"))
            center_layout.addLayout(ph_layout)
        wl_layout = QHBoxLayout()
        wl_layout.addWidget(QCheckBox("Without Lines"))
        center_layout.addLayout(wl_layout)

        # Field Selection
        field_sel_layout = QHBoxLayout()
        fields_list = QListWidget()
        fields_list.addItems([
            "TicketNumber", "VehicleNumber", "Date", "Time", "EmptyWeight", "LoadedWeight",
            "EmptyWeightDate", "EmptyWeightTime"
        ])
        field_sel_layout.addWidget(fields_list)
        # Arrows and Table
        arrow_table_layout = QVBoxLayout()
        ft_layout = QHBoxLayout()
        field_table = QTableWidget(5, 2)
        field_table.setHorizontalHeaderLabels(["Field Name", "Caption"])
        for i in range(5):
            for j in range(2):
                field_table.setItem(i, j, QTableWidgetItem(""))
        arrow_table_layout.addWidget(field_table)
        up_btn = QPushButton("↑")
        down_btn = QPushButton("↓")
        arrow_btns = QVBoxLayout()
        arrow_btns.addWidget(up_btn)
        arrow_btns.addWidget(down_btn)
        arrow_table_layout.addLayout(arrow_btns)
        field_sel_layout.addLayout(arrow_table_layout)

        center_layout.addLayout(field_sel_layout)
        fc_layout = QHBoxLayout()
        fc_layout.addWidget(QLabel("Field Caption"))
        fc_layout.addWidget(QLineEdit())
        fc_layout.addWidget(QPushButton("Save Caption"))
        center_layout.addLayout(fc_layout)

        # Page Footer
        center_layout.addWidget(QLabel("Page Footer:"))
        for _ in range(2):
            pf_layout = QHBoxLayout()
            pf_layout.addWidget(QLineEdit())
            pf_layout.addWidget(QPushButton("Font"))
            center_layout.addLayout(pf_layout)

        # Right: Operations
        right_layout = QVBoxLayout()
        right_layout.addWidget(QPushButton("Add"))
        right_layout.addWidget(QPushButton("Save"))
        right_layout.addWidget(QPushButton("Delete"))
        right_layout.addWidget(QPushButton("Preview"))
        right_layout.addWidget(QPushButton("Exit"))
        right_layout.addStretch()

        # Assembling
        main_layout.addWidget(template_list)
        main_layout.addLayout(center_layout)
        main_layout.addLayout(right_layout)