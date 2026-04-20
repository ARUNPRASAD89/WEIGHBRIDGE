from PyQt5.QtWidgets import (
    QWidget, QLabel, QComboBox, QPushButton, QLineEdit,
    QVBoxLayout, QHBoxLayout, QGroupBox, QGridLayout, QSizePolicy, QDialog, QMessageBox
)
from PyQt5.QtCore import Qt

from db_utils import fetch_all, fetch_one, execute_query

class TicketDataEntryDesignerWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
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
        self.field_label = QLabel("Field Name:")
        self.field_label.setFixedWidth(75)
        self.field_combo = QComboBox()
        self.field_combo.setFixedWidth(160)
        field_layout.addWidget(self.field_label)
        field_layout.addWidget(self.field_combo)
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
        self.fields_grid = QGridLayout()
        self.fields_grid.setHorizontalSpacing(12)
        self.fields_grid.setVerticalSpacing(15)

        self.field_widgets = {}  # {controlname: (label, widget)}

        main_layout.addLayout(self.fields_grid)
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

        # Connections
        self.insert_text_btn.clicked.connect(lambda: self.insert_field("TextBox"))
        self.insert_combo_btn.clicked.connect(lambda: self.insert_field("Combo"))
        self.delete_btn.clicked.connect(self.delete_field)
        self.modify_btn.clicked.connect(self.open_database_designer)
        self.exit_btn.clicked.connect(self.return_to_administration)

        self.load_field_combo()
        self.load_template_fields()

    def load_field_combo(self):
        # Load fields from tablemaster with mandatory = False
        self.field_combo.clear()
        rows = fetch_all(
            "SELECT fieldname FROM tablemaster WHERE tablename='Tickets' AND (mandatory = FALSE OR mandatory IS NULL) ORDER BY id"
        )
        for r in rows:
            self.field_combo.addItem(r["fieldname"])

    def load_template_fields(self):
        # Load fields from ticketdatatemplate and add to grid
        for i in reversed(range(self.fields_grid.count())):
            widget = self.fields_grid.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        self.field_widgets.clear()

        rows = fetch_all("SELECT * FROM ticketdatatemplate WHERE controltable='Tickets' ORDER BY controlarrid")
        for idx, row in enumerate(rows):
            label = QLabel(row["controlcaption"])
            label.setFixedWidth(120)
            if row["controltype"] == "Combo":
                widget = QComboBox()
                widget.setFixedWidth(150)
                # For Combo, you may want to load values from another table if needed
            else:
                widget = QLineEdit()
                widget.setFixedWidth(150)
            self.fields_grid.addWidget(label, idx, 0)
            self.fields_grid.addWidget(widget, idx, 1)
            self.field_widgets[row["controlname"]] = (label, widget)

    def insert_field(self, control_type):
        fieldname = self.field_combo.currentText()
        if not fieldname:
            QMessageBox.warning(self, "Input Error", "Select a field name.")
            return
        # Fetch caption from tablemaster
        row = fetch_one(
            "SELECT fieldcaption FROM tablemaster WHERE tablename='Tickets' AND fieldname=%s",
            (fieldname,)
        )
        caption = row["fieldcaption"] if row else fieldname

        # Determine next controlarrid
        arrid_row = fetch_one(
            "SELECT COALESCE(MAX(controlarrid), 0) + 1 AS nextid FROM ticketdatatemplate WHERE controltable='Tickets'"
        )
        next_arrid = arrid_row["nextid"] if arrid_row else 1

        # Insert into ticketdatatemplate
        try:
            # Check if controlname already exists
            exists = fetch_one(
                "SELECT 1 FROM ticketdatatemplate WHERE controltable='Tickets' AND controlname=%s",
                (fieldname,)
            )
            if exists:
                QMessageBox.warning(self, "Exists", "Field already in form. Delete first to re-add.")
                return
            execute_query(
                """INSERT INTO ticketdatatemplate
                (controlname, controlcaption, controltype, controlarrid, controltable)
                VALUES (%s, %s, %s, %s, %s)""",
                (fieldname, caption, control_type, next_arrid, "Tickets")
            )
            self.load_template_fields()
            QMessageBox.information(self, "Success", f"Field '{fieldname}' inserted as {control_type}.")
        except Exception as e:
            QMessageBox.warning(self, "DB Error", str(e))

    def delete_field(self):
        fieldname = self.field_combo.currentText()
        if not fieldname:
            QMessageBox.warning(self, "Input Error", "Select a field name to delete.")
            return
        try:
            execute_query(
                "DELETE FROM ticketdatatemplate WHERE controltable='Tickets' AND controlname=%s",
                (fieldname,)
            )
            self.load_template_fields()
            QMessageBox.information(self, "Success", f"Field '{fieldname}' deleted from form and template table.")
        except Exception as e:
            QMessageBox.warning(self, "DB Error", str(e))

    def open_database_designer(self):
        # Open DatabaseDesigner window for DB modification
        from database_designer import DatabaseDesigner
        dlg = DatabaseDesigner(parent=self)
        dlg.exec_()
        self.load_field_combo()
        self.load_template_fields()

    def return_to_administration(self):
        self.hide()
        parent = self.parent()
        if parent:
            parent.show()
