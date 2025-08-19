import win32print
import win32ui
import win32con
from db_utils import get_new_connection, fetch_all, fetch_one
from date_time_utils import to_display_date, to_display_time

def mm_to_printer_px(mm, dpi):
    """Converts millimeters to printer device pixels."""
    return int(float(mm) * dpi / 25.4)

def get_template_details(conn, template_name):
    """Fetches the layout and fields for a given report template name."""
    template_settings = fetch_one(
        "SELECT pagewidth, pageheight, topmargin, leftmargin, lineheight FROM reporttemplate WHERE reporttemplatename = %s",
        (template_name,)
    )
    if not template_settings:
        raise Exception(f"Template '{template_name}' not found in reporttemplate table.")

    # --- FIX: Also fetch the fieldcaption for use in headers ---
    field_details = fetch_all(
        "SELECT fieldname, fieldcaption, x, width, fontname, fontsize, alignment FROM reportdetail WHERE reporttemplatename = %s ORDER BY id",
        (template_name,)
    )
    if not field_details:
        raise Exception(f"No fields found for template '{template_name}' in reportdetail table.")

    return template_settings, field_details


def print_report_with_template(title, rows, summary_data=None, printer_name=None):
    """
    Prints a report using a database-driven template and the win32print API.
    This version is corrected to handle column positions properly.
    """
    conn = get_new_connection()
    try:
        template_settings, fields = get_template_details(conn, title)
    finally:
        conn.close()

    if not printer_name:
        printer_name = win32print.GetDefaultPrinter()

    hDC = win32ui.CreateDC()
    hDC.CreatePrinterDC(printer_name)
    dpi_x = hDC.GetDeviceCaps(win32con.LOGPIXELSX)
    dpi_y = hDC.GetDeviceCaps(win32con.LOGPIXELSY)

    page_height_px = mm_to_printer_px(template_settings['pageheight'], dpi_y)
    top_margin_px = mm_to_printer_px(template_settings['topmargin'], dpi_y)
    line_height_px = mm_to_printer_px(template_settings['lineheight'], dpi_y)
    left_margin_px = mm_to_printer_px(template_settings['leftmargin'], dpi_y)

    hDC.StartDoc(f"Report: {title}")
    hDC.StartPage()

    current_y = top_margin_px
    
    # Create fonts once to be efficient
    header_font = win32ui.CreateFont({
        "name": "Arial", "height": int(11 * dpi_y / 72), "weight": win32con.FW_BOLD
    })
    data_font_spec = fields[0] if fields else {"fontname": "Arial", "fontsize": 10}
    data_font = win32ui.CreateFont({
        "name": data_font_spec["fontname"],
        "height": int(data_font_spec["fontsize"] * dpi_y / 72),
        "weight": win32con.FW_NORMAL,
    })

    # --- Print Column Captions ---
    hDC.SelectObject(header_font)
    # --- FIX: This loop now correctly calculates the x position for each column ---
    for field in fields:
        x_pos = left_margin_px + mm_to_printer_px(field['x'], dpi_x)
        caption = (field.get('fieldcaption') or field['fieldname']).upper()
        hDC.TextOut(x_pos, current_y, caption)
    current_y += line_height_px

    # --- Print Data Rows ---
    hDC.SelectObject(data_font)
    for row_data in rows:
        if current_y + line_height_px > page_height_px:
            hDC.EndPage()
            hDC.StartPage()
            current_y = top_margin_px
            # (Optional: re-print headers on new page)

        # --- FIX: This is the main logic correction. Calculate X for each cell. ---
        for field in fields:
            value = str(row_data.get(field['fieldname'], ""))
            if 'date' in field['fieldname'].lower() and value:
                value = to_display_date(value)
            elif 'time' in field['fieldname'].lower() and value:
                value = to_display_time(value)

            x_pos = left_margin_px + mm_to_printer_px(field['x'], dpi_x)
            hDC.TextOut(x_pos, current_y, value)
        
        current_y += line_height_px # Increment Y position AFTER each full row is printed

    # --- Print Summary Row ---
    if summary_data:
        current_y += line_height_px
        hDC.SelectObject(header_font)
        for field in fields:
            value = str(summary_data.get(field['fieldname'], ""))
            if value:
                x_pos = left_margin_px + mm_to_printer_px(field['x'], dpi_x)
                hDC.TextOut(x_pos, current_y, value)

    hDC.EndPage()
    hDC.EndDoc()
    hDC.DeleteDC()
