# -*- coding: utf-8 -*-

"""Class to filter objects according to the specified rules."""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import collections
import contextlib
import itertools


class ObjectFilter(object):
  """Class containing a list of rules determining whether an object matches
  given rules.
  
  Attributes:
  
  * `match_type` (read-only) - Match type. Possible match types:
    
    * MATCH_ALL - For `is_match()` to return `True`, an object must match
      all rules.
    
    * MATCH_ANY - For `is_match()` to return `True`, an object must match
      at least one rule.
  
  * `name` (read-only) - Name of the filter. The name does not have to be unique
    and can be used to manipulate multiple rules (functions or nested filters)
    with the same name at once (e.g. by removing them with `remove()`).
  
  A rule can be a callable (function) or a nested `ObjectFilter` instance (with
  its own rules and different matching type if needed).
  """
  
  _MATCH_TYPES = MATCH_ALL, MATCH_ANY = (0, 1)
  
  _rule_id_counter = itertools.count(start=1)
  
  def __init__(self, match_type=MATCH_ALL, name=''):
    self._match_type = match_type
    self._name = name
    
    # Key: rule/nested filter ID
    # Value: `_Rule` or `ObjectFilter` instance
    self._rules = collections.OrderedDict()
  
  @property
  def match_type(self):
    return self._match_type
  
  @property
  def name(self):
    return self._name
  
  def __bool__(self):
    """Returns `True` if the filter is not empty, `False` otherwise."""
    return bool(self._rules)
  
  def __contains__(self, rule_id):
    """Returns `True` if the filter contains the given rule, `False` otherwise.
    
    Parameters:
    
    * `rule_id` -  rule ID as returned by `add()`.
    """
    return rule_id in self._rules
  
  def __getitem__(self, rule_id):
    """Returns the specified rule - a `_Rule` instance or a nested filter.
    
    Parameters:
    
    * `rule_id` -  rule ID as returned by `add()`.
    
    Raises
    
    * `KeyError` - `rule_id` is not found in the filter.
    """
    return self._rules[rule_id]
  
  def __len__(self):
    """Returns the number of rules in the filter.
    
    Rules within nested filters do not count.
    """
    return len(self._rules)
  
  def add(self, func_or_filter, args=None, kwargs=None, name=''):
    """Adds the specified callable or a nested filter as a rule to the filter.
    
    Parameters:
    
    * `func_or_filter` - A callable (function) or nested filter to filter
      objects by. If a callable, it must have at least one argument - the object
      to match (used by `is_match()`).
    
    * `args` - Arguments for `func_or_filter` if it is a callable.
    
    * `kwargs` - Keyword arguments for `func_or_filter` if it is a callable.
    
    * `name` - Name of the added rule if `func_or_filter` is a callable. If an
      empty string, the `__name__` attribute is used if it exists. `name` does
      not have to be unique and can be used to manipulate multiple rules with
      the same name at once (e.g. by removing them with `remove()`).
    
    Returns:
      
      If `func_or_filter` is a callable, a `_Rule` instance is returned,
      containing the input parameters and a unique identifier. If
      `func_or_filter` is a nested filter, a unique identifier is used. The
      identifier can be used to e.g. access (via `__getitem__`) or remove a
      rule.
    
    Raises:
    
    * `TypeError` - `func_or_filter` is not a callable or an `ObjectFilter`
      instance.
    """
    args = args if args is not None else ()
    kwargs = kwargs if kwargs is not None else {}
    
    rule_id = self._get_rule_id()
    
    if isinstance(func_or_filter, ObjectFilter):
      self._rules[rule_id] = func_or_filter
      
      return rule_id
    elif callable(func_or_filter):
      func = func_or_filter
      rule = _Rule(
        func,
        args,
        kwargs,
        self._get_rule_name_for_func(func, name),
        rule_id)
      self._rules[rule_id] = rule
      
      return rule
    else:
      raise TypeError('"{}": not a callable or ObjectFilter instance'.format(func_or_filter))
  
  def _get_rule_name_for_func(self, func, name):
    if not name and hasattr(func, '__name__'):
      return func.__name__
    else:
      return name
  
  def _get_rule_id(self):
    return self._rule_id_counter.next()
  
  def remove(self, rule_id=None, name=None, func_or_filter=None, count=0):
    """Removes rules from the filter matching one or more criteria.
    
    Parameters:
    
    * `rule_id` -  rule ID as returned by `add()`.
    
    * `name` - See `find()`.
    
    * `func_or_filter` - See `find()`.
    
    * `count` - See `find()`.
    
    Raises:
      
    * `ValueError` - If `rule_id`, `name` and `func_or_filter` are all `None`.
    
    Returns:
      
      A list of removed removed rules (callables or nested filters) and a list
      of the corresponding IDs.
    """
    if rule_id is None and name is None and func_or_filter is None:
      raise ValueError('at least one removal criterion must be specified')
    
    matching_ids = []
    
    if name is not None or func_or_filter is not None:
      matching_ids = self.find(name=name, func_or_filter=func_or_filter, count=count)
    
    if rule_id in self and rule_id not in matching_ids:
      matching_ids.append(rule_id)
    
    matching_rules = [self._rules.pop(id_) for id_ in matching_ids]
    
    return matching_rules, matching_ids
  
  @contextlib.contextmanager
  def add_temp(self, func_or_filter, args=None, kwargs=None, name=''):
    """Temporarily adds a callable or nested filter as a rule to the filter.
    
    Use this function as a context manager:
    
      with filter.add_temp(func_or_filter) as rule_or_id:
        # do stuff
    
    See `add()` for further information about parameters and exceptions.
    """
    args = args if args is not None else ()
    kwargs = kwargs if kwargs is not None else {}
    
    rule_or_id = self.add(func_or_filter, args, kwargs, name)
    
    try:
      yield rule_or_id
    finally:
      if isinstance(rule_or_id, _Rule):
        self.remove(rule_or_id.id)
      else:
        self.remove(rule_or_id)
  
  @contextlib.contextmanager
  def remove_temp(self, rule_id=None, name=None, func_or_filter=None, count=0):
    """Temporarily removes rules from the filter matching one or more criteria.
    
    Use as a context manager:
      
      rule_id = filter.add(...)
      
      with filter.remove_temp(rule_id=rule_id) as rules_and_ids:
        # do stuff
    
    The identifiers (IDs) of the temporarily removed rules are preserved once
    added back.
    
    See `remove()` for further information about parameters and exceptions.
    """
    matching_rules, matching_ids = self.remove(
      rule_id=rule_id, name=name, func_or_filter=func_or_filter, count=count)
    
    try:
      yield matching_rules, matching_ids
    finally:
      for rule_id, rule in zip(matching_ids, matching_rules):
        self._rules[rule_id] = rule
  
  def is_match(self, obj):
    """Returns `True` if the specified object matches the rules, `False`
    otherwise.
    
    If `match_type` is `MATCH_ALL`, `True` is returned if the object matches all
    rules and all top-level nested filters return `True`. Otherwise, `False` is
    returned.
    
    If `match_type` is `MATCH_ANY`, `True` is returned if the object matches at
    least one rule or at least one top-level nested filter returns `True`.
    Otherwise, `False` is returned.
    
    If no rules are specified, `True` is returned.
    """
    if not self._rules:
      return True
    
    if self._match_type == self.MATCH_ALL:
      return self._is_match_all(obj)
    elif self._match_type == self.MATCH_ANY:
      return self._is_match_any(obj)
  
  def _is_match_all(self, obj):
    is_match = True
    
    for value in self._rules.values():
      if isinstance(value, ObjectFilter):
        is_match = is_match and value.is_match(obj)
      else:
        rule = value
        is_match = is_match and rule.function(obj, *rule.args, **rule.kwargs)
      if not is_match:
        break
    
    return is_match
  
  def _is_match_any(self, obj):
    is_match = False
    
    for value in self._rules.values():
      if isinstance(value, ObjectFilter):
        is_match = is_match or value.is_match(obj)
      else:
        rule = value
        is_match = is_match or rule.function(obj, *rule.args, **rule.kwargs)
      if is_match:
        break
    
    return is_match
  
  def find(self, name=None, func_or_filter=None, count=0):
    """Finds rule IDs matching the specified name or object (callable or nested
    filter).
    
    Both `name` and `func_or_filter` can be specified at the same time.
    
    Parameters:
    
    * `name` - Name of the added rule (callable or nested filter).
    
    * `func_or_filter` - Callable (e.g. a function) or a nested `ObjectFilter`
      instance.
    
    * `count` - If 0, return all occurrences. If greater than 0, return up to
      the first `count` occurrences. If less than 0, return up to the last
      `count` occurrences.
    
    Returns:
    
      List of IDs of matching `_Rule` instances or nested filters, or an empty
      list if there is no match.
    
    Raises:
      
    * `ValueError` - If both `name` and `func_or_filter` are `None`.
    """
    if name is None and func_or_filter is None:
      raise ValueError('at least a name or object must be specified')
    
    # We are exploiting `OrderedDict` to keep unique IDs in the order they were
    # found.
    matching_rule_ids = collections.OrderedDict()
    
    for rule_id, rule_or_filter in self._rules.items():
      if name is not None:
        if rule_or_filter.name == name:
          matching_rule_ids[rule_id] = None
      
      if func_or_filter is not None:
        if isinstance(rule_or_filter, _Rule):
          if rule_or_filter.function == func_or_filter:
            matching_rule_ids[rule_id] = None
        else:
          if rule_or_filter == func_or_filter:
            matching_rule_ids[rule_id] = None
    
    matching_rule_ids = list(matching_rule_ids)
    
    if count == 0:
      return matching_rule_ids
    elif count > 0:
      return matching_rule_ids[:count]
    else:
      return matching_rule_ids[count:]
  
  def list_rules(self):
    """Returns a dictionary of (rule ID, rule) pairs."""
    # Return a copy to prevent modifying the original.
    return collections.OrderedDict(self._rules)
  
  def reset(self):
    """Resets the filter, removing all rules. The match type is preserved."""
    self._rules.clear()


_Rule = collections.namedtuple('_Rule', ['function', 'args', 'kwargs', 'name', 'id'])
