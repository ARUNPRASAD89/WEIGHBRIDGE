from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QLabel, QMessageBox,
    QComboBox, QDialog, QGroupBox, QGridLayout
)
from db_utils import fetch_all, execute_query
class VehicleMaster(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        if not self.perform_login():
            self.close()
            return
        self.init_ui()

    def perform_login(self):
        login_dialog = LoginDialog(self)
        while True:
            res = login_dialog.exec_()
            if res == QDialog.Accepted:
                username, password = login_dialog.get_credentials()
                if self.validate_login(username, password):
                    return True
                else:
                    QMessageBox.warning(self, "Login Failed", "Invalid username or password. Please try again.")
            else:
                return False

    def validate_login(self, username, password):

class VehicleLookupDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Search")
        self.setFixedSize(260, 140)
        main_layout = QVBoxLayout(self)

        group_box = QGroupBox("Look Up")
        grid = QGridLayout()

        # By Id
        grid.addWidget(QLabel("By Id"), 0, 0)
        self.by_id_combo = QComboBox()
        self.populate_by_id()
        grid.addWidget(self.by_id_combo, 0, 1)

        # By Name
        grid.addWidget(QLabel("By Name"), 1, 0)
        self.by_name_combo = QComboBox()
        self.populate_by_name()
        grid.addWidget(self.by_name_combo, 1, 1)

        group_box.setLayout(grid)
        main_layout.addWidget(group_box)

        # OK and Exit buttons
        btn_layout = QHBoxLayout()
        self.ok_btn = QPushButton("OK")
        self.exit_btn = QPushButton("Exit")
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.exit_btn)
        main_layout.addLayout(btn_layout)

        self.ok_btn.clicked.connect(self.accept)
        self.exit_btn.clicked.connect(self.reject)

        self.setLayout(main_layout)

        # Synchronize selection between id and name
        self.by_id_combo.currentIndexChanged.connect(self.sync_by_id)
        self.by_name_combo.currentIndexChanged.connect(self.sync_by_name)

    def populate_by_id(self):
        # Fill by_id_combo with all vehicle ids
        rows = fetch_all("SELECT vehicleid, vehiclenumber FROM vehiclemaster ORDER BY vehicleid")
        self.vehicle_rows = rows if rows else []
        self.by_id_combo.clear()
        for row in self.vehicle_rows:
            self.by_id_combo.addItem(str(row['vehicleid']))
    
    def populate_by_name(self):
        # Fill by_name_combo with all vehicle numbers
        rows = getattr(self, "vehicle_rows", None)
        if rows is None:
            rows = fetch_all("SELECT vehicleid, vehiclenumber FROM vehiclemaster ORDER BY vehicleid")
            self.vehicle_rows = rows if rows else []
        self.by_name_combo.clear()
        for row in self.vehicle_rows:
            self.by_name_combo.addItem(str(row['vehiclenumber']))

    def sync_by_id(self, idx):
        # When by_id changes, update by_name to match
        if idx >= 0 and hasattr(self, "vehicle_rows") and idx < len(self.vehicle_rows):
            self.by_name_combo.setCurrentIndex(idx)

    def sync_by_name(self, idx):
        # When by_name changes, update by_id to match
        if idx >= 0 and hasattr(self, "vehicle_rows") and idx < len(self.vehicle_rows):
            self.by_id_combo.setCurrentIndex(idx)

    def get_selected_vehicle(self):
        idx = self.by_id_combo.currentIndex()
        if idx < 0 or not hasattr(self, "vehicle_rows"):
            return None
        return self.vehicle_rows[idx]

class VehicleMaster(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QHBoxLayout()

        self.vehicle_id_combo = QComboBox()
        self.populate_vehicle_id_combo()

        # "..." button for lookup
        self.lookup_btn = QPushButton("...")
        self.lookup_btn.setFixedWidth(30)
        self.lookup_btn.clicked.connect(self.open_lookup_dialog)

        self.vehicle_number_edit = QLineEdit()
        self.vehicle_tareweight_edit = QLineEdit()

        form_layout.addWidget(QLabel("Vehicle ID:"))
        form_layout.addWidget(self.vehicle_id_combo)
        form_layout.addWidget(self.lookup_btn)
        form_layout.addWidget(QLabel("Vehicle Number:"))
        form_layout.addWidget(self.vehicle_number_edit)
        form_layout.addWidget(QLabel("Vehicle Tare Weight:"))
        form_layout.addWidget(self.vehicle_tareweight_edit)
        layout.addLayout(form_layout)

        self.add_btn = QPushButton("Add")
        self.add_btn.clicked.connect(self.add_vehicle)
        layout.addWidget(self.add_btn)

        self.setLayout(layout)

    def populate_vehicle_id_combo(self):
        try:
            rows = fetch_all("SELECT vehicleid FROM vehiclemaster ORDER BY vehicleid")
            self.vehicle_id_combo.clear()
            if rows:
                for row in rows:
                    self.vehicle_id_combo.addItem(str(row['vehicleid']))
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Could not load vehicle IDs:\n{e}")

    def open_lookup_dialog(self):
        dialog = VehicleLookupDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            vehicle = dialog.get_selected_vehicle()
            if vehicle:
                # Set fields for editing
                self.vehicle_id_combo.setCurrentText(str(vehicle['vehicleid']))
                self.vehicle_number_edit.setText(vehicle['vehiclenumber'])
                tare_row = fetch_all(
                    "SELECT vehicletareweight FROM vehiclemaster WHERE vehicleid = %s",
                    (vehicle['vehicleid'],)
                )
                tare_value = tare_row[0]['vehicletareweight'] if tare_row and 'vehicletareweight' in tare_row[0] else ""
                self.vehicle_tareweight_edit.setText(str(tare_value) if tare_value is not None else "")

    def add_vehicle(self):
        vehicle_id = self.vehicle_id_combo.currentText()
        vehicle_number = self.vehicle_number_edit.text().strip()
        vehicle_tareweight = self.vehicle_tareweight_edit.text().strip()

        if not vehicle_number:
            QMessageBox.warning(self, "Validation Error", "Vehicle Number is required!")
            return

        query = """
            UPDATE vehiclemaster
            SET vehiclenumber = %s,
                vehicletareweight = %s
            WHERE vehicleid = %s
        """
        params = (vehicle_number, vehicle_tareweight if vehicle_tareweight else None, vehicle_id)

        try:
            execute_query(query, params)
            QMessageBox.information(self, "Success", "Vehicle updated successfully!")
            self.populate_vehicle_id_combo()
            self.vehicle_number_edit.clear()
            self.vehicle_tareweight_edit.clear()
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Error updating vehicle:\n{e}")
