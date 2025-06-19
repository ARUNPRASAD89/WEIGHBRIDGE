import sys
from PyQt5.QtWidgets import QApplication
from db_utils import fetch_one
from login_window import LoginDialog      # Use LoginDialog, not LoginWindow
from vehicle_master import VehicleMaster  # Import VehicleMaster window

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Show the login dialog
    login_dialog = LoginDialog()
    if login_dialog.exec_() == LoginDialog.Accepted:
        username, password = login_dialog.get_credentials()
        # After successful login, show the main Vehicle Master window
        vehicle_master_window = VehicleMaster(username, password)
        vehicle_master_window.show()
        sys.exit(app.exec_())
    else:
        sys.exit(0)
