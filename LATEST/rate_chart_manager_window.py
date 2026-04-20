import os
import shutil
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QGridLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QMessageBox, QSpacerItem, QSizePolicy,
    QFileDialog, QHBoxLayout, QFrame, QApplication
)
from PyQt5.QtGui import QFont, QDoubleValidator, QPixmap, QIcon
from PyQt5.QtCore import Qt, QSize
import rate_calculator
from resource_helpers import resolve_resource, save_user_file, user_folder, debug_candidates


class RateChartManagerWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Rate Chart Manager")
        self.setMinimumSize(600, 500)
        self.parent_window = parent
        self.selected_image_path = None
        self.all_rates = []

        # Use a user-writable image folder (e.g. %LOCALAPPDATA%\Weighbridge\vehicle_images)
        self.image_folder = user_folder('vehicle_images')

        # --- UI ELEMENTS ---
        self.vehicle_combo = QComboBox()
        self.vehicle_combo.setEditable(True)
        self.vehicle_combo.currentTextChanged.connect(self.on_vehicle_selected)

        self.image_preview_label = QLabel("No Image")
        self.image_preview_label.setFixedSize(150, 150)
        self.image_preview_label.setAlignment(Qt.AlignCenter)
        self.image_preview_label.setFrameShape(QFrame.StyledPanel)
        self.image_preview_label.setStyleSheet("border: 1px solid #bdc3c7; border-radius: 4px; background-color: white;")

        self.rate_fields = {}
        self.db_field_map = {
            "Empty Rate": "empty_rate", "Load Base Rate": "load_base_rate",
            "Above 20-Ton Rate": "above20ton_rate", "Above 30-Ton Rate": "above30ton_rate",
            "Above 40-Ton Rate": "above40ton_rate", "Above 50-Ton Rate": "above50ton_rate",
            "Above 60-Ton Rate": "above60ton_rate", "Increase %": "increase_percentage",
            "Decrease %": "decrease_percentage"
        }

        # --- LAYOUT ---
        main_layout = QVBoxLayout(self)
        top_layout = QHBoxLayout()
        grid_layout = QGridLayout()
        grid_layout.setSpacing(10)

        vehicle_layout = QHBoxLayout()
        self.vehicle_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        vehicle_layout.addWidget(self.vehicle_combo)
        browse_button = QPushButton()
        browse_button.setIcon(QApplication.style().standardIcon(getattr(QApplication.style(), 'SP_DialogOpenButton')))
        browse_button.setToolTip("Browse for Vehicle Image")
        browse_button.clicked.connect(self.browse_for_image)
        vehicle_layout.addWidget(browse_button)

        grid_layout.addWidget(QLabel("Vehicle Name:"), 0, 0)
        grid_layout.addLayout(vehicle_layout, 0, 1)

        validator = QDoubleValidator(0.00, 999999.99, 2)
        for i, label_text in enumerate(self.db_field_map.keys(), 1):
            db_field = self.db_field_map[label_text]
            label = QLabel(f"{label_text}:")
            line_edit = QLineEdit()
            line_edit.setValidator(validator)
            line_edit.setPlaceholderText("0.00")
            grid_layout.addWidget(label, i, 0)
            grid_layout.addWidget(line_edit, i, 1)
            self.rate_fields[db_field] = line_edit

        top_layout.addLayout(grid_layout)
        top_layout.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Fixed, QSizePolicy.Minimum))
        top_layout.addWidget(self.image_preview_label, alignment=Qt.AlignTop)

        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Save Rate")
        self.clear_button = QPushButton("Clear / New")
        self.exit_button = QPushButton("Exit")

        # Connect button clicks to methods
        self.save_button.clicked.connect(self.save_rate)
        self.clear_button.clicked.connect(self.clear_form)
        self.exit_button.clicked.connect(self.close)

        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.clear_button)
        button_layout.addWidget(self.exit_button)

        main_layout.addLayout(top_layout)
        main_layout.addStretch()
        main_layout.addLayout(button_layout)

        self.load_vehicles()

    def browse_for_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Vehicle Image", "", "Image Files (*.png *.jpg *.jpeg *.bmp)")
        if file_path:
            self.selected_image_path = file_path
            try:
                pixmap = QPixmap(file_path)
                self.image_preview_label.setPixmap(pixmap.scaled(self.image_preview_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
            except Exception:
                self.image_preview_label.setText("No Image")
                self.image_preview_label.setPixmap(QPixmap())

    def load_vehicles(self):
        self.vehicle_combo.blockSignals(True)
        current_vehicle = self.vehicle_combo.currentText()
        self.vehicle_combo.clear()
        self.vehicle_combo.addItem("")
        try:
            self.all_rates = rate_calculator.get_all_vehicle_rates()
            for rate in self.all_rates:
                self.vehicle_combo.addItem(rate.get('vehiclename', ''))
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Could not load rates: {e}")
        self.vehicle_combo.blockSignals(False)

        if current_vehicle in [self.vehicle_combo.itemText(i) for i in range(self.vehicle_combo.count())]:
            self.vehicle_combo.setCurrentText(current_vehicle)
        else:
            self.clear_form()

    def on_vehicle_selected(self, vehicle_name):
        # Find the rate info for selected vehicle
        rate_info = next((r for r in self.all_rates if r.get('vehiclename') == vehicle_name), None)
        self.selected_image_path = None

        if not vehicle_name:
            self.clear_form(clear_combo=False)
            return

        if not rate_info:
            self.clear_form(clear_combo=False)
            return

        # Populate rate fields
        try:
            for db_field, widget in self.rate_fields.items():
                value = rate_info.get(db_field, 0.0)
                widget.setText(str(value) if value is not None else "0.00")
        except Exception:
            pass

        # Resolve image via resource_helpers (user folder -> bundled -> absolute legacy)
        image_path_db = rate_info.get('image_path')
        resolved = resolve_resource(image_path_db, 'vehicle_images')
        if resolved and os.path.exists(resolved):
            try:
                pixmap = QPixmap(resolved)
                self.image_preview_label.setPixmap(pixmap.scaled(self.image_preview_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
            except Exception:
                self.image_preview_label.setText("No Image")
                self.image_preview_label.setPixmap(QPixmap())
        else:
            candidates = debug_candidates(image_path_db or '', 'vehicle_images')
            print(f"[DEBUG] vehicle image not found; candidates: {candidates}")
            self.image_preview_label.setText("No Image")
            self.image_preview_label.setPixmap(QPixmap())

    def save_rate(self):
        vehicle_name = self.vehicle_combo.currentText().strip()
        if not vehicle_name:
            QMessageBox.warning(self, "Input Error", "Vehicle Name cannot be empty.")
            return

        # Build rate_data from fields
        rate_data = {'vehiclename': vehicle_name}
        try:
            for db_field, widget in self.rate_fields.items():
                rate_data[db_field] = float(widget.text().strip() or 0.0)
        except ValueError:
            QMessageBox.warning(self, "Input Error", "All rate fields must be valid numbers.")
            return

        # If user selected an image, copy into user folder and store basename
        saved_image_db_path = None
        if self.selected_image_path:
            try:
                _, extension = os.path.splitext(self.selected_image_path)
                safe_filename = "".join(c for c in vehicle_name if c.isalnum() or c in (' ', '_')).rstrip().replace(' ', '_')
                dest_basename = f"{safe_filename}{extension}"
                saved_basename = save_user_file(self.selected_image_path, 'vehicle_images', dest_basename)
                saved_image_db_path = saved_basename  # store basename (portable)
            except Exception as e:
                QMessageBox.critical(self, "Image Error", f"Could not save image: {e}")
                return
        else:
            # Preserve existing image path if present in DB for this vehicle
            existing_rate = next((r for r in self.all_rates if r.get('vehiclename') == vehicle_name), None)
            saved_image_db_path = existing_rate.get('image_path') if existing_rate else None

        if saved_image_db_path:
            rate_data['image_path'] = saved_image_db_path

        try:
            rate_calculator.add_or_update_rate(rate_data)
            QMessageBox.information(self, "Success", f"Rate for '{vehicle_name}' saved successfully.")
            self.load_vehicles()
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Could not save the rate: {e}")

    def clear_form(self, clear_combo=True):
        if clear_combo:
            self.vehicle_combo.setCurrentIndex(0)
        for widget in self.rate_fields.values():
            widget.clear()
        self.image_preview_label.setText("No Image")
        self.image_preview_label.setPixmap(QPixmap())
        self.selected_image_path = None

    def closeEvent(self, event):
        if self.parent_window:
            self.parent_window.show()
        super().closeEvent(event)
