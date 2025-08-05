import sys
from PyQt5.QtWidgets import QApplication, QDialog
from login_window import LoginWindow
from main_menu import MainMenu
from db_utils import get_user_permissions

if __name__ == "__main__":
    app = QApplication(sys.argv)
    login = LoginWindow()
    
    if login.exec_() == QDialog.Accepted:
        username = login.get_username()
        permissions = get_user_permissions(username)
        
        # Ensure permissions dictionary exists and add username to it
        if permissions is None:
            permissions = {}
        permissions['username'] = username
        
        main_menu = MainMenu(permissions=permissions, parent=login)
        main_menu.show()
        sys.exit(app.exec_())
    else:
        sys.exit(0)
