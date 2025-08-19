from base_transaction_window import BaseTransactionWindow
from db_utils import execute_query, fetch_one, fetch_all
from PyQt5.QtWidgets import QPushButton, QComboBox, QDateTimeEdit, QLabel, QMessageBox, QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QLineEdit
from PyQt5.QtCore import  QDateTime, QDate, QTime, QLocale
import random
from print_ticket_with_template_win32 import print_ticket_with_template
from date_time_utils import to_display_date, to_display_time


class PrintPromptDialog(QDialog):
    def __init__(self, ticket_data, parent=None):
        super().__init__(parent)
        print("PrintPromptDialog initialized")
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
        print("Initializing SingleTransactionWindow")
        super().__init__(parent)
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

        # --- Patch: Ensure LoadStatus dropdown exists ---
        if not self.mandatory_widgets.get("LoadStatus"):
            print("[INIT] Adding LoadStatus dropdown manually.")
            self.load_status_widget = QComboBox()
            self.load_status_widget.addItems(["LOAD", "EMPTY"])
            self.load_status_widget.setCurrentText("LOAD")
            self.mand_grid.addWidget(QLabel("Load Status"), 99, 0)
            self.mand_grid.addWidget(self.load_status_widget, 99, 1)
        else:
            print("LoadStatus widget exists, setting combo values")
            self.mandatory_widgets.get("LoadStatus").clear()
            self.mandatory_widgets.get("LoadStatus").addItems(["LOAD", "EMPTY"])
            self.mandatory_widgets.get("LoadStatus").setCurrentText("LOAD")

        # Storage for true weigh event times
        self._empty_weight_date = ""
        self._empty_weight_time = ""
        self._load_weight_date = ""
        self._load_weight_time = ""

        self.btn_weigh.clicked.connect(self.handle_weigh)
        print("Connected Weigh button")

        self.btn_get_tare = QPushButton("Get Tare Weight")
        self.mand_grid.addWidget(self.btn_get_tare, 11, 1)
        self.btn_get_tare.clicked.connect(self.get_tare_weight)
        print("Connected Get Tare Weight button")
        self.btn_save.clicked.connect(self.save_ticket)
        print("Connected Save button")

        if self.ticket_number:
            ticket_num = self.generate_ticket_number()
            print(f"Generated ticket number: {ticket_num}")
            self.ticket_number.setText(ticket_num)
            self.ticket_number.setReadOnly(True)
        if self.loaded_weight:
            self.loaded_weight.setReadOnly(True)
        if self.empty_weight:
            self.empty_weight.setReadOnly(True)
        if self.net_weight:
            self.net_weight.setReadOnly(True)

        # Remove local search button definition
        # self.btn_search = QPushButton("Search")
        # self.btn_search.clicked.connect(self.search_action)
        # self.mand_grid.addWidget(self.btn_search, 12, 1)

        self.result_dialog = None

        # Disconnect and reconnect the inherited search button, if it exists
        try:
            self.btn_exit.clicked.disconnect()
        except TypeError:
            pass  # No connection to disconnect
		#reconnect exit button
        self.btn_exit.clicked.connect(self.return_to_base_transaction_window)

        # Connect the inherited search button (from BaseTransactionWindow) to this class's search_action, if it exists
        if hasattr(self, 'btn_search'):
            try:
                self.btn_search.clicked.disconnect()  # Disconnect existing connection, if any
            except TypeError:
                pass  # No connection to disconnect
            self.btn_search.clicked.connect(self.search_action)  # Connect to this class's search_action
            print("Connected inherited Search button to SingleTransactionWindow's search_action")

        print("SingleTransactionWindow initialized")

    @property
    def load_status(self):
        # Always use manually added widget if present
        if hasattr(self, 'load_status_widget'):
            return self.load_status_widget
        return self.mandatory_widgets.get("LoadStatus")

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
    def amount(self):
        return self.custom_widgets.get("AMOUNT")

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

    def generate_ticket_number(self):
        print("Generating ticket number...")
        row = fetch_one('SELECT COALESCE(MAX(CAST("TicketNumber" AS INTEGER)), 10000) + 1 AS next_ticket FROM tickets')
        print(f"Fetched next_ticket: {row['next_ticket']}")
        return str(row["next_ticket"])

    def handle_weigh(self):
        print("[handle_weigh] called (single transaction)")
        from PyQt5.QtCore import QDateTime
        now = QDateTime.currentDateTime()
        logic_date = now.date().toString("dd/MM/yyyy")
        logic_time = now.time().toString("HH:mm")
        try:
            value = int(float(self.weight_display.text()))
        except (ValueError, TypeError):
            print("[handle_weigh] Error parsing weight_display.text()")
            value = 0
        load_status = self.load_status.currentText().strip().upper() if self.load_status else ""
        print(f"[handle_weigh] LoadStatus: {load_status}")
        if load_status == "EMPTY":
            if self.empty_weight:
                self.empty_weight.setText(str(value))
                print(f"[handle_weigh] Set EmptyWeight: {value}")
            if self.loaded_weight:
                self.loaded_weight.setText("")
                print("[handle_weigh] Cleared LoadedWeight")
            if self.net_weight:
                self.net_weight.setText(str(value))
                print(f"[handle_weigh] Set NetWeight: {value}")
            self._empty_weight_date = logic_date
            self._empty_weight_time = logic_time
        elif load_status == "LOAD":
            if self.loaded_weight:
                self.loaded_weight.setText(str(value))
                print(f"[handle_weigh] Set LoadedWeight: {value}")
            if self.empty_weight:
                self.empty_weight.setText("")
                print("[handle_weigh] Cleared EmptyWeight")
            if self.net_weight:
                self.net_weight.setText(str(value))
                print(f"[handle_weigh] Set NetWeight: {value}")
            self._load_weight_date = logic_date
            self._load_weight_time = logic_time
        else:
            print("[handle_weigh] LoadStatus not set to LOAD or EMPTY, fields not updated")
            if self.empty_weight:
                self.empty_weight.setText("")
            if self.loaded_weight:
                self.loaded_weight.setText("")
            if self.net_weight:
                self.net_weight.setText("")

    def get_tare_weight(self):
        print("get_tare_weight called")
        vehiclenumber = self.vehicle_number.text().strip() if self.vehicle_number else ""
        print(f"Vehicle number for tare lookup: {vehiclenumber}")
        if not vehiclenumber:
            if self.empty_weight:
                self.empty_weight.setText("")
            print("No vehicle number entered, setting EmptyWeight to ''")
            return
        row = fetch_one(
            'SELECT "vehicletareweight" FROM vehiclemaster WHERE "vehiclenumber" = %s',
            (vehiclenumber,)
        )
        print(f"Tare fetch row: {row}")
        if row and row["vehicletareweight"] is not None:
            print(f"Setting EmptyWeight to {row['vehicletareweight']}")
            if self.empty_weight:
                self.empty_weight.setText(str(row["vehicletareweight"]))
        else:
            print("No tare found, setting EmptyWeight to ''")
            if self.empty_weight:
                self.empty_weight.setText("")
        self.calculate_net_weight()

    def calculate_net_weight(self):
        print("calculate_net_weight called")
        try:
            loaded = int(self.loaded_weight.text()) if self.loaded_weight else 0
            empty = int(self.empty_weight.text()) if self.empty_weight else 0
            net = loaded - empty
            print(f"NetWeight calculated: {net} (Loaded: {loaded}, Empty: {empty})")
            if self.net_weight:
                self.net_weight.setText(str(net))
        except Exception as e:
            print(f"Error calculating net weight: {e}")
            if self.net_weight:
                self.net_weight.setText("")

    def save_ticket(self):
        # Use stored weighment event times, not current time
        loaded_present = bool(self.loaded_weight and self.loaded_weight.text())
        empty_present = bool(self.empty_weight and self.empty_weight.text())

        # Pending is true if only one weight present
        pending = (loaded_present != empty_present)  # XOR: only one weight present
        # Closed is true if both weights present
        closed = (loaded_present and empty_present)

        extra_params = {
            # Save the true event times for each weighment (could be blank)
            "EmptyWeightDate": getattr(self, "_empty_weight_date", ""),
            "EmptyWeightTime": getattr(self, "_empty_weight_time", ""),
            "LoadWeightDate": getattr(self, "_load_weight_date", ""),
            "LoadWeightTime": getattr(self, "_load_weight_time", ""),
            # Save ticket date/time as first event (optional: you may keep DB format if required)
            "Date": self._empty_weight_date or self._load_weight_date,
            "Time": self._empty_weight_time or self._load_weight_time,
            "State": "first transaction",
            "Pending": pending,
            "Closed": closed,
            "Shift": "B",
            "Exported": False,
        }

        # PATCH: Always set TicketNumber from widget
        ticket_number = self.ticket_number.text() if self.ticket_number else ""
        if ticket_number:
            try:
                extra_params["TicketNumber"] = int(ticket_number)
            except Exception:
                extra_params["TicketNumber"] = ticket_number  # fallback if ticket numbers are alphanumeric
        else:
            QMessageBox.critical(self, "Error", "No Ticket Number set.")
            return

        # PATCH: convert blank string to None for integer fields
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

        # PATCH: convert blank string to None for date/time fields too!
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

    def show_success_message(self, ticket_number, ticket_data):
        print(f"Showing success message for TicketNumber: {ticket_number}")
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("Success")
        msg.setText(f"Ticket number {ticket_number} successfully saved")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.buttonClicked.connect(lambda _: self.ask_print_prompt(ticket_data))
        msg.exec_()

    def ask_print_prompt(self, ticket_data):
        print("ask_print_prompt called")
        dlg = PrintPromptDialog(ticket_data, parent=self)
        result = dlg.exec_()
        print(f"PrintPromptDialog result: {result}")
        if result == QDialog.Accepted:
            print("Printing ticket...")
            print_ticket_with_template(ticket_data)
            self.return_to_base_transaction_window()
        else:
            print("Returning to base transaction window")
            self.return_to_base_transaction_window()

    

    def display_ticket_fields(self, ticket, parent_dialog):
        print(f"display_ticket_fields called for ticket: {ticket}")
        field_dlg = QDialog(parent_dialog)
        field_dlg.setWindowTitle(f"Ticket {ticket['TicketNumber']} Details")
        layout = QVBoxLayout(field_dlg)
        for k, v in ticket.items():
            row = QHBoxLayout()
            row.addWidget(QLabel(f"{k}:"))
            # Use unified helpers for Date/Time fields
            if k.lower() == "date":
                display_val = to_display_date(v)
            elif k.lower() == "time":
                display_val = to_display_time(v)
            else:
                display_val = str(v)
            field = QLineEdit(display_val)
            field.setReadOnly(True)
            row.addWidget(field)
            layout.addLayout(row)
        btn_print = QPushButton("Print")
        btn_print.clicked.connect(lambda: self.print_selected_ticket(ticket))
        layout.addWidget(btn_print)
        field_dlg.setLayout(layout)
        field_dlg.exec_()


    def print_selected_ticket(self, ticket):
        print(f"print_selected_ticket called for ticket: {ticket}")
        print_ticket_with_template(ticket)

    def return_to_base_transaction_window(self):
        print("return_to_base_transaction_window called")
        parent = self.parent()
        if parent:
            parent.show()
        self.hide()

    def search_action(self):
        print("search_action called")
        tickets = fetch_all('SELECT * FROM tickets WHERE "State" = %s', ("single transaction",))
        print(f"Fetched {len(tickets)} tickets for search")
        for t in tickets:
            print(t)
        if not tickets:
            QMessageBox.information(self, "No Tickets Found", "No single transaction tickets found in the database.")
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("Single Transaction Search")
        layout = QVBoxLayout(dlg)
        headers = ["TicketNumber", "VehicleNumber", "Date", "Time"]
        table = QTableWidget(len(tickets), len(headers))
        table.setHorizontalHeaderLabels(headers)
        for i, t in enumerate(tickets):
            table.setItem(i, 0, QTableWidgetItem(str(t.get("TicketNumber", ""))))
            table.setItem(i, 1, QTableWidgetItem(str(t.get("VehicleNumber", ""))))
            table.setItem(i, 2, QTableWidgetItem(to_display_date(t.get("Date", ""))))
            table.setItem(i, 3, QTableWidgetItem(to_display_time(t.get("Time", ""))))

        def on_cell_clicked(row, col):
            self.display_ticket_fields(tickets[row], dlg)

        table.cellClicked.connect(on_cell_clicked)
        layout.addWidget(table)
        dlg.setLayout(layout)
        dlg.exec_()
