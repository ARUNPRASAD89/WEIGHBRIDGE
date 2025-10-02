from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QWidget, QLabel, QPushButton, QApplication,
    QMessageBox, QHBoxLayout, QSizePolicy, QFrame
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QTimer
from first_load_window import LoadStatusDialog, VehicleSelectionDialog, FirstLoadWindow
from second_load_window import SecondLoadWindow
from third_load_window import ThirdLoadWindow, LoadStatusDialogThird
from main_menu_form import MainMenuForm
from login_window import LoginWindow
from db_utils import fetch_one
import sys


class BigSymbolButton(QPushButton):
    """
    Large symbolic button used for transaction selection.
    """
    def __init__(self, circled_number, text, bg_color, fg_color, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color};
                color: {fg_color};
                border-radius: 28px;
                padding: 0px;
                font-weight: bold;
            }}
            QPushButton:pressed {{
                background-color: #444;
            }}
        """)

        MIN_BUTTON_WIDTH = 300
        MIN_BUTTON_HEIGHT = 330
        self.setMinimumSize(MIN_BUTTON_WIDTH, MIN_BUTTON_HEIGHT)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setCursor(Qt.PointingHandCursor)

        content_widget = QWidget(self)
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 14, 0, 14)
        content_layout.setSpacing(0)

        symbol_label = QLabel(circled_number, self)
        symbol_label.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        symbol_label.setFont(QFont("Arial", 82, QFont.Bold))
        symbol_label.setStyleSheet("color: white; background: transparent;")
        content_layout.addWidget(symbol_label)

        text_label = QLabel(text, self)
        text_label.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        text_label.setFont(QFont("Arial", 20, QFont.Bold))
        text_label.setStyleSheet("color: white; background: transparent;")
        text_label.setWordWrap(True)
        content_layout.addWidget(text_label)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(content_widget)
        outer_layout.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)


class TransactionWindow(QDialog):
    def __init__(self, parent=None, permissions=None):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowCloseButtonHint)
        self.setWindowTitle("Select Transaction Type")
        self.setFixedSize(1200, 550)
        self.parent_window = parent
        self.permissions = permissions or {}

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(18)
        main_layout.setContentsMargins(16, 16, 16, 16)

        # Top bar
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Select Transaction Type")
        title.setFont(QFont("Arial", 18, QFont.Bold))
        title.setStyleSheet("color: #222;")
        top_bar.addWidget(title, alignment=Qt.AlignLeft | Qt.AlignVCenter)

        top_bar.addStretch()

        self.settings_btn = QPushButton("⚙")
        self.settings_btn.setFixedSize(44, 44)
        self.settings_btn.setCursor(Qt.PointingHandCursor)
        self.settings_btn.setToolTip("Settings / Main Menu")
        self.settings_btn.setStyleSheet("""
            QPushButton {
                background: #555;
                color: white;
                border: 2px solid #333;
                border-radius: 8px;
                font-size: 20px;
                font-weight: bold;
                padding: 0px;
            }
            QPushButton:pressed {
                background: #222;
            }
        """)
        self.settings_btn.clicked.connect(self.open_main_menu)
        top_bar.addWidget(self.settings_btn, 0, Qt.AlignRight | Qt.AlignTop)

        main_layout.addLayout(top_bar)

        # Buttons row
        buttons_frame = QFrame()
        buttons_layout = QHBoxLayout(buttons_frame)
        buttons_layout.setContentsMargins(0, 10, 0, 0)
        buttons_layout.setSpacing(40)
        buttons_layout.addStretch(1)

        self.first_load_btn = BigSymbolButton(
            circled_number="❶",
            text="1. First Weighing\nமுதல் எடை\nपहला वजन",
            bg_color="#2471A3",
            fg_color="white"
        )
        self.first_load_btn.clicked.connect(self.open_first_load)
        buttons_layout.addWidget(self.first_load_btn, stretch=2)

        buttons_layout.addStretch(1)

        self.second_load_btn = BigSymbolButton(
            circled_number="❷",
            text="2. SecondWeighing\nஇரண்டாம் எடை\nदूसरा लदान",
            bg_color="#F39C12",
            fg_color="white"
        )
        self.second_load_btn.clicked.connect(self.open_second_load)
        buttons_layout.addWidget(self.second_load_btn, stretch=2)

        buttons_layout.addStretch(1)

        self.third_load_btn = BigSymbolButton(
            circled_number="❸",
            text="3. Third Weighing\nமூன்றாம் எடை\nतीसरा लदान",
            bg_color="#27AE60",
            fg_color="white"
        )
        self.third_load_btn.clicked.connect(self.open_third_load)
        buttons_layout.addWidget(self.third_load_btn, stretch=2)

        buttons_layout.addStretch(1)

        main_layout.addWidget(buttons_frame, stretch=1)
        self.setLayout(main_layout)

    def open_main_menu(self):
        """
        Open a login dialog, validate user, determine admin flag, and open MainMenuForm.
        NOTE: Do not auto-open Administration or Configuration windows here — let MainMenuForm
        handle admin-only options so the operator can open them intentionally.
        """
        try:
            login = LoginWindow(self)
            if login.exec_() == QDialog.Accepted:
                username = login.get_username()

                is_admin = False
                db_problem = False
                try:
                    user_row = fetch_one(
                        "SELECT is_admin FROM usermanagement WHERE username = %s",
                        (username,)
                    )
                except Exception:
                    db_problem = True
                    user_row = None

                if user_row is not None and not db_problem:
                    try:
                        if isinstance(user_row, dict):
                            raw_val = user_row.get('is_admin', next(iter(user_row.values())))
                        elif isinstance(user_row, (list, tuple)):
                            raw_val = user_row[0] if len(user_row) > 0 else None
                        else:
                            raw_val = user_row

                        if isinstance(raw_val, bool):
                            is_admin = raw_val
                        elif isinstance(raw_val, int):
                            is_admin = bool(raw_val)
                        elif isinstance(raw_val, str):
                            is_admin = raw_val.lower() in ('t', 'true', '1', 'y', 'yes')
                        else:
                            is_admin = bool(raw_val)
                    except Exception:
                        is_admin = False
                else:
                    if db_problem:
                        QMessageBox.warning(self, "Warning", "Could not verify user role due to a database error. Proceeding as non-admin.")
                    else:
                        QMessageBox.warning(self, "Warning", "Could not verify user role. Proceeding as non-admin.")

                permissions = {'is_admin': is_admin, 'username': username}

                # Open only the Main Menu here. Admin can open Administration/Configuration via MainMenuForm.
                self.main_menu = MainMenuForm(
                    permissions=permissions,
                    transaction_window=self
                )
                self.main_menu.show()
                self.hide()

            else:
                # Login cancelled or failed; keep TransactionWindow visible
                pass

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Unable to open Main Menu / Login:\n{e}")
            self.show()

    def _open_child_window(self, window_class, *args):
        try:
            self.hide()
            self.child_window = window_class(*args, mode_window=self)
            self.child_window.show()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open window:\n{e}")
            try:
                self.show()
            except Exception:
                pass

    def open_first_load(self):
        self.hide()
        status_dialog = LoadStatusDialog(self)
        if status_dialog.exec_() == QDialog.Accepted:
            load_status = status_dialog.result
            vehicle_dialog = VehicleSelectionDialog(self)
            if vehicle_dialog.exec_() == QDialog.Accepted:
                vehicle_type = vehicle_dialog.result
                self._open_child_window(FirstLoadWindow, load_status, vehicle_type)
            else:
                self.show()
        else:
            self.show()

    def open_second_load(self):
        self.hide()
        try:
            self._open_child_window(SecondLoadWindow)
        except Exception:
            self.show()

    def open_third_load(self):
        self.hide()
        try:
            status_dialog = LoadStatusDialogThird(self)
            if status_dialog.exec_() == QDialog.Accepted:
                load_status = status_dialog.result
                vehicle_dialog = VehicleSelectionDialog(self)
                if vehicle_dialog.exec_() == QDialog.Accepted:
                    vehicle_type = vehicle_dialog.result
                    self._open_child_window(ThirdLoadWindow, load_status, vehicle_type)
                else:
                    self.show()
            else:
                self.show()
        except NameError:
            QMessageBox.critical(self, "Error", "LoadStatusDialog for third window not available.")
            self.show()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open third load flow:\n{e}")
            self.show()

    def closeEvent(self, event):
        if self.parent_window:
            try:
                self.parent_window.show()
            except Exception:
                pass
        super().closeEvent(event)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = TransactionWindow()
    win.show()
    sys.exit(app.exec_())
