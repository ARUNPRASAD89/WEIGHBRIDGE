import sys
import os
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QDialog, QWidget, QLabel, QPushButton, QHBoxLayout, QVBoxLayout, QGroupBox, 
    QComboBox, QLineEdit, QMessageBox, QFileDialog
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

try:
    import cv2
    CAMERA_AVAILABLE = True
except ImportError:
    CAMERA_AVAILABLE = False

from db_utils import fetch_one, execute_query

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
            self.setMinimumSize(500, 400) # Fallback size

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

        main_layout.addWidget(settings_group)

        actions_layout = QHBoxLayout()
        actions_layout.addStretch()
        self.test_btn = QPushButton("Test Camera")
        actions_layout.addWidget(self.test_btn)
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

        self.browse_btn.clicked.connect(self.browse_folder)
        self.test_btn.clicked.connect(self.test_camera)
        self.save_btn.clicked.connect(self.save_settings)
        self.exit_btn.clicked.connect(self.close)

        self.load_settings()

    def populate_cameras(self):
        if not CAMERA_AVAILABLE:
            self.camera_combo.addItems(["Camera Library Missing"])
            return
        
        self.camera_combo.clear()
        indices = []
        for i in range(5): # Check first 5 indices
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                indices.append(i)
                cap.release()
        
        if not indices:
            self.camera_combo.addItem("No Cameras Found")
        else:
            for i in indices:
                self.camera_combo.addItem(f"Camera {i}", i)

    def browse_folder(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Folder")
        if directory:
            self.folder_edit.setText(directory)

    def load_settings(self):
        try:
            settings = fetch_one("SELECT * FROM camerasettings WHERE id = 1")
            if settings:
                cam_index_val = settings.get("cameraindex")
                if cam_index_val is not None:
                    cam_index = self.camera_combo.findData(cam_index_val)
                    if cam_index != -1:
                        self.camera_combo.setCurrentIndex(cam_index)
                
                self.resolution_combo.setCurrentText(settings.get("resolution", "640x480"))
                self.folder_edit.setText(settings.get("camerafolder", ""))
            else:
                QMessageBox.information(self, "No Settings", "No saved camera settings found. Please configure and save.")
        except Exception as e:
            if 'relation "camerasettings" does not exist' in str(e):
                QMessageBox.warning(self, "Table Not Found", "The 'camerasettings' table was not found. Please create it in the database.")
            else:
                QMessageBox.critical(self, "Database Error", f"Failed to load settings: {e}")

    def save_settings(self):
        try:
            cam_index = self.camera_combo.currentData()
            resolution = self.resolution_combo.currentText()
            folder = self.folder_edit.text()

            if not folder:
                QMessageBox.warning(self, "Folder Required", "Please specify a folder to save images.")
                return
            
            if cam_index is None:
                QMessageBox.warning(self, "Camera Required", "Please select a valid camera.")
                return

            existing = fetch_one("SELECT id FROM camerasettings WHERE id = 1")
            
            if existing:
                query = "UPDATE camerasettings SET cameraindex = %s, resolution = %s, camerafolder = %s WHERE id = 1"
                params = (cam_index, resolution, folder)
            else:
                query = "INSERT INTO camerasettings (id, cameraindex, resolution, camerafolder) VALUES (1, %s, %s, %s)"
                params = (cam_index, resolution, folder)
            
            execute_query(query, params)
            QMessageBox.information(self, "Success", "Camera settings saved successfully.")

        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to save settings: {e}")

    def test_camera(self):
        if not CAMERA_AVAILABLE:
            QMessageBox.critical(self, "Library Missing", "The 'opencv-python' library is not installed.")
            return

        cam_index = self.camera_combo.currentData()
        if cam_index is None:
            QMessageBox.warning(self, "No Camera", "No camera selected or available.")
            return
            
        cap = cv2.VideoCapture(cam_index)
        if not cap.isOpened():
            QMessageBox.critical(self, "Error", f"Could not open Camera {cam_index}.")
            return
        
        try:
            res_text = self.resolution_combo.currentText().split('x')
            width, height = int(res_text[0]), int(res_text[1])
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

            while True:
                ret, frame = cap.read()
                if not ret: 
                    QMessageBox.warning(self, "Stream Error", "Failed to grab frame from camera.")
                    break
                cv2.imshow(f"Test - Camera {cam_index} (Press 'q' to close)", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'): 
                    break
        finally:
            cap.release()
            cv2.destroyAllWindows()

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
        """Shows the parent (ConfigurationWindow) when this dialog is closed."""
        parent = self.parent()
        if parent:
            parent.show()
        super().closeEvent(event)
