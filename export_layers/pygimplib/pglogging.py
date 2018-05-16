# -*- coding: utf-8 -*-
#
# Copyright (C) 2014-2018 khalim19
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
This module:
* provides logging of unhandled exceptions and debug information (if
debugging is enabled),
* defines a class to duplicate ("tee") standard output or error output.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
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


def log_output(
      log_mode, log_dirpaths, log_stdout_filename, log_stderr_filename,
      log_header_title="", gimp_console_message_delay_milliseconds=0):
  """
  Enable logging of output.
  
  Parameters:
  
  * `log_mode` - log mode. Possible values:
  
    * LOG_EXCEPTIONS_ONLY - only log exceptions to the error log file.
    * LOG_OUTPUT_FILES - redirect stdout and stderr to log files.
    * LOG_OUTPUT_GIMP_CONSOLE - redirect stdout and stderr to the GIMP error
      console.
  
  * `log_dirpaths` - list of directory paths for log files. If the first
    path is invalid or permission to write is denied, subsequent directories are
    used. For `LOG_OUTPUT_FILES` mode, only the first directory is used. For
    `LOG_OUTPUT_GIMP_CONSOLE` mode, this parameter has no effect.
  
  * `log_stdout_filename` - filename of the log file to write standard output
    to. Applies to `LOG_OUTPUT_FILES` mode only.
  
  * `log_stderr_filename` - filename of the log file to write error output to.
    Applies to `LOG_EXCEPTIONS_ONLY` and `LOG_OUTPUT_FILES` modes only.
  
  * `log_header_title` - optional title in the log header, written before the
    first output to the log files. Applies to `LOG_EXCEPTIONS_ONLY` and
    `LOG_OUTPUT_FILES` modes only.
  
  * `gimp_console_message_delay_milliseconds` - delay to display messages to the
    GIMP console in milliseconds. Only applies to the `LOG_OUTPUT_GIMP_CONSOLE`
    log mode.
  """
  
  if log_mode == pgconstants.LOG_NONE:
    return
  if log_mode == pgconstants.LOG_EXCEPTIONS_ONLY:
    _redirect_exception_output_to_file(
      log_dirpaths, log_stderr_filename, log_header_title)
  elif log_mode == pgconstants.LOG_OUTPUT_FILES:
    sys.stdout = SimpleLogger(
      os.path.join(log_dirpaths[0], log_stdout_filename), "a", log_header_title)
    sys.stderr = SimpleLogger(
      os.path.join(log_dirpaths[0], log_stderr_filename), "a", log_header_title)
  elif log_mode == pgconstants.LOG_OUTPUT_GIMP_CONSOLE:
    sys.stdout = pgpdb.GimpMessageFile(
      message_delay_milliseconds=gimp_console_message_delay_milliseconds)
    sys.stderr = pgpdb.GimpMessageFile(
      message_prefix="Error: ",
      message_delay_milliseconds=gimp_console_message_delay_milliseconds)


def _redirect_exception_output_to_file(
      log_dirpaths, log_filename, log_header_title):
  logger = logging.getLogger(log_filename)
  logger.setLevel(logging.DEBUG)
  
  # Pass the `logger` instance to the function to make sure it is not None.
  # More information at:
  # http://stackoverflow.com/questions/5451746/sys-excepthook-doesnt-work-in-imported-modules/5477639
  # http://bugs.python.org/issue11705
  def log_exception(exctype, value, traceback, logger=logger):
    logger.error(
      get_log_header(log_header_title), exc_info=(exctype, value, traceback))
  
  def log_exception_first_time(exctype, value, traceback, logger=logger):
    can_log = _logger_add_file_handler(
      logger, [os.path.join(log_dirpath, log_filename) for log_dirpath in log_dirpaths])
    if can_log:
      log_exception(exctype, value, traceback, logger=logger)
      sys.excepthook = log_exception
    else:
      sys.excepthook = sys.__excepthook__
  
  sys.excepthook = log_exception_first_time


def _logger_add_file_handler(logger, log_filepaths):
  """
  If the first log path in `log_filepaths` cannot be used (e.g. due to denied
  write permission), try out subsequent paths.
  
  Do not log if directories cannot be created or any of the log files cannot be
  created.
  """
  
  can_log = True
  for log_filepath in log_filepaths:
    try:
      pgpath.make_dirs(os.path.dirname(log_filepath))
    except OSError:
      can_log = False
      break
    
    try:
      logger.addHandler(logging.FileHandler(log_filepath))
    except (OSError, IOError):
      if log_filepath == log_filepaths[-1]:
        can_log = False
    else:
      break
  
  return can_log


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
    
    self.write = self._write
  
  def _write(self, data):
    self._log_file.write(str(data))
    self.flush()
  
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
  
  def __init__(
        self, stream, file_, log_header_title=None, start=True, flush_output=False):
    """
    Parameters:
    
    * `file_` - File or file-like object to write to.
    
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
      self.start(file_)
  
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
  
  def start(self, file_):
    """
    Start `Tee` if not started during the object instantiation.
    
    Parameters:
    
    * `file_` - File or file-like object to write to.
    """
    
    self._orig_stream = self.stream
    setattr(sys, self._stream_name, self)
    
    self._file = file_
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
