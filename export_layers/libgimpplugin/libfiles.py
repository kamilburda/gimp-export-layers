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
* contains functions dealing with files, directories, filenames and strings
"""

#=============================================================================== 

import string
import os

#===============================================================================

def uniquify_string(str_, existing_strings, place_before_file_extension=False):
  """
  If string `str_` is in the `existing_strings` list, return a unique string
  by appending " (<number>)" to `str_`.
  
  If place_before_file_extension is True, place the " (<number>)" string
  before file extension if `str_` has one.
  """
  
  def _uniquify_without_extension(str_, existing_strings):
    j = 1
    uniq_str = '{0} ({1})'.format(str_, j)
    while uniq_str in existing_strings:
      j += 1
      uniq_str = '{0} ({1})'.format(str_, j)
    return uniq_str
  
  def _uniquify_with_extension(root, ext, existing_strings):
    j = 1
    uniq_str = '{0} ({1}).{2}'.format(root, j, ext)
    while uniq_str in existing_strings:
      j += 1
      uniq_str = '{0} ({1}).{2}'.format(root, j, ext)
    return uniq_str
  
  if str_ not in existing_strings:
    return str_
  
  if not place_before_file_extension:
    return _uniquify_without_extension(str_, existing_strings)
  else:
    root, ext = os.path.splitext(str_)
    ext = ext.lstrip('.')
    if ext:
      return _uniquify_with_extension(root, ext, existing_strings)
    else:
      return _uniquify_without_extension(str_, existing_strings)

def uniquify_filename(filename):
  """
  If a file with a specified filename already exists, return a unique filename.
  """
  root, ext = os.path.splitext(filename)
  
  if os.path.exists(filename):
    i = 1
    uniq_filename = ''.join((root, " (", str(i), ")", ext))
    while os.path.exists(uniq_filename):
      i += 1
      uniq_filename = ''.join((root, " (", str(i), ")", ext))
    return uniq_filename
  else:
    return filename

#-------------------------------------------------------------------------------

def get_file_extension(str_):
  return os.path.splitext(str_)[1].lstrip('.').lower()

# Taken from StackOverflow: http://stackoverflow.com/
# Question: http://stackoverflow.com/questions/600268/mkdir-p-functionality-in-python
#   by SetJmp: http://stackoverflow.com/users/30636/setjmp
# Answer: http://stackoverflow.com/questions/600268/mkdir-p-functionality-in-python/600612#600612
#   by tzot: http://stackoverflow.com/users/6899/tzot
#   edited by Craig Ringer: http://stackoverflow.com/users/398670/craig-ringer
def make_dirs(path):
  """
  Recursively create directories.
  Do not raise exception if directory already exists.
  """
  try:
    os.makedirs(path)
  except OSError as exc:
    if exc.errno == os.errno.EEXIST and os.path.isdir(path):
      pass
    elif exc.errno == os.errno.EACCES and os.path.isdir(path):
      # This can happen if os.makedirs is called on a root directory in Windows
      # (e.g. os.makedirs("C:\\")).
      pass
    else:
      raise

#===============================================================================

class StringValidator(object):
  
  """
  This class:
  * checks for validity of characters in a given string
  * deletes invalid characters from a given string
  """
  
  def __init__(self, allowed_chars):
    
    self._delete_table = ""
    self._invalid_chars = set()
    
    self.allowed_characters = allowed_chars
  
  def is_valid(self, string_to_validate):
    self._invalid_chars = set()
    for char in string_to_validate:
      if char not in self._allowed_chars:
        self._invalid_chars.add(char)
    
    is_valid = not self._invalid_chars
    return is_valid
  
  def validate(self, str_):
    self._invalid_chars = set()
    return str_.translate(None, self._delete_table)
  
  @property
  def allowed_characters(self):
    return self._allowed_chars
  
  @allowed_characters.setter
  def allowed_characters(self, chars):
    self._allowed_chars = chars if chars is not None else ""
    self._delete_table = string.maketrans(self._allowed_chars, '\x00' * len(self._allowed_chars))
    self._invalid_chars = set()
  
  @property
  def invalid_characters(self):
    return list(self._invalid_chars)

class DirnameValidator(StringValidator):
  
  _ALLOWED_CHARS = string.ascii_letters + string.digits + r"/\^&'@{}[],$=!-#()%.+~_ "
  _ALLOWED_CHARS_IN_DRIVE = ":" + _ALLOWED_CHARS
  
  def __init__(self):
    super(DirnameValidator, self).__init__(self._ALLOWED_CHARS)
  
  def is_valid(self, dirname):
    self._invalid_chars = set()
    
    drive, tail = os.path.splitdrive(dirname)
    
    if drive:
      for char in drive:
        if char not in self._ALLOWED_CHARS_IN_DRIVE:
          self._invalid_chars.add(char)
    
    for char in tail:
      if char not in self._allowed_chars:
        self._invalid_chars.add(char)
    
    is_valid = not self._invalid_chars
    return is_valid
  
  def validate(self, dirname):
    self._invalid_chars = set()
    
    drive, tail = os.path.splitdrive(dirname)
    
    self.allowed_characters = self._ALLOWED_CHARS_IN_DRIVE
    drive = drive.translate(None, self._delete_table)
    
    self.allowed_characters = self._ALLOWED_CHARS
    tail = tail.translate(None, self._delete_table)
    
    return os.path.normpath(os.path.join(drive, tail))
