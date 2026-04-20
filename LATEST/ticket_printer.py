from PyQt5.QtPrintSupport import QPrinter, QPrintDialog, QPrintPreviewDialog
from PyQt5.QtGui import QPainter, QFont, QPixmap
from PyQt5.QtCore import QRect, Qt
from db_utils import fetch_one, execute_query, get_new_connection
from scale_utils import scale_template_fields
from resource_helpers import resolve_resource, debug_candidates
import os

# Use the Win32-backed print helper for silent/native printing
try:
    from print_ticket_with_template_win32 import print_ticket_with_template as win32_print_ticket
except Exception:
    win32_print_ticket = None


def mm_to_px(mm, dpi=96):
    return int(mm * dpi / 25.4)


def get_template_spec_from_db(template_name):
    template_row = fetch_one(
        "SELECT ticketwidth, ticketheight FROM templatemaster WHERE templatename=%s",
        (template_name,)
    )
    if not template_row:
        raise Exception(f"Template '{template_name}' not found in DB.")
    ticket_width_mm, ticket_height_mm = float(template_row['ticketwidth']), float(template_row['ticketheight'])
    field_rows = execute_query(
        "SELECT fieldname, x, y, width, height, fontname, fontsize, fontstyle FROM templatefields WHERE templatename=%s ORDER BY id",
        (template_name,)
    )
    template_fields = []
    for row in field_rows:
        template_fields.append({
            'fieldname': row['fieldname'],
            'x': float(row['x']),
            'y': float(row['y']),
            'width': float(row['width']),
            'height': float(row['height']),
            'fontname': row.get('fontname'),
            'fontsize': int(row.get('fontsize') or 10),
            'fontstyle': row.get('fontstyle') or 'normal'
        })
    return ticket_width_mm, ticket_height_mm, template_fields


def get_default_template_name():
    row = fetch_one("SELECT templatename FROM templatemaster WHERE defaulttemplate=TRUE")
    if not row:
        raise Exception("No default template set in templatemaster.")
    return row['templatename']


def print_ticket_from_template(
    template_name,
    ticket_data,
    parent=None,
    preview=False,
    export_pdf_path=None,
    silent=False,
    printer_name: str = None
):
    ticket_width_mm, ticket_height_mm, template_fields = get_template_spec_from_db(template_name)
    render_ticket_with_data(
        template_fields=template_fields,
        ticket_data=ticket_data,
        ticket_width_mm=ticket_width_mm,
        ticket_height_mm=ticket_height_mm,
        parent=parent,
        preview=preview,
        export_pdf_path=export_pdf_path,
        silent=silent,
        printer_name=printer_name
    )


def print_ticket_using_default_template(
    ticket_data,
    parent=None,
    preview=False,
    export_pdf_path=None,
    silent=False,
    printer_name: str = None
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
        export_pdf_path=export_pdf_path,
        silent=silent,
        printer_name=printer_name
    )


def render_ticket_with_data(
    template_fields,
    ticket_data,
    ticket_width_mm,
    ticket_height_mm,
    parent=None,
    preview=False,
    export_pdf_path=None,
    silent=False,
    printer_name: str = None
):
    """
    Render and optionally print a ticket.
    """
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

    # export to PDF file (no print dialog)
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
        return

    # preview mode uses the preview dialog (no immediate print job)
    if preview:
        dlg = QPrintPreviewDialog(printer, parent)
        dlg.paintRequested.connect(do_draw)
        dlg.exec_()
        return

    # silent printing: prefer using the Win32 wrapper if available (ensures native, silent print)
    if silent:
        if win32_print_ticket:
            try:
                conn = get_new_connection()
                win32_print_ticket(ticket_data, conn=conn, printer_name=printer_name)
                return
            except Exception:
                # If Win32 printing fails for any reason, fall back to QPrinter-based silent draw below.
                pass

        if printer_name:
            try:
                printer.setPrinterName(printer_name)
            except Exception:
                pass
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
        return

    # Default interactive printing (show QPrintDialog)
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
    """
    DPI-aware drawing routine that mirrors how preview renders the ticket.
    Uses the painter.device() DPI to convert mm -> pixels and converts point
    font sizes to pixel sizes for consistent output between preview, PDF and printer.
    If a field value is a filesystem image path it will be embedded and scaled
    into the field rectangle.
    """
    painter.save()

    # Determine DPI of the paint device (works for QPixmap, QPrinter etc.)
    try:
        dpi_x = painter.device().logicalDpiX() or 96
        dpi_y = painter.device().logicalDpiY() or dpi_x
    except Exception:
        dpi_x = dpi_y = 96

    def mm_to_px_local(mm, dpi=dpi_x):
        return int(round(float(mm) * dpi / 25.4)) if mm is not None else 0

    # center offset in device pixels
    if ticket_width_mm and ticket_height_mm:
        offset_x = mm_to_px_local((page_width_mm - ticket_width_mm) / 2.0)
        offset_y = mm_to_px_local((page_height_mm - ticket_height_mm) / 2.0)
    else:
        offset_x = offset_y = 0

    # Optional border (debug)
    try:
        if ticket_width_mm and ticket_height_mm:
            painter.setPen(Qt.red)
            painter.drawRect(
                offset_x,
                offset_y,
                mm_to_px_local(ticket_width_mm),
                mm_to_px_local(ticket_height_mm)
            )
            painter.setPen(Qt.black)
    except Exception:
        pass

    for field in template_fields:
        try:
            x_mm = float(field.get('x', 0))
            y_mm = float(field.get('y', 0))
            w_mm = float(field.get('width', 0))
            h_mm = float(field.get('height', 0))
        except Exception:
            continue

        field_name = field.get('fieldname')
        if not field_name:
            continue

        x = mm_to_px_local(x_mm) + offset_x
        y = mm_to_px_local(y_mm) + offset_y
        w = mm_to_px_local(w_mm)
        h = mm_to_px_local(h_mm)

        value = ticket_data.get(field_name, "")

        # build font: convert point size -> pixels using device DPI so font matches preview
        font_family = field.get('fontname') or 'Arial'
        try:
            fontsize_pt = float(field.get('fontsize') or 10)
        except Exception:
            fontsize_pt = 10.0
        pixel_size = max(1, int(round(fontsize_pt * dpi_y / 72.0)))

        # Create QFont and apply fontstyle flags if present
        qfont = QFont(font_family)
        fontstyle = (field.get('fontstyle') or "").lower()
        if fontstyle:
            qfont.setBold('bold' in fontstyle)
            qfont.setItalic('italic' in fontstyle)
            qfont.setUnderline('underline' in fontstyle)
        qfont.setPixelSize(pixel_size)
        painter.setFont(qfont)

        # Image embedding (resolve resource from user folder > bundled > absolute)
        image_path_to_use = None
        try:
            if isinstance(value, str) and value.strip():
                resolved = resolve_resource(value, 'vehicle_images')
                if resolved and os.path.exists(resolved):
                    image_path_to_use = resolved
                elif os.path.isabs(value) and os.path.exists(value):
                    image_path_to_use = os.path.normpath(value)
        except Exception:
            image_path_to_use = None

        if image_path_to_use and w > 0 and h > 0:
            try:
                pix = QPixmap(image_path_to_use)
                if not pix.isNull():
                    scaled = pix.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    dx = x + max(0, (w - scaled.width()) // 2)
                    dy = y + max(0, (h - scaled.height()) // 2)
                    painter.drawPixmap(dx, dy, scaled)
                    continue
            except Exception:
                try:
                    candidates = debug_candidates(value or '', 'vehicle_images')
                    print(f"[DEBUG] Failed to draw image for field '{field_name}'. attempted: {candidates}")
                except Exception:
                    pass
                # fall through to text

        # Text fallback: left aligned, vertically centered
        text = str(value) if value is not None else ""
        try:
            painter.drawText(QRect(x, y, w, h), Qt.AlignLeft | Qt.AlignVCenter, text)
        except Exception:
            pass

    painter.restore()


# --- WYSIWYG Print from Preview (unchanged helper) ---
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
