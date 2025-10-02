import os
import win32print
import win32ui
import win32con
from db_utils import get_new_connection, execute_query, fetch_one
from PyQt5.QtCore import QLocale, QDate, QTime
# If an image is present we will hand off printing to the Qt-based renderer
from ticket_printer import render_ticket_with_data, get_template_spec_from_db

def db_date_to_display(db_date_val):
    # Accepts str, datetime.date, QDate, or None
    if db_date_val is None or db_date_val == "":
        return ""
    if isinstance(db_date_val, QDate):
        qdate = db_date_val
    elif hasattr(db_date_val, 'isoformat'):  # datetime.date or datetime.datetime
        qdate = QDate.fromString(db_date_val.isoformat(), "yyyy-MM-dd")
    else:
        qdate = QDate.fromString(str(db_date_val), "yyyy-MM-dd")
    return qdate.toString(QLocale.system().dateFormat(QLocale.ShortFormat)) if qdate.isValid() else str(db_date_val)

def db_time_to_display(db_time_val):
    # Accepts str, datetime.time, QTime, or None
    if db_time_val is None or db_time_val == "":
        return ""
    if isinstance(db_time_val, QTime):
        qtime = db_time_val
    elif hasattr(db_time_val, 'isoformat'):  # datetime.time or datetime.datetime
        # isoformat may return "HH:MM:SS" or "HH:MM:SS.ssssss"
        qtime = QTime.fromString(db_time_val.isoformat(timespec='seconds'), "HH:mm:ss")
    else:
        qtime = QTime.fromString(str(db_time_val), "HH:mm:ss")
    return qtime.toString("HH:mm:ss") if qtime.isValid() else str(db_time_val)

def mm_to_printer_px(mm, dpi):
    return int(mm * dpi / 25.4)

def get_default_template_fields(conn):
    """
    Returns (templatename, ticket_width_mm, ticket_height_mm, fields)
    """
    with conn.cursor() as cur:
        cur.execute("SELECT templatename, ticketwidth, ticketheight FROM templatemaster WHERE defaulttemplate = true;")
        template = cur.fetchone()
        if not template:
            raise Exception("No default template found in templatemaster.")
        templatename = template[0]
        ticket_width_mm = float(template[1]) if template[1] is not None else 0.0
        ticket_height_mm = float(template[2]) if template[2] is not None else 0.0
        cur.execute("""
            SELECT fieldname, displayname, x, y, width, height, fontname, fontsize, fontstyle
            FROM templatefields
            WHERE templatename = %s
            ORDER BY id ASC
        """, (templatename,))
        fields = []
        for row in cur.fetchall():
            fields.append({
                "fieldname": row[0],
                "displayname": row[1],
                "x": float(row[2]),      # mm
                "y": float(row[3]),      # mm
                "width": float(row[4]),  # mm
                "height": float(row[5]), # mm
                "fontname": row[6] or "Arial",
                "fontsize": int(row[7]) if row[7] is not None else 10, # pt
                "fontstyle": (row[8] or "normal").lower()
            })
    return templatename, ticket_width_mm, ticket_height_mm, fields

def looks_like_image_path(v):
    if not isinstance(v, str) or not v:
        return False
    ext = os.path.splitext(v)[1].lower()
    return os.path.exists(v) and ext in ('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tif', '.tiff')

def print_ticket_with_template(data_dict, conn=None, printer_name=None, job_title="Weighbridge Ticket"):
    if conn is None:
        conn = get_new_connection()

    # PATCH: Always fetch ticket from DB by integer TicketNumber for print
    ticket_no = data_dict.get("TicketNumber", None)
    try:
        ticket_no_int = int(ticket_no)
    except Exception:
        ticket_no_int = 0

    saved_row = fetch_one('SELECT * FROM tickets WHERE "TicketNumber" = %s', (ticket_no_int,))
    if saved_row:
        ticket_data = dict(saved_row)
        # Pad for display
        ticket_data["TicketNumber"] = f"{ticket_data['TicketNumber']:05d}"
    else:
        # fallback (should not occur)
        ticket_data = data_dict

    # --- PATCH: format date/time for print ---
    if "Date" in ticket_data:
        ticket_data["Date"] = db_date_to_display(ticket_data["Date"])
    if "Time" in ticket_data:
        ticket_data["Time"] = db_time_to_display(ticket_data["Time"])
    # --- END PATCH ---

    templatename, ticket_width_mm, ticket_height_mm, fields = get_default_template_fields(conn)

    # If any field value is an image path, use the Qt renderer which supports embedding images.
    try:
        if any(looks_like_image_path(ticket_data.get(f["fieldname"])) for f in fields):
            # Use the Qt renderer but in silent mode so there are no dialogs.
            # This will render using QPrinter and honor DPI, font sizing done inside ticket_printer._draw_ticket.
            render_ticket_with_data(
                template_fields=fields,
                ticket_data=ticket_data,
                ticket_width_mm=ticket_width_mm,
                ticket_height_mm=ticket_height_mm,
                parent=None,
                preview=False,
                export_pdf_path=None,
                silent=True,
                printer_name=printer_name
            )
            return
    except Exception:
        # If detection fails, fall back to win32 text printing below
        pass

    # Win32 text-only printing (silent)
    if not printer_name:
        printer_name = win32print.GetDefaultPrinter()

    hDC = win32ui.CreateDC()
    hDC.CreatePrinterDC(printer_name)
    dpi_x = hDC.GetDeviceCaps(win32con.LOGPIXELSX)
    dpi_y = hDC.GetDeviceCaps(win32con.LOGPIXELSY)

    hDC.StartDoc(job_title)
    hDC.StartPage()

    for field in fields:
        value = str(ticket_data.get(field["fieldname"], ""))
        x = mm_to_printer_px(field["x"], dpi_x)
        y = mm_to_printer_px(field["y"], dpi_y)
        # Font size: if stored in points (most likely), convert to pixels as (point * DPI / 72)
        try:
            fontsize_pt = float(field.get("fontsize", 10))
        except Exception:
            fontsize_pt = 10.0
        fontsize_px = max(1, int(round(fontsize_pt * dpi_y / 72.0)))

        # Parse fontstyle (comma-separated like "bold,italic" or "normal")
        fontstyle = (field.get("fontstyle") or "normal").lower()
        is_bold = 'bold' in fontstyle
        is_italic = 'italic' in fontstyle
        is_underline = 'underline' in fontstyle

        weight = win32con.FW_BOLD if is_bold else win32con.FW_NORMAL

        # Create the Win32 font with appropriate style flags
        font_props = {
            "name": field.get("fontname") or "Arial",
            "height": fontsize_px,
            "weight": weight,
            "italic": bool(is_italic),
            "underline": bool(is_underline),
        }
        try:
            font = win32ui.CreateFont(font_props)
            hDC.SelectObject(font)
        except Exception:
            # Fallback: create a simple font with minimal props
            fallback_font = win32ui.CreateFont({
                "name": field.get("fontname") or "Arial",
                "height": fontsize_px
            })
            hDC.SelectObject(fallback_font)

        hDC.TextOut(x, y, value)

    hDC.EndPage()
    hDC.EndDoc()
    hDC.DeleteDC()
