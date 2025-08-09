import re, sys, random, psycopg2, traceback, os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QHBoxLayout, QGridLayout, QButtonGroup,
    QApplication, QSizePolicy, QMessageBox, QDialog, QFrame, QScrollArea, QSpacerItem
)
from PyQt5.QtCore import Qt, QDate, QTime, QTimer, QLocale
from PyQt5.QtGui import QFont, QIntValidator, QPixmap
from db_utils import execute_query, fetch_one, fetch_all, get_new_connection
from ticket_preview_window import TicketPreviewDialog
from print_ticket_with_template_win32 import print_ticket_with_template
from date_time_utils import to_db_date, to_db_time, to_display_date, to_display_time
import rate_calculator # Import the new rate calculator

# --- DATABASE AND UTILITY FUNCTIONS (Unchanged) ---
def get_ticket_columns():
    rows = fetch_all("SELECT column_name FROM information_schema.columns WHERE table_name='tickets'")
    return set(r["column_name"] for r in rows)

def get_ticket_column_types():
    rows = fetch_all("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='tickets'")
    return {r["column_name"]: r["data_type"] for r in rows}

def unified_save_ticket(params):
    ticket_columns = get_ticket_columns()
    filtered_params = {k: v for k, v in params.items() if k in ticket_columns}
    ticket_column_types = get_ticket_column_types()
    for k in list(filtered_params.keys()):
        if k in ticket_column_types and ticket_column_types[k] in ("integer", "bigint", "smallint"):
            if filtered_params[k] in ("", None): filtered_params[k] = None
            else:
                try: filtered_params[k] = int(filtered_params[k])
                except Exception: filtered_params[k] = None
    set_clause = ", ".join([f'"{k}" = %({k})s' for k in filtered_params.keys()])
    insert_columns = ', '.join([f'"{k}"' for k in filtered_params.keys()])
    insert_values = ', '.join([f'%({k})s' for k in filtered_params.keys()])
    query = f"""
    INSERT INTO tickets ({insert_columns}) VALUES ({insert_values})
    ON CONFLICT ("TicketNumber") DO UPDATE SET {set_clause}
    """
    execute_query(query, filtered_params)

def get_default_template_and_fields():
    tpl_row = fetch_one('SELECT templatename, ticketheight, ticketwidth FROM templatemaster WHERE defaulttemplate=TRUE')
    if not tpl_row: raise Exception("No default template set in DB")
    templatename, ticket_height, ticket_width = tpl_row['templatename'], float(tpl_row['ticketheight']), float(tpl_row['ticketwidth'])
    fields = execute_query('SELECT fieldname, x, y, width, height, fontname, fontsize FROM templatefields WHERE templatename=%s ORDER BY id', (templatename,))
    template_fields = [{'fieldname': str(f[0]), 'x': float(f[1]), 'y': float(f[2]), 'width': float(f[3]), 'height': float(f[4]), 'fontname': str(f[5]), 'fontsize': int(f[6])} for f in fields]
    return template_fields, ticket_width, ticket_height

# --- DIALOGS (Updated to be resizable/aligned) ---
class OldWeightDialog(QDialog):
    def __init__(self, parent, ticket_number, vehicle_number):
        super().__init__(parent)
        self.setWindowTitle("OLD WEIGHT")
        self.setWindowModality(Qt.ApplicationModal)
        self.setStyleSheet("background-color: black; color: white;")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.resize(500, 500)

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

class SummaryDialog(QDialog):
    def __init__(self, parent, ticket_no, date, time, vehicle_number, weight, vehicle_type, status, eamount, lamount, tamount, transaction_window=None):
        super().__init__(parent)
        self.setWindowTitle("Summary & Finalize")
        self.setStyleSheet("background-color: black; color: white;")
        self.setWindowModality(Qt.ApplicationModal)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.resize(720, 780)
        self.transaction_window = transaction_window
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        title_font = QFont("Arial", 20, QFont.Bold)
        label_font = QFont("Arial", 16)
        amount_font = QFont("Arial", 18, QFont.Bold)
        button_font = QFont("Arial", 16, QFont.Bold)

        # --- Info Grid ---
        info_grid = QGridLayout()
        info_grid.setSpacing(10)
        def add_info(row, col, label, value):
            lab = QLabel(label); lab.setFont(label_font)
            val = QLabel(str(value)); val.setFont(label_font); val.setStyleSheet("color: #aaffff;")
            lab.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            val.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            info_grid.addWidget(lab, row, col*2); info_grid.addWidget(val, row, col*2+1)
        
        add_info(0, 0, "Ticket No:", ticket_no); add_info(0, 1, "Date:", to_display_date(date))
        add_info(1, 0, "Vehicle Number:", vehicle_number); add_info(1, 1, "Time:", to_display_time(time))
        add_info(2, 0, "Vehicle Type:", vehicle_type); add_info(2, 1, "Weight (KG):", weight)
        add_info(3, 0, "Status:", status)
        main_layout.addLayout(info_grid)
        main_layout.addWidget(QFrame(self, frameShape=QFrame.HLine, frameShadow=QFrame.Sunken))

        # --- Amount Controls ---
        amount_layout = QGridLayout()
        amount_layout.setSpacing(10)
        # E-Amount
        e_label = QLabel("E-Amount:"); e_label.setFont(label_font)
        self.eamount_field = QLineEdit(str(eamount)); self.eamount_field.setFont(amount_font); self.eamount_field.setAlignment(Qt.AlignCenter); self.eamount_field.setMinimumWidth(120)
        e_minus_btn = QPushButton("-"); e_plus_btn = QPushButton("+")
        for btn in [e_minus_btn, e_plus_btn]: btn.setFont(button_font); btn.setMinimumSize(50, 50)
        amount_layout.addWidget(e_label, 0, 0); amount_layout.addWidget(e_minus_btn, 0, 1); amount_layout.addWidget(self.eamount_field, 0, 2); amount_layout.addWidget(e_plus_btn, 0, 3)

        # L-Amount
        l_label = QLabel("L-Amount:"); l_label.setFont(label_font)
        self.lamount_field = QLineEdit(str(lamount)); self.lamount_field.setFont(amount_font); self.lamount_field.setAlignment(Qt.AlignCenter); self.lamount_field.setMinimumWidth(120)
        l_minus_btn = QPushButton("-"); l_plus_btn = QPushButton("+")
        for btn in [l_minus_btn, l_plus_btn]: btn.setFont(button_font); btn.setMinimumSize(50, 50)
        amount_layout.addWidget(l_label, 1, 0); amount_layout.addWidget(l_minus_btn, 1, 1); amount_layout.addWidget(self.lamount_field, 1, 2); amount_layout.addWidget(l_plus_btn, 1, 3)

        # T-Amount
        t_label = QLabel("T-Amount:"); t_label.setFont(label_font)
        self.tamount_display = QLabel(str(tamount)); self.tamount_display.setFont(amount_font); self.tamount_display.setMinimumWidth(120); self.tamount_display.setAlignment(Qt.AlignCenter)
        amount_layout.addWidget(t_label, 2, 0); amount_layout.addWidget(self.tamount_display, 2, 2)
        
        main_layout.addLayout(amount_layout)

        # Signals for amount changes
        e_minus_btn.clicked.connect(lambda: self._modify_amount(self.eamount_field, -5))
        e_plus_btn.clicked.connect(lambda: self._modify_amount(self.eamount_field, 5))
        l_minus_btn.clicked.connect(lambda: self._modify_amount(self.lamount_field, -5))
        l_plus_btn.clicked.connect(lambda: self._modify_amount(self.lamount_field, 5))
        self.eamount_field.textChanged.connect(self._update_tamount)
        self.lamount_field.textChanged.connect(self._update_tamount)

        main_layout.addStretch()

        # --- Bottom Buttons ---
        btn_row = QHBoxLayout()
        self.wp_btn = QPushButton("Weigh & Print"); self.wp_btn.setFont(button_font); self.wp_btn.setMinimumHeight(60); self.wp_btn.setStyleSheet("background: #006400; color: white; border-radius: 8px;")
        self.wp_btn.clicked.connect(self.on_weightprint); btn_row.addWidget(self.wp_btn)
        self.cancel_btn = QPushButton("Cancel"); self.cancel_btn.setFont(button_font); self.cancel_btn.setMinimumHeight(60); self.cancel_btn.setStyleSheet("background: #8B0000; color: white; border-radius: 8px;")
        self.cancel_btn.clicked.connect(self.on_cancel); btn_row.addWidget(self.cancel_btn)
        main_layout.addLayout(btn_row)
        
        self.success_label = QLabel("", self); self.success_label.setAlignment(Qt.AlignCenter); self.success_label.setFont(title_font); self.success_label.setStyleSheet("color: #00ff00;")
        main_layout.addWidget(self.success_label)
        
        self.ticket_no, self.date, self.time, self.vehicle_number, self.vehicle_type, self.weight, self.status = ticket_no, date, time, vehicle_number, vehicle_type, weight, status
        self._preview_dialog, self._print_timer, self._finish_timer = None, None, None
        self._update_tamount() # Initial calculation

    def _modify_amount(self, line_edit, delta):
        try: current_value = int(line_edit.text())
        except ValueError: current_value = 0
        new_value = max(0, current_value + delta)
        line_edit.setText(str(new_value))

    def _update_tamount(self):
        try: e_val = int(self.eamount_field.text())
        except ValueError: e_val = 0
        try: l_val = int(self.lamount_field.text())
        except ValueError: l_val = 0
        self.tamount_display.setText(str(e_val + l_val))

    def on_weightprint(self):
        try:
            blank_to_none = lambda val: None if val in ("", None) else int(float(val))
            ticket_number = int(str(self.ticket_no).lstrip('0') or '0')
            now_date, now_time = QDate.currentDate(), QTime.currentTime()
            date, time = to_db_date(now_date), to_db_time(now_time)
            vehicle_number, status = self.vehicle_number, self.status.strip().upper()
            
            eamount = blank_to_none(self.eamount_field.text())
            lamount = blank_to_none(self.lamount_field.text())
            tamount = blank_to_none(self.tamount_display.text())
            
            empty_weight = blank_to_none(self.weight) if status == "EMPTY" else None
            loaded_weight = blank_to_none(self.weight) if status == "LOAD" else None
            net_weight = loaded_weight - empty_weight if empty_weight is not None and loaded_weight is not None else (loaded_weight or empty_weight)
            
            params = {
                "TicketNumber": ticket_number, "VehicleNumber": vehicle_number, "VehicleType": self.vehicle_type,
                "Date": date, "Time": time, "EmptyWeight": empty_weight, "LoadedWeight": loaded_weight, 
                "EmptyWeightDate": date if status == "EMPTY" else None, "EmptyWeightTime": time if status == "EMPTY" else None, 
                "LoadWeightDate": date if status == "LOAD" else None, "LoadWeightTime": time if status == "LOAD" else None, 
                "NetWeight": net_weight, "Pending": bool(empty_weight) ^ bool(loaded_weight), 
                "Closed": bool(empty_weight and loaded_weight), "Exported": False, "Shift": "B", 
                "Materialname": "", "SupplierName": "", "State": "first transaction", "Blank": None, 
                "AMOUNT": None, "STATUS": self.status, "EAMOUNT": eamount, "LAMOUNT": lamount, "TAMOUNT": tamount, 
                "NetWeight1": None, "LWEIGHT": None, "EWEIGHT": None
            }
            unified_save_ticket(params)
            
            self.ticket_data = {
                "TicketNumber": f"{ticket_number:05d}", "VehicleNumber": vehicle_number, "VehicleType": self.vehicle_type,
                "Date": to_display_date(date), "Time": to_display_time(time), "EmptyWeight": empty_weight or "", 
                "LoadedWeight": loaded_weight or "", "NetWeight": net_weight or "", "Materialname": "", 
                "SupplierName": "", "State": "first transaction", "AMOUNT": "", "STATUS": self.status, 
                "EAMOUNT": eamount or "", "LAMOUNT": lamount or "", "TAMOUNT": tamount or "", 
                "NetWeight1": "", "LWEIGHT": "", "EWEIGHT": ""
            }
            self.wp_btn.setVisible(False); self.success_label.setText("TICKET SAVED!")
            self._preview_dialog = TicketPreviewDialog(self.ticket_data, parent=self); self._preview_dialog.show()
            self.print_preview_timer = QTimer(self); self.print_preview_timer.setSingleShot(True); self.print_preview_timer.timeout.connect(self._do_print_ticket); self.print_preview_timer.start(3000)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save/print ticket:\n{e}\n\n{traceback.format_exc()}")

    def _do_print_ticket(self):
        if self._preview_dialog: self._preview_dialog.close()
        self.success_label.setText("Printing ticket..."); print_ticket_with_template(self.ticket_data, get_new_connection())
        self._finish_timer = QTimer(self); self._finish_timer.setSingleShot(True); self._finish_timer.timeout.connect(self._finish_and_goto_transaction); self._finish_timer.start(2000)
    def _finish_and_goto_transaction(self):
        self.accept()
        if self.transaction_window: parent = self.parent(); parent.close() if parent else None; self.transaction_window.show()
        else: self.parent().show() if self.parent() else None
    def on_cancel(self):
        self.reject()
        if self.transaction_window: parent = self.parent(); parent.close() if parent else None; self.transaction_window.show()
        else: self.parent().show() if self.parent() else None

class LoadStatusDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Step 1: Select Load Status")
        self.setWindowModality(Qt.ApplicationModal)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.resize(420, 240)
        self.result = None

        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignCenter)
        label = QLabel("Select the vehicle's load status:"); label.setFont(QFont("Arial", 14)); label.setAlignment(Qt.AlignCenter); layout.addWidget(label)
        btn_layout = QHBoxLayout(); self.empty_btn = QPushButton("Empty"); self.load_btn = QPushButton("Load")
        for btn in [self.empty_btn, self.load_btn]:
            btn.setFont(QFont("Arial", 18, QFont.Bold))
            btn.setMinimumSize(150, 60)
            btn_layout.addWidget(btn)
        layout.addLayout(btn_layout)
        self.empty_btn.clicked.connect(lambda: self.set_result("Empty")); self.load_btn.clicked.connect(lambda: self.set_result("Load"))
    def set_result(self, status): self.result = status; self.accept()

class VehicleSelectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Step 2: Select Vehicle Type")
        self.setWindowModality(Qt.ApplicationModal)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.resize(700, 560)
        self.result = None

        main_layout = QVBoxLayout(self)
        label = QLabel("Select the Vehicle Type:"); label.setFont(QFont("Arial", 14)); label.setAlignment(Qt.AlignCenter); main_layout.addWidget(label)
        
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        main_layout.addWidget(scroll_area)
        
        scroll_content = QWidget()
        vehicles_grid = QGridLayout(scroll_content)
        vehicles_grid.setSpacing(10)
        self.vehicle_btn_group = QButtonGroup(self)
        
        try:
            vehicle_options = rate_calculator.get_all_vehicle_rates()
            for idx, vehicle_data in enumerate(vehicle_options):
                vehicle_name = vehicle_data['vehiclename']
                btn = QPushButton(vehicle_name)
                btn.setFont(QFont("Arial", 12, QFont.Bold))
                btn.setCheckable(True)
                btn.setMinimumHeight(60)
                btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
                self.vehicle_btn_group.addButton(btn, idx)
                vehicles_grid.addWidget(btn, idx // 2, idx % 2)
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Could not load vehicle types from ratechart: {e}")
            QTimer.singleShot(0, self.reject)

        scroll_area.setWidget(scroll_content)
        self.vehicle_btn_group.buttonClicked[int].connect(self.on_vehicle_selected)

    def on_vehicle_selected(self, button_id):
        vehicle_options = rate_calculator.get_all_vehicle_rates()
        self.result = vehicle_options[button_id]['vehiclename']
        self.accept()

def is_valid_indian_plate(text): return any(re.fullmatch(p, text.upper()) for p in [r'^[A-Z]{2}\d{2}[A-Z]{1,3}\d{4}$', r'^[A-Z]{2}\d{2}[A-Z]{0,2}\d{4}$', r'^[A-Z]{3}\d{4}$', r'^[A-Z]{2}\d{4}$'])

class FirstLoadWindow(QWidget):
    def __init__(self, load_status, vehicle_type, mode_window=None):
        super().__init__()
        self.setWindowTitle("Vehicle First Transaction")
        # Make the main window resizable and allow maximize
        self.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint)
        self.setStyleSheet("background: #fff;")
        self.mode_window = mode_window
        self.load_status = load_status
        self.selected_vehicle_type = vehicle_type
        self.setMinimumSize(1100, 700)
        self.resize(1600, 900)
        self._define_fonts(); self._setup_ui(); self._connect_signals(); self._initialize_state(); self._start_timers(); self.centerOnScreen()
    def _define_fonts(self):
        self.font_label = QFont("Arial", 14, QFont.Bold); self.font_input = QFont("Arial", 18); self.font_weight = QFont("Arial", 28, QFont.Bold)
        self.font_button = QFont("Arial", 18, QFont.Bold); self.font_amount = QFont("Arial", 18, QFont.Bold); self.letter_font = QFont("Arial", 20, QFont.Bold); self.digit_font = QFont("Arial", 22, QFont.Bold)
    def _setup_ui(self):
        main_h_layout = QHBoxLayout(self); main_h_layout.setContentsMargins(15, 15, 15, 15); main_h_layout.setSpacing(15)
        controls_frame = QFrame(); controls_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        controls_layout = QVBoxLayout(controls_frame); controls_layout.setContentsMargins(0,0,0,0); controls_layout.setSpacing(10); controls_layout.setAlignment(Qt.AlignTop)
        top_bar_frame = QFrame(); top_bar_frame.setFrameShape(QFrame.StyledPanel); top_bar_frame.setLayout(self._create_top_bar())
        controls_layout.addWidget(top_bar_frame)
        vehicle_frame = QFrame(); vehicle_frame.setFrameShape(QFrame.StyledPanel); vehicle_frame.setLayout(self._create_vehicle_entry())
        controls_layout.addWidget(vehicle_frame)
        weight_frame = QFrame(); weight_frame.setFrameShape(QFrame.StyledPanel); weight_frame.setLayout(self._create_weight_details())
        controls_layout.addWidget(weight_frame)
        
        amount_frame = QFrame(); amount_frame.setFrameShape(QFrame.StyledPanel); amount_frame.setLayout(self._create_amount_details())
        controls_layout.addWidget(amount_frame)

        info_frame = QFrame(); info_frame.setFrameShape(QFrame.StyledPanel); info_frame.setLayout(self._create_info_display())
        controls_layout.addWidget(info_frame)
        keypad_frame = QFrame(); keypad_frame.setFrameShape(QFrame.StyledPanel); keypad_frame.setLayout(self._create_keyboard())
        controls_layout.addWidget(keypad_frame); controls_layout.addStretch()
        bottom_frame = QFrame(); bottom_frame.setLayout(self._create_bottom_bar()); controls_layout.addWidget(bottom_frame, alignment=Qt.AlignHCenter)
        main_h_layout.addWidget(controls_frame, 1)
        camera_frame = QFrame(); camera_frame.setFrameShape(QFrame.StyledPanel); camera_frame.setStyleSheet("QFrame { background-color: black; border: 2px solid #555; border-radius: 8px; }")
        camera_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        camera_layout = QVBoxLayout(camera_frame); camera_label = QLabel("CAMERA FEED"); camera_label.setAlignment(Qt.AlignCenter); camera_label.setFont(QFont("Arial", 24, QFont.Bold)); camera_label.setStyleSheet("color: white;")
        camera_layout.addWidget(camera_label); main_h_layout.addWidget(camera_frame, 2)
    def _create_top_bar(self):
        layout = QHBoxLayout(); date_label = QLabel("Date:"); date_label.setFont(self.font_label); self.date_field = QLineEdit(); self.date_field.setFont(self.font_input); self.date_field.setReadOnly(True); self.date_field.setFixedWidth(170)
        layout.addWidget(date_label); layout.addWidget(self.date_field); layout.addSpacing(20)
        ticket_label = QLabel("Ticket No:"); ticket_label.setFont(self.font_label); self.ticket_number = QLineEdit(self.generate_ticket_number()); self.ticket_number.setFont(self.font_input); self.ticket_number.setReadOnly(True); self.ticket_number.setFixedWidth(110)
        layout.addWidget(ticket_label); layout.addWidget(self.ticket_number); layout.addStretch()
        weight_label = QLabel("Weight (KG):"); weight_label.setFont(self.font_label); self.weight_display = QLabel(self.get_fake_weight()); self.weight_display.setFont(self.font_weight); self.weight_display.setAlignment(Qt.AlignRight | Qt.AlignVCenter); self.weight_display.setStyleSheet("color:white; background:black; border-radius: 10px; padding: 4px 32px; min-width: 200px;")
        layout.addWidget(weight_label); layout.addWidget(self.weight_display); return layout
    def _create_vehicle_entry(self):
        layout = QHBoxLayout(); time_label = QLabel("Time:"); time_label.setFont(self.font_label); self.time_field = QLineEdit(); self.time_field.setFont(self.font_input); self.time_field.setReadOnly(True); self.time_field.setFixedWidth(130)
        layout.addWidget(time_label); layout.addWidget(self.time_field); layout.addSpacing(15)
        vehicle_label = QLabel("Vehicle:"); vehicle_label.setFont(self.font_label); self.vehicle_input = QLineEdit(); self.vehicle_input.setFont(QFont("Arial", 22, QFont.Bold)); self.vehicle_input.setFixedSize(250, 48); self.vehicle_input.setStyleSheet("background: #fff7d6; border: 2px solid #ff6600; color: #003366; padding: 4px; border-radius: 8px;")
        layout.addWidget(vehicle_label); layout.addWidget(self.vehicle_input); layout.addSpacing(12)
        self.ok_btn = QPushButton("OK"); self.ok_btn.setFont(QFont("Arial", 16, QFont.Bold)); self.ok_btn.setFixedSize(120, 48); self.ok_btn.setStyleSheet("padding: 0 5px; background-color: #c6ffc6; border: 2px solid #0b0; border-radius: 8px;"); self.ok_btn.setEnabled(False)
        layout.addWidget(self.ok_btn); layout.addStretch(); return layout
    def _create_weight_details(self):
        layout = QHBoxLayout(); self.empty_weight_label = QLabel("Empty:"); self.empty_weight_label.setFont(self.font_label); self.empty_weight_field = QLineEdit(); self.empty_weight_field.setFont(self.font_amount); self.empty_weight_field.setReadOnly(True); self.empty_weight_field.setFixedWidth(120)
        layout.addWidget(self.empty_weight_label); layout.addWidget(self.empty_weight_field); layout.addSpacing(40)
        self.load_weight_label = QLabel("Load Weight:"); self.load_weight_label.setFont(self.font_label); self.load_weight_field = QLineEdit(); self.load_weight_field.setFont(self.font_amount); self.load_weight_field.setReadOnly(True); self.load_weight_field.setFixedWidth(120)
        layout.addWidget(self.load_weight_label); layout.addWidget(self.load_weight_field); layout.addStretch(); return layout
    
    def _create_amount_details(self):
        layout = QHBoxLayout(); layout.setSpacing(10)
        e_label = QLabel("E-Amount:"); e_label.setFont(self.font_label); self.eamount_field = QLineEdit("0"); self.eamount_field.setFont(self.font_amount); self.eamount_field.setReadOnly(True);
        l_label = QLabel("L-Amount:"); l_label.setFont(self.font_label); self.lamount_field = QLineEdit("0"); self.lamount_field.setFont(self.font_amount); self.lamount_field.setReadOnly(True);
        t_label = QLabel("T-Amount:"); t_label.setFont(self.font_label); self.tamount_field = QLineEdit("0"); self.tamount_field.setFont(self.font_amount); self.tamount_field.setReadOnly(True);
        for label, field in [(e_label, self.eamount_field), (l_label, self.lamount_field), (t_label, self.tamount_field)]:
            layout.addWidget(label); layout.addWidget(field)
        layout.addStretch(); return layout

    def _create_info_display(self):
        layout = QHBoxLayout(); status_label = QLabel("Status:"); status_label.setFont(self.font_label)
        self.load_status_display = QLabel(self.load_status); self.load_status_display.setFont(self.font_button); self.load_status_display.setStyleSheet("color: blue; font-weight: bold;")
        wheels_label = QLabel("Vehicle Type:"); wheels_label.setFont(self.font_label)
        self.wheels_display = QLabel(self.selected_vehicle_type); self.wheels_display.setFont(QFont("Arial", 12, QFont.Bold)); self.wheels_display.setStyleSheet("color: blue; font-weight: bold;")
        layout.addWidget(status_label); layout.addWidget(self.load_status_display); layout.addSpacing(20)
        layout.addWidget(wheels_label); layout.addWidget(self.wheels_display); layout.addStretch(); return layout
    def _create_keyboard(self):
        keypad_layout = QGridLayout(); keypad_layout.setHorizontalSpacing(10); keypad_layout.setVerticalSpacing(5); az_keys = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'; digit_keys = '1234567890'
        # Letter keys
        for idx, key in enumerate(az_keys):
            btn = QPushButton(key); btn.setFont(self.letter_font); btn.setFixedSize(52, 52); btn.clicked.connect(lambda _, k=key: self.vehicle_input.setText(self.vehicle_input.text() + k))
            keypad_layout.addWidget(btn, idx // 7, idx % 7)
        # Digit keys arranged to avoid overlap; 0 is visible
        for idx, key in enumerate(digit_keys):
            btn = QPushButton(key); btn.setFont(self.digit_font); btn.setFixedSize(52, 52); btn.clicked.connect(lambda _, k=key: self.vehicle_input.setText(self.vehicle_input.text() + k))
            keypad_layout.addWidget(btn, idx // 3, 7 + (idx % 3))
        # Back and Clear aligned without overlapping '0'
        back_btn = QPushButton("<--"); back_btn.setFont(self.digit_font); back_btn.setFixedSize(52, 52); back_btn.clicked.connect(lambda: self.vehicle_input.setText(self.vehicle_input.text()[:-1]))
        keypad_layout.addWidget(back_btn, 3, 8)
        clear_btn = QPushButton("Clear"); clear_btn.setFont(self.digit_font); clear_btn.setFixedSize(52, 52); clear_btn.setStyleSheet("background-color: red; color: white; font-weight: bold;"); clear_btn.clicked.connect(lambda: self.vehicle_input.setText(""))
        keypad_layout.addWidget(clear_btn, 3, 9)
        centered_layout = QHBoxLayout(); centered_layout.addStretch(); centered_layout.addLayout(keypad_layout); centered_layout.addStretch(); return centered_layout
    def _create_bottom_bar(self):
        bottom_layout = QHBoxLayout(); self.cancel_btn = QPushButton("Cancel"); self.cancel_btn.setFont(self.font_button); self.cancel_btn.setFixedSize(150, 48); self.cancel_btn.setStyleSheet("QPushButton {background: #fdd; border: 2px solid #a00; padding: 4px; font-size: 14pt; border-radius: 8px;}")
        bottom_layout.addWidget(self.cancel_btn); bottom_layout.addStretch(); return bottom_layout
    def _connect_signals(self):
        self.ok_btn.clicked.connect(self.ok_pressed); self.vehicle_input.textChanged.connect(self.check_vehicle_entry); self.cancel_btn.clicked.connect(self.cancel_action)
    def _initialize_state(self):
        self.update_weight_placeholders(); system_locale = QLocale.system(); self.date_format = system_locale.dateFormat(QLocale.ShortFormat); self.time_format = "HH:mm:ss"
    def _start_timers(self):
        self.update_date_time(); timer = QTimer(self); timer.timeout.connect(self.update_date_time); timer.start(1000)
    def centerOnScreen(self):
        screen_geo = QApplication.primaryScreen().geometry(); self.move((screen_geo.width() - self.width()) // 2, (screen_geo.height() - self.height()) // 2)
    def update_date_time(self):
        self.date_field.setText(to_display_date(QDate.currentDate())); self.time_field.setText(to_display_time(QTime.currentTime()))
    def generate_ticket_number(self):
        row = fetch_one('SELECT COALESCE(MAX(CAST("TicketNumber" AS INTEGER)), 0) + 1 AS next_ticket FROM tickets')
        next_ticket = row["next_ticket"] if row and row["next_ticket"] else 1; return f"{int(next_ticket):05d}"
    def get_fake_weight(self): return str(random.randint(5000, 12000))
    def check_vehicle_entry(self):
        plate = self.vehicle_input.text().upper(); is_valid = is_valid_indian_plate(plate); self.ok_btn.setEnabled(is_valid)
        style = "background: #e9fce9; border: 2px solid green;" if is_valid else "background: #fff7d6; border: 2px solid #ff6600;"
        self.vehicle_input.setStyleSheet(style + " color: #003366; padding: 4px; border-radius: 8px;")
    
    def ok_pressed(self):
        plate = self.vehicle_input.text().upper()
        try:
            row = fetch_one('SELECT "TicketNumber", "VehicleNumber" FROM tickets WHERE "VehicleNumber" = %s AND "Pending" = TRUE', (plate,))
            if row:
                dlg = OldWeightDialog(self, row["TicketNumber"], plate)
                if dlg.exec_() == QDialog.Accepted and isinstance(dlg.result, tuple): self.open_second_load_window(*dlg.result)
                return
            
            amounts = rate_calculator.calculate_amounts(self.selected_vehicle_type, self.weight_display.text(), self.load_status)
            if not amounts: 
                QMessageBox.critical(self, "Rate Error", "Could not calculate rates for the selected vehicle type.")
                e_val, l_val, t_val = 0, 0, 0
            else:
                e_val = amounts.get('eamount', 0)
                l_val = amounts.get('lamount', 0)
                t_val = amounts.get('tamount', 0)

            self.eamount_field.setText(str(e_val))
            self.lamount_field.setText(str(l_val))
            self.tamount_field.setText(str(t_val))
            
            self.show_summary_dialog(e_val, l_val, t_val)
        except Exception as e: 
            QMessageBox.critical(self, "Database Error", f"Error processing vehicle: {e}\n{traceback.format_exc()}")
    
    def show_summary_dialog(self, eamount, lamount, tamount):
        dlg = SummaryDialog(self, self.ticket_number.text(), self.date_field.text(), self.time_field.text(), self.vehicle_input.text().upper(), self.weight_display.text(), self.selected_vehicle_type, self.load_status, eamount, lamount, tamount, transaction_window=self.mode_window)
        if dlg.exec_() == QDialog.Accepted:
            # This block can be used to get final values back from the dialog if needed
            # For now, all save logic is within the dialog.
            pass

    def open_second_load_window(self, ticket_number, vehicle_number):
        try:
            from second_load_window import SecondLoadWindow
            self.close(); self.second_win = SecondLoadWindow(); self.second_win.ticket_number.setText(str(ticket_number))
            self.second_win.vehicle_input.setText(str(vehicle_number)); self.second_win.show()
        except ImportError: QMessageBox.critical(self, "Error", "SecondLoadWindow module not found.")
    def update_weight_placeholders(self):
        if self.load_status == "Empty": self.empty_weight_field.setText(self.weight_display.text()); self.load_weight_field.clear()
        else: self.empty_weight_field.clear(); self.load_weight_field.setText(self.weight_display.text())
    def cancel_action(self):
        if self.mode_window: self.mode_window.show()
        self.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_win = None
    status_dialog = LoadStatusDialog()
    if status_dialog.exec_() == QDialog.Accepted:
        load_status = status_dialog.result
        vehicle_dialog = VehicleSelectionDialog()
        if vehicle_dialog.exec_() == QDialog.Accepted:
            vehicle_type = vehicle_dialog.result
            main_win = FirstLoadWindow(load_status=load_status, vehicle_type=vehicle_type)
            main_win.show()
    if main_win: sys.exit(app.exec_())
    else: sys.exit(0)
