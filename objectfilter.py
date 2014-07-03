#-------------------------------------------------------------------------------
#
# This file is part of libgimpplugin.
#
# Copyright (C) 2014 khalim19 <khalim19@gmail.com>
# 
# libgimpplugin is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# libgimpplugin is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with libgimpplugin.  If not, see <http://www.gnu.org/licenses/>.
#
#-------------------------------------------------------------------------------

"""
This module:
* defines a filter to filter objects according to specified rules
"""

#===============================================================================

import inspect
from contextlib import contextmanager

#===============================================================================

class ObjectFilter(object):
  
  """
  This class is a filter containing a set of rules that determines whether
  a given object matches the rules or not (using the is_match() method).
  
  Match types:
  - MATCH_ALL - for is_match() to return True, the object must match all rules
  - MATCH_ANY - for is_match() to return True, the object must match at least one rule
  
  For better flexibility, the filter can also contain nested ObjectFilter objects,
  called "subfilters", each with their own set of rules and match type.
  """
  
  MATCH_TYPE = MATCH_ALL, MATCH_ANY = (1,2)
  
  def __init__(self, match_type=MATCH_ALL):
    self.match_type = match_type
    
    # Key: function (rule_func)
    # Value: tuple (rule_func_args)
    self._filter_items = {}
  
  def add_rule(self, rule_func, *rule_func_args):
    """
    Add the specified rule (rule_func) to the filter. `rule_func` must be a function
    (or a callable object) with at least one argument (the object to match) and
    must not already be added to the filter. 
    
    Parameters:
    
    * rule_func: Function to filter objects by.
    
    * rule_func_args: Arguments that rule_func accepts.
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
    Remove the specified rule (rule_func) from the filter.
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
    Temporarily add a rule. Use with the "with" keyword:
    
      with filter.add_rule_temp(rule_func):
        # do stuff
    """
    self.add_rule(rule_func, *rule_func_args)
    try:
      yield
    finally:
      self.remove_rule(rule_func)
  
  @contextmanager
  def remove_rule_temp(self, rule_func):
    """
    Temporarily remove a rule. Use with the "with" keyword:
    
      with filter.remove_rule_temp(rule_func):
        # do stuff
    """
    if rule_func not in self._filter_items:
      raise ValueError(str(rule_func) + " does not exist")
    rule_func_args = self._filter_items[rule_func]
    self.remove_rule(rule_func)
    try:
      yield
    finally:
      self.add_rule(rule_func, *rule_func_args)
  
  def add_subfilter(self, subfilter_name, subfilter):
    """
    Add the specified subfilter (ObjectFilter instance) to the filter, which can
    be later accessed by the `subfilter_name` string as follows:
      filter['my_subfilter']
    """
    if subfilter_name in self._filter_items:
      raise ValueError("subfilter already exists in the filter")
    
    self._filter_items[subfilter_name] = subfilter
  
  def remove_subfilter(self, subfilter_name):
    """
    Remove the subfilter with the corresponding subfilter name.
    """
    if subfilter_name in self._filter_items:
      del self._filter_items[subfilter_name]
    else:
      raise ValueError("subfilter \"" + str(subfilter_name) + "\" does not exist")
  
  def __getitem__(self, subfilter_name):
    """
    Get subfilter by its name.
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
    Temporarily add a subfilter. Use with the "with" keyword:
    
      with filter.add_subfilter_temp(subfilter_name, subfilter):
        # do stuff
    """
    self.add_subfilter(subfilter_name, subfilter)
    try:
      yield
    finally:
      self.remove_subfilter(subfilter_name)
  
  @contextmanager
  def remove_subfilter_temp(self, subfilter_name):
    """
    Temporarily remove a subfilter. Use with the "with" keyword:
    
      with filter.remove_subfilter_temp(subfilter_name):
        # do stuff
    """
    subfilter = self._filter_items[subfilter_name]
    self.remove_subfilter(subfilter_name)
    try:
      yield
    finally:
      self.add_subfilter(subfilter_name, subfilter)
  
  def is_match(self, object_to_match):
    """
    If match_type is MATCH_ALL, return True if `object_to_match` matches all
    specified filter rules and all top-level subfilters return True. Otherwise return False.
    
    If match_type is MATCH_ANY, return True if `object_to_match` matches at least one
    specified filter rule or at least one top-level subfilter returns True. Otherwise return False.
    
    If no filter rules are specified, return True.
    """
    
    if not self._filter_items:
      return True
    
    if self.match_type == self.MATCH_ALL:
      return self._is_match_all(object_to_match)
    elif self.match_type == self.MATCH_ANY:
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
