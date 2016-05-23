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
This module defines a class to log "stdout" and "stderr" output to the specified
file, much like the Unix "tee" command.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

str = unicode

import datetime
import sys

#===============================================================================


def get_log_header(log_header_title):
  return "\n".join(("", "=" * 80, log_header_title, str(datetime.datetime.now()), "\n"))


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
  
    self._streams = {sys.stdout: 'stdout', sys.stderr: 'stderr'}
    
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
      self._file.write(get_log_header(self.log_header_title).encode())
    
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
  
  def flush(self):
    self._file.flush()
    self._stream.flush()
