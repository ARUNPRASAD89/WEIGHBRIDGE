import re
import sys
import random
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QHBoxLayout, QGridLayout, QButtonGroup,
    QApplication, QSizePolicy, QMessageBox, QDialog
)
from PyQt5.QtCore import Qt, QDate, QTime, QTimer
from PyQt5.QtGui import QFont
from db_utils import execute_query, fetch_one
from ticket_printer import render_ticket_with_data,print_ticket_using_default_template
from ticket_preview_window import TicketPreviewDialog

def get_default_template_and_fields():
    # Fetch the default template
    tpl_row = fetch_one('SELECT templatename, ticketheight, ticketwidth FROM templatemaster WHERE defaulttemplate=TRUE')
    if not tpl_row:
        raise Exception("No default template set in DB")
    templatename = tpl_row['templatename']
    ticket_height = float(tpl_row['ticketheight'])
    ticket_width = float(tpl_row['ticketwidth'])
    # Fetch all template fields
    fields = execute_query(
        'SELECT fieldname, x, y, width, height, fontname, fontsize FROM templatefields WHERE templatename=%s ORDER BY id',
        (templatename,)
    )
    template_fields = []
    for f in fields:
        template_fields.append({
            'fieldname': str(f[0]),
            'x': float(f[1]),
            'y': float(f[2]),
            'width': float(f[3]),
            'height': float(f[4]),
            'fontname': str(f[5]),
            'fontsize': int(f[6])
        })
    return template_fields, ticket_width, ticket_height



# --- NEW: OldWeightDialog ---
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

        # Info Label
        self.info_label = QLabel("OLD WEIGHT IS PRESENT")
        self.info_label.setFont(atm_font)
        self.info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.info_label, alignment=Qt.AlignCenter)

        # Buttons Row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(40)

        # X Button
        self.x_btn = QPushButton("X")
        self.x_btn.setFont(QFont("Arial", 28, QFont.Bold))
        self.x_btn.setFixedSize(110, 80)
        self.x_btn.setStyleSheet("background-color: red; color: white; border-radius: 18px;")
        self.x_btn.clicked.connect(lambda: self.x_pressed(ticket_number))
        btn_row.addWidget(self.x_btn)

        # 2 Button
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

# --- SummaryDialog for new tickets ---
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
            lab = QLabel(label)
            val = QLabel(str(value))
            lab.setFont(font)
            val.setFont(font)
            h.addWidget(lab)
            h.addWidget(val)
            layout.addLayout(h)
        add_row("Ticket No:", ticket_no)
        add_row("Date:", date)
        add_row("Time:", time)
        add_row("Vehicle:", vehicle_number)
        add_row("Weight:", weight)
        add_row("Wheels:", wheel_label)
        add_row("Status:", status)
        add_row("E-Amount:", eamount)
        add_row("L-Amount:", lamount)
        add_row("T-Amount:", tamount)
        btn_row = QHBoxLayout()
        self.wp_btn = QPushButton("WeighPrint")
        self.wp_btn.setFont(QFont("Arial", 18, QFont.Bold))
        self.wp_btn.setStyleSheet("background: #c6ffc6; border: 2px solid #0b0; border-radius: 8px;")
        self.wp_btn.clicked.connect(self.on_weightprint)
        btn_row.addWidget(self.wp_btn)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setFont(QFont("Arial", 18, QFont.Bold))
        self.cancel_btn.setStyleSheet("background: #f88; border: 2px solid #a00; border-radius: 8px;")
        self.cancel_btn.clicked.connect(self.on_cancel)
        btn_row.addWidget(self.cancel_btn)
        layout.addSpacing(12)
        layout.addLayout(btn_row)
        self.success_label = QLabel("", self)
        self.success_label.setAlignment(Qt.AlignCenter)
        self.success_label.setFont(QFont("Arial", 18, QFont.Bold))
        self.success_label.setStyleSheet("color: green;")
        layout.addWidget(self.success_label)
        self.ticket_no = ticket_no
        self.date = date
        self.time = time
        self.vehicle_number = vehicle_number
        self.weight = weight
        self.status = status
        self.eamount = eamount
        self.lamount = lamount
        self.tamount = tamount
        # For timer and preview
        self._preview_dialog = None
        self._print_timer = None
        self._finish_timer = None


    def on_weightprint(self):
        try:
            empty_weight = self.weight if self.status == "Empty" else None
            loaded_weight = self.weight if self.status == "Load" else None
            net_weight = None
            if empty_weight and loaded_weight:
                net_weight = int(loaded_weight) - int(empty_weight)
            elif loaded_weight:
                net_weight = int(loaded_weight)
            elif empty_weight:
                net_weight = int(empty_weight)
            def to_int_or_none(s):
                try:
                    return int(s)
                except Exception:
                    return None
            eamount = to_int_or_none(self.eamount)
            lamount = to_int_or_none(self.lamount)
            tamount = to_int_or_none(self.tamount)
        # ... rest of your ticket save/print code ...
            # ... ticket data preparation & DB save as before ...
            ticket_data = {
                "TicketNumber": self.ticket_no,
                "VehicleNumber": self.vehicle_number,
                "Date": self.date,
                "Time": self.time,
                "EmptyWeight": empty_weight or "",
                "LoadedWeight": loaded_weight or "",
                "NetWeight": net_weight or "",
                "EAMOUNT": eamount or "",
                "LAMOUNT": lamount or "",
                "TAMOUNT": tamount or "",
                "STATUS": self.status,
                "Materialname": "",
                "SupplierName": "",
                "State": "",
            }
            self.ticket_data = ticket_data 

            # --- Sequence Start ---
            self.wp_btn.setVisible(False)
            self.success_label.setText(f"TICKET SAVED!")
            # 1. Show print preview for 5 seconds
            self._preview_dialog = TicketPreviewDialog(ticket_data, parent=self)
            self._preview_dialog.show()
            self.print_preview_timer = QTimer(self)
            self.print_preview_timer.setSingleShot(True)
            self.print_preview_timer.timeout.connect(self._do_print_ticket)
            self.print_preview_timer.start(5000)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save/print ticket:\n{e}")

    def _do_print_ticket(self):
        if self._preview_dialog:
            self._preview_dialog.close()
        self.success_label.setText("Printing ticket...")
        print_ticket_using_default_template(self.ticket_data, parent=self, preview=False)
        self._finish_timer = QTimer(self)
        self._finish_timer.setSingleShot(True)
        self._finish_timer.timeout.connect(self._finish_and_goto_transaction)
        self._finish_timer.start(5000)

    def _finish_and_goto_transaction(self):
        self.accept()
        if self.transaction_window:
            parent = self.parent()
            if parent:
                parent.close()
            self.transaction_window.show()
        else:
            parent = self.parent()
            if parent:
                parent.show()

    def on_cancel(self):
        self.reject()
        if self.transaction_window:
            parent = self.parent()
            if parent:
                parent.close()
            self.transaction_window.show()
        else:
            parent = self.parent()
            if parent:
                parent.show()

WHEEL_RATES = {
    "4 wheels": 60, "6 wheels": 80, "10 wheels": 100, "12 wheels": 120,
    "14 wheels": 150, "16 wheels": 180, "18 wheels": 210, "20+ wheels": 250,
}
def is_valid_indian_plate(text):
    text = text.upper()
    patterns = [
        r'^[A-Z]{2}\d{2}[A-Z]{1,3}\d{4}$',
        r'^[A-Z]{2}\d{2}[A-Z]{0,2}\d{4}$',
        r'^[A-Z]{3}\d{4}$',
        r'^[A-Z]{2}\d{4}$',
    ]
    return any(re.fullmatch(pattern, text) for pattern in patterns)

class FirstLoadWindow(QWidget):
    def __init__(self, mode_window=None):
        super().__init__()
        self.setWindowTitle("Vehicle First Transaction")
        self.setFixedSize(1280, 768)
        self.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.WindowMinimizeButtonHint | Qt.WindowCloseButtonHint)
        self.setStyleSheet("background: #fff;")
        self.mode_window = mode_window

        font_label = QFont("Arial", 18, QFont.Bold)
        font_input = QFont("Arial", 18)
        font_weight = QFont("Arial", 28, QFont.Bold)
        font_button = QFont("Arial", 18, QFont.Bold)
        font_wheel = QFont("Arial", 18, QFont.Bold)
        font_keypad = QFont("Arial", 14, QFont.Bold)
        font_amount = QFont("Arial", 18, QFont.Bold)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(16, 16, 16, 16)

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
        self.ticket_number = QLineEdit(self.generate_ticket_number())
        self.ticket_number.setFont(font_input)
        self.ticket_number.setReadOnly(True)
        self.ticket_number.setMaximumWidth(110)
        self.ticket_number.setMinimumWidth(90)
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
        self.ok_btn = QPushButton("OK")
        self.ok_btn.setFont(QFont("Arial", 16, QFont.Bold))
        self.ok_btn.setFixedSize(120, 38)
        self.ok_btn.setStyleSheet("padding: 0 5px; background-color: #c6ffc6; border: 2px solid #0b0; border-radius: 8px;")
        self.ok_btn.clicked.connect(self.ok_pressed)
        self.ok_btn.setEnabled(False)
        row3.addWidget(vehicle_label)
        row3.addWidget(self.vehicle_input)
        row3.addSpacing(12)
        row3.addWidget(self.ok_btn)
        row3.addStretch()
        main_layout.addLayout(row3)

        row3_1 = QHBoxLayout()
        self.empty_weight_label = QLabel("Empty:")
        self.empty_weight_label.setFont(font_label)
        self.empty_weight_field = QLineEdit()
        self.empty_weight_field.setFont(font_amount)
        self.empty_weight_field.setReadOnly(True)
        self.empty_weight_field.setMaximumWidth(120)
        self.empty_weight_field.setMinimumWidth(80)
        self.empty_weight_field.setText("Empty Weight")
        row3_1.addWidget(self.empty_weight_label)
        row3_1.addWidget(self.empty_weight_field)
        row3_1.addSpacing(40)

        self.load_weight_label = QLabel("Load Weight:")
        self.load_weight_label.setFont(font_label)
        self.load_weight_field = QLineEdit()
        self.load_weight_field.setFont(font_amount)
        self.load_weight_field.setReadOnly(True)
        self.load_weight_field.setMaximumWidth(120)
        self.load_weight_field.setMinimumWidth(80)
        self.load_weight_field.setText("Load Weight")
        row3_1.addWidget(self.load_weight_label)
        row3_1.addWidget(self.load_weight_field)
        row3_1.addStretch()
        main_layout.addLayout(row3_1)

        wheels_row = QHBoxLayout()
        wheels_label = QLabel("Wheels:")
        wheels_label.setFont(font_label)
        wheels_row.addWidget(wheels_label, alignment=Qt.AlignVCenter)

        wheels_grid = QGridLayout()
        wheels_grid.setHorizontalSpacing(8)
        wheels_grid.setVerticalSpacing(8)
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
            self.wheel_btns.append(btn)
            btn.setFont(font_wheel)
            btn.setCheckable(True)
            btn.setMinimumSize(button_size, button_size)
            btn.setMaximumSize(button_size, button_size)
            btn.setToolTip(label)
            self.wheel_btn_group.addButton(btn, idx)
            wheels_grid.addWidget(btn, idx // 4, idx % 4)
        self.wheel_btn_group.buttonClicked.connect(self.wheel_selection_changed)

        wheels_row.addLayout(wheels_grid)
        wheels_row.addStretch()
        main_layout.addLayout(wheels_row)

        load_hbox = QHBoxLayout()
        load_label = QLabel("Load Status:")
        load_label.setFont(font_label)
        load_hbox.addWidget(load_label)
        self.empty_btn = QPushButton("Empty")
        self.load_btn = QPushButton("Load")
        self.empty_btn.setFont(font_button)
        self.load_btn.setFont(font_button)
        self.empty_btn.setCheckable(True)
        self.load_btn.setCheckable(True)
        self.empty_btn.setMinimumWidth(80)
        self.load_btn.setMinimumWidth(80)
        self.empty_btn.clicked.connect(self.set_empty)
        self.load_btn.clicked.connect(self.set_load)
        load_hbox.addWidget(self.empty_btn)
        load_hbox.addWidget(self.load_btn)
        load_hbox.addSpacing(8)
        self.load_status_display = QLabel("Empty")
        self.load_status_display.setFont(font_button)
        self.load_status_display.setAlignment(Qt.AlignCenter)
        self.load_status_display.setMaximumWidth(90)
        self.load_status_display.setStyleSheet("background: #fff; color: #004080; border: none;")
        load_hbox.addWidget(self.load_status_display)
        load_hbox.addStretch()
        main_layout.addLayout(load_hbox)

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

        main_layout.addSpacing(8)

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
            btn.clicked.connect(lambda _, k=key: self.vehicle_input.setText(self.vehicle_input.text() + k))
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
                    btn.clicked.connect(lambda _, k=key: self.vehicle_input.setText(self.vehicle_input.text() + k))
                    main_keypad_grid.addWidget(btn, row, 7 + col)

        row_below = 4
        back_btn = QPushButton("<--")
        back_btn.setFont(digit_font)
        back_btn.setFixedSize(backclear_btn_width, letter_btn_size)
        back_btn.clicked.connect(lambda: self.vehicle_input.setText(self.vehicle_input.text()[:-1]))
        main_keypad_grid.addWidget(back_btn, row_below, 11, 1, 2)

        clear_btn = QPushButton("Clear")
        clear_btn.setFont(digit_font)
        clear_btn.setFixedSize(backclear_btn_width, letter_btn_size)
        clear_btn.setStyleSheet("background-color: red; color: white; font-weight: bold;")
        clear_btn.clicked.connect(lambda: self.vehicle_input.setText(""))
        main_keypad_grid.addWidget(clear_btn, row_below, 13, 1, 2)

        keypad_center_hbox = QHBoxLayout()
        keypad_center_hbox.addStretch(1)
        keypad_center_hbox.addLayout(main_keypad_grid)
        keypad_center_hbox.addStretch(1)
        main_layout.addLayout(keypad_center_hbox)

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

        self.selected_wheel_label = "4 wheels"
        self.set_empty()
        self.wheel_btns[0].setChecked(True)

        self.update_date_time()
        timer = QTimer(self)
        timer.timeout.connect(self.update_date_time)
        timer.start(1000)

        self.vehicle_input.textChanged.connect(self.check_vehicle_entry_and_pending)
        self.centerOnScreen()
        self.update_weight_placeholders()

    def centerOnScreen(self):
        screen = QApplication.primaryScreen().geometry()
        size = self.geometry()
        self.move(
            (screen.width() - size.width()) // 2,
            (screen.height() - size.height()) // 2
        )

    def update_date_time(self):
        now = QDate.currentDate()
        current_time = QTime.currentTime()
        self.date_field.setText(now.toString("yyyy-MM-dd"))
        self.time_field.setText(current_time.toString("HH:mm:ss"))

    def generate_ticket_number(self):
        row = fetch_one('SELECT COALESCE(MAX(CAST("TicketNumber" AS INTEGER)), 10000) + 1 AS next_ticket FROM tickets')
        return str(row["next_ticket"])

    def get_fake_weight(self):
        return str(random.randint(5000, 12000))

    def check_vehicle_entry_and_pending(self):
        plate = self.vehicle_input.text().upper()
        if is_valid_indian_plate(plate):
            self.vehicle_input.setStyleSheet("background: #fff7d6; border: 2px solid green; color: #003366; padding: 4px; border-radius: 8px;")
            self.ok_btn.setEnabled(True)
        else:
            self.vehicle_input.setStyleSheet("background: #fff7d6; border: 2px solid #ff6600; color: #003366; padding: 4px; border-radius: 8px;")
            self.ok_btn.setEnabled(False)
            return

        if len(plate) >= 6:
            try:
                row = fetch_one(
                    'SELECT "TicketNumber", "VehicleNumber" FROM tickets WHERE "VehicleNumber" = %s AND "Pending" = TRUE',
                    (plate,)
                )
                if row:
                    dlg = OldWeightDialog(self, row["TicketNumber"], plate)
                    dlg.exec_()
                    if dlg.result == "x":
                        return  # Pending cleared, continue
                    elif isinstance(dlg.result, tuple):
                        ticket_number, vehicle_number = dlg.result
                        self.open_second_load_window(ticket_number, vehicle_number)
                        return
                else:
                    self.show_summary_dialog()
            except Exception as e:
                QMessageBox.critical(self, "Database Error", f"Error searching vehicle: {e}")

    def show_summary_dialog(self):
        ticket_no = self.ticket_number.text()
        date = self.date_field.text()
        time = self.time_field.text()
        vehicle_number = self.vehicle_input.text().upper()
        weight = self.weight_display.text()
        wheel_label = "4 wheels"
        for idx, btn in enumerate(self.wheel_btns):
            if btn.isChecked():
                wheel_label = [
                    "4 wheels", "6 wheels", "10 wheels", "12 wheels",
                    "14 wheels", "16 wheels", "18 wheels", "20+ wheels"
                ][idx]
                break
        status = self.load_status_display.text()
        eamount = self.eamount_input.text()
        lamount = self.lamount_input.text()
        tamount = self.tamount_input.text()
        dlg = SummaryDialog(self, ticket_no, date, time, vehicle_number, weight, wheel_label, status, eamount, lamount, tamount, transaction_window=self.mode_window)
        dlg.exec_()

    def open_second_load_window(self, ticket_number, vehicle_number):
        try:
            from second_load_window import SecondLoadWindow
        except ImportError:
            QMessageBox.critical(self, "Error", "SecondLoadWindow module not found.")
            return
        self.close()
        self.second_win = SecondLoadWindow()
        self.second_win.ticket_number.setText(str(ticket_number))
        self.second_win.vehicle_input.setText(str(vehicle_number))
        self.second_win.show()

    def set_empty(self):
        self.load_status_display.setText("Empty")
        self.empty_btn.setChecked(True)
        self.load_btn.setChecked(False)
        self.empty_btn.setStyleSheet("background-color: orange; font-weight: bold;")
        self.load_btn.setStyleSheet("")
        self.update_amount_fields("Empty")
        self.update_weight_placeholders()

    def set_load(self):
        self.load_status_display.setText("Load")
        self.load_btn.setChecked(True)
        self.empty_btn.setChecked(False)
        self.load_btn.setStyleSheet("background-color: orange; font-weight: bold;")
        self.empty_btn.setStyleSheet("")
        self.update_amount_fields("Load")
        self.update_weight_placeholders()

    def update_weight_placeholders(self):
        if self.empty_btn.isChecked():
            self.empty_weight_field.setText(self.weight_display.text())
            self.load_weight_field.clear()
        elif self.load_btn.isChecked():
            self.empty_weight_field.clear()
            self.load_weight_field.setText(self.weight_display.text())
        else:
            self.empty_weight_field.clear()
            self.load_weight_field.clear()

    def ok_pressed(self):
        # Your normal "first load" window logic goes here
        pass

    def wheel_selection_changed(self, button):
        idx = self.wheel_btn_group.id(button)
        self.selected_wheel_label = [
            "4 wheels", "6 wheels", "10 wheels", "12 wheels",
            "14 wheels", "16 wheels", "18 wheels", "20+ wheels"
        ][idx]
        self.update_amount_fields(self.load_status_display.text())

    def update_amount_fields(self, status):
        rate = WHEEL_RATES.get(self.selected_wheel_label, 0)
        if status == "Empty":
            self.eamount_input.setText(str(rate))
            self.lamount_input.setText("")
            self.tamount_input.setText(str(rate))
        elif status == "Load":
            self.lamount_input.setText(str(rate))
            self.eamount_input.setText("")
            self.tamount_input.setText(str(rate))

    def save_action(self):
        ticket_no = self.ticket_number.text()
        date = self.date_field.text()
        time = self.time_field.text()
        vehicle_number = self.vehicle_input.text().upper()
        empty_weight = self.empty_weight_field.text() or None
        load_weight = self.load_weight_field.text() or None
        net_weight = None
        try:
            if empty_weight and load_weight:
                net_weight = int(load_weight) - int(empty_weight)
            elif load_weight:
                net_weight = int(load_weight)
            elif empty_weight:
                net_weight = int(empty_weight)
            else:
                net_weight = None
        except (TypeError, ValueError):
            net_weight = None

        materialname, suppliername, shift, state = None, None, None, None

        # --- PATCH START: Set Pending/Closed flags based on weights ---
        if (empty_weight and not load_weight) or (load_weight and not empty_weight):
            pending = True
            closed = False
        elif empty_weight and load_weight:
            pending = False
            closed = True
        else:
            pending = True
            closed = False
        # --- PATCH END ---

        try:
            row = fetch_one(
                'SELECT "TicketNumber" FROM tickets WHERE "VehicleNumber" = %s AND "Pending" = TRUE',
                (vehicle_number,)
            )
            if row:
                QMessageBox.warning(self, "Pending Transaction",
                    f"Pending transaction found for vehicle {vehicle_number}. Returning to transaction window.")
                if self.mode_window:
                    self.mode_window.show()
                self.close()
                return
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Error searching vehicle: {e}")
            return

        insert_query = """
            INSERT INTO tickets (
                "VehicleNumber", "Date", "Time", "EmptyWeight", "LoadedWeight", "NetWeight",
                "Materialname", "SupplierName", "Shift", "State", "Pending", "Closed"
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            vehicle_number, date, time, empty_weight, load_weight, net_weight,
            materialname, suppliername, shift, state, pending, closed
        )

        try:
            execute_query(insert_query, params)
            QMessageBox.information(self, "Saved", f"Ticket {ticket_no} saved to database.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save ticket:\n{e}")

    def weigh_action(self):
        pass

    def preview_action(self):
        pass

    def print_action(self):
        pass

    def export_action(self):
        pass

    def search_action(self):
        pass

    def cancel_action(self):
        if self.mode_window:
            self.mode_window.show()
        self.close()

# if __name__ == "__main__":
#     app = QApplication(sys.argv)
#     win = FirstLoadWindow()
#     win.vehicle_input.setText("TN12AL8838")
#     win.wheel_btns[0].setChecked(True)
#     win.set_load()
#     win.check_vehicle_entry_and_pending()
#     win.show()
#     sys.exit(app.exec_())
