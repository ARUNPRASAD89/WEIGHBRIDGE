import re
import serial
import time
import threading
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot
from db_utils import fetch_one


# Module-level singleton storage
_GLOBAL_SERIAL_MANAGER = None
_GLOBAL_SERIAL_MANAGER_LOCK = threading.Lock()


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
            settings['timeout'] = 1  # Use a 1-second timeout for reads
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
    Worker that runs inside a QThread reading the serial port continuously.
    """
    weight_updated = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self._running = True
        self._lock = threading.Lock()
        self.serial_port = None

    @pyqtSlot()
    def run(self):
        """Main worker loop."""
        if not self.settings:
            self.error_occurred.emit("Comm port settings are missing.")
            return

        try:
            parity_map = {
                'None': serial.PARITY_NONE, 'Even': serial.PARITY_EVEN, 'Odd': serial.PARITY_ODD,
                'Mark': serial.PARITY_MARK, 'Space': serial.PARITY_SPACE
            }
            stopbits_map = {
                '1': serial.STOPBITS_ONE, '1.5': serial.STOPBITS_ONE_POINT_FIVE, '2': serial.STOPBITS_TWO
            }

            with self._lock:
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
            # Ensure serial_port is None if failed
            with self._lock:
                self.serial_port = None
            return
        except Exception as e:
            self.error_occurred.emit(f"Unexpected error opening port: {e}")
            with self._lock:
                self.serial_port = None
            return

        buffer = b''
        try:
            while self._running:
                try:
                    with self._lock:
                        sp = self.serial_port
                    if sp is None:
                        # If port lost while running, break out
                        break
                    # Use in_waiting carefully (attribute may raise if port closed)
                    in_waiting = 0
                    try:
                        in_waiting = sp.in_waiting
                    except Exception:
                        in_waiting = 0

                    if in_waiting > 0:
                        chunk = sp.read(in_waiting)
                        buffer += chunk

                        # Process buffer line by line, assuming newline termination
                        while b'\n' in buffer:
                            line, buffer = buffer.split(b'\n', 1)
                            line = line.strip()  # Remove CR, whitespace, etc.
                            if line:
                                try:
                                    text_data = line.decode('ascii', errors='ignore')
                                    # Extract the first valid number from the string
                                    match = re.search(r'(\d+\.?\d*|\d*\.?\d+)', text_data)
                                    if match:
                                        weight = match.group(1)
                                        # Emit the signal to update the UI
                                        try:
                                            self.weight_updated.emit(str(int(float(weight))))
                                        except Exception:
                                            # fallback to raw string if int conversion fails
                                            self.weight_updated.emit(weight)
                                except Exception:
                                    # Ignore lines that are not valid or parsing fails
                                    pass
                    time.sleep(0.1)
                except Exception as e:
                    # Any runtime read errors
                    self.error_occurred.emit(f"Error during reading: {e}")
                    break
        finally:
            # Always attempt to close the port here
            try:
                with self._lock:
                    if self.serial_port and self.serial_port.is_open:
                        try:
                            self.serial_port.close()
                        except Exception:
                            pass
                    self.serial_port = None
            except Exception:
                pass

    def stop(self):
        """Stops the worker loop and closes the serial port immediately."""
        self._running = False
        # Close immediately to free the port for others
        try:
            with self._lock:
                if self.serial_port and self.serial_port.is_open:
                    try:
                        self.serial_port.close()
                    except Exception:
                        pass
                    self.serial_port = None
        except Exception:
            pass


class SerialManager(QObject):
    """
    Manages the SerialWorker and its thread using reference counting so only
    one actual serial port owner exists across multiple windows.
    """
    weight_updated = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.thread = None
        self.worker = None
        self._refcount = 0
        self._ref_lock = threading.Lock()
        self._start_stop_lock = threading.Lock()

    # Reference-counting API: windows call acquire() when they want weight updates
    # and release() when they no longer need them.
    def acquire(self):
        with self._ref_lock:
            self._refcount += 1
            if self._refcount == 1:
                # First client -> start the worker
                self._start_worker()

    def release(self):
        with self._ref_lock:
            if self._refcount > 0:
                self._refcount -= 1
                if self._refcount == 0:
                    # No more clients -> stop the worker
                    self._stop_worker()

    def _start_worker(self):
        with self._start_stop_lock:
            if self.isRunning():
                return
            settings = get_comm_port_settings()
            self.thread = QThread()
            self.worker = SerialWorker(settings)
            self.worker.moveToThread(self.thread)

            # forward worker signals
            self.worker.weight_updated.connect(self.weight_updated)
            self.worker.error_occurred.connect(self.error_occurred)

            self.thread.started.connect(self.worker.run)
            # ensure worker.stop runs when thread is asked to quit
            self.thread.finished.connect(lambda: None)
            self.thread.start()

    def _stop_worker(self):
        with self._start_stop_lock:
            if not self.isRunning():
                # nothing to stop
                return
            if self.worker:
                try:
                    self.worker.stop()
                except Exception:
                    pass
            if self.thread:
                try:
                    self.thread.quit()
                    self.thread.wait(2000)  # wait up to 2s for a clean stop
                except Exception:
                    pass

            # cleanup
            try:
                self.thread = None
                self.worker = None
            except Exception:
                pass

    def isRunning(self):
        return self.thread is not None and self.thread.isRunning()

    # Convenience: allow an external consumer to request immediate start/stop
    def start(self):
        self.acquire()

    def stop(self):
        self.release()


def get_serial_manager():
    """
    Returns the global shared SerialManager instance (singleton).
    """
    global _GLOBAL_SERIAL_MANAGER
    with _GLOBAL_SERIAL_MANAGER_LOCK:
        if _GLOBAL_SERIAL_MANAGER is None:
            _GLOBAL_SERIAL_MANAGER = SerialManager()
        return _GLOBAL_SERIAL_MANAGER
