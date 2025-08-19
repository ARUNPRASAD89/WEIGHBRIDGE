import re
import win32api
import win32con
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit, QComboBox, QPushButton,
    QFrame, QSizePolicy, QSpacerItem, QDialog, QMessageBox
)
from PyQt5.QtGui import QFont, QPalette, QColor
from PyQt5.QtCore import Qt, QDateTime, QDate, QTime, QLocale, pyqtSlot
from db_utils import execute_query, fetch_one, fetch_all
from date_time_utils import to_db_date, to_db_time, to_display_date, to_display_time  # FIX: import display helpers
from serial_manager import SerialManager

def blank_to_none(val):
    if val in ("", None):
        return None
    try:
        return int(val)
    except Exception:
        return None

def get_tablemaster_fields():
    rows = fetch_all("""
        SELECT fieldcaption, fieldname, fieldsize, fieldtype, mandatory, tablename
        FROM tablemaster
        ORDER BY id
    """)
    return rows

def get_supplier_details(suppliername):
    row = fetch_one("SELECT suppliercode, supplieraddress, contactperson, contactnumber FROM suppliers WHERE suppliername=%s", (suppliername,))
    return row if row else {}

def get_combo_values(tablename, fieldname):
    if not tablename or not fieldname:
        return []
    if tablename.lower() == "suppliers":
        rows = fetch_all("SELECT suppliername FROM suppliers ORDER BY suppliername")
        return [r["suppliername"] for r in rows]
    if tablename.lower() == "vehiclemaster":
        rows = fetch_all("SELECT vehiclenumber FROM vehiclemaster ORDER BY vehiclenumber")
        return [r["vehiclenumber"] for r in rows]
    if tablename.lower() == "material":
        rows = fetch_all("SELECT materialname FROM material ORDER BY materialname")
        return [r["materialname"] for r in rows]
    rows = fetch_all(f"SELECT * FROM {tablename} ORDER BY 1")
    if not rows:
        return []
    first_field = list(rows[0].keys())[0]
    return [r[first_field] for r in rows]

def get_material_details(materialname):
    row = fetch_one("SELECT materialcode, materialdescription FROM material WHERE materialname=%s", (materialname,))
    return row if row else {}

def get_ticketdatatemplate_fields():
    rows = fetch_all("""
        SELECT controlcaption, controlname, controltype, controlarrid
        FROM ticketdatatemplate
        WHERE controltable='Tickets'
        ORDER BY controlarrid
    """)
    return rows

def apply_formulas(params):
    formulas = fetch_all("SELECT strformulaname, formulalist FROM formulatable")
    local_vars = {k.lower(): v for k, v in params.items()}
    for f in formulas:
        field_name = f["strformulaname"]
        formula = f["formulalist"]
        try:
            result = eval(formula, {}, local_vars)
            params[field_name] = result
        except Exception as e:
            print(f"Error calculating formula '{field_name}': {e}")
    return params

def clean_integer_fields(params):
    """
    Converts blank string or None for all integer fields in tickets table to Python None.
    Dynamically fetches integer columns from DB schema.
    """
    rows = fetch_all("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name='tickets'
    """)
    int_fields = [r["column_name"] for r in rows if r["data_type"] in ("integer", "bigint", "smallint")]
    for field in int_fields:
        if field in params:
            val = params[field]
            if val in ("", None):
                params[field] = None
            else:
                try:
                    params[field] = int(val)
                except Exception:
                    params[field] = None
    return params

class BaseTransactionWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ticket")
        self.setMinimumSize(940, 600)

        # --- COLOR PALETTE ---
        self.primary_color = "#3498db"   # Blue
        self.secondary_color = "#e74c3c" # Red
        self.accent_color = "#f39c12"    # Orange
        self.bg_color = "#ecf0f1"       # Light Gray
        self.text_color = "#2c3e50"      # Dark Blue-Gray

        # --- APPLY STYLESHEET ---
        self.setStyleSheet(f"""
            QWidget {{
                background: {self.bg_color};
                color: {self.text_color};
                font-family: Arial;
                font-size: 11pt;
            }}
            QLabel {{
                font-weight: bold;
            }}
            QPushButton {{
                background: {self.primary_color};
                color: white;
                border-radius: 5px;
                padding: 8px;
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{
                background: {self.accent_color};
            }}
            QComboBox {{
                background: white;
                border: 1px solid #bdc3c7;
                border-radius: 3px;
                padding: 6px;
            }}
            QLineEdit {{
                background: white;
                border: 1px solid #bdc3c7;
                border-radius: 3px;
                padding: 6px;
            }}
            QFrame[frameShape="4"] {{ /* QFrame.StyledPanel */
                border: 1px solid #bdc3c7;
                border-radius: 5px;
            }}
        """)

        self.system_locale = QLocale.system()
        self.date_format = QLocale.system().dateFormat(QLocale.ShortFormat)
        self.time_format = "HH:mm:ss"

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(0)

        # --- LEFT: Transaction Type Menu ---
        side_menu = QVBoxLayout()
        side_menu.setSpacing(24)
        side_menu.setContentsMargins(0, 0, 10, 0)

        self.btn_single = QPushButton("Single\nTransaction")
        self.btn_first = QPushButton("First\nTransaction")
        self.btn_second = QPushButton("Second\nTransaction")
        for btn in (self.btn_single, self.btn_first, self.btn_second):
            btn.setFixedSize(120, 60)
            btn.setFont(QFont("Arial", 10, QFont.Bold))
            btn.setStyleSheet("text-align:left; padding-left:32px;")
        side_menu.addWidget(self.btn_single)
        side_menu.addWidget(self.btn_first)
        side_menu.addWidget(self.btn_second)
        side_menu.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        main_layout.addLayout(side_menu)

        # --- RIGHT: Main UI Area ---
        right_area = QVBoxLayout()
        right_area.setSpacing(2)
        right_area.setContentsMargins(0, 0, 0, 0)

        # HEADER
        header = QHBoxLayout()
        header.setSpacing(10)
        self.lbl_shift = QLabel("Shift  B")
        self.lbl_shift.setFont(QFont("Arial", 11, QFont.Bold))
        self.lbl_shift.setFixedWidth(70)
        header.addWidget(self.lbl_shift, alignment=Qt.AlignLeft)

        self.lbl_title = QLabel("Vehicle  Transaction")
        self.lbl_title.setFont(QFont("Arial", 15, QFont.Bold))
        self.lbl_title.setStyleSheet(f"color:{self.primary_color};")
        header.addWidget(self.lbl_title, alignment=Qt.AlignHCenter)

        # DateTime in blue, aligned top right
        self.lbl_datetime = QLabel()
        self.lbl_datetime.setFont(QFont("Arial", 10, QFont.Bold))
        self.lbl_datetime.setStyleSheet(f"color:{self.primary_color};")
        header.addStretch(1)
        header.addWidget(self.lbl_datetime, alignment=Qt.AlignRight | Qt.AlignTop)

        self.weight_display = QLabel("0")
        self.weight_display.setFont(QFont("Arial", 38, QFont.Bold))
        self.weight_display.setStyleSheet("background:#111;color:white;padding:0 30px;border-radius:5px;min-width:180px;")
        self.weight_display.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        header.addWidget(self.weight_display)
        kg_label = QLabel("kg")
        kg_label.setFont(QFont("Arial", 18, QFont.Bold))
        kg_label.setStyleSheet("color:#111;")
        header.addWidget(kg_label)
        right_area.addLayout(header)

        # --- FORM FIELDS ---
        form_area = QHBoxLayout()
        form_area.setSpacing(8)

        # MANDATORY FIELDS
        mand_frame = QFrame()
        mand_frame.setFrameShape(QFrame.StyledPanel)
        self.mand_grid = QGridLayout(mand_frame)
        self.mand_grid.setHorizontalSpacing(12)
        self.mand_grid.setVerticalSpacing(10)
        self.lbl_mand = QLabel("Mandatory Fields")
        self.lbl_mand.setFont(QFont("Arial", 10, QFont.Bold))
        self.mand_grid.addWidget(self.lbl_mand, 0, 0, 1, 2)
        self.mandatory_widgets = {}

        # Build mandatory fields (aligned as per screenshot)
        mand_row = 1
        label_width = 150  # Consistent label width
        field_width = 200  # Consistent field width

        # ... inside BaseTransactionWindow.__init__() where mandatory fields are built
        for f in get_tablemaster_fields():
            fieldcaption = f["fieldcaption"]
            fieldname = f["fieldname"]
            fieldtype = f["fieldtype"] or "text"
            fieldsize = f["fieldsize"] or 50
            mandatory = f["mandatory"]
            tablename = f["tablename"]
            # Skip removed fields: date, time, suppliername (one)
            if fieldname.lower() in ["date", "time", "suppliername"]:
                continue

            if mandatory:
                label = QLabel(fieldcaption)
                label.setFixedWidth(label_width)
                label.setFont(QFont("Arial", 10))

                if fieldname == "Materialname":
                    widget = QComboBox()
                    widget.setEditable(False)
                    widget.setFixedWidth(field_width)
                    # ADD a blank placeholder so nothing is selected by default
                    widget.addItem("")  # <-- placeholder
                    widget.addItems(get_combo_values("material", "materialname"))
                    widget.setCurrentIndex(0)  # ensure blank is selected
                    widget.currentTextChanged.connect(self.on_material_changed)
                elif fieldtype.lower() == "combo":
                    widget = QComboBox()
                    widget.setEditable(False)
                    widget.setFixedWidth(field_width)
                    # Optional: you can also add a blank here if you want combos unselected by default
                    # widget.addItem("")
                    widget.addItems(get_combo_values(tablename, fieldname))
                else:
                    widget = QLineEdit()
                    widget.setFixedWidth(field_width)

                self.mand_grid.addWidget(label, mand_row, 0)
                self.mand_grid.addWidget(widget, mand_row, 1)
                self.mandatory_widgets[fieldname] = widget
                mand_row += 1

        form_area.addWidget(mand_frame, stretch=3, alignment=Qt.AlignTop)

        # CUSTOM FIELDS from ticketdatatemplate
        cust_frame = QFrame()
        cust_frame.setFrameShape(QFrame.StyledPanel)
        self.cust_grid = QGridLayout(cust_frame)
        self.cust_grid.setHorizontalSpacing(12)
        self.cust_grid.setVerticalSpacing(10)
        lbl_cust = QLabel("Custom Fields")
        lbl_cust.setFont(QFont("Arial", 10, QFont.Bold))
        self.cust_grid.addWidget(lbl_cust, 0, 0, 1, 2)
        self.custom_widgets = {}

        cust_row = 1
        label_width = 150  # Consistent label width
        field_width = 200  # Consistent field width

        for f in get_ticketdatatemplate_fields():
            fieldcaption = f["controlcaption"]
            fieldname = f["controlname"]
            fieldtype = f["controltype"] or "text"

            label = QLabel(fieldcaption)
            label.setFixedWidth(label_width)  # Consistent label width
            label.setFont(QFont("Arial", 10))

            if fieldtype.lower() == "combo":
                widget = QComboBox()
                widget.setEditable(False)
                widget.setFixedWidth(field_width)
                widget.addItem("")  # You may add options here if applicable
            else:
                widget = QLineEdit()
                widget.setFixedWidth(field_width)

            self.cust_grid.addWidget(label, cust_row, 0)
            self.cust_grid.addWidget(widget, cust_row, 1)
            self.custom_widgets[fieldname] = widget
            cust_row += 1

        form_area.addWidget(cust_frame, stretch=2, alignment=Qt.AlignTop)
        right_area.addLayout(form_area)

        # --- OPERATIONS BAR ---
        operations = QHBoxLayout()
        operations.setSpacing(8)
        operations.setContentsMargins(0, 16, 0, 0)
        self.btn_weigh = QPushButton("Weigh")
        self.btn_save = QPushButton("Save")
        self.btn_preview = QPushButton("Preview")
        self.btn_print = QPushButton("Print")
        self.btn_dosprint = QPushButton("DOS Print")
        self.btn_export = QPushButton("Export")
        self.btn_search = QPushButton("Search")
        self.btn_exit = QPushButton("Exit")
        for btn in [
            self.btn_weigh, self.btn_save, self.btn_preview, self.btn_print,
            self.btn_dosprint, self.btn_export, self.btn_search, self.btn_exit
        ]:
            btn.setFont(QFont("Arial", 10, QFont.Bold))
            btn.setFixedSize(90, 48)
        operations.addWidget(self.btn_weigh)
        operations.addWidget(self.btn_save)
        operations.addWidget(self.btn_preview)
        operations.addWidget(self.btn_print)
        operations.addWidget(self.btn_dosprint)
        operations.addWidget(self.btn_export)
        operations.addWidget(self.btn_search)
        operations.addWidget(self.btn_exit)
        #right_area.addLayout(operations) #comment the line
        # Use a container widget + layout for centering
        op_widget = QWidget()
        op_widget.setLayout(operations)
        op_layout = QHBoxLayout()
        op_layout.addStretch(1)
        op_layout.addWidget(op_widget)
        op_layout.addStretch(1)
        right_area.addLayout(op_layout)

        main_layout.addLayout(right_area, stretch=1)

        # Connections
        self.btn_single.clicked.connect(self.open_single_transaction)
        self.btn_first.clicked.connect(self.open_first_transaction)
        self.btn_second.clicked.connect(self.open_second_transaction)
        # IMPORTANT: Do NOT connect Save here; subclasses handle Save click to avoid double execution
        # self.btn_save.clicked.connect(self.save_ticket)
        self.btn_exit.clicked.connect(self.return_to_main_menu)

        # Show initial current datetime in blue
        self.update_datetime_label()

        # PATCH: Enable live formula calculation for custom fields
        self.setup_formula_autocalc()

        # --- SERIAL PORT INTEGRATION ---
        self.serial_manager = SerialManager(self)
        self.serial_manager.weight_updated.connect(self.update_live_weight)
        self.serial_manager.error_occurred.connect(self.show_serial_error)
        self.serial_manager.start()

    @pyqtSlot(str)
    def update_live_weight(self, weight):
        """Updates the weight display label with data from the serial port."""
        self.weight_display.setText(weight)

    @pyqtSlot(str)
    def show_serial_error(self, message):
        """Shows a non-blocking message box for serial port errors."""
        QMessageBox.warning(self, "Serial Port Error", message)

    def closeEvent(self, event):
        """Ensure the serial manager thread is stopped cleanly on window close."""
        self.serial_manager.stop()
        super().closeEvent(event)

    def update_datetime_label(self):
        now = QDateTime.currentDateTime()
        date_str = now.date().toString(self.date_format)
        time_str = now.time().toString(self.time_format)
        self.lbl_datetime.setText(f"{date_str} {time_str}")

    def update_date_time(self):
        # Not used for display now, only for updates in subclasses if needed
        pass

    def display_ticket_date_time(self, db_date, db_time, date_widget=None, time_widget=None):
        """Show DB date/time in localized display format in the UI/print/search."""
        if date_widget is not None:
            date_widget.setText(to_display_date(db_date))
        if time_widget is not None:
            time_widget.setText(to_display_time(db_time))
        return to_display_date(db_date), to_display_time(db_time)

    # --- PROPERTY ACCESSORS FOR MANDATORY FIELDS ---
    @property
    def ticket_number(self):
        return self.mandatory_widgets.get("TicketNumber")
    @property
    def vehicle_number(self):
        return self.mandatory_widgets.get("VehicleNumber")
    @property
    def load_status(self):
        return self.mandatory_widgets.get("LoadStatus")
    @property
    def material(self):
        return self.mandatory_widgets.get("Materialname")
    @property
    def supplier(self):
        return self.mandatory_widgets.get("Supplier")  # Supplier, not SupplierName
    @property
    def loaded_weight(self):
        return self.mandatory_widgets.get("LoadedWeight")
    @property
    def empty_weight(self):
        return self.mandatory_widgets.get("EmptyWeight")
    @property
    def net_weight(self):
        return self.mandatory_widgets.get("NetWeight")

    def get_custom_widget(self, name):
        return self.custom_widgets.get(name)

    def on_material_changed(self, materialname):
        pass

    def detect_weighbridge_event(self, params):
        """
        Returns: 'empty', 'load', or 'both'
        """
        empty = params.get("EmptyWeight") not in ("", None)
        load = params.get("LoadedWeight") not in ("", None)
        if empty and load:
            return "both"
        elif empty:
            return "empty"
        elif load:
            return "load"
        return None

    def convert_db_date_time_for_display(self, db_date, db_time):
        """Convert DB ISO date/time to localized display format for UI/print/search."""
        ui_date = to_display_date(db_date)
        ui_time = to_display_time(db_time)
        return ui_date, ui_time

    def collect_ticket_params(self):
        params = {}
        for k, widget in self.mandatory_widgets.items():
            if isinstance(widget, QComboBox):
                params[k] = widget.currentText()
            else:
                params[k] = widget.text()
        # Add material details
        materialname = params.get("Materialname", "")
        details = get_material_details(materialname)
        params["MaterialCode"] = details.get("materialcode", "")
        custom_fields = fetch_all("""
            SELECT controlname, controltype FROM ticketdatatemplate
            WHERE controltable='Tickets'
            ORDER BY controlarrid
        """)
        for field in custom_fields:
            fname = field["controlname"]
            ftype = field["controltype"]
            widget = self.custom_widgets.get(fname)
            if not widget:
                continue
            if ftype.lower() == "combo":
                params[fname] = widget.currentText()
            else:
                params[fname] = widget.text()
        params.update({
            "Closed": False,
            "Exported": False,
        })
        return params

    def setup_formula_autocalc(self):
        formulas = fetch_all("SELECT strformulaname, formulalist FROM formulatable")
        self.formula_map = {}
        self.formula_deps = {}
        for f in formulas:
            target = f['strformulaname']
            formula = f['formulalist']
            self.formula_map[target] = formula
            deps = set(re.findall(r'\b\w+\b', formula))
            deps = [d for d in deps if not d.isdigit() and d not in ['+', '-', '*', '/', '(', ')']]
            self.formula_deps[target] = deps

        for target, deps in self.formula_deps.items():
            for dep in deps:
                dep_widget = self.custom_widgets.get(dep)
                target_widget = self.custom_widgets.get(target)
                if dep_widget and target_widget:
                    dep_widget.textChanged.connect(lambda _, t=target: self.update_formula_field(t))

        for target in self.formula_map:
            self.update_formula_field(target)

    def update_formula_field(self, target_field):
        formula = self.formula_map.get(target_field)
        if not formula:
            return
        local_vars = {}
        for fname, widget in self.custom_widgets.items():
            try:
                val = widget.text()
                if val.strip() == "":
                    val = 0
                else:
                    try:
                        val = int(val)
                    except ValueError:
                        try:
                            val = float(val)
                        except ValueError:
                            pass
                local_vars[fname.lower()] = val
                local_vars[fname] = val
            except Exception:
                local_vars[fname] = 0
        try:
            result = eval(formula, {}, local_vars)
            self.custom_widgets[target_field].setText(str(result))
        except Exception as e:
            self.custom_widgets[target_field].setText("")

    def save_ticket(self, extra_params=None):
        print("[BaseTransactionWindow.save_ticket] Called")
        params = {}
        for k, widget in self.mandatory_widgets.items():
            if isinstance(widget, QComboBox):
                params[k] = widget.currentText()
            else:
                params[k] = widget.text()
            print(f"  Mandatory widget: {k} = {params[k]!r}")
        # Add material details
        materialname = params.get("Materialname", "")
        details = get_material_details(materialname)
        params["MaterialCode"] = details.get("materialcode", "")
        custom_fields = fetch_all("""
            SELECT controlname, controltype FROM ticketdatatemplate
            WHERE controltable='Tickets'
            ORDER BY controlarrid
        """)
        for field in custom_fields:
            fname = field["controlname"]
            ftype = field["controltype"]
            widget = self.custom_widgets.get(fname)
            if not widget:
                continue
            if ftype.lower() == "combo":
                params[fname] = widget.currentText()
            else:
                params[fname] = widget.text()
            print(f"  Custom widget: {fname} = {params[fname]!r}")

        params = apply_formulas(params)

        if extra_params:
            print(f"  Merging extra_params: {extra_params}")
            params.update(extra_params)

        # --- PATCH: Clean all integer fields dynamically ---
        params = clean_integer_fields(params)

        def get_ticket_columns():
            print("  Fetching ticket columns from DB")
            rows = fetch_all("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='tickets'
            """)
            cols = set(r["column_name"] for r in rows)
            print(f"  Columns found: {cols}")
            return cols

        ticket_columns = get_ticket_columns()
        # PATCH: Do not exclude any field, insert/update all fields that exist in the table
        filtered_params = {k: v for k, v in params.items() if k in ticket_columns}
        print(f"  Filtered params for DB: {filtered_params}")

        set_clause = ", ".join([f'"{k}" = %({k})s' for k in filtered_params.keys()])
        insert_columns = ', '.join([f'"{k}"' for k in filtered_params.keys()])
        insert_values = ', '.join([f'%({k})s' for k in filtered_params.keys()])
        query = f"""
        INSERT INTO tickets ({insert_columns})
        VALUES ({insert_values})
        ON CONFLICT ("TicketNumber") DO UPDATE SET {set_clause}
        """
        print("  Final query for execute_query:")
        print(query)

        print("  Executing query with params:")
        for k, v in filtered_params.items():
            print(f"    {k}: {v!r}")

        execute_query(query, filtered_params)
        print("[BaseTransactionWindow.save_ticket] Finished")

    # Utility: clear fields
    def clear_non_essential_fields(self, essentials=("TicketNumber", "LoadStatus")):
        """
        Clears all text fields except the ones listed in 'essentials'.
        For QComboBox, resets to index 0 unless the field is essential.
        """
        # Mandatory widgets
        for name, widget in self.mandatory_widgets.items():
            if widget is None:
                continue
            if name in essentials:
                # Reset essentials to a safe default without clearing their existence
                if isinstance(widget, QLineEdit):
                    widget.clear()
                elif isinstance(widget, QComboBox):
                    try:
                        widget.setCurrentIndex(0)
                    except Exception:
                        pass
                continue
            if isinstance(widget, QLineEdit):
                widget.clear()
            elif isinstance(widget, QComboBox):
                try:
                    widget.setCurrentIndex(0)
                except Exception:
                    pass
        # Custom widgets
        for name, widget in self.custom_widgets.items():
            if widget is None:
                continue
            if isinstance(widget, QLineEdit):
                widget.clear()
            elif isinstance(widget, QComboBox):
                try:
                    widget.setCurrentIndex(0)
                except Exception:
                    pass
        # Reset weight display
        try:
            self.weight_display.setText("0")
        except Exception:
            pass

    # RE-ADDED: navigation helpers so signal connections work
    def open_single_transaction(self):
        from single_transaction_window import SingleTransactionWindow
        self.next_window = SingleTransactionWindow(parent=self)
        self.next_window.show()
        self.hide()

    def open_first_transaction(self):
        from first_transaction_window import FirstTransactionWindow
        self.next_window = FirstTransactionWindow(parent=self)
        self.next_window.show()
        self.hide()

    def open_second_transaction(self):
        from second_transaction_window import SecondTransactionWindow
        self.next_window = SecondTransactionWindow(parent=self)
        self.next_window.show()
        self.hide()

    def return_to_main_menu(self):
        parent = self.parent()
        if parent:
            parent.show()
        self.close()
