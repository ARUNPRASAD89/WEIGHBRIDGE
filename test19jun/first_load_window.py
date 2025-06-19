import re
import sys
import random
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QHBoxLayout, QGridLayout, QButtonGroup, QApplication, QSizePolicy
)
from PyQt5.QtCore import Qt, QDate, QTime, QTimer
from PyQt5.QtGui import QFont
from db_utils import execute_query
from PyQt5.QtWidgets import QMessageBox


WHEEL_RATES = {
    "4 wheels": 60,
    "6 wheels": 80,
    "10 wheels": 100,
    "12 wheels": 120,
    "14 wheels": 150,
    "16 wheels": 180,
    "18 wheels": 210,
    "20+ wheels": 250,
}

def is_valid_indian_plate(text):
    text = text.upper()
    patterns = [
        r'^[A-Z]{2}\d{2}[A-Z]{1,3}\d{4}$',   # TN12AL8933
        r'^[A-Z]{2}\d{2}[A-Z]{0,2}\d{4}$',   # TN12AB1234, TN12A1234
        r'^[A-Z]{3}\d{4}$',                  # MSX4055, ABC1234
        r'^[A-Z]{2}\d{4}$',                  # TN1234 (old)
    ]
    return any(re.fullmatch(pattern, text) for pattern in patterns)

class SummaryWindow(QWidget):
    _active_summary = None

    def __init__(self, vehicle_number, weight, amount, load_status, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Summary")
        self.setFixedSize(800, 600)
        self.setWindowModality(Qt.ApplicationModal)
        self.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.CustomizeWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setStyleSheet("""
            QWidget {
                background-color: black;
                color: white;
                font-family: Arial;
            }
            QLabel {
                color: white;
            }
            QPushButton {
                background-color: #222;
                color: white;
                border: 2px solid #fff;
                border-radius: 8px;
            }
            QPushButton#cancelBtn {
                background-color: #932222;
                color: #fff;
                border: 2px solid #fff;
            }
        """)
        atm_font = QFont("Arial", 32, QFont.Bold)
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(32)
        self.info_label = QLabel(
            f"Vehicle: {vehicle_number}\nWeight: {weight}\nAmount: {amount}\nLoad Status: {load_status}"
        )
        self.info_label.setFont(atm_font)
        self.info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.info_label, alignment=Qt.AlignCenter)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(24)

        weigh_print_btn = QPushButton("Weigh&Print")
        weigh_print_btn.setFont(QFont("Arial", 20, QFont.Bold))
        weigh_print_btn.setFixedSize(220, 60)
        weigh_print_btn.clicked.connect(self.accept_and_close)
        btn_row.addWidget(weigh_print_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("cancelBtn")
        cancel_btn.setFont(QFont("Arial", 24, QFont.Bold))
        cancel_btn.setFixedSize(180, 60)
        cancel_btn.clicked.connect(self.close)
        btn_row.addWidget(cancel_btn)

        layout.addLayout(btn_row)
        self.setLayout(layout)
        self.centerOnScreen()
        self.show()
        if SummaryWindow._active_summary is not None and SummaryWindow._active_summary is not self:
            try:
                SummaryWindow._active_summary.close()
            except Exception:
                pass
        SummaryWindow._active_summary = self

        # Dummy widget attributes for printing (replace or set externally as needed)
        self.ticket_number = QLineEdit("123456")
        self.date_field = QLineEdit("12/06/2025")
        self.time_field = QLineEdit("16:08:50")
        self.vehicle_input = QLineEdit(vehicle_number)
        self.eamount_input = QLineEdit(amount)
        self.lamount_input = QLineEdit("")
        self.load_status_display = QLabel(load_status)
        self.weight_display = QLabel(weight)
        self.empty_weight_field = QLineEdit("2000")

    def centerOnScreen(self):
        qr = self.frameGeometry()
        cp = QApplication.primaryScreen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def accept_and_close(self):
        self.print_bill_direct()
        self.close()

    def print_bill_direct(self):
        printer = QPrinter(QPrinter.HighResolution)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName("test_output.pdf")
        painter = QPainter()
        if not painter.begin(printer):
            print("Failed to open printer")
            return

        font = QFont("Courier New", 12)
        painter.setFont(font)

        x_left = 80
        x_right = 450
        y_start = 120
        line_gap = 28

        def print_stub(x, ticket_no, date, time, vehicle, rs, materials, gross, tare, net, container, footer):
            y = y_start
            painter.drawText(x, y, f"No.: {ticket_no}")
            y += line_gap
            painter.drawText(x, y, f"Date: {date}")
            y += line_gap
            painter.drawText(x, y, f"Time: {time}")
            y += line_gap
            painter.drawText(x, y, f"Vehicle No.: {vehicle}")
            y += line_gap
            painter.drawText(x, y, f"Rs.: {rs}")
            y += line_gap
            painter.drawText(x, y, f"Materials: {materials}")
            y += line_gap
            painter.drawText(x, y, f"Gross Wt.: {gross}")
            y += line_gap
            painter.drawText(x, y, f"Tare Wt.: {tare}")
            y += line_gap
            painter.drawText(x, y, f"Net Wt.: {net}")
            y += line_gap
            painter.drawText(x, y, f"Container No.: {container}")
            y += line_gap * 2
            painter.drawText(x, y, footer)

        ticket_no = self.ticket_number.text()
        date = self.date_field.text()
        time = self.time_field.text()
        vehicle = self.vehicle_input.text()
        rs = self.eamount_input.text() or self.lamount_input.text()
        materials = self.load_status_display.text()
        gross = self.weight_display.text()
        tare = self.empty_weight_field.text()
        try:
            net = str(float(gross) - float(tare)) if gross and tare else "0"
        except Exception:
            net = "0"
        container = "-"
        footer = "EMPTY" if materials.strip().upper() == "LOAD" else materials

        print_stub(x_left, ticket_no, date, time, vehicle, rs, materials, gross, tare, net, container, footer)
        print_stub(x_right, ticket_no, date, time, vehicle, rs, materials, gross, tare, net, container, footer)

        painter.end()



class FirstLoadWindow(QWidget):
    def __init__(self, mode_window=None):
        super().__init__()
        self.setWindowTitle("Vehicle First Transaction")
        self.setFixedSize(1280, 768)
        self.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.WindowMinimizeButtonHint | Qt.WindowCloseButtonHint)
        self.setStyleSheet("background: #fff;")
        self.mode_window = mode_window

        # Font sizes
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

        # Row 3: Time, Vehicle, OK
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

        # Row 3.1: Empty and Load Weight fields
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

        # Row 4: Wheels
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
        button_size = 58  # Square size for width and height
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
            self.wheel_btns.append(btn)
        self.wheel_btn_group.buttonClicked.connect(self.wheel_selection_changed)

        wheels_row.addLayout(wheels_grid)
        wheels_row.addStretch()
        main_layout.addLayout(wheels_row)

        # Row 5: Load Status
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

        main_layout.addSpacing(8)

        # Keypad Layout
        main_keypad_grid = QGridLayout()
        main_keypad_grid.setHorizontalSpacing(12)
        main_keypad_grid.setVerticalSpacing(4)

        letter_btn_size = 48
        digit_btn_size = 56
        backclear_btn_width = digit_btn_size * 2 + 4
        letter_font = QFont("Arial", 20, QFont.Bold)
        digit_font = QFont("Arial", 22, QFont.Bold)

        # Letters A-Z, 4 rows x 7 columns
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

        self.vehicle_input.textChanged.connect(self.check_vehicle_entry)
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
        self.date_field.setText(now.toString("dd/MM/yyyy"))
        self.time_field.setText(current_time.toString("HH:mm:ss"))

    def generate_ticket_number(self):
        return str(random.randint(10000, 99999))

    def get_fake_weight(self):
        return str(random.randint(10000, 99999))

    def check_vehicle_entry(self):
        plate = self.vehicle_input.text().upper()
        if is_valid_indian_plate(plate):
            self.vehicle_input.setStyleSheet("background: #fff7d6; border: 2px solid green; color: #003366; padding: 4px; border-radius: 8px;")
            self.ok_btn.setEnabled(True)
        else:
            self.vehicle_input.setStyleSheet("background: #fff7d6; border: 2px solid #ff6600; color: #003366; padding: 4px; border-radius: 8px;")
            self.ok_btn.setEnabled(False)

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
        vehicle_number = self.vehicle_input.text().upper()
        weight = self.weight_display.text()
        amount = self.eamount_input.text() if self.eamount_input.text() else self.lamount_input.text()
        load_status = self.load_status_display.text()
        self.summary = SummaryWindow(vehicle_number, weight, amount, load_status, parent=self)

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
            net_weight = int(load_weight) - int(empty_weight)
        except (TypeError, ValueError):
            net_weight = None

        # Fill these with real values or None as needed
        materialname, suppliername, shift, state = None, None, None, None

        insert_query = """
            INSERT INTO tickets (
                vehiclenumber, date, time, emptyweight, loadedweight, netweight,
                materialname, suppliername, shift, state
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            vehicle_number, date, time, empty_weight, load_weight, net_weight,
            materialname, suppliername, shift, state
        )

        try:
            execute_query(insert_query, params)
            QMessageBox.information(self, "Saved", "Ticket saved to database.")
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
if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = FirstLoadWindow()
    win.vehicle_input.setText("TN12AL8838")
    win.wheel_btns[0].setChecked(True)
    win.set_load()
    win.check_vehicle_entry()
    win.show()
    sys.exit(app.exec_())
