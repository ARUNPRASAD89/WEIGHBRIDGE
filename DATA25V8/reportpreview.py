from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QPushButton, QHBoxLayout, QMessageBox
)

class ReportPreviewDialog(QDialog):
    def __init__(self, title, col_captions, rows, col_fields, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Report Output Preview")
        self.setFixedSize(1000, 600)
        layout = QVBoxLayout(self)
        # Header Info
        top_label = QLabel(f"{title}")
        top_label.setStyleSheet("font-size:22px; font-weight:bold; margin-bottom:12px;")
        layout.addWidget(top_label)
        top_label = QLabel(f"{title}")
        layout.addWidget(top_label)

        # Table
        table = QTableWidget()
        table.setColumnCount(len(col_captions))
        table.setHorizontalHeaderLabels(col_captions)
        table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, field in enumerate(col_fields):
                value = row.get(field, "")
                item = QTableWidgetItem(str(value))
                table.setItem(r, c, item)
        layout.addWidget(table)

        # Totals row
        if col_fields and rows:
            totals_row = []
            for field in col_fields:
                try:
                    total = sum(float(row.get(field, 0)) for row in rows if str(row.get(field, "")).replace(".","",1).isdigit())
                    if total:
                        totals_row.append(f"{total:,.2f}")
                    else:
                        totals_row.append("")
                except Exception:
                    totals_row.append("")
            total_table = QTableWidget(1, len(totals_row))
            total_table.setHorizontalHeaderLabels(col_captions)
            for c, val in enumerate(totals_row):
                total_table.setItem(0, c, QTableWidgetItem(val))
            layout.addWidget(total_table)

        # Export, Print, Close buttons
        btn_layout = QHBoxLayout()
        self.export_btn = QPushButton("Export")
        self.print_btn = QPushButton("Print")
        self.close_btn = QPushButton("Close")
        btn_layout.addWidget(self.export_btn)
        btn_layout.addWidget(self.print_btn)
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)

        self.close_btn.clicked.connect(self.close)
        self.export_btn.clicked.connect(self.export_report)
        self.print_btn.clicked.connect(self.print_report)

    def export_report(self):
        # Implement export logic (CSV, Excel, etc.)
        QMessageBox.information(self, "Export", "Export functionality not yet implemented.")

    def print_report(self):
        # Implement print logic
        QMessageBox.information(self, "Print", "Print functionality not yet implemented.")
