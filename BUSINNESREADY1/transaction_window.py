from PyQt5.QtWidgets import QDialog, QVBoxLayout, QPushButton, QApplication
from PyQt5.QtGui import QFont
from first_load_window import LoadStatusDialog, VehicleSelectionDialog, FirstLoadWindow
from second_load_window import SecondLoadWindow
import sys

class TransactionWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Transaction Type")
        self.setFixedSize(400, 300)
        self.parent_window = parent

        layout = QVBoxLayout(self)
        layout.setSpacing(20)

        font = QFont("Arial", 16, QFont.Bold)

        self.first_load_btn = QPushButton("First Weighing")
        self.first_load_btn.setFont(font)
        self.first_load_btn.setMinimumHeight(80)
        self.first_load_btn.clicked.connect(self.open_first_load)
        layout.addWidget(self.first_load_btn)

        self.second_load_btn = QPushButton("Second Weighing")
        self.second_load_btn.setFont(font)
        self.second_load_btn.setMinimumHeight(80)
        self.second_load_btn.clicked.connect(self.open_second_load)
        layout.addWidget(self.second_load_btn)

    def _open_child_window(self, window_class, *args):
        """Helper to hide current and show child window."""
        self.hide()
        # Pass the current window (self) as the parent for the mode_window parameter
        self.child_window = window_class(*args, mode_window=self)
        self.child_window.show()

    def open_first_load(self):
        # This is the new, corrected workflow
        status_dialog = LoadStatusDialog(self)
        if status_dialog.exec_() == QDialog.Accepted:
            load_status = status_dialog.result
            
            vehicle_dialog = VehicleSelectionDialog(self)
            if vehicle_dialog.exec_() == QDialog.Accepted:
                vehicle_type = vehicle_dialog.result
                
                # Now open the main window with all the required info
                self._open_child_window(FirstLoadWindow, load_status, vehicle_type)

    def open_second_load(self):
        self._open_child_window(SecondLoadWindow)

    def closeEvent(self, event):
        # Ensure the parent window is shown when this one is closed
        if self.parent_window:
            self.parent_window.show()
        super().closeEvent(event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = TransactionWindow()
    win.show()
    sys.exit(app.exec_())
