import os
from datetime import datetime
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QPushButton, QMessageBox, QFileDialog, QLabel,
    QSizePolicy, QApplication
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
from backup_utils import backup_database

class BackupWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Database Backup")
        self.setMinimumSize(400, 220)

        # --- UI Setup ---
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        main_layout.setAlignment(Qt.AlignCenter)

        info_label = QLabel(
            "Click the button below to create a complete backup of the database.\n\n"
            "You will be asked to choose a location to save the backup as a .sql file."
        )
        info_label.setFont(QFont("Arial", 10))
        info_label.setWordWrap(True)
        info_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(info_label)

        main_layout.addStretch()

        self.backup_button = QPushButton("Create Database Backup")
        self.backup_button.setFont(QFont("Arial", 12, QFont.Bold))
        self.backup_button.setMinimumHeight(50)
        self.backup_button.clicked.connect(self.perform_backup)
        main_layout.addWidget(self.backup_button)

        self.exit_button = QPushButton("Exit")
        self.exit_button.setMinimumHeight(40)
        self.exit_button.clicked.connect(self.close)
        main_layout.addWidget(self.exit_button)

    def perform_backup(self):
        """
        Handles the process of creating a database backup.
        """
        # 1. Define the default directory and filename
        backup_dir = os.path.join(os.getcwd(), "backups")
        if not os.path.exists(backup_dir):
            try:
                os.makedirs(backup_dir)
            except OSError as e:
                QMessageBox.critical(self, "Error", f"Could not create backups directory:\n{e}")
                return

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        default_filename = f"weighbridge_backup_{timestamp}.sql"
        default_path = os.path.join(backup_dir, default_filename)

        # 2. Open the "Save File" dialog to let the user choose the location
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Database Backup",
            default_path,
            "SQL Backup Files (*.sql);;All Files (*)"
        )

        # 3. If a path was selected, perform the backup
        if save_path:
            self.backup_button.setEnabled(False)
            self.backup_button.setText("Backing up...")
            QApplication.processEvents() # Update the UI to show the new text

            success, message = backup_database(save_path)

            if success:
                QMessageBox.information(self, "Backup Successful", message)
            else:
                QMessageBox.critical(self, "Backup Failed", message)
            
            self.backup_button.setEnabled(True)
            self.backup_button.setText("Create Database Backup")

    def closeEvent(self, event):
        """Ensure parent window is shown on close if it exists."""
        if self.parent():
            self.parent().show()
        super().closeEvent(event)