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
  
  def test_has_operation(self):
    operation_id = self.operations_executor.add_operation(append_to_list, ["main_processing"])
    self.assertTrue(self.operations_executor.has_operation(operation_id))
  
  def test_has_matching_operation(self):
    test_list = []
    
    self.operations_executor.add_operation(append_test, ["main_processing"], test_list)
    self.assertTrue(self.operations_executor.has_matching_operation(append_test, "main_processing"))
    
    additional_executor = operations.OperationsExecutor()
    self.operations_executor.add_executor(additional_executor, ["main_processing"])
    self.assertTrue(
      self.operations_executor.has_matching_operation(
        additional_executor, "main_processing", operation_type=self.operations_executor.EXECUTOR))
    
    self.operations_executor.add_foreach_operation(append_to_list_again, ["main_processing"], test_list)
    self.assertTrue(
      self.operations_executor.has_matching_operation(
        append_to_list_again, "main_processing", operation_type=self.operations_executor.FOREACH_OPERATION))
  
  def test_add_operation_return_unique_ids(self):
    test_list = []
    operation_ids = []
    
    operation_ids.append(
      self.operations_executor.add_operation(append_to_list, ["main_processing"], test_list, 2))
    operation_ids.append(
      self.operations_executor.add_operation(append_to_list, ["main_processing"], test_list, 3))
    operation_ids.append(
      self.operations_executor.add_operation(append_to_list, ["main_processing"], test_list, 2))
    operation_ids.append(
      self.operations_executor.add_foreach_operation(append_to_list_before, ["main_processing"], test_list, 3))
    operation_ids.append(
      self.operations_executor.add_foreach_operation(append_to_list_before, ["main_processing"], test_list, 3))
    
    additional_executor = operations.OperationsExecutor()
    operation_ids.append(
      self.operations_executor.add_executor(additional_executor, ["main_processing"]))
    operation_ids.append(
      self.operations_executor.add_executor(additional_executor, ["main_processing"]))
    
    self.assertEqual(len(operation_ids), len(set(operation_ids)))
  
  def test_add_operation_return_same_id_for_multiple_groups(self):
    test_list = []
    operation_id = self.operations_executor.add_operation(
      append_to_list, ["main_processing", "additional_processing"], test_list, 2)
    
    self.assertTrue(self.operations_executor.has_operation(operation_id))
    self.assertTrue(self.operations_executor.has_operation(operation_id, "main_processing"))
    self.assertTrue(self.operations_executor.has_operation(operation_id, "additional_processing"))
  
  def test_add_operation_to_another_group(self):
    test_list = []
    operation_id = self.operations_executor.add_operation(append_to_list, ["main_processing"], test_list, 2)
    
    self.operations_executor.add_operation_to_groups(operation_id, ["additional_processing"])
    self.assertTrue(self.operations_executor.has_operation(operation_id, "main_processing"))
    self.assertTrue(self.operations_executor.has_operation(operation_id, "additional_processing"))
    
    self.operations_executor.add_operation_to_groups(operation_id, ["main_processing"])
    self.assertEqual(len(self.operations_executor.get_operations("main_processing")), 1)
    self.assertEqual(len(self.operations_executor.get_foreach_operations("main_processing")), 0)
    
    foreach_operation_id = self.operations_executor.add_foreach_operation(
      append_to_list_before, ["main_processing"], test_list, 2)
    
    self.operations_executor.add_operation_to_groups(foreach_operation_id, ["additional_processing"])
    self.assertTrue(self.operations_executor.has_operation(foreach_operation_id, "main_processing"))
    self.assertTrue(self.operations_executor.has_operation(foreach_operation_id, "additional_processing"))
    
    self.operations_executor.add_operation_to_groups(foreach_operation_id, ["main_processing"])
    self.assertEqual(len(self.operations_executor.get_operations("main_processing")), 1)
    self.assertEqual(len(self.operations_executor.get_foreach_operations("main_processing")), 1)
    
    additional_executor = operations.OperationsExecutor()
    executor_id = self.operations_executor.add_executor(additional_executor, ["main_processing"])
    
    self.operations_executor.add_operation_to_groups(executor_id, ["additional_processing"])
    self.assertTrue(self.operations_executor.has_operation(executor_id, "main_processing"))
    self.assertTrue(self.operations_executor.has_operation(executor_id, "additional_processing"))
    
    self.operations_executor.add_operation_to_groups(executor_id, ["main_processing"])
    self.assertEqual(len(self.operations_executor.get_operations("main_processing")), 2)
    self.assertEqual(len(self.operations_executor.get_foreach_operations("main_processing")), 1)
  
  def test_get_operations_non_existing_group(self):
    self.assertIsNone(self.operations_executor.get_operations("main_processing"))
  
  def test_get_operations(self):
    test_list = []
    self.operations_executor.add_operation(append_to_list, ["main_processing"], test_list, 1)
    self.operations_executor.add_operation(append_to_list, ["main_processing"], test_list, 2)
    
    self.assertListEqual(
      self.operations_executor.get_operations("main_processing"),
      [(append_to_list, (test_list, 1), {}), (append_to_list, (test_list, 2), {})])
    
    self.assertEqual(self.operations_executor.get_foreach_operations("main_processing"), [])
  
  def test_get_foreach_operations_non_existing_group(self):
    self.assertIsNone(self.operations_executor.get_foreach_operations("main_processing"))
  
  def test_get_foreach_operations(self):
    test_list = []
    self.operations_executor.add_foreach_operation(append_to_list_before, ["main_processing"], test_list, 1)
    self.operations_executor.add_foreach_operation(append_to_list_before, ["main_processing"], test_list, 2)
    
    self.assertListEqual(
      self.operations_executor.get_foreach_operations("main_processing"),
      [(append_to_list_before, (test_list, 1), {}), (append_to_list_before, (test_list, 2), {})])
    
    self.assertEqual(self.operations_executor.get_operations("main_processing"), [])
  
  def test_get_operation_groups(self):
    test_list = []
    self.operations_executor.add_operation(append_to_list, ["main_processing"], test_list, 2)
    self.operations_executor.add_operation(append_to_list, ["additional_processing"], test_list, 3)
    
    self.assertEqual(len(self.operations_executor.get_operation_groups()), 2)
    self.assertIn("main_processing", self.operations_executor.get_operation_groups())
    self.assertIn("additional_processing", self.operations_executor.get_operation_groups())
  
  def test_get_operation_groups_without_empty_groups(self):
    test_list = []
    operation_ids = []
    
    operation_ids.append(
      self.operations_executor.add_operation(
        append_to_list, ["main_processing", "additional_processing"], test_list, 2))
    
    operation_ids.append(
      self.operations_executor.add_foreach_operation(
        append_to_list_before, ["main_processing", "additional_processing"], test_list, 2))
    
    additional_executor = operations.OperationsExecutor()
    operation_ids.append(self.operations_executor.add_executor(additional_executor, ["main_processing"]))
    
    self.operations_executor.remove_operation(operation_ids[2], ["main_processing"])
    self.assertEqual(len(self.operations_executor.get_operation_groups(include_empty_groups=False)), 2)
    
    self.operations_executor.remove_operation(operation_ids[1], ["main_processing"])
    self.assertEqual(len(self.operations_executor.get_operation_groups(include_empty_groups=False)), 2)
    
    self.operations_executor.remove_operation(operation_ids[0], ["main_processing"])
    non_empty_operation_groups = self.operations_executor.get_operation_groups(include_empty_groups=False)
    self.assertEqual(len(non_empty_operation_groups), 1)
    self.assertNotIn("main_processing", non_empty_operation_groups)
    self.assertIn("additional_processing", non_empty_operation_groups)
    
    self.operations_executor.remove_operation(operation_ids[1], ["additional_processing"])
    non_empty_operation_groups = self.operations_executor.get_operation_groups(include_empty_groups=False)
    self.assertEqual(len(non_empty_operation_groups), 1)
    self.assertNotIn("main_processing", non_empty_operation_groups)
    self.assertIn("additional_processing", non_empty_operation_groups)
    
    self.operations_executor.remove_operation(operation_ids[0], ["additional_processing"])
    self.assertEqual(len(self.operations_executor.get_operation_groups(include_empty_groups=False)), 0)
  
  def test_get_operation(self):
    test_list = []
    operation_ids = []
    operation_ids.append(
      self.operations_executor.add_operation(append_to_list, ["main_processing"], test_list, 2))
    operation_ids.append(
      self.operations_executor.add_operation(append_to_list, ["additional_processing"], test_list, 3))
    operation_ids.append(
      self.operations_executor.add_foreach_operation(
        append_to_list_before, ["additional_processing"], test_list, 4))
    
    additional_executor = operations.OperationsExecutor()
    operation_ids.append(self.operations_executor.add_executor(additional_executor, ["main_processing"]))
    
    self.assertEqual(
      self.operations_executor.get_operation(operation_ids[0]), (append_to_list, (test_list, 2), {}))
    self.assertEqual(
      self.operations_executor.get_operation(operation_ids[1]), (append_to_list, (test_list, 3), {}))
    self.assertEqual(
      self.operations_executor.get_operation(operation_ids[2]), (append_to_list_before, (test_list, 4), {}))
    
    self.assertEqual(self.operations_executor.get_operation(operation_ids[3]), additional_executor)
  
  def test_get_operation_invalid_id(self):
    self.assertIsNone(self.operations_executor.get_operation(-1))
  
  def test_get_operation_positon(self):
    test_list = []
    operation_ids = []
    
    operation_ids.append(
      self.operations_executor.add_operation(append_to_list, ["main_processing"], test_list, 2))
    operation_ids.append(
      self.operations_executor.add_operation(append_to_list, ["main_processing"], test_list, 3))
    operation_ids.append(
      self.operations_executor.add_operation(append_to_list, ["main_processing"], test_list, 4))
    
    self.assertEqual(self.operations_executor.get_operation_positon(operation_ids[0], "main_processing"), 0)
    self.assertEqual(self.operations_executor.get_operation_positon(operation_ids[1], "main_processing"), 1)
    self.assertEqual(self.operations_executor.get_operation_positon(operation_ids[2], "main_processing"), 2)
  
  def test_get_operation_positon_invalid_id(self):
    self.operations_executor.add_operation(append_test, ["main_processing"])
    with self.assertRaises(ValueError):
      self.operations_executor.get_operation_positon(-1, "main_processing")
  
  def test_get_operation_positon_operation_not_in_group(self):
    operation_id = self.operations_executor.add_operation(append_test, ["main_processing"])
    with self.assertRaises(ValueError):
      self.operations_executor.get_operation_positon(operation_id, "additional_processing")
  
  def test_find_matching_operations(self):
    test_list = []
    operation_ids = []
    
    operation_ids.append(
      self.operations_executor.add_operation(append_to_list, ["main_processing"], test_list, 2))
    operation_ids.append(
      self.operations_executor.add_operation(append_to_list, ["main_processing"], test_list, 3))
    operation_ids.append(
      self.operations_executor.add_operation(append_to_list, ["additional_processing"], test_list, 3))
    
    operation_ids.append(
      self.operations_executor.add_foreach_operation(append_to_list_before, ["main_processing"], test_list, 3))
    
    additional_executor = operations.OperationsExecutor()
    operation_ids.append(self.operations_executor.add_executor(additional_executor, ["main_processing"]))
    
    self.assertEqual(
      self.operations_executor.find_matching_operations(
        append_to_list, "main_processing"), [operation_ids[0], operation_ids[1]])
    self.assertEqual(
      self.operations_executor.find_matching_operations(
        append_to_list, "main_processing", self.operations_executor.FOREACH_OPERATION), [])
    self.assertEqual(
      self.operations_executor.find_matching_operations(
        append_to_list, "main_processing", self.operations_executor.EXECUTOR), [])
    
    self.assertEqual(
      self.operations_executor.find_matching_operations(
        append_to_list_before, "main_processing"), [])
    self.assertEqual(
      self.operations_executor.find_matching_operations(
        append_to_list_before, "main_processing", self.operations_executor.FOREACH_OPERATION),
      [operation_ids[3]])
    self.assertEqual(
      self.operations_executor.find_matching_operations(
        append_to_list_before, "main_processing", self.operations_executor.EXECUTOR), [])
    
    self.assertEqual(
      self.operations_executor.find_matching_operations(
        additional_executor, "main_processing"), [])
    self.assertEqual(
      self.operations_executor.find_matching_operations(
        additional_executor, "main_processing", self.operations_executor.FOREACH_OPERATION), [])
    self.assertEqual(
      self.operations_executor.find_matching_operations(
        additional_executor, "main_processing", self.operations_executor.EXECUTOR), [operation_ids[4]])
  
  def test_find_matching_operations_non_existing_group(self):
    self.operations_executor.add_operation(append_test, ["main_processing"])
    with self.assertRaises(ValueError):
      self.operations_executor.find_matching_operations(append_test, "additional_processing")
  
  def test_reorder_operation(self):
    operation_ids = []
    operation_ids.append(self.operations_executor.add_operation(append_test, ["main_processing"]))
    operation_ids.append(self.operations_executor.add_operation(append_test, ["main_processing"]))
    operation_ids.append(self.operations_executor.add_operation(append_test, ["main_processing"]))
    operation_ids.append(self.operations_executor.add_operation(append_test, ["main_processing"]))
    
    self.operations_executor.reorder_operation(operation_ids[3], "main_processing", 0)
    self.operations_executor.reorder_operation(operation_ids[2], "main_processing", 1)
    self.operations_executor.reorder_operation(operation_ids[1], "main_processing", 2)
    
    self.assertEqual(len(self.operations_executor.get_operations("main_processing")), 4)
    self.assertEqual(self.operations_executor.get_operation_positon(operation_ids[0], "main_processing"), 3)
    self.assertEqual(self.operations_executor.get_operation_positon(operation_ids[1], "main_processing"), 2)
    self.assertEqual(self.operations_executor.get_operation_positon(operation_ids[2], "main_processing"), 1)
    self.assertEqual(self.operations_executor.get_operation_positon(operation_ids[3], "main_processing"), 0)
    
    self.operations_executor.reorder_operation(operation_ids[2], "main_processing", 5)
    self.assertEqual(self.operations_executor.get_operation_positon(operation_ids[2], "main_processing"), 3)
    
    self.operations_executor.reorder_operation(operation_ids[3], "main_processing", -1)
    self.operations_executor.reorder_operation(operation_ids[1], "main_processing", -3)
    self.operations_executor.reorder_operation(operation_ids[0], "main_processing", -4)
    
    self.assertEqual(len(self.operations_executor.get_operations("main_processing")), 4)
    self.assertEqual(self.operations_executor.get_operation_positon(operation_ids[0], "main_processing"), 0)
    self.assertEqual(self.operations_executor.get_operation_positon(operation_ids[1], "main_processing"), 1)
    self.assertEqual(self.operations_executor.get_operation_positon(operation_ids[2], "main_processing"), 2)
    self.assertEqual(self.operations_executor.get_operation_positon(operation_ids[3], "main_processing"), 3)
  
  def test_reorder_operation_invalid_id(self):
    with self.assertRaises(ValueError):
      self.operations_executor.reorder_operation(-1, "main_processing", 0)
  
  def test_reorder_operation_non_existing_group(self):
    operation_id = self.operations_executor.add_operation(append_test, ["main_processing"])
    with self.assertRaises(ValueError):
      self.operations_executor.reorder_operation(operation_id, "additional_processing", 0)
  
  def test_reorder_operation_operation_not_in_group(self):
    operation_id = self.operations_executor.add_operation(append_test, ["main_processing"])
    self.operations_executor.add_operation(append_test, ["additional_processing"])
    with self.assertRaises(ValueError):
      self.operations_executor.reorder_operation(operation_id, "additional_processing", 0)
  
  def test_remove_operation(self):
    test_list = []
    operation_ids = []
    
    operation_ids.append(
      self.operations_executor.add_operation(append_to_list, ["main_processing"], test_list, 2))
    operation_ids.append(
      self.operations_executor.add_foreach_operation(append_to_list_before, ["main_processing"], test_list, 3))
    
    additional_executor = operations.OperationsExecutor()
    operation_ids.append(self.operations_executor.add_executor(additional_executor, ["main_processing"]))
    
    self.operations_executor.remove_operation(operation_ids[0], ["main_processing"])
    self.assertFalse(self.operations_executor.has_operation(operation_ids[0]))
    self.assertFalse(self.operations_executor.has_matching_operation(append_to_list, "main_processing"))
    
    self.operations_executor.remove_operation(operation_ids[1], ["main_processing"])
    self.assertFalse(self.operations_executor.has_operation(operation_ids[1]))
    self.assertFalse(self.operations_executor.has_matching_operation(append_to_list_before, "main_processing"))
    
    self.operations_executor.remove_operation(operation_ids[2], ["main_processing"])
    self.assertFalse(self.operations_executor.has_operation(operation_ids[2]))
    self.assertFalse(
      self.operations_executor.has_matching_operation(
        additional_executor, "main_processing", operation_type=self.operations_executor.EXECUTOR))
  
  def test_remove_multiple_operations(self):
    test_list = []
    operation_ids = []
    
    operation_ids.append(
      self.operations_executor.add_operation(append_to_list, ["main_processing"], test_list, 2))
    operation_ids.append(
      self.operations_executor.add_operation(append_to_list, ["main_processing"], test_list, 3))
    
    self.operations_executor.remove_operation(operation_ids[0], ["main_processing"])
    self.assertFalse(self.operations_executor.has_operation(operation_ids[0]))
    self.assertTrue(self.operations_executor.has_matching_operation(append_to_list, "main_processing"))
    
    self.operations_executor.remove_operation(operation_ids[1], ["main_processing"])
    self.assertFalse(self.operations_executor.has_operation(operation_ids[1]))
    self.assertFalse(self.operations_executor.has_matching_operation(append_to_list, "main_processing"))
    
    operation_ids.append(
      self.operations_executor.add_foreach_operation(
        append_to_list_before, ["main_processing"], test_list, 4))
    operation_ids.append(
      self.operations_executor.add_foreach_operation(
        append_to_list_before, ["main_processing"], test_list, 5))
    
    self.operations_executor.remove_operation(operation_ids[2], ["main_processing"])
    self.assertFalse(self.operations_executor.has_operation(operation_ids[2]))
    self.assertTrue(
      self.operations_executor.has_matching_operation(
        append_to_list_before, "main_processing", operation_type=self.operations_executor.FOREACH_OPERATION))
    
    self.operations_executor.remove_operation(operation_ids[3], ["main_processing"])
    self.assertFalse(self.operations_executor.has_operation(operation_ids[3]))
    self.assertFalse(
      self.operations_executor.has_matching_operation(
        append_to_list_before, "main_processing", operation_type=self.operations_executor.FOREACH_OPERATION))
    
    additional_executor = operations.OperationsExecutor()
    operation_ids.append(self.operations_executor.add_executor(additional_executor, ["main_processing"]))
    operation_ids.append(self.operations_executor.add_executor(additional_executor, ["main_processing"]))
    
    self.operations_executor.remove_operation(operation_ids[4], ["main_processing"])
    self.assertFalse(self.operations_executor.has_operation(operation_ids[4]))
    self.assertTrue(
      self.operations_executor.has_matching_operation(
        additional_executor, "main_processing", operation_type=self.operations_executor.EXECUTOR))
    
    self.operations_executor.remove_operation(operation_ids[5], ["main_processing"])
    self.assertFalse(self.operations_executor.has_operation(operation_ids[5]))
    self.assertFalse(
      self.operations_executor.has_matching_operation(
        additional_executor, "main_processing", operation_type=self.operations_executor.EXECUTOR))
  
  def test_remove_operation_from_all_groups_operation_only_in_one_group(self):
    test_list = []
    
    operation_id = self.operations_executor.add_operation(append_to_list, ["main_processing"], test_list, 2)
    self.operations_executor.add_operation(append_to_list, ["additional_processing"], test_list, 3)
    
    self.operations_executor.remove_operation(operation_id)
    self.assertFalse(self.operations_executor.has_operation(operation_id, "main_processing"))
    self.assertFalse(self.operations_executor.has_operation(operation_id, "additional_processing"))
  
  def test_remove_operation_in_one_group_keep_in_others(self):
    operation_id = self.operations_executor.add_operation(
      append_test, ["main_processing", "additional_processing"])
    
    self.operations_executor.remove_operation(operation_id, ["main_processing"])
    self.assertFalse(self.operations_executor.has_operation(operation_id, "main_processing"))
    self.assertTrue(self.operations_executor.has_operation(operation_id, "additional_processing"))
  
  def test_remove_operation_invalid_id(self):
    with self.assertRaises(ValueError):
      self.operations_executor.remove_operation(-1)
  
  def test_remove_operation_non_existing_group(self):
    operation_id = self.operations_executor.add_operation(append_test, ["main_processing"])
    with self.assertRaises(ValueError):
      self.operations_executor.remove_operation(operation_id, ["additional_processing"])
  
  def test_remove_operation_multiple_groups_at_once(self):
    test_list = []
    operation_id = self.operations_executor.add_operation(
      append_to_list, ["main_processing", "additional_processing"], test_list, 2)
    
    self.operations_executor.remove_operation(operation_id)
    self.assertFalse(self.operations_executor.has_operation(operation_id))
    self.assertFalse(self.operations_executor.has_matching_operation(append_to_list, "main_processing"))
    self.assertFalse(self.operations_executor.has_matching_operation(append_to_list, "additional_processing"))
  
  def test_remove_groups(self):
    test_list = []
    self.operations_executor.add_operation(append_test, ["main_processing", "additional_processing"])
    self.operations_executor.add_foreach_operation(
      append_to_list_before, ["main_processing", "additional_processing"], test_list, 3)
    self.operations_executor.add_executor(append_test, ["main_processing", "additional_processing"])
    
    self.operations_executor.remove_groups(["main_processing"])
    self.assertEqual(len(self.operations_executor.get_operation_groups()), 1)
    self.assertIn("additional_processing", self.operations_executor.get_operation_groups())
    self.assertIsNone(self.operations_executor.get_operations("main_processing"))
    
    self.operations_executor.remove_groups(["additional_processing"])
    self.assertEqual(len(self.operations_executor.get_operation_groups()), 0)
    self.assertIsNone(self.operations_executor.get_operations("main_processing"))
    self.assertIsNone(self.operations_executor.get_operations("additional_processing"))
  
  def test_remove_all_groups(self):
    test_list = []
    self.operations_executor.add_operation(append_test, ["main_processing", "additional_processing"])
    self.operations_executor.add_foreach_operation(
      append_to_list_before, ["main_processing", "additional_processing"], test_list, 3)
    self.operations_executor.add_executor(append_test, ["main_processing", "additional_processing"])
    
    self.operations_executor.remove_groups()
    self.assertEqual(len(self.operations_executor.get_operation_groups()), 0)
    self.assertIsNone(self.operations_executor.get_operations("main_processing"))
    self.assertIsNone(self.operations_executor.get_operations("additional_processing"))
  
  def test_remove_groups_non_existing_group(self):
    with self.assertRaises(ValueError):
      self.operations_executor.remove_groups(["main_processing"])


class TestOperationsExecutorExecute(unittest.TestCase):
  
  def setUp(self):
    self.operations_executor = operations.OperationsExecutor()
  
  def test_execute_single_group_single_operation(self):
    test_list = []
    self.operations_executor.add_operation(append_test, ["main_processing"], test_list)
    self.operations_executor.execute(["main_processing"])
    
    self.assertEqual(test_list, ["test"])
  
  def test_execute_single_group_single_operation_additional_args(self):
    test_list = []
    self.operations_executor.add_operation(append_to_list, ["main_processing"], test_list)
    self.operations_executor.execute(["main_processing"], 1)
    
    self.assertEqual(test_list, [1])
  
  def test_execute_single_group_single_operation_additional_multiple_args(self):
    test_list = []
    self.operations_executor.add_operation(extend_list, ["main_processing"], test_list, 1)
    self.operations_executor.execute(["main_processing"], 2, 3)
    
    self.assertListEqual(test_list, [1, 2, 3])
  
  def test_execute_single_group_single_operation_invalid_number_of_args(self):
    test_list = []
    self.operations_executor.add_operation(append_to_list, ["main_processing"], test_list, 1, 2)
    
    with self.assertRaises(TypeError):
      self.operations_executor.execute(["main_processing"])
  
  def test_execute_single_group_single_operation_additional_args_invalid_number_of_args(self):
    test_list = []
    self.operations_executor.add_operation(append_to_list, ["main_processing"], test_list)
    
    with self.assertRaises(TypeError):
      self.operations_executor.execute(["main_processing"])
    
    with self.assertRaises(TypeError):
      self.operations_executor.execute(["main_processing"], 1, 2)
  
  def test_execute_single_group_single_operation_additional_kwargs_override_former_kwargs(self):
    test_dict = {}
    self.operations_executor.add_operation(update_dict, ["main_processing"], test_dict, one=1, two=2)
    self.operations_executor.execute(["main_processing"], two="two", three=3)
    
    self.assertDictEqual(test_dict, {"one": 1, "two": "two", "three": 3})
  
  def test_execute_single_group_multiple_operations(self):
    test_list = []
    self.operations_executor.add_operation(append_test, ["main_processing"], test_list)
    self.operations_executor.add_operation(extend_list, ["main_processing"], test_list, 1)
    
    self.operations_executor.execute(["main_processing"])
    
    self.assertListEqual(test_list, ["test", 1])
  
  def test_execute_multiple_groups_multiple_operations(self):
    test_dict = {}
    self.operations_executor.add_operation(
      update_dict, ["main_processing", "advanced_processing"], test_dict, one=1, two=2)
    self.operations_executor.add_operation(update_dict, ["main_processing"], test_dict, two="two", three=3)
    
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
  
  def test_execute_empty_group(self):
    try:
      self.operations_executor.execute(["main_processing"])
    except Exception:
      self.fail("executing no operations for given group should not raise exception")
  
  def test_execute_single_foreach_operation_default_execution(self):
    test_list = []
    self.operations_executor.add_operation(append_to_list, ["main_processing"], test_list, 1)
    self.operations_executor.add_operation(append_to_list, ["main_processing"], test_list, 2)
    self.operations_executor.add_foreach_operation(append_to_list, ["main_processing"], test_list, 3)
    
    self.operations_executor.execute(["main_processing"])
    
    self.assertListEqual(test_list, [1, 3, 2, 3])
  
  def test_execute_single_foreach_operation_before_operation(self):
    test_list = []
    self.operations_executor.add_operation(append_to_list, ["main_processing"], test_list, 1)
    self.operations_executor.add_operation(append_to_list, ["main_processing"], test_list, 2)
    self.operations_executor.add_foreach_operation(append_to_list_before, ["main_processing"], test_list, 3)
    
    self.operations_executor.execute(["main_processing"])
    
    self.assertListEqual(test_list, [3, 1, 3, 2])
  
  def test_execute_single_foreach_operation_before_and_after_operation(self):
    test_list = []
    self.operations_executor.add_operation(append_to_list, ["main_processing"], test_list, 1)
    self.operations_executor.add_operation(append_to_list, ["main_processing"], test_list, 2)
    self.operations_executor.add_foreach_operation(
      append_to_list_before_and_after, ["main_processing"], test_list, 3)
    
    self.operations_executor.execute(["main_processing"])
    
    self.assertListEqual(test_list, [3, 1, 3, 3, 2, 3])
  
  def test_execute_single_foreach_operation_before_and_after_operation_multiple_times(self):
    test_list = []
    self.operations_executor.add_operation(append_to_list, ["main_processing"], test_list, 1)
    self.operations_executor.add_operation(append_to_list, ["main_processing"], test_list, 2)
    self.operations_executor.add_foreach_operation(
      append_to_list_before_and_after_execute_twice, ["main_processing"], test_list, 3)
    
    self.operations_executor.execute(["main_processing"])
    
    self.assertListEqual(test_list, [3, 1, 1, 3, 3, 2, 2, 3])
  
  def test_execute_multiple_foreach_operations(self):
    test_list = []
    self.operations_executor.add_operation(append_to_list, ["main_processing"], test_list, 1)
    self.operations_executor.add_operation(append_to_list, ["main_processing"], test_list, 2)
    self.operations_executor.add_foreach_operation(append_to_list_before, ["main_processing"], test_list, 3)
    self.operations_executor.add_foreach_operation(append_to_list, ["main_processing"], test_list, 4)
    
    self.operations_executor.execute(["main_processing"])
    
    self.assertListEqual(test_list, [3, 1, 4, 3, 2, 4])
  
  def test_execute_multiple_foreach_operations_complex(self):
    test_list = []
    self.operations_executor.add_operation(append_to_list, ["main_processing"], test_list, 1)
    self.operations_executor.add_operation(append_to_list, ["main_processing"], test_list, 2)
    self.operations_executor.add_foreach_operation(
      append_to_list_before_and_after, ["main_processing"], test_list, 3)
    self.operations_executor.add_foreach_operation(
      append_to_list_before_and_after_execute_twice, ["main_processing"], test_list, 4)
    
    self.operations_executor.execute(["main_processing"])
    
    self.assertListEqual(
      test_list,
      [3, 4, 1, 3, 1, 4,
       3, 4, 2, 3, 2, 4])
  
  def test_execute_multiple_foreach_operations_even_more_complex(self):
    test_list = []
    self.operations_executor.add_operation(append_to_list, ["main_processing"], test_list, 1)
    self.operations_executor.add_operation(append_to_list, ["main_processing"], test_list, 2)
    self.operations_executor.add_foreach_operation(
      append_to_list_before_and_after, ["main_processing"], test_list, 3)
    self.operations_executor.add_foreach_operation(
      append_to_list_before_middle_after_execute_twice, ["main_processing"], test_list, 4)
    
    self.operations_executor.execute(["main_processing"])
    
    self.assertListEqual(
      test_list,
      [3, 4, 1, 3, 4, 1, 4,
       3, 4, 2, 3, 4, 2, 4])
  
  def test_execute_foreach_operation_use_return_value_from_operation(self):
    test_list = []
    self.operations_executor.add_operation(append_to_list, ["main_processing"], test_list, 1)
    self.operations_executor.add_operation(append_to_list, ["main_processing"], test_list, 2)
    self.operations_executor.add_foreach_operation(append_to_list_again, ["main_processing"], test_list)
    
    self.operations_executor.execute(["main_processing"])
    
    self.assertListEqual(test_list, [1, 1, 2, 2])
  
  def test_execute_foreach_operation_does_nothing_in_another_executor(self):
    test_list = []
    another_operations_executor = operations.OperationsExecutor()
    another_operations_executor.add_operation(append_to_list, ["main_processing"], test_list, 1)
    another_operations_executor.add_operation(append_to_list, ["main_processing"], test_list, 2)
    
    self.operations_executor.add_executor(another_operations_executor, ["main_processing"])
    self.operations_executor.add_operation(append_to_list, ["main_processing"], test_list, 3)
    self.operations_executor.add_foreach_operation(append_to_list_again, ["main_processing"], test_list)
    
    self.operations_executor.execute(["main_processing"])
    
    self.assertListEqual(test_list, [1, 2, 3, 3])
  
  def test_execute_with_executor(self):
    test_list = []
    another_operations_executor = operations.OperationsExecutor()
    another_operations_executor.add_operation(append_to_list, ["main_processing"], test_list, 1)
    another_operations_executor.add_operation(append_test, ["main_processing"], test_list)
    
    self.operations_executor.add_operation(append_to_list, ["main_processing"], test_list, 2)
    self.operations_executor.add_executor(another_operations_executor, ["main_processing"])
    
    self.operations_executor.execute(["main_processing"])
    
    self.assertListEqual(test_list, [2, 1, "test"])
  
  def test_execute_with_executor_after_adding_operations_to_it(self):
    test_list = []
    another_operations_executor = operations.OperationsExecutor()
    
    self.operations_executor.add_operation(append_to_list, ["main_processing"], test_list, 2)
    self.operations_executor.add_executor(another_operations_executor, ["main_processing"])
    
    another_operations_executor.add_operation(append_to_list, ["main_processing"], test_list, 1)
    another_operations_executor.add_operation(append_test, ["main_processing"], test_list)
    
    self.operations_executor.execute(["main_processing"])
    
    self.assertListEqual(test_list, [2, 1, "test"])
  
  def test_execute_with_multiple_executors_after_adding_operations_to_them(self):
    test_list = []
    more_operations_executors = [operations.OperationsExecutor(), operations.OperationsExecutor()]
    
    self.operations_executor.add_operation(append_to_list, ["main_processing"], test_list, 2)
    self.operations_executor.add_executor(more_operations_executors[0], ["main_processing"])
    self.operations_executor.add_executor(more_operations_executors[1], ["main_processing"])
    
    more_operations_executors[0].add_operation(append_to_list, ["main_processing"], test_list, 1)
    more_operations_executors[0].add_operation(append_test, ["main_processing"], test_list)
    
    more_operations_executors[1].add_operation(append_to_list, ["main_processing"], test_list, 3)
    more_operations_executors[1].add_operation(append_to_list, ["main_processing"], test_list, 4)
    
    self.operations_executor.execute(["main_processing"])
    
    self.assertListEqual(test_list, [2, 1, "test", 3, 4])
  
  def test_execute_with_executor_empty_group(self):
    another_operations_executor = operations.OperationsExecutor()
    try:
      self.operations_executor.add_executor(another_operations_executor, ["invalid_group"])
    except Exception:
      self.fail("adding operations from an empty group from another OperationsExecutor should not raise exception")
