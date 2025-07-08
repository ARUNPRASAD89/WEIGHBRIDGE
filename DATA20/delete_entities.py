from PyQt5.QtWidgets import (
    QWidget, QLabel, QRadioButton, QButtonGroup, QComboBox, QLineEdit, QPushButton,
    QHBoxLayout, QVBoxLayout, QGroupBox, QListWidget, QCheckBox, QTextEdit
)

class DeleteEntities(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Delete Entities")
        self.setFixedSize(600, 480)

        main_layout = QVBoxLayout(self)

        # Top: Table selection and criteria
        table_criteria_layout = QHBoxLayout()

        # Table Selection
        table_group = QGroupBox("Select Table")
        table_layout = QVBoxLayout()
        rb_material = QRadioButton("Material")
        rb_ticket = QRadioButton("Ticket")
        rb_supplier = QRadioButton("Supplier")
        rb_vehicle = QRadioButton("Vehicle")
        rb_material.setChecked(True)
        table_layout.addWidget(rb_material)
        table_layout.addWidget(rb_ticket)
        table_layout.addWidget(rb_supplier)
        table_layout.addWidget(rb_vehicle)
        table_group.setLayout(table_layout)
        table_criteria_layout.addWidget(table_group)

        # Criteria Selection
        criteria_group = QGroupBox("Criteria")
        criteria_layout = QVBoxLayout()
        rb_all = QRadioButton("All")
        rb_all.setChecked(True)
        rb_where = QRadioButton("Where")
        where_layout = QHBoxLayout()
        where_layout.addWidget(QLineEdit())
        where_layout.addWidget(QComboBox())
        where_layout.addWidget(QLineEdit())
        rb_from = QRadioButton("From")
        from_layout = QHBoxLayout()
        from_layout.addWidget(QLineEdit())
        from_layout.addWidget(QLabel("To"))
        from_layout.addWidget(QLineEdit())
        criteria_layout.addWidget(rb_all)
        criteria_layout.addWidget(rb_where)
        criteria_layout.addLayout(where_layout)
        criteria_layout.addWidget(rb_from)
        criteria_layout.addLayout(from_layout)
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(QPushButton("AND"))
        btn_layout.addWidget(QPushButton("OR"))
        btn_layout.addWidget(QPushButton("Build"))
        btn_layout.addWidget(QPushButton("Clear"))
        criteria_layout.addLayout(btn_layout)
        criteria_group.setLayout(criteria_layout)
        table_criteria_layout.addWidget(criteria_group)

        main_layout.addLayout(table_criteria_layout)

        # Select Based On
        based_on_layout = QHBoxLayout()
        based_on_layout.addWidget(QLabel("Select Based On"))
        based_on_layout.addWidget(QLineEdit())
        based_on_layout.addWidget(QComboBox())
        main_layout.addLayout(based_on_layout)

        # Select records for deletion
        main_layout.addWidget(QLabel("Select Record(s) for Deletion"))
        record_list = QListWidget()
        record_list.setMinimumHeight(180)
        main_layout.addWidget(record_list)

        # Bottom: Buttons
        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(QCheckBox("Select All"))
        bottom_layout.addStretch()
        bottom_layout.addWidget(QLabel('Press "Ctrl" key while selecting multiple records for deletion'))
        bottom_layout.addWidget(QPushButton("Delete"))
        bottom_layout.addWidget(QPushButton("Exit"))
        main_layout.addLayout(bottom_layout)