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

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import unittest

import parameterized

from .. import pgoperations

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


class OperationExecutorTestCase(unittest.TestCase):
  
  def setUp(self):
    self.executor = pgoperations.OperationExecutor()


#===============================================================================


class TestOperationExecutor(OperationExecutorTestCase):
  
  def test_has_operation(self):
    operation_id = self.executor.add_operation(
      append_to_list, ["main_processing"])
    self.assertTrue(self.executor.has_operation(operation_id))
  
  def test_has_matching_operation(self):
    test_list = []
    
    self.executor.add_operation(append_test, ["main_processing"], test_list)
    self.assertTrue(
      self.executor.has_matching_operation(append_test, "main_processing"))
    
    additional_executor = pgoperations.OperationExecutor()
    self.executor.add_executor(additional_executor, ["main_processing"])
    self.assertTrue(
      self.executor.has_matching_operation(
        additional_executor, "main_processing",
        operation_type=self.executor.TYPE_EXECUTOR))
    
    self.executor.add_foreach_operation(
      append_to_list_again, ["main_processing"], test_list)
    self.assertTrue(
      self.executor.has_matching_operation(
        append_to_list_again, "main_processing",
        operation_type=self.executor.TYPE_FOREACH_OPERATION))
  
  def test_add_operation_return_unique_ids(self):
    test_list = []
    operation_ids = []
    
    operation_ids.append(
      self.executor.add_operation(append_to_list, ["main_processing"], test_list, 2))
    operation_ids.append(
      self.executor.add_operation(append_to_list, ["main_processing"], test_list, 3))
    operation_ids.append(
      self.executor.add_operation(append_to_list, ["main_processing"], test_list, 2))
    operation_ids.append(
      self.executor.add_foreach_operation(
        append_to_list_before, ["main_processing"], test_list, 3))
    operation_ids.append(
      self.executor.add_foreach_operation(
        append_to_list_before, ["main_processing"], test_list, 3))
    
    additional_executor = pgoperations.OperationExecutor()
    operation_ids.append(
      self.executor.add_executor(additional_executor, ["main_processing"]))
    operation_ids.append(
      self.executor.add_executor(additional_executor, ["main_processing"]))
    
    self.assertEqual(len(operation_ids), len(set(operation_ids)))
  
  def test_add_operation_return_same_id_for_multiple_groups(self):
    test_list = []
    operation_id = self.executor.add_operation(
      append_to_list, ["main_processing", "additional_processing"], test_list, 2)
    
    self.assertTrue(self.executor.has_operation(operation_id))
    self.assertTrue(self.executor.has_operation(operation_id, "main_processing"))
    self.assertTrue(self.executor.has_operation(operation_id, "additional_processing"))
  
  def test_add_operation_to_another_group(self):
    test_list = []
    operation_id = self.executor.add_operation(
      append_to_list, ["main_processing"], test_list, 2)
    
    self.executor.add_operation_to_groups(operation_id, ["additional_processing"])
    self.assertTrue(self.executor.has_operation(operation_id, "main_processing"))
    self.assertTrue(self.executor.has_operation(operation_id, "additional_processing"))
    
    self.executor.add_operation_to_groups(operation_id, ["main_processing"])
    self.assertEqual(len(self.executor.get_operations("main_processing")), 1)
    self.assertEqual(len(self.executor.get_foreach_operations("main_processing")), 0)
    
    foreach_operation_id = self.executor.add_foreach_operation(
      append_to_list_before, ["main_processing"], test_list, 2)
    
    self.executor.add_operation_to_groups(
      foreach_operation_id, ["additional_processing"])
    self.assertTrue(self.executor.has_operation(
      foreach_operation_id, "main_processing"))
    self.assertTrue(self.executor.has_operation(
      foreach_operation_id, "additional_processing"))
    
    self.executor.add_operation_to_groups(foreach_operation_id, ["main_processing"])
    self.assertEqual(len(self.executor.get_operations("main_processing")), 1)
    self.assertEqual(len(self.executor.get_foreach_operations("main_processing")), 1)
    
    additional_executor = pgoperations.OperationExecutor()
    executor_id = self.executor.add_executor(additional_executor, ["main_processing"])
    
    self.executor.add_operation_to_groups(executor_id, ["additional_processing"])
    self.assertTrue(self.executor.has_operation(executor_id, "main_processing"))
    self.assertTrue(self.executor.has_operation(executor_id, "additional_processing"))
    
    self.executor.add_operation_to_groups(executor_id, ["main_processing"])
    self.assertEqual(len(self.executor.get_operations("main_processing")), 2)
    self.assertEqual(len(self.executor.get_foreach_operations("main_processing")), 1)
  
  def test_get_operations_non_existing_group(self):
    self.assertIsNone(self.executor.get_operations("main_processing"))
  
  def test_get_operations(self):
    test_list = []
    self.executor.add_operation(append_to_list, ["main_processing"], test_list, 1)
    self.executor.add_operation(append_to_list, ["main_processing"], test_list, 2)
    
    self.assertListEqual(
      self.executor.get_operations("main_processing"),
      [(append_to_list, (test_list, 1), {}), (append_to_list, (test_list, 2), {})])
    
    self.assertEqual(self.executor.get_foreach_operations("main_processing"), [])
  
  def test_get_foreach_operations_non_existing_group(self):
    self.assertIsNone(self.executor.get_foreach_operations("main_processing"))
  
  def test_get_foreach_operations(self):
    test_list = []
    self.executor.add_foreach_operation(
      append_to_list_before, ["main_processing"], test_list, 1)
    self.executor.add_foreach_operation(
      append_to_list_before, ["main_processing"], test_list, 2)
    
    self.assertListEqual(
      self.executor.get_foreach_operations("main_processing"),
      [(append_to_list_before, (test_list, 1), {}),
       (append_to_list_before, (test_list, 2), {})])
    
    self.assertEqual(self.executor.get_operations("main_processing"), [])
  
  def test_get_operation_groups(self):
    test_list = []
    self.executor.add_operation(append_to_list, ["main_processing"], test_list, 2)
    self.executor.add_operation(append_to_list, ["additional_processing"], test_list, 3)
    
    self.assertEqual(len(self.executor.get_operation_groups()), 2)
    self.assertIn("main_processing", self.executor.get_operation_groups())
    self.assertIn("additional_processing", self.executor.get_operation_groups())
  
  def test_get_operation_groups_without_empty_groups(self):
    test_list = []
    operation_ids = []
    
    operation_ids.append(
      self.executor.add_operation(
        append_to_list, ["main_processing", "additional_processing"], test_list, 2))
    
    operation_ids.append(
      self.executor.add_foreach_operation(
        append_to_list_before, ["main_processing", "additional_processing"],
        test_list, 2))
    
    additional_executor = pgoperations.OperationExecutor()
    operation_ids.append(
      self.executor.add_executor(additional_executor, ["main_processing"]))
    
    self.executor.remove_operation(operation_ids[2], ["main_processing"])
    self.assertEqual(
      len(self.executor.get_operation_groups(include_empty_groups=False)), 2)
    
    self.executor.remove_operation(operation_ids[1], ["main_processing"])
    self.assertEqual(
      len(self.executor.get_operation_groups(include_empty_groups=False)), 2)
    
    self.executor.remove_operation(operation_ids[0], ["main_processing"])
    non_empty_operation_groups = self.executor.get_operation_groups(
      include_empty_groups=False)
    self.assertEqual(len(non_empty_operation_groups), 1)
    self.assertNotIn("main_processing", non_empty_operation_groups)
    self.assertIn("additional_processing", non_empty_operation_groups)
    
    self.executor.remove_operation(operation_ids[1], ["additional_processing"])
    non_empty_operation_groups = self.executor.get_operation_groups(
      include_empty_groups=False)
    self.assertEqual(len(non_empty_operation_groups), 1)
    self.assertNotIn("main_processing", non_empty_operation_groups)
    self.assertIn("additional_processing", non_empty_operation_groups)
    
    self.executor.remove_operation(operation_ids[0], ["additional_processing"])
    self.assertEqual(len(self.executor.get_operation_groups(
      include_empty_groups=False)), 0)
  
  def test_get_operation(self):
    test_list = []
    operation_ids = []
    operation_ids.append(
      self.executor.add_operation(
        append_to_list, ["main_processing"], test_list, 2))
    operation_ids.append(
      self.executor.add_operation(
        append_to_list, ["additional_processing"], test_list, 3))
    operation_ids.append(
      self.executor.add_foreach_operation(
        append_to_list_before, ["additional_processing"], test_list, 4))
    
    additional_executor = pgoperations.OperationExecutor()
    operation_ids.append(
      self.executor.add_executor(additional_executor, ["main_processing"]))
    
    self.assertEqual(
      self.executor.get_operation(
        operation_ids[0]), (append_to_list, (test_list, 2), {}))
    self.assertEqual(
      self.executor.get_operation(
        operation_ids[1]), (append_to_list, (test_list, 3), {}))
    self.assertEqual(
      self.executor.get_operation(
        operation_ids[2]), (append_to_list_before, (test_list, 4), {}))
    
    self.assertEqual(self.executor.get_operation(operation_ids[3]), additional_executor)
  
  def test_get_operation_invalid_id(self):
    self.assertIsNone(self.executor.get_operation(-1))
  
  def test_get_operation_positon(self):
    test_list = []
    operation_ids = []
    
    operation_ids.append(
      self.executor.add_operation(append_to_list, ["main_processing"], test_list, 2))
    operation_ids.append(
      self.executor.add_operation(append_to_list, ["main_processing"], test_list, 3))
    operation_ids.append(
      self.executor.add_operation(append_to_list, ["main_processing"], test_list, 4))
    
    self.assertEqual(
      self.executor.get_operation_positon(operation_ids[0], "main_processing"), 0)
    self.assertEqual(
      self.executor.get_operation_positon(operation_ids[1], "main_processing"), 1)
    self.assertEqual(
      self.executor.get_operation_positon(operation_ids[2], "main_processing"), 2)
  
  def test_get_operation_positon_invalid_id(self):
    self.executor.add_operation(append_test, ["main_processing"])
    with self.assertRaises(ValueError):
      self.executor.get_operation_positon(-1, "main_processing")
  
  def test_get_operation_positon_operation_not_in_group(self):
    operation_id = self.executor.add_operation(append_test, ["main_processing"])
    with self.assertRaises(ValueError):
      self.executor.get_operation_positon(operation_id, "additional_processing")
  
  def test_find_matching_operations(self):
    test_list = []
    operation_ids = []
    
    operation_ids.append(
      self.executor.add_operation(append_to_list, ["main_processing"], test_list, 2))
    operation_ids.append(
      self.executor.add_operation(append_to_list, ["main_processing"], test_list, 3))
    operation_ids.append(
      self.executor.add_operation(
        append_to_list, ["additional_processing"], test_list, 3))
    
    operation_ids.append(
      self.executor.add_foreach_operation(
        append_to_list_before, ["main_processing"], test_list, 3))
    
    additional_executor = pgoperations.OperationExecutor()
    operation_ids.append(
      self.executor.add_executor(additional_executor, ["main_processing"]))
    
    self.assertEqual(
      self.executor.find_matching_operations(
        append_to_list, "main_processing"), [operation_ids[0], operation_ids[1]])
    self.assertEqual(
      self.executor.find_matching_operations(
        append_to_list, "main_processing", self.executor.TYPE_FOREACH_OPERATION), [])
    self.assertEqual(
      self.executor.find_matching_operations(
        append_to_list, "main_processing", self.executor.TYPE_EXECUTOR), [])
    
    self.assertEqual(
      self.executor.find_matching_operations(
        append_to_list_before, "main_processing"), [])
    self.assertEqual(
      self.executor.find_matching_operations(
        append_to_list_before, "main_processing", self.executor.TYPE_FOREACH_OPERATION),
      [operation_ids[3]])
    self.assertEqual(
      self.executor.find_matching_operations(
        append_to_list_before, "main_processing", self.executor.TYPE_EXECUTOR), [])
    
    self.assertEqual(
      self.executor.find_matching_operations(additional_executor, "main_processing"),
      [])
    self.assertEqual(
      self.executor.find_matching_operations(
        additional_executor, "main_processing", self.executor.TYPE_FOREACH_OPERATION),
      [])
    self.assertEqual(
      self.executor.find_matching_operations(
        additional_executor, "main_processing", self.executor.TYPE_EXECUTOR),
      [operation_ids[4]])
  
  def test_find_matching_operations_non_existing_group(self):
    self.executor.add_operation(append_test, ["main_processing"])
    with self.assertRaises(ValueError):
      self.executor.find_matching_operations(append_test, "additional_processing")
  
  def test_reorder_operation(self):
    operation_ids = []
    operation_ids.append(self.executor.add_operation(append_test, ["main_processing"]))
    operation_ids.append(self.executor.add_operation(append_test, ["main_processing"]))
    operation_ids.append(self.executor.add_operation(append_test, ["main_processing"]))
    operation_ids.append(self.executor.add_operation(append_test, ["main_processing"]))
    
    self.executor.reorder_operation(operation_ids[3], "main_processing", 0)
    self.executor.reorder_operation(operation_ids[2], "main_processing", 1)
    self.executor.reorder_operation(operation_ids[1], "main_processing", 2)
    
    self.assertEqual(len(self.executor.get_operations("main_processing")), 4)
    self.assertEqual(
      self.executor.get_operation_positon(operation_ids[0], "main_processing"), 3)
    self.assertEqual(
      self.executor.get_operation_positon(operation_ids[1], "main_processing"), 2)
    self.assertEqual(
      self.executor.get_operation_positon(operation_ids[2], "main_processing"), 1)
    self.assertEqual(
      self.executor.get_operation_positon(operation_ids[3], "main_processing"), 0)
    
    self.executor.reorder_operation(operation_ids[2], "main_processing", 5)
    self.assertEqual(
      self.executor.get_operation_positon(operation_ids[2], "main_processing"), 3)
    
    self.executor.reorder_operation(operation_ids[3], "main_processing", -1)
    self.executor.reorder_operation(operation_ids[1], "main_processing", -3)
    self.executor.reorder_operation(operation_ids[0], "main_processing", -4)
    
    self.assertEqual(len(self.executor.get_operations("main_processing")), 4)
    self.assertEqual(
      self.executor.get_operation_positon(operation_ids[0], "main_processing"), 0)
    self.assertEqual(
      self.executor.get_operation_positon(operation_ids[1], "main_processing"), 1)
    self.assertEqual(
      self.executor.get_operation_positon(operation_ids[2], "main_processing"), 2)
    self.assertEqual(
      self.executor.get_operation_positon(operation_ids[3], "main_processing"), 3)
  
  def test_reorder_operation_invalid_id(self):
    with self.assertRaises(ValueError):
      self.executor.reorder_operation(-1, "main_processing", 0)
  
  def test_reorder_operation_non_existing_group(self):
    operation_id = self.executor.add_operation(append_test, ["main_processing"])
    with self.assertRaises(ValueError):
      self.executor.reorder_operation(operation_id, "additional_processing", 0)
  
  def test_reorder_operation_operation_not_in_group(self):
    operation_id = self.executor.add_operation(append_test, ["main_processing"])
    self.executor.add_operation(append_test, ["additional_processing"])
    with self.assertRaises(ValueError):
      self.executor.reorder_operation(operation_id, "additional_processing", 0)
  
  def test_remove_operation(self):
    test_list = []
    operation_ids = []
    
    operation_ids.append(
      self.executor.add_operation(append_to_list, ["main_processing"], test_list, 2))
    operation_ids.append(
      self.executor.add_foreach_operation(
        append_to_list_before, ["main_processing"], test_list, 3))
    
    additional_executor = pgoperations.OperationExecutor()
    operation_ids.append(
      self.executor.add_executor(additional_executor, ["main_processing"]))
    
    self.executor.remove_operation(operation_ids[0], ["main_processing"])
    self.assertFalse(self.executor.has_operation(operation_ids[0]))
    self.assertFalse(
      self.executor.has_matching_operation(append_to_list, "main_processing"))
    
    self.executor.remove_operation(operation_ids[1], ["main_processing"])
    self.assertFalse(self.executor.has_operation(operation_ids[1]))
    self.assertFalse(
      self.executor.has_matching_operation(append_to_list_before, "main_processing"))
    
    self.executor.remove_operation(operation_ids[2], ["main_processing"])
    self.assertFalse(self.executor.has_operation(operation_ids[2]))
    self.assertFalse(
      self.executor.has_matching_operation(
        additional_executor, "main_processing",
        operation_type=self.executor.TYPE_EXECUTOR))
  
  def test_remove_multiple_operations(self):
    test_list = []
    operation_ids = []
    
    operation_ids.append(
      self.executor.add_operation(append_to_list, ["main_processing"], test_list, 2))
    operation_ids.append(
      self.executor.add_operation(append_to_list, ["main_processing"], test_list, 3))
    
    self.executor.remove_operation(operation_ids[0], ["main_processing"])
    self.assertFalse(self.executor.has_operation(operation_ids[0]))
    self.assertTrue(
      self.executor.has_matching_operation(append_to_list, "main_processing"))
    
    self.executor.remove_operation(operation_ids[1], ["main_processing"])
    self.assertFalse(self.executor.has_operation(operation_ids[1]))
    self.assertFalse(
      self.executor.has_matching_operation(append_to_list, "main_processing"))
    
    operation_ids.append(
      self.executor.add_foreach_operation(
        append_to_list_before, ["main_processing"], test_list, 4))
    operation_ids.append(
      self.executor.add_foreach_operation(
        append_to_list_before, ["main_processing"], test_list, 5))
    
    self.executor.remove_operation(operation_ids[2], ["main_processing"])
    self.assertFalse(self.executor.has_operation(operation_ids[2]))
    self.assertTrue(
      self.executor.has_matching_operation(
        append_to_list_before, "main_processing",
        operation_type=self.executor.TYPE_FOREACH_OPERATION))
    
    self.executor.remove_operation(operation_ids[3], ["main_processing"])
    self.assertFalse(self.executor.has_operation(operation_ids[3]))
    self.assertFalse(
      self.executor.has_matching_operation(
        append_to_list_before, "main_processing",
        operation_type=self.executor.TYPE_FOREACH_OPERATION))
    
    additional_executor = pgoperations.OperationExecutor()
    operation_ids.append(
      self.executor.add_executor(additional_executor, ["main_processing"]))
    operation_ids.append(
      self.executor.add_executor(additional_executor, ["main_processing"]))
    
    self.executor.remove_operation(operation_ids[4], ["main_processing"])
    self.assertFalse(self.executor.has_operation(operation_ids[4]))
    self.assertTrue(
      self.executor.has_matching_operation(
        additional_executor, "main_processing",
        operation_type=self.executor.TYPE_EXECUTOR))
    
    self.executor.remove_operation(operation_ids[5], ["main_processing"])
    self.assertFalse(self.executor.has_operation(operation_ids[5]))
    self.assertFalse(
      self.executor.has_matching_operation(
        additional_executor, "main_processing",
        operation_type=self.executor.TYPE_EXECUTOR))
  
  def test_remove_operation_from_all_groups_operation_only_in_one_group(self):
    test_list = []
    
    operation_id = self.executor.add_operation(
      append_to_list, ["main_processing"], test_list, 2)
    self.executor.add_operation(append_to_list, ["additional_processing"], test_list, 3)
    
    self.executor.remove_operation(operation_id)
    self.assertFalse(self.executor.has_operation(operation_id, "main_processing"))
    self.assertFalse(self.executor.has_operation(operation_id, "additional_processing"))
  
  def test_remove_operation_in_one_group_keep_in_others(self):
    operation_id = self.executor.add_operation(
      append_test, ["main_processing", "additional_processing"])
    
    self.executor.remove_operation(operation_id, ["main_processing"])
    self.assertFalse(self.executor.has_operation(operation_id, "main_processing"))
    self.assertTrue(self.executor.has_operation(operation_id, "additional_processing"))
  
  def test_remove_operation_invalid_id(self):
    with self.assertRaises(ValueError):
      self.executor.remove_operation(-1)
  
  def test_remove_operation_non_existing_group(self):
    operation_id = self.executor.add_operation(append_test, ["main_processing"])
    with self.assertRaises(ValueError):
      self.executor.remove_operation(operation_id, ["additional_processing"])
  
  def test_remove_operation_multiple_groups_at_once(self):
    test_list = []
    operation_id = self.executor.add_operation(
      append_to_list, ["main_processing", "additional_processing"], test_list, 2)
    
    self.executor.remove_operation(operation_id)
    self.assertFalse(self.executor.has_operation(operation_id))
    self.assertFalse(
      self.executor.has_matching_operation(append_to_list, "main_processing"))
    self.assertFalse(
      self.executor.has_matching_operation(append_to_list, "additional_processing"))
  
  def test_remove_groups(self):
    test_list = []
    self.executor.add_operation(append_test, ["main_processing", "additional_processing"])
    self.executor.add_foreach_operation(
      append_to_list_before, ["main_processing", "additional_processing"], test_list, 3)
    self.executor.add_executor(append_test, ["main_processing", "additional_processing"])
    
    self.executor.remove_groups(["main_processing"])
    self.assertEqual(len(self.executor.get_operation_groups()), 1)
    self.assertIn("additional_processing", self.executor.get_operation_groups())
    self.assertIsNone(self.executor.get_operations("main_processing"))
    
    self.executor.remove_groups(["additional_processing"])
    self.assertEqual(len(self.executor.get_operation_groups()), 0)
    self.assertIsNone(self.executor.get_operations("main_processing"))
    self.assertIsNone(self.executor.get_operations("additional_processing"))
  
  def test_remove_all_groups(self):
    test_list = []
    self.executor.add_operation(append_test, ["main_processing", "additional_processing"])
    self.executor.add_foreach_operation(
      append_to_list_before, ["main_processing", "additional_processing"], test_list, 3)
    self.executor.add_executor(append_test, ["main_processing", "additional_processing"])
    
    self.executor.remove_groups()
    self.assertEqual(len(self.executor.get_operation_groups()), 0)
    self.assertIsNone(self.executor.get_operations("main_processing"))
    self.assertIsNone(self.executor.get_operations("additional_processing"))
  
  def test_remove_groups_non_existing_group(self):
    with self.assertRaises(ValueError):
      self.executor.remove_groups(["main_processing"])


class TestOperationExecutorExecuteOperations(OperationExecutorTestCase):
  
  @parameterized.parameterized.expand([
    ("default",
     "main_processing", append_test, [], [],
     ["test"]),
    
    ("execute_args",
     "main_processing", append_to_list, [], [1],
     [1]),
    
    ("add_and_execute_args",
     "main_processing", extend_list, [1], [2, 3],
     [1, 2, 3]),
    
  ])
  def test_execute_single_operation(
        self,
        test_case_name_suffix,
        operation_group, operation, add_operation_args, execute_args,
        expected_result):
    test_list = []
    
    self.executor.add_operation(
      operation, [operation_group], test_list, *add_operation_args)
    self.executor.execute([operation_group], *execute_args)
    
    self.assertEqual(test_list, expected_result)
  
  def test_execute_invalid_number_of_args(self):
    test_list = []
    self.executor.add_operation(append_to_list, ["main_processing"], test_list, 1, 2)
    
    with self.assertRaises(TypeError):
      self.executor.execute(["main_processing"])
  
  def test_execute_additional_args_invalid_number_of_args(self):
    test_list = []
    self.executor.add_operation(append_to_list, ["main_processing"], test_list)
    
    with self.assertRaises(TypeError):
      self.executor.execute(["main_processing"])
    
    with self.assertRaises(TypeError):
      self.executor.execute(["main_processing"], 1, 2)
  
  def test_execute_additional_kwargs_override_former_kwargs(self):
    test_dict = {}
    self.executor.add_operation(update_dict, ["main_processing"], test_dict, one=1, two=2)
    self.executor.execute(["main_processing"], two="two", three=3)
    
    self.assertDictEqual(test_dict, {"one": 1, "two": "two", "three": 3})

  def test_execute_multiple_operations(self):
    test_list = []
    self.executor.add_operation(append_test, ["main_processing"], test_list)
    self.executor.add_operation(extend_list, ["main_processing"], test_list, 1)
    
    self.executor.execute(["main_processing"])
    
    self.assertListEqual(test_list, ["test", 1])
  
  def test_execute_multiple_groups_multiple_operations(self):
    test_dict = {}
    self.executor.add_operation(
      update_dict, ["main_processing", "advanced_processing"], test_dict, one=1, two=2)
    self.executor.add_operation(
      update_dict, ["main_processing"], test_dict, two="two", three=3)
    
    self.executor.execute(["main_processing"])
    self.assertDictEqual(test_dict, {"one": 1, "two": "two", "three": 3})
    
    self.executor.execute(["advanced_processing"])
    self.assertDictEqual(test_dict, {"one": 1, "two": 2, "three": 3})
    
    test_dict.clear()
    self.executor.execute(["main_processing", "advanced_processing"])
    self.assertDictEqual(test_dict, {"one": 1, "two": 2, "three": 3})
    
    test_dict.clear()
    self.executor.execute(["advanced_processing", "main_processing"])
    self.assertDictEqual(test_dict, {"one": 1, "two": "two", "three": 3})
    
  def test_execute_empty_group(self):
    try:
      self.executor.execute(["main_processing"])
    except Exception:
      self.fail("executing no operations for the given group should not raise exception")


class TestOperationExecutorExecuteForeachOperations(OperationExecutorTestCase):
  
  @parameterized.parameterized.expand([
    ("default",
     append_to_list, append_to_list, "main_processing", [[1], [2]], [3],
     [1, 3, 2, 3]),
    
    ("before_operation",
     append_to_list, append_to_list_before, "main_processing", [[1], [2]], [3],
     [3, 1, 3, 2]),
    
    ("before_and_after_operation",
     append_to_list, append_to_list_before_and_after, "main_processing", [[1], [2]], [3],
     [3, 1, 3, 3, 2, 3]),
    
    ("before_and_after_operation_multiple_times",
     append_to_list, append_to_list_before_and_after_execute_twice,
     "main_processing", [[1], [2]], [3],
     [3, 1, 1, 3, 3, 2, 2, 3]),
    
  ])
  def test_execute_single_foreach(
        self,
        test_case_name_suffix, operation, foreach_operation, operation_group,
        operations_args, foreach_operation_args,
        expected_result):
    test_list = []
    
    self.executor.add_operation(
      operation, [operation_group], test_list, *operations_args[0])
    self.executor.add_operation(
      operation, [operation_group], test_list, *operations_args[1])
    self.executor.add_foreach_operation(
      foreach_operation, [operation_group], test_list, *foreach_operation_args)
    
    self.executor.execute([operation_group])
    
    self.assertListEqual(test_list, expected_result)
  
  @parameterized.parameterized.expand([
    ("simple",
     append_to_list, [append_to_list_before, append_to_list],
     "main_processing",
     [[1], [2]], [[3], [4]],
     [3, 1, 4, 3, 2, 4]),
    
    ("complex",
     append_to_list,
     [append_to_list_before_and_after, append_to_list_before_and_after_execute_twice],
     "main_processing",
     [[1], [2]], [[3], [4]],
     [3, 4, 1, 3, 1, 4,
      3, 4, 2, 3, 2, 4]),
    
    ("even_more_complex",
     append_to_list,
     [append_to_list_before_and_after, append_to_list_before_middle_after_execute_twice],
     "main_processing",
     [[1], [2]], [[3], [4]],
     [3, 4, 1, 3, 4, 1, 4,
      3, 4, 2, 3, 4, 2, 4]),
  ])
  def test_execute_multiple_foreachs(
        self,
        test_case_name_suffix, operation, foreach_operations, operation_group,
        operations_args, foreach_operations_args,
        expected_result):
    test_list = []
    
    self.executor.add_operation(
      operation, [operation_group], test_list, *operations_args[0])
    self.executor.add_operation(
      operation, [operation_group], test_list, *operations_args[1])
    self.executor.add_foreach_operation(
      foreach_operations[0], [operation_group], test_list, *foreach_operations_args[0])
    self.executor.add_foreach_operation(
      foreach_operations[1], [operation_group], test_list, *foreach_operations_args[1])
    
    self.executor.execute([operation_group])
    
    self.assertListEqual(test_list, expected_result)
  
  def test_execute_foreach_use_return_value_from_operation(self):
    test_list = []
    self.executor.add_operation(append_to_list, ["main_processing"], test_list, 1)
    self.executor.add_operation(append_to_list, ["main_processing"], test_list, 2)
    self.executor.add_foreach_operation(
      append_to_list_again, ["main_processing"], test_list)
    
    self.executor.execute(["main_processing"])
    
    self.assertListEqual(test_list, [1, 1, 2, 2])
  
  def test_execute_foreach_does_nothing_in_another_executor(self):
    test_list = []
    another_executor = pgoperations.OperationExecutor()
    another_executor.add_operation(append_to_list, ["main_processing"], test_list, 1)
    another_executor.add_operation(append_to_list, ["main_processing"], test_list, 2)
    
    self.executor.add_executor(another_executor, ["main_processing"])
    self.executor.add_operation(append_to_list, ["main_processing"], test_list, 3)
    self.executor.add_foreach_operation(
      append_to_list_again, ["main_processing"], test_list)
    
    self.executor.execute(["main_processing"])
    
    self.assertListEqual(test_list, [1, 2, 3, 3])


class TestOperationExecutorExecuteWithExecutor(OperationExecutorTestCase):
  
  def test_execute(self):
    test_list = []
    another_executor = pgoperations.OperationExecutor()
    another_executor.add_operation(append_to_list, ["main_processing"], test_list, 1)
    another_executor.add_operation(append_test, ["main_processing"], test_list)
    
    self.executor.add_operation(append_to_list, ["main_processing"], test_list, 2)
    self.executor.add_executor(another_executor, ["main_processing"])
    
    self.executor.execute(["main_processing"])
    
    self.assertListEqual(test_list, [2, 1, "test"])
  
  def test_execute_after_adding_operations_to_executor(self):
    test_list = []
    another_executor = pgoperations.OperationExecutor()
    
    self.executor.add_operation(append_to_list, ["main_processing"], test_list, 2)
    self.executor.add_executor(another_executor, ["main_processing"])
    
    another_executor.add_operation(append_to_list, ["main_processing"], test_list, 1)
    another_executor.add_operation(append_test, ["main_processing"], test_list)
    
    self.executor.execute(["main_processing"])
    
    self.assertListEqual(test_list, [2, 1, "test"])
  
  def test_execute_multiple_executors_after_adding_operations_to_them(self):
    test_list = []
    more_executors = [pgoperations.OperationExecutor(), pgoperations.OperationExecutor()]
    
    self.executor.add_operation(append_to_list, ["main_processing"], test_list, 2)
    self.executor.add_executor(more_executors[0], ["main_processing"])
    self.executor.add_executor(more_executors[1], ["main_processing"])
    
    more_executors[0].add_operation(append_to_list, ["main_processing"], test_list, 1)
    more_executors[0].add_operation(append_test, ["main_processing"], test_list)
    
    more_executors[1].add_operation(append_to_list, ["main_processing"], test_list, 3)
    more_executors[1].add_operation(append_to_list, ["main_processing"], test_list, 4)
    
    self.executor.execute(["main_processing"])
    
    self.assertListEqual(test_list, [2, 1, "test", 3, 4])
  
  def test_execute_empty_group(self):
    another_executor = pgoperations.OperationExecutor()
    try:
      self.executor.add_executor(another_executor, ["invalid_group"])
    except Exception:
      self.fail("adding operations from an empty group from another "
                "OperationExecutor should not raise exception")
