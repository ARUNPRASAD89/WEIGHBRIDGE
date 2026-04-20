# Updated whatsapp_gui.py — with restored On-Demand Report Sender and Report Designer.
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog, colorchooser
import os
import yaml
import threading
import time
import logging
from queue import Queue
from datetime import datetime, timedelta, date

try:
    from tkcalendar import DateEntry
except ImportError:
    messagebox.showerror("Missing Dependency", "The 'tkcalendar' library is required. Please install it using: pip install tkcalendar")
    DateEntry = None

from db_utils import fetch_one, execute_query
import ticket_renderer
import report_renderer # Assumed to have a render_report function that accepts date ranges
import whatsapp_sender
import sys
import inspect
print(f"DEBUG: 'ticket_renderer' is being imported from: {inspect.getfile(ticket_renderer)}")

# --- Logger Setup to Redirect to GUI ---
class QueueHandler(logging.Handler):
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        self.log_queue.put(self.format(record))

# --- The Core WhatsApp Manager Logic (now as a class) ---
class WhatsAppWorker:
    def __init__(self, config, provider_config=None, stop_event=None):
        import threading
        if isinstance(provider_config, threading.Event) and stop_event is None:
            stop_event = provider_config
            provider_config = {}
        if provider_config is None: provider_config = {}
        if stop_event is None: stop_event = threading.Event()

        self.config = config or {}
        self.ownerno = self.config.get('ownerno')
        self.poll_interval = int(self.config.get('poll_interval_seconds', 10))
        self.provider_config = provider_config or {}
        self.stop_event = stop_event
        self.last_report_sent_date = None # Track daily auto-report

        if not self.provider_config:
            try:
                row = fetch_one("SELECT * FROM weighbridge_config WHERE config_name = %s", ('default',))
                if row and row.get('whatsapp_account_sid'):
                    self.provider_config = {
                        'provider': row.get('whatsapp_provider') or 'mock',
                        'account_sid': row.get('whatsapp_account_sid'),
                        'auth_token': row.get('whatsapp_auth_token'),
                        'from_whatsapp': row.get('whatsapp_from_whatsapp'),
                    }
                    logging.info("WhatsAppWorker: loaded provider_config from DB.")
                else:
                    logging.warning("WhatsAppWorker: no provider_config provided and DB row missing — using mock provider.")
            except Exception as e:
                logging.exception(f"WhatsAppWorker: failed to read provider_config from DB: {e}")

        self.settings = fetch_one("SELECT * FROM whatsappsettings WHERE id = 1")
        if not self.settings:
            logging.error("CRITICAL: Could not load settings from 'whatsappsettings' table. Worker will not run.")
            self.stop_event.set()
            return

        self.output_dir = self.settings.get('imagedirectory', 'generated_tickets')
        self.last_processed_ticket_id = self._get_initial_ticket_id()
        logging.info(f"Worker starting. Will process tickets > {self.last_processed_ticket_id}. Polling every {self.poll_interval}s.")
    
    def _get_initial_ticket_id(self):
        last_sent = fetch_one("SELECT MAX(ticket_number) as max_id FROM whatsapp_sends")
        if last_sent and last_sent.get('max_id') is not None:
            return int(last_sent['max_id'])
        latest_ticket = fetch_one('SELECT MAX("TicketNumber") as max_id FROM tickets')
        if latest_ticket and latest_ticket.get('max_id') is not None:
            return int(latest_ticket['max_id'])
        return 0

    def _log_send_attempt(self, ticket_number, template_id, recipient, status, details, image_path=None):
        execute_query(
            "INSERT INTO whatsapp_sends (ticket_number, template_id, recipient, status, details, generated_image_path, sent_at) VALUES (%s, %s, %s, %s, %s, %s, NOW())",
            (ticket_number, template_id, recipient, status, details, image_path)
        )

    def _format_message(self, message_template, ticket_data):
        class SafeDict(dict):
            def __missing__(self, key): return f"{{{key}}}"
        safe_ticket_data = {k: str(v) if v is not None else "" for k, v in ticket_data.items()}
        return message_template.format_map(SafeDict(safe_ticket_data))

    def process_single_ticket(self, ticket_number, is_test=False):
        ticket = fetch_one('SELECT * FROM tickets WHERE "TicketNumber" = %s', (ticket_number,))
        if not ticket:
            logging.error(f"TEST FAILED: Ticket number {ticket_number} not found in the database.")
            if is_test: messagebox.showerror("Test Failed", f"Ticket number {ticket_number} not found.")
            return

        send_mode_image = self.settings.get('imagewithtext', False)
        send_mode_text = self.settings.get('textonly', True)
        message_template = None
        if send_mode_image: message_template = fetch_one("SELECT * FROM whatsapp_templates WHERE image_caption IS NOT NULL AND image_caption != '' LIMIT 1")
        elif send_mode_text: message_template = fetch_one("SELECT * FROM whatsapp_templates WHERE message_template IS NOT NULL AND message_template != '' LIMIT 1")

        if not message_template:
            logging.error("No suitable message template found in 'whatsapp_templates' for the selected send mode.")
            if is_test: messagebox.showerror("Test Failed", "No suitable message template was found.")
            return

        logging.info(f"Processing Ticket #{ticket_number}...")
        status, details, image_path = "failed", "Unknown error", None
        try:
            if send_mode_image:
                bg_image_path = self.settings.get('bggroundimagedirectory')
                image_path, _ = ticket_renderer.render_ticket(ticket_number, self.output_dir, bg_image_path=bg_image_path)
                caption = self._format_message(message_template['image_caption'], ticket)
                result = whatsapp_sender.send_media(self.provider_config, self.ownerno, caption, image_path)
                status, details = result['status'], result['details']
            elif send_mode_text:
                message = self._format_message(message_template['message_template'], ticket)
                result = whatsapp_sender.send_text(self.provider_config, self.ownerno, message)
                status, details = result['status'], result['details']
        except Exception as e:
            status, details = "failed", str(e)
            logging.exception(f"CRITICAL ERROR processing ticket {ticket_number}: {e}")
            if is_test: messagebox.showerror("Test Failed", f"A critical error occurred:\n\n{e}")
        finally:
            if not is_test:
                template_id = message_template.get('id') if message_template else None
                self._log_send_attempt(ticket_number, template_id, self.ownerno, status, details, image_path)
                self.last_processed_ticket_id = ticket_number
            logging.info(f"Finished processing Ticket #{ticket_number}. Status: {status}")
            if is_test:
                if status in ('sent', 'mock'): messagebox.showinfo("Test Succeeded", f"Test for ticket {ticket_number} completed with status: {status}\n\nDetails: {details}")
                else: messagebox.showerror("Test Failed", f"Test for ticket {ticket_number} failed.\n\nStatus: {status}\nReason: {details}")

    def process_new_tickets(self):
        new_tickets = execute_query('SELECT * FROM tickets WHERE "TicketNumber" > %s ORDER BY "TicketNumber" ASC', (self.last_processed_ticket_id,))
        if not new_tickets: return
        for ticket in new_tickets:
            if self.stop_event.is_set(): break
            self.process_single_ticket(ticket['TicketNumber'])

    def check_and_send_auto_report(self):
        # Refresh settings in case they were changed in the GUI
        self.settings = fetch_one("SELECT * FROM whatsappsettings WHERE id = 1")
        if not self.settings or not self.settings.get('autoreport_enabled'):
            return

        try:
            now = datetime.now()
            report_time_str = str(self.settings.get('autoreport_time', '21:00'))
            report_time = datetime.strptime(report_time_str, '%H:%M:%S').time()

            # Check if it's time to send and if we haven't sent today
            if now.time() >= report_time and self.last_report_sent_date != now.date():
                logging.info("Auto-report time reached. Preparing to send daily report.")
                
                report_date = now.date() - timedelta(days=1)
                recipient = self.settings.get('autoreport_recipient')
                template = self.settings.get('autoreport_template_name')

                if not recipient or not template:
                    logging.error("Auto-report failed: Recipient or template is not configured.")
                    # Mark as 'sent' for today to avoid spamming errors
                    self.last_report_sent_date = now.date()
                    return

                logging.info(f"Generating auto-report for {report_date} to be sent to {recipient}.")
                
                output_dir = self.settings.get('imagedirectory', 'generated_tickets')
                report_path = report_renderer.render_report(template, output_dir, start_date=report_date, end_date=report_date)

                if report_path:
                    caption = f"Daily Weighbridge Report: {report_date.strftime('%Y-%m-%d')}"
                    result = whatsapp_sender.send_media(self.provider_config, recipient, caption, report_path)
                    if result.get('status') in ('sent', 'mock'):
                        logging.info(f"Auto-report for {report_date} sent successfully.")
                        self.last_report_sent_date = now.date() # Mark as sent for today
                    else:
                        logging.error(f"Auto-report send failed for {report_date}: {result.get('details')}. Will retry later.")
                else:
                    logging.error(f"Auto-report generation failed for {report_date}. Will retry later.")
        except Exception as e:
            logging.exception(f"An error occurred during auto-report check: {e}")

    def run(self):
        if self.stop_event.is_set():
            logging.error("Worker did not start due to critical error on initialization.")
            return

        while not self.stop_event.is_set():
            try:
                # Check master enabler switch
                enabler = fetch_one("SELECT enabled FROM whatsappenabler WHERE id = 1")
                if enabler and enabler.get('enabled'):
                    self.process_new_tickets()
                    self.check_and_send_auto_report()
                else:
                    logging.info("WhatsApp is disabled by master switch. Skipping processing loop.")
                
                self.stop_event.wait(self.poll_interval)
            except Exception as e:
                logging.exception(f"An unhandled error occurred in the main worker loop: {e}")
                time.sleep(self.poll_interval * 2)
        logging.info("WhatsApp Worker has stopped.")

# --- Helper DB functions for config ---
def _get_db_config_row(): return fetch_one("SELECT * FROM weighbridge_config WHERE config_name = %s", ('default',))
def _upsert_db_config(ownerno, poll_interval_seconds, provider):
    execute_query("""
        INSERT INTO weighbridge_config (config_name, ownerno, poll_interval_seconds, whatsapp_account_sid, whatsapp_auth_token, whatsapp_from_whatsapp, whatsapp_provider)
        VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT (config_name) DO UPDATE SET
        ownerno = EXCLUDED.ownerno, poll_interval_seconds = EXCLUDED.poll_interval_seconds, whatsapp_account_sid = EXCLUDED.whatsapp_account_sid,
        whatsapp_auth_token = EXCLUDED.whatsapp_auth_token, whatsapp_from_whatsapp = EXCLUDED.whatsapp_from_whatsapp, whatsapp_provider = EXCLUDED.whatsapp_provider, updated_at = NOW()
    """, ('default', ownerno, poll_interval_seconds, provider.get('account_sid'), provider.get('auth_token'), provider.get('from_whatsapp'), provider.get('provider')))
def _clear_whatsapp_credentials():
    execute_query("UPDATE weighbridge_config SET whatsapp_account_sid = NULL, whatsapp_auth_token = NULL, whatsapp_from_whatsapp = NULL, whatsapp_provider = 'mock', updated_at = NOW() WHERE config_name = %s", ('default',))

def save_report_path(report_path: str) -> bool:
    if not report_path: logging.warning("save_report_path called with empty path; skipping DB write."); return False
    try: execute_query("UPDATE whatsappsettings SET reportpath = %s WHERE id = 1", (report_path,)); logging.info("Saved reportpath to DB: %s", report_path); return True
    except Exception as e: logging.exception("Failed to save reportpath to whatsappsettings: %s", e); return False
def load_last_report_dir() -> str:
    try:
        row = fetch_one("SELECT reportpath FROM whatsappsettings WHERE id = 1")
        if not row: return None
        rp = row.get('reportpath') or None
        if not rp: return None
        folder = os.path.dirname(rp)
        return folder if folder else None
    except Exception as e: logging.exception("Failed to read reportpath from whatsappsettings: %s", e); return None

# --- Report Designer and related helpers ---
_MM_TO_PX = 3.78
_PX_TO_MM = 1.0 / _MM_TO_PX
def get_report_template_names():
    try: return [r['reporttemplatename'] for r in (execute_query("SELECT DISTINCT reporttemplatename FROM reportdetail ORDER BY reporttemplatename") or [])]
    except Exception as e: logging.error("Failed to fetch report template names: %s", e); return []
def _page_size_from_reporttemplate(template_name):
    try:
        props = fetch_one("SELECT * FROM reporttemplate WHERE reporttemplatename = %s", (template_name,))
        if not props: return None
        return (int(float(props.get('pagewidth', 210)) * _MM_TO_PX), int(float(props.get('pageheight', 297)) * _MM_TO_PX), int(float(props.get('lineheight', 7)) * _MM_TO_PX))
    except Exception: return None
def _find_layout_row(template_name, field_name):
    try: return fetch_one("SELECT * FROM report_template_layout WHERE report_template_name = %s AND field_name = %s LIMIT 1", (template_name, field_name))
    except: return None
def _find_templatefield_row(template_name, field_name):
    try: return fetch_one("SELECT * FROM templatefields WHERE templatename = %s AND (fieldname = %s OR lower(fieldname) = lower(%s)) LIMIT 1", (template_name, field_name, field_name))
    except: return None

class DraggableField:
    def __init__(self, canvas, x, y, field_name, display_name, font_size, font_color, on_select):
        self.canvas, self.field_name, self.display_name, self.font_size, self.font_color, self.on_select = canvas, field_name, display_name, int(font_size or 12), font_color or 'black', on_select
        self.selected, self.agg_type, self.agg_source = False, "", ""
        self.text_id = self.canvas.create_text(x, y, text=self.display_name, font=("Arial", self.font_size), fill=self.font_color, tags=("field", self.field_name))
        self.canvas.tag_bind(self.text_id, "<Button-1>", self.on_press)
        self.canvas.tag_bind(self.text_id, "<B1-Motion>", self.on_drag)
    def on_press(self, event):
        if callable(self.on_select): self.on_select(self)
        self._drag_start_x, self._drag_start_y = event.x, event.y
    def on_drag(self, event):
        dx, dy = event.x - self._drag_start_x, event.y - self._drag_start_y
        self.canvas.move(self.text_id, dx, dy)
        self._drag_start_x, self._drag_start_y = event.x, event.y
    def select(self): self.selected = True; self.canvas.itemconfig(self.text_id, font=("Arial", self.font_size, "bold"))
    def deselect(self): self.selected = False; self.canvas.itemconfig(self.text_id, font=("Arial", self.font_size, "normal"))
    def get_properties(self):
        x, y = self.canvas.coords(self.text_id)
        return {"field_name": self.field_name, "display_name": self.display_name, "pos_x": int(x), "pos_y": int(y), "font_size": int(self.font_size), "font_color": self.font_color}

class ReportDesigner(tk.Toplevel):
    def __init__(self, parent, template_name):
        super().__init__(parent)
        self.title(f"Report Designer - {template_name}"); self.geometry("1000x750"); self.template_name, self.parent = template_name, parent
        self.canvas_fields, self.selected_field = [], None
        self.available_fields = self._load_available_fields()
        page_size = _page_size_from_reporttemplate(self.template_name)
        self.canvas_width, self.canvas_height, self.canvas_lineheight = page_size if page_size else (1200, 900, 24)
        self._create_widgets(); self.load_layout()
    def _load_available_fields(self):
        names, seen = [], set()
        try:
            for r in (execute_query("SELECT field_name FROM report_template_layout WHERE report_template_name = %s ORDER BY id", (self.template_name,)) or []):
                fn = r.get('field_name');
                if fn and fn not in seen: seen.add(fn); names.append(fn)
        except: pass
        try:
            for r in (execute_query("SELECT fieldname FROM templatefields WHERE templatename = %s ORDER BY id", (self.template_name,)) or []):
                fn = r.get('fieldname')
                if fn and fn not in seen: seen.add(fn); names.append(fn)
        except: pass
        for f in ["TicketNumber", "Date", "Time", "VehicleNumber", "Materialname", "NetWeight", "SnapshotPath"]:
            if f not in seen: names.append(f)
        return names
    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding=10); main_frame.pack(fill=tk.BOTH, expand=True)
        control_frame = ttk.Frame(main_frame, width=320); control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0,10)); control_frame.pack_propagate(False)
        canvas_frame = ttk.Frame(main_frame); canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.canvas = tk.Canvas(canvas_frame, bg="white", width=self.canvas_width, height=self.canvas_height, scrollregion=(0,0,self.canvas_width,self.canvas_height))
        vbar, hbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview), ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=vbar.set, xscrollcommand=hbar.set); self.canvas.pack(fill=tk.BOTH, expand=True); vbar.pack(side=tk.RIGHT, fill=tk.Y); hbar.pack(side=tk.BOTTOM, fill=tk.X)
        field_frame = ttk.LabelFrame(control_frame, text="Manage Fields", padding=8); field_frame.pack(fill=tk.X, pady=(0,8))
        self.field_var = tk.StringVar(); field_combo = ttk.Combobox(field_frame, textvariable=self.field_var, values=self.available_fields, state="readonly"); field_combo.pack(fill=tk.X, pady=(0,6))
        if self.available_fields: field_combo.set(self.available_fields[0])
        ttk.Button(field_frame, text="Add Field", command=self.add_field).pack(fill=tk.X)
        self.properties_frame = ttk.LabelFrame(control_frame, text="Field Properties", padding=8); self.properties_frame.pack(fill=tk.X, pady=6)
        self.display_name_var, self.font_size_var, self.font_color_var = tk.StringVar(), tk.IntVar(value=12), tk.StringVar(value="black")
        self.left_mm_var, self.top_mm_var, self.agg_type_var, self.agg_source_var = tk.DoubleVar(value=0.0), tk.DoubleVar(value=0.0), tk.StringVar(value=""), tk.StringVar(value="")
        ttk.Label(self.properties_frame, text="Display Name:").pack(anchor='w'); ttk.Entry(self.properties_frame, textvariable=self.display_name_var).pack(fill='x', pady=(0,6))
        ttk.Label(self.properties_frame, text="Font Size:").pack(anchor='w'); ttk.Entry(self.properties_frame, textvariable=self.font_size_var).pack(fill='x', pady=(0,6))
        ttk.Label(self.properties_frame, text="Font Color:").pack(anchor='w'); color_frame = ttk.Frame(self.properties_frame); color_frame.pack(fill='x', pady=(0,6))
        self.color_entry = ttk.Entry(color_frame, textvariable=self.font_color_var); self.color_entry.pack(side='left', expand=True, fill='x'); ttk.Button(color_frame, text="...", width=3, command=self.choose_color).pack(side='left', padx=(6,0))
        mm_frame = ttk.Frame(self.properties_frame); mm_frame.pack(fill='x', pady=(0,6)); ttk.Label(mm_frame, text="Left (mm):").grid(row=0, column=0, sticky='w')
        self.left_spin = tk.Spinbox(mm_frame, textvariable=self.left_mm_var, from_=0.0, to=1000.0, increment=0.5, width=10, format="%.2f"); self.left_spin.grid(row=0, column=1, sticky='w', padx=(6,12))
        ttk.Label(mm_frame, text="Top (mm):").grid(row=0, column=2, sticky='w'); self.top_spin = tk.Spinbox(mm_frame, textvariable=self.top_mm_var, from_=0.0, to=1000.0, increment=0.5, width=10, format="%.2f"); self.top_spin.grid(row=0, column=3, sticky='w', padx=(6,0))
        agg_frame = ttk.Frame(self.properties_frame); agg_frame.pack(fill='x', pady=(0,6)); ttk.Label(agg_frame, text="Aggregation:").grid(row=0, column=0, sticky='w')
        agg_combo = ttk.Combobox(agg_frame, textvariable=self.agg_type_var, values=["", "SUM", "COUNT"], state="readonly", width=8); agg_combo.grid(row=0, column=1, sticky='w', padx=(6,12))
        ttk.Label(agg_frame, text="Source Field:").grid(row=0, column=2, sticky='w'); self.agg_source_combo = ttk.Combobox(agg_frame, textvariable=self.agg_source_var, values=self.available_fields, state="readonly", width=18); self.agg_source_combo.grid(row=0, column=3, sticky='w', padx=(6,0))
        ttk.Button(self.properties_frame, text="Apply Changes", command=self.apply_field_properties).pack(fill='x', pady=(4,0))
        ttk.Button(control_frame, text="Remove Selected Field", command=self.remove_field).pack(fill=tk.X, pady=(6,0))
        ttk.Button(control_frame, text="Save Layout", command=self.save_layout).pack(side=tk.BOTTOM, fill=tk.X, pady=10)
        self.update_properties_frame(None)
    def choose_color(self):
        color_code = colorchooser.askcolor(title="Choose color", parent=self)
        if color_code and color_code[1]: self.font_color_var.set(color_code[1])
    def update_properties_frame(self, field_obj):
        if field_obj:
            display = field_obj.display_name;
            if "||__AGG__:" in display: label, marker = display.split("||__AGG__:", 1); display = label; parts = marker.split(":", 2); self.agg_type_var.set(parts[0] if len(parts) >= 1 else ""); self.agg_source_var.set(parts[1] if len(parts) >= 2 else "")
            else: self.agg_type_var.set(""); self.agg_source_var.set("")
            self.display_name_var.set(display); self.font_size_var.set(field_obj.font_size); self.font_color_var.set(field_obj.font_color)
            try: x, y = self.canvas.coords(field_obj.text_id); self.left_mm_var.set(round(x * _PX_TO_MM, 3)); self.top_mm_var.set(round(y * _PX_TO_MM, 3))
            except: self.left_mm_var.set(0.0); self.top_mm_var.set(0.0)
            for w in self.properties_frame.winfo_children():
                try: w.config(state="normal")
                except: pass
        else:
            self.display_name_var.set(""); self.font_size_var.set(12); self.font_color_var.set("black"); self.left_mm_var.set(0.0); self.top_mm_var.set(0.0); self.agg_type_var.set(""); self.agg_source_var.set("")
            for w in self.properties_frame.winfo_children():
                try: w.config(state="disabled")
                except: pass
    def handle_selection(self, field_to_select):
        if self.selected_field: self.selected_field.deselect()
        self.selected_field = field_to_select; self.selected_field.select(); self.update_properties_frame(self.selected_field)
    def load_layout(self):
        logging.info("Loading layout for template: %s", self.template_name); self.canvas.delete("all"); self.canvas_fields = []
        rows = execute_query("SELECT * FROM report_template_layout WHERE report_template_name = %s ORDER BY pos_x, pos_y", (self.template_name,))
        if rows:
            for row in rows:
                px, py = int(row.get('pos_x') or 20), int(row.get('pos_y') or 20); px, py = max(0, min(px, self.canvas_width - 10)), max(0, min(py, self.canvas_height - 10))
                display = row.get('display_name') or row.get('field_name')
                field = DraggableField(self.canvas, px, py, row['field_name'], display, row.get('font_size', 12), row.get('font_color', 'black'), self.handle_selection)
                if "||__AGG__:" in display:
                    try: label, marker = display.split("||__AGG__:", 1); parts = marker.split(":", 2); field.agg_type, field.agg_source, field.display_name = parts[0], parts[1], label; self.canvas.itemconfig(field.text_id, text=label)
                    except: pass
                self.canvas_fields.append(field)
        else:
            tf_rows = execute_query("SELECT * FROM templatefields WHERE templatename = %s ORDER BY y, x", (self.template_name,))
            if tf_rows:
                for r in tf_rows:
                    fn = r.get('fieldname');
                    if not fn or any(f.field_name == fn for f in self.canvas_fields): continue
                    try: px, py = int(float(r.get('x') or 20.0) * _MM_TO_PX), int(float(r.get('y') or 20.0) * _MM_TO_PX)
                    except: px, py = 20, 20
                    px, py = max(0, min(px, self.canvas_width - 10)), max(0, min(py, self.canvas_height - 10))
                    field = DraggableField(self.canvas, px, py, fn, r.get('displayname', fn), r.get('fontsize', 12), 'black', self.handle_selection); self.canvas_fields.append(field)
            else: logging.info("No existing layout found for template %s", self.template_name)
    def add_field(self):
        field_name = self.field_var.get()
        if not field_name: messagebox.showwarning("No Field Selected", "Please select a field to add.", parent=self); return
        if any(f.field_name == field_name for f in self.canvas_fields): messagebox.showwarning("Duplicate Field", f"The field '{field_name}' is already on the canvas.", parent=self); return
        layout_row = _find_layout_row(self.template_name, field_name)
        if layout_row:
            px, py, display_name, font_size, font_color = int(layout_row.get('pos_x') or 20), int(layout_row.get('pos_y') or 20), layout_row.get('display_name') or field_name, layout_row.get('font_size') or 12, layout_row.get('font_color') or 'black'
            field = DraggableField(self.canvas, px, py, field_name, display_name, font_size, font_color, self.handle_selection)
            if "||__AGG__:" in display_name:
                try: label, marker = display_name.split("||__AGG__:", 1); parts = marker.split(":", 2); field.agg_type, field.agg_source, field.display_name = parts[0], parts[1], label; self.canvas.itemconfig(field.text_id, text=label)
                except: pass
            self.canvas_fields.append(field); self.handle_selection(field); return
        tf_row = _find_templatefield_row(self.template_name, field_name)
        if tf_row:
            try: px, py = int(float(tf_row.get('x') or 20.0) * _MM_TO_PX), int(float(tf_row.get('y') or 20.0) * _MM_TO_PX)
            except: px, py = 20, 20
            display_name, font_size = tf_row.get('displayname') or field_name, tf_row.get('fontsize') or 12
            field = DraggableField(self.canvas, px, py, field_name, display_name, font_size, 'black', self.handle_selection); self.canvas_fields.append(field); self.handle_selection(field); return
        base_x, base_y = 20, 20
        if self.canvas_fields: last = self.canvas_fields[-1]; lx, ly = self.canvas.coords(last.text_id); base_x, base_y = int(lx) + 30, int(ly);
        if base_x > self.canvas_width - 100: base_x, base_y = 20, base_y + 30
        field = DraggableField(self.canvas, base_x, base_y, field_name, field_name, 12, "black", self.handle_selection); self.canvas_fields.append(field); self.handle_selection(field)
    def apply_field_properties(self):
        if not self.selected_field: return
        try: new_size = int(self.font_size_var.get()); assert new_size > 0
        except: messagebox.showerror("Invalid Input", "Font size must be a positive number.", parent=self); return
        self.selected_field.display_name, self.selected_field.font_size, self.selected_field.font_color = self.display_name_var.get(), new_size, self.font_color_var.get()
        self.canvas.itemconfig(self.selected_field.text_id, text=self.selected_field.display_name, font=("Arial", new_size, "bold"), fill=self.selected_field.font_color)
        try:
            new_x, new_y = int(float(self.left_mm_var.get()) * _MM_TO_PX), int(float(self.top_mm_var.get()) * _MM_TO_PX)
            self.canvas.coords(self.selected_field.text_id, max(0, min(new_x, self.canvas_width-10)), max(0, min(new_y, self.canvas_height-10)))
        except: pass
        self.selected_field.agg_type, self.selected_field.agg_source = self.agg_type_var.get().strip(), self.agg_source_var.get().strip()
    def remove_field(self):
        if not self.selected_field: messagebox.showwarning("No Selection", "Please select a field to remove.", parent=self); return
        self.canvas.delete(self.selected_field.text_id); self.canvas_fields.remove(self.selected_field); self.selected_field = None; self.update_properties_frame(None)
    def save_layout(self):
        if not messagebox.askyesno("Confirm Save", "This will overwrite the existing layout for this template. Are you sure?", parent=self): return
        try:
            logging.info("Saving layout for template: %s", self.template_name); execute_query("DELETE FROM report_template_layout WHERE report_template_name = %s", (self.template_name,))
            for field in self.canvas_fields:
                props = field.get_properties(); display_to_save = props['display_name']
                agg_type, agg_source = getattr(field, 'agg_type', ''), getattr(field, 'agg_source', '')
                if agg_type: display_to_save = f"{display_to_save}||__AGG__:{agg_type}:{agg_source}"
                execute_query("INSERT INTO report_template_layout (report_template_name, field_name, display_name, pos_x, pos_y, font_size, font_color) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                              (self.template_name, props['field_name'], display_to_save, props['pos_x'], props['pos_y'], props['font_size'], props['font_color']))
            messagebox.showinfo("Layout Saved", "The report layout has been saved successfully.", parent=self); self.destroy()
        except Exception as e: logging.exception("Failed to save report layout."); messagebox.showerror("Database Error", f"Could not save layout to the database:\n{e}", parent=self)

# --- The GUI Application ---
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Weighbridge WhatsApp Manager"); self.geometry("1200x900"); self.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.config_path = "config.yaml"; self.worker_thread = None; self.stop_event = threading.Event(); self.log_queue = Queue()
        self.logger = logging.getLogger(); self.logger.setLevel(logging.INFO)
        queue_handler = QueueHandler(self.log_queue); formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'); queue_handler.setFormatter(formatter)
        if not self.logger.handlers: self.logger.addHandler(queue_handler)
        self.local_output_path_var = tk.StringVar() 
        self.whatsapp_enabled_var = tk.BooleanVar()
        self._create_widgets(); self.load_config(); self.after(100, self.process_log_queue)

    def _create_widgets(self):
        main_pane = ttk.PanedWindow(self, orient=tk.VERTICAL); main_pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        top_pane = ttk.PanedWindow(main_pane, orient=tk.HORIZONTAL); main_pane.add(top_pane, weight=1)
        left_frame = ttk.Frame(top_pane, padding=5); top_pane.add(left_frame, weight=1)
        right_frame = ttk.Frame(top_pane, padding=5); top_pane.add(right_frame, weight=1)
        log_outer_frame = ttk.Frame(main_pane, padding=5); main_pane.add(log_outer_frame, weight=1)

        # --- Left Column ---
        twilio_frame = ttk.LabelFrame(left_frame, text="Twilio Configuration", padding="10"); twilio_frame.pack(fill=tk.X, expand=False, pady=(0, 10)); twilio_frame.columnconfigure(1, weight=1)
        self.ownerno_var, self.sid_var, self.token_var, self.from_var, self.poll_interval_var = tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar(value="10")
        ttk.Label(twilio_frame, text="Owner No:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W); ttk.Entry(twilio_frame, textvariable=self.ownerno_var).grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        ttk.Label(twilio_frame, text="Twilio SID:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W); ttk.Entry(twilio_frame, textvariable=self.sid_var).grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW)
        ttk.Label(twilio_frame, text="Twilio Token:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W); ttk.Entry(twilio_frame, textvariable=self.token_var, show="*").grid(row=2, column=1, padx=5, pady=5, sticky=tk.EW)
        ttk.Label(twilio_frame, text="Twilio From No:").grid(row=3, column=0, padx=5, pady=5, sticky=tk.W); ttk.Entry(twilio_frame, textvariable=self.from_var).grid(row=3, column=1, padx=5, pady=5, sticky=tk.EW)
        ttk.Label(twilio_frame, text="Poll Interval (s):").grid(row=4, column=0, padx=5, pady=5, sticky=tk.W); ttk.Entry(twilio_frame, textvariable=self.poll_interval_var).grid(row=4, column=1, padx=5, pady=5, sticky=tk.EW)
        
        whatsapp_settings_frame = ttk.LabelFrame(left_frame, text="WhatsApp Settings", padding="10"); whatsapp_settings_frame.pack(fill=tk.X, expand=False, pady=(0, 10)); whatsapp_settings_frame.columnconfigure(1, weight=1)
        self.image_path_var, self.imagewithtext_var, self.textonly_var, self.bg_image_path_var = tk.StringVar(), tk.BooleanVar(), tk.BooleanVar(), tk.StringVar()
        
        ttk.Label(whatsapp_settings_frame, text="Ticket Image Path:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        path_frame = ttk.Frame(whatsapp_settings_frame); path_frame.grid(row=0, column=1, sticky=tk.EW); path_frame.columnconfigure(0, weight=1)
        ttk.Entry(path_frame, textvariable=self.image_path_var).grid(row=0, column=0, sticky=tk.EW, padx=(0,5))
        ttk.Button(path_frame, text="Browse...", command=self._browse_image_path).grid(row=0, column=1)

        local_frame = ttk.Frame(whatsapp_settings_frame); local_frame.grid(row=1, column=0, columnspan=2, sticky=tk.EW, pady=(6,0)); local_frame.columnconfigure(1, weight=1)
        ttk.Label(local_frame, text="Local Report Path:").grid(row=0, column=0, sticky=tk.W, padx=(5,4)); ttk.Entry(local_frame, textvariable=self.local_output_path_var).grid(row=0, column=1, sticky=tk.EW)
        ttk.Button(local_frame, text="Browse...", command=self._browse_local_output_path).grid(row=0, column=2, padx=(5,0))
        
        ttk.Label(whatsapp_settings_frame, text="Background Image:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        bg_frame = ttk.Frame(whatsapp_settings_frame); bg_frame.grid(row=2, column=1, sticky=tk.EW); bg_frame.columnconfigure(0, weight=1)
        ttk.Entry(bg_frame, textvariable=self.bg_image_path_var).grid(row=0, column=0, sticky=tk.EW, padx=(0, 5)); ttk.Button(bg_frame, text="Browse...", command=self._browse_bg_image).grid(row=0, column=1)
        
        check_frame = ttk.Frame(whatsapp_settings_frame); check_frame.grid(row=3, column=0, columnspan=2, pady=5, sticky='w')
        ttk.Checkbutton(check_frame, text="Send Image with Text", variable=self.imagewithtext_var, command=self._on_check_change).pack(side=tk.LEFT, padx=10)
        ttk.Checkbutton(check_frame, text="Send Text Only", variable=self.textonly_var, command=self._on_check_change).pack(side=tk.LEFT, padx=10)

        test_frame = ttk.LabelFrame(left_frame, text="Testing", padding="10"); test_frame.pack(fill=tk.X, expand=False, pady=5)
        self.test_ticket_no_var = tk.StringVar(); ttk.Label(test_frame, text="Test with Ticket #:").pack(side=tk.LEFT, padx=5); ttk.Entry(test_frame, textvariable=self.test_ticket_no_var, width=10).pack(side=tk.LEFT, padx=5)
        self.test_ticket_button = ttk.Button(test_frame, text="Send Test with Ticket", command=self.send_ticket_test_message); self.test_ticket_button.pack(side=tk.LEFT, padx=5)
        ttk.Button(test_frame, text="Send Simple Test", command=self.send_simple_test_message).pack(side=tk.LEFT, padx=15)

        # --- Right Column ---
        enabler_frame = ttk.Frame(right_frame); enabler_frame.pack(fill=tk.X, pady=(0,10))
        style = ttk.Style(self)
        style.configure("Switch.TCheckbutton", font=('Helvetica', 12, 'bold'))
        self.enabler_switch = ttk.Checkbutton(enabler_frame, text="Enable WhatsApp", variable=self.whatsapp_enabled_var, style="Switch.TCheckbutton"); self.enabler_switch.pack(side=tk.LEFT, padx=5)

        button_row = ttk.Frame(right_frame); button_row.pack(fill=tk.X, pady=(0,10))
        ttk.Button(button_row, text="Save All Configurations", command=self.save_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_row, text="Clear Credentials", command=self.clear_credentials).pack(side=tk.LEFT, padx=5)

        report_frame = ttk.LabelFrame(right_frame, text="Reports", padding="10"); report_frame.pack(fill=tk.X, expand=False, pady=5); report_frame.columnconfigure(1, weight=1)
        self.autoreport_enabled_var, self.autoreport_time_var, self.autoreport_recipient_var, self.autoreport_template_var = tk.BooleanVar(), tk.StringVar(), tk.StringVar(), tk.StringVar()
        self.report_start_date_var, self.report_end_date_var = tk.StringVar(), tk.StringVar()
        
        ttk.Checkbutton(report_frame, text="Enable Daily Auto-Report", variable=self.autoreport_enabled_var).grid(row=0, column=0, columnspan=2, sticky=tk.W, padx=5)
        ttk.Label(report_frame, text="Auto-Report Time:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W); ttk.Entry(report_frame, textvariable=self.autoreport_time_var).grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW)
        ttk.Label(report_frame, text="Recipient No:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W); ttk.Entry(report_frame, textvariable=self.autoreport_recipient_var).grid(row=2, column=1, columnspan=2, padx=5, pady=5, sticky=tk.EW)
        ttk.Label(report_frame, text="Report Template:").grid(row=3, column=0, padx=5, pady=5, sticky=tk.W)
        template_frame = ttk.Frame(report_frame); template_frame.grid(row=3, column=1, columnspan=2, sticky=tk.EW); template_frame.columnconfigure(0, weight=1)
        self.report_template_combo = ttk.Combobox(template_frame, textvariable=self.autoreport_template_var, state="readonly"); self.report_template_combo.grid(row=0, column=0, padx=(5,2), pady=5, sticky=tk.EW)
        self.design_button = ttk.Button(template_frame, text="...", command=self.open_designer, width=3); self.design_button.grid(row=0, column=1, padx=(2,5), pady=5)
        
        if DateEntry:
            ttk.Separator(report_frame, orient=tk.HORIZONTAL).grid(row=4, column=0, columnspan=3, sticky='ew', pady=10)
            ttk.Label(report_frame, text="On-Demand Report", font="-weight bold").grid(row=5, column=0, columnspan=3, sticky=tk.W, padx=5)
            ttk.Label(report_frame, text="Start Date:").grid(row=6, column=0, padx=5, pady=5, sticky=tk.W)
            self.report_start_date_entry = DateEntry(report_frame, textvariable=self.report_start_date_var, date_pattern='yyyy-mm-dd', state='normal'); self.report_start_date_entry.grid(row=6, column=1, padx=5, pady=5, sticky=tk.EW)
            ttk.Label(report_frame, text="End Date:").grid(row=7, column=0, padx=5, pady=5, sticky=tk.W)
            self.report_end_date_entry = DateEntry(report_frame, textvariable=self.report_end_date_var, date_pattern='yyyy-mm-dd', state='normal'); self.report_end_date_entry.grid(row=7, column=1, padx=5, pady=5, sticky=tk.EW)
            self.send_report_by_date_button = ttk.Button(report_frame, text="Send Report by Date", command=self.send_report_by_date); self.send_report_by_date_button.grid(row=8, column=0, columnspan=3, padx=5, pady=10, sticky=tk.EW)

        control_frame = ttk.LabelFrame(right_frame, text="Controls", padding="10"); control_frame.pack(fill=tk.X, expand=False, pady=5)
        self.start_button = ttk.Button(control_frame, text="Start Manager", command=self.start_worker); self.start_button.pack(side=tk.LEFT, padx=5)
        self.stop_button = ttk.Button(control_frame, text="Stop Manager", command=self.stop_worker, state=tk.DISABLED); self.stop_button.pack(side=tk.LEFT, padx=5)

        # --- Log Viewer ---
        log_frame = ttk.LabelFrame(log_outer_frame, text="Live Log", padding="10"); log_frame.pack(fill=tk.BOTH, expand=True)
        self.log_text = scrolledtext.ScrolledText(log_frame, state='disabled', wrap=tk.WORD, height=10); self.log_text.pack(fill=tk.BOTH, expand=True)

    def _browse_image_path(self):
        folder = filedialog.askdirectory(title="Select folder to save ticket images")
        if folder: self.image_path_var.set(folder)
    def _browse_local_output_path(self):
        folder = filedialog.askdirectory(title="Select folder to save generated reports")
        if folder: self.local_output_path_var.set(folder)
    def _browse_bg_image(self):
        file_path = filedialog.askopenfilename(title="Select a Background Image", filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp"), ("All files", "*.*")])
        if file_path: self.bg_image_path_var.set(file_path)
    def _on_check_change(self):
        if self.imagewithtext_var.get(): self.textonly_var.set(False)
        elif self.textonly_var.get(): self.imagewithtext_var.set(False)
    def open_designer(self):
        template_name = self.autoreport_template_var.get()
        if not template_name: messagebox.showwarning("No Template", "Please select a report template first."); return
        designer = ReportDesigner(self, template_name); designer.grab_set()

    def load_config(self):
        try:
            enabler = fetch_one("SELECT enabled FROM whatsappenabler WHERE id = 1")
            if enabler: self.whatsapp_enabled_var.set(bool(enabler.get('enabled', False)))
            else: self.whatsapp_enabled_var.set(False)
        except Exception as e: logging.error(f"Failed to load whatsappenabler state: {e}")

        try:
            row = _get_db_config_row()
            if row:
                self.ownerno_var.set(row.get('ownerno') or ''); self.sid_var.set(row.get('whatsapp_account_sid') or ''); self.token_var.set(row.get('whatsapp_auth_token') or '')
                self.from_var.set(row.get('whatsapp_from_whatsapp') or ''); self.poll_interval_var.set(str(row.get('poll_interval_seconds') or 10)); logging.info("Loaded Twilio config from DB.")
            elif os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f: config = yaml.safe_load(f)
                self.ownerno_var.set(config.get('ownerno', '')); provider = config.get('whatsapp_provider', {}); self.sid_var.set(provider.get('account_sid', '')); self.token_var.set(provider.get('auth_token', '')); self.from_var.set(provider.get('from_whatsapp', ''))
                self.poll_interval_var.set(config.get('poll_interval_seconds', 10)); logging.info("Loaded Twilio config from local config.yaml (fallback).")
            else: logging.info("No DB config and no local config.yaml found. Fields left empty.")
        except Exception as e: logging.error(f"Failed to load weighbridge_config from DB: {e}")
        
        try:
            settings = fetch_one("SELECT * FROM whatsappsettings WHERE id = 1")
            if settings:
                self.image_path_var.set(settings.get('imagedirectory', 'generated_tickets')); self.imagewithtext_var.set(bool(settings.get('imagewithtext', False)))
                self.textonly_var.set(bool(settings.get('textonly', True))); self.bg_image_path_var.set(settings.get('bggroundimagedirectory', ''))
                self.autoreport_enabled_var.set(bool(settings.get('autoreport_enabled', False))); self.autoreport_time_var.set(str(settings.get('autoreport_time') or '21:00:00'))
                self.autoreport_recipient_var.set(settings.get('autoreport_recipient') or ''); self.autoreport_template_var.set(settings.get('autoreport_template_name') or '')
                
                last_dir = load_last_report_dir()
                if last_dir: self.local_output_path_var.set(last_dir)

                template_names = get_report_template_names(); self.report_template_combo['values'] = template_names
                if settings.get('autoreport_template_name') in template_names: self.report_template_combo.set(settings.get('autoreport_template_name'))
                elif template_names: self.report_template_combo.set(template_names[0])
                logging.info("WhatsApp settings loaded successfully.")
            else: logging.warning("Could not find settings in 'whatsappsettings' table. Using defaults.")
        except Exception as e: logging.error(f"Failed to load from DB. Error: {e}"); messagebox.showerror("Database Error", f"Could not load WhatsApp settings from the database:\n{e}")

    def save_config(self):
        try:
            execute_query("UPDATE whatsappenabler SET enabled = %s WHERE id = 1", (self.whatsapp_enabled_var.get(),))
        except Exception as e: logging.error(f"Failed to save whatsappenabler state: {e}")

        try: poll_interval = int(self.poll_interval_var.get()); assert poll_interval >= 1
        except: messagebox.showerror("Invalid Input", "Poll interval must be a valid number >= 1."); return
        provider = {'provider': 'twilio' if self.sid_var.get() else 'mock', 'account_sid': self.sid_var.get(), 'auth_token': self.token_var.get(), 'from_whatsapp': self.from_var.get()}
        try: _upsert_db_config(self.ownerno_var.get().strip(), poll_interval, provider)
        except Exception as e: logging.error(f"Failed to save weighbridge_config: {e}"); messagebox.showerror("Database Error", f"Could not save configuration to DB:\n{e}"); return
        
        try:
            image_path = self.image_path_var.get().strip(); assert image_path
            report_path = self.local_output_path_var.get().strip()
            if report_path and os.path.isdir(report_path): report_path = os.path.join(report_path, 'placeholder.txt')
            
            execute_query("UPDATE whatsappsettings SET imagedirectory=%s, imagewithtext=%s, textonly=%s, bggroundimagedirectory=%s, autoreport_enabled=%s, autoreport_time=%s, autoreport_recipient=%s, autoreport_template_name=%s, reportpath=%s WHERE id=1",
                          (image_path, self.imagewithtext_var.get(), self.textonly_var.get(), self.bg_image_path_var.get().strip(), self.autoreport_enabled_var.get(), self.autoreport_time_var.get().strip(), self.autoreport_recipient_var.get().strip(), self.autoreport_template_var.get(), report_path))
            logging.info("All configurations saved successfully."); messagebox.showinfo("Success", "All configurations were saved successfully!")
        except Exception as e: logging.error(f"Failed to save settings to DB: {e}"); messagebox.showerror("Database Error", f"Could not save WhatsApp settings to the database:\n{e}"); return

    def clear_credentials(self):
        if not messagebox.askyesno("Confirm", "This will remove Twilio credentials from the shared config. Continue?"): return
        try: _clear_whatsapp_credentials(); self.sid_var.set(''); self.token_var.set(''); self.from_var.set(''); messagebox.showinfo("Cleared", "Twilio credentials removed from database."); logging.info("Twilio credentials cleared.")
        except Exception as e: logging.error(f"Failed to clear credentials: {e}"); messagebox.showerror("Database Error", f"Could not clear credentials:\n{e}")

    def start_worker(self):
        self.save_config(); self.stop_event.clear(); self.start_button.config(state=tk.DISABLED); self.stop_button.config(state=tk.NORMAL)
        row = _get_db_config_row(); config = {'ownerno': row.get('ownerno') if row else self.ownerno_var.get(), 'poll_interval_seconds': row.get('poll_interval_seconds') if row else int(self.poll_interval_var.get())}
        provider = {'provider': row.get('whatsapp_provider') or 'twilio', 'account_sid': row.get('whatsapp_account_sid'), 'auth_token': row.get('whatsapp_auth_token'), 'from_whatsapp': row.get('whatsapp_from_whatsapp')} if row and row.get('whatsapp_provider') else {'provider': 'twilio' if self.sid_var.get() else 'mock', 'account_sid': self.sid_var.get(), 'auth_token': self.token_var.get(), 'from_whatsapp': self.from_var.get()}
        worker = WhatsAppWorker(config=config, provider_config=provider, stop_event=self.stop_event)
        self.worker_thread = threading.Thread(target=worker.run, daemon=True); self.worker_thread.start()

    def stop_worker(self):
        self.stop_event.set(); self.stop_button.config(state=tk.DISABLED); self.after(2000, self._check_thread_stopped)
    def _check_thread_stopped(self):
        if self.worker_thread and self.worker_thread.is_alive(): self.after(1000, self._check_thread_stopped)
        else: self.start_button.config(state=tk.NORMAL); logging.info("Manager stopped by user.")

    def send_report_by_date(self):
        if not self.whatsapp_enabled_var.get(): messagebox.showwarning("WhatsApp Disabled", "Cannot send report because WhatsApp is disabled by the master switch."); return
        try: start_date, end_date = datetime.strptime(self.report_start_date_var.get(), '%Y-%m-%d').date(), datetime.strptime(self.report_end_date_var.get(), '%Y-%m-%d').date()
        except: messagebox.showerror("Invalid Date", "Please enter valid dates in YYYY-MM-DD format."); return
        if start_date > end_date: messagebox.showerror("Invalid Range", "Start date cannot be after the end date."); return
        recipient, template = self.autoreport_recipient_var.get().strip(), self.autoreport_template_var.get()
        if not recipient or not template: messagebox.showerror("Missing Information", "A 'Recipient No' and 'Report Template' must be selected."); return
        if not messagebox.askyesno("Confirm Report Send", f"This will generate and send a report for {start_date} to {end_date} to '{recipient}'.\n\nAre you sure?"): return
        logging.info("Starting on-demand report send for %s to %s", start_date, end_date)
        self.send_report_by_date_button.config(state=tk.DISABLED)
        threading.Thread(target=self._execute_report_send, args=(start_date, end_date, recipient, template), daemon=True).start()

    def _execute_report_send(self, start_date, end_date, recipient, template):
        try:
            output_dir = self.local_output_path_var.get().strip()
            if not output_dir:
                settings = fetch_one("SELECT imagedirectory FROM whatsappsettings WHERE id = 1")
                output_dir = settings.get('imagedirectory', 'generated_tickets') if settings else 'generated_tickets'

            row = _get_db_config_row()
            provider_config = {'provider': row.get('whatsapp_provider') or 'twilio', 'account_sid': row.get('whatsapp_account_sid'), 'auth_token': row.get('whatsapp_auth_token'), 'from_whatsapp': row.get('whatsapp_from_whatsapp')} if row and row.get('whatsapp_account_sid') else {}
            
            logging.info(f"Generating consolidated report for date range: {start_date} to {end_date}")
            report_image_path = report_renderer.render_report(template, output_dir, start_date=start_date, end_date=end_date)
            
            if report_image_path:
                save_report_path(report_image_path)
                caption = f"Weighbridge Report: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
                logging.info(f"Consolidated report generated at: {report_image_path}")
                result = whatsapp_sender.send_media(provider_config, recipient, caption, report_image_path)
                if result.get('status') in ('sent', 'mock'):
                    self.after(0, lambda: messagebox.showinfo("Process Complete", f"Report for {start_date} to {end_date} sent successfully to {recipient}."))
                else:
                    self.after(0, lambda: messagebox.showerror("Send Failed", f"Failed to send report: {result.get('details')}"))
            else:
                self.after(0, lambda: messagebox.showerror("Generation Failed", "Failed to generate the report image. Check logs for details."))
        except Exception as e:
            logging.exception(f"An error occurred during on-demand report sending: {e}")
            self.after(0, lambda: messagebox.showerror("Error", f"An error occurred during the report sending process:\n{e}"))
        finally:
            self.after(0, lambda: self.send_report_by_date_button.config(state=tk.NORMAL))

    def send_simple_test_message(self):
        if not self.whatsapp_enabled_var.get(): messagebox.showwarning("WhatsApp Disabled", "Cannot send test message because WhatsApp is disabled."); return
        ownerno = self.ownerno_var.get().strip(); row = _get_db_config_row()
        provider_config = {'provider': row.get('whatsapp_provider') or 'twilio', 'account_sid': row.get('whatsapp_account_sid'), 'auth_token': row.get('whatsapp_auth_token'), 'from_whatsapp': row.get('whatsapp_from_whatsapp')} if row and row.get('whatsapp_account_sid') else {'provider': 'twilio' if self.sid_var.get() else 'mock', 'account_sid': self.sid_var.get().strip(), 'auth_token': self.token_var.get().strip(), 'from_whatsapp': self.from_var.get().strip()}
        if provider_config.get('provider') == 'twilio' and not all(provider_config.get(k) for k in ['account_sid', 'auth_token', 'from_whatsapp']): messagebox.showerror("Missing Information", "Please fill in all Twilio configuration fields."); return
        threading.Thread(target=self._execute_simple_test_send, args=(provider_config, ownerno), daemon=True).start()
    def _execute_simple_test_send(self, provider_config, recipient):
        logging.info("Sending simple test message..."); result = whatsapp_sender.send_text(provider_config, recipient, "This is a simple test message to confirm Twilio is working.")
        self.after(0, self._show_test_result, result, "Simple Test")
    def send_ticket_test_message(self):
        if not self.whatsapp_enabled_var.get(): messagebox.showwarning("WhatsApp Disabled", "Cannot send test message because WhatsApp is disabled."); return
        ticket_no_str = self.test_ticket_no_var.get();
        if not ticket_no_str.isdigit(): messagebox.showerror("Invalid Input", "Please enter a valid ticket number."); return
        self.save_config(); self.test_ticket_button.config(state=tk.DISABLED); row = _get_db_config_row()
        config = {'ownerno': row.get('ownerno') if row else self.ownerno_var.get(), 'poll_interval_seconds': row.get('poll_interval_seconds') if row else int(self.poll_interval_var.get())}
        provider = {'provider': row.get('whatsapp_provider') or 'twilio', 'account_sid': row.get('whatsapp_account_sid'), 'auth_token': row.get('whatsapp_auth_token'), 'from_whatsapp': row.get('whatsapp_from_whatsapp')} if row and row.get('whatsapp_account_sid') else {}
        worker = WhatsAppWorker(config=config, provider_config=provider, stop_event=threading.Event())
        threading.Thread(target=self._execute_ticket_test_send, args=(worker, int(ticket_no_str)), daemon=True).start()
    def _execute_ticket_test_send(self, worker, ticket_no):
        worker.process_single_ticket(ticket_no, is_test=True); self.after(0, lambda: self.test_ticket_button.config(state=tk.NORMAL))
    def _show_test_result(self, result, test_type):
        status, details = result.get('status'), result.get('details'); logging.info(f"{test_type} result: {status} - {details}")
        if status in ('sent', 'mock'): messagebox.showinfo(f"{test_type} Succeeded", f"Successfully sent test message!\n\nDetails: {details}")
        else: messagebox.showerror(f"{test_type} Failed", f"Failed to send test message.\n\nReason: {details}")

    def process_log_queue(self):
        while not self.log_queue.empty():
            message = self.log_queue.get(); self.log_text.config(state='normal'); self.log_text.insert(tk.END, message + '\n'); self.log_text.config(state='disabled'); self.log_text.see(tk.END)
        self.after(100, self.process_log_queue)
    def _on_closing(self):
        if self.worker_thread and self.worker_thread.is_alive():
            if messagebox.askokcancel("Quit", "The manager is still running. Do you want to stop it and quit?"): self.stop_worker(); self.after(2100, self.destroy)
        else: self.destroy()

if __name__ == "__main__":
    app = App()
    app.mainloop()
