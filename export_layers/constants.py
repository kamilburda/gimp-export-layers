#-------------------------------------------------------------------------------
#
# This file is part of Export Layers.
#
# Copyright (C) 2013-2015 khalim19 <khalim19@gmail.com>
#
# Export Layers is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Export Layers is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Export Layers.  If not, see <http://www.gnu.org/licenses/>.
#
#-------------------------------------------------------------------------------

"""
This module defines plug-in constants used in other modules.
"""

#===============================================================================

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division

str = unicode

#=============================================================================== 

import os
import inspect

try:
  import gimp
except ImportError:
  _gimp_module_imported = False
else:
  _gimp_module_imported = True

#===============================================================================

def N_(s):
  return s

#===============================================================================

PLUGIN_PROGRAM_NAME = "export_layers"
PLUGIN_TITLE = N_("Export Layers")

PLUGIN_VERSION = "2.4"

# If False, log only exceptions to an error log file. If True, log all output
# from `stdout` and `stderr` to separate log files.
DEBUG = False
# If True, display each step of image/layer editing in GIMP.
DEBUG_IMAGE_PROCESSING = False

#===============================================================================

_current_module_path = os.path.dirname(inspect.getfile(inspect.currentframe()))

PLUGINS_DIRECTORY = os.path.dirname(_current_module_path)
PLUGIN_DIRNAME = PLUGIN_PROGRAM_NAME
PLUGIN_PATH = os.path.join(PLUGINS_DIRECTORY, PLUGIN_DIRNAME)

SESSION_SOURCE_NAME = "plug_in_" + PLUGIN_PROGRAM_NAME + "_"
PERSISTENT_SOURCE_NAME = "plug_in_" + PLUGIN_PROGRAM_NAME

BUG_REPORT_URI_LIST = [
  ("GIMP Plugin Registry", "http://registry.gimp.org/node/28268"),
  ("GitHub", "https://github.com/khalim19/gimp-plugin-export-layers/issues")
]

DOMAIN_NAME = PLUGIN_PROGRAM_NAME
LOCALE_DIRNAME = "locale"
LOCALE_PATH = os.path.join(PLUGINS_DIRECTORY, PLUGIN_PROGRAM_NAME, LOCALE_DIRNAME)

PLUGINS_LOG_STDOUT_PATH = os.path.join(PLUGIN_PATH, PLUGIN_PROGRAM_NAME + ".log")
PLUGINS_LOG_STDERR_PATH = os.path.join(PLUGIN_PATH, PLUGIN_PROGRAM_NAME + "_error.log")

# These are alternate paths that can be used to log output to the
# `[user directory]/.gimp-2.8/plug-ins` directory in case the plug-in was
# installed system-wide (e.g. in `Program Files` on Windows) and there is no
# permission to create log files there.
PLUGINS_DIRECTORY_ALTERNATE = None
PLUGIN_PATH_ALTERNATE = None
PLUGINS_LOG_STDOUT_PATH_ALTERNATE = None
PLUGINS_LOG_STDERR_PATH_ALTERNATE = None

if _gimp_module_imported:
  PLUGINS_DIRECTORY_ALTERNATE = os.path.join(gimp.directory, "plug-ins")
  if PLUGINS_DIRECTORY_ALTERNATE != PLUGINS_DIRECTORY:
    PLUGIN_PATH_ALTERNATE = os.path.join(PLUGINS_DIRECTORY_ALTERNATE, PLUGIN_DIRNAME)
    PLUGINS_LOG_STDOUT_PATH_ALTERNATE = os.path.join(PLUGIN_PATH_ALTERNATE,
                                                     PLUGIN_PROGRAM_NAME + ".log")
    PLUGINS_LOG_STDERR_PATH_ALTERNATE = os.path.join(PLUGIN_PATH_ALTERNATE,
                                                     PLUGIN_PROGRAM_NAME + "_error.log")
