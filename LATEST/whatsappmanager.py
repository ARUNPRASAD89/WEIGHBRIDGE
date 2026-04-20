import os
import time
import logging
import yaml
from db_utils import fetch_one, execute_query
import ticket_renderer
import whatsapp_sender

# --- Basic Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SafeDict(dict):
    """A dict that returns {key} if the key is missing, for safe .format() calls."""
    def __missing__(self, key):
        return f"{{{key}}}"

class WhatsAppManager:
    def __init__(self, config_path="config.yaml"):
        self.config = self._load_config(config_path)
        self.ownerno = self.config['ownerno']
        self.poll_interval = self.config.get('poll_interval_seconds', 10)
        self.provider_config = self.config['whatsapp_provider']
        
        # *** NEW: Load settings from the database ***
        self.settings = fetch_one("SELECT * FROM whatsappsettings WHERE id = 1")
        if not self.settings:
            logger.error("CRITICAL: Could not load settings from 'whatsappsettings' table. Manager cannot run.")
            # Set a flag to prevent the run loop from starting
            self.initialization_failed = True
            return
        
        self.initialization_failed = False
        self.output_dir = self.settings.get('imagedirectory', 'generated_tickets')
        
        self.last_processed_ticket_id = self._get_initial_ticket_id()
        logger.info(f"Manager starting. Will process tickets > {self.last_processed_ticket_id}")

    def _load_config(self, path):
        with open(path, 'r') as f:
            return yaml.safe_load(f)

    def _get_initial_ticket_id(self):
        last_sent = fetch_one("SELECT MAX(ticket_number) as max_id FROM whatsapp_sends")
        if last_sent and last_sent['max_id'] is not None:
            return int(last_sent['max_id'])
        latest_ticket = fetch_one('SELECT MAX("TicketNumber") as max_id FROM tickets')
        if latest_ticket and latest_ticket['max_id'] is not None:
            return int(latest_ticket['max_id'])
        return 0

    def _log_send_attempt(self, ticket_number, template_id, recipient, status, details, image_path=None):
        execute_query(
            "INSERT INTO whatsapp_sends (ticket_number, template_id, recipient, status, details, generated_image_path, sent_at) VALUES (%s, %s, %s, %s, %s, %s, NOW())",
            (ticket_number, template_id, recipient, status, details, image_path)
        )

    def _format_message(self, message_template, ticket_data):
        return message_template.format_map(SafeDict(ticket_data))

    def process_new_tickets(self):
        new_tickets = execute_query('SELECT * FROM tickets WHERE "TicketNumber" > %s ORDER BY "TicketNumber" ASC', (self.last_processed_ticket_id,))
        if not new_tickets:
            return

        # *** CORRECTED LOGIC: Use settings from DB, not the 'is_active' flag ***
        message_content_template = fetch_one("SELECT * FROM whatsapp_templates LIMIT 1")
        if not message_content_template:
            logger.error("No templates found in 'whatsapp_templates' table. Cannot create messages.")
            return

        logger.info(f"Found {len(new_tickets)} new ticket(s). Using content from template '{message_content_template['name']}'.")
        
        send_mode_image = self.settings.get('imagewithtext', False)
        send_mode_text = self.settings.get('textonly', True)

        if not send_mode_image and not send_mode_text:
            logger.warning("No send mode is enabled in settings (Image or Text). Skipping processing.")
            return

        for ticket in new_tickets:
            ticket_number = ticket['TicketNumber']
            logger.info(f"Processing Ticket #{ticket_number}...")
            status, details, image_path = "failed", "Unknown error", None
            
            try:
                if send_mode_image:
                    logger.info(f"Mode: 'Image with Text'. Generating image for ticket {ticket_number} to '{self.output_dir}'.")
                    bg_image_path = self.settings.get('bggroundimagedirectory')
                    image_path, _ = ticket_renderer.render_ticket(
                        ticket_number, 
                        message_content_template['template_name_for_image'], 
                        self.output_dir,
                        bg_image_path=bg_image_path
                    )
                    caption = self._format_message(message_content_template['image_caption'], ticket)
                    result = whatsapp_sender.send_media(self.provider_config, self.ownerno, caption, image_path)
                    status, details = result['status'], result['details']
                
                elif send_mode_text:
                    logger.info(f"Mode: 'Text Only'. Formatting text for ticket {ticket_number}.")
                    message = self._format_message(message_content_template['message_template'], ticket)
                    result = whatsapp_sender.send_text(self.provider_config, self.ownerno, message)
                    status, details = result['status'], result['details']

            except Exception as e:
                status, details = "failed", str(e)
                logger.exception(f"CRITICAL ERROR processing ticket {ticket_number}")
            
            finally:
                template_id_to_log = message_content_template.get('id') if message_content_template else None
                self._log_send_attempt(ticket_number, template_id_to_log, self.ownerno, status, details, image_path)
                self.last_processed_ticket_id = ticket_number
                logger.info(f"Finished Ticket #{ticket_number}. Status: {status}")

    def run(self):
        if getattr(self, 'initialization_failed', False):
            logger.error("Manager did not start due to an initialization error.")
            return

        logger.info("WhatsApp Manager is running. Press Ctrl+C to stop.")
        while True:
            try:
                self.process_new_tickets()
                time.sleep(self.poll_interval)
            except KeyboardInterrupt:
                logger.info("Shutdown signal received. Exiting.")
                break
            except Exception:
                logger.exception("An unexpected error occurred in the main loop. Retrying after delay.")
                time.sleep(self.poll_interval * 2)

if __name__ == "__main__":
    manager = WhatsAppManager()
    manager.run()
