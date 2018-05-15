@echo off

for /F "tokens=5,* skip=2" %%G in ('REG QUERY "HKLM\Software\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup 5_is1" /reg:32 /v "Inno Setup: App Path"') do set INNO_SETUP_COMPILER_FILEPATH=%%H\ISCC.exe

if not exist "%INNO_SETUP_COMPILER_FILEPATH%" (
  for /F "tokens=5,* skip=2" %%G in ('REG QUERY "HKLM\Software\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup 5_is1" /reg:64 /v "Inno Setup: App Path"') do set INNO_SETUP_COMPILER_FILEPATH_64=%%H\ISCC.exe
  
  if exist "%INNO_SETUP_COMPILER_FILEPATH_64%" (
    set INNO_SETUP_COMPILER_FILEPATH="%INNO_SETUP_COMPILER_FILEPATH_64%"
  ) else (
    goto innoSetupNotFound
  )
)

if [%1] == [] goto usage
if [%2] == [] goto usage
if [%3] == [] goto usage
if [%4] == [] goto usage
if [%5] == [] goto usage
if [%6] == [] goto usage
if [%7] == [] goto usage

set PLUGIN_NAME=%1
set PLUGIN_VERSION=%2
set AUTHOR_NAME=%3
set INPUT_DIRPATH=%4
set OUTPUT_DIRPATH=%5
set OUTPUT_FILENAME_PREFIX=%6
set INSTALLER_SCRIPT_FILENAME=%7

"%INNO_SETUP_COMPILER_FILEPATH%" /DPLUGIN_NAME="%PLUGIN_NAME%" /DPLUGIN_VERSION="%PLUGIN_VERSION%" /DAUTHOR_NAME="%AUTHOR_NAME%" /DINPUT_DIRPATH="%INPUT_DIRPATH%" /DOUTPUT_DIRPATH="%OUTPUT_DIRPATH%" /DOUTPUT_FILENAME_PREFIX="%OUTPUT_FILENAME_PREFIX%" "%INSTALLER_SCRIPT_FILENAME%"

goto :EOF

:innoSetupNotFound
echo Inno Setup installation path not found in the registry.
goto :EOF

:usage
echo Usage: %~n0%~x0 PLUGIN_NAME PLUGIN_VERSION AUTHOR_NAME INPUT_DIRPATH OUTPUT_DIRPATH OUTPUT_FILENAME_PREFIX INSTALLER_SCRIPT_FILENAME
echo Example: %~n0%~x0 export_layers 3.2 input_files output export_layers-3.2-windows installer.iss
