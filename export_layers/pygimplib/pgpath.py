#-------------------------------------------------------------------------------
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
#-------------------------------------------------------------------------------

"""
This module contains functions dealing with strings, filenames, files and
directories.
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


def uniquify_string(str_, existing_strings, uniquifier_position=None,
                    uniquifier_generator=None):
  """
  If string `str_` is in the `existing_strings` list, return a unique string
  by inserting a "uniquifier" (a string that makes the whole input string
  unique) in `str_`. Otherwise, return `str_`.
  
  Parameters:
  
  * `str_` - String to uniquify.
  
  * `existing_strings` - List of strings to compare against `str_`.
  
  * `uniquifier_position` - See `uniquify_string_generic.uniquifier_position`.
  
  * `uniquifier_generator` - See `uniquify_string_generic.uniquifier_generator`.
  """
  
  return uniquify_string_generic(str_,
                                 lambda str_param: str_param not in existing_strings,
                                 uniquifier_position, uniquifier_generator)
  

def uniquify_filename(filename, uniquifier_position=None, uniquifier_generator=None):
  """
  If a file with the specified filename already exists, return a unique filename.
  
  Parameters:
  
  * `filename` - Filename to uniquify.
  
  * `uniquifier_position` - See `uniquify_string_generic.uniquifier_position`.
  
  * `uniquifier_generator` - See `uniquify_string_generic.uniquifier_generator`.
  """
  
  return uniquify_string_generic(filename,
                                 lambda filename_param: not os.path.exists(filename_param),
                                 uniquifier_position, uniquifier_generator)

def uniquify_string_generic(str_, is_unique_func, uniquifier_position=None,
                            uniquifier_generator=None):
  """
  If string `str_` is not unique according to `is_unique_func`, return a unique
  string by inserting a "uniquifier" (a string that makes the whole input string
  unique) in `str_`. Otherwise, return `str_`.
  
  Parameters:
  
  * `str_` - String to uniquify.
  
  * `is_unique_func` - Function that returns True if `str_` is unique, False
    otherwise. `is_unique_func` must contain `str_` as its only parameter.
  
  * `uniquifier_position` - Position (index) where the uniquifier is inserted.
    If the position is None, insert the uniquifier at the end of `str_` (i.e.
    append it).
  
  * `uniquifier_generator` - A generator object that generates a unique string
    (uniquifier) in each iteration. If None, the generator yields default
    strings - " (1)", " (2)", etc.
    
    An example of a custom uniquifier generator:

      def _generate_unique_copy_string():
        uniquifier = " - copy"
        yield uniquifier
        
        uniquifier = " - another copy"
        yield uniquifier
         
        i = 2
        while True:
          yield "{0} {1}".format(uniquifier, i)
          i += 1
    
    This generator yields " - copy", " - another copy", " - another copy 2",
    etc.
  """
  
  def _get_uniquified_string(uniquifier_generator):
    return "{0}{1}{2}".format(str_[0:uniquifier_position],
                              next(uniquifier_generator),
                              str_[uniquifier_position:])
  
  if is_unique_func(str_):
    return str_
  
  if uniquifier_position is None:
    uniquifier_position = len(str_)
  
  if uniquifier_generator is None:
    uniquifier_generator = _generate_unique_number()
  
  uniq_str = _get_uniquified_string(uniquifier_generator)
  while not is_unique_func(uniq_str):
    uniq_str = _get_uniquified_string(uniquifier_generator)
  
  return uniq_str


def _generate_unique_number():
  i = 1
  while True:
    yield " ({0})".format(i)
    i += 1


#===============================================================================


def get_file_extension(str_, to_lowercase=True):
  """
  Return the file extension from the specified string in lower case and strip
  the leading period. If the string has no file extension, return empty string.
  
  A string has file extension if it contains a "." character and a substring
  following this character.
  
  Paramters:
  
  * `to_lowercase` - If True, convert the file extension to lowercase.
  """
  
  file_ext = os.path.splitext(str_)[1].lstrip(".")
  
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
  """
  
  __metaclass__ = abc.ABCMeta
  
  ERROR_STATUSES = ()
  ERROR_STATUSES_MESSAGES = {}
  
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
  
  @classmethod
  def _status_tuple(cls, status):
    return (status, cls.ERROR_STATUSES_MESSAGES[status])


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
  
  ERROR_STATUSES_MESSAGES = {
    IS_EMPTY: _("Filename is not specified."),
    HAS_INVALID_CHARS: _("Filename contains invalid characters."),
    HAS_SPACES: _("Filename cannot start or end with spaces."),
    HAS_TRAILING_PERIOD: _("Filename cannot end with a period."),
    HAS_INVALID_NAMES: _("\"{0}\" is a reserved name that cannot be used in filenames.\n"),
  }
  
  @classmethod
  def is_valid(cls, filename):
    """
    Check whether the specified filename is valid.
    
    See the class description for details about when the filename is valid.
    """
    
    if not filename or filename is None:
      return False, [cls._status_tuple(cls.IS_EMPTY)]
    
    status_messages = []
    
    if re.search(cls._INVALID_CHARS_PATTERN, filename):
      status_messages.append(cls._status_tuple(cls.HAS_INVALID_CHARS))
    
    if filename.startswith(" ") or filename.endswith(" "):
      status_messages.append(cls._status_tuple(cls.HAS_SPACES))
    
    if filename.endswith("."):
      status_messages.append(cls._status_tuple(cls.HAS_TRAILING_PERIOD))
    
    root, unused_ = os.path.splitext(filename)
    if root.upper() in cls._INVALID_NAMES:
      status_messages.append(cls._status_tuple(cls.HAS_INVALID_NAMES))
    
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
    
    * "/" and "\" characters are allowed
    
    * ":" character is allowed to appear at the root level only (as a part of a
      drive letter, e.g. "C:\")
  """
  
  _INVALID_CHARS = r"\x00-\x1f\x7f-\x9f<>\"|?*"
  _VALID_DRIVE_CHARS = r":"
  
  _INVALID_CHARS_PATTERN_WITHOUT_DRIVE = "[" + _INVALID_CHARS + "]"
  _INVALID_CHARS_PATTERN = "[" + _INVALID_CHARS + _VALID_DRIVE_CHARS + "]"
  
  _INVALID_NAMES = FilenameValidator._INVALID_NAMES
  
  ERROR_STATUSES = (
     IS_EMPTY, DRIVE_HAS_INVALID_CHARS, HAS_INVALID_CHARS,
     HAS_SPACES, HAS_TRAILING_PERIOD, HAS_INVALID_NAMES
  ) = (0, 1, 2, 3, 4, 5)
  
  ERROR_STATUSES_MESSAGES = {
    IS_EMPTY: _("File path is not specified."),
    DRIVE_HAS_INVALID_CHARS: _("Drive letter contains invalid characters."),
    HAS_INVALID_CHARS: _("File path contains invalid characters."),
    HAS_SPACES: _("Path components in the file path cannot start or end with spaces."),
    HAS_TRAILING_PERIOD: _("Path components in the file path cannot end with a period."),
    HAS_INVALID_NAMES: _("\"{0}\" is a reserved name that cannot be used in file paths.\n"),
  }
  
  @classmethod
  def is_valid(cls, filepath):
    if not filepath or filepath is None:
      return False, [cls._status_tuple(cls.IS_EMPTY)]
    
    status_messages = []
    statuses = set()
    invalid_names_status_message = ""
    
    filepath = os.path.normpath(filepath)
    
    drive, path = os.path.splitdrive(filepath)
    
    if drive:
      if re.search(cls._INVALID_CHARS_PATTERN_WITHOUT_DRIVE, drive):
        status_messages.append(cls._status_tuple(cls.DRIVE_HAS_INVALID_CHARS))
    
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
          cls.ERROR_STATUSES_MESSAGES[cls.HAS_INVALID_NAMES].format(root))
    
    if cls.HAS_INVALID_CHARS in statuses:
      status_messages.append(cls._status_tuple(cls.HAS_INVALID_CHARS))
    if cls.HAS_SPACES in statuses:
      status_messages.append(cls._status_tuple(cls.HAS_SPACES))
    if cls.HAS_TRAILING_PERIOD in statuses:
      status_messages.append(cls._status_tuple(cls.HAS_TRAILING_PERIOD))
    if cls.HAS_INVALID_NAMES in statuses:
      invalid_names_status_message = invalid_names_status_message.rstrip("\n")
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


class DirectoryPathValidator(FilePathValidator):
   
  """
  This class is used to validate directory paths (relative or absolute).
  
  The same validation rules that apply to file paths in the `FilePathValidator`
  class apply to directory paths in this class, with the following additions:
  
    * the specified path must be a directory
  """
  
  ERROR_STATUSES = (
     IS_EMPTY, DRIVE_HAS_INVALID_CHARS, HAS_INVALID_CHARS, HAS_SPACES,
     HAS_TRAILING_PERIOD, HAS_INVALID_NAMES, EXISTS_BUT_IS_NOT_DIR
  ) = (0, 1, 2, 3, 4, 5, 6)
  
  ERROR_STATUSES_MESSAGES = {
    IS_EMPTY: _("Directory path is not specified."),
    DRIVE_HAS_INVALID_CHARS: _("Drive letter contains invalid characters."),
    HAS_INVALID_CHARS: _("Directory path contains invalid characters."),
    HAS_SPACES: _("Path components in the directory path cannot start or end with spaces."),
    HAS_TRAILING_PERIOD: _("Path components in the directory path cannot end with a period."),
    HAS_INVALID_NAMES: _("\"{0}\" is a reserved name that cannot be used in directory paths.\n"),
    EXISTS_BUT_IS_NOT_DIR: _("Specified path is not a directory.")
  }
  
  @classmethod
  def is_valid(cls, dirpath):
    unused_, status_messages = super(DirectoryPathValidator, cls).is_valid(dirpath)
    
    if os.path.exists(dirpath) and not os.path.isdir(dirpath):
      status_messages.append(cls._status_tuple(cls.EXISTS_BUT_IS_NOT_DIR))
    
    is_valid = not status_messages
    return is_valid, status_messages
  

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
  
  ERROR_STATUSES_MESSAGES = {
    IS_EMPTY: _("File extension is not specified."),
    HAS_INVALID_CHARS: _("File extension contains invalid characters."),
    ENDS_WITH_SPACES_OR_PERIODS: _("File extension cannot end with spaces or periods.")
  }
  
  @classmethod
  def is_valid(cls, file_ext):
    if not file_ext or file_ext is None:
      return False, [cls._status_tuple(cls.IS_EMPTY)]
    
    status_messages = []
    
    if re.search(cls._INVALID_CHARS_PATTERN, file_ext):
      status_messages.append(cls._status_tuple(cls.HAS_INVALID_CHARS))
    
    if file_ext.endswith(" ") or file_ext.endswith("."):
      status_messages.append(cls._status_tuple(cls.ENDS_WITH_SPACES_OR_PERIODS))
    
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
