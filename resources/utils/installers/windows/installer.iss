#define INSTALLER_NAME "Export Layers for GIMP"

[Setup]
AppName={#INSTALLER_NAME}
AppVersion={#PLUGIN_VERSION}
AppVerName={#INSTALLER_NAME} {#PLUGIN_VERSION}
DefaultDirName={userdocs}\{#INSTALLER_NAME}
DefaultGroupName=GIMP
UninstallFilesDir={app}\{#PLUGIN_NAME}
PrivilegesRequired=lowest
Compression=lzma2
DirExistsWarning=no
OutputDir={#OUTPUT_DIRPATH}
OutputBaseFilename={#OUTPUT_FILENAME_PREFIX}

[Files]
Source: {#INPUT_DIRPATH}\*; DestDir: "{app}"; Flags: ignoreversion recursesubdirs
