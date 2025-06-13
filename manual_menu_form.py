from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton
from ticket_window import TicketWindow

class ManualMenuForm(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Manual Menu")
        layout = QVBoxLayout()
        self.ticket_btn = QPushButton("Ticket Entry")
        self.ticket_btn.clicked.connect(self.open_ticket_window)
        layout.addWidget(self.ticket_btn)
        self.setLayout(layout)

    def open_ticket_window(self):
        self.hide()
        self.ticket_win = TicketWindow(parent_menu=self)
        self.ticket_win.show()