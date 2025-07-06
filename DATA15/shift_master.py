from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QHBoxLayout, QVBoxLayout,
    QListWidget, QGroupBox, QTimeEdit
)

class ShiftMaster(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Shifts")
        self.setFixedSize(300, 370)
        layout = QVBoxLayout(self)

        # Shift List
        list_label = QLabel("Shift List")
        layout.addWidget(list_label)
        shift_list = QListWidget()
        shift_list.setStyleSheet("background: #ffffcc;")
        shift_list.addItems(["A", "B", "C"])
        layout.addWidget(shift_list)

        # Shift Name
        shift_name_layout = QHBoxLayout()
        shift_name_layout.addWidget(QLabel("Shift Name"))
        shift_name_layout.addWidget(QLineEdit())
        layout.addLayout(shift_name_layout)

        # Shift From
        shift_from_layout = QHBoxLayout()
        shift_from_layout.addWidget(QLabel("Shift From"))
        shift_from_layout.addWidget(QTimeEdit())
        layout.addLayout(shift_from_layout)

        # Shift To
        shift_to_layout = QHBoxLayout()
        shift_to_layout.addWidget(QLabel("Shift To"))
        shift_to_layout.addWidget(QTimeEdit())
        layout.addLayout(shift_to_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(QPushButton("Add"))
        btn_layout.addWidget(QPushButton("Edit"))
        btn_layout.addWidget(QPushButton("Delete"))
        btn_layout.addWidget(QPushButton("Exit"))
        layout.addLayout(btn_layout)