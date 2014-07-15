#-------------------------------------------------------------------------------
#
# This file is part of pylibgimpplugin.
#
# Copyright (C) 2014 khalim19 <khalim19@gmail.com>
# 
# pylibgimpplugin is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# pylibgimpplugin is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with pylibgimpplugin.  If not, see <http://www.gnu.org/licenses/>.
#
#-------------------------------------------------------------------------------

"""
This module defines a class to filter objects according to specified filter rules.
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
    
    * MATCH_ALL - for `is_match()` to return True, the object must match
      all rules
    
    * MATCH_ANY - for `is_match()` to return True, the object must match
      at least one rule
  
  For better flexibility, the filter can also contain nested `ObjectFilter`
  objects, called "subfilters", each with their own set of rules and match type.
  """
  
  __MATCH_TYPES = MATCH_ALL, MATCH_ANY = (0, 1)
  
  def __init__(self, match_type=MATCH_ALL):
    self._match_type = match_type
    
    # Key: function (rule_func)
    # Value: tuple (rule_func_args)
    self._filter_items = {}
  
  @property
  def match_type(self):
    return self._match_type
  
  def add_rule(self, rule_func, *rule_func_args):
    """
    Add the specified rule as a function to the filter.
    
    The function must not already be added to the filter.
    
    In order to be able to later remove the function from the filter (using the
    `remove_rule()` method), pass a named function rather than a lambda
    expression.
    
    Parameters:
    
    * `rule_func` - Function to filter objects by. The function must always have
      at least one argument - the object to match (used by the `is_match()`
      method).
    
    * `*rule_func_args` - Arguments for the `rule_func` function.
    
    Raises:
    
    * `TypeError` - `rule_func` is not callable.
    
    * `ValueError` - `rule_func` already exists in the filter or `rule_func`
      does not have at least one argument.
    """
    
    if not callable(rule_func):
      raise TypeError("Not a function")
    
    if rule_func in self._filter_items:
      raise ValueError("rule already exists in the filter")
    
    if len(inspect.getargspec(rule_func)[0]) < 1:
      raise TypeError("Function must have at least one argument (the object to match)")
    
    self._filter_items[rule_func] = rule_func_args
  
  def remove_rule(self, rule_func):
    """
    Remove the rule (`rule_func` function) from the filter.
    
    Parameters:
    
    * `rule_func` - Function to remove from the filter.
    
    Raises:
    
    * `ValueError` - `rule_func` was not found in the filter.
    """
    
    if rule_func in self._filter_items:
      del self._filter_items[rule_func]
    else:
      raise ValueError(str(rule_func) + " not found in filter")
  
  def has_rule(self, rule_func):
    return rule_func in self._filter_items
  
  @contextmanager
  def add_rule_temp(self, rule_func, *rule_func_args):
    """
    Temporarily add a rule. Use as a context manager:
    
      with filter.add_rule_temp(rule_func):
        # do stuff
    
    Parameters:
    
    * `rule_func` - Function to filter objects by. The function must always have
      at least one argument - the object to match (used by the `is_match()`
      method).
    
    * `*rule_func_args` - Arguments for the `rule_func` function.
    
    Raises:
    
    * `TypeError` - `rule_func` is not callable.
    
    * `ValueError` - `rule_func` already exists in the filter or `rule_func`
      does not have at least one argument.
    """
    
    self.add_rule(rule_func, *rule_func_args)
    try:
      yield
    finally:
      self.remove_rule(rule_func)
  
  @contextmanager
  def remove_rule_temp(self, rule_func):
    """
    Temporarily remove a rule. Use as a context manager:
    
      with filter.remove_rule_temp(rule_func):
        # do stuff
    
    Parameters:
    
    * `rule_func` - Function to remove from the filter.
    
    Raises:
    
    * `ValueError` - `rule_func` was not found in the filter.
    """
    
    if rule_func not in self._filter_items:
      raise ValueError(str(rule_func) + " not found in filter")
    rule_func_args = self._filter_items[rule_func]
    self.remove_rule(rule_func)
    try:
      yield
    finally:
      self.add_rule(rule_func, *rule_func_args)
  
  def add_subfilter(self, subfilter_name, subfilter):
    """
    Add the specified subfilter (`ObjectFilter` instance) to the filter, which
    can be later accessed by the `subfilter_name` string as follows:
    
      filter['my_subfilter']
    
    Raises:
    
    * `ValueError` - `subfilter_name` already exists in the filter.
    """
    
    if subfilter_name in self._filter_items:
      raise ValueError("subfilter already exists in the filter")
    
    self._filter_items[subfilter_name] = subfilter
  
  def remove_subfilter(self, subfilter_name):
    """
    Remove the subfilter with the corresponding subfilter name.
    
    Raises:
    
    * `ValueError` - `subfilter_name` does not exist in the filter.
    """
    
    if subfilter_name in self._filter_items:
      del self._filter_items[subfilter_name]
    else:
      raise ValueError("subfilter \"" + str(subfilter_name) + "\" does not exist")
  
  def __getitem__(self, subfilter_name):
    """
    Get subfilter by its name.
    
    Raises:
    
    * `ValueError` - `subfilter_name` does not exist in the filter or the value
      associated with `subfilter_name` is not a subfilter.
    """
    
    if subfilter_name not in self._filter_items:
      raise ValueError("subfilter with the name \"" + str(subfilter_name) + "\" does not exist")
    
    item = self._filter_items[subfilter_name]
    
    if not isinstance(item, ObjectFilter):
      raise ValueError("invalid subfilter name\"" + str(subfilter_name) + "\"; value is not a subfilter")
    
    return item
  
  def has_subfilter(self, subfilter_name):
    return subfilter_name in self._filter_items
  
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
  def remove_subfilter_temp(self, subfilter_name):
    """
    Temporarily remove a subfilter. Use as a context manager:
    
      with filter.remove_subfilter_temp(subfilter_name):
        # do stuff
    
    Raises:
    
    * `ValueError` - `subfilter_name` does not exist in the filter.
    """
    
    subfilter = self._filter_items[subfilter_name]
    self.remove_subfilter(subfilter_name)
    try:
      yield
    finally:
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
