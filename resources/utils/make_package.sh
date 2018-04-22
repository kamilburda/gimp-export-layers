#!/bin/bash

function error_usage()
{
  usage='Usage: make_package [options...]

Options:
  -f, --force - make package even if the repository contains local changes
  -d, --dest-dir - destination directory of the created package
  -h, --help - display this help and exit'
  
  if [ -z "$1" ]; then
    printf '%s\n' "${1:-$usage}"
  else
    printf 'Error: %s\n\n%s\n' "$1" "${2:-$usage}"
  fi
  
  exit 1
} 1>&2

force_if_dirty='False'
destination_dirpath='None'

while [[ "${1:0:1}" = "-" && "$1" != "--" ]]; do
  case "$1" in
  -f | --force ) force_if_dirty='True';;
  -d | --dest-dir ) shift; destination_dirpath='r"'"$1"'"';;
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

make_package.main(destination_dirpath='"$destination_dirpath"', force_if_dirty='"$force_if_dirty"')

pdb.gimp_quit(0)
'
