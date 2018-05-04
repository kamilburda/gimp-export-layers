#define APP_NAME "Export Layers for GIMP"

[Setup]
AppName={#APP_NAME}
AppVersion={#APP_VERSION}
AppVerName={#APP_NAME} {#APP_VERSION}
DefaultDirName={userdocs}\{#APP_NAME}
DefaultGroupName=GIMP
UninstallFilesDir={app}\{#PLUGIN_NAME}
PrivilegesRequired=lowest
Compression=lzma2
DirExistsWarning=no
OutputDir={#OUTPUT_DIRPATH}
OutputBaseFilename={#OUTPUT_FILENAME_PREFIX}

[Files]
Source: {#INPUT_DIRPATH}\*; DestDir: "{app}"; Flags: ignoreversion recursesubdirs
