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
This module provides logging of unhandled exceptions and debug information (if
debugging is enabled).
"""

#===============================================================================

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division

str = unicode

#===============================================================================

import os
import sys
import logging

from export_layers.pygimplib import tee
from export_layers.pygimplib import pgpath
from export_layers import constants

#===============================================================================


def _logger_add_file_handler(logger, log_paths):
  """
  If the first log path in `log_paths` cannot be used (e.g. due to denied write
  permission), try out subsequent paths.
  
  Do not log if directories cannot be created or any of the log files cannot be
  created.
  """
  
  can_log = True
  for log_path in log_paths:
    try:
      pgpath.make_dirs(os.path.dirname(log_path))
    except OSError:
      can_log = False
      break
    
    try:
      logger.addHandler(logging.FileHandler(log_path))
    except (OSError, IOError):
      if log_path == log_paths[-1]:
        can_log = False
    else:
      break
  
  return can_log


def log_output(debug=False):
  if not debug:
    logger = logging.getLogger(constants.PLUGIN_PROGRAM_NAME)
    logger.setLevel(logging.DEBUG)
    
    can_log = _logger_add_file_handler(
      logger, [constants.PLUGINS_LOG_STDERR_PATH, constants.PLUGINS_LOG_STDERR_PATH_ALTERNATE])
    if can_log:
      # Pass the `logger` instance to the function to make sure it is not None.
      # More information at:
      # http://stackoverflow.com/questions/5451746/sys-excepthook-doesnt-work-in-imported-modules/5477639
      # http://bugs.python.org/issue11705
      def log_exceptions(exctype, value, traceback, logger=logger):
        logger.error(tee.get_log_header(constants.PLUGIN_TITLE).encode(), exc_info=(exctype, value, traceback))
      
      sys.excepthook = log_exceptions
  else:
    tee.Tee(sys.stdout, open(constants.PLUGINS_LOG_STDOUT_PATH, "a"),
            log_header_title=constants.PLUGIN_TITLE, flush_file=True)
    tee.Tee(sys.stderr, open(constants.PLUGINS_LOG_STDERR_PATH, "a"),
            log_header_title=constants.PLUGIN_TITLE, flush_file=True)
