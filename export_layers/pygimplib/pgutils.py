# -*- coding: utf-8 -*-
#
# Copyright (C) 2014-2018 khalim19
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
This module provides various utility functions and classes, such as an empty
context manager or an empty function.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import inspect

#===============================================================================


class EmptyContext(object):
  
  """
  This class provides an empty context manager that can be used in `with`
  statements in place of a real context manager if a condition is not met:
    
    with context_manager if condition else EmptyContext():
      ...
  
  Or use the `empty_context` global instance:
    
    with context_manager if condition else empty_context:
      ...
  """
  
  def __init__(self, *args, **kwargs):
    pass
  
  def __enter__(self):
    pass
  
  def __exit__(self, *exc_info):
    pass


empty_context = EmptyContext()


#===============================================================================


def empty_func(*args, **kwargs):
  """
  Use this function when an empty function is desired to be passed as a
  parameter.
  
  For example, if you need to serialize a `collections.defaultdict` instance
  (e.g. via `pickle`) returning None for missing keys, you need to use a named
  function instead of `lambda: None`. To emphasize this particular intent, you
  may want to use the alias `return_none_func` instead.
  """
  
  return None


return_none_func = empty_func


def create_empty_func(return_value=None):
  """
  Return an empty function returning the specified return value.
  """
  
  def _empty_func_with_return_value(*args, **kwargs):
    return return_value
  
  return _empty_func_with_return_value


#===============================================================================


def is_bound_method(func):
  """
  Return True if `func` is a bound method, False otherwise.
  """
  
  return hasattr(func, "__self__") and func.__self__ is not None


def stringify_object(object_, name):
  """
  Return a string representation of the specified object, using the specified
  name as a presumed unique identifier of the object. This can be used in the
  `__str__` method to return a more readable string representation than the
  default.
  """
  
  return "<{0} '{1}'>".format(type(object_).__name__, name)


def get_module_root(full_module_name, name_component_to_trim_after):
  """
  Return the part of the full module name (separated by "." characters) from the
  beginning up to the matching module name component including that component.
  
  If `name_component_to_trim_after` does not match any name component from
  `full_module_name`, return `full_module_name`.
  """
  
  module_name_components = full_module_name.split(".")
  
  if name_component_to_trim_after in module_name_components:
    name_component_index = module_name_components.index(name_component_to_trim_after)
    return ".".join(module_name_components[:name_component_index + 1])
  else:
    return full_module_name


def get_current_module_filepath():
  """
  Get the full path name of the module this function is called from.
  """
  
  return inspect.stack()[1][1]
