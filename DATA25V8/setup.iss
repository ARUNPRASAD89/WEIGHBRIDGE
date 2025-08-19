; WeighbridgeApp installer with desktop shortcut handling for admin vs per-user installs

[Setup]
AppName=WeighbridgeApp
AppVersion=1.2
; Use common Program Files for machine-wide install. Replace with {autopf} if preferred.
DefaultDirName={commonpf}\WeighbridgeApp
DefaultGroupName=WeighbridgeApp
OutputBaseFilename=WeighbridgeApp_Installer
Compression=lzma
SolidCompression=yes
; Set PrivilegesRequired according to the install type you want:
; - For machine-wide installs (all users), keep admin:
PrivilegesRequired=admin
; - For per-user installs, use: PrivilegesRequired=lowest

[Files]
Source: "D:\DATA28V1\DATA26V9\weighbridge\dist\WeighbridgeApp.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "D:\DATA28V1\DATA26V9\weighbridge\dist\assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs
Source: "D:\DATA28V1\DATA26V9\weighbridge\dist\vehicle_images\*"; DestDir: "{app}\vehicle_images"; Flags: ignoreversion recursesubdirs

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; 

[Icons]
Name: "{group}\WeighbridgeApp"; Filename: "{app}\WeighbridgeApp.exe"
Name: "{group}\Uninstall WeighbridgeApp"; Filename: "{uninstallexe}"
; If installer is running in admin (admin install mode), create an all-users desktop icon.
Name: "{commondesktop}\WeighbridgeApp"; Filename: "{app}\WeighbridgeApp.exe"; Tasks: desktopicon; Check: IsAdminInstallMode
; If not running in admin mode, create a per-user desktop icon.
Name: "{userdesktop}\WeighbridgeApp"; Filename: "{app}\WeighbridgeApp.exe"; Tasks: desktopicon; Check: not IsAdminInstallMode