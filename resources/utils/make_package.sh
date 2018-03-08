#!/bin/bash

gimp -i --batch-interpreter="python-fu-eval" -b '
import sys
import os

plugin_dirpath = os.path.join(gimp.directory, "plug-ins - Export Layers")
resources_dirpath = os.path.join(plugin_dirpath, "resources")
utils_dirpath = os.path.join(resources_dirpath, "utils")

sys.path.append(plugin_dirpath)
sys.path.append(os.path.join(plugin_dirpath, "export_layers"))
sys.path.append(os.path.join(plugin_dirpath, "pygimplib"))
sys.path.append(resources_dirpath)
sys.path.append(utils_dirpath)

import make_package

os.chdir(resources_dirpath)

make_package.main()

pdb.gimp_quit(0)
'
