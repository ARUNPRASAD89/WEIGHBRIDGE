from base_transaction_window import BaseTransactionWindow
from db_utils import execute_query, fetch_one, fetch_all
from PyQt5.QtWidgets import (
    QPushButton, QComboBox, QLabel, QMessageBox, QDialog, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QLineEdit, QWidget
)
from PyQt5.QtCore import QDateTime, QDate, QTime, QLocale
from PyQt5.QtGui import QFont
import random
from print_ticket_with_template_win32 import print_ticket_with_template
from date_time_utils import to_display_date, to_display_time

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

class SecondTransactionWindow(BaseTransactionWindow):
    def __init__(self, parent=None, pending_ticket_number=None):
        super().__init__(parent)
        self.lbl_title.setText("Vehicle Second Transaction")
        self.btn_save.setEnabled(True)
        if self.loaded_weight:
            self.loaded_weight.setReadOnly(True)
        if self.empty_weight:
            self.empty_weight.setReadOnly(True)
        if self.net_weight:
            self.net_weight.setReadOnly(True)

        # Ensure single connections for Exit, Save, Weigh
        try:
            self.btn_exit.clicked.disconnect()
        except Exception:
            pass
        self.btn_exit.clicked.connect(self.return_to_base_transaction_window)

        try:
            self.btn_save.clicked.disconnect()
        except Exception:
            pass
        self.btn_save.clicked.connect(self.save_ticket)

        try:
            self.btn_weigh.clicked.disconnect()
        except Exception:
            pass
        self.btn_weigh.clicked.connect(self.handle_weigh_second)

        # Storage for true weigh event times
        self._empty_weight_date = ""
        self._empty_weight_time = ""
        self._load_weight_date = ""
        self._load_weight_time = ""

        # Print flow guards
        self._print_prompt_open = False
        self._printing_in_progress = False
        self._suppress_print_prompt = False  # NEW: suppress printing after Close Transaction

        # Add Search button if not already present
        if not hasattr(self, "btn_search"):
            self.btn_search = QPushButton("Search")
            self.mand_grid.addWidget(self.btn_search, 12, 1)
        try:
            self.btn_search.clicked.disconnect()
        except Exception:
            pass
        self.btn_search.clicked.connect(self.search_action)

        # Combo for selecting pending ticket numbers
        self.ticket_number_combo = QComboBox()
        self.mand_grid.addWidget(self.ticket_number_combo, 1, 1)
        if self.ticket_number:
            self.mand_grid.removeWidget(self.ticket_number)
            self.ticket_number.hide()
        self.ticket_number_combo.currentIndexChanged.connect(self.load_ticket_data)

        # --- Add back "Select Weight Type" and related buttons & logic ---
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

        # Add Loaded Weight, Empty Weight, Net Weight fields - each on their own row
        self.mand_grid.addWidget(QLabel("Loaded Weight"), 4, 0)
        self.mand_grid.addWidget(self.loaded_weight, 4, 1)

        self.mand_grid.addWidget(QLabel("Empty Weight"), 5, 0)
        self.mand_grid.addWidget(self.empty_weight, 5, 1)

        self.mand_grid.addWidget(QLabel("Net Weight"), 6, 0)
        self.mand_grid.addWidget(self.net_weight, 6, 1)

        self.btn_close_tran = QPushButton("Close Transaction")
        self.mand_grid.addWidget(self.btn_close_tran, 9, 1)
        self.btn_close_tran.clicked.connect(self.close_transaction)

        self.now = QDateTime.currentDateTime()
        self.date_str = self.now.date().toString("yyyy-MM-dd")
        self.time_str = self.now.time().toString("HH:mm:ss")

        self.load_pending_tickets()

        # Weigh button & logic
        self.active_weight_type = None
        self.btn_load.clicked.connect(lambda: self.set_active_weight_type("LOAD"))
        self.btn_empty.clicked.connect(lambda: self.set_active_weight_type("EMPTY"))

        if pending_ticket_number:
            for i in range(self.ticket_number_combo.count()):
                if self.ticket_number_combo.itemText(i) == str(pending_ticket_number):
                    self.ticket_number_combo.setCurrentIndex(i)
                    break
            self.load_ticket_data()

    @property
    def ticket_number(self):
        return self.mandatory_widgets.get("TicketNumber")

    @property
    def vehicle_number(self):
        return self.mandatory_widgets.get("VehicleNumber")

    @property
    def material(self):
        return self.mandatory_widgets.get("Materialname")

    @property
    def supplier(self):
        return self.mandatory_widgets.get("SupplierName")

    @property
    def loaded_weight(self):
        return self.mandatory_widgets.get("LoadedWeight")

    @property
    def empty_weight(self):
        return self.mandatory_widgets.get("EmptyWeight")

    @property
    def net_weight(self):
        return self.mandatory_widgets.get("NetWeight")

    @property
    def status(self):
        return self.custom_widgets.get("STATUS")

    @property
    def eamount(self):
        return self.custom_widgets.get("EAMOUNT")

    @property
    def lamount(self):
        return self.custom_widgets.get("LAMOUNT")

    @property
    def tamount(self):
        return self.custom_widgets.get("TAMOUNT")

    @property
    def netweight1(self):
        return self.custom_widgets.get("NetWeight1")

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
        if self.vehicle_number:
            self.vehicle_number.setText(row.get("VehicleNumber", "") or "")
        if self.material:
            self.material.setCurrentText(row.get("Materialname", "") or "")
        if self.supplier:
            self.supplier.setCurrentText(row.get("SupplierName", "") or "")
        if self.status:
            self.status.setText(row.get("STATUS", "") or "")
        if self.eamount:
            self.eamount.setText(str(row.get("EAMOUNT", "") or ""))
        if self.lamount:
            self.lamount.setText(str(row.get("LAMOUNT", "") or ""))
        if self.tamount:
            self.tamount.setText(str(row.get("TAMOUNT", "") or ""))
        if self.netweight1:
            self.netweight1.setText(str(row.get("NetWeight1", "") or ""))
        if self.empty_weight:
            self.empty_weight.setText(str(row.get("EmptyWeight", "") or ""))
        if self.loaded_weight:
            self.loaded_weight.setText(str(row.get("LoadedWeight", "") or ""))
        if self.net_weight:
            self.net_weight.setText(str(row.get("NetWeight", "") or ""))

        # Enable/disable buttons as per weights
        if row.get("LoadedWeight") and row.get("EmptyWeight"):
            self.btn_load.setEnabled(False)
            self.btn_empty.setEnabled(False)
        elif row.get("LoadedWeight"):
            self.btn_load.setEnabled(False)
            self.btn_empty.setEnabled(True)
            self.set_active_weight_type("EMPTY")
        elif row.get("EmptyWeight"):
            self.btn_load.setEnabled(True)
            self.btn_empty.setEnabled(False)
            self.set_active_weight_type("LOAD")
        else:
            self.btn_load.setEnabled(True)
            self.btn_empty.setEnabled(True)
            self.set_active_weight_type("LOAD")

    def handle_weigh_second(self):
        now = QDateTime.currentDateTime()
        logic_date = now.date().toString("dd/MM/yyyy")
        logic_time = now.time().toString("HH:mm")
        value = random.randint(5000, 50000)
        self.weight_display.setText(str(value))
        # Only update the field matching the active weight type
        if self.active_weight_type == "LOAD":
            if self.loaded_weight:
                self.loaded_weight.setText(str(value))
            self._load_weight_date = logic_date
            self._load_weight_time = logic_time
            empty = self.empty_weight.text() if self.empty_weight else ""
            try:
                net = value - int(empty) if empty else value
            except Exception:
                net = value
            if self.net_weight:
                self.net_weight.setText(str(net))
            self.btn_load.setEnabled(False)
            self.btn_empty.setEnabled(True)
            self.set_active_weight_type("EMPTY")
        elif self.active_weight_type == "EMPTY":
            if self.empty_weight:
                self.empty_weight.setText(str(value))
            self._empty_weight_date = logic_date
            self._empty_weight_time = logic_time
            loaded = self.loaded_weight.text() if self.loaded_weight else ""
            try:
                net = int(loaded) - value if loaded else -value
            except Exception:
                net = -value
            if self.net_weight:
                self.net_weight.setText(str(net))
            self.btn_load.setEnabled(True)
            self.btn_empty.setEnabled(False)
            self.set_active_weight_type("LOAD")
        else:
            if self.empty_weight:
                self.empty_weight.setText("")
            if self.loaded_weight:
                self.loaded_weight.setText("")
            if self.net_weight:
                self.net_weight.setText("")

    def save_ticket(self):
        loaded_present = bool(self.loaded_weight and self.loaded_weight.text())
        empty_present = bool(self.empty_weight and self.empty_weight.text())

        pending = (loaded_present != empty_present)  # XOR: only one weight present
        closed = (loaded_present and empty_present)

        ticket_number = self.ticket_number_combo.currentText()
        db_row = None
        if ticket_number:
            db_row = fetch_one('SELECT "EmptyWeightDate", "EmptyWeightTime", "LoadWeightDate", "LoadWeightTime" FROM tickets WHERE "TicketNumber" = %s', (ticket_number,))
        else:
            QMessageBox.critical(self, "Error", "No Ticket Number selected.")
            return

        save_empty_date  = getattr(self, "_empty_weight_date", "") or (db_row["EmptyWeightDate"] if db_row else "")
        save_empty_time  = getattr(self, "_empty_weight_time", "") or (db_row["EmptyWeightTime"] if db_row else "")
        save_load_date   = getattr(self, "_load_weight_date", "")  or (db_row["LoadWeightDate"] if db_row else "")
        save_load_time   = getattr(self, "_load_weight_time", "")  or (db_row["LoadWeightTime"] if db_row else "")

        extra_params = {
            "EmptyWeightDate": save_empty_date,
            "EmptyWeightTime": save_empty_time,
            "LoadWeightDate": save_load_date,
            "LoadWeightTime": save_load_time,
            "Date": save_empty_date or save_load_date,
            "Time": save_empty_time or save_load_time,
            "State": "second transaction",
            "Pending": pending,
            "Closed": closed,
            "Shift": "B",
            "Exported": False,
        }

        try:
            extra_params["TicketNumber"] = int(ticket_number)
        except Exception:
            extra_params["TicketNumber"] = ticket_number

        int_fields = [
            "EmptyWeight", "LoadedWeight", "NetWeight", "AMOUNT", "EAMOUNT", "LAMOUNT", "TAMOUNT",
            "NetWeight1", "Blank", "LWEIGHT", "EWEIGHT"
        ]
        for field in int_fields:
            widget = getattr(self, field.lower(), None)
            if widget:
                val = widget.text() if hasattr(widget, "text") else None
                if val in ("", None):
                    extra_params[field] = None
                else:
                    try:
                        extra_params[field] = int(val)
                    except Exception:
                        extra_params[field] = None

        date_fields = [
            "EmptyWeightDate", "EmptyWeightTime", "LoadWeightDate", "LoadWeightTime", "Date", "Time"
        ]
        for field in date_fields:
            val = extra_params.get(field, None)
            if val == "":
                extra_params[field] = None

        super().save_ticket(extra_params)
        ticket_number = extra_params.get("TicketNumber")
        ticket_data = fetch_one('SELECT * FROM tickets WHERE "TicketNumber" = %s', (ticket_number,))
        if ticket_data:
            self.show_success_message(ticket_number, ticket_data)
        else:
            QMessageBox.critical(self, "Error", f"Ticket {ticket_number} not found after save.")

    def close_transaction(self):
        ticket_number = self.ticket_number_combo.currentText()
        row = fetch_one('SELECT "Closed" FROM tickets WHERE "TicketNumber" = %s', (ticket_number,))
        db_closed = row["Closed"] if row else False
        execute_query(
            'UPDATE tickets SET "Pending" = FALSE, "Closed" = %s WHERE "TicketNumber" = %s',
            (db_closed, ticket_number)
        )
        # Suppress print prompt after closing transaction
        self._suppress_print_prompt = True
        self.save_ticket()

    def show_success_message(self, ticket_number, ticket_data):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("Success")
        msg.setText(f"Ticket number {ticket_number} successfully saved")
        msg.setStandardButtons(QMessageBox.Ok)
        ret = msg.exec_()
        if ret == QMessageBox.Ok:
            if self._suppress_print_prompt:
                # Reset flag and return to base without asking for print
                self._suppress_print_prompt = False
                self.return_to_base_transaction_window()
            else:
                self.ask_print_prompt(ticket_data)

    def ask_print_prompt(self, ticket_data):
        if self._print_prompt_open:
            return
        self._print_prompt_open = True
        try:
            dlg = PrintPromptDialog(ticket_data, parent=self)
            result = dlg.exec_()
            if result == QDialog.Accepted:
                if not self._printing_in_progress:
                    self._printing_in_progress = True
                    try:
                        print_ticket_with_template(ticket_data)
                    finally:
                        self._printing_in_progress = False
                self.return_to_base_transaction_window()
            else:
                self.return_to_base_transaction_window()
        finally:
            self._print_prompt_open = False

    # Search for non-pending (Pending = FALSE) tickets and show print option
    def search_action(self):
        tickets = fetch_all(
            '''
            SELECT *
            FROM tickets
            WHERE "Pending" = FALSE
            ORDER BY "TicketNumber" DESC
            ''',
            ()
        )
        dlg = QDialog(self)
        dlg.setWindowTitle("Closed/Completed Tickets (Pending = FALSE)")
        layout = QVBoxLayout(dlg)

        headers = ["TicketNumber", "VehicleNumber", "Date", "Time", "EmptyWeight", "LoadedWeight"]
        table = QTableWidget(len(tickets), len(headers))
        table.setHorizontalHeaderLabels(headers)

        for i, t in enumerate(tickets):
            row_vals = {
                "TicketNumber": str(t.get("TicketNumber", "")),
                "VehicleNumber": str(t.get("VehicleNumber", "")),
                "Date": to_display_date(t.get("Date", "")),
                "Time": to_display_time(t.get("Time", "")),
                "EmptyWeight": "" if t.get("EmptyWeight") in (None, "", "None") else str(t.get("EmptyWeight")),
                "LoadedWeight": "" if t.get("LoadedWeight") in (None, "", "None") else str(t.get("LoadedWeight")),
            }
            for j, key in enumerate(headers):
                table.setItem(i, j, QTableWidgetItem(row_vals[key]))

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

        fields_to_show = ["TicketNumber", "VehicleNumber", "Date", "Time"]
        for k in fields_to_show:
            row = QHBoxLayout()
            row.addWidget(QLabel(f"{k}:"))
            if k.lower() == "date":
                display_val = to_display_date(ticket.get(k, ""))
            elif k.lower() == "time":
                display_val = to_display_time(ticket.get(k, ""))
            else:
                display_val = str(ticket.get(k, ""))
            field = QLineEdit(display_val)
            field.setReadOnly(True)
            row.addWidget(field)
            layout.addLayout(row)

        if ticket.get("EmptyWeight") not in (None, "", "None"):
            row = QHBoxLayout()
            row.addWidget(QLabel("EmptyWeight:"))
            field = QLineEdit(str(ticket.get("EmptyWeight")))
            field.setReadOnly(True)
            row.addWidget(field)
            layout.addLayout(row)
        if ticket.get("LoadedWeight") not in (None, "", "None"):
            row = QHBoxLayout()
            row.addWidget(QLabel("LoadedWeight:"))
            field = QLineEdit(str(ticket.get("LoadedWeight")))
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
        self.hide()
