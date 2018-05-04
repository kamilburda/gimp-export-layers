#!/bin/bash

function error_usage()
{
  usage='Usage: make_package [options...]

Options:
  -d, --dest-dir [DIRECTORY] - destination directory of the created package
  -f, --force - make package even if the repository contains local changes
  -i, --installers [INSTALLERS] - comma-separated list of installers to create
    - possible values for installers: "windows", "manual", "all"
    - default: "all" (creates all installers)
    - example: -i "windows,manual" creates a Windows installer and a ZIP package for manual install
    - unrecognized installers are silently ignored
  -h, --help - display this help and exit'
  
  if [ -z "$1" ]; then
    printf '%s\n' "${1:-$usage}"
  else
    printf 'Error: %s\n\n%s\n' "$1" "${2:-$usage}"
  fi
  
  exit 1
} 1>&2


destination_dirpath='None'
force_if_dirty='False'
installers='all'


while [[ "${1:0:1}" = "-" && "$1" != "--" ]]; do
  case "$1" in
  -d | --dest-dir ) shift; destination_dirpath='r"'"$1"'"';;
  -f | --force ) force_if_dirty='True';;
  -i | --installers ) shift; installers="$1";;
  -h | --help ) error_usage;;
  * ) [[ "$1" ]] && error_usage "unknown argument: $1";;
  esac

  shift
done

[[ "$1" = "--" ]] && shift


gimp -i --batch-interpreter="python-fu-eval" -b '
import sys
import os

plugin_dirpath = os.path.join(gimp.directory, "plug-ins - Export Layers")
resources_dirpath = os.path.join(plugin_dirpath, "resources")
utils_dirpath = os.path.join(resources_dirpath, "utils")

sys.path.append(plugin_dirpath)
sys.path.append(os.path.join(plugin_dirpath, "export_layers"))
sys.path.append(os.path.join(plugin_dirpath, "export_layers", "pygimplib"))
sys.path.append(resources_dirpath)
sys.path.append(utils_dirpath)

import make_package

os.chdir(resources_dirpath)

make_package.main(destination_dirpath='"$destination_dirpath"', force_if_dirty='"$force_if_dirty"', installers='"$installers"')

pdb.gimp_quit(0)
'
