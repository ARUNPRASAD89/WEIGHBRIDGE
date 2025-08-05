import re, sys, random, psycopg2, traceback, os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QHBoxLayout, QGridLayout, QButtonGroup, QApplication, QDialog, QMessageBox, QFrame
)
from PyQt5.QtCore import Qt, QDate, QTime, QTimer, QLocale
from PyQt5.QtGui import QFont, QIntValidator, QPixmap
from db_utils import execute_query, fetch_one, fetch_all, get_new_connection
from print_ticket_with_template_win32 import print_ticket_with_template
from ticket_preview_window import TicketPreviewDialog
from date_time_utils import to_db_date, to_db_time, to_display_date, to_display_time

# --- DATABASE AND UTILITY FUNCTIONS (Logic Unchanged) ---
def get_ticket_columns():
    rows = fetch_all("SELECT column_name FROM information_schema.columns WHERE table_name='tickets'")
    return set(r["column_name"] for r in rows)

def get_ticket_column_types():
    rows = fetch_all("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='tickets'")
    return {r["column_name"]: r["data_type"] for r in rows}

def unified_update_ticket(params):
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
    set_clause = ", ".join([f'"{k}" = %({k})s' for k in filtered_params.keys() if k != "TicketNumber"])
    query = f'UPDATE tickets SET {set_clause} WHERE "TicketNumber" = %(TicketNumber)s'
    execute_query(query, filtered_params)

# --- SUMMARY DIALOG (Logic Unchanged) ---
class SummaryDialog(QDialog):
    def __init__(self, parent, data, transaction_window=None):
        super().__init__(parent)
        self.setWindowTitle("Summary")
        self.setFixedSize(500, 540); self.setStyleSheet("background: #fff;")
        self.transaction_window = transaction_window; self.data = data
        layout = QVBoxLayout(self); font = QFont("Arial", 16)
        def add_row(label, value):
            h = QHBoxLayout(); lab = QLabel(label); val = QLabel(str(value)); lab.setFont(font); val.setFont(font)
            h.addWidget(lab); h.addWidget(val); layout.addLayout(h)
        add_row("Ticket No:", data.get("TicketNumber", "")); add_row("Date:", data.get("Date", "")); add_row("Time:", data.get("Time", ""))
        add_row("LAST DATE:", data.get("LAST DATE", "")); add_row("LAST TIME:", data.get("LAST TIME", ""))
        add_row("Vehicle:", data.get("VehicleNumber", "")); add_row("Empty Weight:", data.get("EmptyWeight", ""))
        add_row("Load Weight:", data.get("LoadedWeight", "")); add_row("Net Weight:", data.get("NetWeight", ""))
        add_row("E-Amount:", data.get("EAMOUNT", "")); add_row("L-Amount:", data.get("LAMOUNT", "")); add_row("T-Amount:", data.get("TAMOUNT", ""))
        btn_row = QHBoxLayout()
        self.print_btn = QPushButton("WeighPrint"); self.print_btn.setFont(QFont("Arial", 18, QFont.Bold)); self.print_btn.setStyleSheet("background: #c6ffc6; border: 2px solid #0b0; border-radius: 8px;"); self.print_btn.clicked.connect(self.on_weightprint); btn_row.addWidget(self.print_btn)
        self.cancel_btn = QPushButton("Cancel"); self.cancel_btn.setFont(QFont("Arial", 18, QFont.Bold)); self.cancel_btn.setStyleSheet("background: #f88; border: 2px solid #a00; border-radius: 8px;"); self.cancel_btn.clicked.connect(self.reject); btn_row.addWidget(self.cancel_btn)
        layout.addSpacing(12); layout.addLayout(btn_row)
        self.success_label = QLabel("", self); self.success_label.setAlignment(Qt.AlignCenter); self.success_label.setFont(QFont("Arial", 18, QFont.Bold)); self.success_label.setStyleSheet("color: green;"); layout.addWidget(self.success_label)
        self._preview_dialog, self._print_timer, self._finish_timer = None, None, None

    def on_weightprint(self):
        try:
            safe_strip = lambda val: val.strip() if isinstance(val, str) else val
            ticket_number = safe_strip(self.data.get('TicketNumber', '')); vehicle_number = safe_strip(self.data.get('VehicleNumber', ''))
            empty_weight, loaded_weight, net_weight = safe_strip(self.data.get('EmptyWeight', '')), safe_strip(self.data.get('LoadedWeight', '')), safe_strip(self.data.get('NetWeight', ''))
            eamount, lamount, tamount = safe_strip(self.data.get('EAMOUNT', '')), safe_strip(self.data.get('LAMOUNT', '')), safe_strip(self.data.get('TAMOUNT', ''))
            blank_to_none = lambda val: None if val in ("", None) else int(val)
            current_date, current_time = to_db_date(QDate.currentDate()), to_db_time(QTime.currentTime())
            row = fetch_one('SELECT "EmptyWeightDate", "EmptyWeightTime", "LoadWeightDate", "LoadWeightTime", "Pending", "Closed" FROM tickets WHERE "TicketNumber" = %s', (ticket_number,))
            db_pending, db_closed = (row["Pending"], row["Closed"]) if row else (True, False)
            both_recorded = bool(empty_weight) and bool(loaded_weight)
            pending = False if not db_pending or both_recorded else True
            closed = True if db_closed or both_recorded else False
            ew_date, ew_time = (row["EmptyWeightDate"], row["EmptyWeightTime"]) if row and row["EmptyWeightDate"] else (None, None)
            lw_date, lw_time = (row["LoadWeightDate"], row["LoadWeightTime"]) if row and row["LoadWeightDate"] else (None, None)
            if empty_weight and not ew_date: ew_date, ew_time = current_date, current_time
            if loaded_weight and not lw_date: lw_date, lw_time = current_date, current_time
            params = {"TicketNumber": blank_to_none(ticket_number), "VehicleNumber": vehicle_number, "Date": current_date, "Time": current_time, "EmptyWeight": blank_to_none(empty_weight), "LoadedWeight": blank_to_none(loaded_weight), "EmptyWeightDate": ew_date, "EmptyWeightTime": ew_time, "LoadWeightDate": lw_date, "LoadWeightTime": lw_time, "NetWeight": blank_to_none(net_weight), "Pending": pending, "Closed": closed, "Exported": False, "Shift": "B", "Materialname": "", "SupplierName": "", "State": "second transaction", "Blank": None, "AMOUNT": None, "STATUS": "", "EAMOUNT": blank_to_none(eamount), "LAMOUNT": blank_to_none(lamount), "TAMOUNT": blank_to_none(tamount), "NetWeight1": None, "LWEIGHT": None, "EWEIGHT": None}
            unified_update_ticket(params)
            self.ticket_data = {"TicketNumber": ticket_number, "VehicleNumber": vehicle_number, "Date": to_display_date(current_date), "Time": to_display_time(current_time), "EmptyWeight": empty_weight, "LoadedWeight": loaded_weight, "NetWeight": net_weight, "Materialname": "", "SupplierName": "", "State": "second transaction", "AMOUNT": "", "STATUS": "", "EAMOUNT": eamount, "LAMOUNT": lamount, "TAMOUNT": tamount, "NetWeight1": "", "LWEIGHT": "", "EWEIGHT": ""}
            self._preview_dialog = TicketPreviewDialog(self.ticket_data, parent=self); self._preview_dialog.show()
            self._print_timer = QTimer(self); self._print_timer.setSingleShot(True); self._print_timer.timeout.connect(self._do_print_ticket); self._print_timer.start(3000)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save/print ticket:\n{e}")

    def _do_print_ticket(self):
        try:
            if self._preview_dialog: self._preview_dialog.close()
            self.success_label.setText("Printing ticket...")
            print_ticket_with_template(self.ticket_data, get_new_connection())
            self._finish_timer = QTimer(self); self._finish_timer.setSingleShot(True); self._finish_timer.timeout.connect(self._finish_and_goto_transaction); self._finish_timer.start(2000)
        except Exception as e:
            QMessageBox.critical(self, "Printing Error", f"Print job failed:\n{e}")

    def _finish_and_goto_transaction(self):
        self.accept()
        if self.transaction_window:
            parent = self.parent(); parent.close() if parent else None
            self.transaction_window.show()
        else:
            self.parent().show() if self.parent() else None

# --- REFACTORED: SecondLoadWindow ---
class SecondLoadWindow(QWidget):
    def __init__(self, transaction_window=None):
        super().__init__()
        self.setWindowTitle("Vehicle Second Transaction")
        self.setFixedSize(1600, 900)
        self.setStyleSheet("background: #fff;")
        self.first_load_data = None
        self.transaction_window = transaction_window

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
        self.font_net_weight = QFont("Arial", 22, QFont.Bold)
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
        
        amount_frame = QFrame(); amount_frame.setFrameShape(QFrame.StyledPanel); amount_frame.setStyleSheet("QFrame { background: #f7f7f7; border: 1px solid #e0e0e0; border-radius: 8px; padding: 5px; }"); amount_frame.setLayout(self._create_amount_display())
        controls_layout.addWidget(amount_frame)

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
        layout.addWidget(date_label); layout.addWidget(self.date_field)
        layout.addSpacing(20)
        time_label = QLabel("Time:"); time_label.setFont(self.font_label); self.time_field = QLineEdit(); self.time_field.setFont(self.font_input); self.time_field.setReadOnly(True); self.time_field.setFixedWidth(130)
        layout.addWidget(time_label); layout.addWidget(self.time_field)
        layout.addStretch()
        weight_label = QLabel("Weight (kg):"); weight_label.setFont(self.font_label); self.weight_display = QLabel(self.get_fake_weight()); self.weight_display.setFont(self.font_weight); self.weight_display.setAlignment(Qt.AlignRight | Qt.AlignVCenter); self.weight_display.setStyleSheet("color:white; background:black; border-radius: 10px; padding: 4px 32px; min-width: 200px;")
        layout.addWidget(weight_label); layout.addWidget(self.weight_display)
        return layout

    def _create_vehicle_entry(self):
        layout = QHBoxLayout()
        ticket_label = QLabel("Ticket No:"); ticket_label.setFont(self.font_label); self.ticket_number = QLineEdit(); self.ticket_number.setFont(self.font_input); self.ticket_number.setValidator(QIntValidator(0, 99999999, self)); self.ticket_number.setFixedWidth(110)
        layout.addWidget(ticket_label); layout.addWidget(self.ticket_number)
        layout.addSpacing(15)
        vehicle_label = QLabel("Vehicle:"); vehicle_label.setFont(self.font_label); self.vehicle_input = QLineEdit(); self.vehicle_input.setFont(QFont("Arial", 22, QFont.Bold)); self.vehicle_input.setFixedSize(250, 48); self.vehicle_input.setStyleSheet("background: #fff7d6; border: 2px solid #ff6600; color: #003366; padding: 4px; border-radius: 8px;")
        layout.addWidget(vehicle_label); layout.addWidget(self.vehicle_input)
        layout.addSpacing(12)
        self.ok_btn = QPushButton("OK"); self.ok_btn.setFont(QFont("Arial", 16, QFont.Bold)); self.ok_btn.setFixedSize(120, 48); self.ok_btn.setStyleSheet("padding: 0 5px; background-color: #c6ffc6; border: 2px solid #0b0; border-radius: 8px;")
        layout.addWidget(self.ok_btn)
        layout.addStretch()
        return layout

    def _create_weight_details(self):
        layout = QHBoxLayout()
        self.empty_weight_label = QLabel("Empty:"); self.empty_weight_label.setFont(self.font_label); self.empty_weight_field = QLineEdit(); self.empty_weight_field.setFont(self.font_amount); self.empty_weight_field.setReadOnly(True); self.empty_weight_field.setFixedWidth(120)
        layout.addWidget(self.empty_weight_label); layout.addWidget(self.empty_weight_field)
        layout.addSpacing(20)
        self.load_weight_label = QLabel("Load:"); self.load_weight_label.setFont(self.font_label); self.load_weight_field = QLineEdit(); self.load_weight_field.setFont(self.font_amount); self.load_weight_field.setReadOnly(True); self.load_weight_field.setFixedWidth(120)
        layout.addWidget(self.load_weight_label); layout.addWidget(self.load_weight_field)
        layout.addSpacing(40)
        net_label = QLabel("Net Weight:"); net_label.setFont(self.font_net_weight); self.net_weight_field = QLineEdit(); self.net_weight_field.setFont(self.font_net_weight); self.net_weight_field.setReadOnly(True); self.net_weight_field.setFixedWidth(180)
        layout.addWidget(net_label); layout.addWidget(self.net_weight_field)
        layout.addStretch()
        return layout

    def _create_amount_display(self):
        layout = QHBoxLayout()
        eamount_label = QLabel("E-Amount:"); eamount_label.setFont(self.font_label); self.eamount_input = QLineEdit(); self.eamount_input.setFont(self.font_amount); self.eamount_input.setReadOnly(True); self.eamount_input.setFixedWidth(80)
        layout.addWidget(eamount_label); layout.addWidget(self.eamount_input)
        layout.addSpacing(20)
        lamount_label = QLabel("L-Amount:"); lamount_label.setFont(self.font_label); self.lamount_input = QLineEdit(); self.lamount_input.setFont(self.font_amount); self.lamount_input.setReadOnly(True); self.lamount_input.setFixedWidth(80)
        layout.addWidget(lamount_label); layout.addWidget(self.lamount_input)
        layout.addSpacing(20)
        tamount_label = QLabel("T-Amount:"); tamount_label.setFont(self.font_label); self.tamount_input = QLineEdit(); self.tamount_input.setFont(self.font_amount); self.tamount_input.setReadOnly(True); self.tamount_input.setFixedWidth(80)
        layout.addWidget(tamount_label); layout.addWidget(self.tamount_input)
        layout.addStretch()
        return layout

    def _create_keyboard(self):
        keypad_layout = QGridLayout(); keypad_layout.setHorizontalSpacing(10); keypad_layout.setVerticalSpacing(5)
        az_keys = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'; digit_keys = '1234567890'
        for idx, key in enumerate(az_keys):
            btn = QPushButton(key); btn.setFont(self.letter_font); btn.setFixedSize(52, 52); btn.clicked.connect(lambda _, k=key: self.add_keypad_text(k))
            keypad_layout.addWidget(btn, idx // 7, idx % 7)
        for idx, key in enumerate(digit_keys):
            btn = QPushButton(key); btn.setFont(self.digit_font); btn.setFixedSize(52, 52); btn.clicked.connect(lambda _, k=key: self.add_keypad_text(k))
            keypad_layout.addWidget(btn, idx // 3, 7 + (idx % 3))
        back_btn = QPushButton("<--"); back_btn.setFont(self.digit_font); back_btn.setFixedSize(52*2+10, 52); back_btn.clicked.connect(self.keypad_backspace)
        keypad_layout.addWidget(back_btn, 3, 7, 1, 2)
        clear_btn = QPushButton("Clear"); clear_btn.setFont(self.digit_font); clear_btn.setFixedSize(52, 52); clear_btn.setStyleSheet("background-color: red; color: white; font-weight: bold;"); clear_btn.clicked.connect(self.clear_all_fields)
        keypad_layout.addWidget(clear_btn, 3, 9)
        centered_layout = QHBoxLayout(); centered_layout.addStretch(); centered_layout.addLayout(keypad_layout); centered_layout.addStretch()
        return centered_layout

    def _create_bottom_bar(self):
        bottom_layout = QHBoxLayout()
        self.cancel_btn = QPushButton("Cancel"); self.cancel_btn.setFont(self.font_button); self.cancel_btn.setFixedSize(150, 48); self.cancel_btn.setStyleSheet("QPushButton {background: #fdd; border: 2px solid #a00; padding: 4px; font-size: 14pt; border-radius: 8px;}")
        bottom_layout.addWidget(self.cancel_btn)
        bottom_layout.addStretch()
        return bottom_layout

    def _connect_signals(self):
        self.ok_btn.clicked.connect(self.ok_pressed)
        self.cancel_btn.clicked.connect(self.cancel_action)
        self.vehicle_input.installEventFilter(self)
        self.ticket_number.installEventFilter(self)

    def _initialize_state(self):
        self.active_input = self.vehicle_input
        self.vehicle_input.setFocus()
        system_locale = QLocale.system()
        self.date_format = system_locale.dateFormat(QLocale.ShortFormat)
        self.time_format = "HH:mm:ss"

    def _start_timers(self):
        self.update_date_time()
        timer = QTimer(self); timer.timeout.connect(self.update_date_time); timer.start(1000)

    def centerOnScreen(self):
        screen_geo = QApplication.primaryScreen().geometry()
        self.move((screen_geo.width() - self.width()) // 2, (screen_geo.height() - self.height()) // 2)

    # --- LOGIC METHODS (Unchanged) ---
    def update_date_time(self):
        now = QDate.currentDate(); current_time = QTime.currentTime()
        self.date_field.setText(to_display_date(now)); self.time_field.setText(to_display_time(current_time))

    def eventFilter(self, obj, event):
        if event.type() == event.FocusIn:
            self.active_input = obj
        return super().eventFilter(obj, event)

    def get_fake_weight(self):
        return str(random.randint(5000, 15000))

    def add_keypad_text(self, char):
        if self.active_input is not None: self.active_input.insert(char)

    def keypad_backspace(self):
        if self.active_input is not None: self.active_input.backspace()

    def clear_all_fields(self):
        self.vehicle_input.setReadOnly(False); self.ticket_number.setReadOnly(False)
        for field in [self.vehicle_input, self.ticket_number, self.empty_weight_field, self.load_weight_field, self.net_weight_field, self.eamount_input, self.lamount_input, self.tamount_input, self.date_field, self.time_field]:
            field.clear()
        self.vehicle_input.setFocus(); self.active_input = self.vehicle_input
        self.update_date_time()

    def ok_pressed(self):
        ticket = self.ticket_number.text().strip()
        vehicle = self.vehicle_input.text().strip().upper()
        data = None
        
        # --- Logic to fetch data (unchanged) ---
        if ticket:
            # Assuming ticket number is an integer in the DB
            try:
                data = fetch_one('SELECT * FROM tickets WHERE "TicketNumber" = %s', (int(ticket),))
            except ValueError:
                QMessageBox.warning(self, "Invalid Input", "Ticket Number must be a valid number.")
                return
        elif vehicle:
            data = fetch_one('SELECT * FROM tickets WHERE "VehicleNumber" = %s AND "Pending" = TRUE', (vehicle,))
        else:
            QMessageBox.warning(self, "Input Required", "Please enter a Ticket Number or Vehicle Number.")
            return

        if data:
            # --- Logic to check if ticket is closed or not pending (unchanged) ---
            if data.get("Closed"):
                QMessageBox.warning(self, "Ticket Closed", f"Ticket {data['TicketNumber']} is closed and cannot be modified.")
                self.clear_all_fields(); return
            if not data.get("Pending"):
                QMessageBox.warning(self, "Not a Pending Ticket", f"Ticket {data['TicketNumber']} is not pending a second weight.")
                self.clear_all_fields(); return

            self.first_load_data = data
            self.ticket_number.setText(str(data["TicketNumber"]))
            self.vehicle_input.setText(data["VehicleNumber"])

            # --- CORRECTED LOGIC ---
            # This ensures that if a value from the DB is None, we display an empty string instead of the text "None".
            self.eamount_input.setText(str(data.get("EAMOUNT")) if data.get("EAMOUNT") is not None else "")
            self.lamount_input.setText(str(data.get("LAMOUNT")) if data.get("LAMOUNT") is not None else "")
            self.tamount_input.setText(str(data.get("TAMOUNT")) if data.get("TAMOUNT") is not None else "")
            
            # --- Logic to calculate weights (unchanged) ---
            db_empty = data.get("EmptyWeight"); db_load = data.get("LoadedWeight")
            current_weight = int(self.weight_display.text())
            
            if db_empty and not db_load:
                self.empty_weight_field.setText(str(db_empty))
                self.load_weight_field.setText(str(current_weight))
                self.net_weight_field.setText(str(current_weight - db_empty))
            elif db_load and not db_empty:
                self.load_weight_field.setText(str(db_load))
                self.empty_weight_field.setText(str(current_weight))
                self.net_weight_field.setText(str(db_load - current_weight))
            
            self.vehicle_input.setReadOnly(True); self.ticket_number.setReadOnly(True)
            
            # --- Logic to show summary dialog (unchanged) ---
            summary_data = {
                "TicketNumber": str(data.get("TicketNumber")), "Date": to_display_date(QDate.currentDate()), "Time": to_display_time(QTime.currentTime()),
                "LAST DATE": to_display_date(data.get("Date")), "LAST TIME": to_display_time(data.get("Time")),
                "VehicleNumber": str(data.get("VehicleNumber")), "EmptyWeight": self.empty_weight_field.text(),
                "LoadedWeight": self.load_weight_field.text(), "NetWeight": self.net_weight_field.text(),
                "EAMOUNT": self.eamount_input.text(), "LAMOUNT": self.lamount_input.text(), "TAMOUNT": self.tamount_input.text(),
            }
            dlg = SummaryDialog(self, summary_data, transaction_window=self.transaction_window)
            if dlg.exec_() == QDialog.Accepted:
                # After the summary dialog is accepted (printed), clear the fields for the next transaction.
                self.clear_all_fields()
        else:
            QMessageBox.warning(self, "Not Found", "No pending ticket found for the provided details.")
            self.clear_all_fields()
            
    def cancel_action(self):
        if self.transaction_window: self.transaction_window.show()
        self.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = SecondLoadWindow()
    win.show()
    sys.exit(app.exec_())
