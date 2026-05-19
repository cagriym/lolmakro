#define MyAppName "lolsiken"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "xmemo"
#define MyAppExeName "LolMakroBridge.exe"

[Setup]
AppId={{8F7268D1-5F53-4BFD-B24D-2AB7B2E74E7D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
SetupIconFile=assets\app_icon.ico
DefaultDirName={autopf}\LolMakroBridgeInstaller
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\installer
OutputBaseFilename=lolsiken_setup_v10
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
WizardImageBackColor=$B469FF
WizardImageStretch=yes
WizardSmallImageBackColor=$B469FF
BackColor=$00A0FF
BackColor2=$00C0FF

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"

[Files]
Source: "..\dist\LolMakroBridge\*"; DestDir: "{app}\dist\LolMakroBridge"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "install_once.ps1"; DestDir: "{app}\windows"; Flags: ignoreversion
Source: "assets\clip.mp3"; Flags: dontcopy
Source: "assets\app_icon.ico"; Flags: dontcopy
Source: "assets\wizard_photo.jpg"; Flags: dontcopy

[Run]
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -File ""{app}\windows\install_once.ps1"" -SourceDist ""{app}\dist\LolMakroBridge"" -RunNow"; Flags: runhidden nowait postinstall

[Code]
const
  MusicAlias = 'lolsiken_theme';

var
  MusicToggleButton: TButton;
  MusicStatusLabel: TLabel;
  PhotoBox: TBitmapImage;
  MusicPaused: Boolean;
  MusicLoaded: Boolean;
  MusicAttempted: Boolean;

function mciSendString(lpstrCommand: string; lpstrReturnString: string; uReturnLength: Integer; hwndCallback: Integer): Integer;
  external 'mciSendStringW@winmm.dll stdcall';

function Mci(const Command: string): Integer;
begin
  Result := mciSendString(Command, '', 0, 0);
end;

procedure UpdateMusicStatus;
begin
  if not Assigned(MusicStatusLabel) then
    Exit;
  if not MusicAttempted then begin
    MusicStatusLabel.Caption := 'Muzik Durumu: Baslatilmadi';
    Exit;
  end;
  if not MusicLoaded then begin
    MusicStatusLabel.Caption := 'Muzik Durumu: Kullanilamiyor';
    Exit;
  end;
  if MusicPaused then
    MusicStatusLabel.Caption := 'Muzik Durumu: Durduruldu'
  else
    MusicStatusLabel.Caption := 'Muzik Durumu: Caliyor';
end;

procedure CloseMusic;
begin
  if MusicLoaded then begin
    Mci('stop ' + MusicAlias);
    Mci('close ' + MusicAlias);
    MusicLoaded := False;
  end;
end;

procedure ToggleMusicClick(Sender: TObject);
begin
  if not MusicLoaded then begin
    MsgBox('Muzik yuklenemedi. Medya kodegi desteklenmiyor olabilir.', mbInformation, MB_OK);
    Exit;
  end;

  if MusicPaused then begin
    Mci('resume ' + MusicAlias);
    MusicPaused := False;
    MusicToggleButton.Caption := 'Durdur';
  end else begin
    Mci('pause ' + MusicAlias);
    MusicPaused := True;
    MusicToggleButton.Caption := 'Oynat';
  end;
  UpdateMusicStatus;
end;

procedure StartMusic;
var
  MusicPath: string;
  OpenCmd: string;
begin
  if MusicAttempted then
    Exit;
  MusicAttempted := True;

  try
    ExtractTemporaryFile('clip.mp3');
    MusicPath := ExpandConstant('{tmp}\clip.mp3');
    if not FileExists(MusicPath) then begin
      MusicLoaded := False;
      Exit;
    end;

    OpenCmd := 'open "' + MusicPath + '" alias ' + MusicAlias;
    if Mci(OpenCmd) = 0 then begin
      MusicLoaded := True;
      Mci('play ' + MusicAlias + ' repeat');
    end else begin
      MusicLoaded := False;
    end;
  except
    MusicLoaded := False;
  end;
end;

procedure TryLoadWizardPhoto;
var
  PhotoPath: string;
begin
  if not Assigned(PhotoBox) then
    Exit;

  try
    ExtractTemporaryFile('wizard_photo.jpg');
  except
    PhotoBox.Visible := False;
    Exit;
  end;

  PhotoPath := ExpandConstant('{tmp}\wizard_photo.jpg');
  if FileExists(PhotoPath) then begin
    try
      PhotoBox.Bitmap.LoadFromFile(PhotoPath);
      PhotoBox.Visible := True;
    except
      PhotoBox.Visible := False;
    end;
  end else begin
    PhotoBox.Visible := False;
  end;
end;

procedure InitializeWizard;
begin
  WizardForm.Color := $B469FF;
  WizardForm.Caption := 'lolsiken Kurulum Sihirbazi';

  MusicPaused := False;
  MusicAttempted := False;

  PhotoBox := TBitmapImage.Create(WizardForm);
  PhotoBox.Parent := WizardForm;
  PhotoBox.Left := ScaleX(360);
  PhotoBox.Top := ScaleY(68);
  PhotoBox.Width := ScaleX(210);
  PhotoBox.Height := ScaleY(300);
  PhotoBox.Stretch := True;
  PhotoBox.Visible := False;
  TryLoadWizardPhoto;

  MusicToggleButton := TButton.Create(WizardForm);
  MusicToggleButton.Parent := WizardForm.NextButton.Parent;
  MusicToggleButton.Left := ScaleX(12);
  MusicToggleButton.Top := WizardForm.NextButton.Top;
  MusicToggleButton.Width := ScaleX(88);
  MusicToggleButton.Height := WizardForm.NextButton.Height;
  MusicToggleButton.Caption := 'Durdur';
  MusicToggleButton.OnClick := @ToggleMusicClick;
  MusicToggleButton.Visible := True;

  MusicStatusLabel := TLabel.Create(WizardForm);
  MusicStatusLabel.Parent := WizardForm.NextButton.Parent;
  MusicStatusLabel.Left := MusicToggleButton.Left + MusicToggleButton.Width + ScaleX(10);
  MusicStatusLabel.Top := WizardForm.NextButton.Top + ScaleY(6);
  MusicStatusLabel.Width := ScaleX(210);
  MusicStatusLabel.Height := ScaleY(16);
  MusicStatusLabel.Caption := 'Muzik Durumu: Baslatiliyor';
  MusicStatusLabel.Font.Color := clWhite;
  MusicStatusLabel.Transparent := True;
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if not MusicAttempted then begin
    StartMusic;
    if MusicLoaded then begin
      MusicPaused := False;
      MusicToggleButton.Caption := 'Durdur';
    end else begin
      MusicToggleButton.Caption := 'Yok';
    end;
  end;
  UpdateMusicStatus;
end;

procedure DeinitializeSetup;
begin
  CloseMusic;
end;
