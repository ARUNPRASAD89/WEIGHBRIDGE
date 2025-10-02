import os
import sys

def resource_path(*path_segments):
    """
    Return an absolute path to a bundled resource.

    Resolution order:
      - If running from PyInstaller onefile: sys._MEIPASS contains extracted files.
      - If running from PyInstaller onedir: data files sit next to the executable (os.path.dirname(sys.executable)).
      - If running from source: resolve relative to this file's directory (project layout).
    Usage:
      resource_path('vehicle_images', 'car1.jpg')
      resource_path('assets', 'icons', 'weighbridge_icon.png')
    """
    # If running in a PyInstaller bundle, sys.frozen is True and _MEIPASS contains extracted files
    if getattr(sys, 'frozen', False):
        base_path = getattr(sys, '_MEIPASS', None)
        if not base_path:
            # onedir case: data files live next to the executable
            base_path = os.path.dirname(sys.executable)
    else:
        # Running from source: resolve relative to this file
        base_path = os.path.dirname(os.path.abspath(__file__))
        # If your project layout keeps assets one level up, uncomment and adjust:
        # base_path = os.path.abspath(os.path.join(base_path, '..'))

    return os.path.join(base_path, *path_segments)