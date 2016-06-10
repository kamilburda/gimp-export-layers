#
# This file is part of pygimplib.
#
# Copyright (C) 2014, 2015 khalim19 <khalim19@gmail.com>
#
# pygimplib is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pygimplib is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pygimplib.  If not, see <http://www.gnu.org/licenses/>.
#

"""
This module provides logging of unhandled exceptions and debug information (if
debugging is enabled).
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

str = unicode

import logging
import os
import sys

from . import pgpath
from . import pgpdb
from . import tee

#===============================================================================

_LOG_MODES = (EXCEPTIONS_ONLY, DEBUG_FILE, DEBUG_GIMP_CONSOLE) = (0, 1, 2)

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


def log_output(log_mode, log_path_dirnames, log_stdout_filename, log_stderr_filename, log_header_title=""):
  """
  Enable logging of output.
  
  Parameters:
  
  * `log_mode` - log mode. Possible values:
  
    * EXCEPTIONS_ONLY - only log exceptions to the error log file.
    * DEBUG_FILE - redirect stdout and stderr to log files.
    * DEBUG_GIMP_CONSOLE - redirect stdout and stderr to the GIMP error console.
  
  * `log_path_dirnames` - list of directory paths for log files. If the first
    path is invalid or permission to write is denied, subsequent directories are
    used. For `DEBUG_FILE` mode, only the first directory is used. For
    `DEBUG_GIMP_CONSOLE` mode, this parameter has no effect.
  
  * `log_stdout_filename` - filename of the log file to write standard output
    to. Applies to `DEBUG_FILE` mode only.
  
  * `log_stderr_filename` - filename of the log file to write error output to.
    Applies to `EXCEPTIONS_ONLY` and `DEBUG_FILE` modes only.
  
  * `log_header_title` - optional title in the log header, written before the
    first write to the log files. Applies to `EXCEPTIONS_ONLY` and `DEBUG_FILE`
    modes only.
  """
  
  if log_mode == EXCEPTIONS_ONLY:
    logger = logging.getLogger(log_stderr_filename)
    logger.setLevel(logging.DEBUG)
    
    can_log = _logger_add_file_handler(
      logger, [os.path.join(log_path_dirname, log_stderr_filename) for log_path_dirname in log_path_dirnames])
    if can_log:
      # Pass the `logger` instance to the function to make sure it is not None.
      # More information at:
      # http://stackoverflow.com/questions/5451746/sys-excepthook-doesnt-work-in-imported-modules/5477639
      # http://bugs.python.org/issue11705
      def log_exceptions(exctype, value, traceback, logger=logger):
        logger.error(tee.get_log_header(log_header_title).encode(), exc_info=(exctype, value, traceback))
      
      sys.excepthook = log_exceptions
  
  elif log_mode == DEBUG_FILE:
    tee.Tee(sys.stdout, open(os.path.join(log_path_dirnames[0], log_stdout_filename), "a"),
            log_header_title=log_header_title, flush_output=True)
    tee.Tee(sys.stderr, open(os.path.join(log_path_dirnames[0], log_stderr_filename), "a"),
            log_header_title=log_header_title, flush_output=True)
  elif log_mode == DEBUG_GIMP_CONSOLE:
    tee.Tee(sys.stdout, pgpdb.GimpMessageFile(), flush_output=True)
    tee.Tee(sys.stderr, pgpdb.GimpMessageFile(message_prefix="Error: "), flush_output=True)
