from PyQt5.QtPrintSupport import QPrinter, QPrintDialog, QPrintPreviewDialog
from PyQt5.QtGui import QPainter, QFont, QPixmap
from PyQt5.QtCore import QRect, Qt
from db_utils import fetch_one, execute_query
from scale_utils import scale_template_fields

def mm_to_px(mm, dpi=96):
    return int(mm * dpi / 25.4)

def get_template_spec_from_db(template_name):
    template_row = fetch_one(
        "SELECT ticketwidth, ticketheight FROM templatemaster WHERE templatename=%s",
        (template_name,)
    )
    if not template_row:
        raise Exception(f"Template '{template_name}' not found in DB.")
    ticket_width_mm, ticket_height_mm = float(template_row[0]), float(template_row[1])
    field_rows = execute_query(
        "SELECT fieldname, x, y, width, height, fontname, fontsize FROM templatefields WHERE templatename=%s ORDER BY id",
        (template_name,)
    )
    template_fields = []
    for row in field_rows:
        template_fields.append({
            'fieldname': row[0],
            'x': float(row[1]),
            'y': float(row[2]),
            'width': float(row[3]),
            'height': float(row[4]),
            'fontname': row[5],
            'fontsize': int(row[6])
        })
    return ticket_width_mm, ticket_height_mm, template_fields

def get_default_template_name():
    row = fetch_one("SELECT templatename FROM templatemaster WHERE defaulttemplate=TRUE")
    if not row:
        raise Exception("No default template set in templatemaster.")
    return row[0]

def print_ticket_from_template(
    template_name,
    ticket_data,
    parent=None,
    preview=False,
    export_pdf_path=None
):
    ticket_width_mm, ticket_height_mm, template_fields = get_template_spec_from_db(template_name)
    render_ticket_with_data(
        template_fields=template_fields,
        ticket_data=ticket_data,
        ticket_width_mm=ticket_width_mm,
        ticket_height_mm=ticket_height_mm,
        parent=parent,
        preview=preview,
        export_pdf_path=export_pdf_path
    )

def print_ticket_using_default_template(
    ticket_data,
    parent=None,
    preview=False,
    export_pdf_path=None
):
    template_name = get_default_template_name()
    ticket_width_mm, ticket_height_mm, template_fields = get_template_spec_from_db(template_name)
    a4_width_mm, a4_height_mm = 210, 297
    scaled_fields = scale_template_fields(
        template_fields, ticket_width_mm, ticket_height_mm, a4_width_mm, a4_height_mm
    )
    render_ticket_with_data(
        template_fields=scaled_fields,
        ticket_data=ticket_data,
        ticket_width_mm=a4_width_mm,
        ticket_height_mm=a4_height_mm,
        parent=parent,
        preview=preview,
        export_pdf_path=export_pdf_path
    )

def render_ticket_with_data(
    template_fields,
    ticket_data,
    ticket_width_mm,
    ticket_height_mm,
    parent=None,
    preview=False,
    export_pdf_path=None
):
    printer = QPrinter(QPrinter.HighResolution)
    printer.setFullPage(True)
    printer.setPageMargins(0, 0, 0, 0, QPrinter.Millimeter)
    printer.setPaperSize(QPrinter.A4)

    a4_width_mm = 210
    a4_height_mm = 297

    def do_draw(printer_obj):
        painter = QPainter(printer_obj)
        _draw_ticket(
            painter,
            template_fields,
            ticket_data,
            ticket_width_mm,
            ticket_height_mm,
            page_width_mm=a4_width_mm,
            page_height_mm=a4_height_mm
        )
        painter.end()

    if export_pdf_path:
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(export_pdf_path)
        painter = QPainter(printer)
        _draw_ticket(
            painter,
            template_fields,
            ticket_data,
            ticket_width_mm,
            ticket_height_mm,
            page_width_mm=a4_width_mm,
            page_height_mm=a4_height_mm
        )
        painter.end()
    elif preview:
        dlg = QPrintPreviewDialog(printer, parent)
        dlg.paintRequested.connect(do_draw)
        dlg.exec_()
    else:
        if not export_pdf_path:
            dlg = QPrintDialog(printer, parent)
            if dlg.exec_() != QPrintDialog.Accepted:
                return
        painter = QPainter(printer)
        _draw_ticket(
            painter,
            template_fields,
            ticket_data,
            ticket_width_mm,
            ticket_height_mm,
            page_width_mm=a4_width_mm,
            page_height_mm=a4_height_mm
        )
        painter.end()

def _draw_ticket(
    painter,
    template_fields,
    ticket_data,
    ticket_width_mm=None,
    ticket_height_mm=None,
    page_width_mm=210,
    page_height_mm=297
):
    painter.save()
    offset_x = mm_to_px((page_width_mm - ticket_width_mm) / 2)
    offset_y = mm_to_px((page_height_mm - ticket_height_mm) / 2)
    if ticket_width_mm and ticket_height_mm:
        painter.setPen(Qt.red)
        painter.drawRect(
            offset_x,
            offset_y,
            mm_to_px(ticket_width_mm),
            mm_to_px(ticket_height_mm)
        )
        painter.setPen(Qt.black)
    for field in template_fields:
        x_mm = float(field['x'])
        y_mm = float(field['y'])
        w_mm = float(field['width'])
        h_mm = float(field['height'])
        field_name = field['fieldname']
        font = QFont(field['fontname'], int(field['fontsize']))
        x = mm_to_px(x_mm) + offset_x
        y = mm_to_px(y_mm) + offset_y
        w = mm_to_px(w_mm)
        h = mm_to_px(h_mm)
        text = str(ticket_data.get(field_name, ""))
        painter.setFont(font)
        painter.drawText(QRect(x, y, w, h), Qt.AlignLeft | Qt.AlignVCenter, text)
    painter.restore()

# --- WYSIWYG Print from Preview ---

def print_pixmap_on_printer(pixmap, parent=None):
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
