; ============================================================
; Dyno All In One — Inno Setup Script
; ============================================================

#define AppName      "Dyno All In One"
#define AppVersion   "1.0"
#define AppPublisher "Khoa Lê"
#define AppURL       "https://dynoaio.vercel.app"
#define AppExeName   "DynoAllInOne.exe"
#define AppContact   "https://www.facebook.com/lee.khoa257"

[Setup]
AppId={{B91D9297-2194-4580-BEDE-38CBD8A35DC8}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppContact}
AppUpdatesURL={#AppURL}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=no
LicenseFile=license.txt
OutputDir=output
OutputBaseFilename=DynoAllInOne_Setup_v{#AppVersion}
SetupIconFile=..\images\icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
WizardSizePercent=120
DisableWelcomePage=no
DisableDirPage=no
DisableProgramGroupPage=yes
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=
; Luôn chạy với quyền Administrator
ChangesAssociations=no
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName}
VersionInfoVersion={#AppVersion}
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#AppName} Installer
VersionInfoProductName={#AppName}

; ---- Tùy chỉnh màu sắc wizard (dark theme) ----
WizardImageFile=wizard_banner.png
WizardSmallImageFile=wizard_icon.bmp

[Languages]
Name: "vietnamese"; MessagesFile: "Vietnamese.isl"

[CustomMessages]
vietnamese.WelcomeLabel1=Chào mừng đến với trình cài đặt%n{#AppName}
vietnamese.WelcomeLabel2=Trình cài đặt sẽ hướng dẫn bạn cài đặt {#AppName} lên máy tính.%n%nVui lòng đóng tất cả ứng dụng khác trước khi tiếp tục.%n%nNhấn Tiếp theo để tiếp tục.
vietnamese.FinishedHeadingLabel=Hoàn tất cài đặt {#AppName}
vietnamese.FinishedLabelNoIcons=Cài đặt {#AppName} đã hoàn tất.%nNhấn Kết thúc để thoát.
vietnamese.FinishedLabel=Cài đặt {#AppName} đã hoàn tất.%nỨng dụng có thể được khởi chạy bằng cách chọn biểu tượng đã cài đặt.

[Tasks]
Name: "desktopicon"; Description: "Tạo biểu tượng trên màn hình Desktop"; GroupDescription: "Biểu tượng bổ sung:"; Flags: checkedonce
Name: "startmenuicon"; Description: "Tạo biểu tượng trong Start Menu"; GroupDescription: "Biểu tượng bổ sung:"; Flags: checkedonce

[Files]
; Ứng dụng chính (theme.json và images/ đã bundle bên trong exe)
Source: "..\dist\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion

; Thư mục Apps — cấu trúc thư mục + logo.png cho từng app (không có setup files)
Source: "Apps\*"; DestDir: "{app}\Apps"; Flags: ignoreversion recursesubdirs createallsubdirs

; Thư mục Drivers — chứa driver FTDI, CP210x...
Source: "..\Drivers\*"; DestDir: "{app}\Drivers"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\Gỡ cài đặt {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
; Chạy ứng dụng sau khi cài xong (với quyền admin)
Filename: "{app}\{#AppExeName}"; Description: "Khởi chạy {#AppName}"; Flags: nowait postinstall skipifsilent runascurrentuser

[Registry]
; Đảm bảo luôn chạy với quyền Administrator
Root: HKLM; Subkey: "SOFTWARE\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers"; ValueType: string; ValueName: "{app}\{#AppExeName}"; ValueData: "~ RUNASADMIN"; Flags: uninsdeletevalue

[Code]
procedure InitializeWizard();
begin
  WizardForm.Color := $2E1A1A;
  WizardForm.Font.Color := $E0E0E0;
  WizardForm.Font.Name := 'Segoe UI';
  WizardForm.Font.Size := 10;

  WizardForm.NextButton.Caption := 'Tiếp theo >';
  WizardForm.BackButton.Caption := '< Quay lại';
  WizardForm.CancelButton.Caption := 'Hủy';

  // Màu nền tối cho các panel
  WizardForm.MainPanel.Color := $1A1A2E;
  WizardForm.WelcomePage.Color := $2E1A1A;
  WizardForm.FinishedPage.Color := $2E1A1A;

  // Màu chữ cho các label
  WizardForm.WelcomeLabel1.Font.Color := $E0E0E0;
  WizardForm.WelcomeLabel2.Font.Color := $AAAAAA;
  WizardForm.FinishedHeadingLabel.Font.Color := $E0E0E0;
  WizardForm.FinishedLabel.Font.Color := $AAAAAA;

  // License page — nền trắng full, chữ đen dễ đọc
  WizardForm.InnerPage.Color := $FFFFFF;
  WizardForm.LicensePage.Color := $FFFFFF;
  WizardForm.LicenseLabel1.Font.Color := $1A1A2E;
  WizardForm.LicenseLabel1.Font.Style := [fsBold];
  WizardForm.LicenseMemo.Color := $FFFFFF;
  WizardForm.LicenseMemo.BorderStyle := bsNone;

  // Ready to install page — nội dung màu đen
  WizardForm.ReadyMemo.Font.Color := $000000;

  // Header labels màu trắng (áp dụng ngay từ đầu)
  WizardForm.PageNameLabel.Font.Color := $FFFFFF;
  WizardForm.PageDescriptionLabel.Font.Color := $CCCCCC;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = wpFinished then
    WizardForm.NextButton.Caption := 'Kết thúc'
  else
    WizardForm.NextButton.Caption := 'Tiếp theo >';

  // License page: nền trắng full
  if CurPageID = wpLicense then
    WizardForm.InnerPage.Color := $FFFFFF
  else
    WizardForm.InnerPage.Color := $2E1A1A;

  // Đổi màu tiêu đề trang thành trắng
  WizardForm.PageNameLabel.Font.Color := $FFFFFF;
  WizardForm.PageDescriptionLabel.Font.Color := $CCCCCC;
end;
