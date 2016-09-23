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

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

str = unicode

import unittest

from .. import operations

#===============================================================================


def append_test(list_):
  list_.append("test")


def append_to_list(list_, arg):
  list_.append(arg)
  return arg


def extend_list(list_, *args):
  list_.extend(args)


def update_dict(dict_, **kwargs):
  dict_.update(kwargs)


def append_to_list_before(list_, arg):
  list_.append(arg)
  yield


def append_to_list_before_and_after(list_, arg):
  list_.append(arg)
  yield
  list_.append(arg)


def append_to_list_before_and_after_execute_twice(list_, arg):
  list_.append(arg)
  yield
  yield
  list_.append(arg)

def append_to_list_before_middle_after_execute_twice(list_, arg):
  list_.append(arg)
  yield
  list_.append(arg)
  yield
  list_.append(arg)


def append_to_list_again(list_):
  arg = yield
  list_.append(arg)


#===============================================================================


class TestOperationsExecutor(unittest.TestCase):
  
  def setUp(self):
    self.operations_executor = operations.OperationsExecutor()
  
  def test_execute_no_operation_for_group(self):
    with self.assertRaises(ValueError):
      self.operations_executor.execute(["main_processing"])
  
  def test_execute_single_group_single_operation(self):
    test_list = []
    self.operations_executor.add_operation(["main_processing"], append_test, test_list)
    self.operations_executor.execute(["main_processing"])
    
    self.assertEqual(test_list, ["test"])
  
  def test_execute_single_group_single_operation_additional_args(self):
    test_list = []
    self.operations_executor.add_operation(["main_processing"], append_to_list, test_list)
    self.operations_executor.execute(["main_processing"], 1)
    
    self.assertEqual(test_list, [1])
  
  def test_execute_single_group_single_operation_additional_multiple_args(self):
    test_list = []
    self.operations_executor.add_operation(["main_processing"], extend_list, test_list, 1)
    self.operations_executor.execute(["main_processing"], 2, 3)
    
    self.assertListEqual(test_list, [1, 2, 3])
  
  def test_execute_single_group_single_operation_invalid_number_of_args(self):
    test_list = []
    self.operations_executor.add_operation(["main_processing"], append_to_list, test_list, 1, 2)
    
    with self.assertRaises(TypeError):
      self.operations_executor.execute(["main_processing"])
  
  def test_execute_single_group_single_operation_additional_args_invalid_number_of_args(self):
    test_list = []
    self.operations_executor.add_operation(["main_processing"], append_to_list, test_list)
    
    with self.assertRaises(TypeError):
      self.operations_executor.execute(["main_processing"])
    
    with self.assertRaises(TypeError):
      self.operations_executor.execute(["main_processing"], 1, 2)
  
  def test_execute_single_group_single_operation_additional_kwargs_override_former_kwargs(self):
    test_dict = {}
    self.operations_executor.add_operation(["main_processing"], update_dict, test_dict, one=1, two=2)
    self.operations_executor.execute(["main_processing"], two="two", three=3)
    
    self.assertDictEqual(test_dict, {"one": 1, "two": "two", "three": 3})
  
  def test_execute_single_group_multiple_operations(self):
    test_list = []
    self.operations_executor.add_operation(["main_processing"], append_test, test_list)
    self.operations_executor.add_operation(["main_processing"], extend_list, test_list, 1)
    
    self.operations_executor.execute(["main_processing"])
    
    self.assertListEqual(test_list, ["test", 1])
  
  def test_execute_multiple_groups_multiple_operations(self):
    test_dict = {}
    self.operations_executor.add_operation(
      ["main_processing", "advanced_processing"], update_dict, test_dict, one=1, two=2)
    self.operations_executor.add_operation(["main_processing"], update_dict, test_dict, two="two", three=3)
    
    self.operations_executor.execute(["main_processing"])
    self.assertDictEqual(test_dict, {"one": 1, "two": "two", "three": 3})
    
    self.operations_executor.execute(["advanced_processing"])
    self.assertDictEqual(test_dict, {"one": 1, "two": 2, "three": 3})
    
    test_dict.clear()
    self.operations_executor.execute(["main_processing", "advanced_processing"])
    self.assertDictEqual(test_dict, {"one": 1, "two": 2, "three": 3})
    
    test_dict.clear()
    self.operations_executor.execute(["advanced_processing", "main_processing"])
    self.assertDictEqual(test_dict, {"one": 1, "two": "two", "three": 3})
  
  def test_has_operation(self):
    test_list = []
    self.operations_executor.add_operation(["main_processing"], append_test, test_list)
    
    self.assertTrue(self.operations_executor.has_operation("main_processing", append_test))


class TestOperationsExecutorForeachOperations(unittest.TestCase):
  
  def setUp(self):
    self.operations_executor = operations.OperationsExecutor()
  
  def test_execute_single_foreach_operation_default_execution(self):
    test_list = []
    self.operations_executor.add_operation(["main_processing"], append_to_list, test_list, 1)
    self.operations_executor.add_operation(["main_processing"], append_to_list, test_list, 2)
    self.operations_executor.add_foreach_operation(["main_processing"], append_to_list, test_list, 3)
    
    self.operations_executor.execute(["main_processing"])
    
    self.assertListEqual(test_list, [1, 3, 2, 3])
  
  def test_execute_single_foreach_operation_before_operation(self):
    test_list = []
    self.operations_executor.add_operation(["main_processing"], append_to_list, test_list, 1)
    self.operations_executor.add_operation(["main_processing"], append_to_list, test_list, 2)
    self.operations_executor.add_foreach_operation(["main_processing"], append_to_list_before, test_list, 3)
    
    self.operations_executor.execute(["main_processing"])
    
    self.assertListEqual(test_list, [3, 1, 3, 2])
  
  def test_execute_single_foreach_operation_before_and_after_operation(self):
    test_list = []
    self.operations_executor.add_operation(["main_processing"], append_to_list, test_list, 1)
    self.operations_executor.add_operation(["main_processing"], append_to_list, test_list, 2)
    self.operations_executor.add_foreach_operation(
      ["main_processing"], append_to_list_before_and_after, test_list, 3)
    
    self.operations_executor.execute(["main_processing"])
    
    self.assertListEqual(test_list, [3, 1, 3, 3, 2, 3])
  
  def test_execute_single_foreach_operation_before_and_after_operation_multiple_times(self):
    test_list = []
    self.operations_executor.add_operation(["main_processing"], append_to_list, test_list, 1)
    self.operations_executor.add_operation(["main_processing"], append_to_list, test_list, 2)
    self.operations_executor.add_foreach_operation(
      ["main_processing"], append_to_list_before_and_after_execute_twice, test_list, 3)
    
    self.operations_executor.execute(["main_processing"])
    
    self.assertListEqual(test_list, [3, 1, 1, 3, 3, 2, 2, 3])
  
  def test_execute_multiple_foreach_operations(self):
    test_list = []
    self.operations_executor.add_operation(["main_processing"], append_to_list, test_list, 1)
    self.operations_executor.add_operation(["main_processing"], append_to_list, test_list, 2)
    self.operations_executor.add_foreach_operation(["main_processing"], append_to_list_before, test_list, 3)
    self.operations_executor.add_foreach_operation(["main_processing"], append_to_list, test_list, 4)
    
    self.operations_executor.execute(["main_processing"])
    
    self.assertListEqual(test_list, [3, 1, 4, 3, 2, 4])
  
  def test_execute_multiple_foreach_operations_complex(self):
    test_list = []
    self.operations_executor.add_operation(["main_processing"], append_to_list, test_list, 1)
    self.operations_executor.add_operation(["main_processing"], append_to_list, test_list, 2)
    self.operations_executor.add_foreach_operation(
      ["main_processing"], append_to_list_before_and_after, test_list, 3)
    self.operations_executor.add_foreach_operation(
      ["main_processing"], append_to_list_before_and_after_execute_twice, test_list, 4)
    
    self.operations_executor.execute(["main_processing"])
    
    self.assertListEqual(
      test_list,
      [3, 4, 1, 3, 1, 4,
       3, 4, 2, 3, 2, 4])
  
  def test_execute_multiple_foreach_operations_even_more_complex(self):
    test_list = []
    self.operations_executor.add_operation(["main_processing"], append_to_list, test_list, 1)
    self.operations_executor.add_operation(["main_processing"], append_to_list, test_list, 2)
    self.operations_executor.add_foreach_operation(
      ["main_processing"], append_to_list_before_and_after, test_list, 3)
    self.operations_executor.add_foreach_operation(
      ["main_processing"], append_to_list_before_middle_after_execute_twice, test_list, 4)
    
    self.operations_executor.execute(["main_processing"])
    
    self.assertListEqual(
      test_list,
      [3, 4, 1, 3, 4, 1, 4,
       3, 4, 2, 3, 4, 2, 4])
  
  def test_execute_foreach_operation_use_return_value_from_operation(self):
    test_list = []
    self.operations_executor.add_operation(["main_processing"], append_to_list, test_list, 1)
    self.operations_executor.add_operation(["main_processing"], append_to_list, test_list, 2)
    self.operations_executor.add_foreach_operation(["main_processing"], append_to_list_again, test_list)
    
    self.operations_executor.execute(["main_processing"])
    
    self.assertListEqual(test_list, [1, 1, 2, 2])
  
  def test_has_foreach_operation(self):
    test_list = []
    self.operations_executor.add_foreach_operation(["main_processing"], append_to_list_again, test_list)
    
    self.assertTrue(self.operations_executor.has_foreach_operation("main_processing", append_to_list_again))
    self.assertFalse(self.operations_executor.has_operation("main_processing", append_to_list_again))
