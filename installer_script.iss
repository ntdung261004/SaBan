; === Shooting App Installer Script ===

#define MyAppName "Phần Mềm Bắn Pháo Sa Bàn"
#define MyAppVersion "1.0"
#define MyAppPublisher "MinhLuan"
#define MyAppExeName "SaBan.exe"
#define MyAppIconName "assets\app_icon.ico" 
#define MyOutputFolder "dist\SaBan"

[Setup]
; AppId là một mã định danh duy nhất cho ứng dụng của bạn. 
; Bạn có thể tạo mã mới từ menu Tools > Generate GUID trong Inno Setup.
AppId={{C194D481-22C5-42E1-975E-538F36C58925}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=admin
OutputDir=installers
OutputBaseFilename=setup-{#MyAppName}-{#MyAppVersion}
SetupIconFile={#MyAppIconName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Languages]
; Hỗ trợ Tiếng Anh và Tiếng Việt
Name: "english"; MessagesFile: "compiler:Default.isl"
;Name: "vietnamese"; MessagesFile: "compiler:Languages\Vietnamese.isl"

[Tasks]
; Cho phép người dùng tùy chọn tạo icon trên desktop
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}";

[Files]
; Dòng quan trọng nhất: Lấy TẤT CẢ các file và thư mục con từ thư mục output
; của PyInstaller và đưa vào thư mục cài đặt của người dùng.
Source: "{#MyOutputFolder}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Tạo shortcut trong Start Menu
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"

; Tạo shortcut trên Desktop nếu người dùng chọn
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Cho phép chạy ứng dụng ngay sau khi cài đặt xong
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent