import sys
from PyQt5.QtWidgets import (
    QWidget, QGroupBox, QVBoxLayout, QHBoxLayout, QGridLayout,
    QRadioButton, QLabel, QComboBox, QLineEdit, QPushButton, QTableWidget, QDialog,
    QTableWidgetItem, QSizePolicy, QCheckBox, QMessageBox, QDateEdit, QListWidget, QListWidgetItem
)
from PyQt5.QtCore import Qt, QDate
from psycopg2 import InternalError
from db_utils import fetch_all, fetch_one
from date_time_utils import to_db_date, to_display_date, to_display_time
from reportpreview import ReportPreviewDialog

# Helper: Get dynamic fields for each report type from DB (Unchanged)
def get_fields_for_report(report_type, extra_params=None):
    fields = []
    template_row = fetch_one("SELECT reporttemplatename FROM reporttemplate WHERE lower(reporttemplatename) = %s", (report_type.lower(),))
    if template_row:
        template_name = template_row["reporttemplatename"]
        detail_rows = fetch_all("SELECT fieldname FROM reportdetail WHERE reporttemplatename = %s", (template_name,))
        fields = [dr["fieldname"] for dr in detail_rows]
    if not fields:
        if report_type == "Ticket":
            fields = [
                "TicketNumber", "VehicleNumber", "Date", "Time", "EmptyWeight", "LoadedWeight",
                "EmptyWeightDate", "EmptyWeightTime", "LoadWeightDate", "LoadWeightTime",
                "NetWeight", "EAMOUNT", "LAMOUNT", "TAMOUNT"
            ]
        elif report_type == "Material":
            fields = ["materialcode", "materialname", "materialdescription"]
        elif report_type == "Supplier":
            fields = ["suppliercode", "suppliername", "supplieraddress", "contactperson", "contactnumber"]
    if extra_params:
        for param in extra_params:
            if param not in fields:
                fields.append(param)
    return fields

def generate_summary_row(rows, fields):
    """
    Generates a summary row for the report with custom aggregation logic.
    """
    if not rows:
        return None

    summary = {field: "" for field in fields}
    
    if "TicketNumber" in fields:
        summary["TicketNumber"] = f"COUNT: {len(rows)}"

    fields_to_sum = [
        "EmptyWeight", "LoadedWeight", "NetWeight", 
        "EAMOUNT", "LAMOUNT", "TAMOUNT", "AMOUNT"
    ]

    for field in fields_to_sum:
        if field in fields:
            total = 0
            for row in rows:
                try:
                    value = float(row.get(field, 0) or 0)
                    total += value
                except (ValueError, TypeError):
                    continue
            summary[field] = str(total)
            
    return summary

class ReportWindowForm(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Advanced Report Builder")
        self.setMinimumSize(1000, 700)

        self.filters = []
        self.last_query = ""
        self.last_params = []
        self.current_report_type = "Ticket"
        self.extra_params = []

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(6)

        # UI Setup (Unchanged)
        top_grid = QGridLayout()
        top_grid.setSpacing(10)
        reports_on_box = QGroupBox("1. Report On")
        reports_on_layout = QVBoxLayout()
        self.material_radio = QRadioButton("Material")
        self.supplier_radio = QRadioButton("Supplier")
        self.ticket_radio = QRadioButton("Ticket")
        self.ticket_radio.setChecked(True)
        reports_on_layout.addWidget(self.material_radio); reports_on_layout.addWidget(self.supplier_radio); reports_on_layout.addWidget(self.ticket_radio)
        reports_on_box.setLayout(reports_on_layout)
        top_grid.addWidget(reports_on_box, 0, 0, 2, 1)
        criteria_group = QGroupBox("2. Define Filter Criteria")
        criteria_layout = QGridLayout()
        criteria_layout.addWidget(QLabel("Field:"), 0, 0)
        self.selection_combo = QComboBox()
        criteria_layout.addWidget(self.selection_combo, 0, 1, 1, 2)
        self.all_radio = QRadioButton("Show All Records (No Filter)"); self.all_radio.setChecked(True)
        self.value_radio = QRadioButton("Filter by Value:")
        self.date_range_radio = QRadioButton("Filter by Date Range:")
        self.where_field = QLineEdit(); self.where_field.setPlaceholderText("Enter value")
        self.from_date_edit = QDateEdit(calendarPopup=True); self.from_date_edit.setDate(QDate.currentDate())
        self.to_date_edit = QDateEdit(calendarPopup=True); self.to_date_edit.setDate(QDate.currentDate())
        criteria_layout.addWidget(self.all_radio, 1, 0, 1, 3)
        criteria_layout.addWidget(self.value_radio, 2, 0); criteria_layout.addWidget(self.where_field, 2, 1, 1, 2)
        criteria_layout.addWidget(self.date_range_radio, 3, 0); criteria_layout.addWidget(QLabel("From:"), 3, 1); criteria_layout.addWidget(self.from_date_edit, 3, 2)
        criteria_layout.addWidget(QLabel("To:"), 4, 1); criteria_layout.addWidget(self.to_date_edit, 4, 2)
        criteria_group.setLayout(criteria_layout)
        top_grid.addWidget(criteria_group, 0, 1, 2, 1)
        filter_builder_group = QGroupBox("3. Build Your Query")
        filter_builder_layout = QVBoxLayout()
        self.or_btn = QPushButton("Add as OR Filter")
        self.and_btn = QPushButton("Add as AND Filter")
        self.filter_list_widget = QListWidget()
        self.clear_btn = QPushButton("Clear All Filters")
        add_btn_layout = QHBoxLayout()
        add_btn_layout.addWidget(self.and_btn); add_btn_layout.addWidget(self.or_btn)
        filter_builder_layout.addLayout(add_btn_layout)
        filter_builder_layout.addWidget(QLabel("Current Filters:"))
        filter_builder_layout.addWidget(self.filter_list_widget)
        filter_builder_layout.addWidget(self.clear_btn)
        filter_builder_group.setLayout(filter_builder_layout)
        top_grid.addWidget(filter_builder_group, 0, 2, 2, 1)
        main_layout.addLayout(top_grid)
        exec_group = QGroupBox("4. Get Results")
        exec_layout = QHBoxLayout()
        self.build_btn = QPushButton("Build SQL Query")
        self.onscreen_btn = QPushButton("Display On Screen")
        self.print_btn = QPushButton("Print Report")
        exec_layout.addWidget(self.build_btn); exec_layout.addWidget(self.onscreen_btn); exec_layout.addWidget(self.print_btn)
        exec_group.setLayout(exec_layout)
        main_layout.addWidget(exec_group)
        self.table = QTableWidget()
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        main_layout.addWidget(self.table)
        bottom_layout = QHBoxLayout()
        self.extra_field_input = QLineEdit(); self.extra_field_input.setPlaceholderText("Add extra column (e.g. TAMOUNT)")
        self.add_extra_field_btn = QPushButton("Add"); bottom_layout.addWidget(self.extra_field_input); bottom_layout.addWidget(self.add_extra_field_btn)
        bottom_layout.addStretch(1)
        self.without_lines_chk = QCheckBox("Without Lines")
        self.exit_btn = QPushButton("Exit")
        bottom_layout.addWidget(self.without_lines_chk); bottom_layout.addWidget(self.exit_btn)
        main_layout.addLayout(bottom_layout)

        # Signals (Unchanged)
        self.material_radio.toggled.connect(self.on_report_type_changed)
        self.supplier_radio.toggled.connect(self.on_report_type_changed)
        self.ticket_radio.toggled.connect(self.on_report_type_changed)
        self.and_btn.clicked.connect(lambda: self.add_filter('AND'))
        self.or_btn.clicked.connect(lambda: self.add_filter('OR'))
        self.clear_btn.clicked.connect(self.clear_filters)
        self.build_btn.clicked.connect(self.build_query)
        self.onscreen_btn.clicked.connect(self.display_data)
        self.print_btn.clicked.connect(self.print_report)
        self.exit_btn.clicked.connect(self.close)
        self.add_extra_field_btn.clicked.connect(self.add_extra_param)
        self.selection_combo.currentTextChanged.connect(self.on_field_changed)
        
        self.on_report_type_changed()

    def add_filter(self, connector):
        # This function is unchanged
        field = self.selection_combo.currentText()
        if not field:
            QMessageBox.warning(self, "No Field", "Please select a field to filter by.")
            return
        new_filter = {'connector': connector, 'field': field}
        if self.value_radio.isChecked():
            value = self.where_field.text().strip()
            if not value:
                QMessageBox.warning(self, "No Value", "Please enter a value for the filter.")
                return
            new_filter['operator'] = '='
            new_filter['value'] = value
        elif self.date_range_radio.isChecked():
            from_date = self.from_date_edit.date()
            to_date = self.to_date_edit.date()
            if from_date > to_date:
                QMessageBox.warning(self, "Invalid Range", "The 'From' date cannot be after the 'To' date.")
                return
            new_filter['operator'] = 'BETWEEN'
            new_filter['values'] = (to_db_date(from_date), to_db_date(to_date))
        else:
            QMessageBox.information(self, "Information", "Cannot add a filter when 'Show All Records' is selected.")
            return
        if not self.filters:
            new_filter['connector'] = ''
        self.filters.append(new_filter)
        self.update_filter_list_widget()

    def update_filter_list_widget(self):
        # This function is unchanged
        self.filter_list_widget.clear()
        for f in self.filters:
            if f['operator'] == 'BETWEEN':
                text = f"{f['connector']} {f['field']} {f['operator']} {f['values'][0]} AND {f['values'][1]}"
            else:
                text = f"{f['connector']} {f['field']} {f['operator']} '{f['value']}'"
            self.filter_list_widget.addItem(text.strip())

    def clear_filters(self):
        # This function is unchanged
        self.filters.clear()
        self.filter_list_widget.clear()
        self.last_query = ""
        self.last_params = []

    def build_query(self):
        # This function is unchanged
        if self.current_report_type == "Ticket": table = "tickets"
        elif self.current_report_type == "Material": table = "material"
        elif self.current_report_type == "Supplier": table = "suppliers"
        else: return
        query = f"SELECT * FROM {table}"
        params = []
        where_clauses = []
        if self.all_radio.isChecked() or not self.filters:
            self.last_query = query
            self.last_params = []
            QMessageBox.information(self, "Query Built", "Query will select all records.\n\n" + query)
            return
        for f in self.filters:
            field, op = f['field'], f['operator']
            clause = f'{f["connector"]} "{field}" {op} '
            if op == 'BETWEEN':
                clause += '%s AND %s'
                params.extend(f['values'])
            else:
                clause += '%s'
                params.append(f['value'])
            where_clauses.append(clause)
        query += " WHERE " + " ".join(where_clauses)
        self.last_query = query
        self.last_params = params
        QMessageBox.information(self, "Query Built Successfully", "The following query has been prepared:\n\n" + self.last_query)

    def display_data(self):
        # This function is unchanged
        self.build_query()
        if not self.last_query:
            QMessageBox.warning(self, "No Query", "Please build a query first.")
            return
        try:
            rows = fetch_all(self.last_query, tuple(self.last_params))
            fields = get_fields_for_report(self.current_report_type, extra_params=self.extra_params)
            self.table.setRowCount(len(rows))
            self.table.setColumnCount(len(fields))
            self.table.setHorizontalHeaderLabels(fields)
            for r, row in enumerate(rows):
                for c, field in enumerate(fields):
                    value = row.get(field)
                    if 'date' in field.lower():
                        item_text = to_display_date(value)
                    elif 'time' in field.lower():
                        item_text = to_display_time(value)
                    else:
                        item_text = "" if value is None else str(value)
                    self.table.setItem(r, c, QTableWidgetItem(item_text))
            QMessageBox.information(self, "Success", f"{len(rows)} records displayed.")
        except InternalError as e:
            if "current transaction is aborted" in str(e):
                QMessageBox.critical(self, "Database Transaction Error", 
                                     "The database connection is in an error state from a previous failed command.\n\n"
                                     "Please restart the application to establish a new connection.")
            else:
                QMessageBox.critical(self, "Database Internal Error", f"An unexpected internal database error occurred.\nError: {e}")
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to fetch data.\nError: {e}\nQuery: {self.last_query}")

    def on_field_changed(self, field_name):
        # This function is unchanged
        is_date_field = 'date' in field_name.lower()
        self.date_range_radio.setEnabled(is_date_field)
        self.from_date_edit.setEnabled(is_date_field)
        self.to_date_edit.setEnabled(is_date_field)
        if not is_date_field and self.date_range_radio.isChecked():
            self.value_radio.setChecked(True)

    def add_extra_param(self):
        # This function is unchanged
        param = self.extra_field_input.text().strip()
        if param and param not in self.extra_params:
            self.extra_params.append(param)
            self.on_report_type_changed()
            self.extra_field_input.clear()

    def on_report_type_changed(self):
        # This function is unchanged
        if self.material_radio.isChecked(): self.current_report_type = "Material"
        elif self.supplier_radio.isChecked(): self.current_report_type = "Supplier"
        else: self.current_report_type = "Ticket"
        self.clear_filters()
        fields = get_fields_for_report(self.current_report_type, extra_params=self.extra_params)
        self.selection_combo.clear()
        self.selection_combo.addItems(fields)
        self.table.setColumnCount(len(fields))
        self.table.setHorizontalHeaderLabels(fields)
        self.table.setRowCount(0)
        self.on_field_changed(self.selection_combo.currentText())

    def print_report(self):
        self.build_query()
        if not self.last_query:
            QMessageBox.warning(self, "No Query", "Please build a query before printing.")
            return

        template_row = fetch_one('SELECT reporttemplatename FROM reporttemplate WHERE "Default" = %s', (True,))
        if not template_row:
            QMessageBox.warning(self, "No template", "No default template found.")
            return

        template_name = template_row["reporttemplatename"]
        detail_rows = fetch_all("SELECT fieldname, fieldcaption FROM reportdetail WHERE reporttemplatename = %s", (template_name,))
        col_fields = [dr["fieldname"] for dr in detail_rows]
        col_captions = [dr["fieldcaption"] for dr in detail_rows]

        for param in self.extra_params:
            if param not in col_fields:
                col_fields.append(param); col_captions.append(param)
        
        try:
            data_rows = fetch_all(self.last_query, tuple(self.last_params))
            
            # Generate the summary row
            summary_row = generate_summary_row(data_rows, col_fields)
            
            # --- MODIFICATION: Append the summary to the data list and remove the keyword argument ---
            if summary_row:
                data_rows.append(summary_row)
            
            preview = ReportPreviewDialog(
                title=template_name, 
                col_captions=col_captions, 
                rows=data_rows, 
                col_fields=col_fields, 
                # summary_data argument is removed to prevent the error
                parent=self
            )
            preview.exec_()
            
        except InternalError as e:
            if "current transaction is aborted" in str(e):
                QMessageBox.critical(self, "Database Transaction Error", 
                                     "The database connection is in an error state from a previous failed command.\n\n"
                                     "Please restart the application to establish a new connection.")
            else:
                QMessageBox.critical(self, "Database Internal Error", f"An unexpected internal database error occurred.\nError: {e}")
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to fetch data for printing.\nError: {e}\nQuery: {self.last_query}")
