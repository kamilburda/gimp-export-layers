# -*- coding: utf-8 -*-

"""Class to filter objects according to specified filter rules."""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import collections
import contextlib


class ObjectFilter(object):
  """Class containing a list of rules determining whether an object matches
  given rules.
  
  Attributes:
  
  * `match_type` (read-only) - Match type. Possible match types:
    
    * MATCH_ALL - For `is_match()` to return `True`, the object must match
      all rules.
    
    * MATCH_ANY - For `is_match()` to return `True`, the object must match
      at least one rule.
  
  For greater flexibility, the filter can also contain nested `ObjectFilter`
  objects, called "subfilters", each with their own set of rules and match type.
  """
  
  _MATCH_TYPES = MATCH_ALL, MATCH_ANY = (0, 1)
  
  def __init__(self, match_type):
    self._match_type = match_type
    
    # Key: function (func)
    # Value: `_Rule` or ObjectFilter instance (a subfilter)
    self._filter_items = collections.OrderedDict()
  
  @property
  def match_type(self):
    return self._match_type
  
  def __bool__(self):
    """Returns `True` if the filter is not empty, `False` otherwise."""
    return bool(self._filter_items)
  
  def __getitem__(self, subfilter_name):
    """Returns the subfilter specified by its name.
    
    This method is an alias for `get_subfilter()`.
    """
    return self.get_subfilter(subfilter_name)
  
  def has_rule(self, func):
    """Returns `True` if the filter contains the specified rule, `False`
    otherwise.
    """
    return func in self._filter_items
  
  def add_rule(self, func, *func_args):
    """Adds the specified rule as a function to the filter.
    
    If `func` already exists in the filter, do nothing.
    
    If you need to later remove the rule from the filter (using
    `remove_rule()`), pass a named function rather than an inline lambda
    expression. Alternatively, you can use `add_rule_temp()` for temporary
    filters.
    
    Parameters:
    
    * `func` - Function to filter objects by. The function must always have
      at least one argument - the object to match (used by `is_match()`).
    
    * `*func_args` - Arguments for `func`.
    
    Raises:
    
    * `TypeError` - `func` is not callable.
    
    * `ValueError` - `func` does not have at least one argument.
    """
    if self.has_rule(func):
      return
    
    if not callable(func):
      raise TypeError('not a function')
    
    self._filter_items[func] = _Rule(func, func_args, None, func.__name__)
  
  def remove_rule(self, func, raise_if_not_found=True):
    """Removes the rule (`func` function) from the filter.
    
    Parameters:
    
    * `func` - Function to remove from the filter.
    
    * `raise_if_not_found` - If `True`, raise `ValueError` if `func` is not
      found in the filter.
    
    Raises:
    
    * `ValueError` - `func` is not found in the filter and `raise_if_not_found`
    is `True`.
    """
    if self.has_rule(func):
      del self._filter_items[func]
    else:
      if raise_if_not_found:
        raise ValueError('"{}" not found in filter'.format(func))
  
  @contextlib.contextmanager
  def add_rule_temp(self, func, *func_args):
    """Temporarily adds a rule. Use as a context manager:
    
      with filter.add_rule_temp(func):
        # do stuff
    
    If `func` already exists in the filter, the existing rule will not be
    overridden and will not be removed.
    
    Parameters:
    
    * `func` - Function to filter objects by. The function must always have at
      least one argument - the object to match (used by `is_match()`).
    
    * `*func_args` - Arguments for `func`.
    
    Raises:
    
    * `TypeError` - `func` is not callable.
    """
    has_rule_already = self.has_rule(func)
    if not has_rule_already:
      self.add_rule(func, *func_args)
    try:
      yield
    finally:
      if not has_rule_already:
        self.remove_rule(func)
  
  @contextlib.contextmanager
  def remove_rule_temp(self, func, raise_if_not_found=True):
    """Temporarily removes a rule. Use as a context manager:
    
      with filter.remove_rule_temp(func):
        # do stuff
    
    Parameters:
    
    * `func` - Function to remove from the filter.
    
    * `raise_if_not_found` - If `True`, raise `ValueError` if `func` is not in
      the filter.
    
    Raises:
    
    * `ValueError` - `func` is not found in the filter and `raise_if_not_found`
      is `True`.
    """
    has_rule = self.has_rule(func)
    
    if not has_rule:
      if raise_if_not_found:
        raise ValueError('"{}" not found in filter'.format(func))
    else:
      rule = self._filter_items[func]
      self.remove_rule(func)
    
    try:
      yield
    finally:
      if has_rule:
        self.add_rule(func, *rule.args)
  
  def has_subfilter(self, subfilter_name):
    """Returns `True` if the given subfilter exists, `False` otherwise."""
    return subfilter_name in self._filter_items
  
  def add_subfilter(self, subfilter_name, subfilter):
    """Adds the specified subfilter (`ObjectFilter` instance) to the filter.
    
    The subfilter can be later accessed by `get_subfilter()`.
    
    Raises:
    
    * `ValueError` - `subfilter_name` already exists in the filter.
    """
    if self.has_subfilter(subfilter_name):
      raise ValueError(
        'subfilter named "{}" already exists in the filter'.format(subfilter_name))
    
    if not isinstance(subfilter, ObjectFilter):
      raise ValueError(
        'subfilter named "{}" is not a subfilter'.format(subfilter_name))
    
    self._filter_items[subfilter_name] = subfilter
  
  def get_subfilter(self, subfilter_name):
    """Returns the subfilter specified by its name.
    
    Raises:
    
    * `ValueError` - `subfilter_name` does not exist in the filter or the value
      associated with `subfilter_name` is not a subfilter.
    """
    if not self.has_subfilter(subfilter_name):
      raise ValueError(
        'subfilter named "{}" not found in filter'.format(subfilter_name))
    
    item = self._filter_items[subfilter_name]
    
    return item
  
  def remove_subfilter(self, subfilter_name, raise_if_not_found=True):
    """Remove the subfilter with the corresponding subfilter name.
    
    Parameters:
    
    * `subfilter name` - Subfilter name.
    
    * `raise_if_not_found` - If `True`, raise `ValueError` if `subfilter_name`
      is not found in the filter.
    
    Raises:
    
    * `ValueError` - `subfilter_name` is not found in the filter and
      `raise_if_not_found` is `True`.
    """
    if self.has_subfilter(subfilter_name):
      del self._filter_items[subfilter_name]
    else:
      if raise_if_not_found:
        raise ValueError(
          'subfilter named "{}" not found in filter'.format(subfilter_name))
  
  @contextlib.contextmanager
  def add_subfilter_temp(self, subfilter_name, subfilter):
    """Temporarily adds a subfilter. Use as a context manager:
    
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
    """Temporarily removes a subfilter. Use as a context manager:
    
      with filter.remove_subfilter_temp(subfilter_name):
        # do stuff
    
    Parameters:
    
    * `subfilter name` - Subfilter name.
    
    * `raise_if_not_found` - If `True`, raise `ValueError` if `subfilter_name`
      is not found in the filter.
    
    Raises:
    
    * `ValueError` - `subfilter_name` is not found in the filter and
      `raise_if_not_found` is `True`.
    """
    has_subfilter = self.has_subfilter(subfilter_name)
    
    if not has_subfilter:
      if raise_if_not_found:
        raise ValueError(
          'subfilter named "{}" not found in filter'.format(subfilter_name))
    else:
      subfilter = self._filter_items[subfilter_name]
      self.remove_subfilter(subfilter_name)
    
    try:
      yield
    finally:
      if has_subfilter:
        self.add_subfilter(subfilter_name, subfilter)
  
  def is_match(self, object_to_match):
    """Returns `True` if the specified objects matches the rules, `False`
    otherwise.
    
    If `match_type` attribute is `MATCH_ALL`, return `True` if `object_to_match`
    matches all specified filter rules and all top-level subfilters return
    `True`. Otherwise return `False`.
    
    If `match_type` attribute is `MATCH_ANY`, return `True` if `object_to_match`
    matches at least one specified filter rule or at least one top-level
    subfilter returns `True`. Otherwise return `False`.
    
    If no filter rules are specified, return `True`.
    """
    if not self._filter_items:
      return True
    
    if self._match_type == self.MATCH_ALL:
      return self._is_match_all(object_to_match)
    elif self._match_type == self.MATCH_ANY:
      return self._is_match_any(object_to_match)
  
  def reset(self):
    """Resets the filter, removing all rules and subfilters.
    
    The match type is preserved.
    """
    self._filter_items.clear()
  
  def _is_match_all(self, object_to_match):
    is_match = True
    
    for key, value in self._filter_items.items():
      if isinstance(value, ObjectFilter):
        is_match = is_match and value.is_match(object_to_match)
      else:
        func, rule = key, value
        is_match = is_match and func(object_to_match, *rule.args)
      if not is_match:
        break
    
    return is_match
  
  def _is_match_any(self, object_to_match):
    is_match = False
    
    for key, value in self._filter_items.items():
      if isinstance(value, ObjectFilter):
        is_match = is_match or value.is_match(object_to_match)
      else:
        func, rule = key, value
        is_match = is_match or func(object_to_match, *rule.args)
      if is_match:
        break
    
    return is_match


_Rule = collections.namedtuple('_Rule', ['function', 'args', 'kwargs', 'name'])
