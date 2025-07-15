from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QDialog
from transaction_window import TransactionWindow
from main_menu_form import MainMenuForm

class MainMenu(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Mode")
        self.setGeometry(200, 200, 400, 300)
        layout = QVBoxLayout()

        # Create buttons
        self.touch_btn = QPushButton("Touch Mode")
        self.manual_btn = QPushButton("Manual")

        self.touch_btn.setFixedHeight(80)
        self.manual_btn.setFixedHeight(80)

        # Connect buttons to their slots
        self.touch_btn.clicked.connect(self.open_touch_mode)
        self.manual_btn.clicked.connect(self.open_manual_mode)

        # Add buttons to layout
        layout.addWidget(self.touch_btn)
        layout.addWidget(self.manual_btn)

        self.setLayout(layout)

        # References to child windows
        self.tx_win = None
        self.manual_form = None

    def open_touch_mode(self):
        self.hide()
        self.tx_win = TransactionWindow()
        self.tx_win.show()
        # Re-show MainMenu when TransactionWindow is closed
        self.tx_win.destroyed.connect(self.show)

    def open_manual_mode(self):
        self.hide()
        self.manual_form = MainMenuForm(parent=self)  # Pass self as parent!
        self.manual_form.show()
        self.manual_form.destroyed.connect(self.show)
