# Opens the built-in Windows Camera app (works on Windows 10/11)
# Requires pywin32 (pip install pywin32). If pywin32 is not available, fallback to os.startfile.

import os
import subprocess

try:
    import win32api
    import win32con
    import win32gui
    # ShellExecute to launch the UWP Camera app via its URI
    win32api.ShellExecute(None, "open", "microsoft.windows.camera:", None, ".", win32con.SW_SHOWNORMAL)
except Exception:
    # Fallback: use os.startfile or start command
    try:
        os.startfile("microsoft.windows.camera:")
    except Exception:
        # Another fallback using shell start
        subprocess.run('start microsoft.windows.camera:', shell=True)