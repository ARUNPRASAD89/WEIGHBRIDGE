from PyQt5.QtWidgets import (
    QWidget, QLabel, QComboBox, QPushButton, QLineEdit,
    QVBoxLayout, QHBoxLayout, QGroupBox, QGridLayout, QSizePolicy
)
from PyQt5.QtCore import Qt

class TicketDataEntryDesignerWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ticket Data Template")
        self.setFixedSize(520, 410)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(0)

        # --- Group Box Section (Field Name, Insert Text Box, Insert Combo) ---
        group_box = QGroupBox()
        group_box.setTitle("")
        group_box.setStyleSheet("QGroupBox { border: 2px solid black; border-radius: 5px; margin-top: 3px; }")
        group_box_layout = QVBoxLayout(group_box)
        group_box_layout.setSpacing(7)
        group_box_layout.setContentsMargins(10, 10, 10, 10)

        # Field Name row
        field_layout = QHBoxLayout()
        field_label = QLabel("Field Name:")
        field_label.setFixedWidth(75)
        field_combo = QComboBox()
        field_combo.setFixedWidth(160)
        field_layout.addWidget(field_label)
        field_layout.addWidget(field_combo)
        field_layout.addStretch(1)
        group_box_layout.addLayout(field_layout)

        # Insert Text Box & Insert Combo row
        insert_layout = QHBoxLayout()
        self.insert_text_btn = QPushButton("Insert Text Box")
        self.insert_combo_btn = QPushButton("Insert Combo")
        insert_layout.addWidget(self.insert_text_btn)
        insert_layout.addWidget(self.insert_combo_btn)
        insert_layout.addStretch(1)
        group_box_layout.addLayout(insert_layout)

        main_layout.addWidget(group_box)
        main_layout.addSpacing(24)

        # --- Fields Grid Section ---
        fields_grid = QGridLayout()
        fields_grid.setHorizontalSpacing(12)
        fields_grid.setVerticalSpacing(15)

        # Placeholder fields per image
        labels = ["STATUS", "EAMOUNT", "LAMOUNT", "TAMOUNT", "NetWeight1"]
        self.field_edits = []
        for i, label in enumerate(labels):
            l = QLabel(label)
            l.setFixedWidth(85)
            e = QLineEdit()
            e.setFixedWidth(160)
            self.field_edits.append(e)
            fields_grid.addWidget(l, i, 0)
            fields_grid.addWidget(e, i, 1)

        main_layout.addLayout(fields_grid)
        main_layout.addStretch(1)

        # --- Bottom Button Section ---
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.delete_btn = QPushButton("Delete")
        self.disable_btn = QPushButton("Disable")
        self.modify_btn = QPushButton("Modify DB")
        self.exit_btn = QPushButton("Exit")
        for btn in [self.delete_btn, self.disable_btn, self.modify_btn, self.exit_btn]:
            btn.setFixedWidth(100)
            btn_row.addWidget(btn)
        btn_row.addStretch(1)
        main_layout.addSpacing(8)
        main_layout.addLayout(btn_row)