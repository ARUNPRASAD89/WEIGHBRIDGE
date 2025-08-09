# Weighbridge (Python) — Windows Install with SQLite

This guide creates a Windows installer that:
- Installs the app to: C:\\Program Files\\Weighbridge
- Stores config and SQLite DB in: C:\\ProgramData\\Weighbridge\\
- No Python or pip on client machines (bundled via PyInstaller)

## 1) Setup build environment (one-time on your dev PC)

```powershell
# In repo root
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Update `requirements.txt` with your actual libs.

## 2) Build the app (PyInstaller)

Option A: One-folder (recommended; fewer AV false positives)
```powershell
pyinstaller --noconfirm --clean ^
  --name Weighbridge ^
  --icon installer\\weighbridge.ico ^
  --add-data "assets;assets" ^
  src\\main.py
```
- Output: `dist\\Weighbridge\\` (contains Weighbridge.exe + all libs + Python)

Option B: One-file (single EXE; sometimes triggers AV)
```powershell
pyinstaller --noconfirm --onefile --clean ^
  --name Weighbridge ^
  --icon installer\\weighbridge.ico ^
  --add-data "assets;assets" ^
  src\\main.py
```
- Output: `dist\\Weighbridge.exe` (self-extracts at runtime)

If you need more control, use `pyinstaller.spec`.

## 3) Configure DB and logs in ProgramData

Installer will create:
- Config: C:\\ProgramData\\Weighbridge\\config.json (first install only)
- DB folder: C:\\ProgramData\\Weighbridge\\data\\ (your app creates the file on first run)
- Logs:   C:\\ProgramData\\Weighbridge\\logs\\

Your app should read:
- DB path from config: `C:\\\\ProgramData\\\\Weighbridge\\\\data\\\\weighbridge.db`
- Write logs to ProgramData\\Weighbridge\\logs

## 4) Build the Windows installer (Inno Setup)

- Install Inno Setup: https://jrsoftware.org/isinfo.php
- Open `installer\\Weighbridge_Python.iss` and Build.
- Output EXE at `installer\\dist\\Weighbridge-<version>-Setup.exe`

## 5) CI/CD (GitHub Actions)

- Every push builds the PyInstaller bundle and compiles the installer. Find it in the run's Artifacts.
- Create a tag like `v1.0.0` to publish a GitHub Release with the installer attached.

## 6) Install on client PC

- Run the Setup EXE as Administrator.
- Launch from Start Menu or Desktop shortcut.
- ProgramData content (config, DB, logs) is preserved on upgrades/uninstall.

## Notes

- SQLite requires no service. The standard library `sqlite3` module is included with Python.
- If you use SQLAlchemy or an ORM, list it in `requirements.txt`.
- For serial scales, include `pyserial`.
- Touch mode: ensure UI scaling and optionally launch TabTip on focus if needed.
- Future updates: bump version by creating a new tag (e.g., `v1.0.1`).