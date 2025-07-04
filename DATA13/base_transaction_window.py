from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit, QComboBox, QPushButton,
    QFrame, QSizePolicy, QSpacerItem
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

class BaseTransactionWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ticket")
        self.setMinimumSize(940, 600)
        self.setStyleSheet("background: #fff;")

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(0)

        # --- LEFT: Transaction Type Menu ---
        side_menu = QVBoxLayout()
        side_menu.setSpacing(24)
        side_menu.setContentsMargins(0, 0, 10, 0)

        self.btn_single = QPushButton("Single\nTransaction")
        self.btn_first = QPushButton("First\nTransaction")
        self.btn_second = QPushButton("Second\nTransaction")
        for btn in (self.btn_single, self.btn_first, self.btn_second):
            btn.setFixedSize(120, 60)
            btn.setFont(QFont("Arial", 10, QFont.Bold))
            btn.setStyleSheet("text-align:left; padding-left:32px;")
        side_menu.addWidget(self.btn_single)
        side_menu.addWidget(self.btn_first)
        side_menu.addWidget(self.btn_second)
        side_menu.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        main_layout.addLayout(side_menu)

        # --- RIGHT: Main UI Area ---
        right_area = QVBoxLayout()
        right_area.setSpacing(2)
        right_area.setContentsMargins(0, 0, 0, 0)

        # HEADER
        header = QHBoxLayout()
        header.setSpacing(10)
        self.lbl_shift = QLabel("Shift  B")
        self.lbl_shift.setFont(QFont("Arial", 11, QFont.Bold))
        self.lbl_shift.setFixedWidth(70)
        header.addWidget(self.lbl_shift, alignment=Qt.AlignLeft)

        self.lbl_title = QLabel("Select Transaction Type")
        self.lbl_title.setFont(QFont("Arial", 15, QFont.Bold))
        self.lbl_title.setStyleSheet("color:#0B36B1;")
        header.addWidget(self.lbl_title, alignment=Qt.AlignHCenter)

        header.addStretch(1)

        self.weight_display = QLabel("0")
        self.weight_display.setFont(QFont("Arial", 38, QFont.Bold))
        self.weight_display.setStyleSheet("background:#111;color:white;padding:0 30px;border-radius:5px;min-width:180px;")
        self.weight_display.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        header.addWidget(self.weight_display)
        kg_label = QLabel("kg")
        kg_label.setFont(QFont("Arial", 18, QFont.Bold))
        kg_label.setStyleSheet("color:#111;")
        header.addWidget(kg_label)
        right_area.addLayout(header)

        # --- FORM FIELDS ---
        form_area = QHBoxLayout()
        form_area.setSpacing(8)

        # MANDATORY FIELDS (to be used/overridden by child)
        mand_frame = QFrame()
        mand_frame.setFrameShape(QFrame.StyledPanel)
        self.mand_grid = QGridLayout(mand_frame)
        self.mand_grid.setHorizontalSpacing(12)
        self.mand_grid.setVerticalSpacing(10)

        self.lbl_mand = QLabel("Mandatory Fields")
        self.lbl_mand.setFont(QFont("Arial", 10, QFont.Bold))
        self.mand_grid.addWidget(self.lbl_mand, 0, 0, 1, 2)

        self.ticket_number = QLineEdit(); self.ticket_number.setReadOnly(True)
        self.vehicle_number = QLineEdit()
        self.load_status = QComboBox()
        self.material = QLineEdit(); self.material.setReadOnly(False)
        self.supplier = QLineEdit(); self.supplier.setReadOnly(False)
        self.loaded_weight = QLineEdit(); self.loaded_weight.setReadOnly(True)
        self.empty_weight = QLineEdit(); self.empty_weight.setReadOnly(True)
        self.net_weight = QLineEdit(); self.net_weight.setReadOnly(True)

        self.mand_grid.addWidget(QLabel("Ticket Number"), 1, 0)
        self.mand_grid.addWidget(self.ticket_number, 1, 1)
        self.mand_grid.addWidget(QLabel("Vehicle Number"), 2, 0)
        self.mand_grid.addWidget(self.vehicle_number, 2, 1)
        self.mand_grid.addWidget(QLabel("Load Status"), 3, 0)
        self.mand_grid.addWidget(self.load_status, 3, 1)
        self.mand_grid.addWidget(QLabel("Material"), 4, 0)
        self.mand_grid.addWidget(self.material, 4, 1)
        self.mand_grid.addWidget(QLabel("Supplier"), 5, 0)
        self.mand_grid.addWidget(self.supplier, 5, 1)
        self.mand_grid.addWidget(QLabel("Loaded Weight"), 6, 0)
        self.mand_grid.addWidget(self.loaded_weight, 6, 1)
        self.mand_grid.addWidget(QLabel("Empty Weight"), 7, 0)
        self.mand_grid.addWidget(self.empty_weight, 7, 1)
        self.mand_grid.addWidget(QLabel("Net Weight"), 8, 0)
        self.mand_grid.addWidget(self.net_weight, 8, 1)

        form_area.addWidget(mand_frame, stretch=3)

        # CUSTOM FIELDS
        cust_frame = QFrame()
        cust_frame.setFrameShape(QFrame.StyledPanel)
        cust_grid = QGridLayout(cust_frame)
        cust_grid.setHorizontalSpacing(12)
        cust_grid.setVerticalSpacing(10)

        lbl_cust = QLabel("Custom Fields")
        lbl_cust.setFont(QFont("Arial", 10, QFont.Bold))
        cust_grid.addWidget(lbl_cust, 0, 0, 1, 2)

        self.status = QLineEdit()
        self.eamount = QLineEdit()
        self.lamount = QLineEdit()
        self.tamount = QLineEdit()
        self.netweight1 = QLineEdit()

        custom_fields = [
            ("STATUS", self.status),
            ("EAMOUNT", self.eamount),
            ("LAMOUNT", self.lamount),
            ("TAMOUNT", self.tamount),
            ("NetWeight1", self.netweight1),
        ]
        for i, (label, field) in enumerate(custom_fields, 1):
            cust_grid.addWidget(QLabel(label), i, 0)
            cust_grid.addWidget(field, i, 1)
        form_area.addWidget(cust_frame, stretch=2)

        right_area.addLayout(form_area)

        # --- OPERATIONS BAR ---
        operations = QHBoxLayout()
        operations.setSpacing(8)
        operations.setContentsMargins(0, 16, 0, 0)
        self.btn_weigh = QPushButton("Weigh")
        self.btn_save = QPushButton("Save")
        self.btn_preview = QPushButton("Preview")
        self.btn_print = QPushButton("Print")
        self.btn_dosprint = QPushButton("DOS Print")
        self.btn_export = QPushButton("Export")
        self.btn_search = QPushButton("Search")
        self.btn_exit = QPushButton("Exit")
        for btn in [
            self.btn_weigh, self.btn_save, self.btn_preview, self.btn_print,
            self.btn_dosprint, self.btn_export, self.btn_search, self.btn_exit
        ]:
            btn.setFont(QFont("Arial", 10, QFont.Bold))
            btn.setFixedSize(90, 48)
        operations.addWidget(self.btn_weigh)
        operations.addWidget(self.btn_save)
        operations.addWidget(self.btn_preview)
        operations.addWidget(self.btn_print)
        operations.addWidget(self.btn_dosprint)
        operations.addWidget(self.btn_export)
        operations.addWidget(self.btn_search)
        operations.addWidget(self.btn_exit)
        right_area.addLayout(operations)

        main_layout.addLayout(right_area, stretch=1)

        # --- BUTTON CONNECTIONS: open transaction windows (to be handled in main driver) ---
        self.btn_single.clicked.connect(self.open_single_transaction)
        self.btn_first.clicked.connect(self.open_first_transaction)
        self.btn_second.clicked.connect(self.open_second_transaction)

    def open_single_transaction(self):
        from single_transaction_window import SingleTransactionWindow
        self.next_window = SingleTransactionWindow()
        self.next_window.show()
        self.close()

    def open_first_transaction(self):
        from first_transaction_window import FirstTransactionWindow
        self.next_window = FirstTransactionWindow()
        self.next_window.show()
        self.close()

    def open_second_transaction(self):
        from second_transaction_window import SecondTransactionWindow
        self.next_window = SecondTransactionWindow()
        self.next_window.show()
        self.close()