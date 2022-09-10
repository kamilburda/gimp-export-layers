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

"""Functions to modify strings or file paths to make them unique."""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import os

__all__ = [
  'uniquify_string',
  'uniquify_filepath',
  'uniquify_string_generic',
]


def uniquify_string(
      str_, existing_strings, uniquifier_position=None, uniquifier_generator=None):
  """
  If string `str_` is in the `existing_strings` list, return a unique string
  by inserting a 'uniquifier' (a string that makes the whole input string
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
    return '{}{}{}'.format(
      str_[0:uniquifier_position], next(uniquifier_generator), str_[uniquifier_position:])

  def _generate_unique_number():
    i = 1
    while True:
      yield ' ({})'.format(i)
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
