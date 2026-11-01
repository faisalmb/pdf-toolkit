; installer.iss — برنامج تثبيت PDF Merger (Inno Setup 6)
;
; يثبّت المجلد الناتج من PyInstaller (dist\PDFMerger) للمستخدم الحالي فقط
; داخل %LOCALAPPDATA%\Programs، فلا يحتاج صلاحيات مدير ولا يظهر طلب UAC.
; يضيف اختصارًا في قائمة ابدأ (واختياريًا على سطح المكتب) وبرنامج إزالة
; يظهر في "التطبيقات المثبّتة".
;
; البناء:  ISCC.exe installer.iss   (بعد: pyinstaller --noconfirm PDFMerger.spec)
; الناتج:  installer_output\PDFMerger-Setup-<الإصدار>.exe

#define AppName "PDF Merger"
#define AppVersion "11.0.0"
#define AppPublisher "PDF Merger"
#define AppExe "PDFMerger.exe"

[Setup]
; معرّف ثابت: لا تغيّره بين الإصدارات حتى يُحدّث التثبيتُ الجديد القديمَ بدل تكراره
AppId={{6F1E2B7A-3C54-4D8E-9A21-5B7C0D4E8F13}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
VersionInfoVersion={#AppVersion}
VersionInfoDescription={#AppName} Setup
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=installer_output
OutputBaseFilename=PDFMerger-Setup-{#AppVersion}
SetupIconFile=app_icon.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
#ifexist AddBackslash(CompilerPath) + "Languages\Arabic.isl"
Name: "arabic"; MessagesFile: "compiler:Languages\Arabic.isl"
#endif

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "dist\PDFMerger\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
