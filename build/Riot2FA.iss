#ifndef AppVersion
  #error AppVersion must be passed with /DAppVersion=...
#endif

[Setup]
AppId={{F4AEE515-906A-45F4-83BB-23AE750F62F3}
AppName=Riot 2FA
AppVersion={#AppVersion}
AppPublisher=Sysys
DefaultDirName={localappdata}\Programs\Riot 2FA
DefaultGroupName=Riot 2FA
UninstallDisplayIcon={app}\Riot2FA.exe
OutputDir=..\dist
OutputBaseFilename=Riot2FA-Setup
SetupIconFile=..\images\icon.ico
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
CloseApplications=yes
RestartApplications=no
WizardStyle=modern

[Tasks]
Name: desktopicon; Description: Create a desktop shortcut; GroupDescription: Additional shortcuts:

[Files]
Source: "..\dist\Riot2FA\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Riot 2FA"; Filename: "{app}\Riot2FA.exe"
Name: "{autodesktop}\Riot 2FA"; Filename: "{app}\Riot2FA.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Riot2FA.exe"; Description: Launch Riot 2FA; Flags: nowait postinstall skipifsilent
