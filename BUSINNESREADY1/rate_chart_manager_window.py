from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QGridLayout, QLabel, QLineEdit, 
    QPushButton, QComboBox, QMessageBox, QSpacerItem, QSizePolicy
)
from PyQt5.QtGui import QFont, QDoubleValidator
from PyQt5.QtCore import Qt
import rate_calculator
import db_utils

class RateChartManagerWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Rate Chart Manager")
        self.setMinimumSize(500, 450)
        self.parent_window = parent

        # --- UI ELEMENTS ---
        self.vehicle_combo = QComboBox()
        self.vehicle_combo.setEditable(True)
        self.vehicle_combo.currentTextChanged.connect(self.on_vehicle_selected)

        self.rate_fields = {}
        # Map the UI label to the database column name
        self.db_field_map = {
            "Vehicle Name": "vehiclename",
            "Empty Rate": "empty_rate", 
            "Load Base Rate": "load_base_rate",
            "Above 20-Ton Rate": "above20ton_rate", 
            "Above 30-Ton Rate": "above30ton_rate",
            "Above 40-Ton Rate": "above40ton_rate", 
            "Above 50-Ton Rate": "above50ton_rate",
            "Above 60-Ton Rate": "above60ton_rate", 
            "Increase %": "increase_percentage",
            "Decrease %": "decrease_percentage"
        }

        # --- LAYOUT ---
        main_layout = QVBoxLayout(self)
        grid_layout = QGridLayout()
        grid_layout.setSpacing(10)

        grid_layout.addWidget(QLabel("Vehicle Name:"), 0, 0)
        grid_layout.addWidget(self.vehicle_combo, 0, 1)

        validator = QDoubleValidator(0.00, 999999.99, 2)
        # Create fields based on the map, skipping vehiclename
        for i, label_text in enumerate(list(self.db_field_map.keys())[1:], 1):
            db_field = self.db_field_map[label_text]
            label = QLabel(f"{label_text}:")
            line_edit = QLineEdit()
            line_edit.setValidator(validator)
            line_edit.setPlaceholderText("0.00")
            grid_layout.addWidget(label, i, 0)
            grid_layout.addWidget(line_edit, i, 1)
            self.rate_fields[db_field] = line_edit

        # --- BUTTONS ---
        self.save_button = QPushButton("Save Rate")
        self.save_button.clicked.connect(self.save_rate)
        self.clear_button = QPushButton("Clear / New")
        self.clear_button.clicked.connect(self.clear_form)
        self.exit_button = QPushButton("Exit")
        self.exit_button.clicked.connect(self.close)

        main_layout.addLayout(grid_layout)
        main_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        main_layout.addWidget(self.save_button)
        main_layout.addWidget(self.clear_button)
        main_layout.addWidget(self.exit_button)
        
        self.load_vehicles()

    def load_vehicles(self):
        """Load existing vehicle rates into the combo box."""
        self.vehicle_combo.blockSignals(True)
        self.vehicle_combo.clear()
        self.vehicle_combo.addItem("") # Add a blank item for new entries
        try:
            self.all_rates = rate_calculator.get_all_vehicle_rates()
            for rate in self.all_rates:
                self.vehicle_combo.addItem(rate['vehiclename'])
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Could not load rates: {e}")
        self.vehicle_combo.blockSignals(False)
        self.clear_form()

    def on_vehicle_selected(self, vehicle_name):
        """Populate the form when a vehicle is selected from the list."""
        if not vehicle_name:
            self.clear_form(clear_combo=False)
            return

        for rate in self.all_rates:
            if rate['vehiclename'] == vehicle_name:
                for db_field, widget in self.rate_fields.items():
                    value = rate.get(db_field, 0.0)
                    widget.setText(str(value) if value is not None else "0.00")
                return

    def save_rate(self):
        """Collect data from the form and save it to the database."""
        vehicle_name = self.vehicle_combo.currentText().strip()
        if not vehicle_name:
            QMessageBox.warning(self, "Input Error", "Vehicle Name cannot be empty.")
            return

        rate_data = {'vehiclename': vehicle_name}
        try:
            for db_field, widget in self.rate_fields.items():
                text_value = widget.text().strip()
                rate_data[db_field] = float(text_value) if text_value else 0.0
        except ValueError:
            QMessageBox.warning(self, "Input Error", "All rate fields must be valid numbers.")
            return

        try:
            rate_calculator.add_or_update_rate(rate_data)
            QMessageBox.information(self, "Success", f"Rate for '{vehicle_name}' saved successfully.")
            self.load_vehicles() # Reload to reflect changes
            self.vehicle_combo.setCurrentText(vehicle_name)
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Could not save the rate: {e}")

    def clear_form(self, clear_combo=True):
        """Clears all input fields."""
        if clear_combo:
            self.vehicle_combo.setCurrentIndex(0)
        for widget in self.rate_fields.values():
            widget.clear()

    def close(self):
        """Overrides close to show the parent window."""
        if self.parent_window:
            self.parent_window.show()
        super().close()