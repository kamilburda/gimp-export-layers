# -*- coding: utf-8 -*-

"""Logging-related classes."""

# NOTE: In order to allow logging errors as early as possible (before plug-in
# initialization):
# * we are breaking the 'all imports at the beginning of module' convention
#   for some modules,
# * the `future` library is not imported in case some modules in the library are
#   not available in the installed Python distribution and would thus cause an
#   `ImportError` to be raised.

from __future__ import absolute_import, division, print_function, unicode_literals

str = unicode

import datetime
import io
import os
import sys
import traceback

from . import _path_dirs


_LOG_MODES = ('none', 'exceptions', 'files', 'gimp_console')

_exception_logger = None


def log_output(
      log_mode,
      log_dirpaths,
      log_stdout_filename,
      log_stderr_filename,
      log_header_title='',
      gimp_console_message_delay_milliseconds=0):
  """
  Enable logging of output.
  
  Parameters:
  
  * `log_mode` - The log mode. Possible values:
    
    * 'none' - Do not log anything.
    
    * 'exceptions' - Only log exceptions to the error log file.
    
    * 'files' - Redirect `stdout` and `stderr` to log files.
    
    * 'gimp_console' - Redirect `stdout` and `stderr` to the GIMP error console.
  
  * `log_dirpaths` - List of directory paths for log files. If the first path is
    invalid or permission to write is denied, subsequent directories are used.
    For the `'gimp_console'` mode, this parameter has no effect.
  
  * `log_stdout_filename` - Filename of the log file to write standard output
    to. Applies to the `'files'` mode only.
  
  * `log_stderr_filename` - Filename of the log file to write error output to.
    Applies to the `'exceptions'` and `'files'` modes only.
  
  * `log_header_title` - Optional title in the log header, written before the
    first output to the log files. Applies to the `'exceptions'` and `'files'`
    modes only.
  
  * `gimp_console_message_delay_milliseconds` - The delay to display messages to
    the GIMP console in milliseconds. Only applies to the `'gimp_console'` mode.
  """
  _restore_orig_state(log_mode)
  
  if log_mode == 'none':
    return
  
  if log_mode == 'exceptions':
    _redirect_exception_output_to_file(
      log_dirpaths, log_stderr_filename, log_header_title)
  elif log_mode == 'files':
    stdout_file = create_log_file(log_dirpaths, log_stdout_filename)
    
    if stdout_file is not None:
      sys.stdout = SimpleLogger(stdout_file, log_header_title)
    
    stderr_file = create_log_file(log_dirpaths, log_stderr_filename)
    
    if stderr_file is not None:
      sys.stderr = SimpleLogger(stderr_file, log_header_title)
  elif log_mode == 'gimp_console':
    from . import pdbutils as pgpdbutils
    
    sys.stdout = pgpdbutils.GimpMessageFile(
      message_delay_milliseconds=gimp_console_message_delay_milliseconds)
    sys.stderr = pgpdbutils.GimpMessageFile(
      message_prefix='Error: ',
      message_delay_milliseconds=gimp_console_message_delay_milliseconds)
  else:
    raise ValueError('invalid log mode "{}"; allowed values: {}'.format(
      log_mode, ', '.join(_LOG_MODES)))


def get_log_header(log_header_title):
  return '\n'.join(('', '=' * 80, log_header_title, str(datetime.datetime.now()), '\n'))


def create_log_file(log_dirpaths, log_filename, mode='a'):
  """
  Create a log file in the first file path that can be written to.
  
  Return the log file upon successful creation, `None` otherwise.
  """
  log_file = None
  
  for log_dirpath in log_dirpaths:
    try:
      _path_dirs.make_dirs(log_dirpath)
    except OSError:
      continue
    
    try:
      log_file = io.open(os.path.join(log_dirpath, log_filename), mode, encoding='utf-8')
    except IOError:
      continue
    else:
      break
  
  return log_file


def _restore_orig_state(log_mode):
  global _exception_logger
  
  for file_ in [_exception_logger, sys.stdout, sys.stderr]:
    if (file_ is not None
        and hasattr(file_, 'close')
        and file_ not in [sys.__stdout__, sys.__stderr__]):
      try:
        file_.close()
      except IOError:
        # An exception could occur for an invalid file descriptor.
        pass
  
  _exception_logger = None
  sys.excepthook = sys.__excepthook__
   
  sys.stdout = sys.__stdout__
  sys.stderr = sys.__stderr__


def _redirect_exception_output_to_file(log_dirpaths, log_filename, log_header_title):
  global _exception_logger
  
  def create_file_upon_exception_and_log_exception(exc_type, exc_value, exc_traceback):
    global _exception_logger
    
    _exception_log_file = create_log_file(log_dirpaths, log_filename)
    
    if _exception_log_file is not None:
      _exception_logger = SimpleLogger(_exception_log_file, log_header_title)
      log_exception(exc_type, exc_value, exc_traceback)
      
      sys.excepthook = log_exception
    else:
      sys.excepthook = sys.__excepthook__
  
  def log_exception(exc_type, exc_value, exc_traceback):
    global _exception_logger
    
    _exception_logger.write(
      ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback)))
  
  sys.excepthook = create_file_upon_exception_and_log_exception


class SimpleLogger(object):
  """
  This class wraps a file object to write a header before the first output.
  """
  
  def __init__(self, file_, log_header_title):
    self._log_file = file_
    self._log_header_title = log_header_title
  
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


# Original version by Peter Otten:
# http://mail.python.org/pipermail/python-list/2007-May/438106.html
class Tee(object):
  """
  This class copies `stdout` or `stderr` output to a specified file,
  much like the Unix `tee` command.
  
  This class acts as a file-like object containing the `write()` and `flush()`
  methods.
  
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
    
    * `start` - If `True`, start `Tee` upon instantiation. To start later, pass
      `start=False` and call `start()` when desired.
    
    * `flush_output` - If `True`, flush output after each write.
    """
    self._streams = {sys.stdout: 'stdout', sys.stderr: 'stderr'}
    
    self.log_header_title = log_header_title if log_header_title is not None else ''
    self.flush_output = flush_output
    
    self._file = None
    self._is_running = False
    
    self._orig_stream = None
    self._stream_name = ''
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
      raise ValueError('invalid stream; must be sys.stdout or sys.stderr')
  
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
    Return `True` if `Tee` is running (i.e. writing to file), `False` otherwise.
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
