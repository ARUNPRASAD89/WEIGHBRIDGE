from PyQt5.QtWidgets import (
    QWidget, QLabel, QRadioButton, QLineEdit, QComboBox, QDateEdit,
    QTimeEdit, QPushButton, QHBoxLayout, QVBoxLayout, QGroupBox
)
from PyQt5.QtCore import QDate, QTime

class DuplicateTicket(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Duplicate Ticket Printing")
        self.setFixedSize(400, 220)

        layout = QVBoxLayout(self)

        # Transaction Type
        trans_group = QGroupBox("Transaction Type")
        trans_layout = QHBoxLayout()
        rb_pending = QRadioButton("Pending")
        rb_complete = QRadioButton("Complete")
        rb_single = QRadioButton("Single Transaction")
        rb_pending.setChecked(True)
        trans_layout.addWidget(rb_pending)
        trans_layout.addWidget(rb_complete)
        trans_layout.addWidget(rb_single)
        trans_group.setLayout(trans_layout)
        layout.addWidget(trans_group)

        # Transaction Search Options
        search_group = QGroupBox("Transaction Search Options")
        search_layout = QHBoxLayout()
        date_label = QLabel("Date")
        date_edit = QDateEdit()
        date_edit.setDate(QDate(2002, 1, 1))
        vehicle_label = QLabel("Vehicle Number")
        vehicle_combo = QComboBox()
        search_layout.addWidget(date_label)
        search_layout.addWidget(date_edit)
        search_layout.addWidget(vehicle_label)
        search_layout.addWidget(vehicle_combo)
        search_group.setLayout(search_layout)
        layout.addWidget(search_group)

        # From/To Time
        time_layout = QHBoxLayout()
        time_layout.addWidget(QLabel("From Time"))
        from_time = QTimeEdit()
        from_time.setTime(QTime(9, 0, 0))
        time_layout.addWidget(from_time)
        time_layout.addWidget(QLabel("To Time"))
        to_time = QTimeEdit()
        to_time.setTime(QTime(21, 0, 0))
        time_layout.addWidget(to_time)
        search_btn = QPushButton("Search")
        time_layout.addStretch()
        time_layout.addWidget(search_btn)
        layout.addLayout(time_layout)

        # Ticket Number and buttons
        ticket_layout = QHBoxLayout()
        ticket_layout.addWidget(QLabel("Ticket Number"))
        ticket_combo = QComboBox()
        ticket_layout.addWidget(ticket_combo)
        ticket_layout.addStretch()
        ticket_layout.addWidget(QPushButton("Print"))
        ticket_layout.addWidget(QPushButton("Exit"))
        layout.addLayout(ticket_layout)