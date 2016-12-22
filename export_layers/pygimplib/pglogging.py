# -*- coding: utf-8 -*-
#
# This file is part of pygimplib.
#
# Copyright (C) 2014-2016 khalim19 <khalim19@gmail.com>
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
This module:
* provides logging of unhandled exceptions and debug information (if
debugging is enabled),
* defines a class to duplicate ("tee") standard output or error output.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import future.standard_library
future.standard_library.install_aliases()

from future.builtins import *

import datetime
import io
import logging
import os
import sys

from . import pgconstants
from . import pgpath
from . import pgpdb

#===============================================================================


def log_output(log_mode, log_path_dirnames, log_stdout_filename, log_stderr_filename, log_header_title="",
               gimp_console_message_delay_milliseconds=0):
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
    first output to the log files. Applies to `EXCEPTIONS_ONLY` and `DEBUG_FILE`
    modes only.
  """
  
  if log_mode == pgconstants.LOG_EXCEPTIONS_ONLY:
    _redirect_exception_output_to_file(log_path_dirnames, log_stderr_filename, log_header_title)
  elif log_mode == pgconstants.LOG_OUTPUT_FILES:
    sys.stdout = SimpleLogger(os.path.join(log_path_dirnames[0], log_stdout_filename), "a", log_header_title)
    sys.stderr = SimpleLogger(os.path.join(log_path_dirnames[0], log_stderr_filename), "a", log_header_title)
    _redirect_exception_output_to_file(log_path_dirnames, log_stderr_filename, log_header_title)
  elif log_mode == pgconstants.LOG_OUTPUT_GIMP_CONSOLE:
    sys.stdout = pgpdb.GimpMessageFile(message_delay_milliseconds=gimp_console_message_delay_milliseconds)
    sys.stderr = pgpdb.GimpMessageFile(
      message_prefix="Error: ", message_delay_milliseconds=gimp_console_message_delay_milliseconds)


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


def _redirect_exception_output_to_file(log_path_dirnames, log_filename, log_header_title):
  logger = logging.getLogger(log_filename)
  logger.setLevel(logging.DEBUG)
  
  can_log = _logger_add_file_handler(
    logger, [os.path.join(log_path_dirname, log_filename) for log_path_dirname in log_path_dirnames])
  if can_log:
    # Pass the `logger` instance to the function to make sure it is not None.
    # More information at:
    # http://stackoverflow.com/questions/5451746/sys-excepthook-doesnt-work-in-imported-modules/5477639
    # http://bugs.python.org/issue11705
    def log_exceptions(exctype, value, traceback, logger=logger):
      logger.error(get_log_header(log_header_title), exc_info=(exctype, value, traceback))
    
    sys.excepthook = log_exceptions


def get_log_header(log_header_title):
  return "\n".join(("", "=" * 80, log_header_title, str(datetime.datetime.now()), "\n"))


#===============================================================================


class SimpleLogger(object):
  
  """
  This class wraps a file object to write a header before the first output.
  """
  
  def __init__(self, filename, mode, log_header_title):
    self._log_header_title = log_header_title
    self._log_file = io.open(filename, mode, encoding=pgconstants.GIMP_CHARACTER_ENCODING)
  
  def write(self, data):
    if self._log_header_title:
      self._write(get_log_header(self._log_header_title))
    
    self._write(data)
    self.flush()
    
    self.write = self._write
  
  def _write(self, data):
    self._log_file.write(data)
  
  def flush(self):
    self._log_file.flush()
  
  def close(self):
    self._log_file.close()


#===============================================================================


# Original version:
# http://mail.python.org/pipermail/python-list/2007-May/438106.html
# Author: Peter Otten
class Tee(object):
  
  """
  This class copies stdout or stderr output to a specified file,
  much like the Unix "tee" command.
  
  This class acts as a file-like object containing `write` and `flush` methods.
  
  Attributes:
  
  * `stream` - Either `sys.stdout` or `sys.stderr`. Other objects are invalid
    and raise `ValueError`.
    
  * `log_header_title` - Header text to write when writing into the file
    for the first time.
  """
  
  def __init__(self, stream, file_object, log_header_title=None, start=True, flush_output=False):
    """
    Parameters:
    
    * `file_object` - File or file-like object to write to.
    
    * `start` - If True, start `Tee` upon instantiation, otherwise don't.
      To start later, pass `start=False` and call the `start()` method when
      desired.
    
    * `flush_output` - If True, flush output after each write.
    """
  
    self._streams = {sys.stdout: "stdout", sys.stderr: "stderr"}
    
    self.log_header_title = log_header_title if log_header_title is not None else ""
    self.flush_output = flush_output
    
    self._file = None
    self._is_running = False
    
    self._orig_stream = None
    self._stream_name = ""
    self._stream = None
    
    self.stream = stream
    
    if start:
      self.start(file_object)
  
  def __del__(self):
    if self.is_running():
      self.stop()
  
  @property
  def stream(self):
    return self._stream
  
  @stream.setter
  def stream(self, value):
    self._stream = value
    if value in self._streams:
      self._stream_name = self._streams[value]
    else:
      raise ValueError("invalid stream; must be sys.stdout or sys.stderr")
  
  def start(self, file_object):
    """
    Start `Tee` if not started during the object instantiation.
    
    Parameters:
    
    * `file_object` - File or file-like object to write to.
    """
    
    self._orig_stream = self.stream
    setattr(sys, self._stream_name, self)
    
    self._file = file_object
    self._is_running = True
  
  def stop(self):
    """
    Stop `Tee`, i.e. stop writing to the file.
    """
    
    setattr(sys, self._stream_name, self._orig_stream)
    self._file.close()
    
    self._file = None
    self._is_running = False
  
  def is_running(self):
    """
    Return True if `Tee` is running (i.e. writing to file), False otherwise.
    """
    
    return self._is_running
  
  def write(self, data):
    """
    Write output to the stream and the specified file.
    
    If `log_header_title` is not empty, write the log header before the first
    output.
    """
    
    if self.log_header_title:
      self._file.write(get_log_header(self.log_header_title))
    
    self._write_with_flush(data)
    
    if not self.flush_output:
      self.write = self._write
    else:
      self.write = self._write_with_flush
  
  def _write(self, data):
    self._file.write(data)
    self._stream.write(data)

  def _write_with_flush(self, data):
    self._file.write(data)
    self._file.flush()
    self._stream.write(data)
    self._stream.flush()
  
  def flush(self):
    self._file.flush()
    self._stream.flush()
