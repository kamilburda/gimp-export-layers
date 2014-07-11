#-------------------------------------------------------------------------------
#
# This file is part of pylibgimpplugin.
#
# Copyright (C) 2014 khalim19 <khalim19@gmail.com>
# 
# pylibgimpplugin is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# pylibgimpplugin is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with pylibgimpplugin.  If not, see <http://www.gnu.org/licenses/>.
#
#-------------------------------------------------------------------------------

"""
This module contains functions dealing with files, directories, filenames
and strings.
"""

#===============================================================================

from __future__ import absolute_import
from __future__ import print_function
#from __future__ import unicode_literals
from __future__ import division

#=============================================================================== 

import string
import os
import re
import abc

#===============================================================================

def uniquify_string(str_, existing_strings, place_before_file_extension=False):
  """
  If string `str_` is in the `existing_strings` list, return a unique string
  by appending " (<number>)" to `str_`. Otherwise return `str_`.
  
  Parameters:
  
  * `str_` - String to uniquify.
  
  * `existing_strings` - List of string to compare against `str_`.
  
  * `place_before_file_extension` - If True, place the " (<number>)" string
  before file extension if `str_` has one.
  
  Returns:
  
    Uniquified string.
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
  """
  Return the file extension from a string in lower case and strip the leading
  dot. If the string has no file extension, return empty string.
  
  A string has file extension if it contains a '.' character and a substring
  following this character.
  """
  return os.path.splitext(str_)[1].lstrip('.').lower()


# Taken from StackOverflow: http://stackoverflow.com/
# Question: http://stackoverflow.com/questions/600268/mkdir-p-functionality-in-python
#   by SetJmp: http://stackoverflow.com/users/30636/setjmp
# Answer: http://stackoverflow.com/questions/600268/mkdir-p-functionality-in-python/600612#600612
#   by tzot: http://stackoverflow.com/users/6899/tzot
#   edited by Craig Ringer: http://stackoverflow.com/users/398670/craig-ringer
def make_dirs(path):
  """
  Recursively create directories from specified path.
  
  Do not raise exception if the directory already exists.
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


def split_path(path):
  """
  Split the specified path into separate components.
  """
  
  path = os.path.normpath(path)
  path_components = []
  
  head = path
  while True:
    head, tail = os.path.split(head)
    if tail:
      path_components.insert(0, tail)
    else:
      if head:
        path_components.insert(0, head)
      break
  
  return path_components

#===============================================================================

class StringValidator(object):
  
  """
  This class is an interface to validate strings.
  
  Strings are assumed to be Unicode strings.
  
  This class does not specify what strings are valid (whether they contain
  invalid characters, substrings, etc.). This should be handled by subclasses.
  
  Methods:
  
  * `is_valid()` - Check if the specified string is valid.
  
  * `validate()` - Modify the specified string to make it valid.
  """
  
  __metaclass__ = abc.ABCMeta
  
  @abc.abstractmethod
  def is_valid(self, string_to_check):
    """
    Check if the specified input string is valid.
    
    Returns:
      
      * `is_valid` - True if the input string is valid, False otherwise.
      
      * `status_message` - If the input string is invalid, `status_message` is
        a string describing why the input string is invalid.
    """
    pass
  
  @abc.abstractmethod
  def validate(self, string_to_validate):
    """
    Modify the specified string to make it valid.
    """
    pass


class FilenameValidator(StringValidator):
  
  """
  This class is used to validate filenames (not their full path, only the
  name itself, also called "basenames").
  
  In this class, filenames are considered valid if they:
    
    * don't contain control characters with ordinal numbers 0-31 and 127-159
    
    * don't contain the following special characters:
      
      <>:"/\|?*~!@'`#$%&=+{}[]
    
    * don't start or end with spaces
    
    * don't end with one or more periods
    
    * don't have invalid names according to the naming conventions for the
      Windows platform:
      
      http://msdn.microsoft.com/en-us/library/aa365247%28VS.85%29
    
    * are not empty or None
  """
  
  _INVALID_CHARS_PATTERN = r"[\x00-\x1f\x7f-\x9f<>:\"\\/|?*~!@'`#$%&=+{}\[\]]"
  
  # Invalid names for the Windows platform. Taken from:
  # http://msdn.microsoft.com/en-us/library/windows/desktop/aa365247%28v=vs.85%29.aspx
  _INVALID_NAMES = {
   "CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "COM5", "COM6",
   "COM7", "COM8", "COM9", "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6",
   "LPT7", "LPT8", "LPT9"
  }
  
  def is_valid(self, filename):
    """
    Check whether the specified filename is valid.
    
    See the class description for details about when the filename is valid.
    """
    
    if not filename or filename is None:
      return False, "Filename is empty."
    
    status_message = ""
    
    if re.search(self._INVALID_CHARS_PATTERN, filename):
      status_message += "Filename contains invalid characters.\n"
    
    if filename.startswith(" ") or filename.endswith(" "):
      status_message += "Filename cannot start or end with spaces.\n"
    
    if filename.endswith("."):
      status_message += "Filename cannot end with a period.\n"
    
    root, _ = os.path.splitext(filename)
    if root.upper() in self._INVALID_NAMES:
      status_message = (
        "\"" + filename + "\" is a reserved name that cannot be used "
        "in file paths.\n"
      )
    
    status_message = status_message.rstrip('\n')
    is_valid = not status_message
    
    return is_valid, status_message
  
  def validate(self, filename):
    """
    Validate the specified filename by removing invalid characters.
    
    If the filename is one of the reserved names for the Windows platform,
    append " (1)" to the filename (before the file extension if it has one).
    
    If the filename is truncated to an empty string, return "Untitled".
    """
    
    filename = (
      re.sub(self._INVALID_CHARS_PATTERN, "", filename)
        .strip(" ")
        .rstrip(".")
    )
    
    root, ext = os.path.splitext(filename)
    # For reserved names, the comparison must be case-insensitive
    # (because Windows has case-insensitive filenames).
    if root.upper() in self._INVALID_NAMES:
      filename = root + " (1)" + ext
    
    if not filename:
      filename = "Untitled"
    
    return filename


class FilePathValidator(StringValidator):
  
  """
  This class is used to validate file paths (relative or absolute).
  
  The same validation rules that apply to filenames in the `FilenameValidator`
  class apply to file paths in this class, with the following exceptions:
    
    * '/' and '\' characters are allowed
    
    * ':' character is allowed to appear at the root level (as a part of a drive
      letter, e.g. "C:\")
  """
  
  _INVALID_CHARS = r"\x00-\x1f\x7f-\x9f<>\"|?*~!@'`#$%&=+{}\[\]"
  _VALID_DRIVE_CHARS = r':'
  
  _INVALID_CHARS_PATTERN_WITHOUT_DRIVE = "[" + _INVALID_CHARS + "]"
  _INVALID_CHARS_PATTERN = "[" + _INVALID_CHARS + _VALID_DRIVE_CHARS + "]"
  
  _INVALID_NAMES = FilenameValidator._INVALID_NAMES
  
  __PATH_COMPONENT_STATUSES = _INVALID_CHARS, _HAS_SPACES, _HAS_TRAILING_PERIOD = (0, 1, 2)
  
  def is_valid(self, filepath):
    
    if not filepath or filepath is None:
      return False, "File path is empty."
    
    status_message = ""
    statuses = set()
    filepath = os.path.normpath(filepath)
    
    drive, path = os.path.splitdrive(filepath)
    
    if drive:
      if re.search(self._INVALID_CHARS_PATTERN_WITHOUT_DRIVE, drive):
        status_message += "Drive letter contains invalid characters.\n"
    
    path_components = split_path(path)
    for path_component in path_components:
      if re.search(self._INVALID_CHARS_PATTERN, path_component):
        statuses.add(self._INVALID_CHARS)
      if path_component.startswith(" ") or path_component.endswith(" "):
        statuses.add(self._HAS_SPACES)
      if path_component.endswith("."):
        statuses.add(self._HAS_TRAILING_PERIOD)
      
      root, _ = os.path.splitext(path_component)
      if root.upper() in self._INVALID_NAMES:
        status_message += (
          "\"" + path_component + "\" is a reserved name that cannot be used "
          "in file paths.\n"
        )
    
    if self._INVALID_CHARS in statuses:
      status_message += (
        "File path contains invalid characters.\n"
      )
    if self._HAS_SPACES in statuses:
      status_message += (
        "Path components in the file path cannot start or end with spaces.\n"
      )
    if self._HAS_TRAILING_PERIOD in statuses:
      status_message += (
        "Path components in the file path cannot end with a period.\n"
      )
    
    status_message = status_message.rstrip('\n')
    is_valid = not status_message
    
    return is_valid, status_message
  
  def validate(self, filepath):
    """
    Raises:
    
    * `ValueError` - A path component in the file path was truncated
      to an empty string.
    """
    
    filepath = os.path.normpath(filepath)
    drive, path = os.path.splitdrive(filepath)
    
    if drive:
      drive = re.sub(self._INVALID_CHARS_PATTERN_WITHOUT_DRIVE, "", drive)
    
    path_components = split_path(path)
    for i in range(len(path_components)):
      path_component = re.sub(self._INVALID_CHARS_PATTERN, "", path_components[i])
      path_component = path_component.strip(" ").rstrip(".")
      
      root, ext = os.path.splitext(path_component)
      if root.upper() in self._INVALID_NAMES:
        path_component = root + " (1)" + ext
    
      if not path_component:
        raise ValueError("Path component \"" + repr(path_components[i]) + "\"" +
                         " was truncated to an empty string.")
      
      path_components[i] = path_component
    
    filepath = os.path.join(drive, *path_components)
    
    return filepath


class FileExtensionValidator(StringValidator):
  
  """
  This class is used to validate file extensions.
  
  In this class, file extensions are considered valid if they:
    
    * don't contain control characters with ordinal numbers 0-31 and 127-159
    
    * don't contain the following special characters:
      
      <>:"/\|?*~!@'`#$%&=+{}[]
    
    * don't end with spaces or periods
  """
  
  _INVALID_CHARS_PATTERN = FilenameValidator._INVALID_CHARS_PATTERN
  
  def is_valid(self, file_ext):
    
    if not file_ext or file_ext is None:
      return False, "File extension is empty."
    
    status_message = ""
    
    if re.search(self._INVALID_CHARS_PATTERN, file_ext):
      status_message += "File extension contains invalid characters.\n"
    
    if file_ext.endswith(" ") or file_ext.endswith("."):
      status_message += "File extension cannot end with spaces or periods.\n"
    
    status_message = status_message.rstrip('\n')
    is_valid = not status_message
    
    return is_valid, status_message
  
  def validate(self, file_ext):
    """
    Validate the specified file extension by removing invalid characters.
    
    Raises:
    
    * `ValueError` - File extension is truncated to an empty string.
    """
    
    file_ext = (
      re.sub(self._INVALID_CHARS_PATTERN, "", file_ext)
        .rstrip(" ")
        .rstrip(".")
    )
    
    if not file_ext:
      raise ValueError("File extension was truncated to an empty string.")
    
    return file_ext

#===============================================================================

class OldStringValidator(object):
  
  """
  This class:
  * checks for validity of characters in a given string
  * deletes invalid characters from a given string
  
  Attributes:
  
  * `allowed_characters` - String of characters allowed in strings.
  
  * `invalid_characters` - Set of invalid characters found in the string passed
    to `is_valid()` or `validate()`.
  
  Methods:
  
  * `is_valid()` - Check if the specified string contains invalid characters.
  
  * `validate()` - Remove invalid characters from the specified string.
  """
  
  def __init__(self, allowed_chars):
    self._delete_table = ""
    self._invalid_chars = set()
    
    self.allowed_characters = allowed_chars
  
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
  
  def is_valid(self, string_to_validate):
    """
    Check if the specified string contains invalid characters.
    
    All invalid characters found in the string are assigned to the
    `invalid_characters` attribute.
    
    Returns:
    
      True if `string_to_validate` is does not contain invalid characters,
      False otherwise.
    """
    self._invalid_chars = set()
    for char in string_to_validate:
      if char not in self._allowed_chars:
        self._invalid_chars.add(char)
    
    is_valid = not self._invalid_chars
    return is_valid
  
  def validate(self, string_to_validate):
    """
    Remove invalid characters from the specified string.
    
    All invalid characters found in the string are assigned to the
    `invalid_characters` attribute.
    """
    self._invalid_chars = set()
    return string_to_validate.translate(None, self._delete_table)


class OldDirnameValidator(OldStringValidator):
  
  """
  This class:
  * checks for validity of characters in a given directory path
  * deletes invalid characters from a given directory path
  
  This class contains a predefined set of characters allowed in directory paths.
  While the set of valid characters is platform-dependent, this class attempts
  to take the smallest set possible, i.e. allow only characters which are valid
  on all platforms.
  """
  
  _ALLOWED_CHARS = string.ascii_letters + string.digits + r"/\^&'@{}[],$=!-#()%.+~_ "
  _ALLOWED_CHARS_IN_DRIVE = ":" + _ALLOWED_CHARS
  
  def __init__(self):
    super(OldDirnameValidator, self).__init__(self._ALLOWED_CHARS)
  
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
