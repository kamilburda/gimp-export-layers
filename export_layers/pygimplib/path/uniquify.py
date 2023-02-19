# -*- coding: utf-8 -*-

"""Functions to modify strings or file paths to make them unique."""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import os

__all__ = [
  'uniquify_string',
  'uniquify_filepath',
  'uniquify_string_generic',
]


def uniquify_string(str_, existing_strings, position=None, generator=None):
  """
  If string `str_` is in the `existing_strings` list, return a unique string
  by inserting a substring that makes `str_` unique. Otherwise, return original
  `str_`.
  
  Parameters:
  
  * `str_` - String to uniquify.
  
  * `existing_strings` - List of strings to compare against `str_`.
  
  * `position` - See the `position` parameter in `uniquify_string_generic()` for
    more information.
  
  * `generator` - See the `generator` parameter in `uniquify_string_generic()`.
  """
  return uniquify_string_generic(
    str_,
    lambda str_param: str_param not in existing_strings,
    position,
    generator)
  

def uniquify_filepath(filepath, position=None, generator=None):
  """
  If a file at the specified path already exists, return a unique file path.
  
  Parameters:
  
  * `filepath` - File path to uniquify.
  
  * `position` - See the `position` parameter in `uniquify_string_generic()` for
    more information.
  
  * `generator` - See the `generator` parameter in `uniquify_string_generic()`.
  """
  return uniquify_string_generic(
    filepath,
    lambda filepath_param: not os.path.exists(filepath_param),
    position,
    generator)


def uniquify_string_generic(str_, is_unique_func, position=None, generator=None):
  """
  If string `str_` is not unique according to `is_unique_func`, return a unique
  string by inserting a substring that makes `str_` unique. Otherwise, return
  original `str_`.
  
  Parameters:
  
  * `str_` - String to uniquify.
  
  * `is_unique_func` - Function that returns `True` if `str_` is unique, `False`
    otherwise. `is_unique_func` must contain `str_` as its only parameter.
  
  * `position` - Position (index) where the substring is inserted.
    If the position is `None`, insert the substring at the end of `str_` (i.e.
    append it).
  
  * `generator` - A generator object that generates a unique substring in each
    iteration. If `None`, the generator yields default strings - " (1)", " (2)",
    etc.
    
    An example of a custom generator:

      def _generate_unique_copy_string():
        substr = " - copy"
        yield substr
        
        substr = " - another copy"
        yield substr
         
        i = 2
        while True:
          yield "{} {}".format(substr, i)
          i += 1
    
    This generator yields " - copy", " - another copy", " - another copy 2",
    etc.
  """
  
  def _get_uniquified_string(generator):
    return '{}{}{}'.format(
      str_[0:position], next(generator), str_[position:])

  def _generate_unique_number():
    i = 1
    while True:
      yield ' ({})'.format(i)
      i += 1
  
  if is_unique_func(str_):
    return str_
  
  if position is None:
    position = len(str_)
  
  if generator is None:
    generator = _generate_unique_number()
  
  uniq_str = _get_uniquified_string(generator)
  while not is_unique_func(uniq_str):
    uniq_str = _get_uniquified_string(generator)
  
  return uniq_str
