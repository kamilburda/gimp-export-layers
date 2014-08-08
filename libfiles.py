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
from __future__ import unicode_literals
from __future__ import division

str = unicode

#=============================================================================== 

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
  
  if os.path.exists(filename):
    root, ext = os.path.splitext(filename)
    i = 1
    uniq_filename = ''.join((root, " (", str(i), ")", ext))
    while os.path.exists(uniq_filename):
      i += 1
      uniq_filename = ''.join((root, " (", str(i), ")", ext))
    return uniq_filename
  else:
    return filename

#-------------------------------------------------------------------------------

def get_file_extension(str_, to_lowercase=True):
  """
  Return the file extension from the specified string in lower case and strip
  the leading period. If the string has no file extension, return empty string.
  
  A string has file extension if it contains a '.' character and a substring
  following this character.
  
  Paramters:
  
  * `to_lowercase` - If True, convert the file extension to lowercase.
  """
  
  file_ext = os.path.splitext(str_)[1].lstrip('.')
  
  if to_lowercase:
    return file_ext.lower()
  else:
    return file_ext


# Taken from StackOverflow: http://stackoverflow.com/
# Question: http://stackoverflow.com/questions/600268/mkdir-p-functionality-in-python
#   by SetJmp: http://stackoverflow.com/users/30636/setjmp
# Answer: http://stackoverflow.com/questions/600268/mkdir-p-functionality-in-python/600612#600612
#   by tzot: http://stackoverflow.com/users/6899/tzot
#   edited by Craig Ringer: http://stackoverflow.com/users/398670/craig-ringer
def make_dirs(path):
  """
  Recursively create directories from the specified path.
  
  Do not raise exception if the path already exists.
  """
  try:
    os.makedirs(path)
  except OSError as exc:
    if exc.errno == os.errno.EEXIST and os.path.isdir(path):
      pass
    elif exc.errno == os.errno.EACCES and os.path.isdir(path):
      # This can happen if `os.makedirs` is called on a root directory
      # in Windows (e.g. `os.makedirs("C:\\")`).
      pass
    else:
      raise


def split_path(path):
  """
  Split the specified path into separate path components.
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
  
  @classmethod
  def is_valid(cls, string_to_check):
    """
    Check if the specified string is valid.
    
    Returns:
      
      * `is_valid` - True if the string is valid, False otherwise.
      
      * `status_messages` - If the string is invalid, `status_messages` is
        a list of (status code, status message) tuples describing why the string
        is invalid. Otherwise it is an empty list.
    """
    pass
  
  @classmethod
  def validate(cls, string_to_validate):
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
      
      <>:"/\|?*
    
    * don't start or end with spaces
    
    * don't end with one or more periods
    
    * don't have invalid names according to the naming conventions for the
      Windows platform:
      
      http://msdn.microsoft.com/en-us/library/aa365247%28VS.85%29
    
    * are not empty or None
  """
  
  _INVALID_CHARS_PATTERN = r"[\x00-\x1f\x7f-\x9f<>:\"\\/|?*]"
  
  # Invalid names for the Windows platform. Taken from:
  # http://msdn.microsoft.com/en-us/library/windows/desktop/aa365247%28v=vs.85%29.aspx
  _INVALID_NAMES = {
   "CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "COM5", "COM6",
   "COM7", "COM8", "COM9", "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6",
   "LPT7", "LPT8", "LPT9"
  }
  
  ERROR_STATUSES = (
     IS_EMPTY, HAS_INVALID_CHARS, HAS_SPACES, HAS_TRAILING_PERIOD,
     HAS_INVALID_NAMES
  ) = (0, 1, 2, 3, 4)
  
  @classmethod
  def is_valid(cls, filename):
    """
    Check whether the specified filename is valid.
    
    See the class description for details about when the filename is valid.
    """
    
    if not filename or filename is None:
      return False, [(cls.IS_EMPTY, _("Filename is not specified."))]
    
    status_messages = []
    
    if re.search(cls._INVALID_CHARS_PATTERN, filename):
      status_messages.append(
        (cls.HAS_INVALID_CHARS,
         _("Filename contains invalid characters.")))
    
    if filename.startswith(" ") or filename.endswith(" "):
      status_messages.append(
        (cls.HAS_SPACES,
         _("Filename cannot start or end with spaces.")))
    
    if filename.endswith("."):
      status_messages.append(
        (cls.HAS_TRAILING_PERIOD,
         _("Filename cannot end with a period.")))
    
    root, unused_ = os.path.splitext(filename)
    if root.upper() in cls._INVALID_NAMES:
      status_messages.append(
        (cls.HAS_INVALID_NAMES,
         _("\"{0}\" is a reserved name that cannot be used in filenames.").format(filename))
      )
    
    is_valid = not status_messages
    return is_valid, status_messages
  
  @classmethod
  def validate(cls, filename):
    """
    Validate the specified filename by removing invalid characters.
    
    If the filename is one of the reserved names for the Windows platform,
    append " (1)" to the filename (before the file extension if it has one).
    
    If the filename is truncated to an empty string, return "Untitled".
    """
    
    filename = (
      re.sub(cls._INVALID_CHARS_PATTERN, "", filename)
        .strip(" ")
        .rstrip(".")
    )
    
    root, ext = os.path.splitext(filename)
    # For reserved names, the comparison must be case-insensitive
    # (because Windows has case-insensitive filenames).
    if root.upper() in cls._INVALID_NAMES:
      filename = root + " (1)" + ext
    
    if not filename:
      filename = _("Untitled")
    
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
  
  _INVALID_CHARS = r"\x00-\x1f\x7f-\x9f<>\"|?*"
  _VALID_DRIVE_CHARS = r':'
  
  _INVALID_CHARS_PATTERN_WITHOUT_DRIVE = "[" + _INVALID_CHARS + "]"
  _INVALID_CHARS_PATTERN = "[" + _INVALID_CHARS + _VALID_DRIVE_CHARS + "]"
  
  _INVALID_NAMES = FilenameValidator._INVALID_NAMES
  
  ERROR_STATUSES = (
     IS_EMPTY, DRIVE_HAS_INVALID_CHARS, HAS_INVALID_CHARS,
     HAS_SPACES, HAS_TRAILING_PERIOD, HAS_INVALID_NAMES
  ) = (0, 1, 2, 3, 4, 5)
  
  @classmethod
  def is_valid(cls, filepath):
    if not filepath or filepath is None:
      return False, [(cls.IS_EMPTY, _("File path is not specified."))]
    
    status_messages = []
    statuses = set()
    invalid_names_status_message = ""
    
    filepath = os.path.normpath(filepath)
    
    drive, path = os.path.splitdrive(filepath)
    
    if drive:
      if re.search(cls._INVALID_CHARS_PATTERN_WITHOUT_DRIVE, drive):
        status_messages.append(
          (cls.DRIVE_HAS_INVALID_CHARS,
           _("Drive letter contains invalid characters.")))
    
    path_components = split_path(path)
    for path_component in path_components:
      if re.search(cls._INVALID_CHARS_PATTERN, path_component):
        statuses.add(cls.HAS_INVALID_CHARS)
      if path_component.startswith(" ") or path_component.endswith(" "):
        statuses.add(cls.HAS_SPACES)
      if path_component.endswith("."):
        statuses.add(cls.HAS_TRAILING_PERIOD)
      
      root, unused_ = os.path.splitext(path_component)
      if root.upper() in cls._INVALID_NAMES:
        statuses.add(cls.HAS_INVALID_NAMES)
        invalid_names_status_message += (
          _("\"{0}\" is a reserved name that cannot be used "
            "in file paths.\n").format(path_component)
        )
    
    if cls.HAS_INVALID_CHARS in statuses:
      status_messages.append(
        (cls.HAS_INVALID_CHARS,
         _("File path contains invalid characters.")))
    if cls.HAS_SPACES in statuses:
      status_messages.append(
        (cls.HAS_SPACES,
         _("Path components in the file path cannot start or end with spaces.")))
    if cls.HAS_TRAILING_PERIOD in statuses:
      status_messages.append(
        (cls.HAS_TRAILING_PERIOD,
         _("Path components in the file path cannot end with a period.")))
    if cls.HAS_INVALID_NAMES in statuses:
      invalid_names_status_message.rstrip("\n")
      status_messages.append((cls.HAS_INVALID_NAMES, invalid_names_status_message))
    
    is_valid = not status_messages
    return is_valid, status_messages
  
  @classmethod
  def validate(cls, filepath):
    filepath = os.path.normpath(filepath)
    drive, path = os.path.splitdrive(filepath)
    
    if drive:
      drive = re.sub(cls._INVALID_CHARS_PATTERN_WITHOUT_DRIVE, "", drive)
    
    path_components = split_path(path)
    for i in range(len(path_components)):
      path_component = re.sub(cls._INVALID_CHARS_PATTERN, "", path_components[i])
      path_component = path_component.strip(" ").rstrip(".")
      
      root, ext = os.path.splitext(path_component)
      if root.upper() in cls._INVALID_NAMES:
        path_component = root + " (1)" + ext
      
      path_components[i] = path_component
    
    # Normalize again, since the last path component might be truncated to an
    # empty string, resulting in a trailing slash.
    filepath = os.path.normpath(os.path.join(drive, *path_components))
    
    return filepath


class FileExtensionValidator(StringValidator):
  
  """
  This class is used to validate file extensions.
  
  In this class, file extensions are considered valid if they:
    
    * don't contain control characters with ordinal numbers 0-31 and 127-159
    
    * don't contain the following special characters:
      
      <>:"/\|?*
    
    * don't end with spaces or periods
  """
  
  _INVALID_CHARS_PATTERN = FilenameValidator._INVALID_CHARS_PATTERN
  
  ERROR_STATUSES = (
    IS_EMPTY, HAS_INVALID_CHARS, ENDS_WITH_SPACES_OR_PERIODS
  ) = (0, 1, 2)
  
  @classmethod
  def is_valid(cls, file_ext):
    if not file_ext or file_ext is None:
      return False, [(cls.IS_EMPTY, _("File extension is not specified."))]
    
    status_messages = []
    
    if re.search(cls._INVALID_CHARS_PATTERN, file_ext):
      status_messages.append(
        (cls.HAS_INVALID_CHARS,
         _("File extension contains invalid characters.")))
    
    if file_ext.endswith(" ") or file_ext.endswith("."):
      status_messages.append(
        (cls.ENDS_WITH_SPACES_OR_PERIODS,
         _("File extension cannot end with spaces or periods.")))
    
    is_valid = not status_messages
    return is_valid, status_messages
  
  @classmethod
  def validate(cls, file_ext):
    file_ext = (
      re.sub(cls._INVALID_CHARS_PATTERN, "", file_ext)
        .rstrip(" ")
        .rstrip(".")
    )
    
    return file_ext
