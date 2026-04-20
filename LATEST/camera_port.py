import sys
import os
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QDialog, QWidget, QLabel, QPushButton, QHBoxLayout, QVBoxLayout, QGroupBox,
    QComboBox, QLineEdit, QMessageBox, QFileDialog
)
from PyQt5.QtGui import QFont, QImage, QPixmap
from PyQt5.QtCore import Qt, QTimer

# Optional OpenCV for camera feed
try:
    import cv2
    CAMERA_AVAILABLE = True
except Exception:
    cv2 = None
    CAMERA_AVAILABLE = False

import numpy as np

# Optional Tesseract for OCR
try:
    import pytesseract
    _USE_TESSERACT = True
except Exception:
    pytesseract = None
    _USE_TESSERACT = False

# --- NEW: Function to handle bundled Tesseract path ---
def setup_tesseract_for_bundle():
    """
    Sets the path for Tesseract OCR if running as a PyInstaller bundle.
    This makes the OCR feature work out-of-the-box without user configuration.
    """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # This is the path to the temporary folder where PyInstaller unpacks files
        bundle_dir = sys._MEIPASS
        
        # Path to the bundled tesseract executable
        tesseract_exe_path = os.path.join(bundle_dir, 'tesseract.exe')
        
        # Check if the bundled executable exists before setting the path
        if os.path.exists(tesseract_exe_path):
            pytesseract.pytesseract.tesseract_cmd = tesseract_exe_path
            
            # Set the TESSDATA_PREFIX environment variable to the bundled tessdata folder
            tessdata_dir = os.path.join(bundle_dir, 'tessdata')
            os.environ['TESSDATA_PREFIX'] = tessdata_dir
            print(f"INFO: Tesseract configured for bundled app.")
            return True
    return False

# --- MODIFIED: Call the setup function at startup ---
_IS_BUNDLED = setup_tesseract_for_bundle()

# Default tesseract path (used as a fallback or for development)
_DEFAULT_TESSERACT_PATH = r'D:\Program Files\Tesseract-OCR\tesseract.exe'
if not _IS_BUNDLED and _USE_TESSERACT:
    try:
        # Only set this hardcoded path if not running in a bundle
        pytesseract.pytesseract.tesseract_cmd = _DEFAULT_TESSERACT_PATH
    except Exception:
        pass

from db_utils import fetch_one, execute_query

class TestCameraDialog(QDialog):
    """
    A PyQt based camera preview dialog so we don't rely on cv2.imshow / highgui.
    This avoids the OpenCV error "The function is not implemented" when OpenCV
    was built without GUI support.
    """
    def __init__(self, cam_index, resolution=(640, 480), parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Test - Camera {cam_index}")
        self.cam_index = cam_index
        self.width, self.height = resolution
        self.cap = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._grab_frame)

        self.preview_label = QLabel("Starting camera...")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(320, 240)
        self.preview_label.setStyleSheet("background: black; color: white;")

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)

        layout = QVBoxLayout(self)
        layout.addWidget(self.preview_label)
        layout.addWidget(close_btn)

        self._open_camera_and_start()

    def _open_camera_and_start(self):
        if not CAMERA_AVAILABLE:
            self.preview_label.setText("OpenCV not available")
            return

        # Try various backends as a best-effort to open the camera
        backends = []
        try: backends.append(cv2.CAP_DSHOW)
        except Exception: pass
        try: backends.append(cv2.CAP_MSMF)
        except Exception: pass
        try: backends.append(cv2.CAP_V4L2)
        except Exception: pass
        backends.append(0)

        cap = None
        for backend in backends:
            try:
                trial = cv2.VideoCapture(self.cam_index) if backend == 0 else cv2.VideoCapture(self.cam_index, backend)
            except Exception:
                trial = None
            if trial and trial.isOpened():
                cap = trial
                break
            else:
                try:
                    if trial: trial.release()
                except Exception:
                    pass

        if not cap or not cap.isOpened():
            self.preview_label.setText(f"Could not open Camera {self.cam_index}")
            return

        try:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, int(self.width))
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, int(self.height))
        except Exception:
            pass

        self.cap = cap
        self.timer.start(33)

    def _grab_frame(self):
        if not self.cap:
            return
        try:
            ret, frame = self.cap.read()
        except Exception:
            ret, frame = False, None

        if not ret or frame is None:
            self.preview_label.setText("Failed to grab frame")
            return

        # Convert BGR -> RGB and display via QImage
        try:
            if frame.ndim == 2:
                rgb = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
            elif frame.shape[2] == 4:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGRA2RGB)
            else:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            rgb = np.ascontiguousarray(rgb)
            h, w, ch = rgb.shape
            bytes_per_line = ch * w
            qimg = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888).copy()
            pix = QPixmap.fromImage(qimg)
            label_w = max(1, self.preview_label.width())
            label_h = max(1, self.preview_label.height())
            scaled = pix.scaled(label_w, label_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.preview_label.setPixmap(scaled)
        except Exception:
            self.preview_label.setText("Error displaying frame")

    def grab_current_frame(self):
        """
        Attempt a single synchronous frame grab and return the raw frame (BGR) or None.
        Useful for LPR snapshot without launching the preview dialog.
        """
        if not CAMERA_AVAILABLE:
            return None
        # Try same multi-backend open logic as above
        backends = []
        try: backends.append(cv2.CAP_DSHOW)
        except Exception: pass
        try: backends.append(cv2.CAP_MSMF)
        except Exception: pass
        try: backends.append(cv2.CAP_V4L2)
        except Exception: pass
        backends.append(0)

        cap = None
        for backend in backends:
            try:
                trial = cv2.VideoCapture(self.cam_index) if backend == 0 else cv2.VideoCapture(self.cam_index, backend)
            except Exception:
                trial = None
            if trial and trial.isOpened():
                cap = trial
                break
            else:
                try:
                    if trial: trial.release()
                except Exception:
                    pass

        if not cap:
            return None

        try:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, int(self.width))
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, int(self.height))
            # read a few frames to let camera auto-adjust exposure
            frame = None
            for _ in range(5):
                ret, f = cap.read()
                if ret and f is not None:
                    frame = f
                    break
            return frame
        finally:
            try:
                cap.release()
            except Exception:
                pass

    def closeEvent(self, event):
        try:
            if self.timer.isActive():
                self.timer.stop()
        except Exception:
            pass
        try:
            if self.cap:
                self.cap.release()
        except Exception:
            pass
        super().closeEvent(event)


class CameraPortSettings(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Camera Port Settings")

        # --- MODIFICATION: Set initial size based on screen size for better scaling ---
        screen = QApplication.primaryScreen()
        if screen:
            rect = screen.availableGeometry()
            self.setMinimumSize(rect.width() // 4, rect.height() // 3)
        else:
            self.setMinimumSize(500, 400)  # Fallback size

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # --- MODIFICATION: Use point size for font for better scaling ---
        title = QLabel("Camera Settings")
        title_font = title.font()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        settings_group = QGroupBox("Configuration")
        settings_layout = QVBoxLayout(settings_group)

        cam_layout = QHBoxLayout()
        cam_layout.addWidget(QLabel("Select Camera:"))
        self.camera_combo = QComboBox()
        self.populate_cameras()
        cam_layout.addWidget(self.camera_combo)
        settings_layout.addLayout(cam_layout)

        res_layout = QHBoxLayout()
        res_layout.addWidget(QLabel("Resolution:"))
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(["640x480", "800x600", "1280x720", "1920x1080"])
        res_layout.addWidget(self.resolution_combo)
        settings_layout.addLayout(res_layout)

        folder_layout = QHBoxLayout()
        folder_layout.addWidget(QLabel("Camera Folder:"))
        self.folder_edit = QLineEdit()
        self.folder_edit.setPlaceholderText("Select a base directory to save images...")
        self.browse_btn = QPushButton("Browse...")
        folder_layout.addWidget(self.folder_edit)
        folder_layout.addWidget(self.browse_btn)
        settings_layout.addLayout(folder_layout)

        # --- NEW: Tesseract path UI ---
        tess_layout = QHBoxLayout()
        tess_layout.addWidget(QLabel("Tesseract Path:"))
        self.tesseract_edit = QLineEdit()
        self.tesseract_edit.setPlaceholderText(_DEFAULT_TESSERACT_PATH)
        self.tess_browse_btn = QPushButton("Browse...")
        tess_layout.addWidget(self.tesseract_edit)
        tess_layout.addWidget(self.tess_browse_btn)
        settings_layout.addLayout(tess_layout)

        main_layout.addWidget(settings_group)

        actions_layout = QHBoxLayout()
        actions_layout.addStretch()
        self.test_btn = QPushButton("Test Camera")
        self.lpr_btn = QPushButton("Capture & OCR (LPR)")
        actions_layout.addWidget(self.test_btn)
        actions_layout.addWidget(self.lpr_btn)
        main_layout.addLayout(actions_layout)

        # --- MODIFICATION: Add stretch to push buttons to the bottom ---
        main_layout.addStretch(1)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.save_btn = QPushButton("Save Settings")
        self.exit_btn = QPushButton("Exit")
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.exit_btn)
        main_layout.addLayout(btn_layout)

        # Signals
        self.browse_btn.clicked.connect(self.browse_folder)
        self.test_btn.clicked.connect(self.test_camera)
        self.save_btn.clicked.connect(self.save_settings)
        self.exit_btn.clicked.connect(self.close)
        self.tess_browse_btn.clicked.connect(self.browse_tesseract)
        self.lpr_btn.clicked.connect(self.capture_and_ocr)

        # Load DB settings (and try to create missing column if needed)
        self.load_settings()

    def populate_cameras(self):
        if not CAMERA_AVAILABLE:
            self.camera_combo.addItems(["Camera Library Missing"])
            return

        self.camera_combo.clear()
        indices = []
        # Probe first several indices for available cameras
        for i in range(8):  # increase attempts to detect more devices
            try:
                cap = cv2.VideoCapture(i)
                if cap and cap.isOpened():
                    indices.append(i)
                    cap.release()
            except Exception:
                pass

        if not indices:
            self.camera_combo.addItem("No Cameras Found")
        else:
            for i in indices:
                self.camera_combo.addItem(f"Camera {i}", i)

    def browse_folder(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Folder")
        if directory:
            self.folder_edit.setText(directory)

    def browse_tesseract(self):
        # Allow user to pick the tesseract executable
        filt = "Executable Files (*.exe);;All Files (*)"
        path, _ = QFileDialog.getOpenFileName(self, "Select Tesseract Executable", _DEFAULT_TESSERACT_PATH, filt)
        if path:
            self.tesseract_edit.setText(path)

    def load_settings(self):
        # --- MODIFICATION: Don't set pytesseract path here. It's now handled globally. ---
        # We just load the path into the UI field. The OCR function will apply it at runtime.
        try:
            try:
                settings = fetch_one("SELECT * FROM camerasettings WHERE id = 1")
            except Exception as e:
                msg = str(e)
                if 'relation "camerasettings" does not exist' in msg or 'no such table' in msg.lower():
                    QMessageBox.warning(self, "Table Not Found", "The 'camerasettings' table was not found. Please create it in the database.")
                    return
                raise

            if settings:
                cam_index_val = settings.get("cameraindex")
                if cam_index_val is not None:
                    cam_index = self.camera_combo.findData(cam_index_val)
                    if cam_index != -1:
                        self.camera_combo.setCurrentIndex(cam_index)

                self.resolution_combo.setCurrentText(settings.get("resolution", "640x480"))
                self.folder_edit.setText(settings.get("camerafolder", ""))

                tpath = settings.get("tesseractpath") if "tesseractpath" in settings else ""
                self.tesseract_edit.setText(tpath)
            else:
                QMessageBox.information(self, "No Settings", "No saved camera settings found. Please configure and save.")
        except Exception as e:
            msg = str(e)
            if 'column "tesseractpath" does not exist' in msg.lower() or 'unknown column' in msg.lower():
                try:
                    execute_query("ALTER TABLE camerasettings ADD COLUMN tesseractpath TEXT")
                    QMessageBox.information(self, "DB Updated", "Added missing 'tesseractpath' column to camerasettings. Please restart the settings window.")
                except Exception as ex:
                    QMessageBox.warning(self, "DB Warning", f"Could not add tesseractpath column automatically: {ex}")
            else:
                QMessageBox.critical(self, "Database Error", f"Failed to load settings: {e}")

    def save_settings(self):
        # --- This function remains largely the same, its job is to save the user's choices to the DB. ---
        try:
            cam_index = self.camera_combo.currentData()
            resolution = self.resolution_combo.currentText()
            folder = self.folder_edit.text()
            tess_path = self.tesseract_edit.text().strip()

            if not folder:
                QMessageBox.warning(self, "Folder Required", "Please specify a folder to save images.")
                return

            if cam_index is None:
                QMessageBox.warning(self, "Camera Required", "Please select a valid camera.")
                return

            # Simplified save/update logic
            query_update = "UPDATE camerasettings SET cameraindex = %s, resolution = %s, camerafolder = %s, tesseractpath = %s WHERE id = 1"
            query_insert = "INSERT INTO camerasettings (id, cameraindex, resolution, camerafolder, tesseractpath) VALUES (1, %s, %s, %s, %s)"
            params = (cam_index, resolution, folder, tess_path)

            existing = fetch_one("SELECT id FROM camerasettings WHERE id = 1")
            if existing:
                execute_query(query_update, params)
            else:
                execute_query(query_insert, params)

            QMessageBox.information(self, "Success", "Camera settings saved successfully.")
        except Exception as e:
            # Attempt to handle missing column on save as a fallback
            msg = str(e)
            if 'column "tesseractpath" does not exist' in msg.lower():
                 try:
                    execute_query("ALTER TABLE camerasettings ADD COLUMN tesseractpath TEXT")
                    self.save_settings() # Retry the save
                 except Exception as ex:
                    QMessageBox.critical(self, "Database Error", f"Failed to save settings after adding column: {ex}")
            else:
                QMessageBox.critical(self, "Database Error", f"Failed to save settings: {e}")

    def test_camera(self):
        if not CAMERA_AVAILABLE:
            QMessageBox.critical(self, "Library Missing", "The 'opencv-python' library is not installed.")
            return

        cam_index = self.camera_combo.currentData()
        if cam_index is None:
            QMessageBox.warning(self, "No Camera", "No camera selected or available.")
            return

        try:
            res_text = self.resolution_combo.currentText().split('x')
            width, height = int(res_text[0]), int(res_text[1])
        except Exception:
            width, height = 640, 480

        try:
            dlg = TestCameraDialog(cam_index, resolution=(width, height), parent=self)
            dlg.exec_()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Camera test failed: {e}")

    def capture_and_ocr(self):
        # --- MODIFICATION: Apply the user's configured path at the moment of OCR ---
        if not CAMERA_AVAILABLE:
            QMessageBox.critical(self, "Library Missing", "The 'opencv-python' library is not installed.")
            return
        if not _USE_TESSERACT:
            QMessageBox.warning(self, "Tesseract Missing", "pytesseract is not installed.")
            return

        # Apply the path from the UI field, overriding the bundled default if specified.
        # This allows advanced users to use a different Tesseract version.
        tpath = self.tesseract_edit.text().strip()
        if tpath and os.path.exists(tpath):
            try:
                pytesseract.pytesseract.tesseract_cmd = tpath
                print(f"INFO: Using user-defined Tesseract path for OCR: {tpath}")
            except Exception as e:
                QMessageBox.warning(self, "Tesseract Warning", f"Could not apply Tesseract path from settings: {e}")
        elif not _IS_BUNDLED:
             QMessageBox.warning(self, "Tesseract Not Found", "Tesseract is not configured. Please set the path in settings.")
             return

        cam_index = self.camera_combo.currentData()
        if cam_index is None:
            QMessageBox.warning(self, "No Camera", "No camera selected or available.")
            return

        try:
            res_text = self.resolution_combo.currentText().split('x')
            width, height = int(res_text[0]), int(res_text[1])
        except Exception:
            width, height = 640, 480

        try:
            tc = TestCameraDialog(cam_index, resolution=(width, height), parent=self)
            frame = tc.grab_current_frame()
            tc.close()
        except Exception:
            frame = None

        if frame is None:
            QMessageBox.warning(self, "Capture Failed", "Could not capture a frame from the camera.")
            return

        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            rgb = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
        except Exception:
            QMessageBox.warning(self, "Preprocess Failed", "Could not preprocess frame.")
            return

        try:
            config = r'--psm 7'
            text = pytesseract.image_to_string(rgb, config=config).strip()
        except Exception as e:
            QMessageBox.critical(self, "OCR Error", f"pytesseract failed. Ensure the configured path is correct.\n\nError: {e}")
            return

        save_msg = ""
        save_path, err = self.get_image_save_path()
        if save_path:
            try:
                cv2.imwrite(save_path, frame)
                save_msg = f"\nSnapshot saved to: {save_path}"
            except Exception:
                save_msg = "\nSnapshot could not be saved."

        if text:
            QMessageBox.information(self, "OCR Result", f"Extracted text:\n\n{text}{save_msg}")
        else:
            QMessageBox.information(self, "OCR Result", f"No text recognized.{save_msg}")

    def get_image_save_path(self):
        base_folder = self.folder_edit.text()
        if not base_folder:
            return None, "Camera folder is not configured."

        date_folder = os.path.join(base_folder, datetime.now().strftime('%Y-%m-%d'))

        try:
            os.makedirs(date_folder, exist_ok=True)
        except OSError as e:
            return None, f"Could not create directory: {e}"

        timestamp = datetime.now().strftime('%H-%M-%S-%f')
        filename = f"image_{timestamp}.jpg"

        return os.path.join(date_folder, filename), None

    def closeEvent(self, event):
        parent = self.parent()
        if parent:
            parent.show()
        super().closeEvent(event)


if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        win = CameraPortSettings()
        win.show()
        sys.exit(app.exec_())
    except Exception as e:
        print("Failed to launch CameraPortSettings:", e)
