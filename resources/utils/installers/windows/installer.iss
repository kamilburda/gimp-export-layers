#define PLUGIN_TITLE "Export Layers"
#define INSTALLER_NAME PLUGIN_TITLE + " for GIMP"

[Setup]
AppName={#INSTALLER_NAME}
AppVersion={#PLUGIN_VERSION}
AppVerName={#INSTALLER_NAME} {#PLUGIN_VERSION}
AppPublisher={#AUTHOR_NAME}
DefaultDirName={code:GetPluginsDirpath}
DefaultGroupName=GIMP
DisableProgramGroupPage=Yes
DisableDirPage=Yes
UninstallFilesDir={app}\{#PLUGIN_NAME}
PrivilegesRequired=lowest
DirExistsWarning=no
OutputDir={#OUTPUT_DIRPATH}
OutputBaseFilename={#OUTPUT_FILENAME_PREFIX}
WizardSmallImageFile=logo_wizard.bmp
WizardImageFile=menu_path.bmp
SetupIconFile=icon_installer.ico
UninstallDisplayIcon=logo.ico

[Files]
Source: {#INPUT_DIRPATH}\*; DestDir: "{app}"; Flags: ignoreversion recursesubdirs

[Messages]
ReadyLabel2b=Click Install to continue with the installation of {#PLUGIN_TITLE}, or click Customize to modify the installation.
FinishedLabelNoIcons={#PLUGIN_TITLE} successfully installed. To run the plug-in, start GIMP (or restart if already running) and go to File → Export Layers.

[Code]

const
  GIMP_REG_PATH = 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\GIMP-2_is1';
  GIMP_NOT_FOUND_MESSAGE = (
    'Could not find GIMP installation path.'
    + ' Please specify the path to GIMP and GIMP plug-ins manually.'
    + ' If GIMP is not installed, abort this installation and install GIMP first.');
  PYTHON_NOT_FOUND_IN_GIMP_MESSAGE = (
    'It appears that your GIMP installation does not support Python scripting.'
    + ' Please install GIMP with enabled support for Python scripting before proceeding.');
  MIN_REQUIRED_GIMP_VERSION_MAJOR = 2;
  MIN_REQUIRED_GIMP_VERSION_MINOR = 8;
  MIN_REQUIRED_GIMP_VERSION = '2.8';

type
  TVersionArray = array [0..1] of integer;

var
  PluginsDirpath: string;
  GimpDirpath: string;
  
  SelectDirsPage: TInputDirWizardPage;
  PluginsDirpathEdit: TEdit;
  GimpDirpathEdit: TEdit;
  
  IsGimpDirpathDetected: boolean;
  
  InstallerState: (Initialized, Customizing, ReadyToInstall);
  
  CustomizeButton: TNewButton;


procedure AddCustomizeToInstallPage; forward;
procedure OnCustomizeClicked(sender: TObject); forward;
function GetButtonWidthFitToCaption(caption: string; xSpacing: integer) : integer; forward;
procedure CreateSelectDirsPage; forward;

procedure CheckPythonScriptingEnabled; forward;
function GetLocalPluginsDirpath (const gimpVersionMajorMinor: TVersionArray; const gimpVersionMajorMinorStr: string) : string; forward;
function GetGimpVersionMajorMinor (const gimpVersion: string) : TVersionArray; forward;


function GetPluginsDirpath(value: string) : string;
begin
  Result := PluginsDirpath;
end;


function InitializeSetup() : boolean;
var
  gimpVersion: string;
  gimpVersionMajorMinor: TVersionArray;
  gimpVersionMajorMinorStr: string;
begin
  Result := True;
  
  InstallerState := Initialized;
  IsGimpDirpathDetected := True;
  
  if (not RegQueryStringValue(HKLM64, GIMP_REG_PATH, 'DisplayVersion', gimpVersion)
      and not RegQueryStringValue(HKLM32, GIMP_REG_PATH, 'DisplayVersion', gimpVersion)) then begin
    MsgBox(GIMP_NOT_FOUND_MESSAGE, mbInformation, MB_OK);
    IsGimpDirpathDetected := False;
    Exit;
  end;
  
  gimpVersionMajorMinor := GetGimpVersionMajorMinor(gimpVersion);
  gimpVersionMajorMinorStr := IntToStr(gimpVersionMajorMinor[0]) + '.' + IntToStr(gimpVersionMajorMinor[1]);
  
  if (gimpVersionMajorMinor[0] <= MIN_REQUIRED_GIMP_VERSION_MAJOR) and (gimpVersionMajorMinor[1] < MIN_REQUIRED_GIMP_VERSION_MINOR) then begin
    MsgBox(
      'GIMP version ' + gimpVersionMajorMinorStr + ' detected.'
      + ' To use {#PLUGIN_TITLE}, install GIMP ' + MIN_REQUIRED_GIMP_VERSION + ' or later.'
      + ' If you do have GIMP ' + MIN_REQUIRED_GIMP_VERSION + ' or later installed, '
      + 'specify the path to GIMP and GIMP plug-ins manually.'
      + ' Otherwise, abort this installation and install GIMP with a sufficient version first.',
      mbInformation,
      MB_OK);
      
      IsGimpDirpathDetected := False;
      Exit;
  end;
  
  PluginsDirpath := GetLocalPluginsDirpath(gimpVersionMajorMinor, gimpVersionMajorMinorStr);
  
  if (not RegQueryStringValue(HKLM64, GIMP_REG_PATH, 'InstallLocation', GimpDirpath)
      and not RegQueryStringValue(HKLM32, GIMP_REG_PATH, 'InstallLocation', GimpDirpath)) then begin
    MsgBox(GIMP_NOT_FOUND_MESSAGE, mbInformation, MB_OK);
    IsGimpDirpathDetected := False;
    Exit;
  end;
  
  CheckPythonScriptingEnabled();
end;


procedure InitializeWizard;
begin
  WizardForm.BackButton.visible := False;
  
  AddCustomizeToInstallPage();
  
  CreateSelectDirsPage();
end;


function NextButtonClick(curPageID: integer) : boolean;
begin
  Result := True;
  
  if curPageID = SelectDirsPage.ID then begin
    GimpDirpath := GimpDirpathEdit.Text;
    PluginsDirpath := PluginsDirpathEdit.Text;
    
    // `DefaultDirName` may be empty at this point, causing the installer to fail.
    WizardForm.DirEdit.Text := PluginsDirpath;
    
    CheckPythonScriptingEnabled();
  end;
end;


function BackButtonClick(curPageID: integer) : boolean;
begin
  Result := True;
  
  if curPageID = wpReady then
    InstallerState := Customizing;
end;


function ShouldSkipPage(pageID: Integer): Boolean;
begin
  Result := False;
  
  if (pageID <> wpReady) and IsGimpDirpathDetected and (InstallerState = Initialized) then
    Result := True
end;


procedure CurPageChanged(curPageID: Integer);
begin
  WizardForm.BackButton.visible := False;
  CustomizeButton.visible := curPageID = wpReady;
  
  if curPageID = wpReady then
    InstallerState := ReadyToInstall;
end;


procedure AddCustomizeToInstallPage;
begin
  CustomizeButton := TNewButton.Create(WizardForm);
  
  with CustomizeButton do begin
    Caption := 'Customize';
    Parent := WizardForm;
    Width := GetButtonWidthFitToCaption(Caption, 12);
    Height := WizardForm.NextButton.Height;
    Left := WizardForm.ClientWidth - (WizardForm.CancelButton.Left + WizardForm.CancelButton.Width);
    Top := WizardForm.NextButton.Top;
    
    OnClick := @OnCustomizeClicked;
  end;
end;


procedure OnCustomizeClicked(sender: TObject);
begin
  WizardForm.BackButton.OnClick(TNewButton(sender).Parent);
end;


function GetButtonWidthFitToCaption(caption: string; xSpacing: integer) : integer;
var
  dummyLabel: TNewStaticText;
  defaultWidth: integer;
begin
  dummyLabel := TNewStaticText.Create(WizardForm);
  
  dummyLabel.Autosize := True;
  dummyLabel.Caption := caption;
  
  defaultWidth := WizardForm.NextButton.Width;
  
  if defaultWidth >= dummyLabel.Width + ScaleX(xSpacing) then
    Result := defaultWidth
  else
    Result := dummyLabel.Width + ScaleX(xSpacing);
  
  dummyLabel.Free;
end;


procedure CreateSelectDirsPage;
var
  lastAddedDirIndex: integer;
begin
  SelectDirsPage := CreateInputDirPage(
    wpWelcome,
    'Select Location for GIMP and GIMP Plug-ins',
    '',
    'Specify the directory path to a working GIMP installation and the path to GIMP plug-ins (for the current user or system-wide).',
    False,
    'New Folder');
  
  lastAddedDirIndex := SelectDirsPage.Add('Path to GIMP installation');
  GimpDirpathEdit := SelectDirsPage.Edits[lastAddedDirIndex];
  SelectDirsPage.Values[0] := GimpDirpath;
  
  lastAddedDirIndex := SelectDirsPage.Add('Path to GIMP plug-ins');
  PluginsDirpathEdit := SelectDirsPage.Edits[lastAddedDirIndex];
  SelectDirsPage.Values[1] := PluginsDirpath;
end;


procedure CheckPythonScriptingEnabled;
begin
  if not DirExists(GimpDirpath + '\Python') then begin
    MsgBox(PYTHON_NOT_FOUND_IN_GIMP_MESSAGE, mbInformation, MB_OK);
    Abort();
  end;
end;


function GetLocalPluginsDirpath (const gimpVersionMajorMinor: TVersionArray; const gimpVersionMajorMinorStr: string) : string;
begin
  if (gimpVersionMajorMinor[0] <= 2) and (gimpVersionMajorMinor[1] < 9) then
    Result := ExpandConstant('{%USERPROFILE}') + '\.gimp-' + gimpVersionMajorMinorStr + '\plug-ins'
  else
    Result := ExpandConstant('{userappdata}') + '\GIMP\' + gimpVersionMajorMinorStr + '\plug-ins';
end;


function GetGimpVersionMajorMinor (const gimpVersion: string) : TVersionArray;
var
  versionNumberMajorMinor: TVersionArray;
  i: integer;
  versionNumberFields: array of integer;
  versionNumberFieldCurrentArrayIndex: integer;
  versionNumberFieldStartIndex: integer;
begin
  versionNumberFieldCurrentArrayIndex := 0;
  versionNumberFieldStartIndex := 1;
  
  for i := 1 to Length(gimpVersion) do begin
    if gimpVersion[i] = '.' then begin
      SetArrayLength(versionNumberFields, GetArrayLength(versionNumberFields) + 1);
      versionNumberFields[versionNumberFieldCurrentArrayIndex] := (
        StrToIntDef(
          Copy(
            gimpVersion, versionNumberFieldStartIndex, i - versionNumberFieldStartIndex), -1));
      versionNumberFieldCurrentArrayIndex := versionNumberFieldCurrentArrayIndex + 1;
      versionNumberFieldStartIndex := i + 1;
    end;
  end;
  
  if versionNumberFieldStartIndex <= Length(gimpVersion) then begin
    SetArrayLength(versionNumberFields, GetArrayLength(versionNumberFields) + 1);
    versionNumberFields[versionNumberFieldCurrentArrayIndex] := (
      StrToIntDef(
        Copy(
          gimpVersion, versionNumberFieldStartIndex, Length(gimpVersion) + 1 - versionNumberFieldStartIndex), -1));
  end;
  
  versionNumberMajorMinor[0] := versionNumberFields[0];
  versionNumberMajorMinor[1] := versionNumberFields[1];
  
  Result := versionNumberMajorMinor;
end;
