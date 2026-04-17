; Inno Setup Script — NaverBlogAuto
#define MyAppName "NaverBlogAuto"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "kingth0506"
#define MyAppExeName "NaverBlogAuto.exe"

[Setup]
AppId={{7B2C8A5E-4F1D-4A3C-9B2D-1E8F3C7A6D45}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=installer
OutputBaseFilename=NaverBlogAuto_Install
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"

[Tasks]
Name: "desktopicon"; Description: "바탕화면 아이콘 생성"; GroupDescription: "추가 아이콘:"

[Files]
Source: "dist\NaverBlogAuto\NaverBlogAuto.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\NaverBlogAuto\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "프로그램 실행"; Flags: nowait postinstall skipifsilent
