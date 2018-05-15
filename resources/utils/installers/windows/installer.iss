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
Source: logo_wizard.bmp; Flags: dontcopy
Source: menu_path.bmp; Flags: dontcopy
Source: icon_installer.ico; Flags: dontcopy
Source: logo.ico; Flags: dontcopy

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
  
  NUM_CUSTOM_PAGES = 2;

type
  TVersionArray = array [0..1] of Integer;

var
  PluginsDirpath: String;
  GimpDirpath: String;
  GimpVersionMajorMinor: TVersionArray;
  
  CustomPathsPage: TInputDirWizardPage;
  PluginsDirpathEdit: TEdit;
  GimpDirpathEdit: TEdit;
  
  SelectPluginInstallPathPage: TInputOptionWizardPage;
  
  IsGimpDetected: Boolean;
  InstallerState: (Initialized, ReadyToInstall);
  
  CustomizeButton: TNewButton;


procedure AddCustomizeToInstallPage; forward;
procedure OnCustomizeClicked(sender: TObject); forward;
function GetButtonWidthFitToCaption(const caption: String; const xSpacing: Integer) : Integer; forward;

procedure CreateSelectPluginInstallPathPage(const afterID: Integer); forward;
procedure CreateCustomPathsPage(const afterID: Integer); forward;

function ShouldSpecifyCustomPluginsDirpath : Boolean; forward;
procedure CheckPythonScriptingEnabled; forward;

function GetLocalPluginsDirpath(const gimpVersionMajorMinor: TVersionArray) : String; forward;
function GetSystemPluginsDirpath(const gimpVersionMajorMinor: TVersionArray) : String; forward;
function GetGimpVersionMajorMinor(const gimpVersion: String) : TVersionArray; forward;
function GetGimpVersionStr(const gimpVersionArray: array of Integer) : String; forward;


function GetPluginsDirpath(value: String) : String;
begin
  Result := PluginsDirpath;
end;


function InitializeSetup() : Boolean;
var
  gimpVersion: String;
begin
  Result := True;
  
  InstallerState := Initialized;
  IsGimpDetected := True;
  
  if (not RegQueryStringValue(HKLM64, GIMP_REG_PATH, 'DisplayVersion', gimpVersion)
      and not RegQueryStringValue(HKLM32, GIMP_REG_PATH, 'DisplayVersion', gimpVersion)) then begin
    MsgBox(GIMP_NOT_FOUND_MESSAGE, mbInformation, MB_OK);
    IsGimpDetected := False;
    Exit;
  end;
  
  GimpVersionMajorMinor := GetGimpVersionMajorMinor(gimpVersion);
  
  if (GimpVersionMajorMinor[0] <= MIN_REQUIRED_GIMP_VERSION_MAJOR) and (GimpVersionMajorMinor[1] < MIN_REQUIRED_GIMP_VERSION_MINOR) then begin
    MsgBox(
      'GIMP version ' + GetGimpVersionStr(GimpVersionMajorMinor) + ' detected.'
      + ' To use {#PLUGIN_TITLE}, install GIMP ' + MIN_REQUIRED_GIMP_VERSION + ' or later.'
      + ' If you do have GIMP ' + MIN_REQUIRED_GIMP_VERSION + ' or later installed, '
      + 'specify the path to GIMP and GIMP plug-ins manually.'
      + ' Otherwise, abort this installation and install GIMP with a sufficient version first.',
      mbInformation,
      MB_OK);
      
      IsGimpDetected := False;
      Exit;
  end;
  
  PluginsDirpath := GetLocalPluginsDirpath(GimpVersionMajorMinor);
  
  if (not RegQueryStringValue(HKLM64, GIMP_REG_PATH, 'InstallLocation', GimpDirpath)
      and not RegQueryStringValue(HKLM32, GIMP_REG_PATH, 'InstallLocation', GimpDirpath)) then begin
    MsgBox(GIMP_NOT_FOUND_MESSAGE, mbInformation, MB_OK);
    IsGimpDetected := False;
    Exit;
  end
  else begin
    if GimpDirpath[Length(GimpDirpath)] = '\' then begin
      GimpDirpath := Copy(GimpDirpath, 1, Length(GimpDirpath) - 1);
    end;
  end;
  
  CheckPythonScriptingEnabled();
end;


procedure InitializeWizard;
begin
  AddCustomizeToInstallPage();
  
  CreateSelectPluginInstallPathPage(wpWelcome);
  CreateCustomPathsPage(SelectPluginInstallPathPage.ID);
end;


function NextButtonClick(curPageID: Integer) : Boolean;
begin
  Result := True;
  
  if curPageID = CustomPathsPage.ID then begin
    GimpDirpath := GimpDirpathEdit.Text;
    PluginsDirpath := PluginsDirpathEdit.Text;
    
    CheckPythonScriptingEnabled();
  end
  else if curPageID = SelectPluginInstallPathPage.ID then begin
    if SelectPluginInstallPathPage.values[0] then begin
      PluginsDirpath := GetLocalPluginsDirpath(GimpVersionMajorMinor);
    end
    else if SelectPluginInstallPathPage.values[1] then begin
      PluginsDirpath := GetSystemPluginsDirpath(GimpVersionMajorMinor);
    end;
    
    PluginsDirpathEdit.Text := PluginsDirpath;
  end;
end;


function ShouldSkipPage(pageID: Integer) : Boolean;
var
  isInstallerStarted: Boolean;
  isInstallerStartedWithGimpNotDetected: Boolean;
  shouldSkipCustomPathsPage: Boolean;
begin
  isInstallerStarted := (
    (pageID <> wpReady)
    and (InstallerState = Initialized)
    and IsGimpDetected);
  
  isInstallerStartedWithGimpNotDetected := (
    (pageID = SelectPluginInstallPathPage.ID)
    and (InstallerState = Initialized)
    and not IsGimpDetected);
  
  shouldSkipCustomPathsPage := (
    (pageID = CustomPathsPage.ID)
    and (InstallerState <> Initialized)
    and not ShouldSpecifyCustomPluginsDirpath());
  
  Result := (
    isInstallerStarted
    or isInstallerStartedWithGimpNotDetected
    or shouldSkipCustomPathsPage);
end;


procedure CurPageChanged(curPageID: Integer);
begin
  CustomizeButton.visible := (curPageID = wpReady) and IsGimpDetected;
  
  if (curPageID = CustomPathsPage.ID) and not IsGimpDetected then begin
    WizardForm.BackButton.visible := False;
  end;
  
  if curPageID = wpReady then begin
    InstallerState := ReadyToInstall;
    
    // Assign correct value to `DefaultDirName` (it may be empty or incorrect at this point).
    WizardForm.DirEdit.Text := PluginsDirpath;
  end;
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
var
  i: Integer;
begin
  for i := 0 to NUM_CUSTOM_PAGES - 1 do begin
    WizardForm.BackButton.OnClick(TNewButton(sender).Parent);
  end;
end;


function GetButtonWidthFitToCaption(const caption: String; const xSpacing: Integer) : Integer;
var
  dummyLabel: TNewStaticText;
  defaultWidth: Integer;
begin
  dummyLabel := TNewStaticText.Create(WizardForm);
  
  dummyLabel.Autosize := True;
  dummyLabel.Caption := caption;
  
  defaultWidth := WizardForm.NextButton.Width;
  
  if defaultWidth >= dummyLabel.Width + ScaleX(xSpacing) then begin
    Result := defaultWidth;
  end
  else begin
    Result := dummyLabel.Width + ScaleX(xSpacing);
  end;
  
  dummyLabel.Free;
end;


procedure CreateSelectPluginInstallPathPage(const afterID: Integer);
begin
  SelectPluginInstallPathPage := CreateInputOptionPage(
    afterID,
    'Select Installation Path',
    'Where should {#PLUGIN_TITLE} be installed?',
    'Select one of the options below:',
    True,
    False
  );
  
  SelectPluginInstallPathPage.Add('Install for just me');
  SelectPluginInstallPathPage.Add(
    'Install for all users (requires administrator privileges)');
  SelectPluginInstallPathPage.Add('Choose custom installation path');
  
  SelectPluginInstallPathPage.Values[0] := True;
end;


procedure CreateCustomPathsPage(const afterID: Integer);
var
  lastAddedDirIndex: Integer;
begin
  CustomPathsPage := CreateInputDirPage(
    afterID,
    'Select Location for GIMP and GIMP Plug-ins',
    'Where is GIMP located and where should {#PLUGIN_TITLE} be installed?',
    'Specify custom directory path to a working GIMP installation and to GIMP plug-ins.',
    False,
    'New Folder');
  
  lastAddedDirIndex := CustomPathsPage.Add('Path to GIMP installation');
  GimpDirpathEdit := CustomPathsPage.Edits[lastAddedDirIndex];
  CustomPathsPage.Values[0] := GimpDirpath;
  
  lastAddedDirIndex := CustomPathsPage.Add('Path to GIMP plug-ins');
  PluginsDirpathEdit := CustomPathsPage.Edits[lastAddedDirIndex];
  CustomPathsPage.Values[1] := PluginsDirpath;
end;


function ShouldSpecifyCustomPluginsDirpath : Boolean;
begin
  Result := SelectPluginInstallPathPage.values[2];
end;


procedure CheckPythonScriptingEnabled;
var
  possiblePythonDirpaths: TStringList;
  i: Integer;
  pythonPathFound: Boolean;
begin
  pythonPathFound := False;
  
  possiblePythonDirpaths := TStringList.Create;
  possiblePythonDirpaths.Add(GimpDirpath + '\Python');
  possiblePythonDirpaths.Add(GimpDirpath + '\32\lib\python2.7');
  possiblePythonDirpaths.Add(GimpDirpath + '\lib\python2.7');
  
  for i := 0 to possiblePythonDirpaths.Count - 1 do begin
    if DirExists(possiblePythonDirpaths[i]) then begin
      pythonPathFound := True;
      break;
    end;
  end;
  
  possiblePythonDirpaths.Free;
  
  if not pythonPathFound then begin
    MsgBox(PYTHON_NOT_FOUND_IN_GIMP_MESSAGE, mbInformation, MB_OK);
    Abort();
  end;
end;


function GetLocalPluginsDirpath(const gimpVersionMajorMinor: TVersionArray) : String;
var
  gimpVersionMajorMinorStr: String;
begin
  gimpVersionMajorMinorStr := GetGimpVersionStr(gimpVersionMajorMinor);
  
  if (gimpVersionMajorMinor[0] <= 2) and (gimpVersionMajorMinor[1] < 9) then begin
    Result := ExpandConstant('{%USERPROFILE}') + '\.gimp-' + gimpVersionMajorMinorStr + '\plug-ins';
  end
  else begin
    Result := ExpandConstant('{userappdata}') + '\GIMP\' + gimpVersionMajorMinorStr + '\plug-ins';
  end;
end;


function GetSystemPluginsDirpath(const gimpVersionMajorMinor: TVersionArray) : String;
begin
  Result := GimpDirpath + '\lib\gimp\' + IntToStr(gimpVersionMajorMinor[0]) + '.0\plug-ins';
end;


function GetGimpVersionMajorMinor(const gimpVersion: String) : TVersionArray;
var
  versionNumberMajorMinor: TVersionArray;
  i: Integer;
  versionNumberFields: array of Integer;
  versionNumberFieldCurrentArrayIndex: Integer;
  versionNumberFieldStartIndex: Integer;
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


function GetGimpVersionStr(const gimpVersionArray: array of Integer) : String;
var
  i: Integer;
  gimpVersionStr: String;
begin
  gimpVersionStr := '';
  
  for i := 0 to Length(gimpVersionArray) - 1 do begin
    gimpVersionStr := gimpVersionStr + IntToStr(gimpVersionArray[i]) + '.';
  end;
  
  Result := Copy(gimpVersionStr, 1, Length(gimpVersionStr) - 1);
end;
