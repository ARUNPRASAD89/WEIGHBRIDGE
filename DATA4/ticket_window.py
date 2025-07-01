import random
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, QComboBox, QHBoxLayout,
    QVBoxLayout, QGridLayout, QFrame, QMessageBox
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QDateTime
from db_utils import execute_query, fetch_one, get_connection

class TicketWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ticket")
        self.setMinimumSize(1000, 560)
        self.setStyleSheet("background: #f6f6f6;")
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(0)

        # --- Left: Transaction Type Buttons ---
        self.menu_layout = QVBoxLayout()
        self.menu_layout.setSpacing(14)
        self.menu_layout.setContentsMargins(0, 0, 24, 0)

        btn_font = QFont("Arial", 11, QFont.Bold)
        self.single_btn = QPushButton("Single\nTransaction")
        self.first_btn = QPushButton("First\nTransaction")
        self.second_btn = QPushButton("Second\nTransaction")

        for b in (self.single_btn, self.first_btn, self.second_btn):
            b.setFixedSize(150, 54)
            b.setFont(btn_font)
            self.menu_layout.addWidget(b)

        self.menu_layout.addStretch(1)
        main_layout.addLayout(self.menu_layout)

        # --- Right: Main Transaction Panel ---
        self.right_panel = QVBoxLayout()
        self.right_panel.setSpacing(10)
        self.right_panel.setContentsMargins(0, 0, 0, 0)

        # Header: Title and Weight
        self.header_layout = QHBoxLayout()
        self.header_layout.setSpacing(14)
        self.title_label = QLabel()
        self.title_label.setFont(QFont("Arial", 20, QFont.Bold))
        self.title_label.setTextFormat(Qt.RichText)
        self.header_layout.addWidget(self.title_label, alignment=Qt.AlignVCenter)

        self.weight_display = QLabel()
        self.weight_display.setFont(QFont("Arial", 38, QFont.Bold))
        self.weight_display.setStyleSheet(
            "background:#111;color:white;padding:0 40px;border-radius:10px;min-width:220px;text-align:right;"
        )
        self.weight_display.setAlignment(Qt.AlignCenter)
        self.header_layout.addStretch(1)
        self.header_layout.addWidget(self.weight_display, alignment=Qt.AlignRight | Qt.AlignTop)
        self.right_panel.addLayout(self.header_layout)

        # Fields Section
        self.fields_layout = QHBoxLayout()
        self.fields_layout.setSpacing(15)

        # --- Mandatory Fields ---
        mand_frame = QFrame()
        mand_grid = QGridLayout(mand_frame)
        mand_grid.setHorizontalSpacing(10)
        mand_grid.setVerticalSpacing(9)
        mand_lbl = QLabel("Mandatory Fields")
        mand_lbl.setFont(QFont("Arial", 11, QFont.Bold))
        mand_grid.addWidget(mand_lbl, 0, 0, 1, 2)

        self.ticket_number_edit = QLineEdit()
        self.ticket_number_edit.setReadOnly(True)
        self.ticket_number_combo = QComboBox()
        self.ticket_number_combo.setEditable(False)
        self.ticket_number_combo.hide()

        self.vehicle_number = QLineEdit()
        self.load_status = QComboBox()
        self.load_status.addItems(["Empty", "Loaded"])
        self.material = QLineEdit()
        self.supplier = QLineEdit()
        self.loaded_weight = QLineEdit(); self.loaded_weight.setReadOnly(True)
        self.empty_weight = QLineEdit(); self.empty_weight.setReadOnly(True)
        self.net_weight = QLineEdit(); self.net_weight.setReadOnly(True)

        self.get_tare_btn = QPushButton("Get Tare Weight")
        self.get_tare_btn.setFixedHeight(23)
        self.get_tare_btn.setStyleSheet("font-weight:bold;")
        self.get_tare_btn.clicked.connect(self.get_tare_weight)

        mand_grid.addWidget(QLabel("Ticket Number"), 1, 0)
        mand_grid.addWidget(self.ticket_number_edit, 1, 1)
        mand_grid.addWidget(self.ticket_number_combo, 1, 1)
        mand_grid.addWidget(QLabel("Vehicle Number"), 2, 0)
        self.h_vehicle = QHBoxLayout()
        self.h_vehicle.addWidget(self.vehicle_number)
        mand_grid.addLayout(self.h_vehicle, 2, 1)
        mand_grid.addWidget(QLabel("Load Status"), 3, 0)
        mand_grid.addWidget(self.load_status, 3, 1)
        mand_grid.addWidget(QLabel("Material"), 4, 0)
        mand_grid.addWidget(self.material, 4, 1)
        mand_grid.addWidget(QLabel("Supplier"), 5, 0)
        mand_grid.addWidget(self.supplier, 5, 1)
        mand_grid.addWidget(QLabel("Loaded Weight"), 6, 0)
        mand_grid.addWidget(self.loaded_weight, 6, 1)
        mand_grid.addWidget(QLabel("Empty Weight"), 7, 0)
        mand_grid.addWidget(self.empty_weight, 7, 1)
        mand_grid.addWidget(QLabel("Net Weight"), 8, 0)
        mand_grid.addWidget(self.net_weight, 8, 1)

        self.fields_layout.addWidget(mand_frame)

        # --- Custom Fields ---
        cust_frame = QFrame()
        cust_grid = QGridLayout(cust_frame)
        cust_grid.setHorizontalSpacing(10)
        cust_grid.setVerticalSpacing(9)
        cust_lbl = QLabel("Custom Fields")
        cust_lbl.setFont(QFont("Arial", 11, QFont.Bold))
        cust_grid.addWidget(cust_lbl, 0, 0, 1, 2)

        self.state = QLineEdit()
        self.blank = QLineEdit()
        self.amount = QLineEdit()
        self.status = QLineEdit()
        self.eamount = QLineEdit()
        self.lamount = QLineEdit()
        self.tamount = QLineEdit()
        self.netweight1 = QLineEdit()
        self.lweight = QLineEdit()
        self.eweight = QLineEdit()

        custom_fields = [
            ("State", self.state),
            ("Blank", self.blank),
            ("AMOUNT", self.amount),
            ("STATUS", self.status),
            ("EAMOUNT", self.eamount),
            ("LAMOUNT", self.lamount),
            ("TAMOUNT", self.tamount),
            ("NetWeight1", self.netweight1),
            ("LWEIGHT", self.lweight),
            ("EWEIGHT", self.eweight),
        ]
        for i, (label, widget) in enumerate(custom_fields, 1):
            cust_grid.addWidget(QLabel(label), i, 0)
            cust_grid.addWidget(widget, i, 1)
        self.fields_layout.addWidget(cust_frame)

        self.right_panel.addLayout(self.fields_layout)

        # --- Operations Buttons ---
        self.ops_layout = QHBoxLayout()
        self.ops_layout.setSpacing(8)
        op_font = QFont("Arial", 11, QFont.Bold)
        self.weigh_btn = QPushButton("Weigh")
        self.save_btn = QPushButton("Save")
        self.close_tran_btn = QPushButton("Close Transaction")
        self.cancel_btn = QPushButton("Cancel")
        for btn in [self.weigh_btn, self.save_btn, self.close_tran_btn, self.cancel_btn]:
            btn.setFont(op_font)
            btn.setFixedSize(150, 38)
            self.ops_layout.addWidget(btn)
        self.right_panel.addLayout(self.ops_layout)

        main_layout.addLayout(self.right_panel)

        # Connect op_buttons signals
        self.weigh_btn.clicked.connect(self.handle_weigh)
        self.save_btn.clicked.connect(self.handle_save)
        self.close_tran_btn.clicked.connect(self.handle_close_transaction)
        self.cancel_btn.clicked.connect(self.handle_cancel)

        # Connect transaction type buttons
        self.single_btn.clicked.connect(self.show_single)
        self.first_btn.clicked.connect(self.show_first)
        self.second_btn.clicked.connect(self.show_second)

        self.ticket_counter = 15044  # Example start
        self.current_ticket_number = None  # Store ticket number for first transaction

        try:
            conn = get_connection()
            conn.close()
            print("Connection: OK")
        except Exception as e:
            print("Connection failed:", e)

        self.weigh_locked = False
        self.current_mode = "first"
        self.current_weight = self.get_weight_from_display()

        # For second transaction dropdown
        self.ticket_number_combo.currentIndexChanged.connect(self.on_second_ticket_selected)
        self.show_first()  # Default view

    def get_next_ticket_number(self):
        ticket_str = f"{self.ticket_counter:05d}"
        self.ticket_counter += 1
        return ticket_str

    def show_single(self):
        self.current_mode = "single"
        self.clear_fields()
        self.ticket_number_combo.hide()
        self.ticket_number_edit.show()
        self.ticket_number_edit.setText(self.get_next_ticket_number())
        self.load_status.setCurrentIndex(1)
        self.current_weight = self.get_weight_from_display()
        self.weight_display.setText(f"{self.current_weight} <span style='font-size:15pt'>kg</span>")
        self.weigh_locked = False
        if self.h_vehicle.indexOf(self.get_tare_btn) == -1:
            self.h_vehicle.addWidget(self.get_tare_btn)
        self.close_tran_btn.setVisible(False)
        try:
            self.vehicle_number.editingFinished.disconnect(self.check_pending_ticket_on_entry)
        except Exception:
            pass

    def show_first(self):
        self.current_mode = "first"
        self.clear_fields()
        self.ticket_number_combo.hide()
        self.ticket_number_edit.show()
        # Only generate a new ticket number if not resuming after cancel!
        if self.current_ticket_number is None:
            self.current_ticket_number = self.get_next_ticket_number()
        self.ticket_number_edit.setText(self.current_ticket_number)
        self.load_status.setCurrentIndex(0)
        self.current_weight = self.get_weight_from_display()
        self.weight_display.setText(f"{self.current_weight} <span style='font-size:15pt'>kg</span>")
        self.weigh_locked = False
        if self.h_vehicle.indexOf(self.get_tare_btn) != -1:
            self.h_vehicle.removeWidget(self.get_tare_btn)
            self.get_tare_btn.setParent(None)
        self.close_tran_btn.setVisible(False)
        try:
            self.vehicle_number.editingFinished.disconnect(self.check_pending_ticket_on_entry)
        except Exception:
            pass
        self.vehicle_number.editingFinished.connect(self.check_pending_ticket_on_entry)

    def show_second(self, ticket_row=None):
        self.current_mode = "second"
        self.clear_fields()
        self.ticket_number_edit.hide()
        self.ticket_number_combo.show()
        pending_tickets = execute_query('SELECT "TicketNumber" FROM tickets WHERE "Pending" = TRUE')
        print("Pending tickets:", pending_tickets)  # For debugging
        self.ticket_number_combo.blockSignals(True)
        self.ticket_number_combo.clear()
        if pending_tickets:
            ticket_numbers = [str(row[0]) for row in pending_tickets]
            self.ticket_number_combo.addItems(ticket_numbers)
        self.ticket_number_combo.blockSignals(False)
        # Do NOT call load_selected_pending_ticket here
        # Fields will remain empty until a ticket is selected

    def on_second_ticket_selected(self, idx):
        ticket_no = self.ticket_number_combo.currentText()
        if ticket_no:
            self.load_selected_pending_ticket()
        else:
            self.clear_fields()

    def load_selected_pending_ticket(self):
        ticket_no = self.ticket_number_combo.currentText()
        if not ticket_no:
            self.clear_fields()
            return
        row = fetch_one('SELECT * FROM tickets WHERE "TicketNumber" = %s', (ticket_no,))
        if not row:
            self.clear_fields()
            return
        self.vehicle_number.setText(row["VehicleNumber"] if isinstance(row, dict) else row[1])
        self.material.setText(row.get("Materialname", "") if isinstance(row, dict) else "")
        self.supplier.setText(row.get("SupplierName", "") if isinstance(row, dict) else "")
        self.state.setText(str(row.get("State", "")) if isinstance(row, dict) else "")
        self.blank.setText(str(row.get("Blank", "")) if isinstance(row, dict) else "")
        self.amount.setText(str(row.get("AMOUNT", "")) if isinstance(row, dict) else "")
        self.status.setText(str(row.get("STATUS", "")) if isinstance(row, dict) else "")
        self.eamount.setText(str(row.get("EAMOUNT", "")) if isinstance(row, dict) else "")
        self.lamount.setText(str(row.get("LAMOUNT", "")) if isinstance(row, dict) else "")
        self.tamount.setText(str(row.get("TAMOUNT", "")) if isinstance(row, dict) else "")
        self.netweight1.setText(str(row.get("NetWeight1", "")) if isinstance(row, dict) else "")
        self.lweight.setText(str(row.get("LWEIGHT", "")) if isinstance(row, dict) else "")
        self.eweight.setText(str(row.get("EWEIGHT", "")) if isinstance(row, dict) else "")
        loaded = row.get("LoadedWeight") if isinstance(row, dict) else row[5]
        empty = row.get("EmptyWeight") if isinstance(row, dict) else row[4]
        self.loaded_weight.setText(str(loaded) if loaded else "")
        self.empty_weight.setText(str(empty) if empty else "")
        if loaded and not empty:
            self.load_status.setCurrentText("Empty")
        elif empty and not loaded:
            self.load_status.setCurrentText("Loaded")
        else:
            self.load_status.setCurrentIndex(1)
        self.update_net_weight()

    def clear_fields(self):
        self.ticket_number_edit.clear()
        self.vehicle_number.clear()
        self.material.clear()
        self.supplier.clear()
        self.loaded_weight.clear()
        self.empty_weight.clear()
        self.net_weight.clear()
        self.state.clear()
        self.blank.clear()
        self.amount.clear()
        self.status.clear()
        self.eamount.clear()
        self.lamount.clear()
        self.tamount.clear()
        self.netweight1.clear()
        self.lweight.clear()
        self.eweight.clear()
        # IMPORTANT: do not clear self.current_ticket_number here!

    def get_weight_from_display(self):
        return random.randint(3000, 40000)

    def get_tare_weight(self):
        vehicle_number = self.vehicle_number.text().strip()
        if not vehicle_number:
            QMessageBox.warning(self, "Input Error", "Please enter the vehicle number first.")
            return
        try:
            row = fetch_one(
                'SELECT vehicletareweight FROM vehiclemaster WHERE vehiclenumber = %s',
                (vehicle_number,)
            )
            if row and (row.get("vehicletareweight") if isinstance(row, dict) else row[0]) is not None:
                tare = row.get("vehicletareweight") if isinstance(row, dict) else row[0]
                self.empty_weight.setText(str(tare))
                self.update_net_weight()
            else:
                QMessageBox.warning(self, "Not Found", f"No tare weight found for vehicle number {vehicle_number}.")
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Error retrieving tare weight:\n{e}")

    def handle_weigh(self):
        if self.weigh_locked:
            return
        live_weight = self.current_weight
        self.weight_display.setText(f"{live_weight} <span style='font-size:15pt'>kg</span>")
        if self.load_status.currentText().lower() == "loaded":
            self.loaded_weight.setText(str(live_weight))
        else:
            self.empty_weight.setText(str(live_weight))
        self.update_net_weight()
        self.weigh_locked = True

    def handle_save(self):
        try:
            dt_now = QDateTime.currentDateTime()
            if self.current_mode == "second":
                ticket_no = self.ticket_number_combo.currentText()
            else:
                ticket_no = self.ticket_number_edit.text()
            vehicle_no = self.vehicle_number.text()

            def float_or_none(val):
                s = val.strip()
                return float(s) if s else None

            loaded_weight = int(self.loaded_weight.text().strip()) if self.loaded_weight.text().strip() else None
            empty_weight = int(self.empty_weight.text().strip()) if self.empty_weight.text().strip() else None
            net_weight = int(self.net_weight.text().strip()) if self.net_weight.text().strip() else None

            material = self.material.text()
            supplier = self.supplier.text()
            shift = "B"

            state = self.state.text()
            blank = float_or_none(self.blank.text())
            amount = float_or_none(self.amount.text())
            status = self.status.text()
            eamount = float_or_none(self.eamount.text())
            lamount = float_or_none(self.lamount.text())
            tamount = float_or_none(self.tamount.text())
            netweight1 = float_or_none(self.netweight1.text())
            lweight = float_or_none(self.lweight.text())
            eweight = float_or_none(self.eweight.text())

            if self.current_mode == "second":
                pending = False
                closed = True
            else:
                pending = True
                closed = False
            exported = False

            date_str = dt_now.toPyDateTime()
            time_str = dt_now.toPyDateTime()
            empty_weight_date = date_str if empty_weight is not None else None
            empty_weight_time = time_str if empty_weight is not None else None
            load_weight_date = date_str if loaded_weight is not None else None
            load_weight_time = time_str if loaded_weight is not None else None

            sql = """
            INSERT INTO tickets (
                "TicketNumber", "VehicleNumber", "Date", "Time",
                "EmptyWeight", "LoadedWeight", "EmptyWeightDate", "EmptyWeightTime",
                "LoadWeightDate", "LoadWeightTime", "NetWeight", "Pending", "Closed", "Exported",
                "Shift", "Materialname", "SupplierName", "State", "Blank", "AMOUNT", "STATUS",
                "EAMOUNT", "LAMOUNT", "TAMOUNT", "NetWeight1", "LWEIGHT", "EWEIGHT"
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s
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
            ;
            """
            params = (
                int(ticket_no) if ticket_no else None, vehicle_no, date_str, time_str,
                empty_weight, loaded_weight, empty_weight_date, empty_weight_time,
                load_weight_date, load_weight_time, net_weight, pending, closed, exported,
                shift, material, supplier, state, blank, amount, status, eamount, lamount, tamount, netweight1, lweight, eweight
            )
            execute_query(sql, params)
            QMessageBox.information(
                self, "Saved",
                f'Ticket saved successfully on "{ticket_no}"'
            )
            # After saving, increment ticket number for next transaction
            if self.current_mode == "first":
                self.current_ticket_number = None
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to save ticket data:\n{e}")

    def handle_close_transaction(self):
        if self.current_mode == "second":
            ticket_no = self.ticket_number_combo.currentText()
        else:
            ticket_no = self.ticket_number_edit.text()
        vehicle_no = self.vehicle_number.text()
        if not ticket_no and not vehicle_no:
            QMessageBox.warning(self, "Input Error", "Enter either Ticket Number or Vehicle Number to close transaction.")
            return
        row = None
        if ticket_no:
            row = fetch_one('SELECT * FROM tickets WHERE "TicketNumber" = %s AND "Pending" = TRUE', (ticket_no,))
        elif vehicle_no:
            row = fetch_one('SELECT * FROM tickets WHERE "VehicleNumber" = %s AND "Pending" = TRUE', (vehicle_no,))
        if not row:
            QMessageBox.warning(self, "Not Found", "No pending ticket found for the given number.")
            return

        execute_query('UPDATE tickets SET "Pending" = FALSE, "Closed" = TRUE WHERE "TicketNumber" = %s',
                      (row["TicketNumber"] if isinstance(row, dict) else row[0],))
        QMessageBox.information(self, "Closed", "Ticket marked as completed (even if missing a weight).")
        self.show_second(ticket_row=row)

    def update_net_weight(self):
        try:
            loaded = int(self.loaded_weight.text().strip()) if self.loaded_weight.text().strip() else 0
            tare = int(self.empty_weight.text().strip()) if self.empty_weight.text().strip() else 0
            net = loaded - tare
            if loaded and tare:
                self.net_weight.setText(str(net if net >= 0 else 0))
            else:
                self.net_weight.setText("")
        except ValueError:
            self.net_weight.setText("")

    def check_pending_ticket_on_entry(self):
        try:
            vehicle_no = self.vehicle_number.text().strip()
            if not vehicle_no:
                return
            row = fetch_one('SELECT * FROM tickets WHERE "VehicleNumber" = %s AND "Pending" = TRUE', (vehicle_no,))
            if row:
                reply = QMessageBox.question(self, "Pending Ticket",
                    "There is a pending ticket for this vehicle.\nDo you want to continue with the second transaction?",
                    QMessageBox.Ok | QMessageBox.Cancel)
                if reply == QMessageBox.Ok:
                    self.show_second(ticket_row=row)
                else:
                    self.show_first()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred:\n{e}")

    def handle_cancel(self):
        self.clear_fields()
        self.current_weight = self.get_weight_from_display()
        self.weight_display.setText(f"{self.current_weight} <span style='font-size:15pt'>kg</span>")
        self.weigh_locked = False
        # Do NOT generate a new ticket number here; just restore the previous one
        self.show_first()

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    w = TicketWindow()
    w.show()
    sys.exit(app.exec_())
