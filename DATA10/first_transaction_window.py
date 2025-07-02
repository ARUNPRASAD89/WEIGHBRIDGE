from base_transaction_window import BaseTransactionWindow
from db_utils import execute_query, fetch_one
from PyQt5.QtCore import QDateTime, QTimer
from PyQt5.QtWidgets import QMessageBox, QComboBox, QDialog, QVBoxLayout, QLabel, QHBoxLayout, QPushButton
import random

def blank_to_none(val):
    return None if val in ("", None) else int(val)    

class FirstTransactionWindow(BaseTransactionWindow):
    def __init__(self, transaction_window=None):
        super().__init__()
        self.lbl_title.setText("Vehicle First Transaction")
        self.btn_save.setEnabled(True)
        self.ticket_number.setReadOnly(True)
        self.loaded_weight.setReadOnly(True)
        self.empty_weight.setReadOnly(True)
        self.net_weight.setReadOnly(True)
        self.transaction_window = transaction_window

        if hasattr(self, "btn_close_tran"):
            self.btn_close_tran.setVisible(False)

        self.ticket_number.setText(self.generate_ticket_number())
        now = QDateTime.currentDateTime()
        self.date = now.date().toString("yyyy-MM-dd")
        self.time = now.time().toString("HH:mm:ss")

        self.weight_display.setText(str(random.randint(5000, 50000)))

        if not hasattr(self, "load_status"):
            self.load_status = QComboBox()
            self.load_status.addItems(["LOAD", "EMPTY"])
            self.mand_grid.addWidget(self.load_status, 2, 1)
        else:
            self.load_status.clear()
            self.load_status.addItems(["LOAD", "EMPTY"])
        self.load_status.setCurrentText("LOAD")

        self.btn_weigh.clicked.connect(self.handle_weigh)
        self.btn_save.clicked.connect(self.check_pending_and_save)

        self.vehicle_number.editingFinished.connect(self.check_pending_on_vehicle_entry)
        self._pending_checked = False

    def generate_ticket_number(self):
        row = fetch_one('SELECT COALESCE(MAX(CAST("TicketNumber" AS INTEGER)), 10000) + 1 AS next_ticket FROM tickets')
        return str(row["next_ticket"])

    def handle_weigh(self):
        value = int(self.weight_display.text())
        load_status = self.load_status.currentText().strip().upper()
        if load_status == "EMPTY":
            self.empty_weight.setText(str(value))
            self.loaded_weight.setText("")
            self.net_weight.setText(str(value))
        elif load_status == "LOAD":
            self.loaded_weight.setText(str(value))
            self.empty_weight.setText("")
            self.net_weight.setText(str(value))
        else:
            self.empty_weight.setText("")
            self.loaded_weight.setText("")
            self.net_weight.setText("")

    def check_pending_on_vehicle_entry(self):
        veh_number = self.vehicle_number.text().strip()
        if not veh_number:
            return
        # Check for pending=TRUE
        pending_row = fetch_one(
            'SELECT "TicketNumber" FROM tickets WHERE "VehicleNumber" = %s AND "Pending" = TRUE', (veh_number,)
        )
        if pending_row:
            msg = QMessageBox(self)
            msg.setWindowTitle("Pending Transaction")
            msg.setText("Pending transaction found for this vehicle. Do you want to continue to Second Transaction?")
            msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
            ret = msg.exec_()
            if ret == QMessageBox.Ok:
                from second_transaction_window import SecondTransactionWindow
                self.close()
                self.second_tran_win = SecondTransactionWindow(pending_ticket_number=pending_row["TicketNumber"])
                self.second_tran_win.show()
                return
            else:
                self.vehicle_number.setFocus()
                return
        # If pending is FALSE, show summary window with available data
        row = fetch_one(
            'SELECT * FROM tickets WHERE "VehicleNumber" = %s AND ("Pending" = FALSE OR "Closed" = TRUE) ORDER BY "TicketNumber" DESC', (veh_number,)
        )
        if row:
            summary_data = {
                "TicketNumber": row.get("TicketNumber", ""),
                "Date": row.get("Date", ""),
                "Time": row.get("Time", ""),
                "VehicleNumber": row.get("VehicleNumber", ""),
                "EmptyWeight": row.get("EmptyWeight", ""),
                "LoadedWeight": row.get("LoadedWeight", ""),
                "NetWeight": row.get("NetWeight", ""),
                "Materialname": row.get("Materialname", ""),
                "SupplierName": row.get("SupplierName", ""),
            }
            dlg = SummaryDialog(self, summary_data, self.transaction_window)
            dlg.exec_()

    def check_pending_and_save(self):
        veh_number = self.vehicle_number.text().strip()
        pending_row = fetch_one(
            'SELECT "TicketNumber" FROM tickets WHERE "VehicleNumber" = %s AND "Pending" = TRUE', (veh_number,)
        )
        if pending_row:
            msg = QMessageBox(self)
            msg.setWindowTitle("Pending Transaction")
            msg.setText("Pending transaction found for this vehicle. Do you want to continue to Second Transaction?")
            msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
            ret = msg.exec_()
            if ret == QMessageBox.Ok:
                from second_transaction_window import SecondTransactionWindow
                self.close()
                self.second_tran_win = SecondTransactionWindow(pending_ticket_number=pending_row["TicketNumber"])
                self.second_tran_win.show()
                return
            else:
                return
        self.save_ticket()

    def save_ticket(self):
        load_status = self.load_status.currentText().strip().upper()
        if load_status == "EMPTY":
            empty_weight = blank_to_none(self.empty_weight.text())
            loaded_weight = None
            net_weight = empty_weight
        else:  # LOAD
            loaded_weight = blank_to_none(self.loaded_weight.text())
            empty_weight = None
            net_weight = loaded_weight

        ticket_number = self.ticket_number.text()
        row = fetch_one('SELECT "Pending", "Closed" FROM tickets WHERE "TicketNumber" = %s', (ticket_number,))
        curr_pending = row["Pending"] if row else True
        curr_closed = row["Closed"] if row else False

        pending = True if curr_pending else False
        closed = False if not curr_closed else True

        params = {
            "TicketNumber": blank_to_none(ticket_number),
            "VehicleNumber": self.vehicle_number.text(),
            "Date": self.date,
            "Time": self.time,
            "EmptyWeight": empty_weight,
            "LoadedWeight": loaded_weight,
            "EmptyWeightDate": self.date,
            "EmptyWeightTime": self.time,
            "LoadWeightDate": self.date,
            "LoadWeightTime": self.time,
            "NetWeight": net_weight,
            "Pending": pending,
            "Closed": closed,
            "Exported": False,
            "Shift": "B",
            "Materialname": self.material.text(),
            "SupplierName": self.supplier.text(),
            "State": "",
            "Blank": None,
            "AMOUNT": None,
            "STATUS": self.status.text(),
            "EAMOUNT": None,
            "LAMOUNT": None,
            "TAMOUNT": None,
            "NetWeight1": None,
            "LWEIGHT": None,
            "EWEIGHT": None
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
        msg.exec_()
