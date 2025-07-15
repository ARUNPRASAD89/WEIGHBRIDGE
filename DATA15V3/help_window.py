from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QTextEdit, QScrollArea, QDialog
)
from PyQt5.QtCore import Qt

class HelpWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Help")
        self.setFixedSize(600, 400)
        layout = QVBoxLayout(self)
        label = QLabel("Help Window")
        layout.addWidget(label)
        self.exit_btn = QPushButton("Exit")
        layout.addWidget(self.exit_btn)
        self.exit_btn.clicked.connect(self.return_to_administration)


        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)

        # Title
        title = QLabel("Application Help")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 18pt; font-weight: bold;")
        main_layout.addWidget(title)

        # Scrollable help text
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        help_content = QTextEdit()
        help_content.setReadOnly(True)
        help_content.setPlainText(
            "Welcome to the Help Window!\n\n"
            "Here you can find information on how to use the application:\n"
            "\n"
            "• Use the Administration menu to configure tickets, templates, users, and more.\n"
            "• Each designer window (Ticket Data Entry, Print Designer, etc.) allows you to design and save templates for your weighbridge tickets.\n"
            "• The Database Designer allows you to review and edit database tables.\n"
            "• Use the User Manager to add, edit, or remove users and set permissions.\n"
            "• Company Details lets you change your company information.\n"
            "• The Formula Editor lets you define custom calculations.\n"
            "\n"
            "For further assistance, please refer to the official documentation or contact support."
        )
        scroll.setWidget(help_content)
        main_layout.addWidget(scroll, 1)

        # Bottom buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.exit_btn = QPushButton("Exit")
        btn_row.addWidget(self.exit_btn)
        main_layout.addLayout(btn_row)

        # Connect Exit to return to parent window
        self.exit_btn.clicked.connect(self.return_to_administration)

    def return_to_administration(self):
        self.hide()
        parent = self.parent()
        if parent:
            parent.show()
