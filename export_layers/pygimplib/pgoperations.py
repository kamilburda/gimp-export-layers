# -*- coding: utf-8 -*-
#
# This file is part of pygimplib.
#
# Copyright (C) 2014-2016 khalim19 <khalim19@gmail.com>
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

"""
This module provides the means to manipulate a list of operations executed
sequentially.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import future.standard_library
future.standard_library.install_aliases()

from future.builtins import *

import collections
import inspect

#===============================================================================


class OperationsExecutor(object):
  
  _OPERATION_TYPES = OPERATION, FOREACH_OPERATION, EXECUTOR = (0, 1, 2)
  
  class _OperationItem(object):
    def __init__(self, operation, operation_id, operation_groups, operation_type, operation_function):
      self.operation = operation
      self.operation_id = operation_id
      self.operation_groups = operation_groups if operation_groups is not None else set()
      self.operation_type = operation_type if operation_type is not None else OperationsExecutor.OPERATION
      self.operation_function = operation_function
  
  def __init__(self):
    # key: operation group; value: list of `_OperationItem` instances
    self._operations = collections.OrderedDict()
    # key: operation group; value: list of `_OperationItem` instances
    self._foreach_operations = collections.OrderedDict()
    
    # key: operation group; value: dict of (operation function: count) pairs
    self._operations_functions = collections.defaultdict(lambda: collections.defaultdict(int))
    # key: operation group; value: dict of (operation function: count) pairs
    self._foreach_operations_functions = collections.defaultdict(lambda: collections.defaultdict(int))
    # key: operation group; value: dict of (`OperationsExecutor` instance: count) pairs
    self._operations_executors = collections.defaultdict(lambda: collections.defaultdict(int))
    
    self._operation_id_counter = 1
    
    # key: operation ID; value: `_OperationItem` instance
    self._operation_items = {}
  
  def execute(self, operation_groups, *additional_operation_args, **additional_operation_kwargs):
    """
    Execute all operations belonging to the groups in the order given by
    `operation_groups`.
    
    Additional arguments and keyword arguments to all operations in the group
    are given by `*additional_operation_args` and
    `**additional_operation_kwargs`, respectively. `*additional_operation_args`
    are appended at the end of argument list. If some keyword arguments appear
    in both the keyword arguments to the `**operation_kwargs` argument in the
    `add_operation` method and `**additional_operation_kwargs`, the values from
    the latter override the former.
    
    If any of the `operation_groups` do not exist (i.e. do not have any
    operations), raise `ValueError`.
    """
    
    def _execute_operation(operation, operation_args, operation_kwargs):
      args = operation_args + additional_operation_args
      kwargs = dict(operation_kwargs, **additional_operation_kwargs)
      return operation(*args, **kwargs)
    
    def _execute_operation_with_foreach_operations(operation, operation_args, operation_kwargs):
      operation_generators = [
        _execute_operation(*item.operation) for item in self._foreach_operations[operation_group]]
      
      _execute_foreach_operations_once(operation_generators)
      
      while operation_generators:
        result_from_operation = _execute_operation(operation, operation_args, operation_kwargs)
        _execute_foreach_operations_once(operation_generators, result_from_operation)
    
    def _execute_foreach_operations_once(operation_generators, result_from_operation=None):
      operation_generators_to_remove = []
      
      for operation_generator in operation_generators:
        try:
          operation_generator.send(result_from_operation)
        except StopIteration:
          operation_generators_to_remove.append(operation_generator)
      
      for operation_generator_to_remove in operation_generators_to_remove:
        operation_generators.remove(operation_generator_to_remove)
    
    def _execute_executor(executor, operation_group):
      executor.execute([operation_group], *additional_operation_args, **additional_operation_kwargs)
    
    for operation_group in operation_groups:
      if operation_group not in self._operations:
        self._init_operation_group(operation_group)
      
      for item in self._operations[operation_group]:
        if item.operation_type != self.EXECUTOR:
          operation, operation_args, operation_kwargs = item.operation
          if self._foreach_operations[operation_group]:
            _execute_operation_with_foreach_operations(operation, operation_args, operation_kwargs)
          else:
            _execute_operation(operation, operation_args, operation_kwargs)
        else:
          _execute_executor(item.operation, operation_group)
  
  def add_operation(self, operation, operation_groups, *operation_args, **operation_kwargs):
    """
    Add an operation specified by its function `operation`, its arguments
    `*operation_args` (as a list or tuple) and keyword arguments
    `**operation_kwargs` (as a dict), to the operation groups given by
    `operation_groups`. Return the ID of the newly added operation.
    
    The operation groups are created automatically if no operations were added
    to them before.
    
    The operation is added at the end of the list of operations. To modify the
    order of the added operation, call the `reorder_operation` method.
    """
    
    operation_id = self._get_operation_id()
    
    for operation_group in operation_groups:
      self._add_operation(operation_id, operation, operation_group, operation_args, operation_kwargs)
    
    return operation_id
  
  def add_foreach_operation(self, foreach_operation, operation_groups,
                            *foreach_operation_args, **foreach_operation_kwargs):
    """
    Add an operation to be executed for each operation in groups given by
    `operation_groups`. `foreach_operation` is the function to be executed,
    along with its arguments `*foreach_operation_args` and keyword arguments
    `**foreach_operation_kwargs`. Return the ID of the newly added operation.
    
    By default, `foreach_operation` is executed after each operation. To
    customize this behavior, use the `yield` statement to specify where it is
    desired to execute the operation. For example:
    
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
    
    foreach_operation_id = self._get_operation_id()
    
    for operation_group in operation_groups:
      self._add_foreach_operation(
        foreach_operation_id, foreach_operation, operation_group,
        foreach_operation_args, foreach_operation_kwargs)
    
    return foreach_operation_id
  
  def add_executor(self, operations_executor, operation_groups=None):
    """
    Add an existing `OperationsExecutor` instance to be executed in the list of
    operations. The operations will be kept up-to-date if the executor changes.
    Return the ID of the added executor.
    
    `operation_groups` is a list of groups from which to add operations. If
    `operation_groups` is None, add operations from all groups from the
    executor.
    """
    
    executor_id = self._get_operation_id()
    
    if operation_groups is None:
      operation_groups = self.get_operation_groups()
    
    for operation_group in operation_groups:
      self._add_executor(executor_id, operations_executor, operation_group)
    
    return executor_id
  
  def add_operation_to_groups(self, operation_id, operation_groups):
    """
    Add an existing operation, for-each operation or executor to the specified
    operation groups. If the operation was already added to one of the specified
    groups, it will not be added again (to do that, use the `add_operation`
    method). If the ID is not valid, raise `ValueError`.
    """
    
    self._check_operation_id_is_valid(operation_id)
    
    for operation_group in operation_groups:
      if operation_group not in self._operation_items[operation_id].operation_groups:
        self._add_operation_to_group(self._operation_items[operation_id], operation_group)
  
  def has_operation(self, operation_id, operation_group=None):
    """
    Return True if the specified ID belongs to an existing operation, for-each
    operation or a nested `OperationsExecutor`.
    
    If `operation_group` is specified, return True if the ID exists in the
    group. If `operation_group` is None, return True if the ID exists in any of
    the existing groups.
    
    The ID is returned from `add_operation`, `add_foreach_operation` and
    `add_executor`.
    """
    
    if operation_group is None:
      return (operation_id in self._operation_items
              and bool(self._operation_items[operation_id].operation_groups))
    else:
      return (operation_id in self._operation_items
              and operation_group in self._operation_items[operation_id].operation_groups)
  
  def has_matching_operation(self, operation, operation_group, operation_type=OPERATION):
    """
    Return True if the specified operation of the specified type is added to the
    list of operations in group `operation_group`, False otherwise.
    
    `operation_type` can be one of the following:
    
      * OPERATION - regular operation
      
      * FOREACH_OPERATION - for-each operation
      
      * EXECUTOR - `OperationsExecutor` instance
    """
    
    return operation in self._get_operation_lists_and_functions(operation_type)[1][operation_group]
  
  def find_matching_operations(self, operation, operation_group, operation_type=OPERATION):
    """
    Find all operations matching the specified operation in the specified group.
    
    `operation_type` must be one of the following:
    
      * OPERATION - regular operation
      
      * FOREACH_OPERATION - for-each operation
      
      * EXECUTOR - `OperationsExecutor` instance
    
    If the operation group does not exist or the operation type is not valid,
    raise `ValueError`.
    """
    
    self._check_operation_group_exists(operation_group)
    
    operations_lists, _unused = self._get_operation_lists_and_functions(operation_type)
    
    return [operation_item.operation_id for operation_item in operations_lists[operation_group]
            if (operation_item.operation_function == operation
                and operation_item.operation_type == operation_type)]
  
  def get_operation(self, operation_id):
    """
    Get the operation, for-each operation or executor by its ID. If the ID is
    not valid, return None.
    """
    
    if operation_id in self._operation_items:
      return self._operation_items[operation_id].operation
    else:
      return None
  
  def get_operation_positon(self, operation_id, operation_group):
    """
    Get the position of the operation, for-each operation or executor specified
    by its ID in the specified group.
    
    If the ID is not valid or the operation is not in the group, raise
    `ValueError`.
    """
    
    self._check_operation_id_is_valid(operation_id)
    self._check_operation_in_group(operation_id, operation_group)
    
    operation_item = self._operation_items[operation_id]
    operations_lists, _unused = self._get_operation_lists_and_functions(operation_item.operation_type)
    return operations_lists[operation_group].index(operation_item)
  
  def get_operations(self, operation_group):
    """
    Return all operations (along with their arguments and keyword arguments) and
    executors for the operation group in their execution order. If the group
    does not exist, return None.
    """
    
    if operation_group in self._operations:
      return [item.operation for item in self._operations[operation_group]]
    else:
      return None
  
  def get_foreach_operations(self, operation_group):
    """
    Return all for-each operations for the operation group in their execution
    order. If the group does not exist, return None.
    """
    
    if operation_group in self._foreach_operations:
      return [item.operation for item in self._foreach_operations[operation_group]]
    else:
      return None
  
  def get_operation_groups(self, include_empty_groups=True):
    """
    Return a list of all groups in the executor.
    
    If `include_empty_groups` is False, do not include groups with no
    operations, for-each operations or executors.
    """
    
    if include_empty_groups:
      return list(self._operations.keys())
    else:
      def _is_group_non_empty(operation_group):
        return any(
          (operation_group in operation_lists and operation_lists[operation_group])
          for operation_lists in [self._operations, self._foreach_operations])
      
      return [operation_group for operation_group in self._operations.keys()
              if _is_group_non_empty(operation_group)]
  
  def reorder_operation(self, operation_id, operation_group, position):
    """
    Change the execution order of the operation specified by its ID in the
    specified operation group to the specified position.
    
    A position of 0 moves the operation to the beginning of the execution order.
    Negative numbers move the operation to the n-th to last position, i.e. -1
    for the last position, -2 for the second to last position, etc.
    
    Raises:
    
    * `ValueError`:
      
      * invalid operation ID
      * operation group does not exist
      * operation is not in the specified group
    """
    
    self._check_operation_id_is_valid(operation_id)
    self._check_operation_group_exists(operation_group)
    self._check_operation_in_group(operation_id, operation_group)
    
    operation_item = self._operation_items[operation_id]
    operation_lists, _unused = self._get_operation_lists_and_functions(operation_item.operation_type)
    
    operation_lists[operation_group].pop(operation_lists[operation_group].index(operation_item))
    
    if position < 0:
      position = max(len(operation_lists[operation_group]) + position + 1, 0)
    
    operation_lists[operation_group].insert(position, operation_item)
  
  def remove_operation(self, operation_id, operation_groups=None):
    """
    Remove the operation specified by its ID from the specified operation
    groups. If `operation_groups` is None, remove the operation from all groups.
    If the ID is invalid, raise `ValueError`.
      
    For existing groups where the operation is not added, do nothing. If at
    least one of the specified groups do not exist, raise `ValueError`.
    """
    
    self._check_operation_id_is_valid(operation_id)
    
    operations_list, operations_functions = (
      self._get_operation_lists_and_functions(self._operation_items[operation_id].operation_type))
    
    existing_operation_groups = self.get_operation_groups()
    
    if operation_groups is None:
      operation_groups = existing_operation_groups
    
    for operation_group in operation_groups:
      self._check_operation_group_exists(operation_group, existing_operation_groups)
      
      if operation_group in self._operation_items[operation_id].operation_groups:
        self._remove_operation(operation_id, operation_group, operations_list, operations_functions)
        if operation_id not in self._operation_items:
          break
  
  def remove_groups(self, operation_groups=None):
    """
    Remove the specified groups and their operations (including for-each
    operations and nested executors).
    
    If `operation_groups` is None, remove all groups, i.e. clear the entire
    executor.
    """
    
    existing_operation_groups = self.get_operation_groups()
    
    if operation_groups is None:
      operation_groups = existing_operation_groups
    
    for operation_group in operation_groups:
      self._check_operation_group_exists(operation_group, existing_operation_groups)
      
      for operation_item in self._operations[operation_group]:
        if operation_item.operation_type == self.OPERATION:
          self._remove_operation(
            operation_item.operation_id, operation_group, self._operations, self._operations_functions)
        else:
          self._remove_operation(
            operation_item.operation_id, operation_group, self._operations, self._operations_executors)
      
      for operation_item in self._foreach_operations[operation_group]:
        self._remove_operation(
          operation_item.operation_id, operation_group, self._foreach_operations,
          self._foreach_operations_functions)
      
      del self._operations[operation_group]
      del self._foreach_operations[operation_group]
  
  def _init_operation_group(self, operation_group):
    if operation_group not in self._operations:
      self._operations[operation_group] = []
      self._foreach_operations[operation_group] = []
  
  def _add_operation_to_group(self, operation_item, operation_group):
    if operation_item.operation_type == self.OPERATION:
      self._add_operation(
        operation_item.operation_id, operation_item.operation[0], operation_group,
        operation_item.operation[1], operation_item.operation[2])
    elif operation_item.operation_type == self.FOREACH_OPERATION:
      self._add_foreach_operation(
        operation_item.operation_id, operation_item.operation[0], operation_group,
        operation_item.operation[1], operation_item.operation[2])
    elif operation_item.operation_type == self.EXECUTOR:
      self._add_executor(
        operation_item.operation_id, operation_item.operation, operation_group)
  
  def _add_operation(self, operation_id, operation, operation_group, operation_args, operation_kwargs):
    self._init_operation_group(operation_group)
    
    operation_item = self._set_operation_item(
      operation_id, operation_group, (operation, operation_args, operation_kwargs), self.OPERATION, operation)
    
    self._operations[operation_group].append(operation_item)
    self._operations_functions[operation_group][operation] += 1
  
  def _add_foreach_operation(self, operation_id, foreach_operation, operation_group,
                             foreach_operation_args, foreach_operation_kwargs):
    self._init_operation_group(operation_group)
    
    if not inspect.isgeneratorfunction(foreach_operation):
      def execute_foreach_operation_after_operation(*args, **kwargs):
        yield
        foreach_operation(*args, **kwargs)
      
      foreach_operation_generator_function = execute_foreach_operation_after_operation
    else:
      foreach_operation_generator_function = foreach_operation
    
    operation_item = self._set_operation_item(
      operation_id, operation_group,
      (foreach_operation_generator_function, foreach_operation_args, foreach_operation_kwargs),
      self.FOREACH_OPERATION, foreach_operation)
    
    self._foreach_operations[operation_group].append(operation_item)
    self._foreach_operations_functions[operation_group][foreach_operation] += 1
  
  def _add_executor(self, operation_id, operations_executor, operation_group):
    self._init_operation_group(operation_group)
    
    operation_item = self._set_operation_item(
      operation_id, operation_group, operations_executor, self.EXECUTOR, operations_executor)
    
    self._operations[operation_group].append(operation_item)
    self._operations_executors[operation_group][operations_executor] += 1
  
  def _get_operation_id(self):
    operation_id = self._operation_id_counter
    self._operation_id_counter += 1
    
    return operation_id
  
  def _set_operation_item(self, operation_id, operation_group, operation,
                          operation_type, operation_function):
    if operation_id not in self._operation_items:
      self._operation_items[operation_id] = self._OperationItem(
        operation, operation_id, None, operation_type, operation_function)
    
    self._operation_items[operation_id].operation_groups.add(operation_group)
    
    return self._operation_items[operation_id]
  
  def _remove_operation(self, operation_id, operation_group, operations_lists, operations_functions):
    operation_item = self._operation_items[operation_id]
    operations_lists[operation_group].remove(operation_item)
    
    operations_functions[operation_group][operation_item.operation_function] -= 1
    if operations_functions[operation_group][operation_item.operation_function] == 0:
      del operations_functions[operation_group][operation_item.operation_function]
    
    self._remove_operation_item(operation_id, operation_group)
  
  def _remove_operation_item(self, operation_id, operation_group):
    self._operation_items[operation_id].operation_groups.remove(operation_group)
    
    if not self._operation_items[operation_id].operation_groups:
      del self._operation_items[operation_id]
  
  def _get_operation_lists_and_functions(self, operation_type):
    if operation_type == self.OPERATION:
      return self._operations, self._operations_functions
    elif operation_type == self.FOREACH_OPERATION:
      return self._foreach_operations, self._foreach_operations_functions
    elif operation_type == self.EXECUTOR:
      return self._operations, self._operations_executors
    else:
      raise ValueError(
        "invalid operation type {0}; must be one of {1}".format(operation_type, self._OPERATION_TYPES))
  
  def _check_operation_id_is_valid(self, operation_id):
    if operation_id not in self._operation_items:
      raise ValueError("operation with ID {0} does not exist".format(operation_id))
  
  def _check_operation_group_exists(self, operation_group, operation_groups=None):
    if operation_groups is None:
      operation_groups = self.get_operation_groups()
    
    if operation_group not in operation_groups:
      raise ValueError("operation group '{0}' does not exist".format(operation_group))
  
  def _check_operation_in_group(self, operation_id, operation_group):
    if operation_group not in self._operation_items[operation_id].operation_groups:
      raise ValueError("operation with ID {0} is not in group '{1}'".format(operation_id, operation_group))
