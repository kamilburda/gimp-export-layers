# -*- coding: utf-8 -*-

"""Metaclasses for settings and mappings of types."""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import collections
import functools
import inspect
import re
import types

from .. import utils as pgutils


class _TypeMap(object):
  
  def __init__(self, description=None):
    self._description = description
    
    self._name_to_type_map = collections.OrderedDict()
    self._type_to_names_map = collections.defaultdict(list)
  
  def __getitem__(self, type_or_name, return_all_names=False):
    if isinstance(type_or_name, types.StringTypes):
      try:
        return self._name_to_type_map[type_or_name]
      except KeyError:
        raise TypeError(self._get_error_message(type_or_name))
    else:
      if type_or_name not in self._type_to_names_map:
        raise TypeError(self._get_error_message(type_or_name))
      
      names = self._type_to_names_map[type_or_name]
      
      if return_all_names:
        return names
      else:
        return names[0]
  
  def __contains__(self, key):
    if isinstance(key, types.StringTypes):
      return key in self._name_to_type_map
    else:
      return key in self._type_to_names_map
  
  def __getattr__(self, name):
    try:
      return self._name_to_type_map[name]
    except KeyError:
      raise TypeError(self._get_error_message(name))
  
  def __hasattr__(self, name):
    return name in self._name_to_type_map
  
  def _get_error_message(self, value):
    error_message = 'unrecognized type "{}"'.format(value)
    if self._description:
      error_message += '; are you sure this is a {}?'.format(self._description)
    
    return error_message


SettingTypes = _TypeMap(description='setting type')
SettingGuiTypes = _TypeMap(description='setting GUI type')


class SettingMeta(type):
  """Metaclass for the `setting.Setting` class and its subclasses.
  
  The metaclass is responsible for the following:
  
  * Creating a mapping of `Setting` subclasses and human-readable names for
    easier specification of the `'type'` field when creating settings via
    `setting.Group.add()`.
  
  * Tracking names and values of arguments passed to instantiation of a setting.
    The names and values are then passed to `Setting.to_dict()` to allow
    persisting the setting with the arguments it was instantiated with.
  
  * Ensuring that `Setting` classes documented as abstract cannot be initialized
    (`TypeError` is raised on `__init__()`).
  """
  
  def __new__(mcls, name, bases, namespace):  # @NoSelf
    _handle_abstract_attribute(namespace)
    
    _set_init_wrapper(mcls, namespace)
    
    cls = super(SettingMeta, mcls).__new__(mcls, name, bases, namespace)
    
    _register_type_and_aliases(namespace, cls, name, SettingTypes, 'Setting')
    
    return cls
  
  @staticmethod
  def _get_init_wrapper(orig_init):
    
    @functools.wraps(orig_init)
    def init_wrapper(self, *args, **kwargs):
      if getattr(self, '_ABSTRACT', False):
        raise TypeError('cannot initialize abstract setting class "{}"'.format(
          self.__class__.__name__))
      
      # This check prevents a parent class' `__init__()` from overriding the
      # contents of `_dict_on_init`, which may have different arguments.
      if not hasattr(self, '_dict_on_init'):
        self._dict_on_init = dict(kwargs)
        # Exclude `self` as the first argument
        arg_names = inspect.getargspec(orig_init)[0][1:]
        for arg_name, arg in zip(arg_names, args):
          self._dict_on_init[arg_name] = arg
        
        if inspect.getargspec(orig_init)[1] is not None:
          self._dict_on_init['_varargs'] = list(args[len(arg_names):])
      
      orig_init(self, *args, **kwargs)
    
    return init_wrapper


class PresenterMeta(type):
  """Metaclass for the `setting.Presenter` class and its subclasses.
  
  The metaclass is responsible for the following:
  
  * Creating a mapping of `Presenter` subclasses and human-readable names for
    easier specification of the `'gui_type'` field when creating settings via
    `setting.Group.add()`.
  
  * Ensuring that `Presenter` classes documented as abstract cannot be
    initialized by raising `TypeError` on `__init__()`.
  """
  
  def __new__(mcls, name, bases, namespace):  # @NoSelf
    _handle_abstract_attribute(namespace)
    
    _set_init_wrapper(mcls, namespace)
    
    cls = super(PresenterMeta, mcls).__new__(mcls, name, bases, namespace)
    
    _register_type_and_aliases(namespace, cls, name, SettingGuiTypes, 'Presenter')
    
    return cls
  
  @staticmethod
  def _get_init_wrapper(orig_init):
    
    @functools.wraps(orig_init)
    def init_wrapper(self, *args, **kwargs):
      if getattr(self, '_ABSTRACT', False):
        raise TypeError('cannot initialize abstract presenter class "{}"'.format(
          self.__class__.__name__))
      
      orig_init(self, *args, **kwargs)
    
    return init_wrapper


def _set_init_wrapper(mcls, namespace):
  # Only wrap `__init__` if the (sub)class defines or overrides it.
  # Otherwise, the argument list of `__init__` for a subclass would be
  # overridden the parent class' `__init__` argument list.
  if '__init__' in namespace:
    namespace['__init__'] = mcls._get_init_wrapper(namespace['__init__'])


def _handle_abstract_attribute(namespace):
  if '_ABSTRACT' not in namespace:
    namespace['_ABSTRACT'] = False


def _register_type_and_aliases(namespace, cls, type_name, type_map, base_class_name):
  processed_type_name = pgutils.safe_decode(type_name, 'utf-8')
  human_readable_name = _get_human_readable_class_name(processed_type_name, base_class_name)
  
  if human_readable_name not in type_map._name_to_type_map and not namespace['_ABSTRACT']:
    type_map._name_to_type_map[human_readable_name] = cls
    type_map._type_to_names_map[cls].append(human_readable_name)
    
    if '_ALIASES' in namespace:
      for alias in namespace['_ALIASES']:
        if alias not in type_map._name_to_type_map:
          type_map._name_to_type_map[alias] = cls
        else:
          raise TypeError(
            'alias "{}" matches a {} class name or is already specified'.format(
              alias, base_class_name))
        
        type_map._type_to_names_map[cls].append(alias)


def _get_human_readable_class_name(name, suffix_to_strip=None):
  processed_name = name
  
  if suffix_to_strip and processed_name.endswith(suffix_to_strip):
    processed_name = processed_name[:-len(suffix_to_strip)]
  
  # Converts the class name in CamelCase to snake_case.
  # Source: https://stackoverflow.com/a/1176023
  processed_name = re.sub(r'(?<!^)(?=[A-Z])', '_', processed_name).lower()
  
  return processed_name
