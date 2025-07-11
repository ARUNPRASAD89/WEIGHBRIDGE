from PyQt5.QtWidgets import (
    QWidget, QLabel, QComboBox, QPushButton, QLineEdit,
    QVBoxLayout, QHBoxLayout, QGroupBox, QGridLayout, QApplication
)
from PyQt5.QtCore import Qt, pyqtSignal
from db_utils import fetch_all
import sys

MANDATORY_FIELDS = [
    "TicketNumber", "VehicleNumber", "Date", "Time", "EmptyWeight",
    "LoadedWeight", "EmptyWeightDate", "EmptyWeightTime", "LoadWeightDate",
    "LoadWeightTime", "NetWeight", "Pending", "Closed", "Exported", "Shift",
    "Materialname", "SupplierName", "State"
]

class TicketDataEntryDesignerWindow(QWidget):
    custom_fields_updated = pyqtSignal(list)  # Emits list of (field_name, widget) tuples

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ticket Data Template")
        self.setFixedSize(520, 410)
        self.custom_fields = []  # List of (field_name, widget)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(0)

        # --- Group Box Section ---
        group_box = QGroupBox()
        group_box.setStyleSheet("QGroupBox { border: 2px solid black; border-radius: 5px; margin-top: 3px; }")
        group_box_layout = QVBoxLayout(group_box)
        group_box_layout.setSpacing(7)
        group_box_layout.setContentsMargins(10, 10, 10, 10)

        # Field Name row
        field_layout = QHBoxLayout()
        self.field_label = QLabel("Field Name:")
        self.field_label.setFixedWidth(75)
        self.field_combo = QComboBox()
        self.field_combo.setEditable(True)
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

        # --- Fields Grid Section (dynamic) ---
        self.fields_grid = QGridLayout()
        self.fields_grid.setHorizontalSpacing(12)
        self.fields_grid.setVerticalSpacing(15)
        main_layout.addLayout(self.fields_grid)
        main_layout.addStretch(1)

        # --- Bottom Button Section ---
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self.handle_delete_selected_field)
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.reload_field_combo)
        self.exit_btn = QPushButton("Exit")
        self.exit_btn.clicked.connect(self.handle_exit)  # <--- connect it here
        
        for btn in [self.delete_btn, self.refresh_btn, self.exit_btn]:
            btn.setFixedWidth(100)
            btn_row.addWidget(btn)
        btn_row.addStretch(1)
        main_layout.addSpacing(8)
        main_layout.addLayout(btn_row)

        self.insert_text_btn.clicked.connect(self.handle_insert_text_box)
        self.insert_combo_btn.clicked.connect(self.handle_insert_combo_box)

        #self.reload_field_combo()

    def get_all_custom_fields(self):
        sql = """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'tickets' AND table_schema = 'public'
            ORDER BY ordinal_position
        """
        try:
            rows = fetch_all(sql)
            all_fields = [r["column_name"] for r in rows]
            return [f for f in all_fields if f not in MANDATORY_FIELDS]
        except Exception as e:
            print("Error during fetch_all:", e)
            return []

    def reload_field_combo(self):
        # Always reflect actual DB columns minus mandatory fields minus already added custom fields
        available = self.get_all_custom_fields()
        already_added = [f[0] for f in self.custom_fields]
        to_show = [f for f in available if f not in already_added]
        current = self.field_combo.currentText()
        self.field_combo.blockSignals(True)
        self.field_combo.clear()
        self.field_combo.addItems(to_show)
        if current:
            self.field_combo.setEditText(current)
        self.field_combo.blockSignals(False)

    def handle_insert_text_box(self):
        field_name = self.field_combo.currentText().strip()
        if not field_name:
            return
        if field_name not in self.get_all_custom_fields():
            return
        if any(name == field_name for name, _ in self.custom_fields):
            return
        edit = QLineEdit()
        self.custom_fields.append((field_name, edit))
        self.refresh_fields_grid()
        self.emit_custom_fields()
        self.reload_field_combo()

    def handle_insert_combo_box(self):
        field_name = self.field_combo.currentText().strip()
        if not field_name:
            return
        if field_name not in self.get_all_custom_fields():
            return
        if any(name == field_name for name, _ in self.custom_fields):
            return
        combo = QComboBox()
        combo.setEditable(True)
        combo.addItems(["Option 1", "Option 2"])
        self.custom_fields.append((field_name, combo))
        self.refresh_fields_grid()
        self.emit_custom_fields()
        self.reload_field_combo()

    def handle_delete_selected_field(self):
        field_name = self.field_combo.currentText().strip()
        before = len(self.custom_fields)
        self.custom_fields = [(name, widget) for name, widget in self.custom_fields if name != field_name]
        if before != len(self.custom_fields):
            self.refresh_fields_grid()
            self.emit_custom_fields()
            self.reload_field_combo()

    def refresh_fields_grid(self):
        while self.fields_grid.count():
            item = self.fields_grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        for i, (field_name, widget) in enumerate(self.custom_fields):
            lbl = QLabel(field_name)
            lbl.setFixedWidth(85)
            widget.setFixedWidth(160)
            self.fields_grid.addWidget(lbl, i, 0)
            self.fields_grid.addWidget(widget, i, 1)

    def emit_custom_fields(self):
        self.custom_fields_updated.emit(self.custom_fields)
    def handle_exit(self):
        self.close()
        if self.parent():
            self.parent().show()
if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = TicketDataEntryDesignerWindow()
    w.show()
    sys.exit(app.exec_())            
