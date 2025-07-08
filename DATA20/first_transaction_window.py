from base_transaction_window import BaseTransactionWindow
from db_utils import execute_query, fetch_one, fetch_all
from PyQt5.QtWidgets import (
    QPushButton, QComboBox, QDateTimeEdit, QLabel, QMessageBox, QDialog,
    QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QLineEdit
)
from PyQt5.QtCore import QDateTime
import random
from print_ticket_with_template_win32 import print_ticket_with_template

def blank_to_none(val):
    return None if val in ("", None) else int(val)

class PrintPromptDialog(QDialog):
    def __init__(self, ticket_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Print Ticket")
        self.setFixedSize(400, 200)
        layout = QVBoxLayout(self)
        msg = QLabel("Would you like to print the ticket?")
        layout.addWidget(msg)
        btn_row = QHBoxLayout()
        self.yes_btn = QPushButton("Yes")
        self.no_btn = QPushButton("No")
        btn_row.addWidget(self.yes_btn)
        btn_row.addWidget(self.no_btn)
        layout.addLayout(btn_row)
        self.yes_btn.clicked.connect(self.accept)
        self.no_btn.clicked.connect(self.reject)
        self.ticket_data = ticket_data

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

        # Add or connect to existing Search button
        if not hasattr(self, "btn_search"):
            self.btn_search = QPushButton("Search")
            self.mand_grid.addWidget(self.btn_search, 12, 1)
        self.btn_search.clicked.connect(self.search_action)

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
            dlg = QDialog(self)
            dlg.setWindowTitle("Summary")
            layout = QVBoxLayout(dlg)
            for k, v in summary_data.items():
                h = QHBoxLayout()
                h.addWidget(QLabel(f"{k}:"))
                field = QLineEdit(str(v))
                field.setReadOnly(True)
                h.addWidget(field)
                layout.addLayout(h)
            dlg.setLayout(layout)
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
            "State": "first transaction",  # Set state here!
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
        # Prepare ticket_data for printing
        ticket_data = {
            "TicketNumber": ticket_number,
            "VehicleNumber": self.vehicle_number.text(),
            "Date": self.date,
            "Time": self.time,
            "EmptyWeight": self.empty_weight.text(),
            "LoadedWeight": self.loaded_weight.text(),
            "NetWeight": self.net_weight.text(),
            "Materialname": self.material.text(),
            "SupplierName": self.supplier.text(),
            "State": "first transaction",
            "AMOUNT": "",
            "STATUS": self.status.text(),
            "EAMOUNT": "",
            "LAMOUNT": "",
            "TAMOUNT": "",
            "NetWeight1": "",
            "LWEIGHT": "",
            "EWEIGHT": ""
        }
        self.show_success_message(ticket_number, ticket_data)

    def show_success_message(self, ticket_number, ticket_data):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("Success")
        msg.setText(f"Ticket number {ticket_number} successfully saved")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.buttonClicked.connect(lambda _: self.ask_print_prompt(ticket_data))
        msg.exec_()

    def ask_print_prompt(self, ticket_data):
        dlg = PrintPromptDialog(ticket_data, parent=self)
        result = dlg.exec_()
        if result == QDialog.Accepted:
            print_ticket_with_template(ticket_data)
            self.return_to_transaction_menu()
        else:
            self.return_to_transaction_menu()

    # ... (rest of your imports and class code remain unchanged)

    # ... (other imports and class code remain unchanged)

    def search_action(self):
        """
        Show only the first weighment (either empty or load) for each vehicle.
        Only the earliest weighment for each VehicleNumber is shown.
        """
        tickets = fetch_all(
            '''
            SELECT "TicketNumber", "VehicleNumber", "Date", "Time", "EmptyWeight", "LoadedWeight"
            FROM tickets t1
            WHERE t1."TicketNumber" = (
                SELECT MIN(t2."TicketNumber")
                FROM tickets t2
                WHERE t2."VehicleNumber" = t1."VehicleNumber"
                  AND (t2."EmptyWeight" IS NOT NULL OR t2."LoadedWeight" IS NOT NULL)
            )
            AND (t1."EmptyWeight" IS NOT NULL OR t1."LoadedWeight" IS NOT NULL)
            ORDER BY t1."VehicleNumber";
            ''',
            ()
        )
        dlg = QDialog(self)
        dlg.setWindowTitle("First Weighment Per Vehicle")
        layout = QVBoxLayout(dlg)
        headers = ["TicketNumber", "VehicleNumber", "Date", "Time", "EmptyWeight", "LoadedWeight"]
        table = QTableWidget(len(tickets), len(headers))
        table.setHorizontalHeaderLabels(headers)
        for i, t in enumerate(tickets):
            for j, key in enumerate(headers):
                table.setItem(i, j, QTableWidgetItem(str(t.get(key, ""))))
        def on_cell_clicked(row, col):
            self.display_ticket_fields(tickets[row], dlg)
        table.cellClicked.connect(on_cell_clicked)
        layout.addWidget(table)
        dlg.setLayout(layout)
        dlg.exec_()

    def display_ticket_fields(self, ticket, parent_dialog):
        field_dlg = QDialog(parent_dialog)
        field_dlg.setWindowTitle(f"Ticket {ticket['TicketNumber']} Details")
        layout = QVBoxLayout(field_dlg)
        # Always show TicketNumber, VehicleNumber, Date, Time
        fields_to_show = ["TicketNumber", "VehicleNumber", "Date", "Time"]
        for k in fields_to_show:
            row = QHBoxLayout()
            row.addWidget(QLabel(f"{k}:"))
            field = QLineEdit(str(ticket.get(k, "")))
            field.setReadOnly(True)
            row.addWidget(field)
            layout.addLayout(row)
        # Show only one of EmptyWeight or LoadedWeight (first non-NULL)
        if ticket.get("EmptyWeight") not in (None, "", "None"):
            row = QHBoxLayout()
            row.addWidget(QLabel("EmptyWeight:"))
            field = QLineEdit(str(ticket.get("EmptyWeight")))
            field.setReadOnly(True)
            row.addWidget(field)
            layout.addLayout(row)
        elif ticket.get("LoadedWeight") not in (None, "", "None"):
            row = QHBoxLayout()
            row.addWidget(QLabel("LoadedWeight:"))
            field = QLineEdit(str(ticket.get("LoadedWeight")))
            field.setReadOnly(True)
            row.addWidget(field)
            layout.addLayout(row)
        # (Add more fields if desired)
        btn_print = QPushButton("Print")
        btn_print.clicked.connect(lambda: self.print_selected_ticket(ticket))
        layout.addWidget(btn_print)
        field_dlg.setLayout(layout)
        field_dlg.exec_()
    def print_selected_ticket(self, ticket):
        print_ticket_with_template(ticket)

    def return_to_transaction_menu(self):
        self.close()
        if self.transaction_window:
            self.transaction_window.show()
        else:
            from base_transaction_window import BaseTransactionWindow
            self.parent_menu = BaseTransactionWindow()
            self.parent_menu.show()
