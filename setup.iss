; Inno Setup Script — 블로그마스터
#define MyAppName "블로그마스터"
#define MyAppVersion "2.4.2"
#define MyAppPublisher "kingth0506"
#define MyAppExeName "BlogMaster.exe"

[Setup]
AppId={{7B2C8A5E-4F1D-4A3C-9B2D-1E8F3C7A6D45}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\BlogMaster
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=installer
OutputBaseFilename=BlogMaster_Install
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
CloseApplications=yes
RestartApplications=yes

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"

[Tasks]
Name: "desktopicon"; Description: "바탕화면 아이콘 생성"; GroupDescription: "추가 아이콘:"

[InstallDelete]
Type: filesandordirs; Name: "{app}\_internal"
Type: files; Name: "{app}\NaverBlogAuto.exe"
Type: files; Name: "{userdesktop}\NaverBlogAuto.lnk"
Type: files; Name: "{commondesktop}\NaverBlogAuto.lnk"
Type: files; Name: "{group}\NaverBlogAuto.lnk"

[Files]
Source: "dist\BlogMaster\BlogMaster.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\BlogMaster\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "프로그램 실행"; Flags: nowait postinstall
