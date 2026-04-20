# Updated whatsapp_sender.py — will fetch provider config from DB (weighbridge_config)
# and accepts either a dict provider_config, None, or a WhatsAppWorker-like object
# (duck-typed: has .provider_config and .ownerno). Ensures Twilio 'from' uses
# a whatsapp: prefix when needed and falls back to the mock provider.
import logging
import os
import requests
import time
from twilio.rest import Client
from db_utils import fetch_one

logger = logging.getLogger(__name__)

def _upload_to_catbox(file_path, retries=3, delay=2):
    if not os.path.exists(file_path):
        logger.error(f"[Uploader] File does not exist at path: {file_path}")
        return None

    for attempt in range(retries):
        try:
            with open(file_path, 'rb') as f:
                files = {'reqtype': (None, 'fileupload'), 'fileToUpload': (os.path.basename(file_path), f)}
                logger.info(f"[Uploader] Uploading '{os.path.basename(file_path)}' to temporary host (Attempt {attempt + 1}/{retries})...")
                response = requests.post('https://catbox.moe/user/api.php', files=files, timeout=30)
                if response.status_code == 200 and "catbox.moe" in response.text:
                    public_url = response.text.strip()
                    logger.info(f"[Uploader] Success! Public URL: {public_url}")
                    return public_url
                else:
                    logger.error(f"[Uploader] Failed to upload file on attempt {attempt + 1}. Status: {response.status_code}, Response: {response.text}")
        except requests.exceptions.RequestException as e:
            logger.error(f"[Uploader] A network exception occurred during file upload on attempt {attempt + 1}: {e}")
        except Exception as e:
            logger.error(f"[Uploader] A general exception occurred during file upload on attempt {attempt + 1}: {e}")

        if attempt < retries - 1:
            logger.info(f"Waiting {delay} seconds before retrying...")
            time.sleep(delay)

    logger.error("All upload attempts failed.")
    return None

def _get_provider_config_from_db():
    """
    Read the shared provider config from weighbridge_config row config_name='default'
    Returns dict with keys: provider, account_sid, auth_token, from_whatsapp
    """
    try:
        row = fetch_one("SELECT * FROM weighbridge_config WHERE config_name = %s", ('default',))
    except Exception as e:
        logger.exception(f"Failed to fetch weighbridge_config from DB: {e}")
        return None
    if not row:
        return None
    return {
        'provider': row.get('whatsapp_provider') or 'mock',
        'account_sid': row.get('whatsapp_account_sid'),
        'auth_token': row.get('whatsapp_auth_token'),
        'from_whatsapp': row.get('whatsapp_from_whatsapp'),
    }

def _ensure_whatsapp_prefix(number_or_id):
    if not number_or_id:
        return number_or_id
    if str(number_or_id).startswith("whatsapp:"):
        return number_or_id
    return f"whatsapp:{number_or_id}"

def _resolve_provider_and_recipient(provider_config, recipient):
    """
    Accepts:
      - provider_config: dict (existing behavior)
      - provider_config: None -> read from DB
      - provider_config: a WhatsAppWorker-like object that exposes .provider_config and .ownerno
    Returns (resolved_provider_config_dict, resolved_recipient)
    """
    # Detect worker-like object via duck-typing (avoid circular import)
    if provider_config is not None and not isinstance(provider_config, dict):
        # If it looks like a worker (has .provider_config and .ownerno), use it
        if hasattr(provider_config, 'provider_config') and hasattr(provider_config, 'ownerno'):
            worker = provider_config
            # If worker.provider_config is empty, try DB
            if not worker.provider_config:
                db_conf = _get_provider_config_from_db()
                worker.provider_config = db_conf or {}
                if db_conf:
                    logger.info("Resolved provider_config from DB for provided worker instance.")
            # use worker values
            resolved_config = dict(worker.provider_config) if worker.provider_config else {}
            if not recipient:
                recipient = worker.ownerno
            return resolved_config, recipient
        # If it's some other object, attempt to extract attribute-like dict
        if hasattr(provider_config, 'get'):
            # behave like dict-like
            resolved_config = dict(provider_config)
            return resolved_config, recipient
        # Fallback: treat as None
        provider_config = None

    # provider_config is dict or None
    if provider_config is None:
        resolved = _get_provider_config_from_db() or {'provider': 'mock'}
        return resolved, recipient

    # ensure a real dict copy
    return dict(provider_config), recipient

def send_text(provider_config, recipient, message):
    """Sends a text message using the configured provider. If provider_config is None, try DB.
       provider_config may also be a WhatsAppWorker-like object (duck-typed)."""
    provider_config, recipient = _resolve_provider_and_recipient(provider_config, recipient)

    provider = (provider_config.get("provider") or "mock").lower()

    if not recipient:
        logger.error("No recipient provided for send_text.")
        return {"status": "failed", "details": "No recipient provided"}

    if provider == "twilio":
        # Validate required Twilio fields
        account_sid = provider_config.get('account_sid')
        auth_token = provider_config.get('auth_token')
        from_whatsapp = provider_config.get('from_whatsapp')
        if not all([account_sid, auth_token, from_whatsapp]):
            logger.error("Twilio provider selected but account_sid/auth_token/from_whatsapp missing.")
            return {"status": "failed", "details": "Twilio credentials incomplete"}

        try:
            client = Client(account_sid, auth_token)
            from_whatsapp_prefixed = _ensure_whatsapp_prefix(from_whatsapp)
            message_obj = client.messages.create(
                from_=from_whatsapp_prefixed,
                body=message,
                to=_ensure_whatsapp_prefix(recipient)
            )
            logger.info(f"Twilio text message sent successfully! SID: {getattr(message_obj, 'sid', 'unknown')}")
            return {"status": "sent", "details": getattr(message_obj, 'sid', '')}
        except Exception as e:
            logger.exception(f"Twilio failed to send text: {e}")
            return {"status": "failed", "details": str(e)}
    else:  # Mock provider
        logger.info(f"--- MOCK WHATSAPP (To: {recipient}) ---")
        logger.info(f"Message: {message}")
        return {"status": "mock", "details": "Logged to console"}

def send_media(provider_config, recipient, caption, media_path):
    """
    Sends a media message using Twilio, uploading the local file to get a public URL first.
    provider_config may also be a WhatsAppWorker-like object (duck-typed).
    """
    provider_config, recipient = _resolve_provider_and_recipient(provider_config, recipient)

    provider = (provider_config.get("provider") or "mock").lower()

    absolute_media_path = os.path.abspath(media_path)
    logger.info(f"Resolved media path to absolute path: {absolute_media_path}")

    if not recipient:
        logger.error("No recipient provided for send_media.")
        return {"status": "failed", "details": "No recipient provided"}

    if provider == "twilio":
        public_media_url = _upload_to_catbox(absolute_media_path)
        if not public_media_url:
            logger.error("Failed to get public URL for media. Sending caption as a text message instead.")
            fallback_message = f"{caption}\n\n(Image was generated at {os.path.basename(media_path)}, but failed to upload for sending.)"
            return send_text(provider_config, recipient, fallback_message)

        account_sid = provider_config.get('account_sid')
        auth_token = provider_config.get('auth_token')
        from_whatsapp = provider_config.get('from_whatsapp')
        if not all([account_sid, auth_token, from_whatsapp]):
            logger.error("Twilio provider selected but account_sid/auth_token/from_whatsapp missing.")
            return {"status": "failed", "details": "Twilio credentials incomplete"}

        try:
            client = Client(account_sid, auth_token)
            from_whatsapp_prefixed = _ensure_whatsapp_prefix(from_whatsapp)
            message_obj = client.messages.create(
                from_=from_whatsapp_prefixed,
                body=caption,
                media_url=[public_media_url],
                to=_ensure_whatsapp_prefix(recipient)
            )
            logger.info(f"Twilio media message sent successfully! SID: {getattr(message_obj, 'sid', 'unknown')}")
            return {"status": "sent", "details": getattr(message_obj, 'sid', '')}
        except Exception as e:
            logger.exception(f"Twilio failed to send media message: {e}")
            return {"status": "failed", "details": str(e)}
    else:  # Mock provider
        logger.info(f"--- MOCK WHATSAPP (To: {recipient}) ---")
        logger.info(f"Caption: {caption}")
        logger.info(f"Image Path: {absolute_media_path}")
        return {"status": "mock", "details": f"Logged to console, image at {absolute_media_path}"}
