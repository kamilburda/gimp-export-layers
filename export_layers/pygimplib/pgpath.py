# -*- coding: utf-8 -*-
#
# Copyright (C) 2014-2019 khalim19
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
This module contains functions dealing with strings, paths, files and
directories.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *
import future.utils

import abc
import collections
import inspect
import os
import re
import types

from . import pgfileformats
from . import pgutils

from ._pgpath_dirs import *


def uniquify_string(
      str_, existing_strings, uniquifier_position=None, uniquifier_generator=None):
  """
  If string `str_` is in the `existing_strings` list, return a unique string
  by inserting a "uniquifier" (a string that makes the whole input string
  unique) in `str_`. Otherwise, return `str_`.
  
  Parameters:
  
  * `str_` - String to uniquify.
  
  * `existing_strings` - List of strings to compare against `str_`.
  
  * `uniquifier_position` - See the `uniquifier_position` parameter in
    `uniquify_string_generic()` for more information.
  
  * `uniquifier_generator` - See the `uniquifier_generator` parameter in
    `uniquify_string_generic()`.
  """
  return uniquify_string_generic(
    str_,
    lambda str_param: str_param not in existing_strings,
    uniquifier_position,
    uniquifier_generator)
  

def uniquify_filepath(filepath, uniquifier_position=None, uniquifier_generator=None):
  """
  If a file at the specified path already exists, return a unique file path.
  
  Parameters:
  
  * `filepath` - File path to uniquify.
  
  * `uniquifier_position` - See the `uniquifier_position` parameter in
    `uniquify_string_generic()` for more information.
  
  * `uniquifier_generator` - See the `uniquifier_generator` parameter in
    `uniquify_string_generic()`.
  """
  return uniquify_string_generic(
    filepath,
    lambda filepath_param: not os.path.exists(filepath_param),
    uniquifier_position,
    uniquifier_generator)


def uniquify_string_generic(
      str_, is_unique_func, uniquifier_position=None, uniquifier_generator=None):
  """
  If string `str_` is not unique according to `is_unique_func`, return a unique
  string by inserting a "uniquifier" (a string that makes the whole input string
  unique) in `str_`. Otherwise, return `str_`.
  
  Parameters:
  
  * `str_` - String to uniquify.
  
  * `is_unique_func` - Function that returns `True` if `str_` is unique, `False`
    otherwise. `is_unique_func` must contain `str_` as its only parameter.
  
  * `uniquifier_position` - Position (index) where the uniquifier is inserted.
    If the position is `None`, insert the uniquifier at the end of `str_` (i.e.
    append it).
  
  * `uniquifier_generator` - A generator object that generates a unique string
    (uniquifier) in each iteration. If `None`, the generator yields default
    strings - " (1)", " (2)", etc.
    
    An example of a custom uniquifier generator:

      def _generate_unique_copy_string():
        uniquifier = " - copy"
        yield uniquifier
        
        uniquifier = " - another copy"
        yield uniquifier
         
        i = 2
        while True:
          yield "{} {}".format(uniquifier, i)
          i += 1
    
    This generator yields " - copy", " - another copy", " - another copy 2",
    etc.
  """
  
  def _get_uniquified_string(uniquifier_generator):
    return "{}{}{}".format(
      str_[0:uniquifier_position], next(uniquifier_generator), str_[uniquifier_position:])

  def _generate_unique_number():
    i = 1
    while True:
      yield " ({})".format(i)
      i += 1
  
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


def get_file_extension(filename):
  """
  Get file extension from `filename` in lowercase.
  
  If `filename` has no file extension, return an empty string.
  
  If `filename` has multiple periods, it is checked against
  `pgfileformats.file_formats_dict` for a matching file extension containing
  periods. If there is no such extension, return the substring after the last
  period.
  """
  filename_lowercase = filename.lower()
  
  if "." not in filename_lowercase:
    return ""
  
  file_extension = filename_lowercase
  
  while file_extension:
    next_period_index = file_extension.find(".")
    if next_period_index == -1:
      return file_extension
    
    file_extension = file_extension[next_period_index + 1:]
    if file_extension in pgfileformats.file_formats_dict:
      return file_extension
  
  return ""


def get_filename_with_new_file_extension(
      filename, file_extension, keep_extra_trailing_periods=False):
  """
  Return a new filename with the specified new file extension.
  
  To remove the file extension from `filename`, pass an empty string, `None`, or
  a period (".").
  
  If `keep_extra_trailing_periods` is `True`, do not remove duplicate periods
  before the file extension.
  """
  filename_extension = get_file_extension(filename)
  
  if filename_extension:
    filename_without_extension = filename[0:len(filename) - len(filename_extension) - 1]
  else:
    filename_without_extension = filename
    if filename_without_extension.endswith(".") and not keep_extra_trailing_periods:
      filename_without_extension = filename_without_extension.rstrip(".")
  
  if file_extension and file_extension.startswith("."):
    file_extension = file_extension.lstrip(".")
  
  if file_extension:
    file_extension = file_extension.lower()
    new_filename = ".".join((filename_without_extension, file_extension))
  else:
    new_filename = filename_without_extension
  
  return new_filename


#===============================================================================


class StringPatternGenerator(object):
  """
  This class generates strings by a given pattern and optionally fields acting
  as variables in the pattern.
  
  To generate a string, create a new instance of `StringPatternGenerator` with
  the desired pattern and fields and then call `generate()`.
  
  `fields` is a list of `(field regex, function)` tuples inserted into the
  pattern. Fields in the pattern are enclosed in square brackets (`"[field]"`).
  To insert literal square brackets, double the characters (`"[["`, `"]]"`).
  
  Field arguments are separated by commas (`","`). The number of arguments
  depends on the function in the `fields` dictionary. To insert literal commas
  in field arguments, enclose the arguments in square brackets. To insert square
  brackets in field arguments, enclose the arguments in square brackets and
  double the square brackets (the ones inside the argument, not the enclosing
  ones). If the last argument is enclosed in square brackets, insert a comma
  after the argument.
  
  Examples:
  
  Suppose `fields` contains a field named `"date"` returning the current date
  (requiring a date format as a parameter).
  
  * "image" -> "image", "image", ...
  * "image_[date, %Y-%m-%d]" -> "image_2016-07-16", ...
  * "[[image]]" -> "[image]", ...
  * "[date, [[[%Y,%m,%d]]] ]" -> "[2016,07,16]", ...
  """
  
  def __init__(self, pattern, fields=None):
    self._pattern = pattern
    self._fields = collections.OrderedDict(fields if fields is not None else [])
    
    self._pattern_parts, unused_, self._parsed_fields_and_matching_regexes = (
      self._parse_pattern(self._pattern, self._fields))
  
  def generate(self):
    """
    Generate string from the pattern and fields given in the instance of this
    class. For more information about string generation, refer to the class
    documentation.
    """
    pattern_parts = []
    for part in self._pattern_parts:
      if not self._is_field(part):
        pattern_parts.append(part)
      else:
        pattern_parts.append(self._process_field(part))
    
    return "".join(pattern_parts)
  
  @classmethod
  def get_field_at_position(cls, pattern, position):
    """
    If the pattern contains a field at the given character position (starting
    from 0), return the field name, otherwise return `None`.
    """
    unused_, parsed_fields, unused_ = cls._parse_pattern(pattern, fields=None)
    
    for parsed_field in parsed_fields:
      indices = parsed_field[3]
      if indices[0] <= position <= indices[1]:
        return parsed_field[0]
    
    return None
  
  @classmethod
  def _parse_pattern(cls, pattern, fields=None):
    index = 0
    start_of_field_index = 0
    last_constant_substring_index = 0
    field_depth = 0
    
    # item: pair of (field regex, field arguments) or string
    pattern_parts = []
    # item: (field regex, field arguments, raw field string,
    #        (field start index, field end index))
    parsed_fields = []
    # key: parsed field
    # value: matching field regex
    parsed_fields_and_matching_regexes = {}
    
    def _add_pattern_part(end_index=None):
      start_index = max(last_constant_substring_index, start_of_field_index)
      if end_index is not None:
        pattern_parts.append(pattern[start_index:end_index])
      else:
        pattern_parts.append(pattern[start_index:])
    
    while index < len(pattern):
      if pattern[index] == "[":
        is_escaped = cls._is_field_symbol_escaped(pattern, index, "[")
        if field_depth == 0 and is_escaped:
          _add_pattern_part(index)
          pattern_parts.append("[")
          last_constant_substring_index = index + 2
          index += 2
          continue
        elif field_depth == 0 and not is_escaped:
          _add_pattern_part(index)
          start_of_field_index = index
          field_depth += 1
        elif field_depth == 1:
          field_depth += 1
        elif field_depth > 1 and is_escaped:
          index += 2
          continue
        elif field_depth > 1 and not is_escaped:
          field_depth += 1
      elif pattern[index] == "]":
        is_escaped = cls._is_field_symbol_escaped(pattern, index, "]")
        if field_depth == 0 and is_escaped:
          _add_pattern_part(index)
          pattern_parts.append("]")
          last_constant_substring_index = index + 2
          index += 2
          continue
        elif field_depth == 0 and not is_escaped:
          index += 1
          continue
        elif field_depth == 1:
          field_depth -= 1
        elif field_depth > 1 and is_escaped:
          index += 2
          continue
        elif field_depth > 1 and not is_escaped:
          field_depth -= 1
          index += 1
          continue
        
        parsed_field_str = pattern[start_of_field_index + 1:index]
        parsed_field = (
          list(cls._parse_field(parsed_field_str))
          + [parsed_field_str]
          + [(start_of_field_index + 1, index)])
        
        if fields is not None:
          matching_field_regex = (
            cls._get_first_matching_field_regex(parsed_field[0], fields))
        else:
          matching_field_regex = None
        
        if (fields is None
            or (matching_field_regex is not None
                and cls._is_field_valid(parsed_field, matching_field_regex, fields))):
          pattern_parts.append(parsed_field)
          parsed_fields.append(parsed_field)
          parsed_fields_and_matching_regexes[parsed_field[0]] = matching_field_regex
        else:
          _add_pattern_part(index + 1)
        
        last_constant_substring_index = index + 1
      
      index += 1
    
    _add_pattern_part()
    
    return pattern_parts, parsed_fields, parsed_fields_and_matching_regexes
  
  @classmethod
  def _parse_field(cls, field_str):
    field_name_end_index = field_str.find(",")
    if field_name_end_index == -1:
      return field_str.strip(), []
    
    field_name = field_str[:field_name_end_index].strip()
    field_args_str = field_str[field_name_end_index + 1:]
    # Make parsing simpler without having to post-process the last argument
    # outside the main loop.
    field_args_str += ","
    
    is_in_field_arg = False
    last_field_arg_end_index = 0
    index = 0
    field_args = []
    
    def _process_field_args(field_args):
      processed_field_args = []
      for field_arg in field_args:
        processed_arg = field_arg.strip()
        if not processed_arg:
          continue
        
        if processed_arg[0] == "[" and processed_arg[-1] == "]":
          processed_arg = processed_arg[1:-1]
        processed_arg = processed_arg.replace("[[", "[").replace("]]", "]")
        
        processed_field_args.append(processed_arg)
      
      return processed_field_args
    
    while index < len(field_args_str):
      if field_args_str[index] == ",":
        if is_in_field_arg:
          index += 1
          continue
        else:
          field_args.append(field_args_str[last_field_arg_end_index:index])
          last_field_arg_end_index = index + 1
      elif field_args_str[index] == "[":
        if cls._is_field_symbol_escaped(field_args_str, index, "["):
          index += 2
          continue
        else:
          is_in_field_arg = True
      elif field_args_str[index] == "]":
        if cls._is_field_symbol_escaped(field_args_str, index, "]"):
          index += 2
          continue
        else:
          is_in_field_arg = False
      
      index += 1
    
    return field_name, _process_field_args(field_args)
  
  @classmethod
  def _is_field_valid(cls, parsed_field, field_regex, fields):
    field_func = fields[field_regex]
    
    argspec = inspect.getargspec(field_func)
    
    if argspec.keywords:
      raise ValueError(
        "{}: field functions with variable keyword arguments (**kwargs) "
        "are not supported".format(field_func.__name__))
    
    if not argspec.varargs:
      num_defaults = len(argspec.defaults) if argspec.defaults is not None else 0
      # The field value should always be the first argument, hence `- 1`.
      num_required_args = len(argspec.args) - num_defaults - 1
      
      if pgutils.is_bound_method(field_func):
        num_required_args -= 1
      
      if (len(parsed_field[1]) < num_required_args
          or len(parsed_field[1]) > len(argspec.args)):
        return False
    
    return True
  
  @staticmethod
  def _get_first_matching_field_regex(parsed_field_str, fields):
    return next(
      (field_regex for field_regex in fields if re.search(field_regex, parsed_field_str)),
      None)
  
  @staticmethod
  def _is_field_symbol_escaped(pattern, index, symbol):
    return index + 1 < len(pattern) and pattern[index + 1] == symbol
  
  @staticmethod
  def _is_field(pattern_part):
    return not isinstance(pattern_part, types.StringTypes)
  
  def _process_field(self, field):
    field_func = self._fields[self._parsed_fields_and_matching_regexes[field[0]]]
    
    try:
      return_value = field_func(field[0], *field[1])
    except Exception:
      return "[{}]".format(field[2])
    else:
      return str(return_value)


#===============================================================================


def N_(str_):
  return str_


class FileValidatorErrorStatuses(object):
  
  ERROR_STATUSES = (
    IS_EMPTY,
    HAS_INVALID_CHARS,
    DRIVE_HAS_INVALID_CHARS,
    HAS_TRAILING_SPACES,
    HAS_TRAILING_PERIOD,
    HAS_INVALID_NAMES,
    EXISTS_BUT_IS_NOT_DIR
  ) = list(range(7))


class StringValidator(future.utils.with_metaclass(abc.ABCMeta, object)):
  """
  This class is an interface to validate strings.
  
  Strings are assumed to be Unicode strings.
  
  This class does not specify what strings are valid (whether they contain
  invalid characters, substrings, etc.). This should be handled by subclasses.
  """
  
  ERROR_STATUSES_MESSAGES = {}
  
  @classmethod
  def is_valid(cls, string_to_check):
    """
    Check if the specified string is valid.
    
    Returns:
      
      * `is_valid` - `True` if the string is valid, `False` otherwise.
      
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
  def _get_status(cls, status):
    return (status, _(cls.ERROR_STATUSES_MESSAGES[status]))


class FilenameValidator(StringValidator):
  
  r"""
  This class is used to validate filenames (i.e. basenames).
  
  In this class, filenames are considered valid if they:
    
    * do not contain control characters with ordinal numbers 0-31 and 127-159
    
    * do not contain the following special characters:
      
        <>:"/\|?*
    
    * do not start or end with spaces
    
    * do not end with one or more periods
    
    * do not have invalid names according to the naming conventions for the
      Windows platform:
      
      http://msdn.microsoft.com/en-us/library/aa365247%28VS.85%29
    
    * are not empty or `None`
  """
  
  _INVALID_CHARS_PATTERN = r"[\x00-\x1f\x7f-\x9f<>:\"\\/|?*]"
  
  # Invalid names for the Windows platform. Taken from:
  # http://msdn.microsoft.com/en-us/library/windows/desktop/aa365247%28v=vs.85%29.aspx
  _INVALID_NAMES = {
    "CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "COM5", "COM6",
    "COM7", "COM8", "COM9", "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6",
    "LPT7", "LPT8", "LPT9"}
  
  ERROR_STATUSES_MESSAGES = {
    FileValidatorErrorStatuses.IS_EMPTY: N_("Filename is not specified."),
    FileValidatorErrorStatuses.HAS_INVALID_CHARS: N_(
      "Filename contains invalid characters."),
    FileValidatorErrorStatuses.HAS_TRAILING_SPACES: N_(
      "Filename cannot end with spaces."),
    FileValidatorErrorStatuses.HAS_TRAILING_PERIOD: N_(
      "Filename cannot end with a period."),
    FileValidatorErrorStatuses.HAS_INVALID_NAMES: N_(
      '"{}" is a reserved name that cannot be used in filenames.\n')}
  
  @classmethod
  def is_valid(cls, filename):
    """
    Check whether the specified filename is valid.
    
    See the class description for details about when the filename is valid.
    """
    if not filename or filename is None:
      return False, [cls._get_status(FileValidatorErrorStatuses.IS_EMPTY)]
    
    status_messages = []
    
    if re.search(cls._INVALID_CHARS_PATTERN, filename):
      status_messages.append(
        cls._get_status(FileValidatorErrorStatuses.HAS_INVALID_CHARS))
    
    if filename.endswith(" "):
      status_messages.append(
        cls._get_status(FileValidatorErrorStatuses.HAS_TRAILING_SPACES))
    
    if filename.endswith("."):
      status_messages.append(
        cls._get_status(FileValidatorErrorStatuses.HAS_TRAILING_PERIOD))
    
    root, unused_ = os.path.splitext(filename)
    if root.upper() in cls._INVALID_NAMES:
      status_messages.append(
        cls._get_status(FileValidatorErrorStatuses.HAS_INVALID_NAMES))
    
    is_valid = not status_messages
    return is_valid, status_messages
  
  @classmethod
  def validate(cls, filename):
    """
    Validate the specified filename by removing invalid characters.
    
    If the filename is one of the reserved names for the Windows platform,
    append `" (1)"` to the filename (before the file extension if it has one).
    
    If the filename is truncated to an empty string, return `"Untitled"`.
    """
    filename = re.sub(cls._INVALID_CHARS_PATTERN, "", filename).strip(" ").rstrip(".")
    
    root, ext = os.path.splitext(filename)
    # For reserved names, the comparison must be case-insensitive (because
    # Windows has case-insensitive filenames).
    if root.upper() in cls._INVALID_NAMES:
      filename = root + " (1)" + ext
    
    if not filename:
      filename = _("Untitled")
    
    return filename


class FilepathValidator(StringValidator):
  """
  This class is used to validate file paths (relative or absolute).
  
  The same validation rules that apply to filenames in the `FilenameValidator`
  class apply to file paths in this class, with the following exceptions:
    
    * `/` and `\` characters are allowed
    
    * `:` character is allowed to appear at the root level only (as a part of a
      drive letter, e.g. `"C:\"`)
  """
  
  _INVALID_CHARS = r"\x00-\x1f\x7f-\x9f<>\"|?*"
  _VALID_DRIVE_CHARS = r":"
  
  _INVALID_CHARS_PATTERN_WITHOUT_DRIVE = "[" + _INVALID_CHARS + "]"
  _INVALID_CHARS_PATTERN = "[" + _INVALID_CHARS + _VALID_DRIVE_CHARS + "]"
  
  _INVALID_NAMES = FilenameValidator._INVALID_NAMES
  
  ERROR_STATUSES_MESSAGES = {
    FileValidatorErrorStatuses.IS_EMPTY: N_("File path is not specified."),
    FileValidatorErrorStatuses.DRIVE_HAS_INVALID_CHARS: N_(
      "Drive letter contains invalid characters."),
    FileValidatorErrorStatuses.HAS_INVALID_CHARS: N_(
      "File path contains invalid characters."),
    FileValidatorErrorStatuses.HAS_TRAILING_SPACES: N_(
      "Path components in the file path cannot end with spaces."),
    FileValidatorErrorStatuses.HAS_TRAILING_PERIOD: N_(
      "Path components in the file path cannot end with a period."),
    FileValidatorErrorStatuses.HAS_INVALID_NAMES: N_(
      '"{}" is a reserved name that cannot be used in file paths.\n')}
  
  @classmethod
  def is_valid(cls, filepath):
    if not filepath or filepath is None:
      return False, [cls._get_status(FileValidatorErrorStatuses.IS_EMPTY)]
    
    status_messages = []
    statuses = set()
    invalid_names_status_message = ""
    
    filepath = os.path.normpath(filepath)
    
    drive, path = os.path.splitdrive(filepath)
    
    if drive:
      if re.search(cls._INVALID_CHARS_PATTERN_WITHOUT_DRIVE, drive):
        status_messages.append(
          cls._get_status(FileValidatorErrorStatuses.DRIVE_HAS_INVALID_CHARS))
    
    path_components = split_path(path)
    for path_component in path_components:
      if re.search(cls._INVALID_CHARS_PATTERN, path_component):
        statuses.add(FileValidatorErrorStatuses.HAS_INVALID_CHARS)
      if path_component.endswith(" "):
        statuses.add(FileValidatorErrorStatuses.HAS_TRAILING_SPACES)
      if path_component.endswith("."):
        statuses.add(FileValidatorErrorStatuses.HAS_TRAILING_PERIOD)
      
      root, unused_ = os.path.splitext(path_component)
      if root.upper() in cls._INVALID_NAMES:
        statuses.add(FileValidatorErrorStatuses.HAS_INVALID_NAMES)
        invalid_names_status_message += (
          cls.ERROR_STATUSES_MESSAGES[
            FileValidatorErrorStatuses.HAS_INVALID_NAMES].format(root))
    
    if FileValidatorErrorStatuses.HAS_INVALID_CHARS in statuses:
      status_messages.append(
        cls._get_status(FileValidatorErrorStatuses.HAS_INVALID_CHARS))
    if FileValidatorErrorStatuses.HAS_TRAILING_SPACES in statuses:
      status_messages.append(
        cls._get_status(FileValidatorErrorStatuses.HAS_TRAILING_SPACES))
    if FileValidatorErrorStatuses.HAS_TRAILING_PERIOD in statuses:
      status_messages.append(
        cls._get_status(FileValidatorErrorStatuses.HAS_TRAILING_PERIOD))
    if FileValidatorErrorStatuses.HAS_INVALID_NAMES in statuses:
      invalid_names_status_message = invalid_names_status_message.rstrip("\n")
      status_messages.append(
        (FileValidatorErrorStatuses.HAS_INVALID_NAMES, invalid_names_status_message))
    
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


class DirpathValidator(FilepathValidator):
  """
  This class is used to validate directory paths (relative or absolute).
  
  The same validation rules that apply to file paths in the `FilepathValidator`
  class apply to directory paths in this class, with the following additions:
  
    * the specified path must be a directory path
  """
  
  ERROR_STATUSES_MESSAGES = {
    FileValidatorErrorStatuses.IS_EMPTY: N_("Directory path is not specified."),
    FileValidatorErrorStatuses.DRIVE_HAS_INVALID_CHARS: N_(
      "Drive letter contains invalid characters."),
    FileValidatorErrorStatuses.HAS_INVALID_CHARS: N_(
      "Directory path contains invalid characters."),
    FileValidatorErrorStatuses.HAS_TRAILING_SPACES: N_(
      "Path components in the directory path cannot end with spaces."),
    FileValidatorErrorStatuses.HAS_TRAILING_PERIOD: N_(
      "Path components in the directory path cannot end with a period."),
    FileValidatorErrorStatuses.HAS_INVALID_NAMES: N_(
      '"{}" is a reserved name that cannot be used in directory paths.\n'),
    FileValidatorErrorStatuses.EXISTS_BUT_IS_NOT_DIR: N_(
      "Specified path is not a directory path.")}
  
  @classmethod
  def is_valid(cls, dirpath):
    unused_, status_messages = super().is_valid(dirpath)
    
    if os.path.exists(dirpath) and not os.path.isdir(dirpath):
      status_messages.append(
        cls._get_status(FileValidatorErrorStatuses.EXISTS_BUT_IS_NOT_DIR))
    
    is_valid = not status_messages
    return is_valid, status_messages
  

class FileExtensionValidator(StringValidator):
  
  r"""
  This class is used to validate file extensions.
  
  In this class, file extensions are considered valid if they:
    
    * do not contain control characters with ordinal numbers 0-31 and 127-159
    
    * do not contain the following special characters:
      
        <>:"/\|?*
    
    * do not end with spaces or periods
  """
  
  _INVALID_CHARS_PATTERN = FilenameValidator._INVALID_CHARS_PATTERN
  
  ERROR_STATUSES_MESSAGES = {
    FileValidatorErrorStatuses.IS_EMPTY: N_("File extension is not specified."),
    FileValidatorErrorStatuses.HAS_INVALID_CHARS: N_(
      "File extension contains invalid characters."),
    FileValidatorErrorStatuses.HAS_TRAILING_SPACES: N_(
      "File extension cannot end with spaces."),
    FileValidatorErrorStatuses.HAS_TRAILING_PERIOD: N_(
      "File extension cannot end with a period.")}
  
  @classmethod
  def is_valid(cls, file_extension):
    if not file_extension or file_extension is None:
      return False, [cls._get_status(FileValidatorErrorStatuses.IS_EMPTY)]
    
    status_messages = []
    
    if re.search(cls._INVALID_CHARS_PATTERN, file_extension):
      status_messages.append(
        cls._get_status(FileValidatorErrorStatuses.HAS_INVALID_CHARS))
    
    if file_extension.endswith(" "):
      status_messages.append(
        cls._get_status(FileValidatorErrorStatuses.HAS_TRAILING_SPACES))
      
    if file_extension.endswith("."):
      status_messages.append(
        cls._get_status(FileValidatorErrorStatuses.HAS_TRAILING_PERIOD))
    
    is_valid = not status_messages
    return is_valid, status_messages
  
  @classmethod
  def validate(cls, file_extension):
    return re.sub(cls._INVALID_CHARS_PATTERN, "", file_extension).rstrip(" ").rstrip(".")
