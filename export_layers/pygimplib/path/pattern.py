# -*- coding: utf-8 -*-

"""Class providing a string template to substitute fields and their arguments.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import collections
import inspect
import re
import types

__all__ = [
  'StringPattern',
]


class StringPattern(object):
  """
  This class provides string substitution based on fields and their arguments.
  
  Fields are enclosed in square brackets (such as `"[field]"`). Field arguments
  are separated by commas (`","`). The number of arguments depends on the
  substitution function in the `fields` dictionary passed to `__init__`.
  
  To insert literal commas in field arguments, enclose the arguments in square
  brackets. To insert square brackets in field arguments, enclose the arguments
  in square brackets and double the square brackets (the ones inside the
  argument, not the enclosing ones). If the last argument is enclosed in square
  brackets, insert a comma after the argument.
  
  Attributes:
  
  * `pattern` - The original string pattern.
  
  * `pattern_parts` - Parts of `pattern` split into strings (parts of the
    pattern not containing the field) and fields (tuples describing the field).
  
  * `parsed_fields_and_matching_regexes` - Dictionary of
    `(parsed field, first matching field regular expression)` pairs.
  
  Examples:
  
  Suppose `fields` contains a field named `"date"` returning the current date
  (requiring a date format as a parameter).
  
  * "image" -> "image", "image", ...
  * "image_[date, %Y-%m-%d]" -> "image_2016-07-16", ...
  * "[[image]]" -> "[image]", ...
  * "[date, [[[%Y,%m,%d]]] ]" -> "[2016,07,16]", ...
  """
  
  def __init__(self, pattern, fields=None):
    """
    Parameters:
    
    * `pattern` - String containing fields to substitute.
    
    * `fields` - List of `(field regex, function)` tuples. `field regex` matches
      the fields in the pattern and `function` substitutes the field with the
      value returned by the function. The function must always specify at least
      one argument - the field to be substituted.
      
      Any unmatched fields will be silently ignored.
      
      Fields in the pattern are enclosed in square brackets (`"[field]"`). To
      insert literal square brackets, double the characters (`"[["`, `"]]"`).
      
      If `fields` is `None`, no fields in the pattern will be substituted.
    """
    self._pattern = pattern
    self._fields = collections.OrderedDict(fields if fields is not None else [])
    
    self._pattern_parts, unused_, self._parsed_fields_and_matching_regexes = (
      self.parse_pattern(self._pattern, self._fields))
  
  @property
  def pattern(self):
    return self._pattern
  
  @property
  def pattern_parts(self):
    return self._pattern_parts
  
  @property
  def parsed_fields_and_matching_regexes(self):
    return self._parsed_fields_and_matching_regexes
  
  def substitute(self, *additional_args):
    """
    Substitute fields in the string pattern. Return the processed string.
    
    If any substitution function raises an exception, the original string
    pattern is returned.
    
    You may pass additional arguments if `fields` contains functions expecting
    more arguments outside the parsed arguments. These arguments are prepended
    to each function.
    """
    pattern_parts = []
    for part in self._pattern_parts:
      if not self._is_field(part):
        pattern_parts.append(part)
      else:
        pattern_parts.append(self._process_field(part, additional_args))
    
    return ''.join(pattern_parts)
  
  @classmethod
  def get_field_at_position(cls, pattern, position):
    """
    If the pattern contains a field at the given character position (starting
    from 0), return the field name, otherwise return `None`.
    """
    unused_, parsed_fields, unused_ = cls.parse_pattern(pattern, fields=None)
    
    for parsed_field in parsed_fields:
      indices = parsed_field[3]
      if indices[0] <= position <= indices[1]:
        return parsed_field[0]
    
    return None
  
  @classmethod
  def reconstruct_pattern(cls, pattern_parts):
    """
    Reconstruct a string pattern given the parsed `pattern_parts` returned from
    the `pattern_parts` attribute of a `StringPattern` instance.
    
    Raises:
    
    * `ValueError` - A list as an element of `pattern_parts` representing a
      field is empty.
    """
    processed_pattern_parts = []
    
    for part in pattern_parts:
      if not cls._is_field(part):
        processed_pattern_parts.append(part)
      else:
        if not part:
          raise ValueError(
            'lists representing fields must always contain at least one element')
        
        field_components = [part[0]]
        
        if len(part) > 1:
          field_components.extend([str(arg) for arg in part[1]])
        
        processed_pattern_parts.append('[{}]'.format(', '.join(field_components)))
    
    return ''.join(processed_pattern_parts)
  
  @staticmethod
  def get_first_matching_field_regex(parsed_field_str, field_regexes):
    """
    Given the field `parsed_field_str` and the list of field regular
    expressions, return the first matching field regular expression. Return
    `None` if there is no match.
    """
    return next(
      (field_regex for field_regex in field_regexes
       if re.search(field_regex, parsed_field_str)),
      None)
  
  @classmethod
  def parse_pattern(cls, pattern, fields=None):
    """Parses the given string pattern.
    
    Optionally, only the specified fields will be parsed. `fields` is a
    dictionary containing (field regex, function) pairs.
    
    The following tuple is returned:
    * List of parts forming the pattern. The list contains substrings outside
      fields and parsed fields (the second tuple item).
    * List of parsed fields. Each parsed field contains the following elements:
      field name, list of field arguments, the entire field as a string, tuple
      of (field start position in `pattern`, field end position in `pattern`).
    * List of parsed fields and matching field regexes, if `fields` is not
      `None`.
    """
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
      if pattern[index] == '[':
        is_escaped = cls._is_field_symbol_escaped(pattern, index, '[')
        if field_depth == 0 and is_escaped:
          _add_pattern_part(index)
          pattern_parts.append('[')
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
      elif pattern[index] == ']':
        is_escaped = cls._is_field_symbol_escaped(pattern, index, ']')
        if field_depth == 0 and is_escaped:
          _add_pattern_part(index)
          pattern_parts.append(']')
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
          list(cls.parse_field(parsed_field_str))
          + [parsed_field_str]
          + [(start_of_field_index + 1, index)])
        
        if fields is not None:
          matching_field_regex = (
            cls.get_first_matching_field_regex(parsed_field[0], fields))
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
  def parse_field(cls, field_str):
    """Parses the given field as a string.
    
    `field_str` must be specified without `[` and `]` at the beginning and end,
    respectively.
    
    A tuple of (field name, list of field arguments) is returned.
    """
    field_name_end_index = field_str.find(',')
    if field_name_end_index == -1:
      return field_str.strip(), []
    
    field_name = field_str[:field_name_end_index].strip()
    field_args_str = field_str[field_name_end_index + 1:]
    # Make parsing simpler without having to post-process the last argument
    # outside the main loop.
    field_args_str += ','
    
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
        
        if processed_arg[0] == '[' and processed_arg[-1] == ']':
          processed_arg = processed_arg[1:-1]
        processed_arg = processed_arg.replace('[[', '[').replace(']]', ']')
        
        processed_field_args.append(processed_arg)
      
      return processed_field_args
    
    while index < len(field_args_str):
      if field_args_str[index] == ',':
        if is_in_field_arg:
          index += 1
          continue
        else:
          field_args.append(field_args_str[last_field_arg_end_index:index])
          last_field_arg_end_index = index + 1
      elif field_args_str[index] == '[':
        if cls._is_field_symbol_escaped(field_args_str, index, '['):
          index += 2
          continue
        else:
          is_in_field_arg = True
      elif field_args_str[index] == ']':
        if cls._is_field_symbol_escaped(field_args_str, index, ']'):
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
        '{}: field functions with variable keyword arguments (**kwargs)'
        ' are not supported'.format(field_func.__name__))
    
    return True
  
  @staticmethod
  def _is_field_symbol_escaped(pattern, index, symbol):
    return index + 1 < len(pattern) and pattern[index + 1] == symbol
  
  @staticmethod
  def _is_field(pattern_part):
    return not isinstance(pattern_part, types.StringTypes)
  
  def _process_field(self, field, additional_args):
    field_func = self._fields[self._parsed_fields_and_matching_regexes[field[0]]]
    field_func_args = list(additional_args) + [field[0]] + list(field[1])
    
    try:
      return_value = field_func(*field_func_args)
    except Exception:
      return '[{}]'.format(field[2])
    else:
      return str(return_value)
