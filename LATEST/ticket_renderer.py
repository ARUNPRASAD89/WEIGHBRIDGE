import os
from PIL import Image, ImageDraw, ImageFont
from db_utils import fetch_one, execute_query
import logging
from decimal import Decimal

# Get the logger used by the GUI
logger = logging.getLogger()

DPI = 150

def mm_to_px(mm, dpi=DPI):
    return int(Decimal(str(mm)) * Decimal(str(dpi)) / Decimal('25.4'))

def get_font(font_name, font_size_pt, font_style_str=""):
    font_size_px = int(Decimal(str(font_size_pt)) * DPI / 72)
    common_paths = [ f"C:/Windows/Fonts/{font_name}.ttf", "/usr/share/fonts/truetype/msttcorefonts/{font_name}.ttf", f"/System/Library/Fonts/Supplemental/{font_name}.ttf", f"/Library/Fonts/{font_name}.ttf" ]
    font_path = next((path for path in common_paths if os.path.exists(path)), None)
    
    # Handle font style variations (e.g., Arial Bold)
    if 'bold' in font_style_str.lower():
        if font_path and 'Regular' in font_path:
            variant_path = font_path.replace('Regular', 'Bold')
            if os.path.exists(variant_path):
                font_path = variant_path
        elif font_path and '.ttf' in font_path:
             variant_path = font_path.replace('.ttf', 'b.ttf') # Common naming
             if os.path.exists(variant_path):
                font_path = variant_path

    try:
        return ImageFont.truetype(font_path, font_size_px) if font_path else ImageFont.load_default()
    except IOError:
        logger.warning(f"Could not load font {font_name} from path {font_path}. Falling back to default.")
        return ImageFont.load_default()

def render_ticket(ticket_number, output_dir, bg_image_path=None):
    """
    Renders a ticket to an image using the active WhatsApp template.
    """
    # MODIFICATION: Fetch the ACTIVE template from the new whatsapptemplatemaster table
    template_master = fetch_one("SELECT * FROM whatsapptemplatemaster WHERE is_active = TRUE LIMIT 1")
    if not template_master:
        raise ValueError("No active WhatsApp template found in 'whatsapptemplatemaster'. Please set one in the designer.")

    template_name = template_master['templatename']
    width_px = mm_to_px(float(template_master['imagewidth']))
    height_px = mm_to_px(float(template_master['imageheight']))
    logger.info(f"Using active WhatsApp template '{template_name}' with dimensions {width_px}x{height_px}px.")

    ticket_data = fetch_one('SELECT * FROM tickets WHERE "TicketNumber" = %s', (ticket_number,))
    if not ticket_data:
        raise ValueError(f"Ticket number {ticket_number} not found.")
    
    ticket_data_formatted = {k: str(v) if v is not None else "" for k, v in ticket_data.items()}
    
    # MODIFICATION: Fetch fields from the new whatsapptemplatefields table
    template_fields_query = "SELECT * FROM whatsapptemplatefields WHERE templatename = %s"
    template_fields = execute_query(template_fields_query, (template_name,))
    
    canvas = None
    if bg_image_path and os.path.exists(bg_image_path):
        try:
            canvas = Image.open(bg_image_path).resize((width_px, height_px), Image.LANCZOS).convert('RGB')
            logger.info(f"Using background image: {bg_image_path}")
        except Exception as e:
            logger.error(f"Could not load or resize background image '{bg_image_path}'. Error: {e}")
            canvas = Image.new('RGB', (width_px, height_px), 'white')
    else:
        if bg_image_path:
             logger.warning(f"Background image not found at '{bg_image_path}'. Using a white background.")
        canvas = Image.new('RGB', (width_px, height_px), 'white')
    
    draw = ImageDraw.Draw(canvas)
    
    whatsapp_data = {} # This can be removed if not used, but left for compatibility

    for field in template_fields:
        field_name = field['fieldname']
        if field_name not in ticket_data_formatted:
            continue
        
        value_to_draw = ticket_data_formatted[field_name]
        
        x_px, y_px = mm_to_px(float(field['x'])), mm_to_px(float(field['y']))
        w_px, h_px = mm_to_px(float(field['width'])), mm_to_px(float(field['height']))
        
        font = get_font(field['fontname'], float(field['fontsize']), field.get('fontstyle', ''))

        if field_name == 'SnapshotPath':
            original_path = value_to_draw
            if not original_path: continue
            normalized_path = os.path.normpath(original_path)
            if os.path.exists(normalized_path):
                try:
                    with Image.open(normalized_path) as snapshot_img:
                        snapshot_img.thumbnail((w_px, h_px), Image.LANCZOS)
                        paste_x = x_px + (w_px - snapshot_img.width) // 2
                        paste_y = y_px + (h_px - snapshot_img.height) // 2
                        canvas.paste(snapshot_img, (paste_x, paste_y))
                except Exception as e:
                    logger.warning(f"Could not open/process snapshot image '{normalized_path}'. Error: {e}")
            else:
                logger.warning(f"Snapshot file does not exist at path: '{normalized_path}' (Original path was: '{original_path}')")
        else:
            draw.text((x_px, y_px), value_to_draw, font=font, fill='black')
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    output_path = os.path.join(output_dir, f"ticket_{ticket_number}.png")
    canvas.save(output_path, dpi=(DPI, DPI))
    logger.info(f"Successfully saved WhatsApp ticket image to: {output_path}")

    return output_path, whatsapp_data
