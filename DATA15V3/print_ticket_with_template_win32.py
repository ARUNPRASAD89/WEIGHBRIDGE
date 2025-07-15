import win32print
import win32ui
import win32con
from db_utils import get_connection, execute_query, fetch_one

def mm_to_printer_px(mm, dpi):
    return int(mm * dpi / 25.4)

def get_default_template_fields(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT templatename FROM templatemaster WHERE defaulttemplate = true;")
        template = cur.fetchone()
        if not template:
            raise Exception("No default template found in templatemaster.")
        templatename = template[0]
        cur.execute("""
            SELECT fieldname, displayname, x, y, width, height, fontname, fontsize
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
                "fontname": row[6],
                "fontsize": int(row[7]), # pt or mm, see note below
            })
    return templatename, fields

def print_ticket_with_template(data_dict, conn=None, printer_name=None, job_title="Weighbridge Ticket"):
    if conn is None:
        conn = get_connection()

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

    templatename, fields = get_default_template_fields(conn)
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
        fontsize_px = int(field["fontsize"] * dpi_y / 72)

        font = win32ui.CreateFont({
            "name": field["fontname"],
            "height": fontsize_px,
            "weight": win32con.FW_NORMAL,
        })
        hDC.SelectObject(font)
        hDC.TextOut(x, y, value)

    hDC.EndPage()
    hDC.EndDoc()
    hDC.DeleteDC()
