# -*- coding: utf-8 -*-
#
# Copyright (C) 2014-2019 khalim19
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

from .. import operations as pgoperations


def append_test(list_):
  list_.append("test")


def append_to_list(list_, arg):
  list_.append(arg)
  return arg


def append_to_list_multiple_args(list_, arg1, arg2, arg3):
  for arg in [arg1, arg2, arg3]:
    list_.append(arg)
  return arg1, arg2, arg3


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


class OperationExecutorTestCase(unittest.TestCase):
  
  def setUp(self):
    self.executor = pgoperations.OperationExecutor()


class TestOperationExecutor(OperationExecutorTestCase):
  
  @parameterized.parameterized.expand([
    ("default_group",
     None, ["default"]
     ),
    
    ("default_group_explicit_name",
     "default", ["default"]
     ),
    
    ("specific_groups",
     ["main", "additional"],
     ["main", "additional"]
     ),
  ])
  def test_add(self, test_case_name_suffix, groups, list_operations_groups):
    test_list = []
    
    self.executor.add(append_test, groups, args=[test_list])
    
    for list_operations_group in list_operations_groups:
      self.assertEqual(len(self.executor.list_operations(list_operations_group)), 1)
  
  def test_add_to_all_groups(self):
    test_list = []
    
    self.executor.add(append_test, ["main", "additional"], [test_list])
    self.executor.add(append_test, "all", [test_list])
    
    self.assertEqual(len(self.executor.list_operations("main")), 2)
    self.assertEqual(len(self.executor.list_operations("additional")), 2)
    self.assertFalse("default" in self.executor.list_groups())
    
    self.executor.add(append_test, args=[test_list])
    self.executor.add(append_test, "all", [test_list])
    
    self.assertEqual(len(self.executor.list_operations("main")), 3)
    self.assertEqual(len(self.executor.list_operations("additional")), 3)
    self.assertEqual(len(self.executor.list_operations()), 2)
  
  def test_add_return_unique_ids_within_same_executor(self):
    test_list = []
    operation_ids = []
    
    operation_ids.append(self.executor.add(append_to_list, args=[test_list, 2]))
    operation_ids.append(self.executor.add(append_to_list, args=[test_list, 3]))
    operation_ids.append(self.executor.add(append_to_list, args=[test_list, 2]))
    operation_ids.append(
      self.executor.add(append_to_list_before, args=[test_list, 3], foreach=True))
    operation_ids.append(
      self.executor.add(append_to_list_before, args=[test_list, 3], foreach=True))
    
    additional_executor = pgoperations.OperationExecutor()
    operation_ids.append(self.executor.add(additional_executor))
    operation_ids.append(self.executor.add(additional_executor))
    
    self.assertEqual(len(operation_ids), len(set(operation_ids)))
  
  def test_add_return_unique_ids_across_multiple_executors(self):
    operation_id = self.executor.add(append_test)
    
    additional_executor = pgoperations.OperationExecutor()
    additional_operation_id = additional_executor.add(append_test)
    
    self.assertNotEqual(operation_id, additional_operation_id)
  
  def test_add_return_same_id_for_multiple_groups(self):
    test_list = []
    operation_id = self.executor.add(
      append_to_list, ["main", "additional"], [test_list, 2])
    
    self.assertTrue(self.executor.has_operation(operation_id, "all"))
    self.assertTrue(self.executor.has_operation(operation_id, ["main"]))
    self.assertTrue(self.executor.has_operation(operation_id, ["additional"]))
  
  def test_add_to_groups(self):
    test_list = []
    operation_id = self.executor.add(append_to_list, ["main"], [test_list, 2])
    
    self.executor.add_to_groups(operation_id, ["additional"])
    self.assertTrue(self.executor.has_operation(operation_id, ["main"]))
    self.assertTrue(self.executor.has_operation(operation_id, ["additional"]))
    
    self.executor.add_to_groups(operation_id, ["main"])
    self.assertEqual(len(self.executor.list_operations("main")), 1)
    self.assertEqual(len(self.executor.list_operations("main", foreach=True)), 0)
    
    foreach_operation_id = self.executor.add(
      append_to_list_before, ["main"], [test_list, 2], foreach=True)
    
    self.executor.add_to_groups(foreach_operation_id, ["additional"])
    self.assertTrue(self.executor.has_operation(foreach_operation_id, ["main"]))
    self.assertTrue(self.executor.has_operation(foreach_operation_id, ["additional"]))
    
    self.executor.add_to_groups(foreach_operation_id, ["main"])
    self.assertEqual(len(self.executor.list_operations("main")), 1)
    self.assertEqual(len(self.executor.list_operations("main", foreach=True)), 1)
    
    additional_executor = pgoperations.OperationExecutor()
    executor_id = self.executor.add(additional_executor, ["main"])
    
    self.executor.add_to_groups(executor_id, ["additional"])
    self.assertTrue(self.executor.has_operation(executor_id, ["main"]))
    self.assertTrue(self.executor.has_operation(executor_id, ["additional"]))
    
    self.executor.add_to_groups(executor_id, ["main"])
    self.assertEqual(len(self.executor.list_operations("main")), 2)
    self.assertEqual(len(self.executor.list_operations("main", foreach=True)), 1)
  
  def test_add_to_groups_same_group(self):
    test_list = []
    operation_id = self.executor.add(append_to_list, ["main"], [test_list, 2])
    
    self.executor.add_to_groups(operation_id, ["main"])
    self.assertEqual(len(self.executor.list_operations("main")), 1)
  
  def test_add_ignore_if_exists(self):
    test_list = []
    self.executor.add(append_to_list, args=[test_list, 1], ignore_if_exists=True)
    self.assertEqual(len(self.executor.list_operations()), 1)
    
    operation_id = self.executor.add(
      append_to_list, args=[test_list, 2], ignore_if_exists=True)
    self.assertEqual(len(self.executor.list_operations()), 1)
    self.assertIsNone(operation_id)
  
  def test_has_operation(self):
    operation_id = self.executor.add(append_to_list)
    self.assertTrue(self.executor.has_operation(operation_id))
  
  def test_contains(self):
    test_list = []
    
    self.executor.add(append_test, args=[test_list])
    self.assertTrue(self.executor.contains(append_test))
    
    additional_executor = pgoperations.OperationExecutor()
    self.executor.add(additional_executor)
    self.assertTrue(self.executor.contains(additional_executor))
    
    self.executor.add(append_to_list_again, args=[test_list], foreach=True)
    self.assertTrue(self.executor.contains(append_to_list_again, foreach=True))
  
  def test_list_operations_non_existing_group(self):
    self.assertIsNone(self.executor.list_operations("non_existing_group"))
  
  def test_list_operations(self):
    test_list = []
    self.executor.add(append_to_list, args=[test_list, 1])
    self.executor.add(append_to_list, args=[test_list, 2])
    
    self.assertListEqual(
      self.executor.list_operations(),
      [(append_to_list, [test_list, 1], {}), (append_to_list, [test_list, 2], {})])
    
    self.assertEqual(self.executor.list_operations(foreach=True), [])
  
  def test_get_foreach_operations(self):
    test_list = []
    self.executor.add(append_to_list_before, args=[test_list, 1], foreach=True)
    self.executor.add(append_to_list_before, args=[test_list, 2], foreach=True)
    
    self.assertListEqual(
      self.executor.list_operations(foreach=True),
      [(append_to_list_before, [test_list, 1], {}),
       (append_to_list_before, [test_list, 2], {})])
    
    self.assertEqual(self.executor.list_operations(), [])
  
  def test_get_foreach_operations_non_existing_group(self):
    self.assertIsNone(self.executor.list_operations("non_existing_group", foreach=True))
  
  def test_list_groups(self):
    test_list = []
    self.executor.add(append_to_list, ["main"], [test_list, 2])
    self.executor.add(append_to_list, ["additional"], [test_list, 3])
    
    self.assertEqual(len(self.executor.list_groups()), 2)
    self.assertIn("main", self.executor.list_groups())
    self.assertIn("additional", self.executor.list_groups())
  
  def test_list_groups_without_empty_groups(self):
    test_list = []
    operation_ids = []
    
    operation_ids.append(
      self.executor.add(append_to_list, ["main", "additional"], [test_list, 2]))
    
    operation_ids.append(
      self.executor.add(
        append_to_list_before, ["main", "additional"], [test_list, 2], foreach=True))
    
    additional_executor = pgoperations.OperationExecutor()
    operation_ids.append(self.executor.add(additional_executor, ["main"]))
    
    self.executor.remove(operation_ids[2], ["main"])
    self.assertEqual(len(self.executor.list_groups(include_empty_groups=False)), 2)
    
    self.executor.remove(operation_ids[1], ["main"])
    self.assertEqual(len(self.executor.list_groups(include_empty_groups=False)), 2)
    
    self.executor.remove(operation_ids[0], ["main"])
    non_empty_groups = self.executor.list_groups(include_empty_groups=False)
    self.assertEqual(len(non_empty_groups), 1)
    self.assertNotIn("main", non_empty_groups)
    self.assertIn("additional", non_empty_groups)
    
    self.executor.remove(operation_ids[1], ["additional"])
    non_empty_groups = self.executor.list_groups(include_empty_groups=False)
    self.assertEqual(len(non_empty_groups), 1)
    self.assertNotIn("main", non_empty_groups)
    self.assertIn("additional", non_empty_groups)
    
    self.executor.remove(operation_ids[0], ["additional"])
    self.assertEqual(len(self.executor.list_groups(include_empty_groups=False)), 0)
  
  def test_get_operation(self):
    test_list = []
    operation_ids = []
    operation_ids.append(
      self.executor.add(append_to_list, ["main"], [test_list, 2]))
    operation_ids.append(
      self.executor.add(append_to_list, ["additional"], [test_list, 3]))
    operation_ids.append(
      self.executor.add(
        append_to_list_before, ["additional"], [test_list, 4], foreach=True))
    
    additional_executor = pgoperations.OperationExecutor()
    operation_ids.append(self.executor.add(additional_executor, ["main"]))
    
    self.assertEqual(
      self.executor.get_operation(operation_ids[0]),
      (append_to_list, [test_list, 2], {}))
    self.assertEqual(
      self.executor.get_operation(operation_ids[1]),
      (append_to_list, [test_list, 3], {}))
    self.assertEqual(
      self.executor.get_operation(operation_ids[2]),
      (append_to_list_before, [test_list, 4], {}))
    
    self.assertEqual(self.executor.get_operation(operation_ids[3]), additional_executor)
  
  def test_get_operation_invalid_id(self):
    self.assertIsNone(self.executor.get_operation(-1))
  
  def test_get_position(self):
    test_list = []
    operation_ids = []
    
    operation_ids.append(self.executor.add(append_to_list, args=[test_list, 2]))
    operation_ids.append(self.executor.add(append_to_list, args=[test_list, 3]))
    operation_ids.append(self.executor.add(append_to_list, args=[test_list, 4]))
    
    self.assertEqual(self.executor.get_position(operation_ids[0]), 0)
    self.assertEqual(self.executor.get_position(operation_ids[1]), 1)
    self.assertEqual(self.executor.get_position(operation_ids[2]), 2)
  
  def test_get_position_invalid_id(self):
    self.executor.add(append_test)
    with self.assertRaises(ValueError):
      self.executor.get_position(-1)
  
  def test_get_position_operation_not_in_group(self):
    operation_id = self.executor.add(append_test, ["main"])
    with self.assertRaises(ValueError):
      self.executor.get_position(operation_id, "additional")
  
  def test_find(self):
    test_list = []
    operation_ids = []
    
    operation_ids.append(
      self.executor.add(append_to_list, args=[test_list, 2]))
    operation_ids.append(
      self.executor.add(append_to_list, args=[test_list, 3]))
    operation_ids.append(
      self.executor.add(append_to_list, ["additional"], [test_list, 3]))
    
    operation_ids.append(
      self.executor.add(append_to_list_before, args=[test_list, 3], foreach=True))
    
    additional_executor = pgoperations.OperationExecutor()
    operation_ids.append(self.executor.add(additional_executor))
    
    self.assertEqual(
      self.executor.find(append_to_list),
      [operation_ids[0], operation_ids[1]])
    self.assertEqual(
      self.executor.find(append_to_list, foreach=True), [])
    
    self.assertEqual(
      self.executor.find(append_to_list_before), [])
    self.assertEqual(
      self.executor.find(append_to_list_before, foreach=True),
      [operation_ids[3]])
    
    self.assertEqual(
      self.executor.find(additional_executor),
      [operation_ids[4]])
    self.assertEqual(
      self.executor.find(additional_executor, foreach=True), [])
  
  def test_find_non_existing_group(self):
    operation_id = self.executor.add(append_test)
    self.assertEqual(
      self.executor.find(append_test, ["non_existing_group"]),
      [])
    
    self.assertEqual(
      self.executor.find(append_test, ["default", "non_existing_group"]),
      [operation_id])
  
  def test_reorder(self):
    operation_ids = []
    operation_ids.append(self.executor.add(append_test))
    operation_ids.append(self.executor.add(append_test))
    operation_ids.append(self.executor.add(append_test))
    operation_ids.append(self.executor.add(append_test))
    
    self.executor.reorder(operation_ids[3], 0)
    self.executor.reorder(operation_ids[2], 1)
    self.executor.reorder(operation_ids[1], 2)
    
    self.assertEqual(len(self.executor.list_operations()), 4)
    self.assertEqual(self.executor.get_position(operation_ids[0]), 3)
    self.assertEqual(self.executor.get_position(operation_ids[1]), 2)
    self.assertEqual(self.executor.get_position(operation_ids[2]), 1)
    self.assertEqual(self.executor.get_position(operation_ids[3]), 0)
    
    self.executor.reorder(operation_ids[2], 5)
    self.assertEqual(self.executor.get_position(operation_ids[2]), 3)
    
    self.executor.reorder(operation_ids[3], -1)
    self.executor.reorder(operation_ids[1], -3)
    self.executor.reorder(operation_ids[0], -4)
    
    self.assertEqual(len(self.executor.list_operations()), 4)
    self.assertEqual(self.executor.get_position(operation_ids[0]), 0)
    self.assertEqual(self.executor.get_position(operation_ids[1]), 1)
    self.assertEqual(self.executor.get_position(operation_ids[2]), 2)
    self.assertEqual(self.executor.get_position(operation_ids[3]), 3)
  
  def test_reorder_invalid_id(self):
    with self.assertRaises(ValueError):
      self.executor.reorder(-1, 0)
  
  def test_reorder_non_existing_group(self):
    operation_id = self.executor.add(append_test)
    with self.assertRaises(ValueError):
      self.executor.reorder(operation_id, 0, "non_existing_group")
  
  def test_reorder_operation_not_in_group(self):
    operation_id = self.executor.add(append_test, ["main"])
    self.executor.add(append_test, ["additional"])
    with self.assertRaises(ValueError):
      self.executor.reorder(operation_id, 0, "additional")
  
  def test_remove(self):
    test_list = []
    operation_ids = []
    
    operation_ids.append(self.executor.add(append_to_list, args=[test_list, 2]))
    operation_ids.append(
      self.executor.add(append_to_list_before, args=[test_list, 3], foreach=True))
    
    additional_executor = pgoperations.OperationExecutor()
    operation_ids.append(self.executor.add(additional_executor))
    
    self.executor.remove(operation_ids[0])
    self.assertFalse(self.executor.has_operation(operation_ids[0]))
    self.assertFalse(self.executor.contains(append_to_list))
    
    self.executor.remove(operation_ids[1])
    self.assertFalse(self.executor.has_operation(operation_ids[1]))
    self.assertFalse(self.executor.contains(append_to_list_before))
    
    self.executor.remove(operation_ids[2])
    self.assertFalse(self.executor.has_operation(operation_ids[2]))
    self.assertFalse(self.executor.contains(additional_executor))
  
  def test_remove_multiple_operations(self):
    test_list = []
    operation_ids = []
    
    operation_ids.append(self.executor.add(append_to_list, args=[test_list, 2]))
    operation_ids.append(self.executor.add(append_to_list, args=[test_list, 3]))
    
    self.executor.remove(operation_ids[0])
    self.assertFalse(self.executor.has_operation(operation_ids[0]))
    self.assertTrue(self.executor.contains(append_to_list))
    
    self.executor.remove(operation_ids[1])
    self.assertFalse(self.executor.has_operation(operation_ids[1]))
    self.assertFalse(self.executor.contains(append_to_list))
    
    operation_ids.append(
      self.executor.add(append_to_list_before, args=[test_list, 4], foreach=True))
    operation_ids.append(
      self.executor.add(append_to_list_before, args=[test_list, 5], foreach=True))
    
    self.executor.remove(operation_ids[2])
    self.assertFalse(self.executor.has_operation(operation_ids[2]))
    self.assertTrue(self.executor.contains(append_to_list_before, foreach=True))
    
    self.executor.remove(operation_ids[3])
    self.assertFalse(self.executor.has_operation(operation_ids[3]))
    self.assertFalse(self.executor.contains(append_to_list_before, foreach=True))
    
    additional_executor = pgoperations.OperationExecutor()
    operation_ids.append(self.executor.add(additional_executor))
    operation_ids.append(self.executor.add(additional_executor))
    
    self.executor.remove(operation_ids[4])
    self.assertFalse(self.executor.has_operation(operation_ids[4]))
    self.assertTrue(self.executor.contains(additional_executor))
    
    self.executor.remove(operation_ids[5])
    self.assertFalse(self.executor.has_operation(operation_ids[5]))
    self.assertFalse(self.executor.contains(additional_executor))
  
  def test_remove_from_all_groups_operation_only_in_one_group(self):
    test_list = []
    
    operation_id = self.executor.add(append_to_list, ["main"], [test_list, 2])
    self.executor.add(append_to_list, ["additional"], [test_list, 3])
    
    self.executor.remove(operation_id, "all")
    self.assertFalse(self.executor.has_operation(operation_id, ["main"]))
    self.assertFalse(self.executor.has_operation(operation_id, ["additional"]))
  
  def test_remove_in_one_group_keep_in_others(self):
    operation_id = self.executor.add(append_test, ["main", "additional"])
    
    self.executor.remove(operation_id, ["main"])
    self.assertFalse(self.executor.has_operation(operation_id, ["main"]))
    self.assertTrue(self.executor.has_operation(operation_id, ["additional"]))
  
  def test_remove_if_invalid_id(self):
    with self.assertRaises(ValueError):
      self.executor.remove(-1)
  
  def test_remove_non_existing_group(self):
    operation_id = self.executor.add(append_test, ["main"])
    with self.assertRaises(ValueError):
      self.executor.remove(operation_id, ["additional"])
  
  def test_remove_ignore_if_not_exists(self):
    try:
      self.executor.remove(-1, ignore_if_not_exists=True)
    except ValueError:
      self.fail(
        "removing operations when `ignore_if_not_exists=True` should not raise error")
  
  def test_remove_multiple_groups_at_once(self):
    test_list = []
    operation_id = self.executor.add(
      append_to_list, ["main", "additional"], [test_list, 2])
    
    self.executor.remove(operation_id, "all")
    self.assertFalse(self.executor.has_operation(operation_id))
    self.assertFalse(self.executor.contains(append_to_list, ["main"]))
    self.assertFalse(self.executor.contains(append_to_list, ["additional"]))
  
  def test_remove_groups(self):
    test_list = []
    self.executor.add(append_test, ["main", "additional"])
    self.executor.add(
      append_to_list_before, ["main", "additional"], [test_list, 3], foreach=True)
    self.executor.add(append_test, ["main", "additional"])
    
    self.executor.remove_groups(["main"])
    self.assertEqual(len(self.executor.list_groups()), 1)
    self.assertIn("additional", self.executor.list_groups())
    self.assertIsNone(self.executor.list_operations("main"))
    
    self.executor.remove_groups(["additional"])
    self.assertEqual(len(self.executor.list_groups()), 0)
    self.assertIsNone(self.executor.list_operations("main"))
    self.assertIsNone(self.executor.list_operations("additional"))
  
  def test_remove_all_groups(self):
    test_list = []
    self.executor.add(append_test, ["main", "additional"])
    self.executor.add(
      append_to_list_before, ["main", "additional"], [test_list, 3], foreach=True)
    self.executor.add(append_test, ["main", "additional"])
    
    self.executor.remove_groups("all")
    self.assertEqual(len(self.executor.list_groups()), 0)
    self.assertIsNone(self.executor.list_operations("main"))
    self.assertIsNone(self.executor.list_operations("additional"))
  
  def test_remove_groups_non_existing_group(self):
    try:
      self.executor.remove_groups(["non_existing_group"])
    except Exception:
      self.fail("removing a non-existent group should not raise exception")


class TestOperationExecutorExecuteOperations(OperationExecutorTestCase):
  
  @parameterized.parameterized.expand([
    ("default",
     append_test, [], [],
     ["test"]),
    
    ("execute_args",
     append_to_list, [], [1],
     [1]),
    
    ("add_and_execute_args",
     extend_list, [1], [2, 3],
     [1, 2, 3]),
  ])
  def test_execute_single_operation(
        self,
        test_case_name_suffix,
        operation,
        add_args,
        execute_args,
        expected_result):
    test_list = []
    
    self.executor.add(operation, args=[test_list] + add_args)
    self.executor.execute(additional_args=execute_args)
    
    self.assertEqual(test_list, expected_result)
  
  def test_execute_invalid_number_of_args(self):
    test_list = []
    self.executor.add(append_to_list, args=[test_list, 1, 2])
    
    with self.assertRaises(TypeError):
      self.executor.execute()
  
  def test_execute_additional_args_invalid_number_of_args(self):
    test_list = []
    self.executor.add(append_to_list, args=[test_list])
    
    with self.assertRaises(TypeError):
      self.executor.execute()
    
    with self.assertRaises(TypeError):
      self.executor.execute(additional_args=[1, 2])
  
  def test_execute_additional_kwargs_override_former_kwargs(self):
    test_dict = {}
    self.executor.add(update_dict, args=[test_dict], kwargs={"one": 1, "two": 2})
    self.executor.execute(additional_kwargs={"two": "two", "three": 3})
    
    self.assertDictEqual(test_dict, {"one": 1, "two": "two", "three": 3})
  
  def test_execute_additional_args_position_at_beginning(self):
    test_list = []
    self.executor.add(append_to_list, args=[1])
    self.executor.execute(additional_args=[test_list], additional_args_position=0)
    
    self.assertEqual(test_list, [1])
  
  def test_execute_additional_args_position_in_middle(self):
    test_list = []
    self.executor.add(append_to_list_multiple_args, args=[test_list, 1, 3])
    self.executor.execute(additional_args=[2], additional_args_position=2)
    
    self.assertEqual(test_list, [1, 2, 3])
  
  def test_execute_multiple_operations(self):
    test_list = []
    self.executor.add(append_test, args=[test_list])
    self.executor.add(extend_list, args=[test_list, 1])
    
    self.executor.execute()
    
    self.assertListEqual(test_list, ["test", 1])
  
  def test_execute_multiple_groups_multiple_operations(self):
    test_dict = {}
    self.executor.add(
      update_dict, ["main", "additional"], [test_dict], {"one": 1, "two": 2})
    self.executor.add(
      update_dict, ["main"], [test_dict], {"two": "two", "three": 3})
    
    self.executor.execute(["main"])
    self.assertDictEqual(test_dict, {"one": 1, "two": "two", "three": 3})
    
    self.executor.execute(["additional"])
    self.assertDictEqual(test_dict, {"one": 1, "two": 2, "three": 3})
    
    test_dict.clear()
    self.executor.execute(["main", "additional"])
    self.assertDictEqual(test_dict, {"one": 1, "two": 2, "three": 3})
    
    test_dict.clear()
    self.executor.execute(["additional", "main"])
    self.assertDictEqual(test_dict, {"one": 1, "two": "two", "three": 3})
    
  def test_execute_empty_group(self):
    try:
      self.executor.execute()
    except Exception:
      self.fail("executing no operations for the given group should not raise exception")


class TestOperationExecutorExecuteForeachOperations(OperationExecutorTestCase):
  
  @parameterized.parameterized.expand([
    ("default",
     append_to_list, append_to_list, [[1], [2]], [3],
     [1, 3, 2, 3]),
    
    ("before_operation",
     append_to_list, append_to_list_before, [[1], [2]], [3],
     [3, 1, 3, 2]),
    
    ("before_and_after_operation",
     append_to_list, append_to_list_before_and_after, [[1], [2]], [3],
     [3, 1, 3, 3, 2, 3]),
    
    ("before_and_after_operation_multiple_times",
     append_to_list, append_to_list_before_and_after_execute_twice, [[1], [2]], [3],
     [3, 1, 1, 3, 3, 2, 2, 3]),
  ])
  def test_execute_single_foreach(
        self,
        test_case_name_suffix,
        operation,
        foreach_operation,
        operations_args,
        foreach_operation_args,
        expected_result):
    test_list = []
    
    self.executor.add(operation, args=[test_list] + operations_args[0])
    self.executor.add(operation, args=[test_list] + operations_args[1])
    self.executor.add(
      foreach_operation, args=[test_list] + foreach_operation_args, foreach=True)
    
    self.executor.execute()
    
    self.assertListEqual(test_list, expected_result)
  
  @parameterized.parameterized.expand([
    ("simple",
     append_to_list, [append_to_list_before, append_to_list],
     [[1], [2]], [[3], [4]],
     [3, 1, 4, 3, 2, 4]),
    
    ("complex",
     append_to_list,
     [append_to_list_before_and_after, append_to_list_before_and_after_execute_twice],
     [[1], [2]], [[3], [4]],
     [3, 4, 1, 3, 1, 4,
      3, 4, 2, 3, 2, 4]),
    
    ("even_more_complex",
     append_to_list,
     [append_to_list_before_and_after, append_to_list_before_middle_after_execute_twice],
     [[1], [2]], [[3], [4]],
     [3, 4, 1, 3, 4, 1, 4,
      3, 4, 2, 3, 4, 2, 4]),
  ])
  def test_execute_multiple_foreachs(
        self,
        test_case_name_suffix,
        operation,
        foreach_operations,
        operations_args,
        foreach_operations_args,
        expected_result):
    test_list = []
    
    self.executor.add(operation, args=[test_list] + operations_args[0])
    self.executor.add(operation, args=[test_list] + operations_args[1])
    self.executor.add(
      foreach_operations[0], args=[test_list] + foreach_operations_args[0], foreach=True)
    self.executor.add(
      foreach_operations[1], args=[test_list] + foreach_operations_args[1], foreach=True)
    
    self.executor.execute()
    
    self.assertListEqual(test_list, expected_result)
  
  def test_execute_foreach_use_return_value_from_operation(self):
    test_list = []
    self.executor.add(append_to_list, args=[test_list, 1])
    self.executor.add(append_to_list, args=[test_list, 2])
    self.executor.add(append_to_list_again, args=[test_list], foreach=True)
    
    self.executor.execute()
    
    self.assertListEqual(test_list, [1, 1, 2, 2])
  
  def test_execute_foreach_does_nothing_in_another_executor(self):
    test_list = []
    another_executor = pgoperations.OperationExecutor()
    another_executor.add(append_to_list, args=[test_list, 1])
    another_executor.add(append_to_list, args=[test_list, 2])
    
    self.executor.add(another_executor)
    self.executor.add(append_to_list, args=[test_list, 3])
    self.executor.add(append_to_list_again, args=[test_list], foreach=True)
    
    self.executor.execute()
    
    self.assertListEqual(test_list, [1, 2, 3, 3])
  
  def test_execute_foreach_executor(self):
    test_list = []
    
    def append_to_list_before_from_executor():
      another_executor.execute()
      yield
    
    self.executor.add(append_to_list, args=[test_list, 1])
    self.executor.add(append_to_list, args=[test_list, 2])
    
    another_executor = pgoperations.OperationExecutor()
    another_executor.add(append_to_list, args=[test_list, 3])
    another_executor.add(append_to_list, args=[test_list, 4])
    
    self.executor.add(append_to_list_before_from_executor, foreach=True)
    
    self.executor.execute()
    
    self.assertListEqual(test_list, [3, 4, 1, 3, 4, 2])


class TestOperationExecutorExecuteWithExecutor(OperationExecutorTestCase):
  
  def test_execute(self):
    test_list = []
    another_executor = pgoperations.OperationExecutor()
    another_executor.add(append_to_list, args=[test_list, 1])
    another_executor.add(append_test, args=[test_list])
    
    self.executor.add(append_to_list, args=[test_list, 2])
    self.executor.add(another_executor)
    
    self.executor.execute()
    
    self.assertListEqual(test_list, [2, 1, "test"])
  
  def test_execute_after_adding_operations_to_executor(self):
    test_list = []
    another_executor = pgoperations.OperationExecutor()
    
    self.executor.add(append_to_list, args=[test_list, 2])
    self.executor.add(another_executor)
    
    another_executor.add(append_to_list, args=[test_list, 1])
    another_executor.add(append_test, args=[test_list])
    
    self.executor.execute()
    
    self.assertListEqual(test_list, [2, 1, "test"])
  
  def test_execute_multiple_executors_after_adding_operations_to_them(self):
    test_list = []
    more_executors = [pgoperations.OperationExecutor(), pgoperations.OperationExecutor()]
    
    self.executor.add(append_to_list, args=[test_list, 2])
    self.executor.add(more_executors[0])
    self.executor.add(more_executors[1])
    
    more_executors[0].add(append_to_list, args=[test_list, 1])
    more_executors[0].add(append_test, args=[test_list])
    
    more_executors[1].add(append_to_list, args=[test_list, 3])
    more_executors[1].add(append_to_list, args=[test_list, 4])
    
    self.executor.execute()
    
    self.assertListEqual(test_list, [2, 1, "test", 3, 4])
  
  def test_execute_empty_group(self):
    another_executor = pgoperations.OperationExecutor()
    try:
      self.executor.add(another_executor, ["invalid_group"])
    except Exception:
      self.fail("adding operations from an empty group from another "
                "OperationExecutor instance should not raise exception")
