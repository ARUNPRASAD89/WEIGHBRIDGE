from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSpacerItem, QSizePolicy
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
from ticket_window import TicketWindow
from report_window_form import ReportWindowForm
from administration_window import AdministrationWindow
from configuration_window import ConfigurationWindow
from help_window import HelpWindow

class MainMenuForm(QWidget):
    def __init__(self, mode_window=None):
        super().__init__()
        self.mode_window = mode_window  # For returning to mode window if needed
        self.setWindowTitle("WeighBRIDGEMANUAL-Main Menu")
        self.setFixedSize(600, 500)
        self.setStyleSheet("background-color: #e8f2f4;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        banner = QLabel()
        banner.setAlignment(Qt.AlignCenter)
        banner.setStyleSheet("background: white;")
        banner.setFixedHeight(170)
        banner.setText(
            "<div style='padding:16px'><img src='truck_image.png' height='90'/><br>"
            "<span style='font-size:15pt; font-weight:bold;'>Engineered to take Loads off your mind</span></div>"
        )
        main_layout.addWidget(banner)

        center_row = QHBoxLayout()
        center_row.addSpacerItem(QSpacerItem(60, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))

        button_panel = QVBoxLayout()
        button_panel.setSpacing(18)
        btn_font = QFont("Arial", 13, QFont.Bold)
        btn_w, btn_h = 180, 48

        self.transactions_btn = QPushButton("Transactions")
        self.transactions_btn.setFont(btn_font)
        self.transactions_btn.setFixedSize(btn_w, btn_h)
        self.transactions_btn.clicked.connect(self.open_ticket_window)
        button_panel.addWidget(self.transactions_btn)

        self.reports_btn = QPushButton("Reports")
        self.reports_btn.setFont(btn_font)
        self.reports_btn.setFixedSize(btn_w, btn_h)
        self.reports_btn.clicked.connect(self.open_report_window)
        button_panel.addWidget(self.reports_btn)

        self.administration_btn = QPushButton("Administration")
        self.administration_btn.setFont(btn_font)
        self.administration_btn.setFixedSize(btn_w, btn_h)
        self.administration_btn.clicked.connect(self.open_administration_window)
        button_panel.addWidget(self.administration_btn)

        self.configuration_btn = QPushButton("Configuration")
        self.configuration_btn.setFont(btn_font)
        self.configuration_btn.setFixedSize(btn_w, btn_h)
        self.configuration_btn.clicked.connect(self.open_configuration_window)
        button_panel.addWidget(self.configuration_btn)

        self.help_btn = QPushButton("Help")
        self.help_btn.setFont(btn_font)
        self.help_btn.setFixedSize(btn_w, btn_h)
        self.help_btn.clicked.connect(self.open_help_window)
        button_panel.addWidget(self.help_btn)

        self.exit_btn = QPushButton("Exit")
        self.exit_btn.setFont(btn_font)
        self.exit_btn.setFixedSize(btn_w, btn_h)
        self.exit_btn.clicked.connect(self.return_to_mode_window)
        button_panel.addWidget(self.exit_btn)

        button_panel.addStretch(1)
        center_row.addLayout(button_panel)
        center_row.addSpacerItem(QSpacerItem(60, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        main_layout.addLayout(center_row)

        user_label = QLabel("User ID: ADMIN")
        user_label.setFont(QFont("Arial", 11, QFont.Bold))
        user_label.setStyleSheet("color: darkgreen; padding: 8px;")
        user_label.setAlignment(Qt.AlignRight)
        main_layout.addStretch(1)
        main_layout.addWidget(user_label, alignment=Qt.AlignRight | Qt.AlignBottom)

    def open_ticket_window(self):
        self.hide()
        self.ticket_win = TicketWindow()
        self.ticket_win.show()

    def open_report_window(self):
        self.hide()
        self.report_win = ReportWindowForm()
        self.report_win.show()

    def open_administration_window(self):
        self.hide()
        self.admin_win = AdministrationWindow()
        self.admin_win.show()

    def open_configuration_window(self):
        self.hide()
        self.config_win = ConfigurationWindow()
        self.config_win.show()

    def open_help_window(self):
        self.hide()
        self.help_win = HelpWindow()
        self.help_win.show()

    def return_to_mode_window(self):
        self.hide()
        if self.mode_window:
            self.mode_window.show()