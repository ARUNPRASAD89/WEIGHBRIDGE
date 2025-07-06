from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QApplication
from PyQt5.QtGui import QPixmap, QPainter
from PyQt5.QtCore import Qt
from ticket_printer import get_default_template_name, get_template_spec_from_db, _draw_ticket

def print_pixmap_on_printer(pixmap, parent=None):
    from PyQt5.QtPrintSupport import QPrinter, QPrintDialog
    printer = QPrinter(QPrinter.HighResolution)
    printer.setPaperSize(QPrinter.A4)
    printer.setFullPage(True)
    dlg = QPrintDialog(printer, parent)
    if dlg.exec_() != QPrintDialog.Accepted:
        return
    painter = QPainter(printer)
    rect = painter.viewport()
    img = pixmap.toImage()
    # Scale image to page size (fit to page)
    scaled_img = img.scaled(rect.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
    x = (rect.width() - scaled_img.width()) // 2
    y = (rect.height() - scaled_img.height()) // 2
    painter.drawImage(x, y, scaled_img)
    painter.end()

class TicketPreviewWidget(QLabel):
    def __init__(self, template_fields, ticket_data, ticket_width_mm, ticket_height_mm, parent=None):
        super().__init__(parent)
        dpi = 96
        px_width = int(ticket_width_mm * dpi / 25.4)
        px_height = int(ticket_height_mm * dpi / 25.4)
        pixmap = QPixmap(px_width, px_height)
        pixmap.fill(Qt.white)
        painter = QPainter(pixmap)
        from ticket_printer import _draw_ticket
        _draw_ticket(
            painter,
            template_fields,
            ticket_data,
            ticket_width_mm,
            ticket_height_mm,
            page_width_mm=ticket_width_mm,
            page_height_mm=ticket_height_mm
        )
        painter.end()
        self.setPixmap(pixmap)
        self.setAlignment(Qt.AlignCenter)

class TicketPreviewDialog(QDialog):
    def __init__(self, ticket_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ticket Preview (Default Template)")
        self.setMinimumSize(700, 500)
        layout = QVBoxLayout(self)
        template_name = get_default_template_name()
        ticket_width_mm, ticket_height_mm, template_fields = get_template_spec_from_db(template_name)
        self.template_fields = template_fields
        self.ticket_data = ticket_data
        self.ticket_width_mm = ticket_width_mm
        self.ticket_height_mm = ticket_height_mm

        self.ticket_widget = TicketPreviewWidget(
            template_fields, ticket_data, ticket_width_mm, ticket_height_mm, self
        )
        layout.addWidget(self.ticket_widget)

        btn_layout = QHBoxLayout()
        print_btn = QPushButton("Print", self)
        print_btn.clicked.connect(self.print_ticket)
        btn_layout.addWidget(print_btn)
        close_btn = QPushButton("Close", self)
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def print_ticket(self):
        # Render ticket as high-res pixmap for printing
        dpi = 300
        page_width_mm = 210  # A4
        page_height_mm = 297
        px_width = int(page_width_mm * dpi / 25.4)
        px_height = int(page_height_mm * dpi / 25.4)
        pixmap = QPixmap(px_width, px_height)
        pixmap.fill(Qt.white)
        painter = QPainter(pixmap)
        _draw_ticket(
            painter,
            self.template_fields,
            self.ticket_data,
            self.ticket_width_mm,
            self.ticket_height_mm,
            page_width_mm=page_width_mm,
            page_height_mm=page_height_mm
        )
        painter.end()
        print_pixmap_on_printer(pixmap, parent=self)

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    # Example ticket data dictionary
    ticket_data = {
        "TicketNumber": "123456",
        "VehicleNumber": "TN12AB1234",
        "Date": "2025-07-03",
        "Time": "16:10",
        "EmptyWeight": "8000",
        "LoadedWeight": "15000",
        "NetWeight": "7000",
        "EAMOUNT": "60",
        "LAMOUNT": "",
        "TAMOUNT": "60",
        "SupplierName": "ABC Suppliers",
        "Materialname": "Iron Ore",
        "State": "TN",
        "STATUS": "Empty",
    }
    dlg = TicketPreviewDialog(ticket_data)
    dlg.exec_()
