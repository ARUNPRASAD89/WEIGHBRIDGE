import re, sys, traceback, os
from functools import partial
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QHBoxLayout, QGridLayout, QButtonGroup,
    QApplication, QSizePolicy, QMessageBox, QDialog, QFrame, QScrollArea
)
from PyQt5.QtCore import Qt, QDate, QTime, QTimer, QEvent
from PyQt5.QtGui import QFont, QIntValidator

# --- Refactored Imports ---
from db_utils import execute_query, fetch_one, fetch_all
from date_time_utils import to_db_date, to_db_time, to_display_date, to_display_time
import rate_calculator
from camera_manager import CameraManager
from common_dialogs import CommonSummaryDialog
from first_load_window import VehicleSelectionDialog, center_and_resize
from serial_manager import get_serial_manager

# Optional serial port integration
try:
    from serial_manager import SerialManager
    SERIAL_MANAGER_AVAILABLE = True
except ImportError:
    SERIAL_MANAGER_AVAILABLE = False

# --- DIALOGS ---
class LoadStatusDialogThird(QDialog):
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
        
        self.load_btn  = QPushButton("▣\nLOAD[||||| >]\nலோடு\nलदान")
        btn_font_text = QFont("Arial", 30, QFont.Bold)

        self.load_btn.setFont(btn_font_text)
        self.load_btn.setMinimumSize(420, 300)
        self.load_btn.setStyleSheet(
            f"QPushButton {{ background-color: #C0392B; color: white; "
            "border-radius: 20px; padding: 18px; font-weight: bold; }} "
            "QPushButton:pressed { background-color: #555555; }"
        )
        self.load_btn.setFocusPolicy(Qt.NoFocus)
        btn_layout.addWidget(self.load_btn)
        
        self.load_btn.clicked.connect(lambda: self.set_result("Load"))
        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def showEvent(self, event):
        super().showEvent(event)
        center_and_resize(self, width_ratio=0.35, height_ratio=0.35, min_w=420, min_h=320)

    def set_result(self, status): self.result = status; self.accept()

# --- Main Window ---
class ThirdLoadWindow(QWidget):
    def __init__(self, load_status, vehicle_type, mode_window=None):
        super().__init__()
        self.setWindowTitle("Vehicle Single Transaction")
        self.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint)
        self.setStyleSheet("""
            background: #fff;
            QLineEdit:focus { 
                border: 2px solid #ff6600; 
                background: #fff7d6; 
            }
        """)
        self.setMinimumSize(1100, 700)

        self.mode_window = mode_window
        self.load_status = load_status
        self.selected_vehicle_type = vehicle_type
        
        self.selected_supplier = None
        self.suppliers_data = []
        self.selected_material = None
        self.materials_data = []
        self.last_focused_input = None
        
        self._vtare_value = None
        self._last_empty_value = None
        self._last_load_value = None
        self._tare_weight_manually_set = False

        self._define_fonts()
        self._setup_ui()
        self.camera_manager = CameraManager(self.camera_display)
        self._connect_signals()
        self._install_event_filters()
        self._initialize_state()
        self._start_timers()

        center_and_resize(self, width_ratio=0.85, height_ratio=0.93, min_w=1100, min_h=700)

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
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(10)
        controls_layout.setAlignment(Qt.AlignTop)

        top_bar_frame = QFrame(); top_bar_frame.setLayout(self._create_top_bar()); controls_layout.addWidget(top_bar_frame)
        vehicle_frame = QFrame(); vehicle_frame.setLayout(self._create_vehicle_entry()); controls_layout.addWidget(vehicle_frame)
        weight_frame = QFrame(); weight_frame.setLayout(self._create_weight_details()); controls_layout.addWidget(weight_frame)
        amount_frame = QFrame(); amount_frame.setLayout(self._create_amount_details()); controls_layout.addWidget(amount_frame)
        info_frame = QFrame(); info_frame.setLayout(self._create_info_display()); controls_layout.addWidget(info_frame)
        
        keypad_frame = QFrame(); keypad_frame.setLayout(self._create_keyboard()); controls_layout.addWidget(keypad_frame)
        
        supplier_layout = self._create_supplier_buttons(); controls_layout.addLayout(supplier_layout)
        material_layout = self._create_material_buttons(); controls_layout.addLayout(material_layout)
        
        controls_layout.addStretch()
        tare_frame = QFrame(); tare_frame.setLayout(self._create_tare_picker()); controls_layout.addWidget(tare_frame)
        controls_layout.addStretch()
        bottom_frame = QFrame(); bottom_frame.setLayout(self._create_bottom_bar()); controls_layout.addWidget(bottom_frame, alignment=Qt.AlignHCenter)

        main_h_layout.addWidget(controls_frame, 1)

        camera_frame = QFrame()
        camera_frame.setFrameShape(QFrame.StyledPanel)
        camera_frame.setStyleSheet("QFrame { background-color: black; border: 2px solid #555; border-radius: 8px; }")
        camera_layout = QVBoxLayout(camera_frame)
        self.camera_display = QLabel("CAMERA FEED")
        self.camera_display.setAlignment(Qt.AlignCenter)
        self.camera_display.setFont(QFont("Arial", 24, QFont.Bold))
        self.camera_display.setStyleSheet("color: white;")
        self.camera_display.setMinimumSize(320, 240)
        self.camera_display.setScaledContents(False)
        camera_layout.addWidget(self.camera_display)
        main_h_layout.addWidget(camera_frame, 2)

    def _create_top_bar(self):
        layout = QHBoxLayout()
        date_label = QLabel("Date:"); date_label.setFont(self.font_label)
        self.date_field = QLineEdit(); self.date_field.setFont(self.font_input); self.date_field.setReadOnly(True); self.date_field.setFixedWidth(170)
        layout.addWidget(date_label); layout.addWidget(self.date_field); layout.addSpacing(20)
        ticket_label = QLabel("Ticket No:"); ticket_label.setFont(self.font_label)
        self.ticket_number = QLineEdit(self.generate_ticket_number()); self.ticket_number.setFont(self.font_input); self.ticket_number.setReadOnly(True); self.ticket_number.setFixedWidth(110)
        layout.addWidget(ticket_label); layout.addWidget(self.ticket_number); layout.addStretch()
        weight_label = QLabel("Weight (KG):"); weight_label.setFont(self.font_label)
        self.weight_display = QLabel("0"); self.weight_display.setFont(self.font_weight); self.weight_display.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.weight_display.setStyleSheet("color:white; background:black; border-radius: 8px; padding: 4px 32px; min-width: 180px;")
        layout.addWidget(weight_label); layout.addWidget(self.weight_display)
        return layout

    def _create_vehicle_entry(self):
        layout = QHBoxLayout()
        time_label = QLabel("Time:"); time_label.setFont(self.font_label)
        self.time_field = QLineEdit(); self.time_field.setFont(self.font_input); self.time_field.setReadOnly(True); self.time_field.setFixedWidth(130)
        layout.addWidget(time_label); layout.addWidget(self.time_field); layout.addSpacing(15)
        vehicle_label = QLabel("Vehicle:"); vehicle_label.setFont(self.font_label)
        self.vehicle_input = QLineEdit(); self.vehicle_input.setFont(QFont("Arial", 22, QFont.Bold)); self.vehicle_input.setFixedSize(250, 48)
        
        layout.addWidget(vehicle_label); layout.addWidget(self.vehicle_input); layout.addSpacing(12)
        self.ok_btn = QPushButton("OK"); self.ok_btn.setFont(QFont("Arial", 16, QFont.Bold)); self.ok_btn.setFixedSize(120, 48)
        self.ok_btn.setStyleSheet("padding: 0 5px; background-color: #c6ffc6; border: 2px solid #0b0; border-radius: 8px;"); self.ok_btn.setEnabled(False)
        layout.addWidget(self.ok_btn)
        self.get_tare_btn = QPushButton("Get Tare"); self.get_tare_btn.setFont(QFont("Arial", 12, QFont.Bold)); self.get_tare_btn.setFixedSize(110, 36)
        self.get_tare_btn.setStyleSheet("background: #eef; border: 2px solid #44a; border-radius: 6px;")
        layout.addWidget(self.get_tare_btn)
        layout.addStretch()
        return layout

    def _create_weight_details(self):
        layout = QHBoxLayout()
        self.empty_weight_label = QLabel("Empty:"); self.empty_weight_label.setFont(self.font_label)
        self.empty_weight_field = QLineEdit(); self.empty_weight_field.setFont(self.font_amount); self.empty_weight_field.setReadOnly(True); self.empty_weight_field.setFixedWidth(120)
        layout.addWidget(self.empty_weight_label); layout.addWidget(self.empty_weight_field); layout.addSpacing(40)
        self.load_weight_label = QLabel("Load Weight:"); self.load_weight_label.setFont(self.font_label)
        self.load_weight_field = QLineEdit(); self.load_weight_field.setFont(self.font_amount); self.load_weight_field.setReadOnly(True); self.load_weight_field.setFixedWidth(120)
        layout.addWidget(self.load_weight_label); layout.addWidget(self.load_weight_field)
        container_label = QLabel("Container No:"); container_label.setFont(self.font_label)
        self.container_input = QLineEdit(); self.container_input.setFont(self.font_amount); self.container_input.setFixedWidth(200)
        self.container_input.setStyleSheet("background: #ffffff; border: 2px solid #888; padding: 4px; border-radius: 6px;")
        layout.addSpacing(12); layout.addWidget(container_label); layout.addWidget(self.container_input)
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
        layout.addWidget(driver_label); layout.addWidget(self.driverno_input); layout.addSpacing(12)
        return layout

    def _create_keyboard(self):
        keypad_layout = QGridLayout(); keypad_layout.setHorizontalSpacing(7); keypad_layout.setVerticalSpacing(7)
        az_keys = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'; digit_keys = '1234567890'
        for idx, key in enumerate(az_keys):
            btn = QPushButton(key); btn.setFont(self.letter_font); btn.setFixedSize(55, 44)
            btn.clicked.connect(partial(self.add_keypad_text, key))
            keypad_layout.addWidget(btn, idx //7, idx % 7)
        for idx, key in enumerate(digit_keys):
            btn = QPushButton(key); btn.setFont(self.digit_font); btn.setFixedSize(55, 44)
            btn.clicked.connect(partial(self.add_keypad_text, key))
            keypad_layout.addWidget(btn, idx // 3, 7 + (idx % 3))
        back_btn = QPushButton("<--"); back_btn.setFont(self.digit_font); back_btn.setFixedSize(52, 52)
        back_btn.clicked.connect(self.keypad_backspace)
        keypad_layout.addWidget(back_btn, 3, 8)
        clear_btn = QPushButton("Clear"); clear_btn.setFont(self.digit_font); clear_btn.setFixedSize(92, 52)
        clear_btn.setStyleSheet("background-color: red; color: white; font-weight: bold;");
        clear_btn.clicked.connect(self.keypad_clear)
        keypad_layout.addWidget(clear_btn, 3, 10)
        centered_layout = QHBoxLayout(); centered_layout.addStretch(); centered_layout.addLayout(keypad_layout); centered_layout.addStretch()
        return centered_layout

    def _create_supplier_buttons(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(3, 1, 3, 1); layout.setSpacing(0)
        scroll_area = QScrollArea(); scroll_area.setWidgetResizable(True); scroll_area.setFixedHeight(36); scroll_area.setMaximumHeight(38)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded); scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_content = QWidget(); button_layout = QHBoxLayout(scroll_content)
        button_layout.setSpacing(5); button_layout.setContentsMargins(2, 1, 2, 1); button_layout.setAlignment(Qt.AlignLeft)
        self.supplier_button_group = QButtonGroup(self); self.supplier_button_group.setExclusive(True)
        try:
            self.suppliers_data = execute_query("SELECT suppliername, contactnumber, suppliercode FROM suppliers WHERE suppliername IS NOT NULL AND suppliername != '' ORDER BY suppliername")
            if isinstance(self.suppliers_data, list):
                for idx, sup in enumerate(self.suppliers_data):
                    btn = QPushButton(sup.get('suppliername')); btn.setFont(QFont("Arial", 11, QFont.Bold)); btn.setMinimumHeight(28); btn.setMaximumHeight(32)
                    btn.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed); btn.setCheckable(True)
                    btn.setStyleSheet("QPushButton { background-color: #FFFF99; border: 1px solid #BBB; border-radius: 5px; padding: 4px 12px; } QPushButton:checked { background-color: #C6DAFC; border: 2px solid #0053B3; }")
                    btn.adjustSize(); self.supplier_button_group.addButton(btn, idx); button_layout.addWidget(btn)
        except Exception as e: print(f"Error fetching suppliers: {e}")
        self.supplier_button_group.buttonClicked[int].connect(self._on_supplier_button_clicked)
        button_layout.addStretch(); scroll_area.setWidget(scroll_content); layout.addWidget(scroll_area)
        return layout

    def _on_supplier_button_clicked(self, button_id):
        try: self.selected_supplier = self.suppliers_data[button_id]
        except (IndexError, KeyError) as e: print(f"Error selecting supplier: {e}"); self.selected_supplier = None

    def _create_material_buttons(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(3, 1, 3, 1); layout.setSpacing(0)
        scroll_area = QScrollArea(); scroll_area.setWidgetResizable(True); scroll_area.setFixedHeight(36); scroll_area.setMaximumHeight(38)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded); scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_content = QWidget(); button_layout = QHBoxLayout(scroll_content)
        button_layout.setSpacing(5); button_layout.setContentsMargins(2, 1, 2, 1); button_layout.setAlignment(Qt.AlignLeft)
        self.material_button_group = QButtonGroup(self); self.material_button_group.setExclusive(True)
        try:
            self.materials_data = execute_query("SELECT materialname, materialcode FROM material ORDER BY materialname")
            if isinstance(self.materials_data, list):
                for idx, mat in enumerate(self.materials_data):
                    btn = QPushButton(mat.get('materialname')); btn.setFont(QFont("Arial", 11, QFont.Bold)); btn.setMinimumHeight(28); btn.setMaximumHeight(32)
                    btn.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed); btn.setCheckable(True)
                    btn.setStyleSheet("QPushButton { background-color: #FFFACD; border: 1px solid #BBB; border-radius: 5px; padding: 4px 12px; } QPushButton:checked { background-color: #C6DAFC; border: 2px solid #0053B3; }")
                    btn.adjustSize(); self.material_button_group.addButton(btn, idx); button_layout.addWidget(btn)
        except Exception as e: print(f"Error fetching materials: {e}")
        self.material_button_group.buttonClicked[int].connect(self._on_material_button_clicked)
        button_layout.addStretch(); scroll_area.setWidget(scroll_content); layout.addWidget(scroll_area)
        return layout

    def _on_material_button_clicked(self, button_id):
        try: self.selected_material = self.materials_data[button_id]
        except (IndexError, KeyError) as e: print(f"Error selecting material: {e}"); self.selected_material = None
    
    def _create_tare_picker(self):
        layout = QVBoxLayout()
        label = QLabel("Quick Tare / Recent Weights:"); label.setFont(QFont("Arial", 14, QFont.Bold)); layout.addWidget(label)
        grid = QGridLayout(); grid.setSpacing(8)
        shared_btn_style = "QPushButton { background-color: #2E86C1; color: white; border: 2px solid #1B4F72; border-radius: 10px; padding: 10px; min-height: 50px; } QPushButton:disabled { background-color: #cfd8e3; color: #6b7280; border: 2px solid #b0b9c8; }"
        self.vtare_btn = QPushButton("Vehicle Tare\n(—)"); self.vtare_btn.setFont(QFont("Arial", 15, QFont.Bold)); self.vtare_btn.setEnabled(False); self.vtare_btn.setStyleSheet(shared_btn_style)
        self.last_empty_btn = QPushButton("Last Empty\n(—)"); self.last_empty_btn.setFont(QFont("Arial", 15, QFont.Bold)); self.last_empty_btn.setEnabled(False); self.last_empty_btn.setStyleSheet(shared_btn_style)
        self.last_load_btn = QPushButton("Last Load\n(—)"); self.last_load_btn.setFont(QFont("Arial", 15, QFont.Bold)); self.last_load_btn.setEnabled(False); self.last_load_btn.setStyleSheet(shared_btn_style)
        self.vtare_btn.clicked.connect(lambda: self._apply_selected_tare(self._vtare_value))
        self.last_empty_btn.clicked.connect(lambda: self._apply_selected_tare(self._last_empty_value))
        self.last_load_btn.clicked.connect(lambda: self._apply_selected_tare(self._last_load_value))
        grid.addWidget(self.vtare_btn, 0, 0); grid.addWidget(self.last_empty_btn, 0, 1); grid.addWidget(self.last_load_btn, 0, 2)
        layout.addLayout(grid)
        return layout

    def _create_bottom_bar(self):
        bottom_layout = QHBoxLayout()
        self.cancel_btn = QPushButton("Cancel"); self.cancel_btn.setFont(self.font_button); self.cancel_btn.setMinimumHeight(48)
        self.cancel_btn.setStyleSheet("QPushButton {background: #fdd; border: 2px solid #a00; padding: 4px; font-size: 14pt; border-radius: 8px;}")
        bottom_layout.addStretch(); bottom_layout.addWidget(self.cancel_btn); bottom_layout.addStretch()
        return bottom_layout

    def _install_event_filters(self):
        self.vehicle_input.installEventFilter(self)
        self.container_input.installEventFilter(self)
        self.driverno_input.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.FocusIn:
            if obj in [self.vehicle_input, self.container_input, self.driverno_input]:
                self.last_focused_input = obj
        return super().eventFilter(obj, event)

    def _connect_signals(self):
        self.ok_btn.clicked.connect(self.ok_pressed)
        self.vehicle_input.textChanged.connect(self.check_vehicle_entry)
        self.cancel_btn.clicked.connect(self.cancel_action)
        self.get_tare_btn.clicked.connect(self.on_get_tare)

    def _initialize_state(self):
        self.update_weight_placeholders()
        self.vehicle_input.setFocus()
        self.last_focused_input = self.vehicle_input

    def _start_timers(self):
        self.update_date_time()
        timer = QTimer(self); timer.timeout.connect(self.update_date_time); timer.start(1000)

    def update_date_time(self):
        self.date_field.setText(to_display_date(QDate.currentDate()))
        self.time_field.setText(to_display_time(QTime.currentTime()))

    def generate_ticket_number(self):
        row = fetch_one('SELECT COALESCE(MAX(CAST("TicketNumber" AS INTEGER)), 0) + 1 AS next_ticket FROM tickets')
        return f"{int(row['next_ticket']):05d}" if row and row["next_ticket"] else "00001"

    def update_live_weight(self, weight):
        self.weight_display.setText(weight)
        self.update_weight_placeholders()

    def show_serial_error(self, message):
        QMessageBox.warning(self, "Serial Port Error", message)

    def closeEvent(self, event):
        self.camera_manager.stop()
        try:
            if hasattr(self, 'serial_manager'):
                self.serial_manager.release()
        except Exception:
            pass
        super().closeEvent(event)

    def add_keypad_text(self, char):
        if self.last_focused_input and not self.last_focused_input.isReadOnly():
            self.last_focused_input.insert(char)

    def keypad_backspace(self):
        if self.last_focused_input and not self.last_focused_input.isReadOnly():
            self.last_focused_input.backspace()
    
    def keypad_clear(self):
        self.vehicle_input.clear()
        self.container_input.clear()
        self.driverno_input.clear()
        self.check_vehicle_entry()
        self.vehicle_input.setFocus()

    def is_valid_indian_plate(self, text):
    # Always return a bool. Normalize input then test patterns.
        if not text:
            return False
        candidate = text.strip().upper().replace(" ", "").replace("-", "")
        patterns = [
            r'^[A-Z]{2}\d{2}[A-Z]{1,3}\d{4}$',
            r'^[A-Z]{2}\d{2}\d{4}$',
            r'^[A-Z]{3}\d{4}$',
            r'^[A-Z]{2}\d{4}$'
        ]
        return any(re.fullmatch(p, candidate) for p in patterns)


    def check_vehicle_entry(self):
        # Ensure vehicle input is uppercased and normalized, then compute bool is_valid
        plate_text = self.vehicle_input.text().upper()
        if self.vehicle_input.text() != plate_text:
            self.vehicle_input.blockSignals(True)
            cursor_pos = self.vehicle_input.cursorPosition()
            self.vehicle_input.setText(plate_text)
            self.vehicle_input.setCursorPosition(cursor_pos)
            self.vehicle_input.blockSignals(False)

        is_valid = bool(self.is_valid_indian_plate(plate_text))
        # pass an actual boolean to setEnabled to avoid TypeError
        self.ok_btn.setEnabled(is_valid)

        if is_valid:
            self.vehicle_input.setStyleSheet(
                "background: #d4edda; color: #155724; border: 2px solid #28a745; padding: 4px; border-radius: 8px;"
            )
        else:
            self.vehicle_input.setStyleSheet(
                "background: #f8d7da; color: #721c24; border: 2px solid #f5c6cb; padding: 4px; border-radius: 8px;"
            )

    def on_get_tare(self):
        term = self.vehicle_input.text().strip().upper()
        if not term:
            QMessageBox.warning(self, "Input Required", "Please enter a Vehicle Number first.")
            return

        vtare_row = fetch_one("SELECT vehicletareweight FROM vehiclemaster WHERE upper(vehiclenumber) = %s", (term,))
        self._vtare_value = vtare_row['vehicletareweight'] if vtare_row else None
        
        recent_tickets = fetch_all('SELECT "EmptyWeight", "LoadedWeight" FROM tickets WHERE upper("VehicleNumber") = %s ORDER BY "TicketNumber" DESC LIMIT 50', (term,))
        self._last_empty_value = next((r['EmptyWeight'] for r in recent_tickets if r['EmptyWeight']), None)
        self._last_load_value = next((r['LoadedWeight'] for r in recent_tickets if r['LoadedWeight']), None)

        self.vtare_btn.setText(f"Vehicle Tare\n({self._vtare_value or '—'})"); self.vtare_btn.setEnabled(bool(self._vtare_value))
        self.last_empty_btn.setText(f"Last Empty\n({self._last_empty_value or '—'})"); self.last_empty_btn.setEnabled(bool(self._last_empty_value))
        self.last_load_btn.setText(f"Last Load\n({self._last_load_value or '—'})"); self.last_load_btn.setEnabled(bool(self._last_load_value))

    def _apply_selected_tare(self, value):
        if value is None: return
        self.empty_weight_field.setText(str(int(float(value))))
        self._tare_weight_manually_set = True

    def ok_pressed(self):
        amounts = rate_calculator.calculate_amounts(self.selected_vehicle_type, self.weight_display.text(), self.load_status)
        if not amounts:
            QMessageBox.critical(self, "Rate Error", "Could not calculate rates for the selected vehicle type.")
            return
        
        e_val, l_val = amounts.get('eamount', 0), amounts.get('lamount', 0)
        self.eamount_field.setText(str(e_val)); self.lamount_field.setText(str(l_val)); self.tamount_field.setText(str(e_val + l_val))
        
        self.show_summary_dialog(e_val, l_val, e_val + l_val)

    def show_summary_dialog(self, eamount, lamount, tamount):
        try:
            ew_text = self.empty_weight_field.text(); lw_text = self.load_weight_field.text()
            ew = int(ew_text) if ew_text.isdigit() else 0
            lw = int(lw_text) if lw_text.isdigit() else 0
            driver_no_text = self.driverno_input.text().strip()
            driver_no = int(driver_no_text) if driver_no_text.isdigit() else None

            ticket_data = {
                "TicketNumber": self.ticket_number.text(),
                "VehicleNumber": self.vehicle_input.text().upper(),
                "VehicleType": self.selected_vehicle_type,
                "Date": to_db_date(QDate.currentDate()), "Time": to_db_time(QTime.currentTime()),
                "EmptyWeight": ew_text, "LoadedWeight": lw_text,
                "NetWeight": abs(lw - ew), "Status": self.load_status,
                "EAMOUNT": eamount, "LAMOUNT": lamount, "TAMOUNT": tamount,
                "Pending": False, "Closed": True, # Single transaction is always closed
                "ContainerNo": self.container_input.text().strip(),
                "DriverNo": driver_no,
                "SupplierName": self.selected_supplier.get('suppliername') if self.selected_supplier else None,
                "SupplierCode": self.selected_supplier.get('suppliercode') if self.selected_supplier else None,
                "Materialname": self.selected_material.get('materialname') if self.selected_material else None,
            }
            
            dlg = CommonSummaryDialog(self, ticket_data, is_first_load=False, transaction_window=self.mode_window)
            if dlg.exec_() == QDialog.Accepted:
                self.ticket_number.setText(self.generate_ticket_number())
                self.keypad_clear()
                self.empty_weight_field.clear(); self.load_weight_field.clear()
                self.eamount_field.setText("0"); self.lamount_field.setText("0"); self.tamount_field.setText("0")
                if self.supplier_button_group.checkedButton():
                    self.supplier_button_group.setExclusive(False); self.supplier_button_group.checkedButton().setChecked(False); self.supplier_button_group.setExclusive(True)
                if self.material_button_group.checkedButton():
                    self.material_button_group.setExclusive(False); self.material_button_group.checkedButton().setChecked(False); self.material_button_group.setExclusive(True)
                self.selected_supplier = None; self.selected_material = None
                self._tare_weight_manually_set = False

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to prepare summary:\n{traceback.format_exc()}")

    def update_weight_placeholders(self):
        current_weight = self.weight_display.text()
        if self.load_status.upper() == "EMPTY":
            self.empty_weight_field.setText(current_weight)
            self.load_weight_field.clear()
        else:
            if not self._tare_weight_manually_set:
                self.empty_weight_field.clear()
            self.load_weight_field.setText(current_weight)

    def cancel_action(self):
        if self.mode_window: self.mode_window.show()
        self.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    class MockModeWindow(QWidget):
        def __init__(self): super().__init__(); self.setWindowTitle("Main Menu"); self.resize(400,200)
        def show(self): super().show()
    
    mode_window = MockModeWindow()
    
    status_dialog = LoadStatusDialogThird()
    if status_dialog.exec_() == QDialog.Accepted:
        load_status = status_dialog.result
        vehicle_dialog = VehicleSelectionDialog()
        if vehicle_dialog.exec_() == QDialog.Accepted:
            vehicle_type = vehicle_dialog.result
            main_win = ThirdLoadWindow(load_status=load_status, vehicle_type=vehicle_type, mode_window=mode_window)
            main_win.show()
            sys.exit(app.exec_())
    sys.exit(0)
