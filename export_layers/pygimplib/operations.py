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

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

str = unicode

import collections
import inspect

#===============================================================================


class OperationsExecutor(object):
  
  def __init__(self):
    # key: operation group name; value: list of (operation, operation args, operation kwargs) tuples
    self._operations = collections.OrderedDict()
    # key: operation group name; value: list of (operation, operation args, operation kwargs) tuples
    self._foreach_operations = collections.OrderedDict()
    
    # key: operation group name; value: set of operation functions
    self._operations_functions = collections.defaultdict(set)
    # key: operation group name; value: set of operation functions
    self._foreach_operations_functions = collections.defaultdict(set)
    #key: operation group name; value: `OperationsExecutor` instance
    self._operations_executors = collections.defaultdict(set)
  
  def add_operation(self, operation, operation_groups, *operation_args, **operation_kwargs):
    """
    Add an operation specified by its function `operation`, its arguments
    `*operation_args` (as a list or tuple) and keyword arguments
    `**operation_kwargs` (as a dict), to the operation groups given by
    `operation_groups`.
    
    The operation groups are created automatically if no operations were added
    to them before.
    """
    
    for operation_group in operation_groups:
      self._add_operation(operation, operation_group, operation_args, operation_kwargs)
  
  def add_foreach_operation(self, foreach_operation, operation_groups,
                            *foreach_operation_args, **foreach_operation_kwargs):
    """
    Add an operation to be executed for each operation in groups given by
    `operation_groups`. `foreach_operation` is the function to be
    executed, along with its arguments `*foreach_operation_args` and keyword
    arguments `**foreach_operation_kwargs`.
    
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
    
    If multiple "for-each" operations are added, they are executed in the order
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
    
    for operation_group in operation_groups:
      self._add_foreach_operation(
        foreach_operation, operation_group, foreach_operation_args, foreach_operation_kwargs)
  
  def add_executor(self, operations_executor, operation_groups=None):
    """
    Add an existing `OperationsExecutor` instance to be executed in the list of
    operations. The operations will be kept up-to-date if the instance changes.
    
    `operation_groups` is a list of groups from which to add operations. If
    `operation_groups` is None, add operations from all groups.
    """
    
    if operation_groups is None:
      operation_groups = list(self._operations.keys())
    
    for operation_group in operation_groups:
      self._add_executor(operations_executor, operation_group)
  
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
        _execute_operation(*params) for params in self._foreach_operations[operation_group]]
      
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
      item.execute([operation_group], *additional_operation_args, **additional_operation_kwargs)
    
    for operation_group in operation_groups:
      if operation_group not in self._operations:
        self._init_operation_group(operation_group)
      
      for item in self._operations[operation_group]:
        if not isinstance(item, OperationsExecutor):
          operation, operation_args, operation_kwargs = item
          if self._foreach_operations[operation_group]:
            _execute_operation_with_foreach_operations(operation, operation_args, operation_kwargs)
          else:
            _execute_operation(operation, operation_args, operation_kwargs)
        else:
          _execute_executor(item, operation_group)
  
  def has_operation(self, operation, operation_group):
    """
    Return True if `operation` is added to the list of operations in group
    `operation_group`, False otherwise.
    """
    
    return operation in self._operations_functions[operation_group]
  
  def has_foreach_operation(self, foreach_operation, operation_group):
    """
    Return True if `foreach_operation` is added to the list of "for-each"
    operations in group `operation_group`, False otherwise.
    """
    
    return foreach_operation in self._foreach_operations_functions[operation_group]
  
  def _init_operation_group(self, operation_group):
    if operation_group not in self._operations:
      self._operations[operation_group] = []
      self._foreach_operations[operation_group] = []
  
  def _add_operation(self, operation, operation_group, operation_args, operation_kwargs):
    self._init_operation_group(operation_group)
    
    self._operations[operation_group].append((operation, operation_args, operation_kwargs))
    self._operations_functions[operation_group].add(operation)
  
  def _add_foreach_operation(self, foreach_operation, operation_group,
                             foreach_operation_args, foreach_operation_kwargs):
    self._init_operation_group(operation_group)
    
    if not inspect.isgeneratorfunction(foreach_operation):
      def execute_foreach_operation_after_operation(*args, **kwargs):
        yield
        foreach_operation(*args, **kwargs)
      
      foreach_operation_generator_function = execute_foreach_operation_after_operation
    else:
      foreach_operation_generator_function = foreach_operation
    
    self._foreach_operations[operation_group].append(
      (foreach_operation_generator_function, foreach_operation_args, foreach_operation_kwargs))
    self._foreach_operations_functions[operation_group].add(foreach_operation)
  
  def _add_executor(self, operations_executor, operation_group):
    self._init_operation_group(operation_group)
    
    self._operations[operation_group].append(operations_executor)
    self._operations_executors[operation_group].add(operations_executor)
