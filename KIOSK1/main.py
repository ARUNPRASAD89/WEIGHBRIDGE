import sys, logging
from logging.handlers import RotatingFileHandler
from PyQt5.QtWidgets import QApplication, QDialog, QMessageBox
from PyQt5.QtCore import QCoreApplication

# --- MODIFIED: Import TransactionWindow directly ---
from transaction_window import TransactionWindow

# --- MODIFIED: Import functions needed for direct login ---
from db_utils import get_user_permissions, fetch_one

# --- Logging setup remains the same ---
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
log_file = 'weighbridge_app.log'

file_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=2)
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.INFO)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(log_formatter)
stream_handler.setLevel(logging.INFO)

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(stream_handler)


# --- MODIFIED: Main application startup logic for direct launch ---
if __name__ == "__main__":
    app = QApplication(sys.argv)

    # --- 1. SET YOUR HARDCODED LOGIN CREDENTIALS HERE ---
    AUTO_LOGIN_USERNAME = "1"
    AUTO_LOGIN_PASSWORD = "1"

    # --- 2. VALIDATE THE USER DIRECTLY (NO UI) ---
    user_record = fetch_one(
        "SELECT * FROM usermanagement WHERE username = %s AND password = %s",
        (AUTO_LOGIN_USERNAME, AUTO_LOGIN_PASSWORD)
    )

    # --- 3. PROCEED IF LOGIN IS SUCCESSFUL ---
    if user_record:
        logger.info(f"Auto-login successful for user '{AUTO_LOGIN_USERNAME}'.")
        
        permissions = get_user_permissions(AUTO_LOGIN_USERNAME)
        
        if permissions is None:
            QMessageBox.critical(None, "Permission Error", 
                                 f"Could not retrieve permissions for user '{AUTO_LOGIN_USERNAME}'. Exiting.")
            sys.exit(1)

        # --- FINAL CHANGE: Open the TransactionWindow directly, skipping MainMenu ---
        logger.info("Skipping mode selection, opening TransactionWindow directly.")
        main_window = TransactionWindow(permissions=permissions)
        main_window.show()
        sys.exit(app.exec_())
    else:
        # If login fails, show an error and exit.
        logger.error(f"Auto-login failed for user '{AUTO_LOGIN_USERNAME}'. Invalid credentials.")
        QMessageBox.critical(None, "Auto-Login Failed", 
                             f"Invalid credentials for user '{AUTO_LOGIN_USERNAME}'. Please check the hardcoded login details in main.py.")
        sys.exit(1)
