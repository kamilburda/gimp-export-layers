# -*- coding: utf-8 -*-

"""Managing and invoking a list of functions sequentially."""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import collections
import inspect
import itertools


class Invoker(object):
  """Class to invoke (call) a sequence of functions or nested instances,
  hereinafter "actions".
  
  Features include:
  * adding and removing actions,
  * reordering actions,
  * grouping actions and invoking only actions in specified groups,
  * adding actions to be invoked before or after each action, hereinafter
    "for-each actions",
  * adding another `Invoker` instance as an action (i.e. nesting the current
    instance inside another instance).
  """
  
  _ACTION_TYPES = _TYPE_ACTION, _TYPE_FOREACH_ACTION, _TYPE_INVOKER = (0, 1, 2)
  
  _action_id_counter = itertools.count(start=1)
  
  def __init__(self):
    # key: action group; value: list of `_ActionItem` instances
    self._actions = collections.OrderedDict()
    
    # key: action group; value: list of `_ActionItem` instances
    self._foreach_actions = collections.OrderedDict()
    
    # key: action group; value: dict of (action function: count) pairs
    self._action_functions = collections.defaultdict(lambda: collections.defaultdict(int))
    
    # key: action group; value: dict of (action function: count) pairs
    self._foreach_action_functions = collections.defaultdict(lambda: collections.defaultdict(int))
    
    # key: action group; value: dict of (`Invoker` instance: count) pairs
    self._invokers = collections.defaultdict(lambda: collections.defaultdict(int))
    
    # key: action ID; value: `_ActionItem` instance
    self._action_items = {}
  
  def add(
        self,
        action,
        groups=None,
        args=None,
        kwargs=None,
        foreach=False,
        ignore_if_exists=False,
        position=None,
        run_generator=True):
    """Adds an action to be invoked by `invoke()`.
    
    The ID of the newly added action is returned.
    
    An action can be:
    * a function, in which case optional arguments (`args`, a list or tuple) and
      keyword arguments (`kwargs`, a dict) can be specified,
    * another `Invoker` instance.
    
    To control which actions are invoked, you may want to group them.
    
    If `groups` is `None` or `'default'`, the action is added to a default
    group appropriately named `'default'`.
    
    If `groups` is a list of group names (strings), the action is added to
    the specified groups. Groups are created automatically if they previously
    did not exist.
    
    If `groups` is `'all'`, the action is added to all existing groups. The
    action will not be added to the default group if it does not exist.
    
    By default, the action is added at the end of the list of actions in the
    specified group(s). Pass an integer to the `position` parameter to customize
    the insertion position. A negative value represents an n-th to last
    position.
    
    Action as a function can also be a generator function or return a generator.
    This allows customizing which parts of the code of the function are called
    on each invocation. For example:
    
      def foo():
        print('bar')
        while True:
          args, kwargs = yield
          print('baz')
    
    prints `'bar'` the first time the function is called and `'baz'` all
    subsequent times. This allows to e.g. initialize objects to an initial state
    in the first part and then use that state in subsequent invocations of this
    function, effectively eliminating the need for global variables for the same
    purpose.
    
    The generator must contain at least one `yield` statement. If you pass
    arguments and want to use the arguments in the function, the yield statement
    must be in the form `args, kwargs = yield`.
    
    To make sure the generator can be called an arbitrary number of times, place
    a `yield` statement in an infinite loop. To limit the number of calls,
    simply do not use an infinite loop. In such a case, the action is
    permanently removed for the group(s) `invoke()` was called for once no more
    yield statements are encountered.
    
    To prevent activating generators and to treat generator functions as regular
    functions, set `run_generator` to `False`.
    
    If `foreach` is `True` and the action is a function, the action is
    treated as a "for-each" action. By default, a for-each action is
    invoked after each regular action (function or `Invoker` instance). To
    customize this behavior, use the `yield` statement in the for-each action
    to specify where it is desired to invoke each action.
    For example:
    
      def foo():
        print('bar')
        yield
        print('baz')
    
    first prints `'bar'`, then invokes the action and finally prints
    `'baz'`. Multiple `yield` statements can be specified to invoke the wrapped
    action multiple times.
    
    If multiple for-each actions are added, they are invoked in the order
    they were added by this method. For example:
      
      def foo1():
        print('bar1')
        yield
        print('baz1')
      
      def foo2():
        print('bar2')
        yield
        print('baz2')
    
    will print `'bar1'`, `'bar2'`, then invoke the action (only once), and
    then print `'baz1'` and `'baz2'`.
    
    To make an `Invoker` instance behave as a for-each action, wrap
    the instance in a function as shown above. For example:
      
      def invoke_before_each_action():
        invoker.invoke()
        yield
    
    If `ignore_if_exists` is `True`, do not add the action if the same
    function or `Invoker` instance is already added in at least one of
    the specified groups and return `None`. Note that the same function with
    different arguments is still treated as one function.
    """
    if ignore_if_exists and self.contains(action, groups, foreach):
      return None
    
    action_id = self._get_action_id()
    
    if callable(action):
      if not foreach:
        add_action_func = self._add_action
      else:
        add_action_func = self._add_foreach_action
      
      for group in self._process_groups_arg(groups):
        add_action_func(
          action_id,
          action,
          group,
          args if args is not None else (),
          kwargs if kwargs is not None else {},
          position,
          run_generator)
    else:
      for group in self._process_groups_arg(groups):
        self._add_invoker(action_id, action, group, position)
    
    return action_id
  
  def invoke(
        self,
        groups=None,
        additional_args=None,
        additional_kwargs=None,
        additional_args_position=None):
    """Invokes actions.
    
    If `groups` is `None` or `'default'`, invoke actions in the default
    group.
    
    If `groups` is a list of group names (strings), invoke actions in the
    specified groups.
    
    If `groups` is `'all'`, invoke actions in all existing groups.
    
    If any of the `groups` do not exist, raise `ValueError`.
    
    If `action` is an `Invoker` instance, the instance will invoke
    actions in the specified groups.
    
    Additional arguments and keyword arguments to all actions in the group
    are given by `additional_args` and `additional_kwargs`, respectively.
    If some keyword arguments appear in both the `kwargs` parameter in `add()`
    and in `additional_kwargs`, values from the latter override the values in
    the former.
    
    `additional_args` are appended to the argument list by default. Specify
    `additional_args_position` as an integer to change the insertion position of
    `additional_args`. `additional_args_position` also applies to nested
    `Invoker` instances.
    """
    
    def _invoke_action(item, group):
      action, action_args, action_kwargs = item.action
      args = _get_args(action_args)
      kwargs = dict(action_kwargs, **additional_kwargs)
      
      result = action(*args, **kwargs)
      
      if inspect.isgenerator(result):
        item.is_generator = True
      
      if not (item.is_generator and item.run_generator):
        return result
      else:
        if group not in item.generators_per_group:
          item.generators_per_group[group] = result
          return next(item.generators_per_group[group])
        else:
          try:
            return item.generators_per_group[group].send([args, kwargs])
          except StopIteration:
            item.should_be_removed_from_group = True
    
    def _prepare_foreach_action(action, action_args, action_kwargs):
      args = _get_args(action_args)
      kwargs = dict(action_kwargs, **additional_kwargs)
      return action(*args, **kwargs)
    
    def _get_args(action_args):
      if additional_args_position is None:
        return tuple(action_args) + tuple(additional_args)
      else:
        args = list(action_args)
        args[additional_args_position:additional_args_position] = additional_args
        return tuple(args)
    
    def _invoke_action_with_foreach_actions(item, group):
      action_generators = [
        _prepare_foreach_action(*foreach_item.action)
        for foreach_item in self._foreach_actions[group]]
      
      _invoke_foreach_actions_once(action_generators)
      
      while action_generators:
        result_from_action = _invoke_action(item, group)
        _invoke_foreach_actions_once(action_generators, result_from_action)
        
        if item.should_be_removed_from_group:
          self.remove(item.action_id, [group])
          item.should_be_removed_from_group = False
          return
    
    def _invoke_foreach_actions_once(action_generators, result_from_action=None):
      action_generators_to_remove = []
      
      for action_generator in action_generators:
        try:
          action_generator.send(result_from_action)
        except StopIteration:
          action_generators_to_remove.append(action_generator)
      
      for action_generator_to_remove in action_generators_to_remove:
        action_generators.remove(action_generator_to_remove)
    
    def _invoke_invoker(invoker, group):
      invoker.invoke([group], additional_args, additional_kwargs, additional_args_position)
    
    additional_args = additional_args if additional_args is not None else ()
    additional_kwargs = additional_kwargs if additional_kwargs is not None else {}
    
    for group in self._process_groups_arg(groups):
      if group not in self._actions:
        self._init_group(group)
      
      # An action could be removed during invocation, hence create a list and
      # later check for validity.
      items = list(self._actions[group])
      
      for item in items:
        if item not in self._actions[group]:
          continue
        
        if item.action_type != self._TYPE_INVOKER:
          if self._foreach_actions[group]:
            _invoke_action_with_foreach_actions(item, group)
          else:
            _invoke_action(item, group)
            
            if item.should_be_removed_from_group:
              self.remove(item.action_id, [group])
              item.should_be_removed_from_group = False
        else:
          _invoke_invoker(item.action, group)
  
  def add_to_groups(self, action_id, groups=None, position=None):
    """
    Add an existing action specified by its ID to the specified groups. For
    more information about the `groups` parameter, see `add()`.
    
    If the action was already added to one of the specified groups, it will
    not be added again (call `add()` for that purpose).
    
    By default, the action is added at the end of the list of actions in the
    specified group(s). Pass an integer to the `position` parameter to customize
    the insertion position. A negative value represents an n-th-to-last
    position.
    
    If the action ID is not valid, raise `ValueError`.
    """
    self._check_action_id_is_valid(action_id)
    
    for group in self._process_groups_arg(groups):
      if group not in self._action_items[action_id].groups:
        self._add_action_to_group(self._action_items[action_id], group, position)
  
  def contains(self, action, groups=None, foreach=False):
    """
    Return `True` if the specified action exists, `False` otherwise.
    `action` can be a function or `Invoker` instance.
    
    For information about the `groups` parameter, see `has_action()`.
    
    If `foreach` is `True`, treat the action as a for-each action.
    """
    action_functions = self._get_action_lists_and_functions(
      self._get_action_type(action, foreach))[1]
    
    for group in self._process_groups_arg(groups):
      if action in action_functions[group]:
        return True
    
    return False
  
  def find(self, action, groups=None, foreach=False):
    """
    Return action IDs matching the specified action. `action` can be a
    function or `Invoker` instance.
    
    For information about the `groups` parameter, see `has_action()`.
    
    If `foreach` is `True`, treat the action as a for-each action.
    """
    action_type = self._get_action_type(action, foreach)
    action_lists = self._get_action_lists_and_functions(action_type)[0]
    
    processed_groups = [
      group for group in self._process_groups_arg(groups)
      if group in self.list_groups()]
    
    found_action_ids = []
    
    for group in processed_groups:
      found_action_ids.extend([
        action_item.action_id
        for action_item in action_lists[group]
        if (action_item.action_function == action and action_item.action_type == action_type)
      ])
    
    return found_action_ids
  
  def has_action(self, action_id, groups=None):
    """
    Return `True` if the specified ID (returned from `add()`) belongs to an
    existing action in at least one of the specified groups.
    
    `group` can have one of the following values:
      * `None` or `'default'` - the default group,
      * list of group names (strings) - specific groups,
      * `'all'` - all existing groups.
    """
    return (
      action_id in self._action_items
      and any(group in self._action_items[action_id].groups
              for group in self._process_groups_arg(groups)))
  
  def get_action(self, action_id):
    """
    Return action specified by its ID. If the ID is not valid, return `None`.
    """
    if action_id in self._action_items:
      return self._action_items[action_id].action
    else:
      return None
  
  def get_position(self, action_id, group=None):
    """
    Return the position of the action specified by its ID in the specified
    group. If `group` is `None` or `'default'`, use the default group.
    
    If the ID is not valid or the action is not in the group, raise
    `ValueError`.
    """
    if group is None:
      group = 'default'
    
    self._check_action_id_is_valid(action_id)
    self._check_action_in_group(action_id, group)
    
    action_item = self._action_items[action_id]
    action_lists, unused_ = self._get_action_lists_and_functions(action_item.action_type)
    return action_lists[group].index(action_item)
  
  def list_actions(self, group=None, foreach=False):
    """
    Return all actions, along with their arguments and keyword arguments, for
    the specified group in the order they would be invoked. If the group does
    not exist, return `None`.
    
    If `foreach` is `True`, return for-each actions instead.
    """
    if group is None:
      group = 'default'
    
    if not foreach:
      action_items = self._actions
    else:
      action_items = self._foreach_actions
    
    if group in self._actions:
      return [item.action for item in action_items[group]]
    else:
      return None
  
  def list_groups(self, include_empty_groups=True):
    """
    Return a list of all groups in the invoker.
    
    If `include_empty_groups` is `False`, do not include groups with no
    actions.
    """
    if include_empty_groups:
      return list(self._actions)
    else:
      def _is_group_non_empty(group):
        return any(
          (group in action_lists and action_lists[group])
          for action_lists in [self._actions, self._foreach_actions])
      
      return [group for group in self._actions if _is_group_non_empty(group)]
  
  def reorder(self, action_id, position, group=None):
    """Change the order in which an action is invoked.
    
    The action is specified by its ID (as returned by `add()`).
    
    If `group` is `None` or `'default'`, use the default group.
    
    A position of 0 moves the action to the beginning.
    Negative numbers move the action to the n-th to last position, i.e. -1
    for the last position, -2 for the second to last position, etc.
    
    Raises `ValueError` if:
      * action ID is invalid
      * group does not exist
      * action is not in the group
    """
    if group is None:
      group = 'default'
    
    self._check_action_id_is_valid(action_id)
    self._check_group_exists(group)
    self._check_action_in_group(action_id, group)
    
    action_item = self._action_items[action_id]
    action_lists, unused_ = self._get_action_lists_and_functions(action_item.action_type)
    
    action_lists[group].pop(action_lists[group].index(action_item))
    
    if position < 0:
      position = max(len(action_lists[group]) + position + 1, 0)
    
    action_lists[group].insert(position, action_item)
  
  def remove(self, action_id, groups=None, ignore_if_not_exists=False):
    """
    Remove the action specified by its ID from the specified groups.
    
    For information about the `groups` parameter, see `has_action()`.
    
    For existing groups where the action is not added, do nothing.
    
    If `ignore_if_not_exists` is `True`, do not raise `ValueError` if
    `action_id` does not match any added action.
    
    Raises `ValueError` if:
      * action ID is invalid and `ignore_if_not_exists` is `False`
      * at least one of the specified groups does not exist
    """
    if ignore_if_not_exists:
      if action_id not in self._action_items:
        return
    else:
      self._check_action_id_is_valid(action_id)
    
    action_list, action_functions = self._get_action_lists_and_functions(
      self._action_items[action_id].action_type)
    
    for group in self._process_groups_arg(groups):
      self._check_group_exists(group)
      
      if group in self._action_items[action_id].groups:
        self._remove_action(action_id, group, action_list, action_functions)
        if action_id not in self._action_items:
          break
  
  def remove_groups(self, groups):
    """
    Remove the specified groups and their actions (including for-each
    actions).
    
    For information about the `groups` parameter, see `has_action()`.
    
    Non-existent groups in `groups` are ignored.
    """
    processed_groups = [
      group for group in self._process_groups_arg(groups)
      if group in self.list_groups()]
    
    for group in processed_groups:
      for action_item in self._actions[group]:
        if action_item.action_type == self._TYPE_ACTION:
          self._remove_action(action_item.action_id, group, self._actions, self._action_functions)
        else:
          self._remove_action(action_item.action_id, group, self._actions, self._invokers)
      
      for action_item in self._foreach_actions[group]:
        self._remove_action(
          action_item.action_id, group, self._foreach_actions, self._foreach_action_functions)
      
      del self._actions[group]
      del self._foreach_actions[group]
  
  def _init_group(self, group):
    if group not in self._actions:
      self._actions[group] = []
      self._foreach_actions[group] = []
  
  def _add_action_to_group(self, action_item, group, position):
    if action_item.action_type == self._TYPE_ACTION:
      self._add_action(
        action_item.action_id,
        action_item.action[0],
        group,
        action_item.action[1],
        action_item.action[2],
        position,
        action_item.run_generator)
    elif action_item.action_type == self._TYPE_FOREACH_ACTION:
      self._add_foreach_action(
        action_item.action_id,
        action_item.action[0],
        group,
        action_item.action[1],
        action_item.action[2],
        position,
        action_item.run_generator)
    elif action_item.action_type == self._TYPE_INVOKER:
      self._add_invoker(action_item.action_id, action_item.action, group, position)
  
  def _add_action(
        self, action_id, action, group, action_args, action_kwargs, position, run_generator):
    self._init_group(group)
    
    action_item = self._set_action_item(
      action_id,
      group,
      (action, action_args, action_kwargs),
      self._TYPE_ACTION,
      action,
      run_generator)
    
    if position is None:
      self._actions[group].append(action_item)
    else:
      self._actions[group].insert(position, action_item)
    
    self._action_functions[group][action] += 1
  
  def _add_foreach_action(
        self,
        action_id,
        foreach_action,
        group,
        foreach_action_args,
        foreach_action_kwargs,
        position,
        run_generator):
    self._init_group(group)
    
    if not inspect.isgeneratorfunction(foreach_action):
      def invoke_foreach_action_after_action(*args, **kwargs):
        yield
        foreach_action(*args, **kwargs)
      
      foreach_action_generator_function = invoke_foreach_action_after_action
    else:
      foreach_action_generator_function = foreach_action
    
    action_item = self._set_action_item(
      action_id,
      group,
      (foreach_action_generator_function,
       foreach_action_args,
       foreach_action_kwargs),
      self._TYPE_FOREACH_ACTION,
      foreach_action,
      run_generator)
    
    if position is None:
      self._foreach_actions[group].append(action_item)
    else:
      self._foreach_actions[group].insert(position, action_item)
    
    self._foreach_action_functions[group][foreach_action] += 1
  
  def _add_invoker(self, action_id, invoker, group, position):
    self._init_group(group)
    
    action_item = self._set_action_item(
      action_id, group, invoker, self._TYPE_INVOKER, invoker, False)
    
    if position is None:
      self._actions[group].append(action_item)
    else:
      self._actions[group].insert(position, action_item)
    
    self._invokers[group][invoker] += 1
  
  def _get_action_id(self):
    return self._action_id_counter.next()
  
  def _set_action_item(
        self,
        action_id,
        group,
        action,
        action_type,
        action_function,
        run_generator):
    if action_id not in self._action_items:
      self._action_items[action_id] = _ActionItem(
        action, action_id, None, action_type, action_function, run_generator)
    
    self._action_items[action_id].groups.add(group)
    
    return self._action_items[action_id]
  
  def _remove_action(self, action_id, group, action_lists, action_functions):
    action_item = self._action_items[action_id]
    action_lists[group].remove(action_item)
    
    action_functions[group][action_item.action_function] -= 1
    if action_functions[group][action_item.action_function] == 0:
      del action_functions[group][action_item.action_function]
    
    self._remove_action_item(action_id, group)
  
  def _remove_action_item(self, action_id, group):
    self._action_items[action_id].groups.remove(group)
    
    if not self._action_items[action_id].groups:
      del self._action_items[action_id]
  
  def _process_groups_arg(self, groups):
    if groups is None or groups == 'default':
      return ['default']
    elif groups == 'all':
      return self.list_groups()
    else:
      return groups
  
  def _get_action_type(self, action, is_foreach):
    if is_foreach:
      return self._TYPE_FOREACH_ACTION
    else:
      if callable(action):
        return self._TYPE_ACTION
      else:
        return self._TYPE_INVOKER
  
  def _get_action_lists_and_functions(self, action_type):
    if action_type == self._TYPE_ACTION:
      return self._actions, self._action_functions
    elif action_type == self._TYPE_FOREACH_ACTION:
      return self._foreach_actions, self._foreach_action_functions
    elif action_type == self._TYPE_INVOKER:
      return self._actions, self._invokers
    else:
      raise ValueError(
        'invalid action type {}; must be one of {}'.format(action_type, self._ACTION_TYPES))
  
  def _check_action_id_is_valid(self, action_id):
    if action_id not in self._action_items:
      raise ValueError('action with ID {} does not exist'.format(action_id))
  
  def _check_group_exists(self, group, groups=None):
    if groups is None:
      groups = self.list_groups()
    
    if group not in groups:
      raise ValueError('group "{}" does not exist'.format(group))
  
  def _check_action_in_group(self, action_id, group):
    if group not in self._action_items[action_id].groups:
      raise ValueError('action with ID {} is not in group "{}"'.format(action_id, group))


class _ActionItem(object):
  
  def __init__(self, action, action_id, groups, action_type, action_function, run_generator):
    self.action = action
    self.action_id = action_id
    self.groups = groups if groups is not None else set()
    self.action_type = action_type if action_type is not None else Invoker._TYPE_ACTION
    self.action_function = action_function
    self.run_generator = run_generator
    
    self.is_generator = False
    self.generators_per_group = {}
    self.should_be_removed_from_group = False
