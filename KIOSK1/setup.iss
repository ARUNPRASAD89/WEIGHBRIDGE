; ===================================================================
;  Inno Setup Script for the Complete Weighbridge Suite (recommended)
; ===================================================================

[Setup]
AppName=Weighbridge Suite
AppVersion=2.0
AppPublisher=sssweighsystems
DefaultDirName={commonpf}\WeighbridgeSuite
DefaultGroupName=Weighbridge Suite
OutputBaseFilename=Weighbridge_Suite_v2_Installer
OutputDir=.\installer_output
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=admin
; Use Unicode installer if you use non-ASCII in strings:
; Unicode=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon_kiosk"; Description: "Create a desktop shortcut for the &Kiosk App"; GroupDescription: "Desktop Shortcuts:"; Flags: checkedonce
Name: "desktopicon_whatsapp"; Description: "Create a desktop shortcut for the &WhatsApp Manager"; GroupDescription: "Desktop Shortcuts:"; Flags: checkedonce
Name: "launch_whatsapp_postinstall"; Description: "Launch WhatsApp Manager after setup"; Flags: unchecked
Name: "autostart_whatsapp"; Description: "Run WhatsApp Manager at system startup (all users)"; Flags: unchecked

[Files]
; --- Bundle BOTH application FOLDERS (the entire --onedir dist folders) ---
Source: "dist\WeighbridgeApp\*"; DestDir: "{app}\Kiosk"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "dist\WhatsAppManager\*"; DestDir: "{app}\AdminTools"; Flags: ignoreversion recursesubdirs createallsubdirs


[Icons]
; Start Menu group icons
Name: "{group}\Weighbridge Kiosk App"; Filename: "{app}\Kiosk\WeighbridgeApp.exe"
Name: "{group}\WhatsApp Manager"; Filename: "{app}\AdminTools\WhatsAppManager.exe"
Name: "{group}\Uninstall Weighbridge Suite"; Filename: "{uninstallexe}"

; Desktop shortcuts (tied to Tasks checkboxes)
Name: "{commondesktop}\Weighbridge Kiosk"; Filename: "{app}\Kiosk\WeighbridgeApp.exe"; Tasks: desktopicon_kiosk
Name: "{commondesktop}\WhatsApp Manager"; Filename: "{app}\AdminTools\WhatsAppManager.exe"; Tasks: desktopicon_whatsapp

[Registry]
; Optional: add WhatsAppManager to system autostart for all users if user selected the autostart task.
; Note: Writing to HKLM requires admin privileges (installer runs elevated).
Root: HKLM; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "WeighbridgeWhatsAppManager"; ValueData: """{app}\AdminTools\WhatsAppManager.exe"""; Flags: uninsdeletevalue; Tasks: autostart_whatsapp

[Run]
; Launch Kiosk app after install (no checkbox, immediate)
Filename: "{app}\Kiosk\WeighbridgeApp.exe"; Description: "Launch Weighbridge Kiosk App"; Flags: nowait postinstall skipifsilent

; Optional launch WhatsApp Manager (checkbox controlled)
Filename: "{app}\AdminTools\WhatsAppManager.exe"; Description: "Launch WhatsApp Manager"; Flags: nowait postinstall skipifsilent; Tasks: launch_whatsapp_postinstall