# Updated whatsapp_gui.py — now reads/writes Twilio config to/from the weighbridge_config DB table.
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import os
import yaml
import threading
import time
import logging
from queue import Queue

from db_utils import fetch_one, execute_query
import ticket_renderer
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
        """
        Defensive init:
        - Accepts either (config, provider_config, stop_event)
        - or older misordered calls (config, stop_event)
        - If provider_config is empty, try to read it from weighbridge_config in the DB.
        """
        import threading
        # Handle callers that passed Event as second positional arg
        if isinstance(provider_config, threading.Event) and stop_event is None:
            logging.warning("WhatsAppWorker called with an Event in place of provider_config — treating it as stop_event and setting provider_config to {}.")
            stop_event = provider_config
            provider_config = {}

        # Normalize provider_config
        if provider_config is None:
            provider_config = {}

        # Ensure a stop_event exists
        if stop_event is None:
            stop_event = threading.Event()
            logging.warning("WhatsAppWorker.__init__ called without stop_event — created internal Event().")

        self.config = config or {}
        self.ownerno = self.config.get('ownerno')
        self.poll_interval = int(self.config.get('poll_interval_seconds', 10))
        self.provider_config = provider_config or {}
        self.stop_event = stop_event

        # If provider_config is empty, try to load shared provider from DB (weighbridge_config)
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
                    logging.info("WhatsAppWorker: loaded provider_config from weighbridge_config DB row.")
                else:
                    logging.warning("WhatsAppWorker: no provider_config provided and DB row missing or incomplete — using mock provider.")
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
        logging.debug(f"WhatsAppWorker initialized: ownerno={self.ownerno}, poll_interval={self.poll_interval}, stop_event_set={self.stop_event.is_set()}, provider_type={type(self.provider_config)}")
    
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
            if is_test:
                messagebox.showerror("Test Failed", f"Ticket number {ticket_number} not found.")
            return

        send_mode_image = self.settings.get('imagewithtext', False)
        send_mode_text = self.settings.get('textonly', True)

        message_template = None
        if send_mode_image:
            message_template = fetch_one("SELECT * FROM whatsapp_templates WHERE image_caption IS NOT NULL AND image_caption != '' LIMIT 1")
            if not message_template:
                logging.error("Send mode is 'Image', but no suitable template was found in 'whatsapp_templates' table with a valid 'image_caption'.")
                if is_test:
                    messagebox.showerror("Test Failed", "Send mode is 'Image', but no suitable image caption template was found.")
                return
        elif send_mode_text:
            message_template = fetch_one("SELECT * FROM whatsapp_templates WHERE message_template IS NOT NULL AND message_template != '' LIMIT 1")
            if not message_template:
                logging.error("Send mode is 'Text', but no suitable template was found in 'whatsapp_templates' table with a valid 'message_template'.")
                if is_test:
                    messagebox.showerror("Test Failed", "Send mode is 'Text', but no suitable text template was found.")
                return

        logging.info(f"Processing Ticket #{ticket_number}...")
        status, details, image_path = "failed", "Unknown error", None

        try:
            if send_mode_image:
                logging.info(f"Mode: 'Image with Text'. Calling renderer for ticket {ticket_number}...")
                bg_image_path = self.settings.get('bggroundimagedirectory')
                image_path, _ = ticket_renderer.render_ticket(ticket_number, self.output_dir, bg_image_path=bg_image_path)
                caption = self._format_message(message_template['image_caption'], ticket)
                logging.info(f"Rendering complete. Calling sender for image at '{image_path}'...")
                result = whatsapp_sender.send_media(self.provider_config, self.ownerno, caption, image_path)
                status, details = result['status'], result['details']
            elif send_mode_text:
                logging.info(f"Mode: 'Text Only'. Formatting text for ticket {ticket_number}...")
                message = self._format_message(message_template['message_template'], ticket)
                logging.info("Formatting complete. Calling sender...")
                result = whatsapp_sender.send_text(self.provider_config, self.ownerno, message)
                status, details = result['status'], result['details']
        except Exception as e:
            status, details = "failed", str(e)
            logging.exception(f"CRITICAL ERROR processing ticket {ticket_number}: {e}")
            if is_test:
                messagebox.showerror("Test Failed", f"A critical error occurred:\n\n{e}")

        finally:
            if not is_test:
                template_id = message_template.get('id') if message_template else None
                self._log_send_attempt(ticket_number, template_id, self.ownerno, status, details, image_path)
                self.last_processed_ticket_id = ticket_number
            logging.info(f"Finished processing Ticket #{ticket_number}. Status: {status}")
            if is_test:
                if status in ('sent', 'mock'):
                    messagebox.showinfo("Test Succeeded", f"Test for ticket {ticket_number} completed with status: {status}\n\nDetails: {details}")
                else:
                    messagebox.showerror("Test Failed", f"Test for ticket {ticket_number} failed.\n\nStatus: {status}\nReason: {details}")

    def process_new_tickets(self):
        new_tickets = execute_query('SELECT * FROM tickets WHERE "TicketNumber" > %s ORDER BY "TicketNumber" ASC', (self.last_processed_ticket_id,))
        if not new_tickets:
            return
        for ticket in new_tickets:
            if self.stop_event.is_set():
                break
            self.process_single_ticket(ticket['TicketNumber'])

    def run(self):
        if self.stop_event.is_set():
            logging.error("Worker did not start due to critical error on initialization.")
            return
        while not self.stop_event.is_set():
            try:
                self.process_new_tickets()
                for _ in range(int(self.poll_interval)):
                    if self.stop_event.is_set(): break
                    time.sleep(1)
            except Exception as e:
                logging.exception(f"An unhandled error occurred in the main worker loop: {e}")
                time.sleep(self.poll_interval * 2)
        logging.info("WhatsApp Worker has stopped.")

# --- Helper DB functions for config (we use weighbridge_config with config_name='default') ---
def _get_db_config_row():
    row = fetch_one("SELECT * FROM weighbridge_config WHERE config_name = %s", ('default',))
    return row

def _upsert_db_config(ownerno, poll_interval_seconds, provider):
    # provider is a dict with account_sid, auth_token, from_whatsapp, provider
    execute_query("""
        INSERT INTO weighbridge_config
            (config_name, ownerno, poll_interval_seconds, whatsapp_account_sid, whatsapp_auth_token, whatsapp_from_whatsapp, whatsapp_provider)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (config_name) DO UPDATE SET
            ownerno = EXCLUDED.ownerno,
            poll_interval_seconds = EXCLUDED.poll_interval_seconds,
            whatsapp_account_sid = EXCLUDED.whatsapp_account_sid,
            whatsapp_auth_token = EXCLUDED.whatsapp_auth_token,
            whatsapp_from_whatsapp = EXCLUDED.whatsapp_from_whatsapp,
            whatsapp_provider = EXCLUDED.whatsapp_provider,
            updated_at = NOW()
    """, (
        'default',
        ownerno,
        poll_interval_seconds,
        provider.get('account_sid'),
        provider.get('auth_token'),
        provider.get('from_whatsapp'),
        provider.get('provider'),
    ))

def _clear_whatsapp_credentials():
    execute_query("""
        UPDATE weighbridge_config
        SET whatsapp_account_sid = NULL,
            whatsapp_auth_token = NULL,
            whatsapp_from_whatsapp = NULL,
            whatsapp_provider = 'mock',
            updated_at = NOW()
        WHERE config_name = %s
    """, ('default',))

# --- The GUI Application ---
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Weighbridge WhatsApp Manager")
        self.geometry("800x600")
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.config_path = "config.yaml"
        self.worker_thread = None
        self.stop_event = threading.Event()
        self.log_queue = Queue()
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.INFO)
        queue_handler = QueueHandler(self.log_queue)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        queue_handler.setFormatter(formatter)
        if not self.logger.handlers:
            self.logger.addHandler(queue_handler)
        self._create_widgets()
        self.load_config()
        self.after(100, self.process_log_queue)

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        twilio_frame = ttk.LabelFrame(main_frame, text="Twilio Configuration", padding="10")
        twilio_frame.pack(fill=tk.X, expand=False, pady=(0, 10))
        twilio_frame.columnconfigure(1, weight=1)
        self.ownerno_var = tk.StringVar(); self.sid_var = tk.StringVar(); self.token_var = tk.StringVar(); self.from_var = tk.StringVar(); self.poll_interval_var = tk.StringVar(value="10")
        ttk.Label(twilio_frame, text="Owner No:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(twilio_frame, textvariable=self.ownerno_var).grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        ttk.Label(twilio_frame, text="Twilio SID:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(twilio_frame, textvariable=self.sid_var).grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW)
        ttk.Label(twilio_frame, text="Twilio Token:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(twilio_frame, textvariable=self.token_var, show="*").grid(row=2, column=1, padx=5, pady=5, sticky=tk.EW)
        ttk.Label(twilio_frame, text="Twilio From No:").grid(row=3, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(twilio_frame, textvariable=self.from_var).grid(row=3, column=1, padx=5, pady=5, sticky=tk.EW)
        ttk.Label(twilio_frame, text="Poll Interval (s):").grid(row=4, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(twilio_frame, textvariable=self.poll_interval_var).grid(row=4, column=1, padx=5, pady=5, sticky=tk.EW)

        whatsapp_settings_frame = ttk.LabelFrame(main_frame, text="WhatsApp Settings", padding="10")
        whatsapp_settings_frame.pack(fill=tk.X, expand=False, pady=(0, 10))
        whatsapp_settings_frame.columnconfigure(1, weight=1)
        self.image_path_var = tk.StringVar(); self.imagewithtext_var = tk.BooleanVar(); self.textonly_var = tk.BooleanVar()
        self.bg_image_path_var = tk.StringVar()

        ttk.Label(whatsapp_settings_frame, text="Image Save Path:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(whatsapp_settings_frame, textvariable=self.image_path_var).grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)

        ttk.Label(whatsapp_settings_frame, text="Background Image:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        bg_frame = ttk.Frame(whatsapp_settings_frame)
        bg_frame.grid(row=1, column=1, sticky=tk.EW)
        bg_frame.columnconfigure(0, weight=1)
        ttk.Entry(bg_frame, textvariable=self.bg_image_path_var).grid(row=0, column=0, sticky=tk.EW, padx=(0, 5))
        ttk.Button(bg_frame, text="Browse...", command=self._browse_bg_image).grid(row=0, column=1)

        check_frame = ttk.Frame(whatsapp_settings_frame)
        check_frame.grid(row=2, column=0, columnspan=2, pady=5, sticky='w')
        ttk.Checkbutton(check_frame, text="Send Image with Text", variable=self.imagewithtext_var, command=self._on_check_change).pack(side=tk.LEFT, padx=10)
        ttk.Checkbutton(check_frame, text="Send Text Only", variable=self.textonly_var, command=self._on_check_change).pack(side=tk.LEFT, padx=10)

        button_row = ttk.Frame(main_frame)
        button_row.pack(fill=tk.X, pady=5)
        ttk.Button(button_row, text="Save All Configurations", command=self.save_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_row, text="Clear Credentials", command=self.clear_credentials).pack(side=tk.LEFT, padx=5)

        control_frame = ttk.LabelFrame(main_frame, text="Controls", padding="10")
        control_frame.pack(fill=tk.X, expand=False, pady=5)
        self.start_button = ttk.Button(control_frame, text="Start Manager", command=self.start_worker); self.start_button.pack(side=tk.LEFT, padx=5)
        self.stop_button = ttk.Button(control_frame, text="Stop Manager", command=self.stop_worker, state=tk.DISABLED); self.stop_button.pack(side=tk.LEFT, padx=5)

        test_frame = ttk.LabelFrame(main_frame, text="Testing", padding="10")
        test_frame.pack(fill=tk.X, expand=False, pady=5)
        self.test_ticket_no_var = tk.StringVar()
        ttk.Label(test_frame, text="Test with Ticket #:").pack(side=tk.LEFT, padx=5)
        ttk.Entry(test_frame, textvariable=self.test_ticket_no_var, width=10).pack(side=tk.LEFT, padx=5)
        self.test_ticket_button = ttk.Button(test_frame, text="Send Test with Ticket", command=self.send_ticket_test_message); self.test_ticket_button.pack(side=tk.LEFT, padx=5)
        ttk.Button(test_frame, text="Send Simple Test", command=self.send_simple_test_message).pack(side=tk.LEFT, padx=15)

        log_frame = ttk.LabelFrame(main_frame, text="Live Log", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.log_text = scrolledtext.ScrolledText(log_frame, state='disabled', wrap=tk.WORD, height=10); self.log_text.pack(fill=tk.BOTH, expand=True)

    def _browse_bg_image(self):
        file_path = filedialog.askopenfilename(
            title="Select a Background Image",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp"), ("All files", "*.*")]
        )
        if file_path:
            self.bg_image_path_var.set(file_path)

    def _on_check_change(self):
        if self.imagewithtext_var.get(): self.textonly_var.set(False)
        elif self.textonly_var.get(): self.imagewithtext_var.set(False)

    def load_config(self):
        """
        Load Twilio config from weighbridge_config if available; fallback to config.yaml for convenience.
        Also load whatsappsettings table into GUI fields.
        """
        try:
            row = _get_db_config_row()
            if row:
                # Map DB columns to GUI fields
                self.ownerno_var.set(row.get('ownerno') or '')
                self.sid_var.set(row.get('whatsapp_account_sid') or '')
                self.token_var.set(row.get('whatsapp_auth_token') or '')
                self.from_var.set(row.get('whatsapp_from_whatsapp') or '')
                self.poll_interval_var.set(str(row.get('poll_interval_seconds') or 10))
                logging.info("Loaded Twilio config from DB (weighbridge_config).")
            else:
                # fallback to local YAML if present
                if os.path.exists(self.config_path):
                    with open(self.config_path, 'r') as f:
                        config = yaml.safe_load(f)
                    self.ownerno_var.set(config.get('ownerno', ''))
                    provider = config.get('whatsapp_provider', {})
                    self.sid_var.set(provider.get('account_sid', '')); self.token_var.set(provider.get('auth_token', '')); self.from_var.set(provider.get('from_whatsapp', ''))
                    self.poll_interval_var.set(config.get('poll_interval_seconds', 10))
                    logging.info("Loaded Twilio config from local config.yaml (fallback).")
                else:
                    logging.info("No DB config and no local config.yaml found. Fields left empty.")
        except Exception as e:
            logging.error(f"Failed to load weighbridge_config from DB: {e}")

        try:
            settings = fetch_one("SELECT * FROM whatsappsettings WHERE id = 1")
            if settings:
                self.image_path_var.set(settings.get('imagedirectory', 'generated_tickets'))
                self.imagewithtext_var.set(bool(settings.get('imagewithtext', False)))
                self.textonly_var.set(bool(settings.get('textonly', True)))
                self.bg_image_path_var.set(settings.get('bggroundimagedirectory', ''))
                logging.info("WhatsApp settings loaded successfully.")
            else:
                logging.warning("Could not find settings in 'whatsappsettings' table. Using defaults.")
        except Exception as e:
            logging.error(f"Failed to load from DB. Using defaults. Error: {e}")
            messagebox.showerror("Database Error", f"Could not load WhatsApp settings from the database:\n{e}")

    def save_config(self):
        try:
            poll_interval = int(self.poll_interval_var.get())
        except ValueError:
            messagebox.showerror("Invalid Input", "Poll interval must be a valid number.")
            return
        if poll_interval < 1:
            messagebox.showerror("Invalid Input", "Poll interval must be at least 1 second.")
            return

        provider = {
            'provider': 'twilio' if self.sid_var.get() else 'mock',
            'account_sid': self.sid_var.get(),
            'auth_token': self.token_var.get(),
            'from_whatsapp': self.from_var.get()
        }

        try:
            # Upsert into weighbridge_config
            _upsert_db_config(self.ownerno_var.get().strip(), poll_interval, provider)
        except Exception as e:
            logging.error(f"Failed to save weighbridge_config: {e}")
            messagebox.showerror("Database Error", f"Could not save configuration to DB:\n{e}")
            return

        # Save whatsappsettings as before
        try:
            image_path = self.image_path_var.get().strip()
            if not image_path:
                messagebox.showerror("Invalid Input", "Image Save Path cannot be empty.")
                return

            execute_query(
                "UPDATE whatsappsettings SET imagedirectory=%s, imagewithtext=%s, textonly=%s, bggroundimagedirectory=%s WHERE id=1",
                (image_path, self.imagewithtext_var.get(), self.textonly_var.get(), self.bg_image_path_var.get().strip())
            )
            logging.info("All configurations saved successfully.")
            messagebox.showinfo("Success", "All configurations were saved successfully!")
        except Exception as e:
            logging.error(f"Failed to save settings to DB: {e}")
            messagebox.showerror("Database Error", f"Could not save WhatsApp settings to the database:\n{e}")
            return

    def clear_credentials(self):
        if not messagebox.askyesno("Confirm", "This will remove Twilio credentials from the shared config. Continue?"):
            return
        try:
            _clear_whatsapp_credentials()
            # Clear GUI fields
            self.sid_var.set(''); self.token_var.set(''); self.from_var.set('')
            messagebox.showinfo("Cleared", "Twilio credentials removed from database.")
            logging.info("Twilio credentials cleared from weighbridge_config.")
        except Exception as e:
            logging.error(f"Failed to clear credentials: {e}")
            messagebox.showerror("Database Error", f"Could not clear credentials:\n{e}")

    def start_worker(self):
        # Save GUI state to DB first
        self.save_config()
        self.stop_event.clear()
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)

        # Load latest config and provider from DB
        row = _get_db_config_row()
        config = {
            'ownerno': row.get('ownerno') if row else self.ownerno_var.get(),
            'poll_interval_seconds': row.get('poll_interval_seconds') if row else int(self.poll_interval_var.get())
        }
        provider = {}
        if row and row.get('whatsapp_provider') and row.get('whatsapp_account_sid'):
            provider = {
                'provider': row.get('whatsapp_provider') or 'twilio',
                'account_sid': row.get('whatsapp_account_sid'),
                'auth_token': row.get('whatsapp_auth_token'),
                'from_whatsapp': row.get('whatsapp_from_whatsapp'),
            }
        else:
            # Fallback to GUI fields
            provider = {
                'provider': 'twilio' if self.sid_var.get() else 'mock',
                'account_sid': self.sid_var.get(),
                'auth_token': self.token_var.get(),
                'from_whatsapp': self.from_var.get(),
            }

        # Use keyword args to avoid accidental positional-argument misordering
        worker = WhatsAppWorker(config=config, provider_config=provider, stop_event=self.stop_event)
        self.worker_thread = threading.Thread(target=worker.run, daemon=True)
        self.worker_thread.start()

    def stop_worker(self):
        if hasattr(self, 'status_var'):
            self.status_var.set("Status: Stopping...")
        self.stop_event.set()
        self.stop_button.config(state=tk.DISABLED)
        self.after(2000, self._check_thread_stopped)

    def _check_thread_stopped(self):
        if self.worker_thread and self.worker_thread.is_alive():
            self.after(1000, self._check_thread_stopped)
        else:
            self.start_button.config(state=tk.NORMAL)
            if hasattr(self, 'status_var'):
                self.status_var.set("Status: Stopped")
            logging.info("Manager stopped by user.")

    def send_simple_test_message(self):
        ownerno = self.ownerno_var.get().strip()
        # Don't rely on GUI values for provider; read DB live to ensure exact behavior
        row = _get_db_config_row()
        if row and row.get('whatsapp_account_sid'):
            provider_config = {
                'provider': row.get('whatsapp_provider') or 'twilio',
                'account_sid': row.get('whatsapp_account_sid'),
                'auth_token': row.get('whatsapp_auth_token'),
                'from_whatsapp': row.get('whatsapp_from_whatsapp'),
            }
        else:
            # GUI fallback
            sid = self.sid_var.get().strip(); token = self.token_var.get().strip(); from_no = self.from_var.get().strip()
            provider_config = {'provider': 'twilio' if sid else 'mock', 'account_sid': sid, 'auth_token': token, 'from_whatsapp': from_no}

        if provider_config.get('provider') == 'twilio' and not all([provider_config.get('account_sid'), provider_config.get('auth_token'), provider_config.get('from_whatsapp')]):
            messagebox.showerror("Missing Information", "Please fill in all Twilio configuration fields in the GUI or set them via the shared DB.")
            return

        threading.Thread(target=self._execute_simple_test_send, args=(provider_config, ownerno), daemon=True).start()

    def _execute_simple_test_send(self, provider_config, recipient):
        logging.info("Sending simple test message...")
        result = whatsapp_sender.send_text(provider_config, recipient, "This is a simple test message to confirm Twilio is working.")
        self.after(0, self._show_test_result, result, "Simple Test")

    def send_ticket_test_message(self):
        ticket_no_str = self.test_ticket_no_var.get()
        if not ticket_no_str.isdigit():
            messagebox.showerror("Invalid Input", "Please enter a valid ticket number.")
            return

        self.save_config()
        self.test_ticket_button.config(state=tk.DISABLED)
        row = _get_db_config_row()
        config = {
            'ownerno': row.get('ownerno') if row else self.ownerno_var.get(),
            'poll_interval_seconds': row.get('poll_interval_seconds') if row else int(self.poll_interval_var.get())
        }
        provider = {}
        if row and row.get('whatsapp_account_sid'):
            provider = {
                'provider': row.get('whatsapp_provider') or 'twilio',
                'account_sid': row.get('whatsapp_account_sid'),
                'auth_token': row.get('whatsapp_auth_token'),
                'from_whatsapp': row.get('whatsapp_from_whatsapp'),
            }
        # Use keyword args to avoid positional mistakes
        worker = WhatsAppWorker(config=config, provider_config=provider, stop_event=threading.Event())
        threading.Thread(target=self._execute_ticket_test_send, args=(worker, int(ticket_no_str)), daemon=True).start()

    def _execute_ticket_test_send(self, worker, ticket_no):
        worker.process_single_ticket(ticket_no, is_test=True)
        self.after(0, lambda: self.test_ticket_button.config(state=tk.NORMAL))

    def _show_test_result(self, result, test_type):
        status, details = result.get('status'), result.get('details')
        logging.info(f"{test_type} result: {status} - {details}")
        if status in ('sent', 'mock'):
            messagebox.showinfo(f"{test_type} Succeeded", f"Successfully sent test message!\n\nDetails: {details}")
        else:
            messagebox.showerror(f"{test_type} Failed", f"Failed to send test message.\n\nReason: {details}")

    def process_log_queue(self):
        while not self.log_queue.empty():
            message = self.log_queue.get()
            self.log_text.config(state='normal')
            self.log_text.insert(tk.END, message + '\n')
            self.log_text.config(state='disabled')
            self.log_text.see(tk.END)
        self.after(100, self.process_log_queue)

    def _on_closing(self):
        if self.worker_thread and self.worker_thread.is_alive():
            if messagebox.askokcancel("Quit", "The manager is still running. Do you want to stop it and quit?"):
                self.stop_worker()
                self.after(2100, self.destroy)
        else:
            self.destroy()

if __name__ == "__main__":
    app = App()
    app.mainloop()
