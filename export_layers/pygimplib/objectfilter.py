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
This module defines a class to filter objects according to specified filter
rules.
"""

#===============================================================================

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division

str = unicode

#===============================================================================

import inspect
from contextlib import contextmanager

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
  
  __MATCH_TYPES = MATCH_ALL, MATCH_ANY = (0, 1)
  
  def __init__(self, match_type):
    self._match_type = match_type
    
    # Key: function (rule_func)
    # Value: tuple (rule_func_args) or ObjectFilter instance (a subfilter)
    self._filter_items = {}
  
  @property
  def match_type(self):
    return self._match_type
  
  def has_rule(self, rule_func):
    return rule_func in self._filter_items
  
  def add_rule(self, rule_func, *rule_func_args):
    """
    Add the specified rule as a function to the filter.
    
    If `rule_func` already exists in the filter, nothing happens.
    
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
    
    if len(inspect.getargspec(rule_func)[0]) < 1:
      raise TypeError("function must have at least one argument (the object to match)")
    
    self._filter_items[rule_func] = rule_func_args
  
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
        raise ValueError("\"" + str(rule_func) + "\" not found in filter")
  
  @contextmanager
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
  
  @contextmanager
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
        raise ValueError("\"" + str(rule_func) + "\" not found in filter")
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
      raise ValueError("subfilter named \"" + str(subfilter_name) + "\" already exists in the filter")
    
    if not isinstance(subfilter, ObjectFilter):
      raise ValueError("subfilter named \"" + str(subfilter_name) + "\" is not a subfilter")
    
    self._filter_items[subfilter_name] = subfilter
  
  def get_subfilter(self, subfilter_name):
    """
    Get the subfilter specified by its name.
    
    Raises:
    
    * `ValueError` - `subfilter_name` does not exist in the filter or the value
      associated with `subfilter_name` is not a subfilter.
    """
    
    if not self.has_subfilter(subfilter_name):
      raise ValueError("subfilter named \"" + str(subfilter_name) + "\" not found in filter")
    
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
        raise ValueError("subfilter named \"" + str(subfilter_name) + "\" not found in filter")
  
  @contextmanager
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
  
  @contextmanager
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
        raise ValueError("subfilter named \"" + str(subfilter_name) + "\" not found in filter")
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
