from base_transaction_window import BaseTransactionWindow
from db_utils import execute_query, fetch_all, fetch_one
from PyQt5.QtWidgets import QComboBox, QPushButton, QMessageBox, QLabel, QHBoxLayout, QWidget, QLineEdit
from PyQt5.QtCore import QDateTime
import random

def blank_to_none(val):
    return None if val in ("", None) else int(val)

class SecondTransactionWindow(BaseTransactionWindow):
    def __init__(self, pending_ticket_number=None):
        super().__init__()
        self.lbl_title.setText("Vehicle Second Transaction")
        self.btn_save.setEnabled(True)
        self.loaded_weight.setReadOnly(True)
        self.empty_weight.setReadOnly(True)
        self.net_weight.setReadOnly(True)

        if not isinstance(self.supplier, QLineEdit):
            supplier_row, supplier_col = self.mand_grid.getItemPosition(self.mand_grid.indexOf(self.supplier))[:2]
            self.mand_grid.removeWidget(self.supplier)
            self.supplier.deleteLater()
            self.supplier = QLineEdit()
            self.mand_grid.addWidget(self.supplier, supplier_row, supplier_col)

        self.ticket_number_combo = QComboBox()
        self.mand_grid.addWidget(self.ticket_number_combo, 1, 1)
        self.mand_grid.removeWidget(self.ticket_number)
        self.ticket_number.hide()
        self.ticket_number_combo.currentIndexChanged.connect(self.load_ticket_data)

        self.mand_grid.addWidget(QLabel("Select Weight Type"), 3, 0)
        btn_widget = QWidget()
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        self.btn_load = QPushButton("Load")
        self.btn_empty = QPushButton("Empty")
        btn_layout.addWidget(self.btn_load)
        btn_layout.addWidget(self.btn_empty)
        btn_widget.setLayout(btn_layout)
        self.mand_grid.addWidget(btn_widget, 3, 1)
        self.btn_load.setEnabled(True)
        self.btn_empty.setEnabled(True)

        self.btn_close_tran = QPushButton("Close Transaction")
        self.mand_grid.addWidget(self.btn_close_tran, 9, 1)
        self.btn_close_tran.clicked.connect(self.close_transaction)

        self.now = QDateTime.currentDateTime()
        self.date_str = self.now.date().toString("yyyy-MM-dd")
        self.time_str = self.now.time().toString("HH:mm:ss")

        self.btn_save.clicked.connect(self.save_ticket)

        self.load_pending_tickets()

        self.btn_weigh.clicked.connect(self.handle_weigh_second)

        self.active_weight_type = None
        self.btn_load.clicked.connect(lambda: self.set_active_weight_type("LOAD"))
        self.btn_empty.clicked.connect(lambda: self.set_active_weight_type("EMPTY"))

        if pending_ticket_number:
            for i in range(self.ticket_number_combo.count()):
                if self.ticket_number_combo.itemText(i) == str(pending_ticket_number):
                    self.ticket_number_combo.setCurrentIndex(i)
                    break
            self.load_ticket_data()

    def set_active_weight_type(self, weight_type):
        self.active_weight_type = weight_type
        if weight_type == "LOAD":
            self.btn_load.setStyleSheet("font-weight: bold; background-color: #c4df9b")
            self.btn_empty.setStyleSheet("")
        else:
            self.btn_empty.setStyleSheet("font-weight: bold; background-color: #c4df9b")
            self.btn_load.setStyleSheet("")

    def load_pending_tickets(self):
        rows = fetch_all('SELECT "TicketNumber" FROM tickets WHERE "Pending" = TRUE')
        self.ticket_number_combo.clear()
        for row in rows:
            self.ticket_number_combo.addItem(str(row["TicketNumber"]))

    def load_ticket_data(self):
        ticket_number = self.ticket_number_combo.currentText()
        if not ticket_number:
            return
        row = fetch_one('SELECT * FROM tickets WHERE "TicketNumber" = %s', (ticket_number,))
        if not row:
            return
        self.vehicle_number.setText(row["VehicleNumber"] or "")
        self.material.setText(row["Materialname"] or "")
        self.supplier.setText(row["SupplierName"] or "")
        self.status.setText(row["STATUS"] or "")
        self.eamount.setText(str(row["EAMOUNT"] or ""))
        self.lamount.setText(str(row["LAMOUNT"] or ""))
        self.tamount.setText(str(row["TAMOUNT"] or ""))
        self.netweight1.setText(str(row["NetWeight1"] or ""))
        self.empty_weight.setText(str(row["EmptyWeight"] or ""))
        self.loaded_weight.setText(str(row["LoadedWeight"] or ""))
        self.net_weight.setText(str(row["NetWeight"] or ""))

        if row["LoadedWeight"] and row["EmptyWeight"]:
            self.btn_load.setEnabled(False)
            self.btn_empty.setEnabled(False)
        elif row["LoadedWeight"]:
            self.btn_load.setEnabled(False)
            self.btn_empty.setEnabled(True)
            self.set_active_weight_type("EMPTY")
        elif row["EmptyWeight"]:
            self.btn_load.setEnabled(True)
            self.btn_empty.setEnabled(False)
            self.set_active_weight_type("LOAD")
        else:
            self.btn_load.setEnabled(True)
            self.btn_empty.setEnabled(True)
            self.set_active_weight_type("LOAD")

    def handle_weigh_second(self):
        value = random.randint(5000, 50000)
        self.weight_display.setText(str(value))
        if self.btn_load.isEnabled() and not self.btn_empty.isEnabled():
            self.loaded_weight.setText(str(value))
            empty = self.empty_weight.text()
            try:
                net = value - int(empty) if empty else value
            except Exception:
                net = value
            self.net_weight.setText(str(net))
        elif self.btn_empty.isEnabled() and not self.btn_load.isEnabled():
            self.empty_weight.setText(str(value))
            loaded = self.loaded_weight.text()
            try:
                net = int(loaded) - value if loaded else -value
            except Exception:
                net = -value
            self.net_weight.setText(str(net))
        elif self.active_weight_type == "LOAD":
            self.loaded_weight.setText(str(value))
            empty = self.empty_weight.text()
            try:
                net = value - int(empty) if empty else value
            except Exception:
                net = value
            self.net_weight.setText(str(net))
        elif self.active_weight_type == "EMPTY":
            self.empty_weight.setText(str(value))
            loaded = self.loaded_weight.text()
            try:
                net = int(loaded) - value if loaded else -value
            except Exception:
                net = -value
            self.net_weight.setText(str(net))
        else:
            self.empty_weight.setText("")
            self.loaded_weight.setText("")
            self.net_weight.setText("")

    def save_ticket(self):
        ticket_number = self.ticket_number_combo.currentText()
        empty_weight_val = self.empty_weight.text()
        loaded_weight_val = self.loaded_weight.text()
        both_recorded = bool(empty_weight_val) and bool(loaded_weight_val)

        row = fetch_one('SELECT "Pending", "Closed" FROM tickets WHERE "TicketNumber" = %s', (ticket_number,))
        db_pending = row["Pending"] if row else True
        db_closed = row["Closed"] if row else False

        pending = False if (not db_pending) or both_recorded else True
        closed = True if db_closed or both_recorded else False

        params = {
            "TicketNumber": blank_to_none(ticket_number),
            "VehicleNumber": self.vehicle_number.text(),
            "Date": self.date_str,
            "Time": self.time_str,
            "EmptyWeight": blank_to_none(empty_weight_val),
            "LoadedWeight": blank_to_none(loaded_weight_val),
            "EmptyWeightDate": self.date_str,
            "EmptyWeightTime": self.time_str,
            "LoadWeightDate": self.date_str,
            "LoadWeightTime": self.time_str,
            "NetWeight": blank_to_none(self.net_weight.text()),
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
            "EAMOUNT": blank_to_none(self.eamount.text()),
            "LAMOUNT": blank_to_none(self.lamount.text()),
            "TAMOUNT": blank_to_none(self.tamount.text()),
            "NetWeight1": blank_to_none(self.netweight1.text()),
            "LWEIGHT": None,
            "EWEIGHT": None,
        }
        query = """
        UPDATE tickets SET
            "VehicleNumber" = %(VehicleNumber)s,
            "Date" = %(Date)s,
            "Time" = %(Time)s,
            "EmptyWeight" = %(EmptyWeight)s,
            "LoadedWeight" = %(LoadedWeight)s,
            "EmptyWeightDate" = %(EmptyWeightDate)s,
            "EmptyWeightTime" = %(EmptyWeightTime)s,
            "LoadWeightDate" = %(LoadWeightDate)s,
            "LoadWeightTime" = %(LoadWeightTime)s,
            "NetWeight" = %(NetWeight)s,
            "Pending" = %(Pending)s,
            "Closed" = %(Closed)s,
            "Exported" = %(Exported)s,
            "Shift" = %(Shift)s,
            "Materialname" = %(Materialname)s,
            "SupplierName" = %(SupplierName)s,
            "State" = %(State)s,
            "Blank" = %(Blank)s,
            "AMOUNT" = %(AMOUNT)s,
            "STATUS" = %(STATUS)s,
            "EAMOUNT" = %(EAMOUNT)s,
            "LAMOUNT" = %(LAMOUNT)s,
            "TAMOUNT" = %(TAMOUNT)s,
            "NetWeight1" = %(NetWeight1)s,
            "LWEIGHT" = %(LWEIGHT)s,
            "EWEIGHT" = %(EWEIGHT)s
        WHERE "TicketNumber" = %(TicketNumber)s
        """
        # ... your save logic ...
        execute_query(query, params)
        self.show_success_message(self.ticket_number.text())

    def close_transaction(self):
        ticket_number = self.ticket_number_combo.currentText()
        row = fetch_one('SELECT "Closed" FROM tickets WHERE "TicketNumber" = %s', (ticket_number,))
        db_closed = row["Closed"] if row else False
        execute_query(
            'UPDATE tickets SET "Pending" = FALSE, "Closed" = %s WHERE "TicketNumber" = %s',
            (db_closed, ticket_number)
        )
        self.save_ticket()

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
        from base_transaction_window import BaseTransactionWindow
        self.parent_menu = BaseTransactionWindow()
        self.parent_menu.show()
