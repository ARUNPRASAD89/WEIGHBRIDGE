import sys
from PyQt5.QtWidgets import QApplication, QDialog, QMessageBox
from login_window import LoginWindow
from main_menu import MainMenu
from db_utils import get_user_permissions

if __name__ == "__main__":
    app = QApplication(sys.argv)
    login = LoginWindow()
    
    if login.exec_() == QDialog.Accepted:
        username = login.get_username()
        permissions = get_user_permissions(username)
        
        # 1. Check if permissions were fetched successfully
        if permissions is None:
            QMessageBox.critical(None, "Permission Error", 
                                 f"Could not retrieve permissions for user '{username}'. Exiting.")
            sys.exit(1)

        # The old, faulty permission check has been removed.
        # The MainMenuForm will now correctly handle enabling/disabling buttons.
        
        main_menu = MainMenu(permissions=permissions, parent=login)
        main_menu.show()
        sys.exit(app.exec_())
    else:
        # User cancelled the login
        sys.exit(0)
