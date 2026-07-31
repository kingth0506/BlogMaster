; Inno Setup Script — 블로그마스터
#define MyAppName "블로그마스터"
#define MyAppVersion "2.6.3"
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
; ⚠ _internal 통째 삭제 금지 — 사용자 데이터(generated_posts_*.json / logs / saved_images / crawled_*.json)가
;   _internal 안에 저장되므로, 재설치 시 덮어쓰기만 하고 데이터는 보존한다. (자동업데이트 robocopy /E 와 동일)
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
