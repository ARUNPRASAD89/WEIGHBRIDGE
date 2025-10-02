from base_transaction_window import BaseTransactionWindow
from db_utils import execute_query, fetch_one, fetch_all
from PyQt5.QtWidgets import (
    QPushButton, QComboBox, QDateTimeEdit, QLabel, QMessageBox, QDialog,
    QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QLineEdit,
    QScrollArea, QWidget # Added QScrollArea and QWidget
)
from PyQt5.QtCore import  QDateTime, QDate, QTime, QLocale, Qt # Added Qt
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

class FirstTransactionWindow(BaseTransactionWindow):
    def __init__(self, parent=None, transaction_window=None):
        super().__init__(parent)
        # FIX: Set button states to reflect this window's mode
        self.set_active_transaction_buttons('first')

        self.transaction_window = transaction_window
        self.lbl_title.setText("Vehicle First Transaction")
        self.btn_save.setEnabled(True)
        if self.ticket_number:
            self.ticket_number.setReadOnly(True)
            self.ticket_number.setText(self.generate_ticket_number())
        if self.loaded_weight:
            self.loaded_weight.setReadOnly(True)
        if self.empty_weight:
            self.empty_weight.setReadOnly(True)
        if self.net_weight:
            self.net_weight.setReadOnly(True)

        now = QDateTime.currentDateTime()
        self.date = now.date().toString("yyyy-MM-dd")
        self.time = now.time().toString("HH:mm:ss")

        # Storage for true weigh event times
        self._empty_weight_date = ""
        self._empty_weight_time = ""
        self._load_weight_date = ""
        self._load_weight_time = ""

        # Flow control flags
        self._pending_checked = False            # Ask pending verification at start only
        self._suppress_pending_check = False     # Suppress during printing/cleanup
        self._print_prompt_open = False          # Avoid multiple print prompts
        self._printing_in_progress = False       # Avoid multiple print windows

        # --- Patch: Ensure LoadStatus dropdown exists ---
        if not self.mandatory_widgets.get("LoadStatus"):
            print("[INIT] Adding LoadStatus dropdown manually.")
            self.load_status_widget = QComboBox()
            self.load_status_widget.addItems(["LOAD", "EMPTY"])
            self.load_status_widget.setCurrentText("LOAD")
            self.mand_grid.addWidget(QLabel("Load Status"), 99, 0)
            self.mand_grid.addWidget(self.load_status_widget, 99, 1)
        else:
            self.mandatory_widgets.get("LoadStatus").clear()
            self.mandatory_widgets.get("LoadStatus").addItems(["LOAD", "EMPTY"])
            self.mandatory_widgets.get("LoadStatus").setCurrentText("LOAD")

        # Ensure single connection for Save and Weigh
        try:
            self.btn_save.clicked.disconnect()
        except Exception:
            pass
        self.btn_save.clicked.connect(self.check_pending_and_save)

        try:
            self.btn_weigh.clicked.disconnect()
        except Exception:
            pass
        self.btn_weigh.clicked.connect(self.handle_weigh)

        if self.vehicle_number:
            try:
                self.vehicle_number.editingFinished.disconnect()
            except Exception:
                pass
            self.vehicle_number.editingFinished.connect(self.check_pending_on_vehicle_entry)

        # Add or connect to existing Search button
        if not hasattr(self, "btn_search"):
            self.btn_search = QPushButton("Search")
            self.mand_grid.addWidget(self.btn_search, 12, 1)
        try:
            self.btn_search.clicked.disconnect()
        except Exception:
            pass
        self.btn_search.clicked.connect(self.search_action)

        # FIX: Ensure Exit button returns to the correct parent window
        try:
            self.btn_exit.clicked.disconnect()
        except Exception:
            pass
        self.btn_exit.clicked.connect(self.return_to_base_transaction_window)

        if hasattr(self, "btn_close_tran"):
            self.btn_close_tran.setVisible(False)

    def return_to_base_transaction_window(self):
        """Custom exit behavior for this window."""
        parent = self.parent()
        if parent:
            # Reset parent's buttons to the base state
            parent.set_active_transaction_buttons('base')
            parent.show()
        self.close()

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
        row = fetch_one('SELECT COALESCE(MAX(CAST("TicketNumber" AS INTEGER)), 10000) + 1 AS next_ticket FROM tickets')
        return str(row["next_ticket"])

    def handle_weigh(self):
        from PyQt5.QtCore import QDateTime
        now = QDateTime.currentDateTime()
        logic_date = now.date().toString("dd/MM/yyyy")
        logic_time = now.time().toString("HH:mm")
        print("[handle_weigh] called (first transaction)")
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
            # Set empty event time
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
            # Set load event time
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

    def check_pending_on_vehicle_entry(self):
        if self._suppress_pending_check or self._pending_checked:
            return
        veh_number = self.vehicle_number.text().strip() if self.vehicle_number else ""
        if not veh_number:
            return
        # Check for pending=TRUE
        pending_row = fetch_one(
            'SELECT "TicketNumber" FROM tickets WHERE "VehicleNumber" = %s AND "Pending" = TRUE', (veh_number,)
        )
        self._pending_checked = True  # Ask only once per form session
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
                if self.vehicle_number:
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
        # Ask pending verification at start only (on vehicle entry). Do not re-ask on Save.
        self.save_ticket()

    def save_ticket(self):
        loaded_present = bool(self.loaded_weight and self.loaded_weight.text())
        empty_present = bool(self.empty_weight and self.empty_weight.text())
        pending = (loaded_present != empty_present)
        closed = (loaded_present and empty_present)

        ticket_number = self.ticket_number.text() if self.ticket_number else ""
        db_row = None
        if ticket_number:
            db_row = fetch_one(
                'SELECT "EmptyWeightDate", "EmptyWeightTime", "LoadWeightDate", "LoadWeightTime" FROM tickets WHERE "TicketNumber" = %s',
                (ticket_number,)
            )
        else:
            QMessageBox.critical(self, "Error", "No Ticket Number set.")
            return

        # Preserve previous event time if only one event is updated
        save_empty_date = getattr(self, "_empty_weight_date", "") or (db_row["EmptyWeightDate"] if db_row else "")
        save_empty_time = getattr(self, "_empty_weight_time", "") or (db_row["EmptyWeightTime"] if db_row else "")
        save_load_date = getattr(self, "_load_weight_date", "") or (db_row["LoadWeightDate"] if db_row else "")
        save_load_time = getattr(self, "_load_weight_time", "") or (db_row["LoadWeightTime"] if db_row else "")

        extra_params = {
            "EmptyWeightDate": save_empty_date,
            "EmptyWeightTime": save_empty_time,
            "LoadWeightDate": save_load_date,
            "LoadWeightTime": save_load_time,
            "Date": save_empty_date or save_load_date,
            "Time": save_empty_time or save_load_time,
            "State": "first transaction",
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

    def show_success_message(self, ticket_number, ticket_data):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("Success")
        msg.setText(f"Ticket number {ticket_number} successfully saved")
        msg.setStandardButtons(QMessageBox.Ok)
        ret = msg.exec_()
        if ret == QMessageBox.Ok:
            self.ask_print_prompt(ticket_data)

    def ask_print_prompt(self, ticket_data):
        if self._print_prompt_open:
            return
        self._print_prompt_open = True
        try:
            dlg = PrintPromptDialog(ticket_data, parent=self)
            result = dlg.exec_()
            if result == QDialog.Accepted:
                # Avoid any re-entrant checks or duplicate print windows
                if not self._printing_in_progress:
                    self._suppress_pending_check = True
                    self._printing_in_progress = True
                    try:
                        print_ticket_with_template(ticket_data)
                    finally:
                        self._printing_in_progress = False
                        self._suppress_pending_check = False
                # Clear fields and return to base
                self.clear_all_fields()
                self.return_to_base_transaction_window()
            else:
                # User chose not to print; clear and return
                self.clear_all_fields()
                self.return_to_base_transaction_window()
        finally:
            self._print_prompt_open = False

    def clear_all_fields(self):
        # Clear everything according to weighbridge end-of-transaction logic
        try:
            self.clear_non_essential_fields(essentials=())
        except Exception:
            pass
        # Explicitly clear ticket number and set combos to default index 0
        if self.ticket_number:
            self.ticket_number.clear()
        if self.load_status:
            try:
                self.load_status.setCurrentIndex(0)
            except Exception:
                pass
        # Reset weight display and internal timestamps/flags
        try:
            self.weight_display.setText("0")
        except Exception:
            pass
        self._empty_weight_date = ""
        self._empty_weight_time = ""
        self._load_weight_date = ""
        self._load_weight_time = ""
        self._pending_checked = False

    def search_action(self):
        # MODIFIED: Changed ORDER BY to sort by TicketNumber DESC
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
            ORDER BY t1."TicketNumber" DESC;
            ''',
            ()
        )
        dlg = QDialog(self)
        dlg.setWindowTitle("First Weighment Per Vehicle")
        dlg.setMinimumSize(800, 600) # Set a reasonable minimum size

        layout = QVBoxLayout(dlg)
        headers = ["TicketNumber", "VehicleNumber", "Date", "Time", "EmptyWeight", "LoadedWeight"]
        
        table = QTableWidget(len(tickets), len(headers))
        table.setHorizontalHeaderLabels(headers)
        
        for i, t in enumerate(tickets):
            for j, key in enumerate(headers):
                if key.lower() == "date":
                    value = to_display_date(t.get(key, ""))
                elif key.lower() == "time":
                    value = to_display_time(t.get(key, ""))
                else:
                    value = str(t.get(key, ""))
                table.setItem(i, j, QTableWidgetItem(value))
        
        table.cellClicked.connect(lambda row, col: self.display_ticket_fields(tickets[row], dlg))
        
        # MODIFIED: Wrap the table in a QScrollArea
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(table)
        
        layout.addWidget(scroll_area)
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
        elif ticket.get("LoadedWeight") not in (None, "", "None"):
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
