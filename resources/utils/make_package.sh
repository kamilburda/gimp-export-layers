#!/bin/bash

if [ -z "$1" ]; then
  dest_dirpath='None'
else
  dest_dirpath='r"'"$1"'"'
fi

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

make_package.main('"$dest_dirpath"')

pdb.gimp_quit(0)
'
