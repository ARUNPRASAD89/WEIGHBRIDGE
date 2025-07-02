import sys
import random
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QHBoxLayout, QGridLayout, QButtonGroup, QApplication, QDialog, QMessageBox
)
from PyQt5.QtCore import Qt, QDate, QTime, QTimer
from PyQt5.QtGui import QFont, QIntValidator
from db_utils import execute_query, fetch_one


class SummaryDialog(QDialog):
    def __init__(self, parent, data, transaction_window=None):
        super().__init__(parent)
        self.setWindowTitle("Summary")
        self.setFixedSize(500, 540)
        self.setStyleSheet("background: #fff;")
        self.transaction_window = transaction_window
        self.data = data

        layout = QVBoxLayout(self)
        font = QFont("Arial", 16)

        def add_row(label, value):
            h = QHBoxLayout()
            lab = QLabel(label)
            val = QLabel(str(value))
            lab.setFont(font)
            val.setFont(font)
            h.addWidget(lab)
            h.addWidget(val)
            layout.addLayout(h)

        add_row("Ticket No:", data.get("TicketNumber", ""))
        add_row("Date:", data.get("Date", ""))
        add_row("Time:", data.get("Time", ""))
        add_row("Vehicle:", data.get("VehicleNumber", ""))
        add_row("Empty Weight:", data.get("EmptyWeight", ""))
        add_row("Load Weight:", data.get("LoadedWeight", ""))
        add_row("Net Weight:", data.get("NetWeight", ""))
        add_row("E-Amount:", data.get("EAMOUNT", ""))
        add_row("L-Amount:", data.get("LAMOUNT", ""))
        add_row("T-Amount:", data.get("TAMOUNT", ""))

        btn_row = QHBoxLayout()
        self.print_btn = QPushButton("WeighPrint")
        self.print_btn.setFont(QFont("Arial", 18, QFont.Bold))
        self.print_btn.setStyleSheet("background: #c6ffc6; border: 2px solid #0b0; border-radius: 8px;")
        self.print_btn.clicked.connect(self.on_weighprint)
        btn_row.addWidget(self.print_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setFont(QFont("Arial", 18, QFont.Bold))
        self.cancel_btn.setStyleSheet("background: #f88; border: 2px solid #a00; border-radius: 8px;")
        self.cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.cancel_btn)

        layout.addSpacing(12)
        layout.addLayout(btn_row)

        # Placeholder for the success label
        self.success_label = QLabel("", self)
        self.success_label.setAlignment(Qt.AlignCenter)
        self.success_label.setFont(QFont("Arial", 18, QFont.Bold))
        self.success_label.setStyleSheet("color: green;")
        layout.addWidget(self.success_label)

    def on_weighprint(self):
        try:
            update_query = """
                UPDATE tickets SET
                    "LoadedWeight" = %s,
                    "LoadWeightDate" = %s,
                    "LoadWeightTime" = %s,
                    "EmptyWeight" = %s,
                    "EmptyWeightDate" = %s,
                    "EmptyWeightTime" = %s,
                    "NetWeight" = %s,
                    "EAMOUNT" = %s,
                    "LAMOUNT" = %s,
                    "TAMOUNT" = %s,
                    "Pending" = FALSE,
                    "Closed" = TRUE
                WHERE "TicketNumber" = %s
            """
            params = (
                self.data.get("LoadedWeight", None) or None,
                self.data.get("Date", None) or None,
                self.data.get("Time", None) or None,
                self.data.get("EmptyWeight", None) or None,
                self.data.get("Date", None) or None,
                self.data.get("Time", None) or None,
                self.data.get("NetWeight", None) or None,
                self.data.get("EAMOUNT", None) or None,
                self.data.get("LAMOUNT", None) or None,
                self.data.get("TAMOUNT", None) or None,
                self.data.get("TicketNumber", None),
            )
            execute_query(update_query, params)

            self.print_btn.setEnabled(False)
            self.cancel_btn.setEnabled(False)

            ticket_number = self.data.get('TicketNumber', '')
            self.success_label.setText(f"Successfully saved to ticket number {ticket_number}")

            def finish():
                self.accept()
                parent = self.parent()
                if parent:
                    parent.close()  # closes SecondLoadWindow
                if self.transaction_window:
                    self.transaction_window.show()

            QTimer.singleShot(5000, finish)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save ticket:\n{e}")

    

class SecondLoadWindow(QWidget):
    def __init__(self, transaction_window=None):
        super().__init__()
        self.setWindowTitle("Vehicle Second Transaction")
        self.setFixedSize(1280, 768)
        self.setStyleSheet("background: #fff;")
        self.first_load_data = None
        self.transaction_window = transaction_window

        font_label = QFont("Arial", 18, QFont.Bold)
        font_input = QFont("Arial", 18)
        font_weight = QFont("Arial", 28, QFont.Bold)
        font_button = QFont("Arial", 18, QFont.Bold)
        font_wheel = QFont("Arial", 18, QFont.Bold)
        font_amount = QFont("Arial", 18, QFont.Bold)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(16, 16, 16, 16)

        # Row 2: Date, Ticket No, Weight
        row2 = QHBoxLayout()
        date_label = QLabel("Date:")
        date_label.setFont(font_label)
        self.date_field = QLineEdit()
        self.date_field.setFont(font_input)
        self.date_field.setReadOnly(True)
        self.date_field.setMaximumWidth(170)
        self.date_field.setMinimumWidth(140)
        row2.addWidget(date_label)
        row2.addWidget(self.date_field)
        row2.addSpacing(20)

        ticket_label = QLabel("Ticket No:")
        ticket_label.setFont(font_label)
        self.ticket_number = QLineEdit()
        self.ticket_number.setFont(font_input)
        self.ticket_number.setReadOnly(False)
        self.ticket_number.setMaximumWidth(110)
        self.ticket_number.setMinimumWidth(90)
        self.ticket_number.setValidator(QIntValidator(0, 99999999, self))  # Only numbers allowed
        row2.addWidget(ticket_label)
        row2.addWidget(self.ticket_number)
        row2.addSpacing(20)

        weight_label = QLabel("Weight (kg):")
        weight_label.setFont(font_label)
        self.weight_display = QLabel(self.get_fake_weight())
        self.weight_display.setFont(font_weight)
        self.weight_display.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.weight_display.setStyleSheet("color:white; background:black; border-radius: 10px; padding: 4px 32px; min-width: 100px;")
        row2.addWidget(weight_label)
        row2.addWidget(self.weight_display)

        row2.addStretch()
        main_layout.addLayout(row2)

        # Row 3: Time, Vehicle, OK, Empty/Load fields on right
        row3 = QHBoxLayout()
        time_label = QLabel("Time:")
        time_label.setFont(font_label)
        self.time_field = QLineEdit()
        self.time_field.setFont(font_input)
        self.time_field.setReadOnly(True)
        self.time_field.setMaximumWidth(130)
        self.time_field.setMinimumWidth(110)
        row3.addWidget(time_label)
        row3.addWidget(self.time_field)
        row3.addSpacing(15)

        vehicle_label = QLabel("Vehicle:")
        vehicle_label.setFont(font_label)
        self.vehicle_input = QLineEdit()
        self.vehicle_input.setFont(QFont("Arial", 22, QFont.Bold))
        self.vehicle_input.setReadOnly(False)
        self.vehicle_input.setMinimumWidth(230)
        self.vehicle_input.setMaximumWidth(250)
        self.vehicle_input.setMinimumHeight(38)
        self.vehicle_input.setStyleSheet(
            "background: #fff7d6; border: 2px solid #ff6600; color: #003366; padding: 4px; border-radius: 8px;"
        )
        row3.addWidget(vehicle_label)
        row3.addWidget(self.vehicle_input)

        self.ok_btn = QPushButton("OK")
        self.ok_btn.setFont(QFont("Arial", 16, QFont.Bold))
        self.ok_btn.setFixedSize(120, 38)
        self.ok_btn.setStyleSheet("padding: 0 5px; background-color: #c6ffc6; border: 2px solid #0b0; border-radius: 8px;")
        self.ok_btn.clicked.connect(self.ok_pressed)
        row3.addSpacing(12)
        row3.addWidget(self.ok_btn)

        row3.addStretch(1)

        # Right-aligned: Empty/Load fields
        self.empty_weight_label = QLabel("Empty:")
        self.empty_weight_label.setFont(font_label)
        self.empty_weight_field = QLineEdit()
        self.empty_weight_field.setFont(font_amount)
        self.empty_weight_field.setReadOnly(True)
        self.empty_weight_field.setMaximumWidth(120)
        self.empty_weight_field.setMinimumWidth(80)
        self.empty_weight_field.setAlignment(Qt.AlignRight)
        row3.addWidget(self.empty_weight_label)
        row3.addWidget(self.empty_weight_field)
        row3.addSpacing(30)

        self.load_weight_label = QLabel("Load Weight:")
        self.load_weight_label.setFont(font_label)
        self.load_weight_field = QLineEdit()
        self.load_weight_field.setFont(font_amount)
        self.load_weight_field.setReadOnly(True)
        self.load_weight_field.setMaximumWidth(120)
        self.load_weight_field.setMinimumWidth(80)
        self.load_weight_field.setAlignment(Qt.AlignRight)
        row3.addWidget(self.load_weight_label)
        row3.addWidget(self.load_weight_field)
        main_layout.addLayout(row3)

        # Net Weight row
        net_row = QHBoxLayout()
        net_row.addStretch()
        net_label = QLabel("Net Weight:")
        net_label.setFont(QFont("Arial", 22, QFont.Bold))
        self.net_weight_field = QLineEdit()
        self.net_weight_field.setFont(QFont("Arial", 22, QFont.Bold))
        self.net_weight_field.setReadOnly(True)
        self.net_weight_field.setMaximumWidth(180)
        self.net_weight_field.setMinimumWidth(120)
        self.net_weight_field.setAlignment(Qt.AlignRight)
        net_row.addWidget(net_label)
        net_row.addWidget(self.net_weight_field)
        net_row.addStretch()
        main_layout.addLayout(net_row)

        # Row 4: Wheels (not selectable)
        wheels_row = QHBoxLayout()
        wheels_label = QLabel("Wheels:")
        wheels_label.setFont(font_label)
        self.wheel_btns = []
        self.wheel_btn_group = QButtonGroup(self)
        wheel_options = [
            "4", "6 ", "10 ", "12 ",
            "14 ", "16 ", "18 ", "20+"
        ]
        button_size = 58
        for idx, label in enumerate(wheel_options):
            btn = QPushButton(label)
            btn.setStyleSheet("background-color: blue; color: white; font-weight: bold; text-align: center;")
            btn.setFont(font_wheel)
            btn.setCheckable(True)
            btn.setMinimumSize(button_size, button_size)
            btn.setMaximumSize(button_size, button_size)
            btn.setToolTip(label)
            btn.setEnabled(False)  # Not selectable in second load
            self.wheel_btns.append(btn)
            self.wheel_btn_group.addButton(btn, idx)
            wheels_row.addWidget(btn)
        wheels_row.addStretch()
        main_layout.addLayout(wheels_row)

        # Row 5: Load Status
        load_hbox = QHBoxLayout()
        load_label = QLabel("Load Status:")
        load_label.setFont(font_label)
        self.empty_btn = QPushButton("Empty")
        self.load_btn = QPushButton("Load")
        self.empty_btn.setFont(font_button)
        self.load_btn.setFont(font_button)
        self.empty_btn.setCheckable(True)
        self.load_btn.setCheckable(True)
        self.empty_btn.setMinimumWidth(80)
        self.load_btn.setMinimumWidth(80)
        self.empty_btn.setEnabled(False)
        self.load_btn.setEnabled(False)
        load_hbox.addWidget(load_label)
        load_hbox.addWidget(self.empty_btn)
        load_hbox.addWidget(self.load_btn)
        load_hbox.addSpacing(8)
        self.load_status_display = QLabel("")
        self.load_status_display.setFont(font_button)
        self.load_status_display.setAlignment(Qt.AlignCenter)
        self.load_status_display.setMaximumWidth(90)
        self.load_status_display.setStyleSheet("background: #fff; color: #004080; border: none;")
        load_hbox.addWidget(self.load_status_display)
        load_hbox.addStretch()
        main_layout.addLayout(load_hbox)

        # Row 6: Amounts
        amount_hbox = QHBoxLayout()
        eamount_label = QLabel("E-Amount:")
        eamount_label.setFont(font_label)
        self.eamount_input = QLineEdit()
        self.eamount_input.setFont(font_amount)
        self.eamount_input.setReadOnly(True)
        self.eamount_input.setMaximumWidth(70)
        self.eamount_input.setMinimumWidth(50)
        amount_hbox.addWidget(eamount_label)
        amount_hbox.addWidget(self.eamount_input)
        amount_hbox.addSpacing(20)

        lamount_label = QLabel("L-Amount:")
        lamount_label.setFont(font_label)
        self.lamount_input = QLineEdit()
        self.lamount_input.setFont(font_amount)
        self.lamount_input.setReadOnly(True)
        self.lamount_input.setMaximumWidth(70)
        self.lamount_input.setMinimumWidth(50)
        amount_hbox.addWidget(lamount_label)
        amount_hbox.addWidget(self.lamount_input)
        amount_hbox.addSpacing(20)

        tamount_label = QLabel("T-Amount:")
        tamount_label.setFont(font_label)
        self.tamount_input = QLineEdit()
        self.tamount_input.setFont(font_amount)
        self.tamount_input.setReadOnly(True)
        self.tamount_input.setMaximumWidth(70)
        self.tamount_input.setMinimumWidth(50)
        amount_hbox.addWidget(tamount_label)
        amount_hbox.addWidget(self.tamount_input)
        amount_hbox.addStretch()
        main_layout.addLayout(amount_hbox)

        # Keypad Layout (same as first load)
        main_keypad_grid = QGridLayout()
        main_keypad_grid.setHorizontalSpacing(12)
        main_keypad_grid.setVerticalSpacing(4)
        letter_btn_size = 48
        digit_btn_size = 56
        backclear_btn_width = digit_btn_size * 2 + 4
        letter_font = QFont("Arial", 20, QFont.Bold)
        digit_font = QFont("Arial", 22, QFont.Bold)

        az_keys = 'A B C D E F G H I J K L M N O P Q R S T U V W X Y Z'.split()
        for idx, key in enumerate(az_keys):
            btn = QPushButton(key)
            btn.setFont(letter_font)
            btn.setFixedSize(letter_btn_size, letter_btn_size)
            btn.clicked.connect(lambda _, k=key: self.add_keypad_text(k))
            row = idx // 7
            col = idx % 7
            main_keypad_grid.addWidget(btn, row, col)

        digit_keys = [
            ['7', '8', '9'],
            ['4', '5', '6'],
            ['1', '2', '3'],
            ['',  '0', '']
        ]
        for row, line in enumerate(digit_keys):
            for col, key in enumerate(line):
                if key:
                    btn = QPushButton(key)
                    btn.setFont(digit_font)
                    btn.setFixedSize(digit_btn_size, letter_btn_size)
                    btn.clicked.connect(lambda _, k=key: self.add_keypad_text(k))
                    main_keypad_grid.addWidget(btn, row, 7 + col)

        row_below = 4
        back_btn = QPushButton("<--")
        back_btn.setFont(digit_font)
        back_btn.setFixedSize(backclear_btn_width, letter_btn_size)
        back_btn.clicked.connect(self.keypad_backspace)
        main_keypad_grid.addWidget(back_btn, row_below, 11, 1, 2)

        clear_btn = QPushButton("Clear")
        clear_btn.setFont(digit_font)
        clear_btn.setFixedSize(backclear_btn_width, letter_btn_size)
        clear_btn.setStyleSheet("background-color: red; color: white; font-weight: bold;")
        clear_btn.clicked.connect(self.clear_all_fields)
        main_keypad_grid.addWidget(clear_btn, row_below, 13, 1, 2)

        keypad_center_hbox = QHBoxLayout()
        keypad_center_hbox.addStretch(1)
        keypad_center_hbox.addLayout(main_keypad_grid)
        keypad_center_hbox.addStretch(1)
        main_layout.addLayout(keypad_center_hbox)

        # Operation buttons
        bottom_layout = QHBoxLayout()
        self.op_buttons = []
        operations = [
            ("Weigh", self.weigh_action),
            ("Save", self.save_action),
            ("Preview", self.preview_action),
            ("Print", self.print_action),
            ("Export", self.export_action),
            ("Search", self.search_action),
            ("Cancel", self.cancel_action),
        ]
        for name, action in operations:
            op_btn = QPushButton(name)
            op_btn.setFont(font_button)
            op_btn.setMinimumHeight(38)
            op_btn.setMinimumWidth(90)
            op_btn.setStyleSheet("QPushButton {background: #fff; border: 2px solid #000; padding: 4px; font-size: 14pt;}")
            op_btn.clicked.connect(action)
            bottom_layout.addWidget(op_btn)
            self.op_buttons.append(op_btn)
        main_layout.addLayout(bottom_layout)
        main_layout.addSpacing(4)
        self.setLayout(main_layout)

        # --- Focus tracking for keypad ---
        self.active_input = self.vehicle_input
        self.vehicle_input.installEventFilter(self)
        self.ticket_number.installEventFilter(self)

        # Initialize
        self.update_date_time()
        timer = QTimer(self)
        timer.timeout.connect(self.update_date_time)
        timer.start(1000)

    def eventFilter(self, obj, event):
        if event.type() == event.FocusIn:
            self.active_input = obj
        return super().eventFilter(obj, event)

    def update_date_time(self):
        now = QDate.currentDate()
        current_time = QTime.currentTime()
        self.date_field.setText(now.toString("dd/MM/yyyy"))
        self.time_field.setText(current_time.toString("HH:mm:ss"))

    def get_fake_weight(self):
        return str(random.randint(12000, 50000))

    def add_keypad_text(self, char):
        if self.active_input is not None:
            self.active_input.insert(char)

    def keypad_backspace(self):
        if self.active_input is not None:
            self.active_input.backspace()

    def clear_all_fields(self):
        self.vehicle_input.setReadOnly(False)
        self.ticket_number.setReadOnly(False)
        self.vehicle_input.clear()
        self.ticket_number.clear()
        self.empty_weight_field.clear()
        self.load_weight_field.clear()
        self.net_weight_field.clear()
        self.eamount_input.clear()
        self.lamount_input.clear()
        self.tamount_input.clear()
        self.load_status_display.setText("")
        for btn in self.wheel_btns:
            btn.setChecked(False)
        self.empty_btn.setChecked(False)
        self.load_btn.setChecked(False)
        self.vehicle_input.setFocus()
        self.active_input = self.vehicle_input
        self.date_field.clear()
        self.time_field.clear()

    def ok_pressed(self):
        ticket = self.ticket_number.text().strip()
        vehicle = self.vehicle_input.text().strip().upper()
        data = None

        # Fetch from DB
        if ticket and not vehicle:
            data = fetch_one('SELECT * FROM tickets WHERE "TicketNumber" = %s', (ticket,))
            if data:
                vehicle = data["VehicleNumber"]
                self.vehicle_input.setText(vehicle)
        elif vehicle and not ticket:
            data = fetch_one('SELECT * FROM tickets WHERE "VehicleNumber" = %s AND "Pending" = TRUE', (vehicle,))
            if data:
                ticket = data["TicketNumber"]
                self.ticket_number.setText(str(ticket))
        elif vehicle and ticket:
            data = fetch_one('SELECT * FROM tickets WHERE "VehicleNumber" = %s AND "TicketNumber" = %s', (vehicle, ticket))
        else:
            self.load_status_display.setText("Enter ticket or vehicle number!")
            return

        if data:
            self.first_load_data = data
            self.ticket_number.setText(str(data["TicketNumber"]))
            self.vehicle_input.setText(data["VehicleNumber"])
            self.date_field.setText(str(data["Date"]))
            self.time_field.setText(str(data["Time"]))

            # Amounts
            self.eamount_input.setText(str(data.get("EAMOUNT", "")) if data.get("EAMOUNT") is not None else "")
            self.lamount_input.setText(str(data.get("LAMOUNT", "")) if data.get("LAMOUNT") is not None else "")
            self.tamount_input.setText(str(data.get("TAMOUNT", "")) if data.get("TAMOUNT") is not None else "")

            # Fill weights according to weighbridge logic
            db_empty = str(data.get("EmptyWeight", "") or "")
            db_load = str(data.get("LoadedWeight", "") or "")
            current_weight = self.weight_display.text()

            if db_empty and not db_load:
                self.empty_weight_field.setText(db_empty)
                self.load_weight_field.setText(current_weight)
                try:
                    net_wt = int(current_weight) - int(db_empty)
                    self.net_weight_field.setText(str(net_wt))
                except Exception:
                    self.net_weight_field.setText("")
                self.load_status_display.setText("Load")
            elif db_load and not db_empty:
                self.empty_weight_field.setText(current_weight)
                self.load_weight_field.setText(db_load)
                try:
                    net_wt = int(db_load) - int(current_weight)
                    self.net_weight_field.setText(str(net_wt))
                except Exception:
                    self.net_weight_field.setText("")
                self.load_status_display.setText("Empty")
            elif db_empty and db_load:
                self.empty_weight_field.setText(db_empty)
                self.load_weight_field.setText(db_load)
                try:
                    net_wt = int(db_load) - int(db_empty)
                    self.net_weight_field.setText(str(net_wt))
                except Exception:
                    self.net_weight_field.setText("")
                self.load_status_display.setText("Both")
            else:
                self.empty_weight_field.setText("")
                self.load_weight_field.setText(current_weight)
                self.net_weight_field.setText("")
                self.load_status_display.setText("Load")

            self.vehicle_input.setReadOnly(True)
            self.ticket_number.setReadOnly(True)

            summary_data = {
                "TicketNumber": str(data.get("TicketNumber", "")),
                "Date": str(data.get("Date", "")),
                "Time": str(data.get("Time", "")),
                "VehicleNumber": str(data.get("VehicleNumber", "")),
                "EmptyWeight": self.empty_weight_field.text(),
                "LoadedWeight": self.load_weight_field.text(),
                "NetWeight": self.net_weight_field.text(),
                "EAMOUNT": self.eamount_input.text(),
                "LAMOUNT": self.lamount_input.text(),
                "TAMOUNT": self.tamount_input.text(),
            }

            # -- THE ONLY THING THAT HAPPENS AFTER GETTING DATA --
            dlg = SummaryDialog(self, summary_data, transaction_window=self.transaction_window)
            dlg.exec_()
            # DO NOT call self.close() here!
        else:
            self.clear_all_fields()
            self.load_status_display.setText("Not Found!")

    def weigh_action(self): pass
    def save_action(self): pass
    def preview_action(self): pass
    def print_action(self): pass
    def export_action(self): pass
    def search_action(self): pass
    def cancel_action(self): self.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = SecondLoadWindow()
    win.show()
    sys.exit(app.exec_())
