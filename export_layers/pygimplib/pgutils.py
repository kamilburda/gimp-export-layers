# -*- coding: utf-8 -*-
#
# This file is part of pygimplib.
#
# Copyright (C) 2014-2016 khalim19 <khalim19@gmail.com>
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
This module provides various utility functions and classes, such as an empty
context manager or an empty function.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

str = unicode

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
  function instead of `lambda: None`. To emphasize this particular intent,
  however, you may want to use the alias `return_none_func` instead.
  """
  
  return None


return_none_func = empty_func


def create_empty_func(return_value):
  """
  Return an empty function returning the specified return value.
  """
  
  def return_value_func(*args, **kwargs):
    return return_value
  
  return return_value_func


#===============================================================================


def is_bound_method(func):
  """
  Return True if `func` is a bound method, False otherwise.
  """
  
  return hasattr(func, "__self__") and func.__self__ is not None


def get_module_root(module_path, path_component_to_trim_after):
  module_path_components = module_path.split(".")
  
  if path_component_to_trim_after in module_path_components:
    path_component_index = module_path_components.index(path_component_to_trim_after)
    return '.'.join(module_path_components[:path_component_index + 1])
  else:
    return module_path
