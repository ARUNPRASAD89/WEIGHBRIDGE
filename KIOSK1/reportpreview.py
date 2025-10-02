import sys, csv, os, math
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QWidget, QLabel, QSizePolicy,
    QFileDialog, QMessageBox, QComboBox, QSpinBox, QAbstractScrollArea, QScrollArea
)
# Corrected import for printing classes
from PyQt5.QtPrintSupport import QPrintDialog, QPrinter
from PyQt5.QtGui import QPainter, QFont, QFontMetrics, QPalette
from PyQt5.QtCore import Qt, QRectF, QSize

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

class PreviewCanvas(QWidget):
    """A widget that uses a QPainter to draw a preview of a single report page."""
    def __init__(self, parent_dialog):
        super().__init__(parent_dialog)
        self.dlg = parent_dialog
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet("background-color: white;")

    def paintEvent(self, event):
        if not self.dlg.is_ready:
            return

        p = QPainter(self)
        try:
            # The dialog now handles scaling and pagination, just tell it to paint
            self.dlg.paint_page(p, self.dlg.current_page)
        finally:
            p.end()

    def sizeHint(self):
        # Provide a size hint based on the scaled page dimensions
        if self.dlg and self.dlg.is_ready:
            return self.dlg.get_page_size_px()
        return QSize(800, 600)

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
                 page_height_mm=297.0, # Added for pagination
                 top_margin_mm=10.0,
                 left_margin_mm=10.0,
                 parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Report Preview - {title}")
        self.setMinimumSize(1000, 800)
        self.is_ready = False

        # --- Store all data and settings ---
        self.report_title = title
        self.col_captions = col_captions
        self.rows = rows
        self.col_fields = col_fields
        self.field_layout = field_layout
        self.summary_data = summary_data

        # --- Layout & Font Properties ---
        self.header_font_size = header_font_size
        self.detail_font_size = detail_font_size
        self.summary_font_size = detail_font_size
        self.header_font_name = header_font_name
        self.detail_font_name = detail_font_name
        self.line_height_mm = line_height_mm
        self.page_width_mm = page_width_mm
        self.page_height_mm = page_height_mm
        self.top_margin_mm = top_margin_mm
        self.left_margin_mm = left_margin_mm
        self.right_margin_mm = left_margin_mm
        self.bottom_margin_mm = top_margin_mm # Assume symmetric margins

        # --- Pagination & Zoom state ---
        self.current_page = 1
        self.total_pages = 1
        self.page_row_counts = [] # Stores number of rows on each page
        self.zoom_factor = 1.0

        # --- UI Setup ---
        self._setup_ui()
        self._setup_connections()

        # --- Finalize ---
        self.is_ready = True
        self.recalculate_and_redraw()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        control_row = QHBoxLayout()

        # --- Page Navigation & Zoom ---
        control_row.addWidget(QLabel("Page:"))
        self.prev_page_btn = QPushButton("<"); self.prev_page_btn.setFixedWidth(30)
        self.page_label = QLabel("1 / 1"); self.page_label.setFixedWidth(50)
        self.next_page_btn = QPushButton(">"); self.next_page_btn.setFixedWidth(30)
        control_row.addWidget(self.prev_page_btn); control_row.addWidget(self.page_label); control_row.addWidget(self.next_page_btn)
        control_row.addSpacing(20)
        control_row.addWidget(QLabel("Zoom:"))
        self.zoom_combo = QComboBox(); self.zoom_combo.addItems(["50%", "75%", "100%", "125%", "150%", "200%"]); self.zoom_combo.setCurrentText("100%")
        control_row.addWidget(self.zoom_combo)
        control_row.addSpacing(20)

        # --- Font Size Controls ---
        control_row.addWidget(QLabel("Header:"))
        self.header_font_spin = QSpinBox(); self.header_font_spin.setRange(5, 72); self.header_font_spin.setValue(self.header_font_size)
        control_row.addWidget(self.header_font_spin)
        control_row.addWidget(QLabel("Detail:"))
        self.detail_font_spin = QSpinBox(); self.detail_font_spin.setRange(5, 72); self.detail_font_spin.setValue(self.detail_font_size)
        control_row.addWidget(self.detail_font_spin)
        control_row.addStretch(1)

        # --- Action Buttons ---
        self.export_btn = QPushButton("Export..."); self.print_btn = QPushButton("Print..."); self.close_btn = QPushButton("Close")
        control_row.addWidget(self.export_btn); control_row.addWidget(self.print_btn); control_row.addWidget(self.close_btn)
        main_layout.addLayout(control_row)

        # --- Canvas in a Scroll Area for Zooming ---
        self.canvas = PreviewCanvas(self)
        self.scroll_area = QScrollArea()
        self.scroll_area.setBackgroundRole(QPalette.Dark)
        self.scroll_area.setWidget(self.canvas)
        self.scroll_area.setWidgetResizable(True)
        main_layout.addWidget(self.scroll_area, 1)

    def _setup_connections(self):
        self.header_font_spin.valueChanged.connect(self.adjust_header_size)
        self.detail_font_spin.valueChanged.connect(self.adjust_detail_size)
        self.zoom_combo.currentTextChanged.connect(self.adjust_zoom)
        self.prev_page_btn.clicked.connect(self.prev_page)
        self.next_page_btn.clicked.connect(self.next_page)
        self.export_btn.clicked.connect(self.export_data)
        self.print_btn.clicked.connect(self.print_report_with_dialog)
        self.close_btn.clicked.connect(self.accept)

    # --- Core Logic ---

    def recalculate_and_redraw(self):
        """Recalculates pagination and updates the view. The main update method."""
        if not self.is_ready: return
        self._calculate_pagination()
        self.update_page_controls()
        self.redraw()

    def redraw(self):
        """Forces a repaint of the canvas."""
        if not self.is_ready: return
        self.canvas.updateGeometry() # Recalculate size hint
        self.canvas.update()

    def _calculate_pagination(self):
        """Calculates how many rows fit on each page."""
        # Use a dummy widget to get DPI without a visible canvas
        metrics_widget = QWidget()
        header_font = QFont(self.header_font_name, self.header_font_size, QFont.Bold)
        detail_font = QFont(self.detail_font_name, self.detail_font_size)
        
        def mm_to_px(mm): return mm * (metrics_widget.logicalDpiY() / 25.4)

        line_px = mm_to_px(self.line_height_mm)
        header_h = max(QFontMetrics(header_font).height(), line_px)
        detail_h = max(QFontMetrics(detail_font).height(), line_px)
        
        page_h_px = mm_to_px(self.page_height_mm)
        margins_h_px = mm_to_px(self.top_margin_mm + self.bottom_margin_mm)
        available_h = page_h_px - margins_h_px
        
        self.page_row_counts = []
        rows_on_this_page = 0
        current_y = header_h
        
        if not self.rows:
            self.total_pages = 1
            self.page_row_counts.append(0)
            return

        for _ in self.rows:
            if current_y + detail_h > available_h:
                self.page_row_counts.append(rows_on_this_page)
                rows_on_this_page = 0
                current_y = header_h
            rows_on_this_page += 1
            current_y += detail_h

        # Add the last page
        if rows_on_this_page > 0:
            self.page_row_counts.append(rows_on_this_page)

        self.total_pages = len(self.page_row_counts)
        if self.current_page > self.total_pages:
            self.current_page = self.total_pages

    def paint_page(self, painter: QPainter, page_number: int):
        """Paints a single page of the report using the given painter."""
        painter.save()

        # --- Setup Fonts and Metrics ---
        header_font = QFont(self.header_font_name, self.header_font_size, QFont.Bold)
        detail_font = QFont(self.detail_font_name, self.detail_font_size)
        summary_font = QFont(self.detail_font_name, self.summary_font_size, QFont.Bold)
        
        def mm_to_px(mm, is_y=False):
            dpi = painter.device().logicalDpiY() if is_y else painter.device().logicalDpiX()
            return mm * (dpi / 25.4)

        # Apply zoom
        painter.scale(self.zoom_factor, self.zoom_factor)

        # --- Calculate Dimensions ---
        line_px = mm_to_px(self.line_height_mm, True)
        header_h = max(QFontMetrics(header_font).height(), line_px)
        detail_h = max(QFontMetrics(detail_font).height(), line_px)
        summary_h = max(QFontMetrics(summary_font).height(), line_px)
        
        top_margin_px = mm_to_px(self.top_margin_mm, True)
        left_margin_px = mm_to_px(self.left_margin_mm)
        
        page_w_mm = self.page_width_mm - self.left_margin_mm - self.right_margin_mm
        page_w_px = mm_to_px(page_w_mm)

        y_cursor = top_margin_px

        # --- Draw Header ---
        painter.setFont(header_font)
        x_cursor = left_margin_px
        for i, caption in enumerate(self.col_captions):
            width_mm = float(self.field_layout[i].get("width", 20.0))
            width_px = mm_to_px(width_mm)
            painter.drawText(QRectF(x_cursor, y_cursor, width_px, header_h), Qt.AlignLeft | Qt.AlignVCenter, str(caption))
            x_cursor += width_px
        y_cursor += header_h
        
        # --- Draw Detail Rows for the current page ---
        if self.page_row_counts:
            start_row_index = sum(self.page_row_counts[:page_number - 1])
            rows_to_draw = self.page_row_counts[page_number - 1]
            page_rows = self.rows[start_row_index : start_row_index + rows_to_draw]

            painter.setFont(detail_font)
            for row_data in page_rows:
                x_cursor = left_margin_px
                for i, field_name in enumerate(self.col_fields):
                    val = row_data.get(field_name, "")
                    width_mm = float(self.field_layout[i].get("width", 20.0))
                    width_px = mm_to_px(width_mm)
                    painter.drawText(QRectF(x_cursor, y_cursor, width_px, detail_h), Qt.AlignLeft | Qt.AlignVCenter, "" if val is None else str(val))
                    x_cursor += width_px
                y_cursor += detail_h

        # --- Draw Summary (only on the last page) ---
        if self.summary_data and page_number == self.total_pages:
            painter.setFont(summary_font)
            y_cursor += int(detail_h * 0.4) # Small gap
            x_cursor = left_margin_px
            for i, field_name in enumerate(self.col_fields):
                txt = self.summary_data.get(field_name, "")
                width_mm = float(self.field_layout[i].get("width", 20.0))
                width_px = mm_to_px(width_mm)
                painter.drawText(QRectF(x_cursor, y_cursor, width_px, summary_h), Qt.AlignLeft | Qt.AlignVCenter, txt)
                x_cursor += width_px

        painter.restore()

    # --- Event Handlers & Slots ---

    def adjust_header_size(self, size):
        self.header_font_size = size
        self.recalculate_and_redraw()

    def adjust_detail_size(self, size):
        self.detail_font_size = size
        self.summary_font_size = size
        self.recalculate_and_redraw()

    def adjust_zoom(self, text):
        self.zoom_factor = float(text.replace('%', '')) / 100.0
        self.redraw()

    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.update_page_controls()
            self.redraw()

    def next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.update_page_controls()
            self.redraw()
            
    def update_page_controls(self):
        self.page_label.setText(f"{self.current_page} / {self.total_pages}")
        self.prev_page_btn.setEnabled(self.current_page > 1)
        self.next_page_btn.setEnabled(self.current_page < self.total_pages)

    def get_page_size_px(self):
        # Returns the target page size in pixels, scaled by the zoom factor
        if not self.is_ready: return QSize(1,1)
        # Use a dummy widget to get DPI if needed
        dpi_x = self.logicalDpiX()
        dpi_y = self.logicalDpiY()
        width_px = self.page_width_mm * (dpi_x / 25.4) * self.zoom_factor
        height_px = self.page_height_mm * (dpi_y / 25.4) * self.zoom_factor
        return QSize(int(width_px), int(height_px))
        
    def print_report_with_dialog(self):
        """Opens a QPrintDialog and prints the entire report if accepted."""
        printer = QPrinter(QPrinter.HighResolution)
        printer.setPageSize(QPrinter.A4) # Sensible default
        printer.setOrientation(QPrinter.Portrait if self.page_height_mm > self.page_width_mm else QPrinter.Landscape)
        
        dialog = QPrintDialog(printer, self)
        if dialog.exec_() == QDialog.Accepted:
            painter = QPainter()
            # Start painting on the printer device
            if painter.begin(printer):
                # Temporarily set zoom to 100% for printing
                original_zoom = self.zoom_factor
                self.zoom_factor = 1.0
                
                for page in range(1, self.total_pages + 1):
                    if page > 1:
                        printer.newPage()
                    # Paint the page onto the printer's painter
                    self.paint_page(painter, page)
                
                painter.end()
                # Restore original zoom for the screen preview
                self.zoom_factor = original_zoom
                QMessageBox.information(self, "Success", "Report sent to the printer.")
            else:
                QMessageBox.critical(self, "Printing Error", "Could not start painting on the selected printer.")

    # --- Data Export ---
    def _get_table_data_as_list(self):
        header = self.col_captions
        data = [header]
        for r_data in self.rows:
            row = [r_data.get(field, "") for field in self.col_fields]
            data.append(row)
        if self.summary_data:
            summary_row = [self.summary_data.get(field, "") for field in self.col_fields]
            data.append(summary_row)
        return data

    def export_data(self):
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self, "Export Report", f"{self.report_title.replace(' ', '_')}.csv",
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
        doc = SimpleDocTemplate(file_path, pagesize=landscape(letter) if self.page_width_mm > self.page_height_mm else letter)
        data = self._get_table_data_as_list()
        pdf_table = Table(data)
        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey), ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12), ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ])
        pdf_table.setStyle(style); elements = [pdf_table]; doc.build(elements)
