from base_transaction_window import BaseTransactionWindow
from db_utils import execute_query, fetch_one
from PyQt5.QtWidgets import QPushButton, QComboBox, QDateTimeEdit, QLabel, QMessageBox
from PyQt5.QtCore import QDateTime
import random

def blank_to_none(val):
    return None if val in ("", None) else int(val)

class SingleTransactionWindow(BaseTransactionWindow):
    def __init__(self):
        super().__init__()
        self.weight_display.setText(str(random.randint(5000, 50000)))
        self.lbl_title.setText("Vehicle Single Transaction")

        # Date and Time fields (show + set to current on load, read-only)
        self.date_edit = QDateTimeEdit(QDateTime.currentDateTime())
        self.date_edit.setDisplayFormat('yyyy-MM-dd')
        self.date_edit.setReadOnly(True)
        self.time_edit = QDateTimeEdit(QDateTime.currentDateTime())
        self.time_edit.setDisplayFormat('HH:mm:ss')
        self.time_edit.setReadOnly(True)

        self.mand_grid.addWidget(QLabel("Date"), 9, 0)
        self.mand_grid.addWidget(self.date_edit, 9, 1)
        self.mand_grid.addWidget(QLabel("Time"), 10, 0)
        self.mand_grid.addWidget(self.time_edit, 10, 1)

        # Load Status dropdown
        self.load_status.clear()
        self.load_status.addItems(["LOAD", "EMPTY"])
        self.load_status.setCurrentText("LOAD")

        self.btn_weigh.clicked.connect(self.record_loaded_weight)

        self.btn_get_tare = QPushButton("Get Tare Weight")
        self.mand_grid.addWidget(self.btn_get_tare, 11, 1)
        self.btn_get_tare.clicked.connect(self.get_tare_weight)

        self.btn_save.clicked.connect(self.save_ticket)

        self.ticket_number.setText(self.generate_ticket_number())
        self.ticket_number.setReadOnly(True)
        self.loaded_weight.setReadOnly(True)
        self.empty_weight.setReadOnly(True)
        self.net_weight.setReadOnly(True)

    def generate_ticket_number(self):
        row = fetch_one('SELECT COALESCE(MAX(CAST("TicketNumber" AS INTEGER)), 10000) + 1 AS next_ticket FROM tickets')
        return str(row["next_ticket"])

    def record_loaded_weight(self):
        try:
            value = int(self.weight_display.text())
        except Exception:
            value = 0
        self.loaded_weight.setText(str(value))
        self.calculate_net_weight()

    def get_tare_weight(self):
        vehiclenumber = self.vehicle_number.text().strip()
        if not vehiclenumber:
            self.empty_weight.setText("")
            return
        row = fetch_one(
            'SELECT "vehicletareweight" FROM vehiclemaster WHERE "vehiclenumber" = %s',
            (vehiclenumber,)
        )
        if row and row["vehicletareweight"] is not None:
            self.empty_weight.setText(str(row["vehicletareweight"]))
        else:
            self.empty_weight.setText("")
        self.calculate_net_weight()

    def calculate_net_weight(self):
        try:
            loaded = int(self.loaded_weight.text())
            empty = int(self.empty_weight.text())
            net = loaded - empty
            self.net_weight.setText(str(net))
        except Exception:
            self.net_weight.setText("")

    def save_ticket(self):
        date_part = self.date_edit.date().toString("yyyy-MM-dd")
        time_part = self.time_edit.time().toString("HH:mm:ss")

        ticket_number = self.ticket_number.text()
        row = fetch_one('SELECT "Pending", "Closed" FROM tickets WHERE "TicketNumber" = %s', (ticket_number,))
        curr_pending = row["Pending"] if row else True
        curr_closed = row["Closed"] if row else False

        pending = not (self.loaded_weight.text() and self.empty_weight.text())
        pending = False if not curr_pending or not pending else True
        closed = True if curr_closed or not pending else False

        params = {
            "TicketNumber": blank_to_none(ticket_number),
            "VehicleNumber": self.vehicle_number.text(),
            "Date": date_part,
            "Time": time_part,
            "EmptyWeight": blank_to_none(self.empty_weight.text()),
            "LoadedWeight": blank_to_none(self.loaded_weight.text()),
            "EmptyWeightDate": date_part,
            "EmptyWeightTime": time_part,
            "LoadWeightDate": date_part,
            "LoadWeightTime": time_part,
            "NetWeight": blank_to_none(self.net_weight.text()),
            "Pending": pending,
            "Closed": closed,
            "Exported": False,
            "Shift": "B",
            "Materialname": self.material.text(),
            "SupplierName": self.supplier.text(),
            "State": "",
            "Blank": None,
            "AMOUNT": blank_to_none(self.amount.text() if hasattr(self, "amount") else None),
            "STATUS": self.status.text(),
            "EAMOUNT": blank_to_none(self.eamount.text()),
            "LAMOUNT": blank_to_none(self.lamount.text()),
            "TAMOUNT": blank_to_none(self.tamount.text()),
            "NetWeight1": blank_to_none(self.netweight1.text()),
            "LWEIGHT": None,
            "EWEIGHT": None,
        }
        query = """
        INSERT INTO tickets (
            "TicketNumber", "VehicleNumber", "Date", "Time", "EmptyWeight", "LoadedWeight",
            "EmptyWeightDate", "EmptyWeightTime", "LoadWeightDate", "LoadWeightTime",
            "NetWeight", "Pending", "Closed", "Exported", "Shift", "Materialname", "SupplierName",
            "State", "Blank", "AMOUNT", "STATUS", "EAMOUNT", "LAMOUNT", "TAMOUNT", "NetWeight1",
            "LWEIGHT", "EWEIGHT"
        ) VALUES (
            %(TicketNumber)s, %(VehicleNumber)s, %(Date)s, %(Time)s, %(EmptyWeight)s, %(LoadedWeight)s,
            %(EmptyWeightDate)s, %(EmptyWeightTime)s, %(LoadWeightDate)s, %(LoadWeightTime)s,
            %(NetWeight)s, %(Pending)s, %(Closed)s, %(Exported)s, %(Shift)s, %(Materialname)s, %(SupplierName)s,
            %(State)s, %(Blank)s, %(AMOUNT)s, %(STATUS)s, %(EAMOUNT)s, %(LAMOUNT)s, %(TAMOUNT)s, %(NetWeight1)s,
            %(LWEIGHT)s, %(EWEIGHT)s
        )
        ON CONFLICT ("TicketNumber") DO UPDATE SET
            "VehicleNumber" = EXCLUDED."VehicleNumber",
            "Date" = EXCLUDED."Date",
            "Time" = EXCLUDED."Time",
            "EmptyWeight" = EXCLUDED."EmptyWeight",
            "LoadedWeight" = EXCLUDED."LoadedWeight",
            "EmptyWeightDate" = EXCLUDED."EmptyWeightDate",
            "EmptyWeightTime" = EXCLUDED."EmptyWeightTime",
            "LoadWeightDate" = EXCLUDED."LoadWeightDate",
            "LoadWeightTime" = EXCLUDED."LoadWeightTime",
            "NetWeight" = EXCLUDED."NetWeight",
            "Pending" = EXCLUDED."Pending",
            "Closed" = EXCLUDED."Closed",
            "Exported" = EXCLUDED."Exported",
            "Shift" = EXCLUDED."Shift",
            "Materialname" = EXCLUDED."Materialname",
            "SupplierName" = EXCLUDED."SupplierName",
            "State" = EXCLUDED."State",
            "Blank" = EXCLUDED."Blank",
            "AMOUNT" = EXCLUDED."AMOUNT",
            "STATUS" = EXCLUDED."STATUS",
            "EAMOUNT" = EXCLUDED."EAMOUNT",
            "LAMOUNT" = EXCLUDED."LAMOUNT",
            "TAMOUNT" = EXCLUDED."TAMOUNT",
            "NetWeight1" = EXCLUDED."NetWeight1",
            "LWEIGHT" = EXCLUDED."LWEIGHT",
            "EWEIGHT" = EXCLUDED."EWEIGHT"
        """
        execute_query(query, params)
        self.show_success_message(self.ticket_number.text())

    def show_success_message(self, ticket_number):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("Success")
        msg.setText(f"Ticket number {ticket_number} successfully saved")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.buttonClicked.connect(self.return_to_transaction_menu)
        msg.exec_()

    def return_to_transaction_menu(self):
        self.close()
        self.parent_menu = BaseTransactionWindow()
        self.parent_menu.show()
