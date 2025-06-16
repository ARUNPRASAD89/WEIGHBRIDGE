from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, QComboBox, QHBoxLayout,
    QVBoxLayout, QGridLayout, QFrame, QSizePolicy
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

class TicketWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ticket")
        self.setMinimumSize(1000, 560)
        self.setStyleSheet("background: #f6f6f6;")
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(0)

        # --- Left: Transaction Type Buttons ---
        self.menu_layout = QVBoxLayout()
        self.menu_layout.setSpacing(14)
        self.menu_layout.setContentsMargins(0, 0, 24, 0)

        btn_font = QFont("Arial", 11, QFont.Bold)
        self.single_btn = QPushButton("Single\nTransaction")
        self.first_btn = QPushButton("First\nTransaction")
        self.second_btn = QPushButton("Second\nTransaction")

        for b in (self.single_btn, self.first_btn, self.second_btn):
            b.setFixedSize(150, 54)
            b.setFont(btn_font)
            self.menu_layout.addWidget(b)

        self.menu_layout.addStretch(1)
        main_layout.addLayout(self.menu_layout)

        # --- Right: Main Transaction Panel ---
        self.right_panel = QVBoxLayout()
        self.right_panel.setSpacing(10)
        self.right_panel.setContentsMargins(0, 0, 0, 0)

        # Header: Title and Weight
        self.header_layout = QHBoxLayout()
        self.header_layout.setSpacing(14)
        self.title_label = QLabel()
        self.title_label.setFont(QFont("Arial", 20, QFont.Bold))
        self.title_label.setTextFormat(Qt.RichText)  # Allow colored text (for Shift B)
        self.header_layout.addWidget(self.title_label, alignment=Qt.AlignVCenter)

        # Wider Weight Display
        self.weight_display = QLabel("0 <span style='font-size:15pt'>kg</span>")
        self.weight_display.setFont(QFont("Arial", 38, QFont.Bold))
        self.weight_display.setStyleSheet(
            "background:#111;color:white;padding:0 40px;border-radius:10px;min-width:220px;text-align:right;"
        )
        self.weight_display.setAlignment(Qt.AlignCenter)
        self.header_layout.addStretch(1)
        self.header_layout.addWidget(self.weight_display, alignment=Qt.AlignRight | Qt.AlignTop)
        self.right_panel.addLayout(self.header_layout)

        # Fields Section
        self.fields_layout = QHBoxLayout()
        self.fields_layout.setSpacing(15)

        # --- Mandatory Fields ---
        mand_frame = QFrame()
        mand_grid = QGridLayout(mand_frame)
        mand_grid.setHorizontalSpacing(10)
        mand_grid.setVerticalSpacing(9)
        mand_lbl = QLabel("Mandatory Fields")
        mand_lbl.setFont(QFont("Arial", 11, QFont.Bold))
        mand_grid.addWidget(mand_lbl, 0, 0, 1, 2)

        self.ticket_number = QLineEdit()
        self.vehicle_number = QLineEdit()
        self.load_status = QComboBox()
        self.load_status.addItems(["Empty", "Load"])
        self.material = QLineEdit()
        self.supplier = QLineEdit()
        self.loaded_weight = QLineEdit()
        self.empty_weight = QLineEdit()
        self.net_weight = QLineEdit()

        mand_fields = [
            ("Ticket Number", self.ticket_number),
            ("Vehicle Number", self.vehicle_number),
            ("Load Status", self.load_status),
            ("Material", self.material),
            ("Supplier", self.supplier),
            ("Loaded Weight", self.loaded_weight),
            ("Empty Weight", self.empty_weight),
            ("Net Weight", self.net_weight),
        ]
        for i, (label, widget) in enumerate(mand_fields, 1):
            mand_grid.addWidget(QLabel(label), i, 0)
            mand_grid.addWidget(widget, i, 1)
        self.fields_layout.addWidget(mand_frame)

        # --- Custom Fields ---
        cust_frame = QFrame()
        cust_grid = QGridLayout(cust_frame)
        cust_grid.setHorizontalSpacing(10)
        cust_grid.setVerticalSpacing(9)
        cust_lbl = QLabel("Custom Fields")
        cust_lbl.setFont(QFont("Arial", 11, QFont.Bold))
        cust_grid.addWidget(cust_lbl, 0, 0, 1, 2)

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
        for i, (label, widget) in enumerate(custom_fields, 1):
            cust_grid.addWidget(QLabel(label), i, 0)
            cust_grid.addWidget(widget, i, 1)
        self.fields_layout.addWidget(cust_frame)

        self.right_panel.addLayout(self.fields_layout)

        # --- Operations Buttons ---
        self.ops_layout = QHBoxLayout()
        self.ops_layout.setSpacing(8)
        op_font = QFont("Arial", 11, QFont.Bold)
        op_btns = [
            "Weigh", "Save", "Preview", "Print", "DOS Print", "Export", "Search", "Cancel"
        ]
        self.op_buttons = []
        for name in op_btns:
            btn = QPushButton(name)
            btn.setFont(op_font)
            btn.setFixedSize(110, 38)
            self.ops_layout.addWidget(btn)
            self.op_buttons.append(btn)
        self.right_panel.addLayout(self.ops_layout)

        main_layout.addLayout(self.right_panel)

        # Connect transaction type buttons
        self.single_btn.clicked.connect(self.show_single)
        self.first_btn.clicked.connect(self.show_first)
        self.second_btn.clicked.connect(self.show_second)

        # Set fake data for testing
        self.show_first()  # Default view
        self.set_fake_data("first")  # Default to fake data for first

    def set_fake_data(self, tx_type):
        if tx_type == "single":
            self.title_label.setText(
                '<span style="color:blue">Shift B</span>  Vehicle Single Transaction'
            )
            self.ticket_number.setText("20001")
            self.vehicle_number.setText("TN10AB1234")
            self.load_status.setCurrentIndex(1)  # Load
            self.material.setText("Iron Ore")
            self.supplier.setText("ABC Minerals Ltd")
            self.loaded_weight.setText("28740")
            self.empty_weight.setText("7320")
            self.net_weight.setText("21420")
            self.status.setText("Completed")
            self.eamount.setText("6700")
            self.lamount.setText("12800")
            self.tamount.setText("19500")
            self.netweight1.setText("21420")
            self.weight_display.setText("28740 <span style='font-size:15pt'>kg</span>")
        elif tx_type == "first":
            self.title_label.setText(
                '<span style="color:blue">Shift B</span>  Vehicle First Transaction'
            )
            self.ticket_number.setText("20002")
            self.vehicle_number.setText("TN09XY5678")
            self.load_status.setCurrentIndex(0)  # Empty
            self.material.setText("Cement")
            self.supplier.setText("UltraTech")
            self.loaded_weight.setText("0")
            self.empty_weight.setText("8450")
            self.net_weight.setText("")
            self.status.setText("In Progress")
            self.eamount.setText("0")
            self.lamount.setText("0")
            self.tamount.setText("0")
            self.netweight1.setText("")
            self.weight_display.setText("0 <span style='font-size:15pt'>kg</span>")
        elif tx_type == "second":
            self.title_label.setText(
                '<span style="color:blue">Shift B</span>  Vehicle Second Transaction'
            )
            self.ticket_number.setText("20002")
            self.vehicle_number.setText("TN09XY5678")
            self.load_status.setCurrentIndex(1)  # Load
            self.material.setText("Cement")
            self.supplier.setText("UltraTech")
            self.loaded_weight.setText("21540")
            self.empty_weight.setText("8450")
            self.net_weight.setText("13090")
            self.status.setText("Completed")
            self.eamount.setText("0")
            self.lamount.setText("0")
            self.tamount.setText("0")
            self.netweight1.setText("13090")
            self.weight_display.setText("21540 <span style='font-size:15pt'>kg</span>")

    def show_single(self):
        self.set_fake_data("single")

    def show_first(self):
        self.set_fake_data("first")

    def show_second(self):
        self.set_fake_data("second")

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    w = TicketWindow()
    w.show()
    sys.exit(app.exec_())