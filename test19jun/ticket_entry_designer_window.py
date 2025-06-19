from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QLabel,
    QLineEdit, QComboBox, QTextEdit, QGroupBox, QSizePolicy, QFrame
)
from PyQt5.QtCore import Qt

class TicketEntryDesignerWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ticket Print Designer")
        self.setMinimumSize(680, 650)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(4)

        # --- Top Controls Layout ---
        top_layout = QHBoxLayout()
        # Left-side buttons
        left_btn_layout = QVBoxLayout()
        for text in ["Open", "Delete", "Save", "Help", "Exit"]:
            btn = QPushButton(text)
            btn.setFixedWidth(70)
            left_btn_layout.addWidget(btn)
        left_btn_layout.addStretch(1)
        top_layout.addLayout(left_btn_layout)

        # Field Spec
        field_spec = QGroupBox("Field Spec")
        field_spec_layout = QGridLayout(field_spec)
        field_spec_layout.addWidget(QLabel("Height"), 0, 0)
        field_spec_layout.addWidget(QLineEdit(), 0, 1)
        field_spec_layout.addWidget(QLabel("Width"), 0, 2)
        field_spec_layout.addWidget(QLineEdit(), 0, 3)
        field_spec_layout.addWidget(QLabel("Top"), 1, 0)
        field_spec_layout.addWidget(QLineEdit(), 1, 1)
        field_spec_layout.addWidget(QLabel("Left"), 1, 2)
        field_spec_layout.addWidget(QLineEdit(), 1, 3)
        top_layout.addWidget(field_spec)

        # Template Name and Status (center top)
        center_top_layout = QVBoxLayout()
        template_line = QHBoxLayout()
        template_line.addWidget(QLabel(), 1)
        template_name = QLabel("Template Name : TEST2")
        template_name.setStyleSheet("color: red; font-weight: bold")
        template_line.addWidget(template_name)
        center_top_layout.addLayout(template_line)
        status_label = QLabel("STATUS")
        status_label.setStyleSheet("color: red;")
        center_top_layout.addWidget(status_label)
        top_layout.addLayout(center_top_layout)

        # Controls group
        controls_group = QGroupBox("Controls")
        controls_layout = QGridLayout(controls_group)
        controls_layout.addWidget(QLabel("Field"), 0, 0)
        controls_layout.addWidget(QComboBox(), 0, 1)
        controls_layout.addWidget(QPushButton("..."), 0, 2)
        controls_layout.addWidget(QLabel("Formula"), 1, 0)
        controls_layout.addWidget(QLineEdit(), 1, 1, 1, 2)
        controls_layout.addWidget(QPushButton("Modify DB"), 2, 0)
        controls_layout.addWidget(QPushButton("Label"), 2, 1)
        controls_layout.addWidget(QPushButton("Insert Logo"), 3, 0, 1, 3)
        top_layout.addWidget(controls_group)

        # Ticket Spec group
        ticket_spec_group = QGroupBox("Ticket Spec")
        ticket_spec_layout = QGridLayout(ticket_spec_group)
        ticket_spec_layout.addWidget(QLabel("Height"), 0, 0)
        ticket_spec_layout.addWidget(QLineEdit(), 0, 1)
        ticket_spec_layout.addWidget(QLabel("Width"), 1, 0)
        ticket_spec_layout.addWidget(QLineEdit(), 1, 1)
        top_layout.addWidget(ticket_spec_group)

        # Alignment buttons
        align_layout = QVBoxLayout()
        align_layout.addWidget(QLabel("Alignment"))
        row = QHBoxLayout()
        for _ in range(3):
            row.addWidget(QPushButton())
        align_layout.addLayout(row)
        top_layout.addLayout(align_layout)

        main_layout.addLayout(top_layout)

        # --- Font Controls ---
        font_box = QGroupBox("Font")
        font_layout = QVBoxLayout(font_box)
        font_layout.addWidget(QLabel("Tahoma"))
        btn_row = QHBoxLayout()
        btn_row.addWidget(QPushButton("Change Font"))
        btn_row.addWidget(QPushButton("Underline"))
        btn_row.addWidget(QPushButton("Default"))
        font_layout.addLayout(btn_row)
        main_layout.addWidget(font_box)

        # --- Rulers (top and left) ---
        ruler_top = QHBoxLayout()
        for i in range(1, 6):
            lab = QLabel(str(i))
            lab.setAlignment(Qt.AlignCenter)
            lab.setFixedWidth(60)
            ruler_top.addWidget(lab)
        main_layout.addLayout(ruler_top)

        # --- Placeholder Design Area ---
        design_area = QTextEdit()
        design_area.setReadOnly(True)
        design_area.setPlaceholderText("Designer Canvas Area (placeholder)")
        design_area.setFixedHeight(400)
        main_layout.addWidget(design_area)

        # --- Optional: Add a left side ruler (for more realism) ---
        # Left ruler is not interactive, just for appearance
        # This is skipped for simplicity, but can be added with a QGridLayout if needed.