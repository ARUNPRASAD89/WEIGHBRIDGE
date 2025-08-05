import re, sys, random, psycopg2, traceback, os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QHBoxLayout, QGridLayout, QButtonGroup,
    QApplication, QSizePolicy, QMessageBox, QDialog, QFrame
)
from PyQt5.QtCore import Qt, QDate, QTime, QTimer, QLocale
from PyQt5.QtGui import QFont, QIntValidator, QPixmap
from db_utils import execute_query, fetch_one, fetch_all, get_new_connection
from ticket_preview_window import TicketPreviewDialog
from print_ticket_with_template_win32 import print_ticket_with_template
from date_time_utils import to_db_date, to_db_time, to_display_date, to_display_time

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
            if filtered_params[k] in ("", None):
                filtered_params[k] = None
            else:
                try:
                    filtered_params[k] = int(filtered_params[k])
                except Exception:
                    filtered_params[k] = None
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
    if not tpl_row:
        raise Exception("No default template set in DB")
    templatename, ticket_height, ticket_width = tpl_row['templatename'], float(tpl_row['ticketheight']), float(tpl_row['ticketwidth'])
    fields = execute_query('SELECT fieldname, x, y, width, height, fontname, fontsize FROM templatefields WHERE templatename=%s ORDER BY id', (templatename,))
    template_fields = [{'fieldname': str(f[0]), 'x': float(f[1]), 'y': float(f[2]), 'width': float(f[3]), 'height': float(f[4]), 'fontname': str(f[5]), 'fontsize': int(f[6])} for f in fields]
    return template_fields, ticket_width, ticket_height

# --- DIALOGS (OldWeightDialog and SummaryDialog remain unchanged) ---
class OldWeightDialog(QDialog):
    def __init__(self, parent, ticket_number, vehicle_number):
        super().__init__(parent)
        self.setWindowTitle("OLD WEIGHT")
        self.setFixedSize(500, 500)
        self.setWindowModality(Qt.ApplicationModal)
        self.setStyleSheet("background-color: black; color: white;")
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
        self.x_btn.setFixedSize(110, 80)
        self.x_btn.setStyleSheet("background-color: red; color: white; border-radius: 18px;")
        self.x_btn.clicked.connect(lambda: self.x_pressed(ticket_number))
        btn_row.addWidget(self.x_btn)
        self.two_btn = QPushButton("2")
        self.two_btn.setFont(QFont("Arial", 28, QFont.Bold))
        self.two_btn.setFixedSize(110, 80)
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
    def __init__(self, parent, ticket_no, date, time, vehicle_number, weight, wheel_label, status, eamount, lamount, tamount, transaction_window=None):
        super().__init__(parent)
        self.setWindowTitle("Summary")
        self.setFixedSize(500, 600)
        self.setStyleSheet("background: #fff;")
        self.transaction_window = transaction_window
        layout = QVBoxLayout(self)
        font = QFont("Arial", 16)
        def add_row(label, value):
            h = QHBoxLayout()
            lab, val = QLabel(label), QLabel(str(value))
            lab.setFont(font); val.setFont(font)
            h.addWidget(lab); h.addWidget(val)
            layout.addLayout(h)
        add_row("Ticket No:", ticket_no); add_row("Date:", to_display_date(date)); add_row("Time:", to_display_time(time))
        add_row("Vehicle:", vehicle_number); add_row("Weight:", weight); add_row("Wheels:", wheel_label); add_row("Status:", status)
        add_row("E-Amount:", eamount); add_row("L-Amount:", lamount); add_row("T-Amount:", tamount)
        btn_row = QHBoxLayout()
        self.wp_btn = QPushButton("WeighPrint"); self.wp_btn.setFont(QFont("Arial", 18, QFont.Bold)); self.wp_btn.setStyleSheet("background: #c6ffc6; border: 2px solid #0b0; border-radius: 8px;")
        self.wp_btn.clicked.connect(self.on_weightprint); btn_row.addWidget(self.wp_btn)
        self.cancel_btn = QPushButton("Cancel"); self.cancel_btn.setFont(QFont("Arial", 18, QFont.Bold)); self.cancel_btn.setStyleSheet("background: #f88; border: 2px solid #a00; border-radius: 8px;")
        self.cancel_btn.clicked.connect(self.on_cancel); btn_row.addWidget(self.cancel_btn)
        layout.addSpacing(12); layout.addLayout(btn_row)
        self.success_label = QLabel("", self); self.success_label.setAlignment(Qt.AlignCenter); self.success_label.setFont(QFont("Arial", 18, QFont.Bold)); self.success_label.setStyleSheet("color: green;")
        layout.addWidget(self.success_label)
        self.ticket_no, self.date, self.time, self.vehicle_number, self.weight, self.status, self.eamount, self.lamount, self.tamount = ticket_no, date, time, vehicle_number, weight, status, eamount, lamount, tamount
        self._preview_dialog, self._print_timer, self._finish_timer = None, None, None

    def on_weightprint(self):
        try:
            blank_to_none = lambda val: None if val in ("", None) else int(val)
            ticket_number = int(str(self.ticket_no).lstrip('0') or '0')
            now_date, now_time = QDate.currentDate(), QTime.currentTime()
            date, time = to_db_date(now_date), to_db_time(now_time)
            vehicle_number, status = self.vehicle_number, self.status.strip().upper()
            eamount, lamount, tamount = blank_to_none(self.eamount), blank_to_none(self.lamount), blank_to_none(self.tamount)
            empty_weight = blank_to_none(self.weight) if status == "EMPTY" else None
            loaded_weight = blank_to_none(self.weight) if status == "LOAD" else None
            net_weight = loaded_weight - empty_weight if empty_weight is not None and loaded_weight is not None else (loaded_weight or empty_weight)
            params = {"TicketNumber": ticket_number, "VehicleNumber": vehicle_number, "Date": date, "Time": time, "EmptyWeight": empty_weight, "LoadedWeight": loaded_weight, "EmptyWeightDate": date if status == "EMPTY" else None, "EmptyWeightTime": time if status == "EMPTY" else None, "LoadWeightDate": date if status == "LOAD" else None, "LoadWeightTime": time if status == "LOAD" else None, "NetWeight": net_weight, "Pending": bool(empty_weight) ^ bool(loaded_weight), "Closed": bool(empty_weight and loaded_weight), "Exported": False, "Shift": "B", "Materialname": "", "SupplierName": "", "State": "first transaction", "Blank": None, "AMOUNT": None, "STATUS": self.status, "EAMOUNT": eamount, "LAMOUNT": lamount, "TAMOUNT": tamount, "NetWeight1": None, "LWEIGHT": None, "EWEIGHT": None}
            unified_save_ticket(params)
            self.ticket_data = {"TicketNumber": f"{ticket_number:05d}", "VehicleNumber": vehicle_number, "Date": to_display_date(date), "Time": to_display_time(time), "EmptyWeight": empty_weight or "", "LoadedWeight": loaded_weight or "", "NetWeight": net_weight or "", "Materialname": "", "SupplierName": "", "State": "first transaction", "AMOUNT": "", "STATUS": self.status, "EAMOUNT": eamount or "", "LAMOUNT": lamount or "", "TAMOUNT": tamount or "", "NetWeight1": "", "LWEIGHT": "", "EWEIGHT": ""}
            self.wp_btn.setVisible(False); self.success_label.setText("TICKET SAVED!")
            self._preview_dialog = TicketPreviewDialog(self.ticket_data, parent=self); self._preview_dialog.show()
            self.print_preview_timer = QTimer(self); self.print_preview_timer.setSingleShot(True); self.print_preview_timer.timeout.connect(self._do_print_ticket); self.print_preview_timer.start(3000)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save/print ticket:\n{e}\n\n{traceback.format_exc()}")

    def _do_print_ticket(self):
        if self._preview_dialog: self._preview_dialog.close()
        self.success_label.setText("Printing ticket...")
        print_ticket_with_template(self.ticket_data, get_new_connection())
        self._finish_timer = QTimer(self); self._finish_timer.setSingleShot(True); self._finish_timer.timeout.connect(self._finish_and_goto_transaction); self._finish_timer.start(2000)

    def _finish_and_goto_transaction(self):
        self.accept()
        if self.transaction_window:
            parent = self.parent(); parent.close() if parent else None
            self.transaction_window.show()
        else:
            self.parent().show() if self.parent() else None

    def on_cancel(self):
        self.reject()
        if self.transaction_window:
            parent = self.parent(); parent.close() if parent else None
            self.transaction_window.show()
        else:
            self.parent().show() if self.parent() else None

# --- NEW: Step 1 Window ---
class LoadStatusDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Step 1: Select Load Status")
        self.setFixedSize(400, 200)
        self.setWindowModality(Qt.ApplicationModal)
        self.result = None

        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignCenter)

        label = QLabel("Select the vehicle's load status:")
        label.setFont(QFont("Arial", 14))
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        btn_layout = QHBoxLayout()
        self.empty_btn = QPushButton("Empty")
        self.load_btn = QPushButton("Load")
        
        for btn in [self.empty_btn, self.load_btn]:
            btn.setFont(QFont("Arial", 18, QFont.Bold))
            btn.setFixedSize(150, 60)
            btn_layout.addWidget(btn)

        layout.addLayout(btn_layout)
        
        self.empty_btn.clicked.connect(lambda: self.set_result("Empty"))
        self.load_btn.clicked.connect(lambda: self.set_result("Load"))

    def set_result(self, status):
        self.result = status
        self.accept()

# --- NEW: Step 2 Window ---
class WheelSelectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Step 2: Select Wheels")
        self.setFixedSize(400, 300)
        self.setWindowModality(Qt.ApplicationModal)
        self.result = None

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        label = QLabel("Select the number of wheels:")
        label.setFont(QFont("Arial", 14))
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        wheels_grid = QGridLayout()
        self.wheel_btn_group = QButtonGroup(self)
        wheel_options = ["4 wheels", "6 wheels", "10 wheels", "12 wheels", "14 wheels", "16 wheels", "18 wheels", "20+ wheels"]
        
        for idx, label_text in enumerate(wheel_options):
            btn = QPushButton(label_text.split(" ")[0])
            btn.setFont(QFont("Arial", 16, QFont.Bold))
            btn.setCheckable(True)
            btn.setFixedSize(80, 80)
            self.wheel_btn_group.addButton(btn, idx)
            wheels_grid.addWidget(btn, idx // 4, idx % 4)
        
        layout.addLayout(wheels_grid)
        self.wheel_btn_group.buttonClicked.connect(self.on_wheel_selected)

    def on_wheel_selected(self, button):
        wheel_options = ["4 wheels", "6 wheels", "10 wheels", "12 wheels", "14 wheels", "16 wheels", "18 wheels", "20+ wheels"]
        self.result = wheel_options[self.wheel_btn_group.id(button)]
        self.accept()

# --- CONSTANTS ---
WHEEL_RATES = {"4 wheels": 60, "6 wheels": 80, "10 wheels": 100, "12 wheels": 120, "14 wheels": 150, "16 wheels": 180, "18 wheels": 210, "20+ wheels": 250}
def is_valid_indian_plate(text):
    return any(re.fullmatch(p, text.upper()) for p in [r'^[A-Z]{2}\d{2}[A-Z]{1,3}\d{4}$', r'^[A-Z]{2}\d{2}[A-Z]{0,2}\d{4}$', r'^[A-Z]{3}\d{4}$', r'^[A-Z]{2}\d{4}$'])

# --- REFACTORED: Main Transaction Window ---
class FirstLoadWindow(QWidget):
    def __init__(self, load_status, wheel_type, mode_window=None):
        super().__init__()
        self.setWindowTitle("Vehicle First Transaction")
        self.setFixedSize(1600, 900)
        self.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.WindowMinimizeButtonHint | Qt.WindowCloseButtonHint)
        self.setStyleSheet("background: #fff;")
        
        self.mode_window = mode_window
        self.load_status = load_status
        self.selected_wheel_label = wheel_type

        self._define_fonts()
        self._setup_ui()
        self._connect_signals()
        self._initialize_state()
        self._start_timers()
        self.centerOnScreen()

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
        controls_layout.setContentsMargins(0,0,0,0); controls_layout.setSpacing(10); controls_layout.setAlignment(Qt.AlignTop)

        top_bar_frame = QFrame(); top_bar_frame.setFrameShape(QFrame.StyledPanel); top_bar_frame.setLayout(self._create_top_bar())
        controls_layout.addWidget(top_bar_frame)

        vehicle_frame = QFrame(); vehicle_frame.setFrameShape(QFrame.StyledPanel); vehicle_frame.setLayout(self._create_vehicle_entry())
        controls_layout.addWidget(vehicle_frame)

        weight_frame = QFrame(); weight_frame.setFrameShape(QFrame.StyledPanel); weight_frame.setLayout(self._create_weight_details())
        controls_layout.addWidget(weight_frame)
        
        # Display selected status and wheels
        info_frame = QFrame(); info_frame.setFrameShape(QFrame.StyledPanel); info_frame.setLayout(self._create_info_display())
        controls_layout.addWidget(info_frame)

        keypad_frame = QFrame(); keypad_frame.setFrameShape(QFrame.StyledPanel); keypad_frame.setLayout(self._create_keyboard())
        controls_layout.addWidget(keypad_frame)
        
        controls_layout.addStretch()

        bottom_frame = QFrame(); bottom_frame.setLayout(self._create_bottom_bar())
        controls_layout.addWidget(bottom_frame, alignment=Qt.AlignHCenter)

        main_h_layout.addWidget(controls_frame, 1)

        camera_frame = QFrame(); camera_frame.setFrameShape(QFrame.StyledPanel); camera_frame.setStyleSheet("QFrame { background-color: black; border: 2px solid #555; border-radius: 8px; }")
        camera_layout = QVBoxLayout(camera_frame)
        camera_label = QLabel("CAMERA FEED"); camera_label.setAlignment(Qt.AlignCenter); camera_label.setFont(QFont("Arial", 24, QFont.Bold)); camera_label.setStyleSheet("color: white;")
        camera_layout.addWidget(camera_label)
        main_h_layout.addWidget(camera_frame, 2)

    def _create_top_bar(self):
        layout = QHBoxLayout()
        date_label = QLabel("Date:"); date_label.setFont(self.font_label); self.date_field = QLineEdit(); self.date_field.setFont(self.font_input); self.date_field.setReadOnly(True); self.date_field.setFixedWidth(170)
        layout.addWidget(date_label); layout.addWidget(self.date_field); layout.addSpacing(20)
        ticket_label = QLabel("Ticket No:"); ticket_label.setFont(self.font_label); self.ticket_number = QLineEdit(self.generate_ticket_number()); self.ticket_number.setFont(self.font_input); self.ticket_number.setReadOnly(True); self.ticket_number.setFixedWidth(110)
        layout.addWidget(ticket_label); layout.addWidget(self.ticket_number); layout.addStretch()
        weight_label = QLabel("Weight (kg):"); weight_label.setFont(self.font_label); self.weight_display = QLabel(self.get_fake_weight()); self.weight_display.setFont(self.font_weight); self.weight_display.setAlignment(Qt.AlignRight | Qt.AlignVCenter); self.weight_display.setStyleSheet("color:white; background:black; border-radius: 10px; padding: 4px 32px; min-width: 200px;")
        layout.addWidget(weight_label); layout.addWidget(self.weight_display)
        return layout

    def _create_vehicle_entry(self):
        layout = QHBoxLayout()
        time_label = QLabel("Time:"); time_label.setFont(self.font_label); self.time_field = QLineEdit(); self.time_field.setFont(self.font_input); self.time_field.setReadOnly(True); self.time_field.setFixedWidth(130)
        layout.addWidget(time_label); layout.addWidget(self.time_field); layout.addSpacing(15)
        vehicle_label = QLabel("Vehicle:"); vehicle_label.setFont(self.font_label); self.vehicle_input = QLineEdit(); self.vehicle_input.setFont(QFont("Arial", 22, QFont.Bold)); self.vehicle_input.setFixedSize(250, 48); self.vehicle_input.setStyleSheet("background: #fff7d6; border: 2px solid #ff6600; color: #003366; padding: 4px; border-radius: 8px;")
        layout.addWidget(vehicle_label); layout.addWidget(self.vehicle_input); layout.addSpacing(12)
        self.ok_btn = QPushButton("OK"); self.ok_btn.setFont(QFont("Arial", 16, QFont.Bold)); self.ok_btn.setFixedSize(120, 48); self.ok_btn.setStyleSheet("padding: 0 5px; background-color: #c6ffc6; border: 2px solid #0b0; border-radius: 8px;"); self.ok_btn.setEnabled(False)
        layout.addWidget(self.ok_btn); layout.addStretch()
        return layout

    def _create_weight_details(self):
        layout = QHBoxLayout()
        self.empty_weight_label = QLabel("Empty:"); self.empty_weight_label.setFont(self.font_label); self.empty_weight_field = QLineEdit(); self.empty_weight_field.setFont(self.font_amount); self.empty_weight_field.setReadOnly(True); self.empty_weight_field.setFixedWidth(120)
        layout.addWidget(self.empty_weight_label); layout.addWidget(self.empty_weight_field); layout.addSpacing(40)
        self.load_weight_label = QLabel("Load Weight:"); self.load_weight_label.setFont(self.font_label); self.load_weight_field = QLineEdit(); self.load_weight_field.setFont(self.font_amount); self.load_weight_field.setReadOnly(True); self.load_weight_field.setFixedWidth(120)
        layout.addWidget(self.load_weight_label); layout.addWidget(self.load_weight_field); layout.addStretch()
        return layout

    def _create_info_display(self):
        layout = QHBoxLayout()
        status_label = QLabel("Status:"); status_label.setFont(self.font_label)
        self.load_status_display = QLabel(self.load_status); self.load_status_display.setFont(self.font_button); self.load_status_display.setStyleSheet("color: blue; font-weight: bold;")
        wheels_label = QLabel("Wheels:"); wheels_label.setFont(self.font_label)
        self.wheels_display = QLabel(self.selected_wheel_label); self.wheels_display.setFont(self.font_button); self.wheels_display.setStyleSheet("color: blue; font-weight: bold;")
        layout.addWidget(status_label); layout.addWidget(self.load_status_display); layout.addSpacing(40)
        layout.addWidget(wheels_label); layout.addWidget(self.wheels_display); layout.addStretch()
        return layout

    def _create_keyboard(self):
        keypad_layout = QGridLayout(); keypad_layout.setHorizontalSpacing(10); keypad_layout.setVerticalSpacing(5)
        az_keys = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'; digit_keys = '1234567890'
        for idx, key in enumerate(az_keys):
            btn = QPushButton(key); btn.setFont(self.letter_font); btn.setFixedSize(52, 52); btn.clicked.connect(lambda _, k=key: self.vehicle_input.setText(self.vehicle_input.text() + k))
            keypad_layout.addWidget(btn, idx // 7, idx % 7)
        for idx, key in enumerate(digit_keys):
            btn = QPushButton(key); btn.setFont(self.digit_font); btn.setFixedSize(52, 52); btn.clicked.connect(lambda _, k=key: self.vehicle_input.setText(self.vehicle_input.text() + k))
            keypad_layout.addWidget(btn, idx // 3, 7 + (idx % 3))
        back_btn = QPushButton("<--"); back_btn.setFont(self.digit_font); back_btn.setFixedSize(52*2+10, 52); back_btn.clicked.connect(lambda: self.vehicle_input.setText(self.vehicle_input.text()[:-1]))
        keypad_layout.addWidget(back_btn, 3, 7, 1, 2)
        clear_btn = QPushButton("Clear"); clear_btn.setFont(self.digit_font); clear_btn.setFixedSize(52, 52); clear_btn.setStyleSheet("background-color: red; color: white; font-weight: bold;"); clear_btn.clicked.connect(lambda: self.vehicle_input.setText(""))
        keypad_layout.addWidget(clear_btn, 3, 9)
        centered_layout = QHBoxLayout(); centered_layout.addStretch(); centered_layout.addLayout(keypad_layout); centered_layout.addStretch()
        return centered_layout

    def _create_bottom_bar(self):
        bottom_layout = QHBoxLayout()
        self.cancel_btn = QPushButton("Cancel"); self.cancel_btn.setFont(self.font_button); self.cancel_btn.setFixedSize(150, 48); self.cancel_btn.setStyleSheet("QPushButton {background: #fdd; border: 2px solid #a00; padding: 4px; font-size: 14pt; border-radius: 8px;}")
        bottom_layout.addWidget(self.cancel_btn); bottom_layout.addStretch()
        return bottom_layout

    def _connect_signals(self):
        self.ok_btn.clicked.connect(self.ok_pressed)
        self.vehicle_input.textChanged.connect(self.check_vehicle_entry)
        self.cancel_btn.clicked.connect(self.cancel_action)

    def _initialize_state(self):
        self.update_weight_placeholders()
        self.update_amount_fields()
        system_locale = QLocale.system()
        self.date_format = system_locale.dateFormat(QLocale.ShortFormat)
        self.time_format = "HH:mm:ss"

    def _start_timers(self):
        self.update_date_time()
        timer = QTimer(self); timer.timeout.connect(self.update_date_time); timer.start(1000)

    def centerOnScreen(self):
        screen_geo = QApplication.primaryScreen().geometry()
        self.move((screen_geo.width() - self.width()) // 2, (screen_geo.height() - self.height()) // 2)

    def update_date_time(self):
        self.date_field.setText(to_display_date(QDate.currentDate()))
        self.time_field.setText(to_display_time(QTime.currentTime()))
        
    def generate_ticket_number(self):
        row = fetch_one('SELECT COALESCE(MAX(CAST("TicketNumber" AS INTEGER)), 0) + 1 AS next_ticket FROM tickets')
        next_ticket = row["next_ticket"] if row and row["next_ticket"] else 1
        return f"{int(next_ticket):05d}"

    def get_fake_weight(self):
        return str(random.randint(5000, 12000))

    def check_vehicle_entry(self):
        plate = self.vehicle_input.text().upper()
        is_valid = is_valid_indian_plate(plate)
        self.ok_btn.setEnabled(is_valid)
        style = "background: #e9fce9; border: 2px solid green;" if is_valid else "background: #fff7d6; border: 2px solid #ff6600;"
        self.vehicle_input.setStyleSheet(style + " color: #003366; padding: 4px; border-radius: 8px;")

    def ok_pressed(self):
        plate = self.vehicle_input.text().upper()
        try:
            row = fetch_one('SELECT "TicketNumber", "VehicleNumber" FROM tickets WHERE "VehicleNumber" = %s AND "Pending" = TRUE', (plate,))
            if row:
                dlg = OldWeightDialog(self, row["TicketNumber"], plate)
                if dlg.exec_() == QDialog.Accepted and isinstance(dlg.result, tuple):
                    self.open_second_load_window(*dlg.result)
                return
            self.show_summary_dialog()
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Error searching vehicle: {e}")

    def show_summary_dialog(self):
        # The amount fields are now read-only and calculated, so we don't need to get text from them
        rate = WHEEL_RATES.get(self.selected_wheel_label, 0)
        eamount = str(rate) if self.load_status == "Empty" else ""
        lamount = str(rate) if self.load_status == "Load" else ""
        tamount = str(rate)
        
        dlg = SummaryDialog(self, self.ticket_number.text(), self.date_field.text(), self.time_field.text(), self.vehicle_input.text().upper(), self.weight_display.text(), self.selected_wheel_label, self.load_status, eamount, lamount, tamount, transaction_window=self.mode_window)
        dlg.exec_()

    def open_second_load_window(self, ticket_number, vehicle_number):
        try:
            from second_load_window import SecondLoadWindow
            self.close()
            self.second_win = SecondLoadWindow()
            self.second_win.ticket_number.setText(str(ticket_number))
            self.second_win.vehicle_input.setText(str(vehicle_number))
            self.second_win.show()
        except ImportError:
            QMessageBox.critical(self, "Error", "SecondLoadWindow module not found.")

    def update_weight_placeholders(self):
        if self.load_status == "Empty":
            self.empty_weight_field.setText(self.weight_display.text())
            self.load_weight_field.clear()
        else:
            self.empty_weight_field.clear()
            self.load_weight_field.setText(self.weight_display.text())

    def update_amount_fields(self):
        # This method is now simplified as it doesn't need to interact with input fields
        pass

    def cancel_action(self):
        if self.mode_window: self.mode_window.show()
        self.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # --- New Workflow ---
    main_win = None
    
    # Step 1: Show Load Status Dialog
    status_dialog = LoadStatusDialog()
    if status_dialog.exec_() == QDialog.Accepted:
        load_status = status_dialog.result
        
        # Step 2: Show Wheel Selection Dialog
        wheel_dialog = WheelSelectionDialog()
        if wheel_dialog.exec_() == QDialog.Accepted:
            wheel_type = wheel_dialog.result
            
            # Step 3: Show Main Window with results
            main_win = FirstLoadWindow(load_status=load_status, wheel_type=wheel_type)
            main_win.show()

    if main_win:
        sys.exit(app.exec_())
    else:
        # Exit if the user closed any of the dialogs
        sys.exit(0)
