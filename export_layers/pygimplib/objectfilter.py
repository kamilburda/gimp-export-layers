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
  objects, each with their own set of rules and match type.
  """
  
  _MATCH_TYPES = MATCH_ALL, MATCH_ANY = (0, 1)
  
  def __init__(self, match_type=MATCH_ALL):
    self._match_type = match_type
    
    # Key: function (func)
    # Value: `_Rule` or `ObjectFilter` instance
    self._filter_items = collections.OrderedDict()
  
  @property
  def match_type(self):
    return self._match_type
  
  def __bool__(self):
    """Returns `True` if the filter is not empty, `False` otherwise."""
    return bool(self._filter_items)
  
  def __getitem__(self, function_or_name):
    """Returns the specified rule - a `_Rule` instance or a nested filter.
        
    Parameters:
    
    * `function_or_name` - Function or nested filter specified by its name.
    
    Raises
    
    * `KeyError` - `function_or_name` is not found in the filter.
    """
    return self._filter_items[function_or_name]
  
  def __contains__(self, func_or_filter):
    """Returns `True` if the filter contains the given rule or nested filter,
    `False` otherwise.
    """
    return func_or_filter in self._filter_items
  
  def add(self, func_or_filter, func_args=None, func_kwargs=None, name=''):
    """Adds the specified function or a nested filter as a rule to the filter.
    
    If `func_or_filter` already exists in the filter, do nothing.
    
    If you need to later remove the rule (via `remove`), pass a named function
    rather than an inline lambda expression. Alternatively, you can use
    `add_temp()` for temporary filters.
    
    Parameters:
    
    * `func_or_filter` - Function or nested filter to filter objects by. If a
      function, it always have at least one argument - the object to match (used
      by `is_match()`).
    
    * `func_args` - Arguments for `func_or_filter` if it is a function.
    
    * `func_kwargs` - Keyword arguments for `func_or_filter` if it is a function.
    
    * `name` - Name of the added rule. For functions, this defaults to its
      `__name__` attribute. If a function does not have the `__name__`
      attribute, an empty string is used.
    
    Raises:
    
    * `TypeError` - `func_or_filter` is not a function or an `ObjectFilter`
      instance.
    """
    func_args = func_args if func_args is not None else ()
    func_kwargs = func_kwargs if func_kwargs is not None else {}
    
    if func_or_filter in self:
      return
    
    if isinstance(func_or_filter, ObjectFilter):
      self._filter_items[name] = func_or_filter
    elif callable(func_or_filter):
      func = func_or_filter
      self._filter_items[func] = _Rule(
        func, func_args, func_kwargs, self._get_rule_name_for_func(func, name))
    else:
      raise TypeError('"{}": not a function or ObjectFilter instance'.format(func_or_filter))
  
  def _get_rule_name_for_func(self, func, name):
    if not name and hasattr(func, '__name__'):
      return func.__name__
    else:
      return name
  
  def remove(self, func_or_filter_name, raise_if_not_found=True):
    """Removes the specified rule (function or nested filter) from the filter.
    
    Parameters:
    
    * `func_or_filter` - Function or nested filter name to remove from the
      filter.
    
    * `raise_if_not_found` - If `True`, raise `ValueError` if `func_or_filter`
      is not found in the filter.
    
    Raises:
    
    * `ValueError` - `func_or_filter` is not found in the filter and
      `raise_if_not_found` is `True`.
    """
    if func_or_filter_name in self:
      del self._filter_items[func_or_filter_name]
    else:
      if raise_if_not_found:
        raise ValueError('"{}" not found in filter'.format(func_or_filter_name))
  
  @contextlib.contextmanager
  def add_temp(self, func_or_filter, func_args=None, func_kwargs=None, name=''):
    """Temporarily adds a function or nested filter as a rule to the filter.
    
    Use this function as a context manager:
    
      with filter.add_temp(func_or_filter):
        # do stuff
    
    If `func_or_filter` already exists in the filter, the existing rule will not
    be overridden and will not be removed.
    
    See `add()` for further information about parameters and exceptions.
    """
    has_func_or_filter_already = func_or_filter in self
    func_args = func_args if func_args is not None else ()
    func_kwargs = func_kwargs if func_kwargs is not None else {}
    
    if not has_func_or_filter_already:
      self.add(func_or_filter, func_args, func_kwargs, name)
    try:
      yield
    finally:
      if not has_func_or_filter_already:
        if isinstance(func_or_filter, ObjectFilter):
          self.remove(name)
        else:
          self.remove(func_or_filter)
  
  @contextlib.contextmanager
  def remove_temp(self, func_or_filter_name, raise_if_not_found=True):
    """Temporarily removes a rule. Use as a context manager:
    
      with filter.remove_temp(func_or_filter_name):
        # do stuff
    
    See `remove()` for further information about parameters and exceptions.
    """
    has_rule = func_or_filter_name in self
    
    if not has_rule:
      if raise_if_not_found:
        raise ValueError('"{}" not found in filter'.format(func_or_filter_name))
    else:
      rule = self._filter_items[func_or_filter_name]
      self.remove(func_or_filter_name)
    
    try:
      yield
    finally:
      if has_rule:
        if isinstance(rule, ObjectFilter):
          self.add(rule, None, None, func_or_filter_name)
        else:
          self.add(rule.function, rule.args, rule.kwargs, rule.name)
  
  def is_match(self, object_to_match):
    """Returns `True` if the specified objects matches the rules, `False`
    otherwise.
    
    If `match_type` attribute is `MATCH_ALL`, return `True` if `object_to_match`
    matches all specified filter rules and all top-level nested filters return
    `True`. Otherwise return `False`.
    
    If `match_type` attribute is `MATCH_ANY`, return `True` if `object_to_match`
    matches at least one specified filter rule or at least one top-level nested
    filter returns `True`. Otherwise return `False`.
    
    If no filter rules are specified, return `True`.
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
        func, rule = key, value
        is_match = is_match and func(object_to_match, *rule.args, **rule.kwargs)
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
        is_match = is_match or func(object_to_match, *rule.args, **rule.kwargs)
      if is_match:
        break
    
    return is_match
  
  def list_rules(self):
    """Returns a list of rules (functions and nested filters)."""
    return list(self._filter_items.values())
  
  def reset(self):
    """Resets the filter, removing all rules. The match type is preserved."""
    self._filter_items.clear()


_Rule = collections.namedtuple('_Rule', ['function', 'args', 'kwargs', 'name'])
