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
This module defines a class to filter objects according to specified filter
rules.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import inspect
import contextlib

#===============================================================================


class ObjectFilter(object):
  
  """
  This class is a filter containing a set of rules that determines whether
  a given object matches the rules or not (using the `is_match()` method).
  
  Attributes:
  
  * `match_type` (read-only) - Match type. Possible match types:
    
    * MATCH_ALL - For `is_match()` to return True, the object must match
      all rules.
    
    * MATCH_ANY - For `is_match()` to return True, the object must match
      at least one rule.
  
  For greater flexibility, the filter can also contain nested `ObjectFilter`
  objects, called "subfilters", each with their own set of rules and match type.
  """
  
  _MATCH_TYPES = MATCH_ALL, MATCH_ANY = (0, 1)
  
  def __init__(self, match_type):
    self._match_type = match_type
    
    # Key: function (rule_func)
    # Value: tuple (rule_func_args) or ObjectFilter instance (a subfilter)
    self._filter_items = {}
  
  @property
  def match_type(self):
    return self._match_type
  
  def __bool__(self):
    """
    Return True if the filter is not empty, False otherwise.
    """
    
    return bool(self._filter_items)
  
  def has_rule(self, rule_func):
    return rule_func in self._filter_items
  
  def add_rule(self, rule_func, *rule_func_args):
    """
    Add the specified rule as a function to the filter.
    
    If `rule_func` already exists in the filter, do nothing.
    
    If you need to later remove the rule from the filter (using the
    `remove_rule()` method), pass a named function rather than an inline lambda
    expression. Alternatively, you can use `add_rule_temp()` for temporary
    filters.
    
    Parameters:
    
    * `rule_func` - Function to filter objects by. The function must always have
      at least one argument - the object to match (used by the `is_match()`
      method).
    
    * `*rule_func_args` - Arguments for the `rule_func` function.
    
    Raises:
    
    * `TypeError` - `rule_func` is not callable.
    
    * `ValueError` - `rule_func` does not have at least one argument.
    """
    
    if self.has_rule(rule_func):
      return
    
    if not callable(rule_func):
      raise TypeError("not a function")
    
    if not self._is_rule_func_valid(rule_func):
      raise TypeError("function must have at least one argument (the object to match)")
    
    self._filter_items[rule_func] = rule_func_args
  
  @staticmethod
  def _is_rule_func_valid(rule_func):
    num_args = len(inspect.getargspec(rule_func)[0])
    
    return (
      ((inspect.isfunction(rule_func) or inspect.isbuiltin(rule_func)) and num_args >= 1)
      or (inspect.ismethod(rule_func) and num_args >= 2))
  
  def remove_rule(self, rule_func, raise_if_not_found=True):
    """
    Remove the rule (`rule_func` function) from the filter.
    
    Parameters:
    
    * `rule_func` - Function to remove from the filter.
    
    * `raise_if_not_found` - If True, raise `ValueError` if `rule_func` is not
      found in the filter.
    
    Raises:
    
    * `ValueError` - `rule_func` is not found in the filter and
      `raise_if_not_found` is True.
    """
    
    if self.has_rule(rule_func):
      del self._filter_items[rule_func]
    else:
      if raise_if_not_found:
        raise ValueError("'{0}' not found in filter".format(rule_func))
  
  @contextlib.contextmanager
  def add_rule_temp(self, rule_func, *rule_func_args):
    """
    Temporarily add a rule. Use as a context manager:
    
      with filter.add_rule_temp(rule_func):
        # do stuff
    
    If `rule_func` already exists in the filter, the existing rule will not be
    overridden and will not be removed.
    
    Parameters:
    
    * `rule_func` - Function to filter objects by. The function must always have
      at least one argument - the object to match (used by the `is_match()`
      method).
    
    * `*rule_func_args` - Arguments for the `rule_func` function.
    
    Raises:
    
    * `TypeError` - `rule_func` is not callable.
    
    * `ValueError` - `rule_func` does not have at least one argument.
    """
    
    has_rule_already = self.has_rule(rule_func)
    if not has_rule_already:
      self.add_rule(rule_func, *rule_func_args)
    try:
      yield
    finally:
      if not has_rule_already:
        self.remove_rule(rule_func)
  
  @contextlib.contextmanager
  def remove_rule_temp(self, rule_func, raise_if_not_found=True):
    """
    Temporarily remove a rule. Use as a context manager:
    
      with filter.remove_rule_temp(rule_func):
        # do stuff
    
    Parameters:
    
    * `rule_func` - Function to remove from the filter.
    
    * `raise_if_not_found` - If True, raise `ValueError` if `rule_func` is not
      in the filter.
    
    Raises:
    
    * `ValueError` - `rule_func` is not found in the filter and
      `raise_if_not_found` is True.
    """
    
    has_rule = self.has_rule(rule_func)
    
    if not has_rule:
      if raise_if_not_found:
        raise ValueError("'{0}' not found in filter".format(rule_func))
    else:
      rule_func_args = self._filter_items[rule_func]
      self.remove_rule(rule_func)
    
    try:
      yield
    finally:
      if has_rule:
        self.add_rule(rule_func, *rule_func_args)
  
  def has_subfilter(self, subfilter_name):
    return subfilter_name in self._filter_items
  
  def add_subfilter(self, subfilter_name, subfilter):
    """
    Add the specified subfilter (`ObjectFilter` instance) to the filter.
    
    The subfilter can be later accessed by the `get_subfilter` method.
    
    Raises:
    
    * `ValueError` - `subfilter_name` already exists in the filter.
    """
    
    if self.has_subfilter(subfilter_name):
      raise ValueError(
        "subfilter named '{0}' already exists in the filter".format(subfilter_name))
    
    if not isinstance(subfilter, ObjectFilter):
      raise ValueError(
        "subfilter named '{0}' is not a subfilter".format(subfilter_name))
    
    self._filter_items[subfilter_name] = subfilter
  
  def get_subfilter(self, subfilter_name):
    """
    Get the subfilter specified by its name.
    
    Raises:
    
    * `ValueError` - `subfilter_name` does not exist in the filter or the value
      associated with `subfilter_name` is not a subfilter.
    """
    
    if not self.has_subfilter(subfilter_name):
      raise ValueError(
        "subfilter named '{0}' not found in filter".format(subfilter_name))
    
    item = self._filter_items[subfilter_name]
    
    return item
  
  # Provide alias to `get_subfilter` for easier access.
  __getitem__ = get_subfilter
  
  def remove_subfilter(self, subfilter_name, raise_if_not_found=True):
    """
    Remove the subfilter with the corresponding subfilter name.
    
    Parameters:
    
    * `subfilter name` - Subfilter name.
    
    * `raise_if_not_found` - If True, raise `ValueError` if `subfilter_name`
      is not found in the filter.
    
    Raises:
    
    * `ValueError` - `subfilter_name` is not found in the filter and
      `raise_if_not_found` is True.
    """
    
    if self.has_subfilter(subfilter_name):
      del self._filter_items[subfilter_name]
    else:
      if raise_if_not_found:
        raise ValueError(
          "subfilter named '{0}' not found in filter".format(subfilter_name))
  
  @contextlib.contextmanager
  def add_subfilter_temp(self, subfilter_name, subfilter):
    """
    Temporarily add a subfilter. Use as a context manager:
    
      with filter.add_subfilter_temp(subfilter_name, subfilter):
        # do stuff
    
    Raises:
    
    * `ValueError` - `subfilter_name` already exists in the filter.
    """
    
    self.add_subfilter(subfilter_name, subfilter)
    try:
      yield
    finally:
      self.remove_subfilter(subfilter_name)
  
  @contextlib.contextmanager
  def remove_subfilter_temp(self, subfilter_name, raise_if_not_found=True):
    """
    Temporarily remove a subfilter. Use as a context manager:
    
      with filter.remove_subfilter_temp(subfilter_name):
        # do stuff
    
    Parameters:
    
    * `subfilter name` - Subfilter name.
    
    * `raise_if_not_found` - If True, raise `ValueError` if `subfilter_name`
      is not found in the filter.
    
    Raises:
    
    * `ValueError` - `subfilter_name` is not found in the filter and
      `raise_if_not_found` is True.
    """
    
    has_subfilter = self.has_subfilter(subfilter_name)
    
    if not has_subfilter:
      if raise_if_not_found:
        raise ValueError(
          "subfilter named '{0}' not found in filter".format(subfilter_name))
    else:
      subfilter = self._filter_items[subfilter_name]
      self.remove_subfilter(subfilter_name)
    
    try:
      yield
    finally:
      if has_subfilter:
        self.add_subfilter(subfilter_name, subfilter)
  
  def is_match(self, object_to_match):
    """
    If `match_type` attribute is `MATCH_ALL`, return True if `object_to_match`
    matches all specified filter rules and all top-level subfilters return True.
    Otherwise return False.
    
    If `match_type` attribute is `MATCH_ANY`, return True if `object_to_match`
    matches at least one specified filter rule or at least one top-level
    subfilter returns True. Otherwise return False.
    
    If no filter rules are specified, return True.
    """
    
    if not self._filter_items:
      return True
    
    if self._match_type == self.MATCH_ALL:
      return self._is_match_all(object_to_match)
    elif self._match_type == self.MATCH_ANY:
      return self._is_match_any(object_to_match)
  
  def reset(self):
    """
    Reset the filter, removing all rules and subfilters. The match type is
    preserved.
    """
    
    self._filter_items.clear()
  
  def _is_match_all(self, object_to_match):
    is_match = True
    
    for key, value in self._filter_items.items():
      if isinstance(value, ObjectFilter):
        is_match = is_match and value.is_match(object_to_match)
      else:
        # key = rule_func, value = rule_func_args
        is_match = is_match and key(object_to_match, *value)
      if not is_match:
        break
    
    return is_match
  
  def _is_match_any(self, object_to_match):
    is_match = False
    
    for key, value in self._filter_items.items():
      if isinstance(value, ObjectFilter):
        is_match = is_match or value.is_match(object_to_match)
      else:
        # key = rule_func, value = rule_func_args
        is_match = is_match or key(object_to_match, *value)
      if is_match:
        break
    
    return is_match
