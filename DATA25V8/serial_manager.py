import re
import serial
import time
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot
from db_utils import fetch_one

def get_comm_port_settings():
    """
    Fetches comm port settings from the database.
    Returns a dictionary of settings or None if not found.
    """
    try:
        settings = fetch_one('SELECT * FROM public.commport WHERE comportno = 1')
        if settings:
            # Ensure correct types for serial library
            settings['baudrate'] = int(settings.get('baudrate', 9600))
            settings['databits'] = int(settings.get('databits', 8))
            settings['timeout'] = 1 # Use a 1-second timeout for reads
            return settings
        return None
    except Exception:
        # Fallback if DB is not available or table doesn't exist
        return {
            'settings': 'COM3', 'baudrate': 9600, 'parity': 'None', 
            'databits': 8, 'stopbit': '1', 'timeout': 1
        }

class SerialWorker(QObject):
    """
    Worker that runs in a separate thread to read from the serial port
    continuously without freezing the main application.
    """
    weight_updated = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self._running = True
        self.serial_port = None

    @pyqtSlot()
    def run(self):
        """Main worker loop."""
        if not self.settings:
            self.error_occurred.emit("Comm port settings are missing.")
            return

        try:
            parity_map = {'None': serial.PARITY_NONE, 'Even': serial.PARITY_EVEN, 'Odd': serial.PARITY_ODD, 'Mark': serial.PARITY_MARK, 'Space': serial.PARITY_SPACE}
            stopbits_map = {'1': serial.STOPBITS_ONE, '1.5': serial.STOPBITS_ONE_POINT_FIVE, '2': serial.STOPBITS_TWO}

            self.serial_port = serial.Serial(
                port=self.settings.get('settings'),
                baudrate=self.settings.get('baudrate'),
                parity=parity_map.get(self.settings.get('parity', 'None')),
                stopbits=stopbits_map.get(str(self.settings.get('stopbit', '1'))),
                bytesize=self.settings.get('databits'),
                timeout=self.settings.get('timeout')
            )
        except serial.SerialException as e:
            self.error_occurred.emit(f"Failed to open port {self.settings.get('settings')}: {e}")
            return

        buffer = b''
        while self._running:
            try:
                if self.serial_port.in_waiting > 0:
                    buffer += self.serial_port.read(self.serial_port.in_waiting)
                    
                    # Process buffer line by line, assuming newline termination
                    while b'\n' in buffer:
                        line, buffer = buffer.split(b'\n', 1)
                        line = line.strip()  # Remove CR, whitespace, etc.
                        if line:
                            try:
                                text_data = line.decode('ascii')
                                # Extract the first valid number from the string
                                match = re.search(r'(\d+\.?\d*|\d*\.?\d+)', text_data)
                                if match:
                                    weight = match.group(1)
                                    # Emit the signal to update the UI
                                    self.weight_updated.emit(str(int(float(weight))))
                            except (UnicodeDecodeError, ValueError):
                                # Ignore lines that are not valid ascii or numbers
                                pass
                time.sleep(0.1)  # Small delay to prevent high CPU usage
            except Exception as e:
                self.error_occurred.emit(f"Error during reading: {e}")
                self._running = False

        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()

    def stop(self):
        """Stops the worker loop."""
        self._running = False

class SerialManager(QObject):
    """Manages the SerialWorker and its thread."""
    weight_updated = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.thread = None
        self.worker = None

    def start(self):
        """Starts the serial reading thread."""
        settings = get_comm_port_settings()
        
        self.thread = QThread()
        self.worker = SerialWorker(settings)
        self.worker.moveToThread(self.thread)

        # Forward signals from worker
        self.worker.weight_updated.connect(self.weight_updated)
        self.worker.error_occurred.connect(self.error_occurred)
        
        self.thread.started.connect(self.worker.run)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def stop(self):
        """Stops the serial reading thread safely."""
        if self.worker:
            self.worker.stop()
        if self.thread:
            self.thread.quit()
            self.thread.wait()