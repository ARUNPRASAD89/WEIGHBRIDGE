import re, sys, random, psycopg2, traceback, os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QHBoxLayout, QGridLayout, QButtonGroup, QApplication, QDialog, QMessageBox, QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt, QDate, QTime, QTimer, QLocale
from PyQt5.QtGui import QFont, QIntValidator, QPixmap
from db_utils import execute_query, fetch_one, fetch_all, get_new_connection
from print_ticket_with_template_win32 import print_ticket_with_template
from ticket_preview_window import TicketPreviewDialog
from date_time_utils import to_db_date, to_db_time, to_display_date, to_display_time
import rate_calculator

# --- ADDED: Import the dialog from the other window ---
from first_load_window import VehicleSelectionDialog

# --- DATABASE AND UTILITY FUNCTIONS (No Changes) ---
def get_ticket_columns():
    rows = fetch_all("SELECT column_name FROM information_schema.columns WHERE table_name='tickets'")
    return set(r["column_name"] for r in rows)
def get_ticket_column_types():
    rows = fetch_all("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='tickets'")
    return {r["column_name"]: r["data_type"] for r in rows}
def unified_update_ticket(params):
    ticket_columns = get_ticket_columns(); filtered_params = {k: v for k, v in params.items() if k in ticket_columns}; ticket_column_types = get_ticket_column_types()
    for k in list(filtered_params.keys()):
        if k in ticket_column_types and ticket_column_types[k] in ("integer", "bigint", "smallint"):
            if filtered_params[k] in ("", None): filtered_params[k] = None
            else:
                try: filtered_params[k] = int(filtered_params[k])
                except (ValueError, TypeError): filtered_params[k] = None
    set_clause = ", ".join([f'"{k}" = %({k})s' for k in filtered_params.keys() if k != "TicketNumber"])
    query = f'UPDATE tickets SET {set_clause} WHERE "TicketNumber" = %(TicketNumber)s'; execute_query(query, filtered_params)

# --- UPDATED: SummaryDialog to be resizable/aligned like FirstLoadWindow ---
class SummaryDialog(QDialog):
    def __init__(self, parent, data, transaction_window=None):
        super().__init__(parent)
        self.setWindowTitle("Summary & Finalize")
        self.setStyleSheet("background-color: black; color: white;")
        self.setWindowModality(Qt.ApplicationModal)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.resize(720, 780)
        self.transaction_window = transaction_window
        self.data = data
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        title_font = QFont("Arial", 20, QFont.Bold)
        label_font = QFont("Arial", 16)
        amount_font = QFont("Arial", 18, QFont.Bold)
        button_font = QFont("Arial", 16, QFont.Bold)
        
        info_grid = QGridLayout()
        info_grid.setSpacing(10)
        def add_info(row, col, label, value):
            lab = QLabel(label); lab.setFont(label_font)
            val = QLabel(str(value)); val.setFont(label_font); val.setStyleSheet("color: #aaffff;")
            lab.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            val.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            info_grid.addWidget(lab, row, col*2); info_grid.addWidget(val, row, col*2+1)
        
        add_info(0, 0, "Ticket No:", data.get("TicketNumber", "")); add_info(0, 1, "Date:", data.get("Date", ""))
        add_info(1, 0, "LAST DATE:", data.get("LAST DATE", "")); add_info(1, 1, "LAST TIME:", data.get("LAST TIME", ""))
        add_info(2, 0, "Vehicle:", data.get("VehicleNumber", "")); add_info(2, 1, "Vehicle Type:", data.get("VehicleType", ""))
        add_info(3, 0, "Empty Weight:", data.get("EmptyWeight", "")); add_info(3, 1, "Load Weight:", data.get("LoadedWeight", ""))
        add_info(4, 0, "Net Weight:", data.get("NetWeight", ""))
        main_layout.addLayout(info_grid)
        main_layout.addWidget(QFrame(self, frameShape=QFrame.HLine, frameShadow=QFrame.Sunken))
        
        amount_layout = QGridLayout()
        amount_layout.setSpacing(10)
        e_label = QLabel("E-Amount:"); e_label.setFont(label_font)
        self.eamount_field = QLineEdit(str(data.get("EAMOUNT", "0"))); self.eamount_field.setFont(amount_font); self.eamount_field.setAlignment(Qt.AlignCenter); self.eamount_field.setMinimumWidth(120)
        e_minus_btn = QPushButton("-"); e_plus_btn = QPushButton("+")
        for btn in [e_minus_btn, e_plus_btn]: btn.setFont(button_font); btn.setMinimumSize(50, 50); btn.setStyleSheet("border: 1px solid white;")
        amount_layout.addWidget(e_label, 0, 0); amount_layout.addWidget(e_minus_btn, 0, 1); amount_layout.addWidget(self.eamount_field, 0, 2); amount_layout.addWidget(e_plus_btn, 0, 3)

        l_label = QLabel("L-Amount:"); l_label.setFont(label_font)
        self.lamount_field = QLineEdit(str(data.get("LAMOUNT", "0"))); self.lamount_field.setFont(amount_font); self.lamount_field.setAlignment(Qt.AlignCenter); self.lamount_field.setMinimumWidth(120)
        l_minus_btn = QPushButton("-"); l_plus_btn = QPushButton("+")
        for btn in [l_minus_btn, l_plus_btn]: btn.setFont(button_font); btn.setMinimumSize(50, 50); btn.setStyleSheet("border: 1px solid white;")
        amount_layout.addWidget(l_label, 1, 0); amount_layout.addWidget(l_minus_btn, 1, 1); amount_layout.addWidget(self.lamount_field, 1, 2); amount_layout.addWidget(l_plus_btn, 1, 3)

        t_label = QLabel("T-Amount:"); t_label.setFont(label_font)
        self.tamount_display = QLabel(str(data.get("TAMOUNT", "0"))); self.tamount_display.setFont(amount_font); self.tamount_display.setMinimumWidth(120); self.tamount_display.setAlignment(Qt.AlignCenter)
        amount_layout.addWidget(t_label, 2, 0); amount_layout.addWidget(self.tamount_display, 2, 2)
        main_layout.addLayout(amount_layout)

        e_minus_btn.clicked.connect(lambda: self._modify_amount(self.eamount_field, -5)); e_plus_btn.clicked.connect(lambda: self._modify_amount(self.eamount_field, 5))
        l_minus_btn.clicked.connect(lambda: self._modify_amount(self.lamount_field, -5)); l_plus_btn.clicked.connect(lambda: self._modify_amount(self.lamount_field, 5))
        self.eamount_field.textChanged.connect(self._update_tamount); self.lamount_field.textChanged.connect(self._update_tamount)
        main_layout.addStretch()

        btn_row = QHBoxLayout()
        self.print_btn = QPushButton("Weigh & Print"); self.print_btn.setFont(button_font); self.print_btn.setMinimumHeight(60); self.print_btn.setStyleSheet("background: #006400; color: white; border-radius: 8px;")
        self.print_btn.clicked.connect(self.on_weightprint); btn_row.addWidget(self.print_btn)
        self.cancel_btn = QPushButton("Cancel"); self.cancel_btn.setFont(button_font); self.cancel_btn.setMinimumHeight(60); self.cancel_btn.setStyleSheet("background: #8B0000; color: white; border-radius: 8px;")
        self.cancel_btn.clicked.connect(self.reject); btn_row.addWidget(self.cancel_btn)
        main_layout.addLayout(btn_row)

        self.success_label = QLabel("", self); self.success_label.setAlignment(Qt.AlignCenter); self.success_label.setFont(title_font); self.success_label.setStyleSheet("color: #00ff00;")
        main_layout.addWidget(self.success_label)
        self._preview_dialog, self._print_timer, self._finish_timer = None, None, None
        self._update_tamount()

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
            current_date, current_time = to_db_date(QDate.currentDate()), to_db_time(QTime.currentTime())
            row = fetch_one('SELECT "EmptyWeightDate", "EmptyWeightTime", "LoadWeightDate", "LoadWeightTime" FROM tickets WHERE "TicketNumber" = %s', (self.data.get('TicketNumber'),))
            ew_date, ew_time = (row["EmptyWeightDate"], row["EmptyWeightTime"]) if row and row["EmptyWeightDate"] else (None, None)
            lw_date, lw_time = (row["LoadWeightDate"], row["LoadWeightTime"]) if row and row["LoadWeightDate"] else (None, None)
            if self.data.get('EmptyWeight') and not ew_date: ew_date, ew_time = current_date, current_time
            if self.data.get('LoadedWeight') and not lw_date: lw_date, lw_time = current_date, current_time
            
            params = {
                "TicketNumber": blank_to_none(self.data.get('TicketNumber')), "VehicleNumber": self.data.get('VehicleNumber'),
                "VehicleType": self.data.get('VehicleType'), "Date": current_date, "Time": current_time,
                "EmptyWeight": blank_to_none(self.data.get('EmptyWeight')), "LoadedWeight": blank_to_none(self.data.get('LoadedWeight')),
                "EmptyWeightDate": ew_date, "EmptyWeightTime": ew_time, "LoadWeightDate": lw_date, "LoadWeightTime": lw_time,
                "NetWeight": blank_to_none(self.data.get('NetWeight')), "Pending": False, "Closed": True,
                "EAMOUNT": blank_to_none(self.eamount_field.text()), "LAMOUNT": blank_to_none(self.lamount_field.text()),
                "TAMOUNT": blank_to_none(self.tamount_display.text())
            }
            unified_update_ticket(params)
            
            self.ticket_data = self.data.copy()
            self.ticket_data.update({
                "Date": to_display_date(current_date), "Time": to_display_time(current_time),
                "EAMOUNT": self.eamount_field.text(), "LAMOUNT": self.lamount_field.text(), "TAMOUNT": self.tamount_display.text()
            })
            self.print_btn.setVisible(False); self.cancel_btn.setVisible(False); self.success_label.setText("TICKET SAVED!")
            self._preview_dialog = TicketPreviewDialog(self.ticket_data, parent=self); self._preview_dialog.show()
            self._print_timer = QTimer(self); self._print_timer.setSingleShot(True); self._print_timer.timeout.connect(self._do_print_ticket); self._print_timer.start(3000)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save/print ticket:\n{traceback.format_exc()}")

    def _do_print_ticket(self):
        try:
            if self._preview_dialog: self._preview_dialog.close()
            self.success_label.setText("Printing ticket..."); print_ticket_with_template(self.ticket_data, get_new_connection())
            self._finish_timer = QTimer(self); self._finish_timer.setSingleShot(True); self._finish_timer.timeout.connect(self._finish_and_goto_transaction); self._finish_timer.start(2000)
        except Exception as e: QMessageBox.critical(self, "Printing Error", f"Print job failed:\n{e}")

    def _finish_and_goto_transaction(self):
        self.accept()
        if self.transaction_window: # This is the SecondLoadWindow instance
            # The mode_window of SecondLoadWindow is the TransactionWindow
            if self.transaction_window.transaction_window:
                self.transaction_window.transaction_window.show()
            self.transaction_window.close()

# --- UPDATED: SecondLoadWindow to be resizable and keypad aligned like FirstLoadWindow ---
class SecondLoadWindow(QWidget):
    def __init__(self, mode_window=None):
        super().__init__()
        self.setWindowTitle("Vehicle Second Transaction")
        # Make the main window resizable and allow maximize (like FirstLoadWindow)
        self.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint)
        self.setStyleSheet("background: #fff;")
        self.setMinimumSize(1100, 700)
        self.resize(1600, 900)

        self.first_load_data = None
        self.transaction_window = mode_window
        self._define_fonts(); self._setup_ui(); self._connect_signals(); self._initialize_state(); self._start_timers(); self.centerOnScreen()
    def _define_fonts(self):
        self.font_label = QFont("Arial", 14, QFont.Bold); self.font_input = QFont("Arial", 18); self.font_weight = QFont("Arial", 28, QFont.Bold)
        self.font_button = QFont("Arial", 18, QFont.Bold); self.font_amount = QFont("Arial", 18, QFont.Bold); self.font_net_weight = QFont("Arial", 22, QFont.Bold)
        self.letter_font = QFont("Arial", 20, QFont.Bold); self.digit_font = QFont("Arial", 22, QFont.Bold)
    def _setup_ui(self):
        main_h_layout = QHBoxLayout(self); main_h_layout.setContentsMargins(15, 15, 15, 15); main_h_layout.setSpacing(15)
        controls_frame = QFrame(); controls_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        controls_layout = QVBoxLayout(controls_frame); controls_layout.setContentsMargins(0,0,0,0); controls_layout.setSpacing(10); controls_layout.setAlignment(Qt.AlignTop)
        top_bar_frame = QFrame(); top_bar_frame.setFrameShape(QFrame.StyledPanel); top_bar_frame.setLayout(self._create_top_bar()); controls_layout.addWidget(top_bar_frame)
        vehicle_frame = QFrame(); vehicle_frame.setFrameShape(QFrame.StyledPanel); vehicle_frame.setLayout(self._create_vehicle_entry()); controls_layout.addWidget(vehicle_frame)
        weight_frame = QFrame(); weight_frame.setFrameShape(QFrame.StyledPanel); weight_frame.setLayout(self._create_weight_details()); controls_layout.addWidget(weight_frame)
        amount_frame = QFrame(); amount_frame.setFrameShape(QFrame.StyledPanel); amount_frame.setStyleSheet("QFrame { background: #f7f7f7; border: 1px solid #e0e0e0; border-radius: 8px; padding: 5px; }"); amount_frame.setLayout(self._create_amount_display()); controls_layout.addWidget(amount_frame)
        keypad_frame = QFrame(); keypad_frame.setFrameShape(QFrame.StyledPanel); keypad_frame.setLayout(self._create_keyboard()); controls_layout.addWidget(keypad_frame); controls_layout.addStretch()
        bottom_frame = QFrame(); bottom_frame.setLayout(self._create_bottom_bar()); controls_layout.addWidget(bottom_frame, alignment=Qt.AlignHCenter)
        main_h_layout.addWidget(controls_frame, 1)
        camera_frame = QFrame(); camera_frame.setFrameShape(QFrame.StyledPanel); camera_frame.setStyleSheet("QFrame { background-color: black; border: 2px solid #555; border-radius: 8px; }")
        camera_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        camera_layout = QVBoxLayout(camera_frame); camera_label = QLabel("CAMERA FEED"); camera_label.setAlignment(Qt.AlignCenter); camera_label.setFont(QFont("Arial", 24, QFont.Bold)); camera_label.setStyleSheet("color: white;"); camera_layout.addWidget(camera_label); main_h_layout.addWidget(camera_frame, 2)
    def _create_top_bar(self):
        layout = QHBoxLayout(); date_label = QLabel("Date:"); date_label.setFont(self.font_label); self.date_field = QLineEdit(); self.date_field.setFont(self.font_input); self.date_field.setReadOnly(True); self.date_field.setFixedWidth(170)
        layout.addWidget(date_label); layout.addWidget(self.date_field); layout.addSpacing(20)
        time_label = QLabel("Time:"); time_label.setFont(self.font_label); self.time_field = QLineEdit(); self.time_field.setFont(self.font_input); self.time_field.setReadOnly(True); self.time_field.setFixedWidth(130)
        layout.addWidget(time_label); layout.addWidget(self.time_field); layout.addStretch()
        weight_label = QLabel("Weight (KG):"); weight_label.setFont(self.font_label); self.weight_display = QLabel(self.get_fake_weight()); self.weight_display.setFont(self.font_weight); self.weight_display.setAlignment(Qt.AlignRight | Qt.AlignVCenter); self.weight_display.setStyleSheet("color:white; background:black; border-radius: 10px; padding: 4px 32px; min-width: 200px;")
        layout.addWidget(weight_label); layout.addWidget(self.weight_display); return layout
    def _create_vehicle_entry(self):
        layout = QHBoxLayout()
        search_label = QLabel("Search Ticket/Vehicle:"); search_label.setFont(self.font_label)
        self.search_input = QLineEdit(); self.search_input.setFont(QFont("Arial", 22, QFont.Bold)); self.search_input.setFixedSize(350, 48)
        self.search_input.setStyleSheet("background: #fff7d6; border: 2px solid #ff6600; color: #003366; padding: 4px; border-radius: 8px;")
        layout.addWidget(search_label); layout.addWidget(self.search_input); layout.addSpacing(12)
        self.ok_btn = QPushButton("OK"); self.ok_btn.setFont(QFont("Arial", 16, QFont.Bold)); self.ok_btn.setFixedSize(120, 48); self.ok_btn.setStyleSheet("padding: 0 5px; background-color: #c6ffc6; border: 2px solid #0b0; border-radius: 8px;")
        layout.addWidget(self.ok_btn); layout.addStretch(); return layout
    def _create_weight_details(self):
        layout = QHBoxLayout(); self.empty_weight_label = QLabel("Empty:"); self.empty_weight_label.setFont(self.font_label); self.empty_weight_field = QLineEdit(); self.empty_weight_field.setFont(self.font_amount); self.empty_weight_field.setReadOnly(True); self.empty_weight_field.setFixedWidth(120)
        layout.addWidget(self.empty_weight_label); layout.addWidget(self.empty_weight_field); layout.addSpacing(20)
        self.load_weight_label = QLabel("Load:"); self.load_weight_label.setFont(self.font_label); self.load_weight_field = QLineEdit(); self.load_weight_field.setFont(self.font_amount); self.load_weight_field.setReadOnly(True); self.load_weight_field.setFixedWidth(120)
        layout.addWidget(self.load_weight_label); layout.addWidget(self.load_weight_field); layout.addSpacing(40)
        net_label = QLabel("Net Weight:"); net_label.setFont(self.font_net_weight); self.net_weight_field = QLineEdit(); self.net_weight_field.setFont(self.font_net_weight); self.net_weight_field.setReadOnly(True); self.net_weight_field.setFixedWidth(180)
        layout.addWidget(net_label); layout.addWidget(self.net_weight_field); layout.addStretch(); return layout
    def _create_amount_display(self):
        layout = QHBoxLayout(); eamount_label = QLabel("E-Amount:"); eamount_label.setFont(self.font_label); self.eamount_input = QLineEdit(); self.eamount_input.setFont(self.font_amount); self.eamount_input.setReadOnly(True); self.eamount_input.setFixedWidth(80)
        layout.addWidget(eamount_label); layout.addWidget(self.eamount_input); layout.addSpacing(20)
        lamount_label = QLabel("L-Amount:"); lamount_label.setFont(self.font_label); self.lamount_input = QLineEdit(); self.lamount_input.setFont(self.font_amount); self.lamount_input.setReadOnly(True); self.lamount_input.setFixedWidth(80)
        layout.addWidget(lamount_label); layout.addWidget(self.lamount_input); layout.addSpacing(20)
        tamount_label = QLabel("T-Amount:"); tamount_label.setFont(self.font_label); self.tamount_input = QLineEdit(); self.tamount_input.setFont(self.font_amount); self.tamount_input.setReadOnly(True); self.tamount_input.setFixedWidth(80)
        layout.addWidget(tamount_label); layout.addWidget(self.tamount_input); layout.addStretch(); return layout
    def _create_keyboard(self):
        keypad_layout = QGridLayout(); keypad_layout.setHorizontalSpacing(10); keypad_layout.setVerticalSpacing(5); az_keys = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'; digit_keys = '1234567890'
        # Letter keys
        for idx, key in enumerate(az_keys):
            btn = QPushButton(key); btn.setFont(self.letter_font); btn.setFixedSize(52, 52); btn.clicked.connect(lambda _, k=key: self.add_keypad_text(k))
            keypad_layout.addWidget(btn, idx // 7, idx % 7)
        # Digit keys arranged to avoid overlap; 0 is visible
        for idx, key in enumerate(digit_keys):
            btn = QPushButton(key); btn.setFont(self.digit_font); btn.setFixedSize(52, 52); btn.clicked.connect(lambda _, k=key: self.add_keypad_text(k))
            keypad_layout.addWidget(btn, idx // 3, 7 + (idx % 3))
        # Back and Clear aligned without overlapping '0'
        back_btn = QPushButton("<--"); back_btn.setFont(self.digit_font); back_btn.setFixedSize(52, 52); back_btn.clicked.connect(self.keypad_backspace); keypad_layout.addWidget(back_btn, 3, 8)
        clear_btn = QPushButton("Clear"); clear_btn.setFont(self.digit_font); clear_btn.setFixedSize(52, 52); clear_btn.setStyleSheet("background-color: red; color: white; font-weight: bold;"); clear_btn.clicked.connect(self.clear_all_fields); keypad_layout.addWidget(clear_btn, 3, 9)
        centered_layout = QHBoxLayout(); centered_layout.addStretch(); centered_layout.addLayout(keypad_layout); centered_layout.addStretch(); return centered_layout
    def _create_bottom_bar(self):
        bottom_layout = QHBoxLayout(); self.cancel_btn = QPushButton("Cancel"); self.cancel_btn.setFont(self.font_button); self.cancel_btn.setFixedSize(150, 48); self.cancel_btn.setStyleSheet("QPushButton {background: #fdd; border: 2px solid #a00; padding: 4px; font-size: 14pt; border-radius: 8px;}")
        bottom_layout.addWidget(self.cancel_btn); bottom_layout.addStretch(); return bottom_layout
    def _connect_signals(self):
        self.ok_btn.clicked.connect(self.ok_pressed); self.cancel_btn.clicked.connect(self.cancel_action)
    def _initialize_state(self):
        self.search_input.setFocus()
    def _start_timers(self):
        self.update_date_time(); timer = QTimer(self); timer.timeout.connect(self.update_date_time); timer.start(1000)
    def centerOnScreen(self):
        screen_geo = QApplication.primaryScreen().geometry(); self.move((screen_geo.width() - self.width()) // 2, (screen_geo.height() - self.height()) // 2)
    def update_date_time(self):
        now = QDate.currentDate(); current_time = QTime.currentTime(); self.date_field.setText(to_display_date(now)); self.time_field.setText(to_display_time(current_time))
    def get_fake_weight(self): return str(random.randint(15000, 40000))
    def add_keypad_text(self, char): self.search_input.insert(char)
    def keypad_backspace(self): self.search_input.backspace()
    def clear_all_fields(self):
        self.search_input.setReadOnly(False); self.search_input.clear()
        for field in [self.empty_weight_field, self.load_weight_field, self.net_weight_field, self.eamount_input, self.lamount_input, self.tamount_input]: field.clear()
        self.search_input.setFocus()

    def ok_pressed(self):
        search_term = self.search_input.text().strip().upper()
        if not search_term:
            QMessageBox.warning(self, "Input Required", "Please enter a Ticket Number or Vehicle Number to search."); return
        
        data = None
        if search_term.isdigit():
            data = fetch_one('SELECT * FROM tickets WHERE "TicketNumber" = %s AND "Pending" = TRUE', (int(search_term),))
        if not data:
            data = fetch_one('SELECT * FROM tickets WHERE "VehicleNumber" = %s AND "Pending" = TRUE', (search_term,))

        if data:
            if data.get("Closed"): QMessageBox.warning(self, "Ticket Closed", f"Ticket {data['TicketNumber']} is closed."); self.clear_all_fields(); return
            if not data.get("Pending"): QMessageBox.warning(self, "Not a Pending Ticket", f"Ticket {data['TicketNumber']} is not pending."); self.clear_all_fields(); return
            
            self.first_load_data = data
            self.search_input.setText(f"{data['TicketNumber']} / {data['VehicleNumber']}")
            self.search_input.setReadOnly(True)

            vehicle_type = data.get("VehicleType")
            
            if not vehicle_type:
                QMessageBox.information(self, "Vehicle Type Required", "This ticket is missing a Vehicle Type. Please select one to continue.")
                dialog = VehicleSelectionDialog(self)
                if dialog.exec_() == QDialog.Accepted:
                    vehicle_type = dialog.result
                    try:
                        execute_query('UPDATE tickets SET "VehicleType" = %s WHERE "TicketNumber" = %s', (vehicle_type, data['TicketNumber']))
                        data['VehicleType'] = vehicle_type
                    except Exception as e:
                        QMessageBox.critical(self, "Database Error", f"Could not update vehicle type for ticket:\n{e}")
                        self.clear_all_fields(); return
                else:
                    self.clear_all_fields(); return

            db_empty = data.get("EmptyWeight"); db_load = data.get("LoadedWeight"); current_weight = int(self.weight_display.text())
            final_empty, final_load, load_status_for_calc = (0, 0, "")
            if db_empty and not db_load:
                final_empty, final_load, load_status_for_calc = db_empty, current_weight, "Load"
            elif db_load and not db_empty:
                final_empty, final_load, load_status_for_calc = current_weight, db_load, "Empty"
            
            self.empty_weight_field.setText(str(final_empty)); self.load_weight_field.setText(str(final_load)); self.net_weight_field.setText(str(abs(final_load - final_empty)))
            new_amounts = rate_calculator.calculate_amounts(vehicle_type, current_weight, load_status_for_calc)
            
            # --- Handle None from database by defaulting to 0 ---
            final_eamount = (data.get("EAMOUNT") or 0) + new_amounts.get('eamount', 0)
            final_lamount = (data.get("LAMOUNT") or 0) + new_amounts.get('lamount', 0)
            final_tamount = final_eamount + final_lamount
            
            self.eamount_input.setText(str(final_eamount)); self.lamount_input.setText(str(final_lamount)); self.tamount_input.setText(str(final_tamount))
            
            summary_data = {
                "TicketNumber": str(data.get("TicketNumber")), "Date": to_display_date(QDate.currentDate()), "Time": to_display_time(QTime.currentTime()),
                "LAST DATE": to_display_date(data.get("Date")), "LAST TIME": to_display_time(data.get("Time")),
                "VehicleNumber": str(data.get("VehicleNumber")), "VehicleType": vehicle_type,
                "EmptyWeight": self.empty_weight_field.text(), "LoadedWeight": self.load_weight_field.text(),
                "NetWeight": self.net_weight_field.text(), "EAMOUNT": self.eamount_input.text(),
                "LAMOUNT": self.lamount_input.text(), "TAMOUNT": self.tamount_input.text(),
            }
            dlg = SummaryDialog(self, summary_data, transaction_window=self)
            if dlg.exec_() == QDialog.Accepted: self.clear_all_fields()
        else:
            QMessageBox.warning(self, "Not Found", "No pending ticket found for the provided details."); self.clear_all_fields()

    def cancel_action(self):
        if self.transaction_window: self.transaction_window.show()
        self.close()

if __name__ == "__main__":
    app = QApplication(sys.argv); win = SecondLoadWindow(); win.show(); sys.exit(app.exec_())
