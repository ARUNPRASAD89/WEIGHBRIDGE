from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QHBoxLayout, QVBoxLayout, QGroupBox, QComboBox, QRadioButton, QButtonGroup, QGridLayout
)
from PyQt5.QtCore import Qt

class CommPortSettings(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Comm Port Settings")
        self.setFixedSize(430, 285)
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(2)

        # Title
        title = QLabel("<b><span style='font-size:18px'>Comm Port Settings</span></b>")
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        # Main group layouts
        prop_group = QGroupBox("General Properties")
        prop_layout = QGridLayout()
        prop_layout.setVerticalSpacing(5)
        prop_layout.setHorizontalSpacing(10)

        # Comm Port
        prop_layout.addWidget(QLabel("Comm Port"), 0, 0)
        prop_layout.addWidget(QLineEdit(), 0, 1)
        # Parity Replace
        prop_layout.addWidget(QLabel("Parity Replace"), 1, 0)
        prop_layout.addWidget(QLineEdit(), 1, 1)
        # Input Length
        prop_layout.addWidget(QLabel("Input Length"), 2, 0)
        prop_layout.addWidget(QLineEdit(), 2, 1)
        # Handshaking
        prop_layout.addWidget(QLabel("Handshaking"), 3, 0)
        hand_combo = QComboBox()
        hand_combo.addItems(["None"])  # Placeholder
        prop_layout.addWidget(hand_combo, 3, 1)
        # DTR Enable
        dtr_label = QLabel("DTR Enable")
        prop_layout.addWidget(dtr_label, 4, 0)
        dtr_true = QRadioButton("True")
        dtr_false = QRadioButton("False")
        dtr_false.setChecked(True)
        dtr_group = QButtonGroup()
        dtr_group.addButton(dtr_true)
        dtr_group.addButton(dtr_false)
        dtr_hbox = QHBoxLayout()
        dtr_hbox.addWidget(dtr_true)
        dtr_hbox.addWidget(dtr_false)
        prop_layout.addLayout(dtr_hbox, 4, 1)
        prop_group.setLayout(prop_layout)

        # Settings group
        set_group = QGroupBox("Settings")
        set_layout = QGridLayout()
        set_layout.setVerticalSpacing(5)
        set_layout.setHorizontalSpacing(10)
        # Baud Rate
        set_layout.addWidget(QLabel("Baud Rate"), 0, 0)
        baud_combo = QComboBox()
        baud_combo.addItems(["9600"])  # Placeholder
        set_layout.addWidget(baud_combo, 0, 1)
        # Parity
        set_layout.addWidget(QLabel("Parity"), 1, 0)
        parity_combo = QComboBox()
        parity_combo.addItems(["None"])  # Placeholder
        set_layout.addWidget(parity_combo, 1, 1)
        # Data Bits
        set_layout.addWidget(QLabel("Data Bits"), 2, 0)
        databits_combo = QComboBox()
        databits_combo.addItems(["7", "8"])  # Placeholder
        set_layout.addWidget(databits_combo, 2, 1)
        # Stop Bit
        set_layout.addWidget(QLabel("Stop Bit"), 3, 0)
        stopbit_combo = QComboBox()
        stopbit_combo.addItems(["1", "2"])  # Placeholder
        set_layout.addWidget(stopbit_combo, 3, 1)
        set_group.setLayout(set_layout)

        # Two columns side by side
        cols = QHBoxLayout()
        cols.addWidget(prop_group)
        cols.addWidget(set_group)
        main_layout.addLayout(cols)

        # Diagnose button
        diag_layout = QHBoxLayout()
        diag_layout.addStretch()
        diag_layout.addWidget(QPushButton("Diagnoise"))
        main_layout.addLayout(diag_layout)

        # Bottom buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(QPushButton("Change"))
        btn_layout.addWidget(QPushButton("Exit"))
        main_layout.addLayout(btn_layout)