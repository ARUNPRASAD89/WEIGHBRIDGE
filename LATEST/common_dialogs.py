# (only the file-level header and imports are unchanged; full file provided with the updated _send_whatsapp_notification)
import os, traceback, random, io
from datetime import datetime
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QHBoxLayout, QGridLayout,
    QApplication, QSizePolicy, QMessageBox, QFrame
)
from PyQt5.QtCore import Qt, QDate, QTime, QTimer
from PyQt5.QtGui import QFont, QPixmap
import threading
import yaml

# Local imports from your project
from db_utils import fetch_one, unified_save_ticket, get_new_connection
from ticket_preview_window import TicketPreviewDialog
from print_ticket_with_template_win32 import print_ticket_with_template
from date_time_utils import to_db_date, to_db_time, to_display_date, to_display_time
import whatsapp_sender

try:
    from whatsapp_gui import WhatsAppWorker
    WHATSAPP_WORKER_AVAILABLE = True
except ImportError:
    WHATSAPP_WORKER_AVAILABLE = False

class CommonSummaryDialog(QDialog):
    def __init__(self, parent, ticket_data, is_first_load, transaction_window=None):
        super().__init__(parent)
        self.setWindowTitle("Summary & Finalize")
        self.setStyleSheet("background-color: white; color: black;")
        self.setWindowModality(Qt.ApplicationModal)
        self.resize(700, 550)

        self.ticket_data = ticket_data
        self.is_first_load = is_first_load
        self.transaction_window = transaction_window
        
        self._setup_ui()
        self._connect_signals()
        self._populate_data()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        title_font = QFont("Arial", 20, QFont.Bold)
        label_font = QFont("Arial", 16, QFont.Bold)
        amount_font = QFont("Arial", 16, QFont.Bold)
        button_font = QFont("Arial", 16, QFont.Bold)

        self.info_grid = QGridLayout()
        self.info_grid.setSpacing(10)
        main_layout.addLayout(self.info_grid)
        main_layout.addWidget(QFrame(self, frameShape=QFrame.HLine, frameShadow=QFrame.Sunken))

        amount_layout = QGridLayout()
        amount_layout.setSpacing(10)
        
        e_label = QLabel("E-Amount:", font=label_font)
        self.eamount_field = QLineEdit(); self.eamount_field.setFont(amount_font); self.eamount_field.setAlignment(Qt.AlignCenter); self.eamount_field.setMinimumWidth(120)
        self.e_minus_btn = QPushButton("[ - ]"); self.e_plus_btn = QPushButton("[ + ]")
        for btn in [self.e_minus_btn, self.e_plus_btn]: btn.setFont(button_font); btn.setMinimumSize(50, 50)
        amount_layout.addWidget(e_label, 0, 0); amount_layout.addWidget(self.e_minus_btn, 0, 1); amount_layout.addWidget(self.eamount_field, 0, 2); amount_layout.addWidget(self.e_plus_btn, 0, 3)

        l_label = QLabel("L-Amount:", font=label_font)
        self.lamount_field = QLineEdit(); self.lamount_field.setFont(amount_font); self.lamount_field.setAlignment(Qt.AlignCenter); self.lamount_field.setMinimumWidth(120)
        self.l_minus_btn = QPushButton("[ - ]"); self.l_plus_btn = QPushButton("[ + ]")
        for btn in [self.l_minus_btn, self.l_plus_btn]: btn.setFont(button_font); btn.setMinimumSize(50, 50)
        amount_layout.addWidget(l_label, 1, 0); amount_layout.addWidget(self.l_minus_btn, 1, 1); amount_layout.addWidget(self.lamount_field, 1, 2); amount_layout.addWidget(self.l_plus_btn, 1, 3)

        t_label = QLabel("T-Amount:", font=label_font)
        self.tamount_display = QLabel(); self.tamount_display.setFont(amount_font); self.tamount_display.setMinimumWidth(120); self.tamount_display.setAlignment(Qt.AlignCenter)
        amount_layout.addWidget(t_label, 2, 0); amount_layout.addWidget(self.tamount_display, 2, 2)
        
        main_layout.addLayout(amount_layout)
        main_layout.addStretch()

        btn_row = QHBoxLayout()
        self.wp_btn = QPushButton("Weigh & Print"); self.wp_btn.setFont(button_font); self.wp_btn.setMinimumHeight(60); self.wp_btn.setStyleSheet("background: #006400; color: white; border-radius: 8px;")
        btn_row.addWidget(self.wp_btn)
        
        self.cancel_btn = QPushButton("Cancel"); self.cancel_btn.setFont(button_font); self.cancel_btn.setMinimumHeight(60); self.cancel_btn.setStyleSheet("background: #8B0000; color: white; border-radius: 8px;")
        btn_row.addWidget(self.cancel_btn)
        main_layout.addLayout(btn_row)
        
        self.success_label = QLabel("", self); self.success_label.setAlignment(Qt.AlignCenter); self.success_label.setFont(title_font); self.success_label.setStyleSheet("color: #006400;")
        main_layout.addWidget(self.success_label)

    def _connect_signals(self):
        self.eamount_field.textChanged.connect(self._update_tamount)
        self.lamount_field.textChanged.connect(self._update_tamount)
        self.wp_btn.clicked.connect(self.on_weightprint)
        self.cancel_btn.clicked.connect(self.reject)
        self.e_minus_btn.clicked.connect(lambda: self._modify_amount(self.eamount_field, -5))
        self.e_plus_btn.clicked.connect(lambda: self._modify_amount(self.eamount_field, 5))
        self.l_minus_btn.clicked.connect(lambda: self._modify_amount(self.lamount_field, -5))
        self.l_plus_btn.clicked.connect(lambda: self._modify_amount(self.lamount_field, 5))

    def _populate_data(self):
        def add_info(row, col, label, value):
            lab = QLabel(label); lab.setFont(QFont("Arial", 16, QFont.Bold))
            val = QLabel(str(value)); val.setFont(QFont("Arial", 16, QFont.Bold)); val.setStyleSheet("color: black;")
            self.info_grid.addWidget(lab, row, col*2); self.info_grid.addWidget(val, row, col*2+1)

        row_idx = 0
        add_info(row_idx, 0, "Ticket No:", self.ticket_data.get("TicketNumber", "")); row_idx+=1
        date_val = self.ticket_data.get("Date"); time_val = self.ticket_data.get("Time")
        add_info(row_idx, 0, "Date:", to_display_date(date_val) if date_val else "");
        add_info(row_idx, 1, "Time:", to_display_time(time_val) if time_val else ""); row_idx+=1
        if "LAST DATE" in self.ticket_data:
            last_date_val = self.ticket_data.get("LAST DATE"); last_time_val = self.ticket_data.get("LAST TIME")
            add_info(row_idx, 0, "Last Date:", to_display_date(last_date_val) if last_date_val else "");
            add_info(row_idx, 1, "Last Time:", to_display_time(last_time_val) if last_time_val else ""); row_idx+=1
        add_info(row_idx, 0, "Vehicle:", self.ticket_data.get("VehicleNumber", ""));
        add_info(row_idx, 1, "Type:", self.ticket_data.get("VehicleType", "")); row_idx+=1
        add_info(row_idx, 0, "Empty Wt:", self.ticket_data.get("EmptyWeight", ""));
        add_info(row_idx, 1, "Load Wt:", self.ticket_data.get("LoadedWeight", "")); row_idx+=1
        add_info(row_idx, 0, "Net Wt:", self.ticket_data.get("NetWeight", ""));
        if self.ticket_data.get("ContainerNo"):
            add_info(row_idx, 1, "Container:", self.ticket_data.get("ContainerNo", "")); row_idx+=1
        
        if self.ticket_data.get("SupplierName"):
            add_info(row_idx, 0, "Supplier:", self.ticket_data.get("SupplierName", '')); row_idx+=1

        self.eamount_field.setText(str(self.ticket_data.get("EAMOUNT", "0")))
        self.lamount_field.setText(str(self.ticket_data.get("LAMOUNT", "0")))
        self._update_tamount()

    def _modify_amount(self, line_edit, delta):
        try: current_value = int(line_edit.text())
        except (ValueError, TypeError): current_value = 0
        new_value = max(0, current_value + delta)
        line_edit.setText(str(new_value))

    def _update_tamount(self):
        e_val = int(self.eamount_field.text()) if self.eamount_field.text().isdigit() else 0
        l_val = int(self.lamount_field.text()) if self.lamount_field.text().isdigit() else 0
        self.tamount_display.setText(str(e_val + l_val))

    def on_weightprint(self):
        try:
            snapshot_path = None
            if hasattr(self.parent(), 'camera_manager') and self.parent().camera_manager:
                snapshot_path = self.parent().camera_manager.save_snapshot()
            
            self.ticket_data["EAMOUNT"] = self.eamount_field.text()
            self.ticket_data["LAMOUNT"] = self.lamount_field.text()
            self.ticket_data["TAMOUNT"] = self.tamount_display.text()
            self.ticket_data["SnapshotPath"] = snapshot_path or self.ticket_data.get("SnapshotPath")
            
            if not self.is_first_load:
                self.ticket_data["Pending"] = False
                self.ticket_data["Closed"] = True

            unified_save_ticket(self.ticket_data)

            self.wp_btn.setVisible(False)
            self.cancel_btn.setVisible(False)
            self.success_label.setText("TICKET SAVED!")

            if WHATSAPP_WORKER_AVAILABLE:
                self._send_whatsapp_notification(self.ticket_data.get("TicketNumber"))

            self._preview_dialog = TicketPreviewDialog(self.ticket_data, parent=self)
            self._preview_dialog.show()
            QTimer.singleShot(3000, self._do_print_ticket)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save/print ticket:\n{traceback.format_exc()}")

    def _do_print_ticket(self):
        try:
            if hasattr(self, '_preview_dialog') and self._preview_dialog: self._preview_dialog.close()
            print_ticket_with_template(self.ticket_data, get_new_connection())
            self.success_label.setText("Printing Complete!")
            QTimer.singleShot(2000, self._finish_and_return_to_menu)
        except Exception as e:
            QMessageBox.critical(self, "Printing Error", f"Print job failed:\n{e}")
            self.accept()

    def _finish_and_return_to_menu(self):
        if self.transaction_window:
            parent_window = self.parent()
            if parent_window: parent_window.close()
            self.transaction_window.show()
        self.accept()

    def _send_whatsapp_notification(self, ticket_number):
        if not WHATSAPP_WORKER_AVAILABLE:
            return

        try:
            # Check the master enabler switch first
            enabler = fetch_one("SELECT enabled FROM whatsappenabler WHERE id = 1")
            if not enabler or not enabler.get('enabled'):
                print("WhatsApp notification skipped: Master switch is disabled.")
                return
        except Exception as e:
            print(f"Could not check whatsappenabler status, skipping notification. Error: {e}")
            return

        def _execute_send():
            try:
                # Prefer database (weighbridge_config) values — read the row and pass both config and provider_config
                db_row = None
                try:
                    db_row = fetch_one("SELECT * FROM weighbridge_config WHERE config_name = %s", ('default',))
                except Exception:
                    db_row = None

                # Build provider_conf from DB (if present)
                provider_conf = None
                if db_row:
                    provider_conf = {
                        'provider': db_row.get('whatsapp_provider') or 'mock',
                        'account_sid': db_row.get('whatsapp_account_sid'),
                        'auth_token': db_row.get('whatsapp_auth_token'),
                        'from_whatsapp': db_row.get('whatsapp_from_whatsapp'),
                    }

                # Build config dict including ownerno (recipient) so worker.ownerno is set
                config_for_worker = {}
                if db_row:
                    config_for_worker = {
                        'ownerno': db_row.get('ownerno'),
                        'poll_interval_seconds': db_row.get('poll_interval_seconds') or 10
                    }
                else:
                    # fallback: try to read config.yaml if DB row not present (best-effort)
                    if os.path.exists("config.yaml"):
                        try:
                            with open("config.yaml", 'r') as f:
                                cfg = yaml.safe_load(f) or {}
                                config_for_worker['ownerno'] = cfg.get('ownerno')
                                config_for_worker['poll_interval_seconds'] = cfg.get('poll_interval_seconds', 10)
                        except Exception:
                            pass

                stop_event = threading.Event()
                # Instantiate worker correctly using keyword args so arguments aren't misinterpreted.
                worker = WhatsAppWorker(config=config_for_worker, provider_config=provider_conf or {}, stop_event=stop_event)

                # Now call worker to process the single ticket
                worker.process_single_ticket(ticket_number, is_test=False)
            except Exception as e:
                print(f"Error in WhatsApp thread for ticket {ticket_number}: {e}")

        thread = threading.Thread(target=_execute_send, daemon=True)
        thread.start()
