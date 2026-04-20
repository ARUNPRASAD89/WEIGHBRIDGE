import os
import cv2
import numpy as np
from datetime import datetime
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QImage, QPixmap
from db_utils import fetch_one
from date_time_utils import to_display_date, to_display_time
from PyQt5.QtCore import QDate, QTime

class CameraManager:
    """A class to manage the camera feed, settings, and snapshots."""

    def __init__(self, camera_display_label):
        """
        Initializes the CameraManager.
        Args:
            camera_display_label (QLabel): The label widget to display the camera feed on.
        """
        self.camera_display = camera_display_label
        self.cap = None
        self.camera_timer = QTimer()
        self.camera_timer.timeout.connect(self._update_frame)
        self._camera_failed_reads = 0
        
        # Fetch settings once on initialization
        self.cam_index, self.cam_width, self.cam_height = self._get_camera_settings()

    def _get_camera_settings(self):
        """Fetches camera settings from the database, with sane defaults."""
        try:
            settings = fetch_one("SELECT cameraindex, resolution FROM camerasettings WHERE id = 1")
            if settings:
                cam_index = int(settings.get("cameraindex", 0))
                res_str = settings.get("resolution", "640x480")
                width, height = map(int, res_str.split('x'))
                return cam_index, width, height
        except Exception as e:
            print(f"Could not fetch camera settings: {e}")
        return 0, 640, 480 # Default values

    def start(self):
        """Starts the camera feed."""
        if not cv2:
            self.camera_display.setText("OpenCV (cv2) is not installed.")
            return

        self.stop() # Ensure any existing capture is released

        self.cap = cv2.VideoCapture(self.cam_index, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(self.cam_index) # Fallback
            if not self.cap.isOpened():
                self.camera_display.setText(f"Cannot open camera {self.cam_index}")
                return

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.cam_width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.cam_height)
        
        self.camera_display.setScaledContents(True)
        self.camera_timer.start(33) # Update at ~30 FPS
        self._camera_failed_reads = 0

    def stop(self):
        """Stops the camera feed and releases resources."""
        self.camera_timer.stop()
        if self.cap:
            self.cap.release()
            self.cap = None

    def _update_frame(self):
        """Reads a frame from the camera, converts it, and displays it."""
        if not self.cap or not self.cap.isOpened():
            return

        ret, frame = self.cap.read()
        if not ret or frame is None:
            self._camera_failed_reads += 1
            if self._camera_failed_reads > 10:
                self.camera_display.setText("Camera feed lost.")
                self.stop()
            return
        self._camera_failed_reads = 0

        try:
            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image)
            self.camera_display.setPixmap(pixmap)
        except Exception as e:
            print(f"Error updating camera frame: {e}")

    def get_current_frame(self):
        """Safely gets the current raw frame from the camera for processing."""
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                return frame
        return None

    def save_snapshot(self):
        """Captures the current frame, stamps it with date/time, and saves it."""
        frame = self.get_current_frame()
        if frame is None:
            return None

        try:
            settings = fetch_one("SELECT camerafolder FROM camerasettings WHERE id = 1")
            base_folder = settings.get("camerafolder") if settings else None
            if not base_folder or not os.path.isdir(base_folder):
                print("Warning: Camera folder is not configured or does not exist.")
                return None

            date_folder = os.path.join(base_folder, datetime.now().strftime('%Y-%m-%d'))
            os.makedirs(date_folder, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
            filename = f"image_{timestamp}.jpg"
            fullpath = os.path.join(date_folder, filename)

            # Add timestamp overlay
            stamp = f"{to_display_date(QDate.currentDate())} {to_display_time(QTime.currentTime())}"
            # Add a semi-transparent background for the text for better visibility
            overlay = frame.copy()
            (text_w, text_h), _ = cv2.getTextSize(stamp, cv2.FONT_HERSHEY_SIMPLEX, 1, 2)
            cv2.rectangle(overlay, (10, 10), (20 + text_w, 40 + text_h), (0,0,0), -1)
            alpha = 0.4 
            frame_with_overlay = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)
            cv2.putText(frame_with_overlay, stamp, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)


            cv2.imwrite(fullpath, frame_with_overlay)
            return fullpath
        except Exception as e:
            print(f"Error saving snapshot: {e}")
            return None
