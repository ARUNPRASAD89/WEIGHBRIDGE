from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton
)
from transaction_window import TransactionWindow  # keep as-is if needed
from main_menu_form import MainMenuForm  # <-- Change: import MainMenuForm

class MainMenu(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Select Mode")
        self.setGeometry(200, 200, 400, 300)
        layout = QVBoxLayout()

        self.touch_btn = QPushButton("Touch Mode")
        self.manual_btn = QPushButton("Manual")

        self.touch_btn.setFixedHeight(80)
        self.manual_btn.setFixedHeight(80)

        self.touch_btn.clicked.connect(self.open_touch_mode)
        self.manual_btn.clicked.connect(self.open_manual_mode)  # <-- Connect Manual button

        layout.addWidget(self.touch_btn)
        layout.addWidget(self.manual_btn)

        self.setLayout(layout)

    def open_touch_mode(self):
        self.hide()
        self.tx_win = TransactionWindow()
        self.tx_win.show()

    def open_manual_mode(self):
        self.hide()
        self.manual_form = MainMenuForm()  # <-- Change: load MainMenuForm, not TicketWindow
        self.manual_form.show()
