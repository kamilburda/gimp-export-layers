; To successfully compile the installer, run `compile_installer.bat` instead
; with specified parameters.
;
; Code dealing with re-running installer with elevated privileges taken from:
; https://stackoverflow.com/a/35435534
;
; Custom parameters for installer:
; pluginpath - plug-in installation directory

#define PLUGIN_TITLE "Export Layers"
#define INSTALLER_NAME PLUGIN_TITLE + " for GIMP"

[Setup]
AppName={#INSTALLER_NAME}
AppVersion={#PLUGIN_VERSION}
AppVerName={#INSTALLER_NAME} {#PLUGIN_VERSION}
AppPublisher={#AUTHOR_NAME}
VersionInfoVersion={#PLUGIN_VERSION}
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

[UninstallDelete]
Type: filesandordirs; Name: "{app}\{#PLUGIN_NAME}"

[Code]

#ifdef UNICODE
  #define AW "W"
#else
  #define AW "A"
#endif


const
  GIMP_REG_PATH = 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\GIMP-2_is1';
  GIMP_NOT_FOUND_MESSAGE = (
    'Could not find GIMP installation path.'
    + ' Please specify the path to GIMP and GIMP plug-ins manually.'
    + ' If GIMP is not installed, abort this installation and install GIMP first.');
  PYTHON_NOT_FOUND_IN_GIMP_MESSAGE = (
    'It appears that your GIMP installation does not support Python scripting.'
    + ' Please install GIMP with enabled support for Python scripting before proceeding.');
  NO_WRITE_PERMISSION_MESSAGE_PROMPT = (
    'It appears that you do not have permissions to install to directory "%s". '
    + 'Would you like to re-run the installer with administrator privileges?'
  );
  NO_WRITE_PERMISSION_MESSAGE = (
    'It appears that you do not have permissions to install to directory "%s". '
    + 'Please select a different directory.'
  );
  FAILED_TO_RUN_ELEVATED = (
    'Failed to run with administrator privileges. '
    + 'Try again or install to a directory with write permissions.'
  );
  
  PLUGIN_PATH_PARAM_NAME = 'pluginpath';
  
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

function HasElevatedPrivileges : Boolean; forward;
function HasWritePermission(const dirpath: String) : Boolean; forward;
function CheckWritePermission(const dirpath: String; out shouldElevate: Boolean) : Boolean; forward;
function CreateDirRecursive(const dirpath: String; out nonexistentDirpaths: array of String) : Boolean; forward;
function RemoveDirs(const dirpaths: array of String) : Boolean; forward;
function RunWithElevatedPrivileges : Boolean; forward;

procedure ExitProcess(uExitCode: UINT); external 'ExitProcess@kernel32.dll stdcall';
function ShellExecute(hwnd: HWND; lpOperation, lpFile, lpParameters, lpDirectory: String; nShowCmd: Integer) : THandle; external 'ShellExecute{#AW}@shell32.dll stdcall';


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
  
  IsGimpDetected := (
    RegQueryStringValue(HKLM64, GIMP_REG_PATH, 'DisplayVersion', gimpVersion)
    or RegQueryStringValue(HKLM32, GIMP_REG_PATH, 'DisplayVersion', gimpVersion));
  
  if not IsGimpDetected then begin
    MsgBox(GIMP_NOT_FOUND_MESSAGE, mbInformation, MB_OK);
    Exit;
  end;
  
  GimpVersionMajorMinor := GetGimpVersionMajorMinor(gimpVersion);
  
  if ((GimpVersionMajorMinor[0] <= MIN_REQUIRED_GIMP_VERSION_MAJOR)
      and (GimpVersionMajorMinor[1] < MIN_REQUIRED_GIMP_VERSION_MINOR)) then begin
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
  
  PluginsDirpath := ExpandConstant(
    '{param:' + PLUGIN_PATH_PARAM_NAME + '|' + GetLocalPluginsDirpath(GimpVersionMajorMinor) + '}');
  
  IsGimpDetected := (
    RegQueryStringValue(HKLM64, GIMP_REG_PATH, 'InstallLocation', GimpDirpath)
    or RegQueryStringValue(HKLM32, GIMP_REG_PATH, 'InstallLocation', GimpDirpath));
  
  if not IsGimpDetected then begin
    MsgBox(GIMP_NOT_FOUND_MESSAGE, mbInformation, MB_OK);
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
var
  shouldElevate: Boolean;
begin
  Result := True;
  shouldElevate := False;
  
  if curPageID = CustomPathsPage.ID then begin
    GimpDirpath := GimpDirpathEdit.Text;
    PluginsDirpath := PluginsDirpathEdit.Text;
    
    CheckPythonScriptingEnabled();
    Result := CheckWritePermission(PluginsDirpath, shouldElevate);
  end
  else if curPageID = SelectPluginInstallPathPage.ID then begin
    if SelectPluginInstallPathPage.values[0] then begin
      PluginsDirpath := GetLocalPluginsDirpath(GimpVersionMajorMinor);
      Result := CheckWritePermission(PluginsDirpath, shouldElevate);
    end
    else if SelectPluginInstallPathPage.values[1] then begin
      PluginsDirpath := GetSystemPluginsDirpath(GimpVersionMajorMinor);
      Result := CheckWritePermission(PluginsDirpath, shouldElevate);
    end;
    
    PluginsDirpathEdit.Text := PluginsDirpath;
  end;
  
  if shouldElevate then begin
    RunWithElevatedPrivileges();
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
  SelectPluginInstallPathPage.Add('Install for all users');
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
      Inc(versionNumberFieldCurrentArrayIndex);
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


function HasElevatedPrivileges : Boolean;
begin
  Result := IsAdminLoggedOn or IsPowerUserLoggedOn;
end;


function HasWritePermission(const dirpath: String) : Boolean;
var
  tempFilepath: String;
  directoryCreated: Boolean;
  nonexistentDirpaths: array of String;
begin
  repeat
    tempFilepath := dirpath + '\' + 'temp_' + IntToStr(Random(MAXINT));
  until not FileExists(tempFilepath);
  
  if not DirExists(dirpath) then begin
    directoryCreated := CreateDirRecursive(dirpath, nonexistentDirpaths);
  end
  else begin
    directoryCreated := False;
  end;
  
  Result := SaveStringToFile(tempFilepath, 'test', False);
  
  if Result then begin
    DeleteFile(tempFilepath);
  end;
  
  if directoryCreated then begin
    RemoveDirs(nonexistentDirpaths);
  end;
end;


function CheckWritePermission(const dirpath: String; out shouldElevate: Boolean) : Boolean;
var
  noWritePermissionPromptResult: Integer;
begin
  Result := HasWritePermission(dirpath);
  shouldElevate := False;
  
  if not Result then begin
    if not HasElevatedPrivileges() then begin
      noWritePermissionPromptResult := MsgBox(
        Format(NO_WRITE_PERMISSION_MESSAGE_PROMPT, [dirpath]), mbConfirmation, MB_YESNO);
      shouldElevate := noWritePermissionPromptResult = IDYES;
    end
    else begin
      MsgBox(
        Format(NO_WRITE_PERMISSION_MESSAGE, [dirpath]), mbInformation, MB_OK);
    end;
  end;
end;


function CreateDirRecursive(const dirpath: String; out nonexistentDirpaths: array of String) : Boolean;
var
  currentDirectory: String;
  nonexistentDirpathsIndex: Integer;
begin
  nonexistentDirpathsIndex := 0;
  currentDirectory := dirpath;
  
  while not DirExists(currentDirectory) do begin
    SetArrayLength(nonexistentDirpaths, GetArrayLength(nonexistentDirpaths) + 1);
    nonexistentDirpaths[nonexistentDirpathsIndex] := currentDirectory;
    currentDirectory := ExtractFileDir(currentDirectory);
    Inc(nonexistentDirpathsIndex);
  end;
  
  Result := True;
  
  for nonexistentDirpathsIndex := GetArrayLength(nonexistentDirpaths) - 1 downto 0 do begin
    Result := Result and CreateDir(nonexistentDirpaths[nonexistentDirpathsIndex]);
  end;
end;


function RemoveDirs(const dirpaths: array of String) : Boolean;
var
  dirpathsIndex: Integer;
begin
  Result := True;
  
  for dirpathsIndex := 0 to GetArrayLength(dirpaths) - 1 do begin
    Result := Result and RemoveDir(dirpaths[dirpathsIndex]);
  end;
end;


function RunWithElevatedPrivileges : Boolean;
var
  shellExecuteRetVal: Integer;
  params: String;
  paramIndex: Integer;
begin
  for paramIndex := 1 to ParamCount do begin
    params := params + AddQuotes(ParamStr(paramIndex)) + ' ';
  end;
  
  params := params + AddQuotes('/LANG=' + ActiveLanguage) + ' ';
  params := params + AddQuotes('/' + PLUGIN_PATH_PARAM_NAME + '=' + PluginsDirpath);
  
  shellExecuteRetVal := ShellExecute(0, 'runas', ExpandConstant('{srcexe}'), params, '', SW_SHOW);
  
  Result := shellExecuteRetVal > 32;
  
  if Result then begin
    ExitProcess(0);
  end
  else begin
    MsgBox(FAILED_TO_RUN_ELEVATED, mbInformation, MB_OK);
  end;
end;
