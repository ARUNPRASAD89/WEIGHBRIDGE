from base_transaction_window import BaseTransactionWindow
from db_utils import execute_query, fetch_one, fetch_all
from PyQt5.QtWidgets import (
    QPushButton, QComboBox, QDateTimeEdit, QLabel, QMessageBox, QDialog,
    QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QLineEdit,
    QScrollArea, QWidget # Added QScrollArea and QWidget
)
from PyQt5.QtCore import  QDateTime, Qt # Added Qt
import random
from print_ticket_with_template_win32 import print_ticket_with_template
from date_time_utils import to_display_date, to_display_time, to_db_date, to_db_time

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
        # FIX: Set button states to reflect this window's mode
        self.set_active_transaction_buttons('single')

        self.lbl_title.setText("Vehicle Single Transaction")
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

        # Ensure single connection for Save and Weigh
        try:
            self.btn_save.clicked.disconnect()
        except Exception:
            pass
        self.btn_save.clicked.connect(self.save_ticket)

        try:
            self.btn_weigh.clicked.disconnect()
        except Exception:
            pass
        self.btn_weigh.clicked.connect(self.handle_weigh)

        # FIX: Ensure Exit button returns to the correct parent window
        try:
            self.btn_exit.clicked.disconnect()
        except Exception:
            pass
        self.btn_exit.clicked.connect(self.return_to_base_transaction_window)
        
        # NEW: Add Search button
        if not hasattr(self, "btn_search"):
            self.btn_search = QPushButton("Search")
            self.mand_grid.addWidget(self.btn_search, 12, 1)
        try:
            self.btn_search.clicked.disconnect()
        except Exception:
            pass
        self.btn_search.clicked.connect(self.search_action)


        # Hide unnecessary buttons for single transaction
        if hasattr(self, "btn_close_tran"):
            self.btn_close_tran.setVisible(False)
        if hasattr(self, "load_status") and self.load_status:
            self.load_status.setVisible(False)
            # Find the label for LoadStatus and hide it too
            for i in range(self.mand_grid.count()):
                item = self.mand_grid.itemAt(i)
                if item is None: continue
                widget = item.widget()
                if isinstance(widget, QLabel) and "Load Status" in widget.text():
                    widget.setVisible(False)
                    break

        # NEW: Add "Get Tare" button next to VehicleNumber input (if present)
        self._tare_weight_manually_set = False
        self.btn_get_tare = QPushButton("Get Tare")
        self.btn_get_tare.setToolTip("Retrieve vehicle tare from VehicleMaster and fill Empty Weight")
        self.btn_get_tare.setFixedSize(110, 32)
        self.btn_get_tare.clicked.connect(self.get_tare_weight)

        # Try to place the button beside the vehicle input in the mandatory grid.
        placed = False
        try:
            for idx in range(self.mand_grid.count()):
                item = self.mand_grid.itemAt(idx)
                if not item:
                    continue
                widget = item.widget()
                if widget is self.vehicle_number:
                    # getItemPosition returns (row, column, rowSpan, colSpan)
                    row, col, rowspan, colspan = self.mand_grid.getItemPosition(idx)
                    # Place button in next column. If next column already has something, place in col+2.
                    target_col = col + 1
                    # If target column is occupied, just place at col+2
                    occupied = False
                    for j in range(self.mand_grid.count()):
                        r, c, rs, cs = self.mand_grid.getItemPosition(j)
                        if r == row and c == target_col:
                            occupied = True
                            break
                    if occupied:
                        target_col = col + 2
                    self.mand_grid.addWidget(self.btn_get_tare, row, target_col)
                    placed = True
                    break
        except Exception:
            placed = False

        if not placed:
            # Fallback: add the button near the Search button location if placed earlier,
            # otherwise add to a reasonable default row.
            try:
                self.mand_grid.addWidget(self.btn_get_tare, 12, 2)
            except Exception:
                try:
                    self.mand_grid.addWidget(self.btn_get_tare, 2, 2)
                except Exception:
                    # Last fallback: ignore placement error (button exists but not visible)
                    pass

    def return_to_base_transaction_window(self):
        """Custom exit behavior for this window."""
        parent = self.parent()
        if parent:
            # Reset parent's buttons to the base state
            parent.set_active_transaction_buttons('base')
            parent.show()
        self.close()

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
    def load_status(self):
        return self.mandatory_widgets.get("LoadStatus")

    def generate_ticket_number(self):
        row = fetch_one('SELECT COALESCE(MAX(CAST("TicketNumber" AS INTEGER)), 10000) + 1 AS next_ticket FROM tickets')
        return str(row["next_ticket"])

    def handle_weigh(self):
        now = QDateTime.currentDateTime()
        logic_date = now.date().toString("dd/MM/yyyy")
        logic_time = now.time().toString("HH:mm")
        try:
            value = int(float(self.weight_display.text()))
        except (ValueError, TypeError):
            value = 0

        # In single transaction, the first weigh is always the loaded weight
        if not self.loaded_weight.text():
            self.loaded_weight.setText(str(value))
            self.net_weight.setText(str(value))
            self._load_weight_date = logic_date
            self._load_weight_time = logic_time
        # The second weigh is always the empty weight
        else:
            self.empty_weight.setText(str(value))
            try:
                net = int(self.loaded_weight.text()) - value
                self.net_weight.setText(str(net))
            except Exception:
                self.net_weight.setText(str(-value))
            self._empty_weight_date = logic_date
            self._empty_weight_time = logic_time

    def get_tare_weight(self):
        """
        When the Get Tare button is pressed:
        - Read the vehicle number from the vehicle_number input (mandatory field).
        - Query vehiclemaster for vehicletareweight (case-insensitive match).
        - If found, populate the EmptyWeight field with the tare value (integer).
        - If not found or DB error, show a warning message.
        """
        try:
            veh_widget = self.vehicle_number
            if veh_widget is None:
                QMessageBox.warning(self, "No Vehicle Field", "Vehicle number field is not available on this form.")
                return
            veh_text = veh_widget.text().strip().upper()
            if not veh_text:
                QMessageBox.warning(self, "Input Required", "Please enter a vehicle number before getting tare.")
                veh_widget.setFocus()
                return

            # Query DB for tare value
            row = fetch_one(
                "SELECT vehicletareweight FROM vehiclemaster WHERE UPPER(vehiclenumber) = %s LIMIT 1",
                (veh_text,)
            )
            if not row:
                QMessageBox.information(self, "Not Found", f"No tare weight recorded for vehicle '{veh_text}'.")
                return

            tare_val = None
            # row can be dict-like or tuple; handle both
            if isinstance(row, dict):
                tare_val = row.get("vehicletareweight") or row.get("vehicletareweight".lower())
            elif isinstance(row, (list, tuple)):
                tare_val = row[0] if len(row) > 0 else None
            else:
                # scalar
                tare_val = row

            if tare_val in (None, ""):
                QMessageBox.information(self, "No Tare", f"Vehicle '{veh_text}' does not have a tare weight defined.")
                return

            try:
                # Normalize to integer kg
                tare_int = int(float(tare_val))
            except Exception:
                # If conversion fails, use raw string
                tare_int = tare_val

            # Populate empty weight field
            ew_widget = self.empty_weight
            if ew_widget:
                ew_widget.setText(str(tare_int))
                self._tare_weight_manually_set = True
                QMessageBox.information(self, "Tare Applied", f"Tare weight {tare_int} applied to Empty Weight.")
            else:
                QMessageBox.warning(self, "No Empty Weight Field", "Empty Weight field not available to populate tare.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to retrieve tare weight:\n{e}")

    def save_ticket(self):
        # Validate that both weights are present before saving
        if not self.loaded_weight.text() or not self.empty_weight.text():
            QMessageBox.warning(self, "Incomplete Data", "Both Loaded Weight and Empty Weight must be captured before saving.")
            return

        # Use QDateTime + helpers to produce DB-format or None for date/time fields
        now = QDateTime.currentDateTime()

        def _db_date_or_none(val):
            # to_db_date returns "" when it can't parse; convert that to None
            if val is None or val == "":
                return None
            converted = to_db_date(val)
            return converted if converted else None

        def _db_time_or_none(val):
            if val is None or val == "":
                return None
            converted = to_db_time(val)
            return converted if converted else None

        extra_params = {
            # main Date/Time should use DB format
            "Date": _db_date_or_none(now.date()),
            "Time": _db_time_or_none(now.time()),
            # convert stored event timestamps (may be display strings like 'dd/MM/yyyy'/'HH:mm')
            "LoadWeightDate": _db_date_or_none(getattr(self, "_load_weight_date", "")),
            "LoadWeightTime": _db_time_or_none(getattr(self, "_load_weight_time", "")),
            "EmptyWeightDate": _db_date_or_none(getattr(self, "_empty_weight_date", "")),
            "EmptyWeightTime": _db_time_or_none(getattr(self, "_empty_weight_time", "")),
            "State": "single transaction",
            "Pending": False,
            "Closed": True, # A single transaction is always closed
            "Shift": "B",
            "Exported": False,
        }

        # Now call the base saver which will filter and upsert fields.
        super().save_ticket(extra_params)
        ticket_number = self.ticket_number.text()
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
        dlg = PrintPromptDialog(ticket_data, parent=self)
        result = dlg.exec_()
        if result == QDialog.Accepted:
            try:
                print_ticket_with_template(ticket_data)
            except Exception as e:
                QMessageBox.critical(self, "Print Error", f"Failed to print ticket: {e}")
        
        # Always clear and return after prompt
        self.clear_all_fields()
        self.return_to_base_transaction_window()

    def clear_all_fields(self):
        try:
            self.clear_non_essential_fields(essentials=())
        except Exception as e:
            print(f"Error clearing fields: {e}")

        if self.ticket_number:
            self.ticket_number.clear()
        
        try:
            self.weight_display.setText("0")
        except Exception:
            pass
        
        self._load_weight_date = ""
        self._load_weight_time = ""
        self._empty_weight_date = ""
        self._empty_weight_time = ""
        self._tare_weight_manually_set = False

    # NEW: Search action for single transaction tickets
    def search_action(self):
        tickets = fetch_all(
            '''
            SELECT *
            FROM tickets
            WHERE "State" = 'single transaction'
            ORDER BY "TicketNumber" DESC
            ''',
            ()
        )
        dlg = QDialog(self)
        dlg.setWindowTitle("Completed Single Transactions")
        dlg.setMinimumSize(800, 600)

        layout = QVBoxLayout(dlg)
        headers = ["TicketNumber", "VehicleNumber", "Date", "Time", "EmptyWeight", "LoadedWeight", "NetWeight"]
        
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
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(table)
        
        layout.addWidget(scroll_area)
        dlg.setLayout(layout)
        dlg.exec_()

    # NEW: Display details for a selected ticket
    def display_ticket_fields(self, ticket, parent_dialog):
        field_dlg = QDialog(parent_dialog)
        field_dlg.setWindowTitle(f"Ticket {ticket['TicketNumber']} Details")
        layout = QVBoxLayout(field_dlg)

        fields_to_show = ["TicketNumber", "VehicleNumber", "Date", "Time", "LoadedWeight", "EmptyWeight", "NetWeight"]
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

        btn_print = QPushButton("Print")
        btn_print.clicked.connect(lambda: self.print_selected_ticket(ticket))
        layout.addWidget(btn_print)

        field_dlg.setLayout(layout)
        field_dlg.exec_()

    # NEW: Print a selected ticket
    def print_selected_ticket(self, ticket):
        print_ticket_with_template(ticket)
