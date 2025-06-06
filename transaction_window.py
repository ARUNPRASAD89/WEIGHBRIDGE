from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton
)
from first_load_window import FirstLoadWindow

class TransactionWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Transaction Type")
        self.setGeometry(250, 250, 400, 200)
        layout = QVBoxLayout()

        self.first_load_btn = QPushButton("First Load")
        self.second_load_btn = QPushButton("Second Load")

        self.first_load_btn.setFixedHeight(80)
        self.second_load_btn.setFixedHeight(80)

        self.first_load_btn.clicked.connect(self.open_first_load)
        # self.second_load_btn.clicked.connect(self.open_second_load)  # Not implemented

        layout.addWidget(self.first_load_btn)
        layout.addWidget(self.second_load_btn)

        self.setLayout(layout)

    def open_first_load(self):
        self.hide()
        self.first_load_win = FirstLoadWindow()
        self.first_load_win.show()