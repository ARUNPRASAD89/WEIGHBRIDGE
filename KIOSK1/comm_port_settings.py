import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, QHBoxLayout, QVBoxLayout, QGroupBox, 
    QComboBox, QRadioButton, QButtonGroup, QGridLayout, QDialog, QMessageBox
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

# Import serial for live diagnostics
try:
    import serial
    from serial.tools import list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False

from db_utils import fetch_one, execute_query

class CommPortSettings(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Comm Port Settings")
        
        # --- MODIFICATION: Set initial size based on screen size for better scaling ---
        screen = QApplication.primaryScreen()
        if screen:
            rect = screen.availableGeometry()
            self.setMinimumSize(rect.width() // 3, rect.height() // 2)
        else:
            self.setMinimumSize(640, 480) # Fallback size

        self.serial_port = None

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # --- MODIFICATION: Use point size for font for better scaling ---
        title = QLabel("Comm Port Settings")
        title_font = title.font()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        prop_group = QGroupBox("General Properties")
        prop_layout = QGridLayout()
        prop_layout.setVerticalSpacing(8)
        prop_layout.setHorizontalSpacing(10)

        prop_layout.addWidget(QLabel("Comm Port:"), 0, 0)
        self.comm_port_combo = QComboBox()
        if SERIAL_AVAILABLE:
            self.comm_port_combo.addItems([port.device for port in list_ports.comports()])
        else:
            self.comm_port_combo.addItems(["COM1", "COM2", "COM3", "COM4"]) # Fallback
        prop_layout.addWidget(self.comm_port_combo, 0, 1)
        
        prop_layout.addWidget(QLabel("Parity Replace Char:"), 1, 0)
        self.parity_replace_edit = QLineEdit("?")
        self.parity_replace_edit.setMaxLength(1)
        prop_layout.addWidget(self.parity_replace_edit, 1, 1)

        prop_layout.addWidget(QLabel("Input Buffer Length:"), 2, 0)
        self.input_len_edit = QLineEdit("1024")
        prop_layout.addWidget(self.input_len_edit, 2, 1)

        prop_layout.addWidget(QLabel("Handshaking:"), 3, 0)
        self.handshake_combo = QComboBox()
        self.handshake_combo.addItems(["None", "XON/XOFF", "RTS/CTS", "DSR/DTR"])
        prop_layout.addWidget(self.handshake_combo, 3, 1)

        prop_layout.addWidget(QLabel("DTR Enable:"), 4, 0)
        self.dtr_true_radio = QRadioButton("True")
        self.dtr_false_radio = QRadioButton("False")
        self.dtr_button_group = QButtonGroup()
        self.dtr_button_group.addButton(self.dtr_true_radio); self.dtr_button_group.addButton(self.dtr_false_radio)
        dtr_hbox = QHBoxLayout()
        dtr_hbox.addWidget(self.dtr_true_radio); dtr_hbox.addWidget(self.dtr_false_radio)
        dtr_hbox.addStretch()
        prop_layout.addLayout(dtr_hbox, 4, 1)
        prop_group.setLayout(prop_layout)

        set_group = QGroupBox("Port Settings")
        set_layout = QGridLayout()
        set_layout.setVerticalSpacing(8)
        set_layout.setHorizontalSpacing(10)

        set_layout.addWidget(QLabel("Baud Rate:"), 0, 0)
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(["1200", "2400", "4800", "9600", "19200", "38400", "57600", "115200"])
        set_layout.addWidget(self.baud_combo, 0, 1)

        set_layout.addWidget(QLabel("Parity:"), 1, 0)
        self.parity_combo = QComboBox()
        self.parity_combo.addItems(["None", "Even", "Odd", "Mark", "Space"])
        set_layout.addWidget(self.parity_combo, 1, 1)

        set_layout.addWidget(QLabel("Data Bits:"), 2, 0)
        self.databits_combo = QComboBox()
        self.databits_combo.addItems(["5", "6", "7", "8"])
        set_layout.addWidget(self.databits_combo, 2, 1)

        set_layout.addWidget(QLabel("Stop Bit:"), 3, 0)
        self.stopbit_combo = QComboBox()
        self.stopbit_combo.addItems(["1", "1.5", "2"])
        set_layout.addWidget(self.stopbit_combo, 3, 1)
        set_group.setLayout(set_layout)

        cols = QHBoxLayout()
        cols.addWidget(prop_group, 1) # Add stretch factor
        cols.addWidget(set_group, 1)  # Add stretch factor
        main_layout.addLayout(cols, 1) # --- MODIFICATION: Add stretch factor to the layout

        display_group = QGroupBox("Live Data Display")
        display_layout = QHBoxLayout(display_group)
        self.data_display = QLineEdit()
        self.data_display.setReadOnly(True)
        self.data_display.setStyleSheet("background-color: #f0f0f0;")
        self.diagnose_btn = QPushButton("Read From Port")
        display_layout.addWidget(self.data_display)
        display_layout.addWidget(self.diagnose_btn)
        main_layout.addWidget(display_group)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.save_btn = QPushButton("Save Settings")
        self.exit_btn = QPushButton("Exit")
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.exit_btn)
        main_layout.addLayout(btn_layout)

        self.save_btn.clicked.connect(self.save_settings)
        self.diagnose_btn.clicked.connect(self.diagnose_port)
        self.exit_btn.clicked.connect(self.exit_to_config)

        self.load_settings()

    def load_settings(self):
        """Loads settings from the commport table and populates the form."""
        try:
            settings = fetch_one('SELECT * FROM public.commport WHERE comportno = 1')
            if settings:
                self.comm_port_combo.setCurrentText(settings.get("settings", "COM1"))
                self.input_len_edit.setText(str(settings.get("inputlen", "1024")))
                self.parity_replace_edit.setText(settings.get("parityreplace", "?"))
                self.handshake_combo.setCurrentText(settings.get("handshaking", "None"))
                
                if settings.get("dtrenable") == 1:
                    self.dtr_true_radio.setChecked(True)
                else:
                    self.dtr_false_radio.setChecked(True)

                self.baud_combo.setCurrentText(str(settings.get("baudrate", "9600")))
                self.parity_combo.setCurrentText(settings.get("parity", "None"))
                self.databits_combo.setCurrentText(str(settings.get("databits", "8")))
                self.stopbit_combo.setCurrentText(str(settings.get("stopbit", "1")))
            else:
                self.dtr_false_radio.setChecked(True)
                self.baud_combo.setCurrentText("9600")
                self.parity_combo.setCurrentText("None")
                self.databits_combo.setCurrentText("8")
                self.stopbit_combo.setCurrentText("1")
        except Exception as e:
            if 'relation "public.commport" does not exist' in str(e):
                 QMessageBox.warning(self, "Table Not Found", "The 'commport' table was not found. Loading default values.")
            else:
                QMessageBox.critical(self, "Database Error", f"Failed to load settings: {e}")

    def save_settings(self):
        """Saves the current form settings to the commport table."""
        try:
            port_no = 1 # Hardcoding to 1 as per schema.
            
            existing = fetch_one('SELECT comportno FROM public.commport WHERE comportno = %s', (port_no,))
            
            params = (
                self.comm_port_combo.currentText(),
                int(self.input_len_edit.text()),
                1 if self.dtr_true_radio.isChecked() else 0,
                self.parity_replace_edit.text(),
                self.handshake_combo.currentText(),
                int(self.baud_combo.currentText()),
                self.parity_combo.currentText(),
                int(self.databits_combo.currentText()),
                self.stopbit_combo.currentText(),
                port_no
            )

            if existing:
                query = """
                    UPDATE public.commport SET
                    settings = %s, inputlen = %s, dtrenable = %s, parityreplace = %s, handshaking = %s,
                    baudrate = %s, parity = %s, databits = %s, stopbit = %s
                    WHERE comportno = %s
                """
                execute_query(query, params)
            else:
                insert_params = (port_no,) + params[:-1]
                query = """
                    INSERT INTO public.commport (
                    comportno, settings, inputlen, dtrenable, parityreplace, handshaking,
                    baudrate, parity, databits, stopbit
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                execute_query(query, insert_params)
            
            QMessageBox.information(self, "Success", f"Settings for Port {self.comm_port_combo.currentText()} saved successfully.")
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Input Length must be a valid number.")
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to save settings: {e}")

    def diagnose_port(self):
        """Opens the configured port, reads data, and displays it."""
        if not SERIAL_AVAILABLE:
            QMessageBox.critical(self, "Serial Library Missing", "The 'pyserial' library is not installed. Please run 'pip install pyserial' to enable this feature.")
            return

        try:
            port = self.comm_port_combo.currentText()
            baudrate = int(self.baud_combo.currentText())
            parity_map = {'None': serial.PARITY_NONE, 'Even': serial.PARITY_EVEN, 'Odd': serial.PARITY_ODD, 'Mark': serial.PARITY_MARK, 'Space': serial.PARITY_SPACE}
            parity = parity_map[self.parity_combo.currentText()]
            stopbits_map = {'1': serial.STOPBITS_ONE, '1.5': serial.STOPBITS_ONE_POINT_FIVE, '2': serial.STOPBITS_TWO}
            stopbits = stopbits_map[self.stopbit_combo.currentText()]
            bytesize = int(self.databits_combo.currentText())

            self.serial_port = serial.Serial(
                port=port,
                baudrate=baudrate,
                parity=parity,
                stopbits=stopbits,
                bytesize=bytesize,
                timeout=1
            )
            
            if self.serial_port.is_open:
                QMessageBox.information(self, "Port Opened", f"Successfully opened {port}. Reading data...")
                data = self.serial_port.read(100)
                if data:
                    self.data_display.setText(f"Data: {data.hex(' ')} (Hex)")
                else:
                    self.data_display.setText("No data received within timeout.")
            else:
                QMessageBox.warning(self, "Failed", f"Could not open port {port}.")

        except serial.SerialException as e:
            QMessageBox.critical(self, "Serial Port Error", f"An error occurred: {e}")
        except ValueError as e:
            QMessageBox.critical(self, "Configuration Error", f"Invalid setting value: {e}")
        finally:
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()
    def exit_to_config(self):
        self.close()
        parent = self.parent()
        if parent:
            parent.show()   
                
