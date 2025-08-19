from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QApplication, QWidget, QLabel
from PyQt5.QtGui import QFont, QColor, QPalette
from PyQt5.QtCore import Qt
from first_load_window import LoadStatusDialog, VehicleSelectionDialog, FirstLoadWindow
from second_load_window import SecondLoadWindow
import sys

class BigSymbolButton(QPushButton):
    """
    A custom QPushButton composed of a large circled number (QLabel) above
    and a smaller multilingual text (QLabel) below, all clickable as a button.
    """
    def __init__(self, circled_number, text, bg_color, fg_color, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color};
                color: {fg_color};
                border-radius: 32px;
                padding: 0px;
                font-weight: bold;
            }}
            QPushButton:pressed {{
                background-color: #444;
            }}
        """)
        self.setMinimumHeight(330)
        self.setCursor(Qt.PointingHandCursor)

        # Layout for the button's custom content
        content_widget = QWidget(self)
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 10, 0, 10)
        content_layout.setSpacing(0)

        # Big circled number label
        symbol_label = QLabel(circled_number)
        symbol_label.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        symbol_label.setFont(QFont("Arial", 100, QFont.Bold))
        symbol_label.setStyleSheet(f"color: {fg_color}; background: transparent;")
        content_layout.addWidget(symbol_label)

        # Multilingual label
        text_label = QLabel(text)
        text_label.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        text_label.setFont(QFont("Arial", 22, QFont.Bold))
        text_label.setStyleSheet(f"color: {fg_color}; background: transparent;")
        content_layout.addWidget(text_label)

        # Set button layout content
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(content_widget)
        layout.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)

class TransactionWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Transaction Type")
        self.setFixedSize(700, 700)
        self.parent_window = parent

        layout = QVBoxLayout(self)
        layout.setSpacing(32)

        # Button 1: ❶, blue, multilingual text
        self.first_load_btn = BigSymbolButton(
            circled_number="❶",
            text="1. First Weighing\nமுதல் எடை\nपहला वजन",
            bg_color="#2471A3",
            fg_color="white"
        )
        self.first_load_btn.clicked.connect(self.open_first_load)
        layout.addWidget(self.first_load_btn)

        # Button 2: ❷, orange, multilingual text
        self.second_load_btn = BigSymbolButton(
            circled_number="❷",
            text="2. Second Weighing\nஇரண்டாம் எடை\nदूसरा लदान",
            bg_color="#F39C12",
            fg_color="white"
        )
        self.second_load_btn.clicked.connect(self.open_second_load)
        layout.addWidget(self.second_load_btn)

        self.setLayout(layout)

    

    def open_first_load(self):
        self.hide()
        status_dialog = LoadStatusDialog(self)
        if status_dialog.exec_() == QDialog.Accepted:
            load_status = status_dialog.result

            vehicle_dialog = VehicleSelectionDialog(self)
            if vehicle_dialog.exec_() == QDialog.Accepted:
                vehicle_type = vehicle_dialog.result
                self._open_child_window(FirstLoadWindow, load_status, vehicle_type)

    def open_second_load(self):
        self.hide()
        vehicle_dialog = VehicleSelectionDialog(self)
        if vehicle_dialog.exec_() == QDialog.Accepted:
            vehicle_type = vehicle_dialog.result
            self.hide()
            self.child_window = SecondLoadWindow(mode_window=self)
            try:
                self.child_window.preselected_vehicle_type = vehicle_type
            except Exception:
                pass
            self.child_window.show()

    def closeEvent(self, event):
        if self.parent_window:
            self.parent_window.show()
        super().closeEvent(event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = TransactionWindow()
    win.show()
    sys.exit(app.exec_())
