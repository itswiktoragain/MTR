[Setup]
AppId=MTR-Antivirus
AppName=MTR Antivirus
AppVersion=0.2.0
AppPublisher=MTR
DefaultDirName={autopf}\MTR Antivirus
DefaultGroupName=MTR Antivirus
OutputDir=dist
OutputBaseFilename=MTR-Setup
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\MTR.exe
SetupIconFile=build\mtr.ico
WizardStyle=modern
CloseApplications=yes
RestartApplications=no

[Files]
Source: "publish\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{commonprograms}\MTR Antivirus"; Filename: "{app}\MTR.exe"
Name: "{commonstartup}\MTR Antivirus"; Filename: "{app}\MTR.exe"; Parameters: "--background"

[Run]
Filename: "{app}\MTR.exe"; Description: "Open MTR Antivirus"; Flags: nowait postinstall skipifsilent runasoriginaluser
