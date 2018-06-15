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
This module provides the means to manipulate a list of functions (operations)
executed sequentially.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import collections
import inspect
import itertools

#===============================================================================


class OperationExecutor(object):
  
  _OPERATION_TYPES = _TYPE_OPERATION, _TYPE_FOREACH_OPERATION, _TYPE_EXECUTOR = (0, 1, 2)
  
  def __init__(self):
    # key: operation group; value: list of `_OperationItem` instances
    self._operations = collections.OrderedDict()
    
    # key: operation group; value: list of `_OperationItem` instances
    self._foreach_operations = collections.OrderedDict()
    
    # key: operation group; value: dict of (operation function: count) pairs
    self._operation_functions = collections.defaultdict(
      lambda: collections.defaultdict(int))
    
    # key: operation group; value: dict of (operation function: count) pairs
    self._foreach_operation_functions = collections.defaultdict(
      lambda: collections.defaultdict(int))
    
    # key: operation group
    # value: dict of (`OperationExecutor` instance: count) pairs
    self._executors = collections.defaultdict(lambda: collections.defaultdict(int))
    
    self._operation_id_counter = itertools.count(start=1)
    
    # key: operation ID; value: `_OperationItem` instance
    self._operation_items = {}
  
  def execute(self, groups=None, additional_args=None, additional_kwargs=None):
    """
    Execute operations.
    
    If `groups` is None or "default", execute operations in the default group.
    
    If `groups` is a list of group names (strings), execute operations in the
    specified groups.
    
    If `groups` is "all", execute operations in all existing groups.
    
    If any of the `groups` do not exist, raise `ValueError`.
    
    If `operation` is an `OperationExecutor` instance, the instance will execute
    operations in the specified groups.
    
    Additional arguments and keyword arguments to all operations in the group
    are given by `additional_args` and `additional_kwargs`, respectively.
    `additional_args` are appended at the end of argument list. If some keyword
    arguments appear in both the keyword arguments to the `kwargs` argument in
    the `add` method and `additional_kwargs`, the values from the latter
    override the former.
    """
    
    def _execute_operation(operation, operation_args, operation_kwargs):
      args = tuple(operation_args) + tuple(additional_args)
      kwargs = dict(operation_kwargs, **additional_kwargs)
      return operation(*args, **kwargs)
    
    def _execute_operation_with_foreach_operations(
          operation, operation_args, operation_kwargs, group):
      operation_generators = [
        _execute_operation(*item.operation)
        for item in self._foreach_operations[group]]
      
      _execute_foreach_operations_once(operation_generators)
      
      while operation_generators:
        result_from_operation = _execute_operation(
          operation, operation_args, operation_kwargs)
        _execute_foreach_operations_once(operation_generators, result_from_operation)
    
    def _execute_foreach_operations_once(
          operation_generators, result_from_operation=None):
      operation_generators_to_remove = []
      
      for operation_generator in operation_generators:
        try:
          operation_generator.send(result_from_operation)
        except StopIteration:
          operation_generators_to_remove.append(operation_generator)
      
      for operation_generator_to_remove in operation_generators_to_remove:
        operation_generators.remove(operation_generator_to_remove)
    
    def _execute_executor(executor, group):
      executor.execute([group], additional_args, additional_kwargs)
    
    additional_args = additional_args if additional_args is not None else ()
    additional_kwargs = additional_kwargs if additional_kwargs is not None else {}
    
    for group in self._process_groups_arg(groups):
      if group not in self._operations:
        self._init_group(group)
      
      for item in self._operations[group]:
        if item.operation_type != self._TYPE_EXECUTOR:
          operation, operation_args, operation_kwargs = item.operation
          if self._foreach_operations[group]:
            _execute_operation_with_foreach_operations(
              operation, operation_args, operation_kwargs, group)
          else:
            _execute_operation(operation, operation_args, operation_kwargs)
        else:
          _execute_executor(item.operation, group)
  
  def add(self, operation, groups=None, args=None, kwargs=None, foreach=False):
    """
    Add an operation to be executed by `execute`. Return the ID of the newly
    added operation.
    
    The operation can be:
    * a function, in which case optional arguments (`args`, a list or tuple) and
      keyword arguments (`kwargs`, a dict) can be specified,
    * an `OperationExecutor` instance.
    
    To control which operations are executed, you may want to group them.
    
    If `groups` is None or "default", the operation is added to a default group
    appropriately named "default".
    
    If `groups` is a list of group names (strings), the operation is added to
    the specified groups. Groups are created automatically if they previously
    did not exist.
    
    If `groups` is "all", the operation is added to all existing groups. The
    operation will not be added to the default group if it does not exist.
    
    The operation is added at the end of the list of operations in the specified
    group(s). To modify the order of the added operation, use the `reorder`
    method.
    
    If `foreach` is True and the operation is a function, the operation is
    treated as a "for-each" operation. By default, a for-each operation is
    executed after each regular operation or `OperationExecutor` instance. To
    customize this behavior, use the `yield` statement in the for-each operation
    to specify where it is desired to execute each operation. For example:
    
      def foo():
        print("bar")
        yield
        print("baz")
    
    first prints "bar", then executes the operation and finally prints "baz".
    Multiple `yield` statements can be specified to execute the wrapped
    operation multiple times.
    
    If multiple for-each operations are added, they are executed in the order
    they were added by this method. For example:
      
      def foo1():
        print("bar1")
        yield
        print("baz1")
      
      def foo2():
        print("bar2")
        yield
        print("baz2")
    
    will print "bar1", "bar2", then execute the operation (only once), and then
    print "baz1" and "baz2".
    """
    
    operation_id = self._get_operation_id()
    
    if isinstance(operation, self.__class__):
      for group in self._process_groups_arg(groups):
        self._add_executor(operation_id, operation, group)
    else:
      if not foreach:
        add_operation_func = self._add_operation
      else:
        add_operation_func = self._add_foreach_operation
      
      for group in self._process_groups_arg(groups):
        add_operation_func(
          operation_id, operation, group,
          args if args is not None else (),
          kwargs if kwargs is not None else {})
    
    return operation_id
  
  def add_to_groups(self, operation_id, groups=None):
    """
    Add an existing operation specified by its ID to the specified operation
    groups. For more information about the `groups` parameter, see `add`.
    
    If the operation was already added to one of the specified groups, it will
    not be added again (use the `add` method for that purpose).
    
    If the operation ID is not valid, raise `ValueError`.
    """
    
    self._check_operation_id_is_valid(operation_id)
    
    for group in self._process_groups_arg(groups):
      if group not in self._operation_items[operation_id].groups:
        self._add_operation_to_group(self._operation_items[operation_id], group)
  
  def has_operation(self, operation_id, groups=None):
    """
    Return True if the specified ID (returned from the `add` method) belongs to
    an existing operation in at least one of the specified groups.
    
    `group` can have one of the following values:
      * None or "default" - the default group,
      * list of group names (strings) - specific groups,
      * "all" - all existing groups.
    """
    
    return (
      operation_id in self._operation_items
      and any(group in self._operation_items[operation_id].groups
              for group in self._process_groups_arg(groups)))
  
  def has_matching_operation(self, operation, groups=None, foreach=False):
    """
    Return True if the specified operation exists, False otherwise. `operation`
    can be a function or `OperationExecutor` instance.
    
    For information about the `groups` parameter, see `has_operation`.
    
    If `foreach` is True, treat the operation as a for-each operation.
    """
    
    operation_functions = self._get_operation_lists_and_functions(
      self._get_operation_type(operation, foreach))[1]
    
    for group in self._process_groups_arg(groups):
      if operation in operation_functions[group]:
        return True
    
    return False
  
  def find_matching_operations(self, operation, groups=None, foreach=False):
    """
    Return operation IDs matching the specified operation. `operation` can be a
    function or `OperationExecutor` instance.
    
    For information about the `groups` parameter, see `has_operation`.
    
    If `foreach` is True, treat the operation as a for-each operation.
    """
    
    operation_type = self._get_operation_type(operation, foreach)
    operation_lists = self._get_operation_lists_and_functions(operation_type)[0]
    
    processed_groups = [
      group for group in self._process_groups_arg(groups)
      if group in self.get_groups()]
    
    found_operation_ids = []
    
    for group in processed_groups:
      found_operation_ids.extend([
        operation_item.operation_id
        for operation_item in operation_lists[group]
        if (operation_item.operation_function == operation
            and operation_item.operation_type == operation_type)])
    
    return found_operation_ids
  
  def get_operation(self, operation_id):
    """
    Return operation specified by its ID. If the ID is not valid, return None.
    """
    
    if operation_id in self._operation_items:
      return self._operation_items[operation_id].operation
    else:
      return None
  
  def get_operation_position(self, operation_id, group=None):
    """
    Return the position of the operation specified by its ID in the specified
    group. If `group` is None or "default", use the default group.
    
    If the ID is not valid or the operation is not in the group, raise
    `ValueError`.
    """
    
    if group is None:
      group = "default"
    
    self._check_operation_id_is_valid(operation_id)
    self._check_operation_in_group(operation_id, group)
    
    operation_item = self._operation_items[operation_id]
    operation_lists, unused_ = self._get_operation_lists_and_functions(
      operation_item.operation_type)
    return operation_lists[group].index(operation_item)
  
  def get_operations(self, group=None, foreach=False):
    """
    Return all operations, along with their arguments and keyword arguments for
    the operation group in their execution order. If the group does not exist,
    return None.
    
    If `foreach` is True, return for-each operations instead.
    """
    
    if group is None:
      group = "default"
    
    if not foreach:
      operation_items = self._operations
    else:
      operation_items = self._foreach_operations
    
    if group in self._operations:
      return [item.operation for item in operation_items[group]]
    else:
      return None
  
  def get_groups(self, include_empty_groups=True):
    """
    Return a list of all groups in the executor.
    
    If `include_empty_groups` is False, do not include groups with no
    operations.
    """
    
    if include_empty_groups:
      return list(self._operations)
    else:
      def _is_group_non_empty(group):
        return any(
          (group in operation_lists and operation_lists[group])
          for operation_lists in [self._operations, self._foreach_operations])
      
      return [group for group in self._operations
              if _is_group_non_empty(group)]
  
  def reorder(self, operation_id, position, group=None):
    """
    Change the execution order of the operation specified by its ID in the
    specified operation group to the specified position. If `group` is None or
    "default", use the default group.
    
    A position of 0 moves the operation to the beginning of the execution order.
    Negative numbers move the operation to the n-th to last position, i.e. -1
    for the last position, -2 for the second to last position, etc.
    
    Raises `ValueError` if:
      * operation ID is invalid
      * operation group does not exist
      * operation is not in the specified group
    """
    
    if group is None:
      group = "default"
    
    self._check_operation_id_is_valid(operation_id)
    self._check_group_exists(group)
    self._check_operation_in_group(operation_id, group)
    
    operation_item = self._operation_items[operation_id]
    operation_lists, unused_ = self._get_operation_lists_and_functions(
      operation_item.operation_type)
    
    operation_lists[group].pop(
      operation_lists[group].index(operation_item))
    
    if position < 0:
      position = max(len(operation_lists[group]) + position + 1, 0)
    
    operation_lists[group].insert(position, operation_item)
  
  def remove(self, operation_id, groups=None):
    """
    Remove the operation specified by its ID from the specified operation
    groups.
    
    For information about the `groups` parameter, see `has_operation`.
    
    For existing groups where the operation is not added, do nothing.
    
    Raises `ValueError` if:
      * operation ID is invalid
      * at least one of the specified groups does not exist
    """
    
    self._check_operation_id_is_valid(operation_id)
    
    operation_list, operation_functions = (
      self._get_operation_lists_and_functions(
        self._operation_items[operation_id].operation_type))
    
    for group in self._process_groups_arg(groups):
      self._check_group_exists(group)
      
      if group in self._operation_items[operation_id].groups:
        self._remove_operation(
          operation_id, group, operation_list, operation_functions)
        if operation_id not in self._operation_items:
          break
  
  def remove_groups(self, groups=None):
    """
    Remove the specified groups and their operations (including for-each
    operations).
    
    For information about the `groups` parameter, see `has_operation`.
    
    Non-existent groups in `groups` are ignored.
    """
    
    processed_groups = [
      group for group in self._process_groups_arg(groups)
      if group in self.get_groups()]
    
    for group in processed_groups:
      for operation_item in self._operations[group]:
        if operation_item.operation_type == self._TYPE_OPERATION:
          self._remove_operation(
            operation_item.operation_id, group, self._operations,
            self._operation_functions)
        else:
          self._remove_operation(
            operation_item.operation_id, group, self._operations,
            self._executors)
      
      for operation_item in self._foreach_operations[group]:
        self._remove_operation(
          operation_item.operation_id, group, self._foreach_operations,
          self._foreach_operation_functions)
      
      del self._operations[group]
      del self._foreach_operations[group]
  
  def _init_group(self, group):
    if group not in self._operations:
      self._operations[group] = []
      self._foreach_operations[group] = []
  
  def _add_operation_to_group(self, operation_item, group):
    if operation_item.operation_type == self._TYPE_OPERATION:
      self._add_operation(
        operation_item.operation_id, operation_item.operation[0], group,
        operation_item.operation[1], operation_item.operation[2])
    elif operation_item.operation_type == self._TYPE_FOREACH_OPERATION:
      self._add_foreach_operation(
        operation_item.operation_id, operation_item.operation[0], group,
        operation_item.operation[1], operation_item.operation[2])
    elif operation_item.operation_type == self._TYPE_EXECUTOR:
      self._add_executor(
        operation_item.operation_id, operation_item.operation, group)
  
  def _add_operation(
        self, operation_id, operation, group, operation_args, operation_kwargs):
    self._init_group(group)
    
    operation_item = self._set_operation_item(
      operation_id, group, (operation, operation_args, operation_kwargs),
      self._TYPE_OPERATION, operation)
    
    self._operations[group].append(operation_item)
    self._operation_functions[group][operation] += 1
  
  def _add_foreach_operation(
        self, operation_id, foreach_operation, group,
        foreach_operation_args, foreach_operation_kwargs):
    self._init_group(group)
    
    if not inspect.isgeneratorfunction(foreach_operation):
      def execute_foreach_operation_after_operation(*args, **kwargs):
        yield
        foreach_operation(*args, **kwargs)
      
      foreach_operation_generator_function = execute_foreach_operation_after_operation
    else:
      foreach_operation_generator_function = foreach_operation
    
    operation_item = self._set_operation_item(
      operation_id, group,
      (foreach_operation_generator_function,
       foreach_operation_args, foreach_operation_kwargs),
      self._TYPE_FOREACH_OPERATION, foreach_operation)
    
    self._foreach_operations[group].append(operation_item)
    self._foreach_operation_functions[group][foreach_operation] += 1
  
  def _add_executor(self, operation_id, executor, group):
    self._init_group(group)
    
    operation_item = self._set_operation_item(
      operation_id, group, executor,
      self._TYPE_EXECUTOR, executor)
    
    self._operations[group].append(operation_item)
    self._executors[group][executor] += 1
  
  def _get_operation_id(self):
    return self._operation_id_counter.next()
  
  def _set_operation_item(
        self, operation_id, group, operation,
        operation_type, operation_function):
    if operation_id not in self._operation_items:
      self._operation_items[operation_id] = _OperationItem(
        operation, operation_id, None, operation_type, operation_function)
    
    self._operation_items[operation_id].groups.add(group)
    
    return self._operation_items[operation_id]
  
  def _remove_operation(
        self, operation_id, group, operation_lists, operation_functions):
    operation_item = self._operation_items[operation_id]
    operation_lists[group].remove(operation_item)
    
    operation_functions[group][operation_item.operation_function] -= 1
    if operation_functions[group][operation_item.operation_function] == 0:
      del operation_functions[group][operation_item.operation_function]
    
    self._remove_operation_item(operation_id, group)
  
  def _remove_operation_item(self, operation_id, group):
    self._operation_items[operation_id].groups.remove(group)
    
    if not self._operation_items[operation_id].groups:
      del self._operation_items[operation_id]
  
  def _process_groups_arg(self, groups):
    if groups is None or groups == "default":
      return ["default"]
    elif groups == "all":
      return self.get_groups()
    else:
      return groups
  
  def _get_operation_type(self, operation, is_foreach):
    if is_foreach:
      return self._TYPE_FOREACH_OPERATION
    else:
      if isinstance(operation, self.__class__):
        return self._TYPE_EXECUTOR
      else:
        return self._TYPE_OPERATION
  
  def _get_operation_lists_and_functions(self, operation_type):
    if operation_type == self._TYPE_OPERATION:
      return self._operations, self._operation_functions
    elif operation_type == self._TYPE_FOREACH_OPERATION:
      return self._foreach_operations, self._foreach_operation_functions
    elif operation_type == self._TYPE_EXECUTOR:
      return self._operations, self._executors
    else:
      raise ValueError(
        "invalid operation type {0}; must be one of {1}".format(
          operation_type, self._OPERATION_TYPES))
  
  def _check_operation_id_is_valid(self, operation_id):
    if operation_id not in self._operation_items:
      raise ValueError("operation with ID {0} does not exist".format(operation_id))
  
  def _check_group_exists(self, group, groups=None):
    if groups is None:
      groups = self.get_groups()
    
    if group not in groups:
      raise ValueError("operation group '{0}' does not exist".format(group))
  
  def _check_operation_in_group(self, operation_id, group):
    if group not in self._operation_items[operation_id].groups:
      raise ValueError("operation with ID {0} is not in group '{1}'".format(
        operation_id, group))

  
class _OperationItem(object):
  
  def __init__(
        self, operation, operation_id, groups, operation_type,
        operation_function):
    self.operation = operation
    self.operation_id = operation_id
    self.groups = groups if groups is not None else set()
    self.operation_type = (
      operation_type if operation_type is not None else OperationExecutor._TYPE_OPERATION)
    self.operation_function = operation_function
