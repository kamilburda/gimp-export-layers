#define PLUGIN_TITLE "Export Layers"
#define INSTALLER_NAME PLUGIN_TITLE + " for GIMP"

[Setup]
AppName={#INSTALLER_NAME}
AppVersion={#PLUGIN_VERSION}
AppVerName={#INSTALLER_NAME} {#PLUGIN_VERSION}
DefaultDirName={code:GetPluginsDirpath}
DisableDirPage=Yes
UninstallFilesDir={app}\{#PLUGIN_NAME}
PrivilegesRequired=lowest
Compression=lzma2
DirExistsWarning=no
OutputDir={#OUTPUT_DIRPATH}
OutputBaseFilename={#OUTPUT_FILENAME_PREFIX}

[Files]
Source: {#INPUT_DIRPATH}\*; DestDir: "{app}"; Flags: ignoreversion recursesubdirs

[Code]

const
  GIMP_REG_PATH = 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\GIMP-2_is1';
  MIN_REQUIRED_GIMP_VERSION_MAJOR = 2;
  MIN_REQUIRED_GIMP_VERSION_MINOR = 8;
  MIN_REQUIRED_GIMP_VERSION = '2.8';

type
  TVersionArray = array [0..1] of integer;

var
  PluginsDirpath: string;
  GimpDirpath: string;
  ShouldShowSelectDirsPage: boolean;
  SelectDirsPage: TInputDirWizardPage;
  PluginsDirpathEdit: TEdit;
  GimpDirpathEdit: TEdit;


function GetLocalPluginsDirpath (const gimpVersionMajorMinor: TVersionArray; const gimpVersionMajorMinorStr: string) : string; forward;
function GetGimpVersionMajorMinor (const gimpVersion: string) : TVersionArray; forward;
procedure CreateSelectDirsPage; forward;


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
  
  ShouldShowSelectDirsPage := False;
  
  if not RegQueryStringValue(HKLM64, GIMP_REG_PATH, 'DisplayVersion', gimpVersion) then begin
    if not RegQueryStringValue(HKLM32, GIMP_REG_PATH, 'DisplayVersion', gimpVersion) then begin
      MsgBox(
        'Could not find GIMP installation path. Please specify the path to GIMP and GIMP plug-ins manually.'
        + ' If GIMP is not installed, abort this installation and install GIMP first.',
        mbInformation,
        MB_OK);
      
      ShouldShowSelectDirsPage := True;
      Exit;
    end;
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
      
      ShouldShowSelectDirsPage := True;
      Exit;
  end;
  
  PluginsDirpath := GetLocalPluginsDirpath(gimpVersionMajorMinor, gimpVersionMajorMinorStr);
end;


procedure InitializeWizard;
begin
  if ShouldShowSelectDirsPage then begin
    CreateSelectDirsPage();
  end;
end;


function NextButtonClick(curPageID: integer) : boolean;
begin
  Result := True;
  
  if (SelectDirsPage <> nil) and (curPageID = SelectDirsPage.ID) then begin
    GimpDirpath := GimpDirpathEdit.Text;
    PluginsDirpath := PluginsDirpathEdit.Text;
    
    { `DefaultDirName` may be empty at this point, causing the installer to fail. }
    WizardForm.DirEdit.Text := PluginsDirpath;
  end;
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
  
  lastAddedDirIndex := SelectDirsPage.Add('Path to GIMP plug-ins');
  PluginsDirpathEdit := SelectDirsPage.Edits[lastAddedDirIndex];
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
