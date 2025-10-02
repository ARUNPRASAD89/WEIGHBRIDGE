from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QCheckBox, QListWidget,
    QHBoxLayout, QVBoxLayout, QGridLayout, QGroupBox, QDialog, QFormLayout,
    QMessageBox
)
from PyQt5.QtCore import Qt
from db_utils import fetch_all, fetch_one, execute_query

class UserManager(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("User Manager")
        self.setFixedSize(560, 320)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # --- Top section: User Details and Existing Users ---
        top_layout = QHBoxLayout()
        top_layout.setSpacing(12)

        # User Details
        user_details = QGroupBox("User Details")
        user_form = QFormLayout()
        user_form.setLabelAlignment(Qt.AlignRight)
        
        self.name_edit = QLineEdit()
        user_form.addRow("Name:", self.name_edit)
        
        self.pwd_edit = QLineEdit()
        self.pwd_edit.setEchoMode(QLineEdit.Password)
        user_form.addRow("Password:", self.pwd_edit)
        
        self.conf_edit = QLineEdit()
        self.conf_edit.setEchoMode(QLineEdit.Password)
        user_form.addRow("Confirm Password:", self.conf_edit)
        
        self.admin_check = QCheckBox("Administrator")
        user_form.addRow(self.admin_check)
        
        user_details.setLayout(user_form)
        top_layout.addWidget(user_details)

        # Existing Users
        existing_users_group = QGroupBox("Existing Users")
        vbox = QVBoxLayout()
        self.user_list = QListWidget()
        vbox.addWidget(self.user_list)
        existing_users_group.setLayout(vbox)
        top_layout.addWidget(existing_users_group)

        main_layout.addLayout(top_layout)

        # --- Authorization section ---
        auth_group = QGroupBox("The user is authorized to")
        auth_layout = QHBoxLayout()
        self.duplicate_check = QCheckBox("Print duplicate tickets")
        self.delete_check = QCheckBox("Delete Entities")
        self.vehicle_check = QCheckBox("Configure Vehicle Master")
        auth_layout.addWidget(self.duplicate_check)
        auth_layout.addWidget(self.delete_check)
        auth_layout.addWidget(self.vehicle_check)
        auth_layout.addStretch(1)
        auth_group.setLayout(auth_layout)
        main_layout.addWidget(auth_group)

        # --- Bottom buttons ---
        btn_layout = QHBoxLayout()
        btn_layout.addStretch(1)
        self.new_btn = QPushButton("New")
        self.save_btn = QPushButton("Save")
        self.delete_btn = QPushButton("Delete")
        self.exit_btn = QPushButton("Exit")
        
        for btn in [self.new_btn, self.save_btn, self.delete_btn, self.exit_btn]:
            btn.setMinimumWidth(90)
            btn_layout.addWidget(btn)
        main_layout.addLayout(btn_layout)

        # --- Connections ---
        self.user_list.itemClicked.connect(self.display_user_details)
        self.new_btn.clicked.connect(self.clear_fields_for_new)
        self.save_btn.clicked.connect(self.save_user)
        self.delete_btn.clicked.connect(self.delete_user)
        self.exit_btn.clicked.connect(self.close)

        self.load_users()

    def load_users(self):
        """Loads usernames from the database into the list widget."""
        self.user_list.clear()
        users = fetch_all("SELECT username FROM usermanagement ORDER BY username")
        if users:
            for user in users:
                self.user_list.addItem(user['username'])

    def display_user_details(self, item):
        """Fills the form with data of the selected user."""
        username = item.text()
        user_data = fetch_one("SELECT * FROM usermanagement WHERE username = %s", (username,))
        if not user_data:
            QMessageBox.warning(self, "Error", "User not found.")
            return
            
        self.name_edit.setText(user_data['username'])
        self.pwd_edit.clear()
        self.conf_edit.clear()
        
        self.admin_check.setChecked(user_data.get('adminuser', False))
        self.duplicate_check.setChecked(user_data.get('duplicateticket', False))
        self.delete_check.setChecked(user_data.get('deleterecords', False))
        self.vehicle_check.setChecked(user_data.get('vehiclemaster', False))

    def clear_fields_for_new(self):
        """Clears all fields to prepare for new user entry."""
        self.user_list.clearSelection()
        self.name_edit.clear()
        self.pwd_edit.clear()
        self.conf_edit.clear()
        self.admin_check.setChecked(False)
        self.duplicate_check.setChecked(False)
        self.delete_check.setChecked(False)
        self.vehicle_check.setChecked(False)
        self.name_edit.setFocus()

    def save_user(self):
        """Saves a new or existing user to the database."""
        username = self.name_edit.text().strip()
        password = self.pwd_edit.text()
        confirm_pwd = self.conf_edit.text()

        if not username:
            QMessageBox.warning(self, "Input Error", "Username cannot be empty.")
            return

        selected_item = self.user_list.currentItem()
        is_new_user = not selected_item or selected_item.text().lower() != username.lower()

        if is_new_user:
            # Logic for creating a new user
            if not password:
                QMessageBox.warning(self, "Input Error", "Password cannot be empty for a new user.")
                return
            if password != confirm_pwd:
                QMessageBox.warning(self, "Input Error", "Passwords do not match.")
                return
            
            exists = fetch_one("SELECT 1 FROM usermanagement WHERE username = %s", (username,))
            if exists:
                QMessageBox.warning(self, "Error", "A user with this name already exists.")
                return
            
            query = """
                INSERT INTO usermanagement (username, password, adminuser, duplicateticket, deleterecords, vehiclemaster, offlinetickets, primaryuser)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            params = (username, password, self.admin_check.isChecked(), self.duplicate_check.isChecked(),
                      self.delete_check.isChecked(), self.vehicle_check.isChecked(), False, False)
            execute_query(query, params)
            QMessageBox.information(self, "Success", f"User '{username}' created successfully.")

        else:
            # Logic for updating an existing user
            query_parts = ["adminuser=%s", "duplicateticket=%s", "deleterecords=%s", "vehiclemaster=%s"]
            params = [self.admin_check.isChecked(), self.duplicate_check.isChecked(), 
                      self.delete_check.isChecked(), self.vehicle_check.isChecked()]
            
            if password:
                if password != confirm_pwd:
                    QMessageBox.warning(self, "Input Error", "Passwords do not match.")
                    return
                query_parts.append("password=%s")
                params.append(password)
            
            params.append(username)
            query = f"UPDATE usermanagement SET {', '.join(query_parts)} WHERE username = %s"
            execute_query(query, tuple(params))
            QMessageBox.information(self, "Success", f"User '{username}' updated successfully.")

        self.load_users()
        self.clear_fields_for_new()

    def delete_user(self):
        """Deletes the selected user from the database."""
        selected_item = self.user_list.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "Selection Error", "Please select a user to delete.")
            return
        
        username = selected_item.text()
        user_data = fetch_one("SELECT primaryuser FROM usermanagement WHERE username = %s", (username,))

        if user_data and user_data.get('primaryuser'):
            QMessageBox.critical(self, "Error", "Cannot delete the primary admin user.")
            return

        reply = QMessageBox.question(self, "Confirm Deletion", f"Are you sure you want to delete user '{username}'?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            execute_query("DELETE FROM usermanagement WHERE username = %s", (username,))
            QMessageBox.information(self, "Success", f"User '{username}' has been deleted.")
            self.load_users()
            self.clear_fields_for_new()

    def closeEvent(self, event):
        """Ensure parent is shown when this window is closed."""
        parent = self.parent()
        if parent:
            parent.show()
        super().closeEvent(event)
