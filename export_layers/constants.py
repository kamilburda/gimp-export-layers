#-------------------------------------------------------------------------------
#
# This file is part of Export Layers.
#
# Copyright (C) 2013, 2014 khalim19 <khalim19@gmail.com>
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
This module:
* defines plug-in constants used in other modules
"""

#===============================================================================

from __future__ import absolute_import
from __future__ import print_function
#from __future__ import unicode_literals
from __future__ import division

#=============================================================================== 

import os

import gimp

#===============================================================================

PLUGINS_DIRECTORY = os.path.join(gimp.directory, 'plug-ins')

PLUGIN_PROGRAM_NAME = "export_layers"
PLUGIN_TITLE = "Export Layers"

PLUGIN_DIRNAME = PLUGIN_PROGRAM_NAME
PLUGIN_PATH = os.path.join(PLUGINS_DIRECTORY, PLUGIN_DIRNAME)

SHELF_PREFIX = PLUGIN_PROGRAM_NAME + "_"
CONFIG_FILE = os.path.join(PLUGIN_PATH, PLUGIN_PROGRAM_NAME + ".json")

BUG_REPORT_URI_LIST = [
                        ("GIMP Plugin Registry", "http://registry.gimp.org/node/28268"),
                        ("GitHub", "https://github.com/khalim19/gimp-plugin-export-layers/issues")
]
