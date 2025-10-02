import sys, traceback, os
from functools import partial
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QHBoxLayout, QGridLayout,
    QApplication, QDialog, QMessageBox, QFrame, QSizePolicy, QButtonGroup, QScrollArea
)
from PyQt5.QtCore import Qt, QDate, QTime, QTimer, QEvent
from PyQt5.QtGui import QFont, QIntValidator

# --- Centralized/Refactored Imports ---
from db_utils import fetch_one, execute_query
from date_time_utils import to_db_date, to_db_time, to_display_date, to_display_time
import rate_calculator
from camera_manager import CameraManager
from common_dialogs import CommonSummaryDialog
from first_load_window import VehicleSelectionDialog # For vehicle type selection if missing
from serial_manager import get_serial_manager
# Optional serial port integration
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

# --- SecondLoadWindow Class ---
class SecondLoadWindow(QWidget):
    def __init__(self, mode_window=None):
        super().__init__()
        self.setWindowTitle("Vehicle Second Transaction")
        self.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint)
        self.setStyleSheet("""
            background: #fff;
            QLineEdit:focus { 
                border: 2px solid #ff6600; 
                background: #fff7d6; 
            }
        """)
        self.setMinimumSize(1100, 700)

        self.first_load_data = None
        self.transaction_window = mode_window
        self.selected_supplier = None
        self.suppliers_data = []
        self.selected_material = None
        self.materials_data = []
        self.last_focused_input = None

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
        self.font_net_weight = QFont("Arial", 18, QFont.Bold)
        self.letter_font = QFont("Arial", 20, QFont.Bold)
        self.digit_font = QFont("Arial", 22, QFont.Bold)

    def _setup_ui(self):
        main_h_layout = QHBoxLayout(self)
        main_h_layout.setContentsMargins(15, 15, 15, 15)
        main_h_layout.setSpacing(15)

        controls_frame = QFrame()
        controls_layout = QVBoxLayout(controls_frame)
        controls_layout.setContentsMargins(0,0,0,0)
        controls_layout.setSpacing(10)
        controls_layout.setAlignment(Qt.AlignTop)

        top_bar_frame = QFrame(); top_bar_frame.setLayout(self._create_top_bar()); controls_layout.addWidget(top_bar_frame)
        vehicle_frame = QFrame(); vehicle_frame.setLayout(self._create_vehicle_entry()); controls_layout.addWidget(vehicle_frame)
        weight_frame = QFrame(); weight_frame.setLayout(self._create_weight_details()); controls_layout.addWidget(weight_frame)
        amount_frame = QFrame(); amount_frame.setLayout(self._create_amount_display()); controls_layout.addWidget(amount_frame)
        
        keypad_frame = QFrame(); keypad_frame.setLayout(self._create_keyboard()); controls_layout.addWidget(keypad_frame)
        
        supplier_buttons_layout = self._create_supplier_buttons()
        controls_layout.addLayout(supplier_buttons_layout)

        material_buttons_layout = self._create_material_buttons()
        controls_layout.addLayout(material_buttons_layout)

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
            print(f"Supplier selected for second load: {self.selected_supplier['suppliername']}")
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
                            QPushButton:checked { background-color: #C6DAFC; border: 2px solid #FF6600; }
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
        self.date_field = QLineEdit(); self.date_field.setFont(self.font_input); self.date_field.setReadOnly(True)
        layout.addWidget(date_label); layout.addWidget(self.date_field)
        time_label = QLabel("Time:"); time_label.setFont(self.font_label)
        self.time_field = QLineEdit(); self.time_field.setFont(self.font_input); self.time_field.setReadOnly(True)
        layout.addWidget(time_label); layout.addWidget(self.time_field); layout.addStretch()
        weight_label = QLabel("Weight (KG):"); weight_label.setFont(self.font_label)
        self.weight_display = QLabel("0"); self.weight_display.setFont(self.font_weight)
        self.weight_display.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.weight_display.setStyleSheet("color:white; background:black; border-radius: 10px; padding: 4px 32px; min-width: 200px;")
        layout.addWidget(weight_label); layout.addWidget(self.weight_display)
        return layout

    def _create_vehicle_entry(self):
        layout = QHBoxLayout()
        search_label = QLabel("Search Ticket/Vehicle:"); search_label.setFont(self.font_label)
        self.search_input = QLineEdit(); self.search_input.setFont(QFont("Arial", 22, QFont.Bold))
        layout.addWidget(search_label); layout.addWidget(self.search_input)
        self.ok_btn = QPushButton("OK"); self.ok_btn.setFont(QFont("Arial", 16, QFont.Bold)); self.ok_btn.setMinimumHeight(48)
        self.ok_btn.setStyleSheet("padding: 0 5px; background-color: #c6ffc6; border: 2px solid #0b0; border-radius: 8px;")
        layout.addWidget(self.ok_btn); layout.addStretch()
        return layout

    def _create_weight_details(self):
        layout = QGridLayout()
        layout.setSpacing(10)

        self.empty_weight_label = QLabel("Empty:"); self.empty_weight_label.setFont(self.font_label)
        self.empty_weight_field = QLineEdit(); self.empty_weight_field.setFont(self.font_amount); self.empty_weight_field.setReadOnly(True)
        layout.addWidget(self.empty_weight_label, 0, 0); layout.addWidget(self.empty_weight_field, 0, 1)

        self.load_weight_label = QLabel("Load:"); self.load_weight_label.setFont(self.font_label)
        self.load_weight_field = QLineEdit(); self.load_weight_field.setFont(self.font_amount); self.load_weight_field.setReadOnly(True)
        layout.addWidget(self.load_weight_label, 0, 2); layout.addWidget(self.load_weight_field, 0, 3)

        net_label = QLabel("Net Weight:"); net_label.setFont(self.font_net_weight)
        self.net_weight_field = QLineEdit(); self.net_weight_field.setFont(self.font_net_weight); self.net_weight_field.setReadOnly(True)
        layout.addWidget(net_label, 0, 4); layout.addWidget(self.net_weight_field, 0, 5)

        self.container_label = QLabel("Container No:"); self.container_label.setFont(self.font_label)
        self.container_input = QLineEdit(); self.container_input.setFont(self.font_amount)
        self.container_input.setStyleSheet("background: #ffffff; border: 2px solid #888; padding: 4px; border-radius: 6px;")
        layout.addWidget(self.container_label, 1, 0); layout.addWidget(self.container_input, 1, 1)

        driver_label = QLabel("Driver No:"); driver_label.setFont(self.font_label)
        self.driverno_input = QLineEdit(); self.driverno_input.setFont(QFont("Arial", 18));
        self.driverno_input.setStyleSheet("background: #ffffff; border: 2px solid #888; padding: 4px; border-radius: 6px;")
        self.driverno_input.setValidator(QIntValidator())
        layout.addWidget(driver_label, 1, 2); layout.addWidget(self.driverno_input, 1, 3)

        return layout

    def _create_amount_display(self):
        layout = QHBoxLayout()
        eamount_label = QLabel("E-Amount:"); eamount_label.setFont(self.font_label)
        self.eamount_input = QLineEdit(); self.eamount_input.setFont(self.font_amount); self.eamount_input.setReadOnly(True)
        layout.addWidget(eamount_label); layout.addWidget(self.eamount_input)
        lamount_label = QLabel("L-Amount:"); lamount_label.setFont(self.font_label)
        self.lamount_input = QLineEdit(); self.lamount_input.setFont(self.font_amount); self.lamount_input.setReadOnly(True)
        layout.addWidget(lamount_label); layout.addWidget(self.lamount_input)
        tamount_label = QLabel("T-Amount:"); tamount_label.setFont(self.font_label)
        self.tamount_input = QLineEdit(); self.tamount_input.setFont(self.font_amount); self.tamount_input.setReadOnly(True)
        layout.addWidget(tamount_label); layout.addWidget(self.tamount_input)
        layout.addStretch()
        return layout

    def _create_keyboard(self):
        keypad_layout = QGridLayout(); keypad_layout.setHorizontalSpacing(10); keypad_layout.setVerticalSpacing(5)
        az_keys = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'; digit_keys = '1234567890'
        
        for idx, key in enumerate(az_keys):
            btn = QPushButton(key); btn.setFont(self.letter_font); btn.setFixedSize(52, 52)
            btn.clicked.connect(partial(self.add_keypad_text, key))
            keypad_layout.addWidget(btn, idx // 7, idx % 7)
            
        for idx, key in enumerate(digit_keys):
            btn = QPushButton(key); btn.setFont(self.digit_font); btn.setFixedSize(52, 52)
            btn.clicked.connect(partial(self.add_keypad_text, key))
            keypad_layout.addWidget(btn, idx // 3, 7 + (idx % 3))
            
        back_btn = QPushButton("<--"); back_btn.setFont(self.digit_font); back_btn.setFixedSize(52, 52)
        back_btn.clicked.connect(self.keypad_backspace)
        keypad_layout.addWidget(back_btn, 3, 8)
        
        clear_btn = QPushButton("Clear"); clear_btn.setFont(self.digit_font); clear_btn.setFixedSize(92, 52)
        clear_btn.setStyleSheet("background-color: red; color: white; font-weight: bold;")
        clear_btn.clicked.connect(self.clear_all_fields)
        keypad_layout.addWidget(clear_btn, 3, 10)
        
        centered_layout = QHBoxLayout(); centered_layout.addStretch(); centered_layout.addLayout(keypad_layout); centered_layout.addStretch()
        return centered_layout

    def _create_bottom_bar(self):
        bottom_layout = QHBoxLayout(); bottom_layout.setSpacing(10)
        self.cancel_btn = QPushButton("Cancel"); self.cancel_btn.setFont(self.font_button); self.cancel_btn.setFixedSize(150, 48)
        self.cancel_btn.setStyleSheet("QPushButton { background: #fdd; border: 2px solid #a00; padding: 4px; font-size: 14pt; border-radius: 8px; }")
        bottom_layout.addStretch(); bottom_layout.addWidget(self.cancel_btn); bottom_layout.addStretch()
        return bottom_layout

    def _install_event_filters(self):
        self.search_input.installEventFilter(self)
        self.container_input.installEventFilter(self)
        self.driverno_input.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.FocusIn:
            if obj in [self.search_input, self.container_input, self.driverno_input]:
                self.last_focused_input = obj
        return super().eventFilter(obj, event)

    def _connect_signals(self):
        self.ok_btn.clicked.connect(self.ok_pressed)
        self.cancel_btn.clicked.connect(self.cancel_action)

    def _initialize_state(self):
        self.search_input.setFocus()
        self.last_focused_input = self.search_input

    def _start_timers(self):
        self.update_date_time()
        timer = QTimer(self); timer.timeout.connect(self.update_date_time); timer.start(1000)

    def update_date_time(self):
        self.date_field.setText(to_display_date(QDate.currentDate()))
        self.time_field.setText(to_display_time(QTime.currentTime()))
    
    def update_live_weight(self, weight):
        self.weight_display.setText(weight)

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

    def clear_all_fields(self):
        for field in [self.search_input, self.empty_weight_field, self.load_weight_field, 
                      self.net_weight_field, self.eamount_input, self.lamount_input, 
                      self.tamount_input, self.container_input, self.driverno_input]:
            if isinstance(field, QLineEdit):
                field.clear()
        
        self.search_input.setReadOnly(False)
        self.search_input.setStyleSheet("")
        self.first_load_data = None
        self.selected_supplier = None
        self.selected_material = None
        
        if self.supplier_button_group.checkedButton():
            self.supplier_button_group.setExclusive(False)
            self.supplier_button_group.checkedButton().setChecked(False)
            self.supplier_button_group.setExclusive(True)
            
        if self.material_button_group.checkedButton():
            self.material_button_group.setExclusive(False)
            self.material_button_group.checkedButton().setChecked(False)
            self.material_button_group.setExclusive(True)
            
        self.search_input.setFocus()

    def prefill_for_second_load(self, ticket_number):
        self.search_input.setText(str(ticket_number))
        self.search_input.setReadOnly(True)
        self.ok_pressed()

    def ok_pressed(self):
        search_term = self.search_input.text().strip().upper()
        if not search_term:
            QMessageBox.warning(self, "Input Required", "Please enter a Ticket Number or Vehicle Number to search.")
            return
        
        data = None
        if search_term.isdigit():
            data = fetch_one('SELECT * FROM tickets WHERE "TicketNumber" = %s AND "Pending" = TRUE', (search_term,))
        if not data:
            data = fetch_one('SELECT * FROM tickets WHERE "VehicleNumber" = %s AND "Pending" = TRUE', (search_term,))

        if not data:
            QMessageBox.warning(self, "Not Found", "No pending ticket found for the provided details.")
            self.clear_all_fields()
            return

        if data.get("Closed"):
            QMessageBox.warning(self, "Ticket Closed", f"Ticket {data['TicketNumber']} is already closed.")
            self.clear_all_fields()
            return
            
        self.first_load_data = data
        self.search_input.setText(f"{data['TicketNumber']} / {data['VehicleNumber']}")
        self.search_input.setReadOnly(True)
        self.search_input.setStyleSheet("background: #e8f8e8; border: 2px solid #008000;")

        vehicle_type = data.get("VehicleType")
        if not vehicle_type:
            QMessageBox.information(self, "Vehicle Type Required", "This ticket is missing a Vehicle Type. Please select one to continue.")
            dialog = VehicleSelectionDialog(self)
            if dialog.exec_() == QDialog.Accepted:
                vehicle_type = dialog.result
                try:
                    execute_query('UPDATE "tickets" SET "VehicleType" = %s WHERE "TicketNumber" = %s', (vehicle_type, data['TicketNumber']))
                    data['VehicleType'] = vehicle_type
                except Exception as e:
                    QMessageBox.critical(self, "Database Error", f"Could not update vehicle type for ticket:\n{e}")
                    self.clear_all_fields(); return
            else:
                self.clear_all_fields(); return

        try:
            current_weight = int(float(self.weight_display.text()))
        except (ValueError, TypeError):
            QMessageBox.critical(self, "Weight Error", "Invalid weight from the weighbridge.")
            return

        # --- FIX: Correctly handle integer/None from database ---
        db_empty = data.get("EmptyWeight")
        db_load = data.get("LoadedWeight")
        
        final_empty, final_load, load_status_for_calc = (0, 0, "")

        if db_empty is not None and db_load is None:
            final_empty, final_load, load_status_for_calc = int(db_empty), current_weight, "Load"
        elif db_load is not None and db_empty is None:
            final_empty, final_load, load_status_for_calc = current_weight, int(db_load), "Empty"
        else:
            QMessageBox.warning(self, "Ticket Error", "This ticket is in an invalid state (both weights are present or missing).")
            self.clear_all_fields(); return
        
        self.empty_weight_field.setText(str(final_empty))
        self.load_weight_field.setText(str(final_load))
        self.net_weight_field.setText(str(abs(final_load - final_empty)))
        
        new_amounts = rate_calculator.calculate_amounts(vehicle_type, current_weight, load_status_for_calc)
        final_eamount = (data.get("EAMOUNT") or 0) + new_amounts.get('eamount', 0)
        final_lamount = (data.get("LAMOUNT") or 0) + new_amounts.get('lamount', 0)
        final_tamount = final_eamount + final_lamount
        
        self.eamount_input.setText(str(final_eamount))
        self.lamount_input.setText(str(final_lamount))
        self.tamount_input.setText(str(final_tamount))
        self.container_input.setText(str(data.get("ContainerNo") or ""))
        self.driverno_input.setText(str(data.get("DriverNo") or ""))

        summary_data = {
            "TicketNumber": data.get("TicketNumber"),
            "Date": to_db_date(QDate.currentDate()), "Time": to_db_time(QTime.currentTime()),
            "LAST DATE": data.get("Date"), "LAST TIME": data.get("Time"),
            "VehicleNumber": data.get("VehicleNumber"), "VehicleType": vehicle_type,
            "EmptyWeight": final_empty, "LoadedWeight": final_load,
            "NetWeight": abs(final_load - final_empty),
            "EAMOUNT": final_eamount, "LAMOUNT": final_lamount, "TAMOUNT": final_tamount,
            "ContainerNo": self.container_input.text().strip() or data.get("ContainerNo"),
            "SnapshotPath": data.get("SnapshotPath"),
            "SupplierName": self.selected_supplier.get('suppliername') if self.selected_supplier else data.get('suppliername'),
            "SupplierCode": self.selected_supplier.get('suppliercode') if self.selected_supplier else data.get('suppliercode'),
            "Materialname": self.selected_material.get('materialname') if self.selected_material else data.get('materialname'),
            "DriverNo": int(self.driverno_input.text()) if self.driverno_input.text().strip().isdigit() else data.get("DriverNo"),
        }
        
        # FIX: Remove the unexpected keyword argument 'selected_supplier'
        dlg = CommonSummaryDialog(self, summary_data, is_first_load=False, transaction_window=self.transaction_window)
        if dlg.exec_() == QDialog.Accepted:
            self.clear_all_fields()

    def cancel_action(self):
        if self.transaction_window: self.transaction_window.show()
        self.close()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = SecondLoadWindow()
    win.show()
    sys.exit(app.exec_())
