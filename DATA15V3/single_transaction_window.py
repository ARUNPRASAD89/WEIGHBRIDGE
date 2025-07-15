from base_transaction_window import BaseTransactionWindow
from db_utils import execute_query, fetch_one, fetch_all
from PyQt5.QtWidgets import QPushButton, QComboBox, QDateTimeEdit, QLabel, QMessageBox, QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QLineEdit
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

class SingleTransactionWindow(BaseTransactionWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
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
        self.btn_search = QPushButton("Search")
        self.btn_search.clicked.connect(self.search_action)
        self.mand_grid.addWidget(self.btn_search, 12, 1)
        self.result_dialog = None
        self.btn_exit.clicked.connect(self.return_to_base_transaction_window)

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
            "State": "single transaction",  # Set state here!
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
        # Prepare ticket_data for printing
        ticket_data = {
            "TicketNumber": ticket_number,
            "VehicleNumber": self.vehicle_number.text(),
            "Date": date_part,
            "Time": time_part,
            "EmptyWeight": self.empty_weight.text(),
            "LoadedWeight": self.loaded_weight.text(),
            "NetWeight": self.net_weight.text(),
            "Materialname": self.material.text(),
            "SupplierName": self.supplier.text(),
            "State": "single transaction",  # so search works right after save
            "AMOUNT": self.amount.text() if hasattr(self, "amount") else "",
            "STATUS": self.status.text(),
            "EAMOUNT": self.eamount.text(),
            "LAMOUNT": self.lamount.text(),
            "TAMOUNT": self.tamount.text(),
            "NetWeight1": self.netweight1.text(),
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

    def search_action(self):
        tickets = fetch_all('SELECT * FROM tickets WHERE "State" = %s', ("single transaction",))
        dlg = QDialog(self)
        dlg.setWindowTitle("Single Transaction Search")
        layout = QVBoxLayout(dlg)
        table = QTableWidget(len(tickets), 2)
        table.setHorizontalHeaderLabels(["TicketNumber", "VehicleNumber"])
        for i, t in enumerate(tickets):
            table.setItem(i, 0, QTableWidgetItem(str(t["TicketNumber"])))
            table.setItem(i, 1, QTableWidgetItem(str(t["VehicleNumber"])))
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
        for k, v in ticket.items():
            row = QHBoxLayout()
            row.addWidget(QLabel(f"{k}:"))
            field = QLineEdit(str(v))
            field.setReadOnly(True)
            row.addWidget(field)
            layout.addLayout(row)
        btn_print = QPushButton("Print")
        btn_print.clicked.connect(lambda: self.print_selected_ticket(ticket))
        layout.addWidget(btn_print)
        field_dlg.setLayout(layout)
        field_dlg.exec_()

    def print_selected_ticket(self, ticket):
        print_ticket_with_template(ticket)        

    def return_to_base_transaction_window(self):
        parent = self.parent()
        if parent:
            parent.show()
        self.close()
