; Inno Setup script for Python + SQLite Weighbridge
; Build locally or via GitHub Actions

#define AppName "Weighbridge"
#define AppPublisher "Your Company"
#define AppURL "https://github.com/ARUNPRASAD89/WEIGHBRIDGE"
; AppVersion is provided by CI via /DAppVersion=... ; defaults to 1.0.0
#define AppVersion GetStringDef("AppVersion", "1.0.0")
#define InstallDirName "{autopf}\Weighbridge"

[Setup]
AppId={{3E3C7B17-8A3C-4A31-9B83-9C38A0D1B66A}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
DefaultDirName={#InstallDirName}
DefaultGroupName={#AppName}
UninstallDisplayIcon={app}\Weighbridge.exe
OutputDir=installer\dist
OutputBaseFilename=Weighbridge-{#AppVersion}-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=admin
DisableDirPage=no
DisableProgramGroupPage=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional tasks:"; Flags: unchecked

[Files]
; PyInstaller one-folder output
Source: "dist\Weighbridge\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

; Config template (only on first install)
Source: "installer\defaults\config.json"; DestDir: "{commonappdata}\Weighbridge"; Flags: onlyifdoesntexist

[Dirs]
Name: "{commonappdata}\Weighbridge"; Flags: uninsneveruninstall
Name: "{commonappdata}\Weighbridge\data"; Flags: uninsneveruninstall
Name: "{commonappdata}\Weighbridge\logs"; Flags: uninsneveruninstall

[Icons]
Name: "{group}\Weighbridge"; Filename: "{app}\Weighbridge.exe"
Name: "{commondesktop}\Weighbridge"; Filename: "{app}\Weighbridge.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Weighbridge.exe"; Description: "Launch Weighbridge now"; Flags: nowait postinstall skipifsilent