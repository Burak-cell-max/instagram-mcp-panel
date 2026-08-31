; Inno Setup script for the local Instagram panel.
; Build:  python installer/build.py   (runs PyInstaller then this)
; Output: installer/Output/Instagram-Panel-Setup.exe

#define MyAppName "Instagram Panel"
#define MyAppExe  "Instagram Panel.exe"
#ifndef MyAppVersion
  #define MyAppVersion "0.1.0"
#endif
#define MyAppPublisher "Bitronix"
#define MyAppURL "https://github.com/Burak-cell-max/instagram-mcp-panel"
; RepoRoot is passed on the ISCC command line by build.py (-DRepoRoot=...)
#ifndef RepoRoot
  #define RepoRoot ".."
#endif

[Setup]
AppId={{4A3365FF-5992-492E-8CE3-0B4BA54C2C2D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={userappdata}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir={#RepoRoot}\installer\Output
OutputBaseFilename=Instagram-Panel-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExe}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "tr"; MessagesFile: "compiler:Languages\Turkish.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "{#RepoRoot}\dist\{#MyAppExe}"; DestDir: "{app}"; Flags: ignoreversion
; blank config on first install only — keeps the user's token on upgrades
Source: "{#RepoRoot}\.mcp.json.example"; DestDir: "{app}"; DestName: ".mcp.json"; Flags: onlyifdoesntexist
Source: "{#RepoRoot}\panel\README.md"; DestDir: "{app}"; DestName: "README.md"; Flags: ignoreversion isreadme

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"; WorkingDir: "{app}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{userdesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExe}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\bin"
Type: filesandordirs; Name: "{app}\media"
Type: files; Name: "{app}\queue.db*"
Type: files; Name: "{app}\state.json"
