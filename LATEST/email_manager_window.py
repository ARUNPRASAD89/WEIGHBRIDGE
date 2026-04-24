"""
Email Manager UI Window - PyQt5 Interface
COMPLETE VERSION with Test Mail button
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox, QPushButton, QLineEdit,
    QComboBox, QCheckBox, QLabel, QSpinBox, QTimeEdit, QMessageBox, QListWidget, 
    QListWidgetItem, QAbstractItemView, QSplitter, QWidget, QFileDialog, QTabWidget,
    QTableWidget, QTableWidgetItem, QTextEdit
)
from PyQt5.QtCore import Qt, QTime, QEvent
from PyQt5.QtGui import QFont

from db_utils import fetch_all, fetch_one, execute_query
import json
import logging

logger = logging.getLogger(__name__)


class EmailManagerWindow(QDialog):
    """Enhanced Email Manager Configuration Window"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Email Manager - Sales Report Configuration")
        self.setMinimumSize(1200, 800)
        self.setGeometry(100, 100, 1200, 800)
        
        # LAZY IMPORT
        from email_manager_core import EmailManager
        self.email_manager = EmailManager()
        self.current_config_id = None
        
        self._setup_ui()
        self.load_configurations()
    
    def _setup_ui(self):
        """Setup UI layout"""
        main_layout = QHBoxLayout(self)
        
        # --- LEFT: Configuration List ---
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("Configurations"))
        
        self.config_list = QListWidget()
        self.config_list.itemSelectionChanged.connect(self.on_config_selected)
        left_layout.addWidget(self.config_list)
        
        btn_layout = QHBoxLayout()
        self.new_btn = QPushButton("New")
        self.new_btn.clicked.connect(self.create_new_config)
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self.delete_config)
        btn_layout.addWidget(self.new_btn)
        btn_layout.addWidget(self.delete_btn)
        left_layout.addLayout(btn_layout)
        
        left_widget = QWidget()
        left_widget.setLayout(left_layout)
        left_widget.setMaximumWidth(250)
        
        # --- RIGHT: Configuration Details with Tabs ---
        self.tabs = QTabWidget()
        
        # TAB 1: Basic Settings
        self._create_basic_settings_tab()
        
        # TAB 2: Field Selection
        self._create_field_selection_tab()
        
        # TAB 3: Aggregation
        self._create_aggregation_tab()
        
        # TAB 4: Export Settings
        self._create_export_settings_tab()
        
        # Bottom buttons
        bottom_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save Configuration")
        self.save_btn.clicked.connect(self.save_configuration)
        
        #  NEW: Test Mail Button
        self.test_mail_btn = QPushButton("Test Mail Connection")
        self.test_mail_btn.clicked.connect(self.test_mail_connection)
        self.test_mail_btn.setStyleSheet("""
            QPushButton {
                background-color: #f39c12;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 5px 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e67e22;
            }
        """)
        
        self.test_btn = QPushButton("Send Test Report")
        self.test_btn.clicked.connect(self.send_test_report)
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.on_close_clicked)
        
        bottom_layout.addWidget(self.save_btn)
        bottom_layout.addWidget(self.test_mail_btn)  #  ADD TEST MAIL BUTTON
        bottom_layout.addWidget(self.test_btn)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.close_btn)
        
        tabs_layout = QVBoxLayout()
        tabs_layout.addWidget(self.tabs)
        tabs_layout.addLayout(bottom_layout)
        
        tabs_widget = QWidget()
        tabs_widget.setLayout(tabs_layout)
        
        # Splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(tabs_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        
        main_layout.addWidget(splitter)
        
        # Enable window resizing and maximize
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint)
    
    def keyPressEvent(self, event):
        """Handle ESC key to close window"""
        if event.key() == Qt.Key_Escape:
            self.on_close_clicked()
        else:
            super().keyPressEvent(event)
    
    def _create_basic_settings_tab(self):
        """Create Basic Settings Tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Configuration name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Config Name:"))
        self.name_input = QLineEdit()
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)
        
        # SMTP Settings Group
        smtp_group = QGroupBox("SMTP Settings")
        smtp_layout = QGridLayout(smtp_group)
        
        smtp_layout.addWidget(QLabel("SMTP Server:"), 0, 0)
        self.smtp_server = QLineEdit()
        self.smtp_server.setPlaceholderText("e.g., smtp.gmail.com")
        smtp_layout.addWidget(self.smtp_server, 0, 1)
        
        smtp_layout.addWidget(QLabel("Port:"), 0, 2)
        self.smtp_port = QSpinBox()
        self.smtp_port.setValue(587)
        self.smtp_port.setMaximum(65535)
        smtp_layout.addWidget(self.smtp_port, 0, 3)
        
        smtp_layout.addWidget(QLabel("From Email:"), 1, 0)
        self.sender_email = QLineEdit()
        self.sender_email.setPlaceholderText("sender@example.com")
        smtp_layout.addWidget(self.sender_email, 1, 1, 1, 3)
        
        smtp_layout.addWidget(QLabel("Password:"), 2, 0)
        self.sender_password = QLineEdit()
        self.sender_password.setEchoMode(QLineEdit.Password)
        self.sender_password.setPlaceholderText("App password or email password")
        smtp_layout.addWidget(self.sender_password, 2, 1, 1, 3)
        
        self.use_tls = QCheckBox("Use TLS (Port 587)")
        self.use_tls.setChecked(True)
        smtp_layout.addWidget(self.use_tls, 3, 0)
        
        self.use_ssl = QCheckBox("Use SSL (Port 465)")
        smtp_layout.addWidget(self.use_ssl, 3, 1)
        
        layout.addWidget(smtp_group)
        
        # Recipients Group
        recipients_group = QGroupBox("Recipients (Configure Email IDs)")
        recipients_layout = QGridLayout(recipients_group)
        
        recipients_layout.addWidget(QLabel("To (comma-separated):"), 0, 0)
        self.to_emails = QLineEdit()
        self.to_emails.setPlaceholderText("user1@example.com, user2@example.com")
        recipients_layout.addWidget(self.to_emails, 0, 1)
        
        recipients_layout.addWidget(QLabel("CC (comma-separated):"), 1, 0)
        self.cc_emails = QLineEdit()
        self.cc_emails.setPlaceholderText("cc1@example.com, cc2@example.com")
        recipients_layout.addWidget(self.cc_emails, 1, 1)
        
        recipients_layout.addWidget(QLabel("BCC (comma-separated):"), 2, 0)
        self.bcc_emails = QLineEdit()
        self.bcc_emails.setPlaceholderText("bcc1@example.com")
        recipients_layout.addWidget(self.bcc_emails, 2, 1)
        
        # Email configuration help
        help_text = QLabel(
            "💡 Email Configuration:\n"
            "• Gmail: Use SMTP server 'smtp.gmail.com', port 587 (TLS)\n"
            "• Use App Passwords for Gmail (not your main password)\n"
            "• Separate multiple emails with commas\n"
            "• Spaces around commas are automatically cleaned"
        )
        help_text.setStyleSheet("color: #7f8c8d; font-size: 9pt; font-style: italic;")
        recipients_layout.addWidget(help_text, 3, 0, 1, 2)
        
        layout.addWidget(recipients_group)
        
        # Report Configuration Group
        report_group = QGroupBox("Report Scheduling")
        report_layout = QGridLayout(report_group)
        
        report_layout.addWidget(QLabel("Report Type:"), 0, 0)
        self.report_type = QComboBox()
        self.report_type.addItems(["DAILY", "WEEKLY", "MONTHLY"])
        report_layout.addWidget(self.report_type, 0, 1)
        
        report_layout.addWidget(QLabel("Schedule Time:"), 0, 2)
        self.schedule_time = QTimeEdit()
        self.schedule_time.setTime(QTime(8, 0))
        report_layout.addWidget(self.schedule_time, 0, 3)
        
        layout.addWidget(report_group)
        
        # Email Subject
        layout.addWidget(QLabel("Email Subject:"))
        self.subject_template = QLineEdit()
        self.subject_template.setText("WEIGHBRIDGE {report_type} Report - {date}")
        self.subject_template.setPlaceholderText("Use {report_type} and {date} as placeholders")
        layout.addWidget(self.subject_template)
        
        # Active and AutoSend checkboxes
        checkbox_layout = QHBoxLayout()
        
        self.is_active = QCheckBox("Active")
        
        self.is_active.setChecked(True)
        checkbox_layout.addWidget(self.is_active)
        
        # ✅ NEW: AutoSend Checkbox
        self.autosend = QCheckBox("AutoSend")
        self.autosend.setChecked(False)
        self.autosend.setStyleSheet("""
            QCheckBox {
                color: #27ae60;
                font-weight: bold;
            }
            QCheckBox::indicator:checked {
                background-color: #27ae60;
            }
        """)
        checkbox_layout.addWidget(self.autosend)
        
        checkbox_layout.addStretch()
        layout.addLayout(checkbox_layout)
        
        layout.addStretch()
        self.tabs.addTab(widget, "Basic Settings")
    
    def _create_field_selection_tab(self):
        """Create Field Selection Tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Title
        title_layout = QHBoxLayout()
        title_layout.addWidget(QLabel("📋 Select Fields to Include in Report (Multi-select)"))
        title_layout.addStretch()
        layout.addLayout(title_layout)
        
        # Available Fields (Left) and Selected Fields (Right)
        fields_container = QHBoxLayout()
        
        # LEFT SIDE
        left_side = QVBoxLayout()
        left_side.addWidget(QLabel("Available Fields"))
        
        self.available_fields_list = QListWidget()
        self.available_fields_list.setSelectionMode(QAbstractItemView.MultiSelection)
        self._populate_available_fields()
        left_side.addWidget(self.available_fields_list)
        
        add_field_btn = QPushButton("➕ Add Field >>")
        add_field_btn.setMinimumHeight(40)
        add_field_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        add_field_btn.clicked.connect(self.add_fields_to_report)
        left_side.addWidget(add_field_btn)
        
        # RIGHT SIDE
        right_side = QVBoxLayout()
        right_side.addWidget(QLabel("Selected Report Fields"))
        
        self.selected_fields_list = QListWidget()
        self.selected_fields_list.setSelectionMode(QAbstractItemView.MultiSelection)
        right_side.addWidget(self.selected_fields_list)
        
        remove_field_btn = QPushButton("❌ Remove Field")
        remove_field_btn.setMinimumHeight(40)
        remove_field_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        remove_field_btn.clicked.connect(self.remove_fields_from_report)
        right_side.addWidget(remove_field_btn)
        
        fields_container.addLayout(left_side, 1)
        fields_container.addLayout(right_side, 1)
        
        layout.addLayout(fields_container)
        
        info_label = QLabel(
            "💡 How to use:\n"
            "1. Select fields in 'Available Fields' (left)\n"
            "2. Click 'Add Field >>' to move to report\n"
            "3. Select fields in 'Selected Report Fields' (right)\n"
            "4. Click 'Remove Field' to remove from report"
        )
        info_label.setStyleSheet("color: #3498db; font-size: 9pt; background-color: #ecf0f1; padding: 10px; border-radius: 5px;")
        layout.addWidget(info_label)
        
        self.tabs.addTab(widget, "Field Selection")
    
    def add_fields_to_report(self):
        """Add selected fields from available to selected list"""
        selected_items = self.available_fields_list.selectedItems()
        
        if not selected_items:
            QMessageBox.warning(self, "Error", "Select at least one field to add")
            return
        
        for item in selected_items:
            field_name = item.text()
            col_name = item.data(Qt.UserRole)
            
            # Check if already in selected list
            for row in range(self.selected_fields_list.count()):
                if self.selected_fields_list.item(row).data(Qt.UserRole) == col_name:
                    QMessageBox.warning(self, "Error", f"'{field_name}' already in selected fields")
                    return
            
            # Add to selected list
            new_item = QListWidgetItem(field_name)
            new_item.setData(Qt.UserRole, col_name)
            self.selected_fields_list.addItem(new_item)
        
        # Remove from available
        for item in selected_items:
            self.available_fields_list.takeItem(self.available_fields_list.row(item))
    
    def remove_fields_from_report(self):
        """Remove selected fields from selected list back to available"""
        selected_items = self.selected_fields_list.selectedItems()
        
        if not selected_items:
            QMessageBox.warning(self, "Error", "Select at least one field to remove")
            return
        
        for item in selected_items:
            field_name = item.text()
            col_name = item.data(Qt.UserRole)
            
            # Remove from selected
            self.selected_fields_list.takeItem(self.selected_fields_list.row(item))
            
            # Add back to available
            new_item = QListWidgetItem(field_name)
            new_item.setData(Qt.UserRole, col_name)
            self.available_fields_list.addItem(new_item)
        
        # Sort available list
        self.available_fields_list.sortItems()
    
    def _create_aggregation_tab(self):
        """Create Aggregation Tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        layout.addWidget(QLabel("Configure Aggregations (Optional)"))
        layout.addWidget(QLabel("Select ANY field from tickets table to COUNT, SUM, AVG, etc:"))
        
        self.aggregation_table = QTableWidget()
        self.aggregation_table.setColumnCount(3)
        self.aggregation_table.setHorizontalHeaderLabels(["Field Name", "Aggregation Type", "Remove"])
        layout.addWidget(self.aggregation_table)
        
        add_agg_layout = QHBoxLayout()
        add_agg_layout.addWidget(QLabel("Select Field:"))
        self.agg_field_combo = QComboBox()
        self._populate_agg_field_combo()
        add_agg_layout.addWidget(self.agg_field_combo)
        
        add_agg_layout.addWidget(QLabel("Select Type:"))
        self.agg_type_combo = QComboBox()
        from email_manager_core import DynamicAggregator
        self.agg_type_combo.addItems(DynamicAggregator.get_aggregation_types())
        add_agg_layout.addWidget(self.agg_type_combo)
        
        add_agg_btn = QPushButton("Add Aggregation")
        add_agg_btn.clicked.connect(self.add_aggregation)
        add_agg_layout.addWidget(add_agg_btn)
        add_agg_layout.addStretch()
        
        layout.addLayout(add_agg_layout)
        self.tabs.addTab(widget, "Aggregation")
    
    def _create_export_settings_tab(self):
        """Create Export Settings Tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        export_group = QGroupBox("Save Reports to Folder")
        export_layout = QGridLayout(export_group)
        
        self.save_reports_check = QCheckBox("Save Reports")
        self.save_reports_check.setChecked(False)
        self.save_reports_check.stateChanged.connect(self.on_save_reports_toggled)
        export_layout.addWidget(self.save_reports_check, 0, 0, 1, 3)
        
        export_layout.addWidget(QLabel("Export Format:"), 1, 0)
        self.export_format_combo = QComboBox()
        self.export_format_combo.addItems(["xlsx", "csv", "html"])
        self.export_format_combo.setEnabled(False)
        export_layout.addWidget(self.export_format_combo, 1, 1)
        
        export_layout.addWidget(QLabel("Save Folder:"), 2, 0)
        self.export_folder_input = QLineEdit()
        self.export_folder_input.setReadOnly(True)
        self.export_folder_input.setEnabled(False)
        export_layout.addWidget(self.export_folder_input, 2, 1)
        
        browse_folder_btn = QPushButton("Browse...")
        browse_folder_btn.clicked.connect(self.browse_export_folder)
        browse_folder_btn.setEnabled(False)
        self.browse_folder_btn = browse_folder_btn
        export_layout.addWidget(browse_folder_btn, 2, 2)
        
        layout.addWidget(export_group)
        layout.addStretch()
        
        self.tabs.addTab(widget, "Export Settings")
    
    def on_save_reports_toggled(self, state):
        """Toggle export controls"""
        enabled = self.save_reports_check.isChecked()
        self.export_format_combo.setEnabled(enabled)
        self.export_folder_input.setEnabled(enabled)
        self.browse_folder_btn.setEnabled(enabled)
    
    def browse_export_folder(self):
        """Browse and select export folder"""
        folder = QFileDialog.getExistingDirectory(self, "Select Export Folder")
        if folder:
            self.export_folder_input.setText(folder)
    
    def _populate_available_fields(self):
        """Populate list of available ticket fields"""
        self.available_fields_list.clear()
        
        from email_manager_core import TicketFieldLoader
        fields = TicketFieldLoader.get_available_fields()
        display_names = TicketFieldLoader.get_field_display_names()
        
        for field in fields:
            col_name = field['column_name']
            display_name = display_names.get(col_name, col_name)
            
            item = QListWidgetItem(display_name)
            item.setData(Qt.UserRole, col_name)
            self.available_fields_list.addItem(item)
    
    def _populate_agg_field_combo(self):
        """Populate aggregation field combo"""
        self.agg_field_combo.clear()
        
        from email_manager_core import TicketFieldLoader
        fields = TicketFieldLoader.get_available_fields()
        display_names = TicketFieldLoader.get_field_display_names()
        
        for field in fields:
            col_name = field['column_name']
            display_name = display_names.get(col_name, col_name)
            data_type = field.get('data_type', 'unknown')
            
            display_with_type = f"{display_name} ({data_type})"
            self.agg_field_combo.addItem(display_with_type, col_name)
    
    def add_aggregation(self):
        """Add aggregation to table"""
        field_name = self.agg_field_combo.currentData()
        agg_type = self.agg_type_combo.currentText()
        display_name = self.agg_field_combo.currentText().split('(')[0].strip()
        
        if not field_name:
            QMessageBox.warning(self, "Error", "Select a field")
            return
        
        # Check if already exists
        for row in range(self.aggregation_table.rowCount()):
            if self.aggregation_table.item(row, 0).text() == display_name:
                QMessageBox.warning(self, "Error", f"Field '{display_name}' already added")
                return
        
        row = self.aggregation_table.rowCount()
        self.aggregation_table.insertRow(row)
        
        self.aggregation_table.setItem(row, 0, QTableWidgetItem(display_name))
        self.aggregation_table.setItem(row, 1, QTableWidgetItem(agg_type))
        
        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(lambda: self.aggregation_table.removeRow(row))
        self.aggregation_table.setCellWidget(row, 2, remove_btn)
    
    def load_configurations(self):
        """Load existing configurations"""
        self.config_list.clear()
        
        configs = self.email_manager.list_active_configs()
        for config in configs:
            item = QListWidgetItem(config['email_name'])
            item.setData(Qt.UserRole, config['id'])
            self.config_list.addItem(item)
    
    def on_config_selected(self):
        """Load selected configuration"""
        item = self.config_list.currentItem()
        if not item:
            return
        
        config_id = item.data(Qt.UserRole)
        config = self.email_manager.get_email_config(config_id)
        
        if config:
            self.current_config_id = config_id
            
            # Basic settings
            self.name_input.setText(config.get('email_name', ''))
            self.smtp_server.setText(config.get('smtp_server', ''))
            self.smtp_port.setValue(config.get('smtp_port', 587))
            self.sender_email.setText(config.get('sender_email', ''))
            self.sender_password.setText(config.get('sender_password', ''))
            self.use_tls.setChecked(config.get('use_tls', True))
            self.use_ssl.setChecked(config.get('use_ssl', False))
            
            self.to_emails.setText(config.get('recipient_emails', ''))
            self.cc_emails.setText(config.get('cc_emails', ''))
            self.bcc_emails.setText(config.get('bcc_emails', ''))
            
            self.report_type.setCurrentText(config.get('report_type', 'DAILY'))
            self.subject_template.setText(config.get('subject_template', ''))
            self.is_active.setChecked(config.get('is_active', True))
            self.autosend.setChecked(config.get('autosend', False))
            
            # Field selection
            self._populate_available_fields()
            self.selected_fields_list.clear()
            
            try:
                selected_fields = json.loads(config.get('selected_fields', '[]'))
                from email_manager_core import TicketFieldLoader
                display_names = TicketFieldLoader.get_field_display_names()
                
                fields_to_remove = []
                for i in range(self.available_fields_list.count()):
                    item = self.available_fields_list.item(i)
                    col_name = item.data(Qt.UserRole)
                    
                    if col_name in selected_fields:
                        new_item = QListWidgetItem(item.text())
                        new_item.setData(Qt.UserRole, col_name)
                        self.selected_fields_list.addItem(new_item)
                        fields_to_remove.append(i)
                
                for i in reversed(fields_to_remove):
                    self.available_fields_list.takeItem(i)
            except Exception as e:
                logger.error(f"Error loading selected fields: {e}")
            
            # Aggregations
            self.aggregation_table.setRowCount(0)
            try:
                aggregation_config = json.loads(config.get('aggregation_fields', '{}'))
                for field_name, agg_type in aggregation_config.items():
                    row = self.aggregation_table.rowCount()
                    self.aggregation_table.insertRow(row)
                    self.aggregation_table.setItem(row, 0, QTableWidgetItem(field_name))
                    self.aggregation_table.setItem(row, 1, QTableWidgetItem(agg_type))
                    remove_btn = QPushButton("Remove")
                    remove_btn.clicked.connect(lambda r=row: self.aggregation_table.removeRow(r))
                    self.aggregation_table.setCellWidget(row, 2, remove_btn)
            except Exception as e:
                logger.error(f"Error loading aggregations: {e}")
            
            # Export settings
            self.save_reports_check.setChecked(config.get('save_reports', False))
            self.export_format_combo.setCurrentText(config.get('export_format', 'xlsx'))
            self.export_folder_input.setText(config.get('export_folder', ''))
    
    def create_new_config(self):
        """Create new configuration"""
        self.current_config_id = None
        self.name_input.clear()
        self.smtp_server.clear()
        self.smtp_port.setValue(587)
        self.sender_email.clear()
        self.sender_password.clear()
        self.to_emails.clear()
        self.cc_emails.clear()
        self.bcc_emails.clear()
        self.report_type.setCurrentText("DAILY")
        self.subject_template.setText("WEIGHBRIDGE {report_type} Report - {date}")
        self.is_active.setChecked(True)
        self.export_format_combo.setCurrentText("xlsx")
        self.export_folder_input.clear()
        self.save_reports_check.setChecked(False)
        self.aggregation_table.setRowCount(0)
        
        self.selected_fields_list.clear()
        self._populate_available_fields()
        self.config_list.setCurrentItem(None)
        
        logger.info("New configuration created - ready for input")
    
    def _parse_email_list(self, email_string: str) -> str:
        """Parse and clean email list - FIXED"""
        if not email_string.strip():
            return '[]'
        
        # Split by comma and clean
        emails = [e.strip() for e in email_string.split(',') if e.strip()]
        
        # Validate basic email format
        valid_emails = []
        for email in emails:
            # Remove any quotes or brackets that might have been added
            email_clean = email.replace('"', '').replace('[', '').replace(']', '').replace('\\', '').strip()
            if '@' in email_clean and '.' in email_clean:
                valid_emails.append(email_clean)
        
        logger.info(f"Parsed emails: {valid_emails}")  #  DEBUG LOG
        return json.dumps(valid_emails)
    
    def test_mail_connection(self):
        """✅ NEW: Test SMTP connection - FIXED"""
        # Validate SMTP settings first
        if not self.smtp_server.text().strip():
            QMessageBox.warning(self, "Error", "SMTP Server is required")
            return
        
        if not self.sender_email.text().strip():
            QMessageBox.warning(self, "Error", "Sender Email is required")
            return
        
        if not self.sender_password.text().strip():
            QMessageBox.warning(self, "Error", "Password is required")
            return
        
        try:
            # Prepare SMTP config
            smtp_config = {
                "smtp_server": self.smtp_server.text().strip(),
                "smtp_port": self.smtp_port.value(),
                "sender_email": self.sender_email.text().strip(),
                "sender_password": self.sender_password.text().strip(),
                "use_tls": self.use_tls.isChecked(),
                "use_ssl": self.use_ssl.isChecked()
            }
            
            # Test connection DIRECTLY (no dialog)
            logger.info("Testing SMTP connection...")
            from email_manager_core import EmailSender
            success, message = EmailSender.test_smtp_connection(smtp_config)
            
            if success:
                QMessageBox.information(
                    self,
                    "Success!",
                    "SMTP connection successful!\n\n"
                    "Your email configuration is correct.\n"
                    "You can now send test reports."
                )
                logger.info("[SUCCESS] SMTP connection test passed")
            else:
                QMessageBox.warning(
                    self,
                    "Failed",
                    f"SMTP connection failed:\n\n{message}"
                )
                logger.error(f"[FAILED] SMTP connection test: {message}")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error testing connection:\n\n{str(e)}")
            logger.error(f"Test connection error: {e}", exc_info=True)
    
    def save_configuration(self):
        """Save configuration to database"""
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "Configuration name required")
            return
        
        if not self.smtp_server.text().strip():
            QMessageBox.warning(self, "Error", "SMTP Server is required")
            return
        
        if not self.sender_email.text().strip():
            QMessageBox.warning(self, "Error", "Sender Email is required")
            return
        
        if not self.sender_password.text().strip():
            QMessageBox.warning(self, "Error", "Password is required")
            return
        
        to_emails_str = self._parse_email_list(self.to_emails.text())
        to_emails_list = json.loads(to_emails_str)
        
        if not to_emails_list:
            QMessageBox.warning(self, "Error", "At least one 'To' email is required")
            return
        
        cc_emails_str = self._parse_email_list(self.cc_emails.text())
        bcc_emails_str = self._parse_email_list(self.bcc_emails.text())
        
        selected_fields = []
        for i in range(self.selected_fields_list.count()):
            item = self.selected_fields_list.item(i)
            col_name = item.data(Qt.UserRole)
            if col_name:
                selected_fields.append(col_name)
        
        if not selected_fields:
            QMessageBox.warning(self, "Error", "Select at least one field in Field Selection tab")
            return
        
        logger.info(f"Selected fields (column names): {selected_fields}")
        
        aggregation_config = {}
        for row in range(self.aggregation_table.rowCount()):
            field_item = self.aggregation_table.item(row, 0)
            type_item = self.aggregation_table.item(row, 1)
            if field_item and type_item:
                field_name = field_item.text()
                agg_type = type_item.text()
                aggregation_config[field_name] = agg_type
        
        logger.info(f"Aggregation config: {aggregation_config}")
        
        if self.save_reports_check.isChecked():
            if not self.export_folder_input.text().strip():
                QMessageBox.warning(self, "Error", "Select export folder")
                return
        
        try:
            if self.current_config_id:
                logger.info(f"Updating configuration {self.current_config_id}: {name}")
                execute_query("""
                    UPDATE emailmanager SET
                        email_name = %s,
                        smtp_server = %s,
                        smtp_port = %s,
                        sender_email = %s,
                        sender_password = %s,
                        use_tls = %s,
                        use_ssl = %s,
                        recipient_emails = %s,
                        cc_emails = %s,
                        bcc_emails = %s,
                        report_type = %s,
                        schedule_time = %s,
                        selected_fields = %s,
                        aggregation_fields = %s,
                        subject_template = %s,
                        save_reports = %s,
                        export_format = %s,
                        export_folder = %s,
                        is_active = %s,
                        autosend = %s,
                        updated_at = NOW()
                    WHERE id = %s
                """, (
                    name,
                    self.smtp_server.text().strip(),
                    self.smtp_port.value(),
                    self.sender_email.text().strip(),
                    self.sender_password.text().strip(),
                    self.use_tls.isChecked(),
                    self.use_ssl.isChecked(),
                    to_emails_str,
                    cc_emails_str,
                    bcc_emails_str,
                    self.report_type.currentText(),
                    self.schedule_time.time().toString("HH:mm:ss"),
                    json.dumps(selected_fields),
                    json.dumps(aggregation_config),
                    self.subject_template.text().strip(),
                    self.save_reports_check.isChecked(),
                    self.export_format_combo.currentText(),
                    self.export_folder_input.text().strip(),
                    self.is_active.isChecked(),
                    self.autosend.isChecked(),  # ✅ PARAMETER 20
                    self.current_config_id  # ✅ WHERE clause parameter
                ))
    
            
            QMessageBox.information(
                self,
                "Success! ",
                "Configuration saved successfully!\n\n"
                "You can now send test reports."
            )
            self.load_configurations()
            
            configs = self.email_manager.list_active_configs()
            if configs:
                latest = configs[-1]
                self.current_config_id = latest['id']
                logger.info(f"Current config ID set to: {self.current_config_id}")
                
                for i in range(self.config_list.count()):
                    if self.config_list.item(i).data(Qt.UserRole) == self.current_config_id:
                        self.config_list.setCurrentRow(i)
                        break
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save:\n\n{str(e)}")
            logger.error(f"Save error: {e}", exc_info=True)
    
    def delete_config(self):
        """Delete selected configuration"""
        item = self.config_list.currentItem()
        if not item:
            QMessageBox.warning(self, "Error", "Select a configuration")
            return
        
        if not QMessageBox.question(self, "Confirm", "Delete this configuration?"):
            return
        
        config_id = item.data(Qt.UserRole)
        try:
            execute_query("DELETE FROM emailmanager WHERE id = %s", (config_id,))
            QMessageBox.information(self, "Success", "Configuration deleted!")
            self.load_configurations()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to delete: {e}")
    
    def send_test_report(self):
        """Send test report immediately - FIXED"""
        if not self.current_config_id:
            QMessageBox.warning(self, "Error", "Save configuration first")
            return
        
        config = self.email_manager.get_email_config(self.current_config_id)
        if not config:
            QMessageBox.warning(self, "Error", "Configuration not found")
            return
        
        try:
            logger.info(f"[SENDING] Test report for config: {config['email_name']}")
            logger.info(f"[DEBUG] Recipients: {config.get('recipient_emails')}")
            logger.info(f"[DEBUG] Selected Fields: {config.get('selected_fields')}")
            
            # Send report
            success = self.email_manager.send_scheduled_report(config)
            
            if success:
                QMessageBox.information(
                    self,
                    "Success!",
                    "Test report sent successfully!\n\n"
                    "Check your email inbox.\n\n"
                    "If no records were found,\n"
                    "you'll receive a notification\n"
                    "saying 'NO RECORDS'."
                )
                logger.info("[SUCCESS] Test report sent")
            else:
                QMessageBox.warning(
                    self,
                    "Failed",
                    "Failed to send test report.\n\n"
                    "Check: Logs show details"
                )
                logger.warning("[FAILED] Test report not sent")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error: {str(e)}")
            logger.error(f"Test report error: {e}", exc_info=True)
    
    def on_close_clicked(self):
        """Close window and return to Administration window"""
        parent = self.parent()
        if parent:
            parent.show()
        self.close()
