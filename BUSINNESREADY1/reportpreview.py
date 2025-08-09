import sys, csv, os, math
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QWidget, QLabel, QSizePolicy,
    QFileDialog, QMessageBox
)
from PyQt5.QtGui import QPainter, QFont, QFontMetrics
from PyQt5.QtCore import Qt, QRectF

# --- EXPORTING LIBRARIES (requires pip install openpyxl reportlab) ---
try:
    from openpyxl import Workbook
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
    CAN_EXPORT_EXCEL = True
    CAN_EXPORT_PDF = True
except ImportError:
    CAN_EXPORT_EXCEL = False
    CAN_EXPORT_PDF = False
    
# --- Assumed import for the direct printing function ---
# Make sure print_report_win32.py is available in your project.
try:
    from print_report_win32 import print_report_with_template
except ImportError:
    # Provide a fallback if the module is not found
    def print_report_with_template(**kwargs):
        raise ImportError("The 'print_report_with_template' function could not be found.")

class PreviewCanvas(QWidget):
    """A widget that uses a QPainter to draw a preview of the report."""
    def __init__(self, parent_dialog):
        super().__init__(parent_dialog)
        self.dlg = parent_dialog
        self.setMinimumSize(900, 600)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet("background-color: white;")

    def paintEvent(self, event):
        p = QPainter(self)
        try:
            self.dlg.paint_with_painter(p, self)
        finally:
            p.end()

class ReportPreviewDialog(QDialog):
    def __init__(self, title, col_captions, rows, col_fields,
                 field_layout,
                 summary_data=None,
                 header_font_size=10,
                 detail_font_size=8,
                 line_height_mm=7.0,
                 header_font_name="Arial",
                 detail_font_name="Arial",
                 page_width_mm=210.0,
                 top_margin_mm=10.0,
                 left_margin_mm=10.0,
                 parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Report Preview - {title}")
        self.setMinimumSize(1000, 800)

        # Data properties
        self.report_title = title
        self.col_captions = col_captions
        self.rows = rows
        self.col_fields = col_fields
        self.field_layout = field_layout
        self.summary_data = summary_data

        # Layout and Font properties
        self.header_font_size = header_font_size
        self.detail_font_size = detail_font_size
        self.summary_font_size = max(5, detail_font_size) # Make summary same as detail by default
        self.header_font_name = header_font_name
        self.detail_font_name = detail_font_name
        self.line_height_mm = line_height_mm
        self.page_width_mm = page_width_mm
        self.top_margin_mm = top_margin_mm
        self.left_margin_mm = left_margin_mm
        # Assume right margin is same as left for simplicity
        self.right_margin_mm = left_margin_mm

        main_layout = QVBoxLayout(self)
        
        # --- UI Controls from both versions ---
        control_row = QHBoxLayout()

        # Size adjustment controls
        control_row.addWidget(QLabel("Header:"))
        self.header_minus = QPushButton("-"); self.header_minus.setFixedWidth(30)
        self.header_plus = QPushButton("+"); self.header_plus.setFixedWidth(30)
        control_row.addWidget(self.header_minus)
        control_row.addWidget(self.header_plus)

        control_row.addWidget(QLabel("Detail:"))
        self.detail_minus = QPushButton("-"); self.detail_minus.setFixedWidth(30)
        self.detail_plus = QPushButton("+"); self.detail_plus.setFixedWidth(30)
        control_row.addWidget(self.detail_minus)
        control_row.addWidget(self.detail_plus)

        control_row.addWidget(QLabel("Summary:"))
        self.summary_minus = QPushButton("-"); self.summary_minus.setFixedWidth(30)
        self.summary_plus = QPushButton("+"); self.summary_plus.setFixedWidth(30)
        control_row.addWidget(self.summary_minus)
        control_row.addWidget(self.summary_plus)

        self.autofit_btn = QPushButton("Auto-Fit Width")
        self.autofit_btn.setCheckable(True)
        self.autofit_btn.setChecked(True)
        control_row.addWidget(self.autofit_btn)

        control_row.addStretch(1)

        # Action buttons
        self.export_btn = QPushButton("Export...")
        self.print_btn = QPushButton("Print")
        self.close_btn = QPushButton("Close")
        control_row.addWidget(self.export_btn)
        control_row.addWidget(self.print_btn)
        control_row.addWidget(self.close_btn)

        main_layout.addLayout(control_row)

        self.canvas = PreviewCanvas(self)
        main_layout.addWidget(self.canvas, 1)

        # --- Connections ---
        self.header_minus.clicked.connect(lambda: self.adjust_size("header", -1))
        self.header_plus.clicked.connect(lambda: self.adjust_size("header", 1))
        self.detail_minus.clicked.connect(lambda: self.adjust_size("detail", -1))
        self.detail_plus.clicked.connect(lambda: self.adjust_size("detail", 1))
        self.summary_minus.clicked.connect(lambda: self.adjust_size("summary", -1))
        self.summary_plus.clicked.connect(lambda: self.adjust_size("summary", 1))
        self.autofit_btn.clicked.connect(self.redraw)
        
        self.export_btn.clicked.connect(self.export_data)
        self.print_btn.clicked.connect(self.print_report)
        self.close_btn.clicked.connect(self.accept)

    def adjust_size(self, which, delta):
        if which == "header":
            self.header_font_size = max(5, self.header_font_size + delta)
        elif which == "detail":
            self.detail_font_size = max(5, self.detail_font_size + delta)
        elif which == "summary":
            self.summary_font_size = max(5, self.summary_font_size + delta)
        self.redraw()

    def redraw(self):
        self.canvas.update()
        
    def mm_to_px(self, canvas, mm, is_y=False):
        dpi = canvas.logicalDpiY() if is_y else canvas.logicalDpiX()
        return mm * (dpi / 25.4)

    def paint_with_painter(self, painter: QPainter, canvas: QWidget):
        # Determine scaling factor if auto-fit is enabled
        total_width_mm = sum(float(f.get("width", 20.0)) for f in self.field_layout)
        available_width_mm = self.page_width_mm - self.left_margin_mm - self.right_margin_mm
        scale = 1.0
        if self.autofit_btn.isChecked() and total_width_mm > 0:
            scale = available_width_mm / total_width_mm
        
        # --- Draw Header ---
        header_font = QFont(self.header_font_name, self.header_font_size, QFont.Bold)
        painter.setFont(header_font)
        header_metrics = QFontMetrics(header_font)
        y_cursor_px = self.mm_to_px(canvas, self.top_margin_mm, is_y=True)
        line_height_px = self.mm_to_px(canvas, self.line_height_mm, is_y=True)
        header_height_px = max(header_metrics.height(), line_height_px)
        
        x_cursor_mm = self.left_margin_mm
        for i, fld_layout in enumerate(self.field_layout):
            caption = self.col_captions[i]
            x_px = self.mm_to_px(canvas, x_cursor_mm)
            width_mm = float(fld_layout.get("width", 20.0)) * scale
            width_px = self.mm_to_px(canvas, width_mm)
            painter.drawText(QRectF(x_px, y_cursor_px, width_px, header_height_px), Qt.AlignLeft | Qt.AlignVCenter, str(caption))
            x_cursor_mm += width_mm
        y_cursor_px += header_height_px

        # --- Draw Detail Rows ---
        detail_font = QFont(self.detail_font_name, self.detail_font_size)
        painter.setFont(detail_font)
        detail_metrics = QFontMetrics(detail_font)
        detail_line_height_px = max(detail_metrics.height(), line_height_px)

        for row in self.rows:
            x_cursor_mm = self.left_margin_mm
            for idx, fld_layout in enumerate(self.field_layout):
                field_name = self.col_fields[idx]
                val = row.get(field_name, "")
                x_px = self.mm_to_px(canvas, x_cursor_mm)
                width_mm = float(fld_layout.get("width", 20.0)) * scale
                width_px = self.mm_to_px(canvas, width_mm)
                painter.drawText(QRectF(x_px, y_cursor_px, width_px, detail_line_height_px), Qt.AlignLeft | Qt.AlignVCenter, "" if val is None else str(val))
                x_cursor_mm += width_mm
            y_cursor_px += detail_line_height_px

        # --- Draw Summary Row ---
        if self.summary_data:
            summary_font = QFont(self.detail_font_name, self.summary_font_size, QFont.Bold)
            painter.setFont(summary_font)
            summary_metrics = QFontMetrics(summary_font)
            summary_height_px = max(summary_metrics.height(), line_height_px)
            y_cursor_px += int(detail_line_height_px * 0.4) # Small gap before summary
            
            x_cursor_mm = self.left_margin_mm
            for idx, fld_layout in enumerate(self.field_layout):
                field_name = self.col_fields[idx]
                txt = self.summary_data.get(field_name, "")
                x_px = self.mm_to_px(canvas, x_cursor_mm)
                width_mm = float(fld_layout.get("width", 20.0)) * scale
                width_px = self.mm_to_px(canvas, width_mm)
                painter.drawText(QRectF(x_px, y_cursor_px, width_px, summary_height_px), Qt.AlignLeft | Qt.AlignVCenter, txt)
                x_cursor_mm += width_mm

    def print_report(self):
        try:
            print_report_with_template(
                title=self.report_title,
                rows=self.rows,
                summary_data=self.summary_data
            )
            QMessageBox.information(self, "Success", "Report has been sent to the default printer.")
        except Exception as e:
            QMessageBox.critical(self, "Printing Error", f"Failed to print report:\n{e}")

    def _get_table_data_as_list(self):
        header = self.col_captions
        data = [header]
        # Add data rows
        for r_data in self.rows:
            row = [r_data.get(field, "") for field in self.col_fields]
            data.append(row)
        # Add summary row
        if self.summary_data:
            summary_row = [self.summary_data.get(field, "") for field in self.col_fields]
            data.append(summary_row)
        return data

    def export_data(self):
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self, 
            "Export Report", 
            f"{self.report_title.replace(' ', '_')}.csv",
            "CSV Files (*.csv);;Excel Files (*.xlsx);;PDF Files (*.pdf)"
        )
        if not file_path: return
        try:
            if 'csv' in selected_filter: self._export_to_csv(file_path)
            elif 'xlsx' in selected_filter: self._export_to_excel(file_path)
            elif 'pdf' in selected_filter: self._export_to_pdf(file_path)
            QMessageBox.information(self, "Success", f"Report successfully exported to:\n{file_path}")
        except Exception as e: QMessageBox.critical(self, "Export Error", f"An error occurred during export:\n{e}")

    def _export_to_csv(self, file_path):
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerows(self._get_table_data_as_list())

    def _export_to_excel(self, file_path):
        if not CAN_EXPORT_EXCEL: raise ImportError("The 'openpyxl' library is required. Please run: pip install openpyxl")
        wb = Workbook(); ws = wb.active; ws.title = self.report_title[:30]
        for row_data in self._get_table_data_as_list(): ws.append(row_data)
        wb.save(file_path)

    def _export_to_pdf(self, file_path):
        if not CAN_EXPORT_PDF: raise ImportError("The 'reportlab' library is required. Please run: pip install reportlab")
        doc = SimpleDocTemplate(file_path, pagesize=landscape(letter)); elements = []
        data = self._get_table_data_as_list()
        pdf_table = Table(data)
        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey), ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12), ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ])
        pdf_table.setStyle(style); elements.append(pdf_table); doc.build(elements)
