from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QApplication, QSpacerItem, QSizePolicy
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

class MainMenuForm(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("WeighBRIDGEMANUAL-Main Menu")
        self.setFixedSize(600, 500)
        self.setStyleSheet("background-color: #e8f2f4;")

        # === MAIN LAYOUT ===
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # === Banner Section (Logo and Slogan) ===
        banner = QLabel()
        banner.setAlignment(Qt.AlignCenter)
        banner.setStyleSheet("background: white;")
        banner.setFixedHeight(170)
        banner.setText(
            "<div style='padding:16px'><img src='truck_image.png' height='90'/><br>"
            "<span style='font-size:15pt; font-weight:bold;'>Engineered to take Loads off your mind</span></div>"
        )
        main_layout.addWidget(banner)

        # === Center Row: Button Panel ===
        center_row = QHBoxLayout()
        center_row.addSpacerItem(QSpacerItem(60, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))

        button_panel = QVBoxLayout()
        button_panel.setSpacing(18)
        btn_font = QFont("Arial", 13, QFont.Bold)
        btn_w, btn_h = 180, 48  # Rectangular but balanced

        # Transactions
        self.transactions_btn = QPushButton("Transactions")
        self.transactions_btn.setFont(btn_font)
        self.transactions_btn.setFixedSize(btn_w, btn_h)
        button_panel.addWidget(self.transactions_btn)

        # Reports
        self.reports_btn = QPushButton("Reports")
        self.reports_btn.setFont(btn_font)
        self.reports_btn.setFixedSize(btn_w, btn_h)
        button_panel.addWidget(self.reports_btn)

        # Administration
        self.administration_btn = QPushButton("Administration")
        self.administration_btn.setFont(btn_font)
        self.administration_btn.setFixedSize(btn_w, btn_h)
        button_panel.addWidget(self.administration_btn)

        # Configuration
        self.configuration_btn = QPushButton("Configuration")
        self.configuration_btn.setFont(btn_font)
        self.configuration_btn.setFixedSize(btn_w, btn_h)
        button_panel.addWidget(self.configuration_btn)

        # Help
        self.help_btn = QPushButton("Help")
        self.help_btn.setFont(btn_font)
        self.help_btn.setFixedSize(btn_w, btn_h)
        button_panel.addWidget(self.help_btn)

        # Exit
        self.exit_btn = QPushButton("Exit")
        self.exit_btn.setFont(btn_font)
        self.exit_btn.setFixedSize(btn_w, btn_h)
        button_panel.addWidget(self.exit_btn)

        # Add vertical stretch to center the button group
        button_panel.addStretch(1)
        center_row.addLayout(button_panel)
        center_row.addSpacerItem(QSpacerItem(60, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        main_layout.addLayout(center_row)

        # === User ID Label at Bottom Right ===
        user_label = QLabel("User ID: ADMIN")
        user_label.setFont(QFont("Arial", 11, QFont.Bold))
        user_label.setStyleSheet("color: darkgreen; padding: 8px;")
        user_label.setAlignment(Qt.AlignRight)
        main_layout.addStretch(1)
        main_layout.addWidget(user_label, alignment=Qt.AlignRight | Qt.AlignBottom)

        # Connect exit
        self.exit_btn.clicked.connect(self.close)

# For standalone testing
if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    w = MainMenuForm()
    w.show()
    sys.exit(app.exec_())