from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QHBoxLayout, QVBoxLayout
)

class VehicleMaster(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Vehicle Details")
        self.setFixedSize(310, 140)

        layout = QVBoxLayout(self)

        # Vehicle Id
        id_layout = QHBoxLayout()
        id_layout.addWidget(QLabel("Vehicle Id:"))
        id_edit = QLineEdit()
        id_layout.addWidget(id_edit)
        id_layout.addWidget(QPushButton("..."))
        layout.addLayout(id_layout)

        # Vehicle No
        no_layout = QHBoxLayout()
        no_layout.addWidget(QLabel("Vehicle No:"))
        no_edit = QLineEdit()
        no_layout.addWidget(no_edit)
        layout.addLayout(no_layout)

        # Tare Weight
        tare_layout = QHBoxLayout()
        tare_layout.addWidget(QLabel("Vehicle Tare Weight:"))
        tare_edit = QLineEdit()
        tare_layout.addWidget(tare_edit)
        layout.addLayout(tare_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(QPushButton("Add"))
        btn_layout.addWidget(QPushButton("Edit"))
        btn_layout.addWidget(QPushButton("Exit"))
        layout.addLayout(btn_layout)