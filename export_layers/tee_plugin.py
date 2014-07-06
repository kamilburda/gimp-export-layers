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
* wraps the "tee" module for easier usage in GIMP plug-ins
"""

#===============================================================================

import sys
import os

from export_layers.libgimpplugin import tee

from export_layers import constants

#===============================================================================

PLUGINS_STDOUT_FILENAME = constants.PLUGIN_PROGRAM_NAME + '.log'
PLUGINS_STDERR_FILENAME = constants.PLUGIN_PROGRAM_NAME + '_error.log'

_tee_stdout = None
_tee_stderr = None

def tee_plugin(log_header):
  global _tee_stdout, _tee_stderr
  
  file_stdout = open(os.path.join(constants.PLUGIN_PATH, PLUGINS_STDOUT_FILENAME), 'a')
  file_stderr = open(os.path.join(constants.PLUGIN_PATH, PLUGINS_STDERR_FILENAME), 'a')
  _tee_stdout = tee.Tee(sys.stdout, file_stdout, log_header_title=log_header, flush_file=True)
  _tee_stderr = tee.Tee(sys.stderr, file_stderr, log_header_title=log_header, flush_file=True)
