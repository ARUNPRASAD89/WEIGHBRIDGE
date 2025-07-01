import sys
from PyQt5.QtWidgets import QApplication, QDialog
from login_window import LoginWindow
from main_menu import MainMenu

if __name__ == "__main__":
    app = QApplication(sys.argv)
    login = LoginWindow()
    if login.exec_() == QDialog.Accepted:
        main_menu = MainMenu()
        main_menu.show()
        sys.exit(app.exec_())
    else:
        sys.exit(0)
