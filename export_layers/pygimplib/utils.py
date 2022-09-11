# -*- coding: utf-8 -*-

"""Misc. utility functions and classes."""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import inspect


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


def empty_func(*args, **kwargs):
  """
  Use this function when an empty function is desired to be passed as a
  parameter.
  
  For example, if you need to serialize a `collections.defaultdict` instance
  (e.g. via `pickle`) returning `None` for missing keys, you need to use a named
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


def is_bound_method(func):
  """
  Return `True` if `func` is a bound method, `False` otherwise.
  """
  return hasattr(func, '__self__') and func.__self__ is not None


def stringify_object(object_, name):
  """
  Return a string representation of the specified object, using the specified
  name as a presumed unique identifier of the object. This can be used in the
  `__str__()` method to return a more readable string representation than the
  default.
  """
  return '<{} "{}">'.format(type(object_).__name__, name)


def get_module_root(full_module_name, name_component_to_trim_after):
  """
  Return the part of the full module name (separated by '.' characters) from the
  beginning up to the matching module name component including that component.
  
  If `name_component_to_trim_after` does not match any name component from
  `full_module_name`, return `full_module_name`.
  """
  module_name_components = full_module_name.split('.')
  
  if name_component_to_trim_after in module_name_components:
    name_component_index = module_name_components.index(name_component_to_trim_after)
    return '.'.join(module_name_components[:name_component_index + 1])
  else:
    return full_module_name


def get_current_module_filepath():
  """
  Get the full path name of the module this function is called from.
  """
  return inspect.stack()[1][1]


def create_read_only_property(obj, name, value):
  """
  For the given `obj` object, create a private attribute named `_[name]` and a
  read-only property named `name` returning the value of the private attribute.
  """
  setattr(obj, '_' + name, value)
  setattr(
    obj.__class__,
    name,
    property(fget=lambda obj, name=name: getattr(obj, '_' + name)))
