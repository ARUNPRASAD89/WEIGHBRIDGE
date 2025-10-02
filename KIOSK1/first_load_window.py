import re, sys, random, psycopg2, traceback, os, yaml, threading, io
from datetime import datetime
from functools import partial
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QHBoxLayout, QGridLayout, QButtonGroup,
    QApplication, QSizePolicy, QMessageBox, QDialog, QFrame, QScrollArea, QSpacerItem
)
from PyQt5.QtCore import Qt, QDate, QTime, QTimer, QLocale, QSize, QCoreApplication, QEvent
from PyQt5.QtGui import QFont, QIntValidator, QPixmap, QIcon, QImage

# --- Local Imports ---
from db_utils import execute_query, fetch_one, unified_save_ticket, get_new_connection
from ticket_preview_window import TicketPreviewDialog
from print_ticket_with_template_win32 import print_ticket_with_template
from date_time_utils import to_db_date, to_db_time, to_display_date, to_display_time
import rate_calculator
from common_dialogs import CommonSummaryDialog
from camera_manager import CameraManager
import whatsapp_sender
from serial_manager import get_serial_manager

import numpy as np

# Add the qrcode library import
try:
    import qrcode
    QRCODE_AVAILABLE = True
except ImportError:
    QRCODE_AVAILABLE = False


try:
    from whatsapp_gui import WhatsAppWorker
    WHATSAPP_WORKER_AVAILABLE = True
except ImportError:
    WHATSAPP_WORKER_AVAILABLE = False

# Optional OpenCV for camera feed
try:
    import cv2
    CAMERA_AVAILABLE = True
except ImportError:
    cv2 = None
    CAMERA_AVAILABLE = False

try:
    from serial_manager import SerialManager
    SERIAL_MANAGER_AVAILABLE = True
except ImportError:
    SERIAL_MANAGER_AVAILABLE = False

# --- SCREEN/RESOLUTION HELPERS ---
def center_and_resize(widget, width_ratio=0.65, height_ratio=0.75, min_w=1000, min_h=500):
    screen = QApplication.primaryScreen()
    if not screen: return
    ag = screen.availableGeometry()
    w = max(min_w, int(ag.width() * float(width_ratio)))
    h = max(min_h, int(ag.height() * float(height_ratio)))
    widget.resize(w, h)
    x = ag.x() + (ag.width() - w) // 2
    y = ag.y() + (ag.height() - h) // 2
    widget.move(x, y)

# --- DIALOGS ---
class OldWeightDialog(QDialog):
    def __init__(self, parent, ticket_number, vehicle_number):
        super().__init__(parent)
        self.setWindowTitle("OLD WEIGHT")
        self.setWindowModality(Qt.ApplicationModal)
        self.setStyleSheet("background-color: black; color: white;")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        atm_font = QFont("Arial", 32, QFont.Bold)
        layout = QVBoxLayout()
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(36)

        self.info_label = QLabel("OLD WEIGHT IS PRESENT")
        self.info_label.setFont(atm_font)
        self.info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.info_label, alignment=Qt.AlignCenter)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(40)

        self.x_btn = QPushButton("X")
        self.x_btn.setFont(QFont("Arial", 28, QFont.Bold))
        self.x_btn.setMinimumSize(110, 80)
        self.x_btn.setStyleSheet("background-color: red; color: white; border-radius: 18px;")
        self.x_btn.clicked.connect(lambda: self.x_pressed(ticket_number))
        btn_row.addWidget(self.x_btn)

        self.two_btn = QPushButton("2")
        self.two_btn.setFont(QFont("Arial", 28, QFont.Bold))
        self.two_btn.setMinimumSize(110, 80)
        self.two_btn.setStyleSheet("background-color: #222; color: white; border-radius: 18px;")
        self.two_btn.clicked.connect(lambda: self.two_pressed(ticket_number, vehicle_number))
        btn_row.addWidget(self.two_btn)

        layout.addSpacing(30)
        layout.addLayout(btn_row)
        self.setLayout(layout)
        self.result = None

    def x_pressed(self, ticket_number):
        try:
            execute_query('UPDATE tickets SET "Pending" = FALSE WHERE "TicketNumber" = %s', (ticket_number,))
        except Exception as e:
            QMessageBox.critical(self, "DB Error", f"Could not update ticket: {e}")
        self.result = "x"
        self.accept()

    def two_pressed(self, ticket_number, vehicle_number):
        self.result = (ticket_number, vehicle_number)
        self.accept()

class LoadStatusDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Step 1: Select Load Status")
        self.setWindowModality(Qt.ApplicationModal)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.result = None

        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignCenter)
        label = QLabel("Select the vehicle's load status:"); label.setFont(QFont("Arial", 14)); label.setAlignment(Qt.AlignCenter); layout.addWidget(label)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(40)

        self.empty_btn = QPushButton("○\nEMPTY\n[    >]")
        self.load_btn  = QPushButton("▣\nLOAD\n[|||||>]")

        btn_font = QFont("Arial", 30, QFont.Bold)
        for btn, bg_color in [(self.empty_btn, "#2E86C1"), (self.load_btn, "#C0392B")]:
            btn.setFont(btn_font)
            btn.setMinimumSize(420, 300)
            btn.setStyleSheet(
                f"QPushButton {{ background-color: {bg_color}; color: white; border-radius: 20px; padding: 18px; font-weight: bold; text-align: center; }} "
                "QPushButton:pressed { background-color: #555555; }"
            )
            btn_layout.addWidget(btn)

        self.empty_btn.clicked.connect(lambda: self.set_result("Empty"))
        self.load_btn.clicked.connect(lambda: self.set_result("Load"))

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def set_result(self, status): self.result = status; self.accept()

class VehicleSelectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Step 2: Select Vehicle Type")
        self.setWindowModality(Qt.ApplicationModal)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.result = None
        self.vehicle_options = []

        main_layout = QVBoxLayout(self)
        label = QLabel("Select the Vehicle Type:"); label.setFont(QFont("Arial", 14)); label.setAlignment(Qt.AlignCenter); main_layout.addWidget(label)
        
        scroll_area = QScrollArea(self); scroll_area.setWidgetResizable(True); main_layout.addWidget(scroll_area)
        
        scroll_content = QWidget(); vehicles_grid = QGridLayout(scroll_content); vehicles_grid.setSpacing(10)
        self.vehicle_btn_group = QButtonGroup(self)
        
        try:
            self.vehicle_options = rate_calculator.get_all_vehicle_rates()
            for idx, vehicle_data in enumerate(self.vehicle_options):
                vehicle_name = vehicle_data['vehiclename']
                image_path = vehicle_data.get('image_path')
                btn = QPushButton(vehicle_name)
                btn.setFont(QFont("Arial", 12, QFont.Bold)); btn.setCheckable(True); btn.setMinimumHeight(80)
                btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred); btn.setIconSize(QSize(140, 140))
                if image_path and os.path.exists(image_path): btn.setIcon(QIcon(image_path))
                self.vehicle_btn_group.addButton(btn, idx)
                vehicles_grid.addWidget(btn, idx // 2, idx % 2)
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Could not load vehicle types: {e}")
            QTimer.singleShot(0, self.reject)

        scroll_area.setWidget(scroll_content)
        self.vehicle_btn_group.buttonClicked[int].connect(self.on_vehicle_selected)

    def showEvent(self, event):
        super().showEvent(event)
        center_and_resize(self, width_ratio=0.6, height_ratio=0.7, min_w=700, min_h=500)

    def on_vehicle_selected(self, button_id):
        self.result = self.vehicle_options[button_id]['vehiclename']
        self.accept()

# --- Main Window ---
class FirstLoadWindow(QWidget):
    def __init__(self, load_status, vehicle_type, mode_window=None):
        super().__init__()
        self.setWindowTitle("Vehicle First Transaction")
        self.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint)
        self.setStyleSheet("""
            background: #fff;
            QLineEdit:focus { 
                border: 2px solid #ff6600; 
                background: #fff7d6; 
            }
        """)
        self.mode_window = mode_window
        self.load_status = load_status
        self.selected_vehicle_type = vehicle_type
        self.selected_supplier = None 
        self.suppliers_data = [] 
        self.last_focused_input = None
        self.setMinimumSize(1100, 700)

        # To hold the imported pytesseract module
        self.pytesseract = None

        self._define_fonts()
        self._setup_ui()
        self.camera_manager = CameraManager(self.camera_display)
        self._connect_signals()
        self._install_event_filters()
        self._initialize_state()
        self._start_timers()

        center_and_resize(self, width_ratio=0.75, height_ratio=0.85, min_w=1100, min_h=700)

        self.serial_manager = get_serial_manager()
        try:
            if not hasattr(self, "_serial_signals_connected"):
                self.serial_manager.weight_updated.connect(self.update_live_weight)
                self.serial_manager.error_occurred.connect(self.show_serial_error)
                self._serial_signals_connected = True
        except Exception:
            pass
        # Acquire a claim on the shared manager
        try:
            self.serial_manager.acquire()
        except Exception:
            QMessageBox.warning(self, "Serial Manager Error", "Could not acquire serial manager.")

        QTimer.singleShot(100, self.camera_manager.start)
        
    def _define_fonts(self):
        self.font_label = QFont("Arial", 14, QFont.Bold)
        self.font_input = QFont("Arial", 18)
        self.font_weight = QFont("Arial", 28, QFont.Bold)
        self.font_button = QFont("Arial", 18, QFont.Bold)
        self.font_amount = QFont("Arial", 18, QFont.Bold)
        self.letter_font = QFont("Arial", 20, QFont.Bold)
        self.digit_font = QFont("Arial", 22, QFont.Bold)

    def _setup_ui(self):
        main_h_layout = QHBoxLayout(self)
        main_h_layout.setContentsMargins(15, 15, 15, 15)
        main_h_layout.setSpacing(15)

        controls_frame = QFrame()
        controls_layout = QVBoxLayout(controls_frame)
        controls_layout.setContentsMargins(0, 0, 0, 0); controls_layout.setSpacing(10); controls_layout.setAlignment(Qt.AlignTop)

        top_bar_frame = QFrame(); top_bar_frame.setLayout(self._create_top_bar()); controls_layout.addWidget(top_bar_frame)
        vehicle_frame = QFrame(); vehicle_frame.setLayout(self._create_vehicle_entry()); controls_layout.addWidget(vehicle_frame)
        weight_frame = QFrame(); weight_frame.setLayout(self._create_weight_details()); controls_layout.addWidget(weight_frame)
        amount_frame = QFrame(); amount_frame.setLayout(self._create_amount_details()); controls_layout.addWidget(amount_frame)
        info_frame = QFrame(); info_frame.setLayout(self._create_info_display()); controls_layout.addWidget(info_frame)

        keypad_frame = QFrame(); keypad_frame.setLayout(self._create_keyboard()); controls_layout.addWidget(keypad_frame)
        
        supplier_layout = self._create_supplier_buttons(); controls_layout.addLayout(supplier_layout)
        material_layout = self._create_material_buttons(); controls_layout.addLayout(material_layout)

        controls_layout.addStretch()
        bottom_frame = QFrame(); bottom_frame.setLayout(self._create_bottom_bar()); controls_layout.addWidget(bottom_frame, alignment=Qt.AlignHCenter)
        main_h_layout.addWidget(controls_frame, 1)

        camera_frame = QFrame()
        camera_frame.setFrameShape(QFrame.StyledPanel); camera_frame.setStyleSheet("QFrame { background-color: black; border: 2px solid #555; border-radius: 8px; }")
        camera_layout = QVBoxLayout(camera_frame)
        self.camera_display = QLabel("CAMERA FEED"); self.camera_display.setAlignment(Qt.AlignCenter); self.camera_display.setFont(QFont("Arial", 24, QFont.Bold))
        self.camera_display.setStyleSheet("color: white;"); self.camera_display.setMinimumSize(320, 240); self.camera_display.setScaledContents(False)
        camera_layout.addWidget(self.camera_display)
        main_h_layout.addWidget(camera_frame, 2)

    def _create_supplier_buttons(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(3, 1, 3, 1)
        layout.setSpacing(0)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFixedHeight(36)
        scroll_area.setMaximumHeight(38)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        scroll_content = QWidget()
        button_layout = QHBoxLayout(scroll_content)
        button_layout.setSpacing(5)
        button_layout.setContentsMargins(2, 1, 2, 1)
        button_layout.setAlignment(Qt.AlignLeft)

        self.supplier_button_group = QButtonGroup(self)
        self.supplier_button_group.setExclusive(True)

        try:
            self.suppliers_data = execute_query("SELECT suppliername, contactnumber, suppliercode FROM suppliers WHERE suppliername IS NOT NULL AND suppliername != '' ORDER BY suppliername")
            if not isinstance(self.suppliers_data, list):
                self.suppliers_data = []
                raise ValueError("Database query did not return a list of suppliers.")
            for idx, supplier_dict in enumerate(self.suppliers_data):
                supplier_name = supplier_dict.get('suppliername')
                if supplier_name:
                    btn = QPushButton(supplier_name)
                    btn.setFont(QFont("Arial", 11, QFont.Bold))
                    btn.setMinimumHeight(28)
                    btn.setMaximumHeight(32)
                    btn.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
                    btn.setCheckable(True)
                    btn.setStyleSheet("""
                        QPushButton { background-color: #FFFF99; border: 1px solid #BBB; border-radius: 5px; padding: 4px 12px; }
                        QPushButton:checked { background-color: #C6DAFC; border: 2px solid #0053B3; }
                    """)
                    btn.adjustSize()
                    self.supplier_button_group.addButton(btn, idx)
                    button_layout.addWidget(btn)
        except Exception as e:
            print(f"Error fetching or processing suppliers: {e}")
            error_label = QLabel("Could not load suppliers.")
            button_layout.addWidget(error_label)
        
        self.supplier_button_group.buttonClicked[int].connect(self._on_supplier_button_clicked)
        button_layout.addStretch()
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)
        return layout

    def _on_supplier_button_clicked(self, button_id):
        try:
            selected_dict = self.suppliers_data[button_id]
            self.selected_supplier = {
                'suppliername': selected_dict.get('suppliername'),
                'contactnumber': selected_dict.get('contactnumber'),
                'suppliercode': selected_dict.get('suppliercode')
            }
            print(f"Supplier selected: {self.selected_supplier['suppliername']}")
        except (IndexError, KeyError, Exception) as e:
            print(f"Error selecting supplier: {e}")
            self.selected_supplier = None
    

    def _create_material_buttons(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(3, 1, 3, 1)
        layout.setSpacing(0)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFixedHeight(36)
        scroll_area.setMaximumHeight(38)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        scroll_content = QWidget()
        button_layout = QHBoxLayout(scroll_content)
        button_layout.setSpacing(5)
        button_layout.setContentsMargins(2, 1, 2, 1)
        button_layout.setAlignment(Qt.AlignLeft)

        self.material_button_group = QButtonGroup(self)
        self.material_button_group.setExclusive(True)
        self.materials_data = []
        try:
            self.materials_data = execute_query("SELECT materialname, materialcode FROM material ORDER BY materialname")
            if isinstance(self.materials_data, list):
                for idx, mat in enumerate(self.materials_data):
                    mat_name = mat.get('materialname')
                    if mat_name:
                        btn = QPushButton(mat_name)
                        btn.setFont(QFont("Arial", 11, QFont.Bold))
                        btn.setMinimumHeight(28)
                        btn.setMaximumHeight(32)
                        btn.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
                        btn.setCheckable(True)
                        btn.setStyleSheet("""
                            QPushButton { background-color: #FFFACD; border: 1px solid #BBB; border-radius: 5px; padding: 4px 12px; }
                            QPushButton:checked { background-color: #C6DAFC; border: 2px solid #0053B3; }
                        """)
                        btn.adjustSize()
                        self.material_button_group.addButton(btn, idx)
                        button_layout.addWidget(btn)
        except Exception as e:
            print(f"Error fetching materials: {e}")
            error_label = QLabel("Could not load materials.")
            button_layout.addWidget(error_label)
        self.material_button_group.buttonClicked[int].connect(self._on_material_button_clicked)
        button_layout.addStretch()
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)
        return layout

    def _on_material_button_clicked(self, button_id):
        try:
            selected = self.materials_data[button_id]
            self.selected_material = {
                'materialname': selected.get('materialname'),
                'materialcode': selected.get('materialcode')
            }
            print(f"Material selected: {self.selected_material['materialname']}")
        except Exception as e:
            print(f"Error selecting material: {e}")
            self.selected_material = None

    def _create_top_bar(self):
        layout = QHBoxLayout()
        date_label = QLabel("Date:"); date_label.setFont(self.font_label)
        self.date_field = QLineEdit(); self.date_field.setFont(self.font_input); self.date_field.setReadOnly(True); self.date_field.setFixedWidth(170)
        layout.addWidget(date_label); layout.addWidget(self.date_field); layout.addSpacing(20)

        ticket_label = QLabel("Ticket No:"); ticket_label.setFont(self.font_label)
        self.ticket_number = QLineEdit(self.generate_ticket_number()); self.ticket_number.setFont(self.font_input); self.ticket_number.setReadOnly(True); self.ticket_number.setFixedWidth(110)
        layout.addWidget(ticket_label); layout.addWidget(self.ticket_number); layout.addStretch()

        weight_label = QLabel("Weight (KG):"); weight_label.setFont(self.font_label)
        self.weight_display = QLabel("0"); self.weight_display.setFont(self.font_weight)
        self.weight_display.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.weight_display.setStyleSheet("color:white; background:black; border-radius: 8px; padding: 4px 32px; min-width: 180px;")
        layout.addWidget(weight_label); layout.addWidget(self.weight_display)
        return layout

    def _create_vehicle_entry(self):
        layout = QHBoxLayout()
        time_label = QLabel("Time:"); time_label.setFont(self.font_label)
        self.time_field = QLineEdit(); self.time_field.setFont(self.font_input); self.time_field.setReadOnly(True); self.time_field.setFixedWidth(130)
        layout.addWidget(time_label); layout.addWidget(self.time_field); layout.addSpacing(15)

        vehicle_label = QLabel("Vehicle:"); vehicle_label.setFont(self.font_label)
        self.vehicle_input = QLineEdit()
        self.vehicle_input.setFont(QFont("Arial", 22, QFont.Bold))
        self.vehicle_input.setFixedSize(250, 48)
        self.vehicle_input.setFocusPolicy(Qt.StrongFocus)

        layout.addWidget(vehicle_label); layout.addWidget(self.vehicle_input); layout.addSpacing(12)

        self.ok_btn = QPushButton("OK"); self.ok_btn.setFont(QFont("Arial", 16, QFont.Bold)); self.ok_btn.setFixedSize(120, 48)
        self.ok_btn.setStyleSheet("padding: 0 5px; background-color: #c6ffc6; border: 2px solid #0b0; border-radius: 8px;")
        self.ok_btn.setEnabled(False)
        layout.addWidget(self.ok_btn)

        self.lpr_btn = QPushButton("📷 LPR"); self.lpr_btn.setFont(QFont("Arial", 12, QFont.Bold)); self.lpr_btn.setFixedSize(110, 36)
        self.lpr_btn.setStyleSheet("background: #fff; border: 2px solid #888; border-radius: 6px;")
        layout.addWidget(self.lpr_btn)
        layout.addStretch()
        return layout

    def _insert_key_to_focused_field(self, k):
        if self.last_focused_input and not self.last_focused_input.isReadOnly():
            self.last_focused_input.insert(k)

    def _create_weight_details(self):
        layout = QHBoxLayout()
        self.empty_weight_label = QLabel("Empty:"); self.empty_weight_label.setFont(self.font_label)
        self.empty_weight_field = QLineEdit(); self.empty_weight_field.setFont(self.font_amount); self.empty_weight_field.setReadOnly(True); self.empty_weight_field.setFixedWidth(120)
        layout.addWidget(self.empty_weight_label); layout.addWidget(self.empty_weight_field); layout.addSpacing(40)

        self.load_weight_label = QLabel("Load Weight:"); self.load_weight_label.setFont(self.font_label)
        self.load_weight_field = QLineEdit(); self.load_weight_field.setFont(self.font_amount); self.load_weight_field.setReadOnly(True); self.load_weight_field.setFixedWidth(120)
        layout.addWidget(self.load_weight_label); layout.addWidget(self.load_weight_field)

        container_label = QLabel("Container No:"); container_label.setFont(self.font_label)
        self.container_input = QLineEdit()
        self.container_input.setFont(self.font_amount)
        self.container_input.setFixedWidth(200)
        self.container_input.setStyleSheet("background: #ffffff; border: 2px solid #888; padding: 4px; border-radius: 6px;")
        self.container_input.setFocusPolicy(Qt.StrongFocus)

        layout.addSpacing(12)
        layout.addWidget(container_label); layout.addWidget(self.container_input)

        layout.addStretch()
        return layout

    def _create_amount_details(self):
        layout = QHBoxLayout(); layout.setSpacing(10)
        e_label = QLabel("E-Amount:"); e_label.setFont(self.font_label)
        self.eamount_field = QLineEdit("0"); self.eamount_field.setFont(self.font_amount); self.eamount_field.setReadOnly(True)
        l_label = QLabel("L-Amount:"); l_label.setFont(self.font_label)
        self.lamount_field = QLineEdit("0"); self.lamount_field.setFont(self.font_amount); self.lamount_field.setReadOnly(True)
        t_label = QLabel("T-Amount:"); t_label.setFont(self.font_label)
        self.tamount_field = QLineEdit("0"); self.tamount_field.setFont(self.font_amount); self.tamount_field.setReadOnly(True)
        for label, field in [(e_label, self.eamount_field), (l_label, self.lamount_field), (t_label, self.tamount_field)]:
            layout.addWidget(label); layout.addWidget(field)
        layout.addStretch(); return layout

    def _create_info_display(self):
        layout = QHBoxLayout()
        status_label = QLabel("Status:"); status_label.setFont(self.font_label)
        self.load_status_display = QLabel(self.load_status); self.load_status_display.setFont(self.font_button)
        self.load_status_display.setStyleSheet("color: blue; font-weight: bold;")
        wheels_label = QLabel("Vehicle Type:"); wheels_label.setFont(self.font_label)
        self.wheels_display = QLabel(self.selected_vehicle_type); self.wheels_display.setFont(QFont("Arial", 12, QFont.Bold))
        self.wheels_display.setStyleSheet("color: blue; font-weight: bold;")
        layout.addWidget(status_label); layout.addWidget(self.load_status_display); layout.addSpacing(20)
        layout.addWidget(wheels_label); layout.addWidget(self.wheels_display); layout.addStretch()
        driver_label = QLabel("Driver No:"); driver_label.setFont(self.font_label)
        self.driverno_input = QLineEdit(); self.driverno_input.setFont(QFont("Arial", 18)); self.driverno_input.setFixedWidth(200)
        self.driverno_input.setStyleSheet("background: #ffffff; border: 2px solid #888; padding: 4px; border-radius: 6px;")
        self.driverno_input.setValidator(QIntValidator())
        self.driverno_input.setFocusPolicy(Qt.StrongFocus)
        layout.addWidget(driver_label); layout.addWidget(self.driverno_input); layout.addSpacing(12)
        return layout

    def validate_inputs(self):
        vehicle_valid = self.is_valid_indian_plate(self.vehicle_input.text())
        driver_valid = True
        if self.driverno_input.text().strip() and not self.driverno_input.text().strip().isdigit():
            driver_valid = False
        return vehicle_valid and driver_valid

    def _keypad_backspace(self):
        if self.last_focused_input and not self.last_focused_input.isReadOnly():
            self.last_focused_input.backspace()

    def _keypad_clear(self):
        self.vehicle_input.clear()
        self.container_input.clear()
        self.driverno_input.clear()
        self.check_vehicle_entry()
        self.vehicle_input.setFocus()

    def _create_keyboard(self):
        keypad_layout = QGridLayout()
        keypad_layout.setHorizontalSpacing(10)
        keypad_layout.setVerticalSpacing(5)

        az_keys = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        digit_keys = '1234567890'

        for idx, key in enumerate(az_keys):
            btn = QPushButton(key)
            btn.setFont(self.letter_font)
            btn.setFixedSize(52, 52)
            btn.clicked.connect(partial(self._insert_key_to_focused_field, key))
            keypad_layout.addWidget(btn, idx // 7, idx % 7)

        for idx, key in enumerate(digit_keys):
            btn = QPushButton(key)
            btn.setFont(self.digit_font)
            btn.setFixedSize(52, 52)
            btn.clicked.connect(partial(self._insert_key_to_focused_field, key))
            keypad_layout.addWidget(btn, idx // 3, 7 + (idx % 3))

        back_btn = QPushButton("<--")
        back_btn.setFont(self.digit_font)
        back_btn.setFixedSize(52, 52)
        back_btn.clicked.connect(self._keypad_backspace)
        keypad_layout.addWidget(back_btn, 3, 8)

        clear_btn = QPushButton("Clear")
        clear_btn.setFont(self.digit_font)
        clear_btn.setFixedSize(92, 52)
        clear_btn.setStyleSheet("background-color: red; color: white; font-weight: bold;")
        clear_btn.clicked.connect(self._keypad_clear)
        keypad_layout.addWidget(clear_btn, 3, 10)

        centered_layout = QHBoxLayout()
        centered_layout.addStretch()
        centered_layout.addLayout(keypad_layout)
        centered_layout.addStretch()
        return centered_layout

    def _install_event_filters(self):
        self.vehicle_input.installEventFilter(self)
        self.container_input.installEventFilter(self)
        self.driverno_input.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.FocusIn:
            if obj in [self.vehicle_input, self.container_input, self.driverno_input]:
                self.last_focused_input = obj
        return super().eventFilter(obj, event)

    def _initialize_state(self):
        self.update_weight_placeholders()
        self.date_format = QLocale.system().dateFormat(QLocale.ShortFormat)
        self.time_format = "HH:mm:ss"
        self.check_vehicle_entry()
        try:
            self.setTabOrder(self.vehicle_input, self.container_input)
            self.setTabOrder(self.container_input, self.driverno_input)
            self.setTabOrder(self.driverno_input, self.ok_btn)
        except Exception as e:
            print(f"Could not set tab order: {e}")
        QTimer.singleShot(50, lambda: self.vehicle_input.setFocus())

    def _create_bottom_bar(self):
        bottom_layout = QHBoxLayout()
        self.cancel_btn = QPushButton("Cancel"); self.cancel_btn.setFont(self.font_button); self.cancel_btn.setFixedSize(150, 48)
        self.cancel_btn.setStyleSheet("QPushButton {background: #fdd; border: 2px solid #a00; padding: 4px; font-size: 14pt; border-radius: 8px;}")
        bottom_layout.addWidget(self.cancel_btn); bottom_layout.addStretch()
        return bottom_layout

    @staticmethod
    def is_valid_indian_plate(text):
        if not text: return False
        t = text.strip().upper().replace(" ", "").replace("-", "")
        patterns = [r'^[A-Z]{2}\d{2}[A-Z]{1,3}\d{4}$', r'^[A-Z]{2}\d{2}\d{4}$', r'^[A-Z]{3}\d{4}$', r'^[A-Z]{2}\d{4}$']
        return any(re.fullmatch(p, t) for p in patterns)

    def check_vehicle_entry(self):
        plate_text = self.vehicle_input.text().upper()
        
        if self.vehicle_input.text() != plate_text:
            self.vehicle_input.blockSignals(True)
            cursor_pos = self.vehicle_input.cursorPosition()
            self.vehicle_input.setText(plate_text)
            self.vehicle_input.setCursorPosition(cursor_pos)
            self.vehicle_input.blockSignals(False)

        is_valid = self.is_valid_indian_plate(plate_text)
        self.ok_btn.setEnabled(is_valid)
        
        if is_valid:
            self.vehicle_input.setStyleSheet("background: #d4edda; color: #155724; border: 2px solid #28a745; padding: 4px; border-radius: 8px;")
        else:
            self.vehicle_input.setStyleSheet("background: #f8d7da; color: #721c24; border: 2px solid #f5c6cb; padding: 4px; border-radius: 8px;")

    def _lazy_load_tesseract(self):
        """Import and configure pytesseract on first use."""
        if self.pytesseract:
            return True
        try:
            import pytesseract
            self.pytesseract = pytesseract
            # Try to find Tesseract automatically or use a known path
            tesseract_path = r'D:\Program Files\Tesseract-OCR\tesseract.exe'
            if os.path.exists(tesseract_path):
                self.pytesseract.pytesseract.tesseract_cmd = tesseract_path
            print(f"Tesseract configured: {self.pytesseract.pytesseract.tesseract_cmd}")
            return True
        except ImportError:
            QMessageBox.critical(self, "LPR Error", "Pytesseract library is not installed.")
            return False
        except Exception as e:
            QMessageBox.critical(self, "LPR Error", f"Could not configure Tesseract OCR: {e}")
            return False

    def run_lpr(self):
        """Run License Plate Recognition on the current camera frame."""
        if not self._lazy_load_tesseract():
            return
            
        frame = self.camera_manager.get_current_frame()
        if frame is None:
            QMessageBox.warning(self, "LPR Error", "Could not get frame from camera.")
            return

        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            # Convert to grayscale for better OCR performance
            gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Use Tesseract to find text
            # Add custom config for license plates if needed, e.g. '--psm 8'
            config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
            detected_text = self.pytesseract.image_to_string(gray_frame, config=config).strip()
            
            # Simple post-processing to find a valid plate
            best_match = ""
            for word in re.split(r'[\s\n]+', detected_text):
                if self.is_valid_indian_plate(word) and len(word) > len(best_match):
                    best_match = word

            if best_match:
                self.vehicle_input.setText(best_match)
                QMessageBox.information(self, "LPR Success", f"Detected Vehicle Number: {best_match}")
            else:
                QMessageBox.warning(self, "LPR Result", f"Could not detect a valid vehicle number. Found: '{detected_text}'")

        except Exception as e:
            QMessageBox.critical(self, "LPR Processing Error", f"An error occurred during LPR:\n{e}")
        finally:
            QApplication.restoreOverrideCursor()


    def closeEvent(self, event):
        self.camera_manager.stop()
        try:
            if hasattr(self, 'serial_manager'):
                self.serial_manager.release()
        except Exception:
            pass
        super().closeEvent(event)
        
    def _connect_signals(self):
        self.ok_btn.clicked.connect(self.ok_pressed)
        self.vehicle_input.textChanged.connect(self.check_vehicle_entry)
        self.cancel_btn.clicked.connect(self.cancel_action)
        self.lpr_btn.clicked.connect(self.run_lpr)

    def _start_timers(self):
        self.update_date_time()
        timer = QTimer(self); timer.timeout.connect(self.update_date_time); timer.start(1000)

    def update_date_time(self):
        self.date_field.setText(to_display_date(QDate.currentDate()))
        self.time_field.setText(to_display_time(QTime.currentTime()))

    def generate_ticket_number(self):
        row = fetch_one('SELECT COALESCE(MAX(CAST("TicketNumber" AS INTEGER)), 0) + 1 AS next_ticket FROM tickets')
        return f"{int(row['next_ticket'] if row and row['next_ticket'] else 1):05d}"

    def update_live_weight(self, weight):
        self.weight_display.setText(weight)
        self.update_weight_placeholders()

    def show_serial_error(self, message):
        QMessageBox.warning(self, "Serial Port Error", message)

    def ok_pressed(self):
        if not self.validate_inputs():
            QMessageBox.warning(self, "Validation Error", "Please check vehicle and driver information.")
            return
        
        plate = self.vehicle_input.text().upper()
        try:
            row = fetch_one('SELECT "TicketNumber", "VehicleNumber" FROM tickets WHERE "VehicleNumber" = %s AND "Pending" = TRUE', (plate,))
            if row:
                dlg = OldWeightDialog(self, row["TicketNumber"], plate)
                if dlg.exec_() == QDialog.Accepted and isinstance(dlg.result, tuple): self.open_second_load_window(*dlg.result)
                return

            amounts = rate_calculator.calculate_amounts(self.selected_vehicle_type, self.weight_display.text(), self.load_status)
            e_val, l_val, t_val = (amounts.get('eamount', 0), amounts.get('lamount', 0), amounts.get('tamount', 0)) if amounts else (0, 0, 0)
            
            self.eamount_field.setText(str(e_val)); self.lamount_field.setText(str(l_val)); self.tamount_field.setText(str(t_val))
            self.show_summary_dialog(e_val, l_val, t_val)
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Error processing vehicle: {e}\n{traceback.format_exc()}")

    def show_summary_dialog(self, eamount, lamount, tamount):
        try:
            ew_text = self.empty_weight_field.text(); lw_text = self.load_weight_field.text()
            supplier_name = self.selected_supplier.get('suppliername') if self.selected_supplier else None
            material_name = self.selected_material.get('materialname') if hasattr(self, 'selected_material') and self.selected_material else None

            container_no = self.container_input.text().strip() or None
            driver_no_text = self.driverno_input.text().strip()
            driver_no = int(driver_no_text) if driver_no_text.isdigit() else None

            ticket_data = {
                "TicketNumber": self.ticket_number.text(), "VehicleNumber": self.vehicle_input.text().upper(),
                "VehicleType": self.selected_vehicle_type, "Date": to_db_date(QDate.currentDate()), "Time": to_db_time(QTime.currentTime()),
                "EmptyWeight": ew_text, "LoadedWeight": lw_text, "Status": self.load_status, "EAMOUNT": eamount, "LAMOUNT": lamount,
                "TAMOUNT": tamount, "Pending": True, "Closed": False, "ContainerNo": container_no,
                "NetWeight": abs(int(lw_text or 0) - int(ew_text or 0)),
                "SupplierCode": self.selected_supplier.get('suppliercode') if self.selected_supplier else None,
                "SupplierName": supplier_name,
                "Materialname": material_name,
                "DriverNo": driver_no
            }
            dlg = CommonSummaryDialog(self, ticket_data, is_first_load=True, transaction_window=self.mode_window)
            
            if dlg.exec_() == QDialog.Accepted:
                # Reset the form for the next transaction
                self.ticket_number.setText(self.generate_ticket_number())
                self._keypad_clear()
                self.empty_weight_field.clear(); self.load_weight_field.clear()
                self.eamount_field.setText("0"); self.lamount_field.setText("0"); self.tamount_field.setText("0")
                if self.supplier_button_group.checkedButton():
                    self.supplier_button_group.setExclusive(False)
                    self.supplier_button_group.checkedButton().setChecked(False)
                    self.supplier_button_group.setExclusive(True)
                if self.material_button_group.checkedButton():
                    self.material_button_group.setExclusive(False)
                    self.material_button_group.checkedButton().setChecked(False)
                    self.material_button_group.setExclusive(True)
                self.selected_supplier = None
                self.selected_material = None
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to prepare summary:\n{traceback.format_exc()}")

    def open_second_load_window(self, ticket_number, vehicle_number):
        try:
            from second_load_window import SecondLoadWindow
            self.close()
            self.second_win = SecondLoadWindow(mode_window=self.mode_window)
            self.second_win.prefill_for_second_load(ticket_number)
            self.second_win.show()
        except ImportError:
            QMessageBox.critical(self, "Error", "SecondLoadWindow module not found.")

    def update_weight_placeholders(self):
        current_weight = self.weight_display.text()
        if self.load_status.upper() == "EMPTY":
            self.empty_weight_field.setText(current_weight); self.load_weight_field.clear()
        else:
            self.empty_weight_field.clear(); self.load_weight_field.setText(current_weight)

    def cancel_action(self):
        if self.mode_window: self.mode_window.show()
        self.close()

if __name__ == "__main__":
    try:
        QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QCoreApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    except Exception: pass
    app = QApplication(sys.argv)
    
    class MockModeWindow(QWidget):
        def __init__(self):
            super().__init__(); self.setWindowTitle("Main Menu"); self.resize(400, 200)
            layout = QVBoxLayout(self); self.label = QLabel("This is the main transaction window."); self.start_button = QPushButton("Start First Load")
            self.start_button.clicked.connect(self.start_first_load); layout.addWidget(self.label); layout.addWidget(self.start_button)
        def start_first_load(self):
            self.hide()
            status_dialog = LoadStatusDialog()
            if status_dialog.exec_() == QDialog.Accepted:
                load_status = status_dialog.result
                vehicle_dialog = VehicleSelectionDialog()
                if vehicle_dialog.exec_() == QDialog.Accepted:
                    vehicle_type = vehicle_dialog.result
                    self.main_win = FirstLoadWindow(load_status=load_status, vehicle_type=vehicle_type, mode_window=self)
                    self.main_win.show()
                else: self.show()
            else: self.show()

    main_menu = MockModeWindow(); main_menu.show()
    sys.exit(app.exec_())
