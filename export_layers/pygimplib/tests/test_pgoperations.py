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
  
  @parameterized.parameterized.expand([
    ("default_group",
     None, ["default"]
     ),
    
    ("default_group_explicit_name",
     "default", ["default"]
     ),
    
    ("specific_groups",
     ["main_processing", "advanced_processing"],
     ["main_processing", "advanced_processing"]
     ),
  ])
  def test_add(self, test_case_name_suffix, groups, get_operations_groups):
    test_list = []
    
    self.executor.add(append_test, groups, args=[test_list])
    
    for get_operations_group in get_operations_groups:
      self.assertEqual(len(self.executor.get_operations(get_operations_group)), 1)
  
  def test_add_to_all_groups(self):
    test_list = []
    
    self.executor.add(
      append_test, ["main_processing", "advanced_processing"], [test_list])
    self.executor.add(append_test, "all", [test_list])
    
    self.assertEqual(len(self.executor.get_operations("main_processing")), 2)
    self.assertEqual(len(self.executor.get_operations("advanced_processing")), 2)
    self.assertFalse("default" in self.executor.get_groups())
    
    self.executor.add(append_test, args=[test_list])
    self.executor.add(append_test, "all", [test_list])
    
    self.assertEqual(len(self.executor.get_operations("main_processing")), 3)
    self.assertEqual(len(self.executor.get_operations("advanced_processing")), 3)
    self.assertEqual(len(self.executor.get_operations()), 2)
  
  def test_add_return_unique_ids(self):
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
  
  def test_add_return_same_id_for_multiple_groups(self):
    test_list = []
    operation_id = self.executor.add(
      append_to_list, ["main_processing", "additional_processing"], [test_list, 2])
    
    self.assertTrue(self.executor.has_operation(operation_id, "all"))
    self.assertTrue(self.executor.has_operation(operation_id, ["main_processing"]))
    self.assertTrue(self.executor.has_operation(operation_id, ["additional_processing"]))
  
  def test_add_to_groups(self):
    test_list = []
    operation_id = self.executor.add(append_to_list, ["main_processing"], [test_list, 2])
    
    self.executor.add_to_groups(operation_id, ["additional_processing"])
    self.assertTrue(self.executor.has_operation(operation_id, ["main_processing"]))
    self.assertTrue(self.executor.has_operation(operation_id, ["additional_processing"]))
    
    self.executor.add_to_groups(operation_id, ["main_processing"])
    self.assertEqual(len(self.executor.get_operations("main_processing")), 1)
    self.assertEqual(
      len(self.executor.get_operations("main_processing", foreach=True)), 0)
    
    foreach_operation_id = self.executor.add(
      append_to_list_before, ["main_processing"], [test_list, 2], foreach=True)
    
    self.executor.add_to_groups(foreach_operation_id, ["additional_processing"])
    self.assertTrue(self.executor.has_operation(
      foreach_operation_id, ["main_processing"]))
    self.assertTrue(self.executor.has_operation(
      foreach_operation_id, ["additional_processing"]))
    
    self.executor.add_to_groups(foreach_operation_id, ["main_processing"])
    self.assertEqual(len(self.executor.get_operations("main_processing")), 1)
    self.assertEqual(
      len(self.executor.get_operations("main_processing", foreach=True)), 1)
    
    additional_executor = pgoperations.OperationExecutor()
    executor_id = self.executor.add(additional_executor, ["main_processing"])
    
    self.executor.add_to_groups(executor_id, ["additional_processing"])
    self.assertTrue(self.executor.has_operation(executor_id, ["main_processing"]))
    self.assertTrue(self.executor.has_operation(executor_id, ["additional_processing"]))
    
    self.executor.add_to_groups(executor_id, ["main_processing"])
    self.assertEqual(len(self.executor.get_operations("main_processing")), 2)
    self.assertEqual(
      len(self.executor.get_operations("main_processing", foreach=True)), 1)
  
  def test_add_to_groups_same_group(self):
    test_list = []
    operation_id = self.executor.add(append_to_list, ["main_processing"], [test_list, 2])
    
    self.executor.add_to_groups(operation_id, ["main_processing"])
    self.assertEqual(len(self.executor.get_operations("main_processing")), 1)
  
  def test_has_operation(self):
    operation_id = self.executor.add(append_to_list)
    self.assertTrue(self.executor.has_operation(operation_id))
  
  def test_has_matching_operation(self):
    test_list = []
    
    self.executor.add(append_test, args=[test_list])
    self.assertTrue(self.executor.has_matching_operation(append_test))
    
    additional_executor = pgoperations.OperationExecutor()
    self.executor.add(additional_executor)
    self.assertTrue(self.executor.has_matching_operation(additional_executor))
    
    self.executor.add(
      append_to_list_again, args=[test_list], foreach=True)
    self.assertTrue(
      self.executor.has_matching_operation(append_to_list_again, foreach=True))
  
  def test_get_operations_non_existing_group(self):
    self.assertIsNone(self.executor.get_operations("non_existing_group"))
  
  def test_get_operations(self):
    test_list = []
    self.executor.add(append_to_list, args=[test_list, 1])
    self.executor.add(append_to_list, args=[test_list, 2])
    
    self.assertListEqual(
      self.executor.get_operations(),
      [(append_to_list, [test_list, 1], {}), (append_to_list, [test_list, 2], {})])
    
    self.assertEqual(self.executor.get_operations(foreach=True), [])
  
  def test_get_foreach_operations(self):
    test_list = []
    self.executor.add(append_to_list_before, args=[test_list, 1], foreach=True)
    self.executor.add(append_to_list_before, args=[test_list, 2], foreach=True)
    
    self.assertListEqual(
      self.executor.get_operations(foreach=True),
      [(append_to_list_before, [test_list, 1], {}),
       (append_to_list_before, [test_list, 2], {})])
    
    self.assertEqual(self.executor.get_operations(), [])
  
  def test_get_foreach_operations_non_existing_group(self):
    self.assertIsNone(self.executor.get_operations("non_existing_group", foreach=True))
  
  def test_get_groups(self):
    test_list = []
    self.executor.add(append_to_list, ["main_processing"], [test_list, 2])
    self.executor.add(append_to_list, ["additional_processing"], [test_list, 3])
    
    self.assertEqual(len(self.executor.get_groups()), 2)
    self.assertIn("main_processing", self.executor.get_groups())
    self.assertIn("additional_processing", self.executor.get_groups())
  
  def test_get_groups_without_empty_groups(self):
    test_list = []
    operation_ids = []
    
    operation_ids.append(
      self.executor.add(
        append_to_list, ["main_processing", "additional_processing"], [test_list, 2]))
    
    operation_ids.append(
      self.executor.add(
        append_to_list_before, ["main_processing", "additional_processing"],
        [test_list, 2], foreach=True))
    
    additional_executor = pgoperations.OperationExecutor()
    operation_ids.append(self.executor.add(additional_executor, ["main_processing"]))
    
    self.executor.remove(operation_ids[2], ["main_processing"])
    self.assertEqual(len(self.executor.get_groups(include_empty_groups=False)), 2)
    
    self.executor.remove(operation_ids[1], ["main_processing"])
    self.assertEqual(len(self.executor.get_groups(include_empty_groups=False)), 2)
    
    self.executor.remove(operation_ids[0], ["main_processing"])
    non_empty_groups = self.executor.get_groups(include_empty_groups=False)
    self.assertEqual(len(non_empty_groups), 1)
    self.assertNotIn("main_processing", non_empty_groups)
    self.assertIn("additional_processing", non_empty_groups)
    
    self.executor.remove(operation_ids[1], ["additional_processing"])
    non_empty_groups = self.executor.get_groups(include_empty_groups=False)
    self.assertEqual(len(non_empty_groups), 1)
    self.assertNotIn("main_processing", non_empty_groups)
    self.assertIn("additional_processing", non_empty_groups)
    
    self.executor.remove(operation_ids[0], ["additional_processing"])
    self.assertEqual(len(self.executor.get_groups(include_empty_groups=False)), 0)
  
  def test_get_operation(self):
    test_list = []
    operation_ids = []
    operation_ids.append(
      self.executor.add(
        append_to_list, ["main_processing"], [test_list, 2]))
    operation_ids.append(
      self.executor.add(
        append_to_list, ["additional_processing"], [test_list, 3]))
    operation_ids.append(
      self.executor.add(
        append_to_list_before, ["additional_processing"], [test_list, 4], foreach=True))
    
    additional_executor = pgoperations.OperationExecutor()
    operation_ids.append(
      self.executor.add(additional_executor, ["main_processing"]))
    
    self.assertEqual(
      self.executor.get_operation(
        operation_ids[0]), (append_to_list, [test_list, 2], {}))
    self.assertEqual(
      self.executor.get_operation(
        operation_ids[1]), (append_to_list, [test_list, 3], {}))
    self.assertEqual(
      self.executor.get_operation(
        operation_ids[2]), (append_to_list_before, [test_list, 4], {}))
    
    self.assertEqual(self.executor.get_operation(operation_ids[3]), additional_executor)
  
  def test_get_operation_invalid_id(self):
    self.assertIsNone(self.executor.get_operation(-1))
  
  def test_get_operation_position(self):
    test_list = []
    operation_ids = []
    
    operation_ids.append(self.executor.add(append_to_list, args=[test_list, 2]))
    operation_ids.append(self.executor.add(append_to_list, args=[test_list, 3]))
    operation_ids.append(self.executor.add(append_to_list, args=[test_list, 4]))
    
    self.assertEqual(self.executor.get_operation_position(operation_ids[0]), 0)
    self.assertEqual(self.executor.get_operation_position(operation_ids[1]), 1)
    self.assertEqual(self.executor.get_operation_position(operation_ids[2]), 2)
  
  def test_get_operation_position_invalid_id(self):
    self.executor.add(append_test)
    with self.assertRaises(ValueError):
      self.executor.get_operation_position(-1)
  
  def test_get_operation_position_operation_not_in_group(self):
    operation_id = self.executor.add(append_test, ["main_processing"])
    with self.assertRaises(ValueError):
      self.executor.get_operation_position(operation_id, "additional_processing")
  
  def test_find_matching_operations(self):
    test_list = []
    operation_ids = []
    
    operation_ids.append(
      self.executor.add(append_to_list, args=[test_list, 2]))
    operation_ids.append(
      self.executor.add(append_to_list, args=[test_list, 3]))
    operation_ids.append(
      self.executor.add(append_to_list, ["additional_processing"], [test_list, 3]))
    
    operation_ids.append(
      self.executor.add(
        append_to_list_before, args=[test_list, 3], foreach=True))
    
    additional_executor = pgoperations.OperationExecutor()
    operation_ids.append(self.executor.add(additional_executor))
    
    self.assertEqual(
      self.executor.find_matching_operations(append_to_list),
      [operation_ids[0], operation_ids[1]])
    self.assertEqual(
      self.executor.find_matching_operations(append_to_list, foreach=True), [])
    
    self.assertEqual(
      self.executor.find_matching_operations(append_to_list_before), [])
    self.assertEqual(
      self.executor.find_matching_operations(append_to_list_before, foreach=True),
      [operation_ids[3]])
    
    self.assertEqual(
      self.executor.find_matching_operations(additional_executor),
      [operation_ids[4]])
    self.assertEqual(
      self.executor.find_matching_operations(additional_executor, foreach=True), [])
  
  def test_find_matching_operations_non_existing_group(self):
    operation_id = self.executor.add(append_test)
    self.assertEqual(
      self.executor.find_matching_operations(append_test, ["non_existing_group"]), [])
    
    self.assertEqual(
      self.executor.find_matching_operations(
        append_test, ["default", "non_existing_group"]),
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
    
    self.assertEqual(len(self.executor.get_operations()), 4)
    self.assertEqual(self.executor.get_operation_position(operation_ids[0]), 3)
    self.assertEqual(self.executor.get_operation_position(operation_ids[1]), 2)
    self.assertEqual(self.executor.get_operation_position(operation_ids[2]), 1)
    self.assertEqual(self.executor.get_operation_position(operation_ids[3]), 0)
    
    self.executor.reorder(operation_ids[2], 5)
    self.assertEqual(self.executor.get_operation_position(operation_ids[2]), 3)
    
    self.executor.reorder(operation_ids[3], -1)
    self.executor.reorder(operation_ids[1], -3)
    self.executor.reorder(operation_ids[0], -4)
    
    self.assertEqual(len(self.executor.get_operations()), 4)
    self.assertEqual(self.executor.get_operation_position(operation_ids[0]), 0)
    self.assertEqual(self.executor.get_operation_position(operation_ids[1]), 1)
    self.assertEqual(self.executor.get_operation_position(operation_ids[2]), 2)
    self.assertEqual(self.executor.get_operation_position(operation_ids[3]), 3)
  
  def test_reorder_invalid_id(self):
    with self.assertRaises(ValueError):
      self.executor.reorder(-1, 0)
  
  def test_reorder_non_existing_group(self):
    operation_id = self.executor.add(append_test)
    with self.assertRaises(ValueError):
      self.executor.reorder(operation_id, 0, "non_existing_group")
  
  def test_reorder_operation_not_in_group(self):
    operation_id = self.executor.add(append_test, ["main_processing"])
    self.executor.add(append_test, ["additional_processing"])
    with self.assertRaises(ValueError):
      self.executor.reorder(operation_id, 0, "additional_processing")
  
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
    self.assertFalse(self.executor.has_matching_operation(append_to_list))
    
    self.executor.remove(operation_ids[1])
    self.assertFalse(self.executor.has_operation(operation_ids[1]))
    self.assertFalse(self.executor.has_matching_operation(append_to_list_before))
    
    self.executor.remove(operation_ids[2])
    self.assertFalse(self.executor.has_operation(operation_ids[2]))
    self.assertFalse(self.executor.has_matching_operation(additional_executor))
  
  def test_remove_multiple_operations(self):
    test_list = []
    operation_ids = []
    
    operation_ids.append(
      self.executor.add(append_to_list, args=[test_list, 2]))
    operation_ids.append(
      self.executor.add(append_to_list, args=[test_list, 3]))
    
    self.executor.remove(operation_ids[0])
    self.assertFalse(self.executor.has_operation(operation_ids[0]))
    self.assertTrue(self.executor.has_matching_operation(append_to_list))
    
    self.executor.remove(operation_ids[1])
    self.assertFalse(self.executor.has_operation(operation_ids[1]))
    self.assertFalse(self.executor.has_matching_operation(append_to_list))
    
    operation_ids.append(
      self.executor.add(
        append_to_list_before, args=[test_list, 4], foreach=True))
    operation_ids.append(
      self.executor.add(
        append_to_list_before, args=[test_list, 5], foreach=True))
    
    self.executor.remove(operation_ids[2])
    self.assertFalse(self.executor.has_operation(operation_ids[2]))
    self.assertTrue(
      self.executor.has_matching_operation(append_to_list_before, foreach=True))
    
    self.executor.remove(operation_ids[3])
    self.assertFalse(self.executor.has_operation(operation_ids[3]))
    self.assertFalse(
      self.executor.has_matching_operation(append_to_list_before, foreach=True))
    
    additional_executor = pgoperations.OperationExecutor()
    operation_ids.append(self.executor.add(additional_executor))
    operation_ids.append(self.executor.add(additional_executor))
    
    self.executor.remove(operation_ids[4])
    self.assertFalse(self.executor.has_operation(operation_ids[4]))
    self.assertTrue(self.executor.has_matching_operation(additional_executor))
    
    self.executor.remove(operation_ids[5])
    self.assertFalse(self.executor.has_operation(operation_ids[5]))
    self.assertFalse(self.executor.has_matching_operation(additional_executor))
  
  def test_remove_from_all_groups_operation_only_in_one_group(self):
    test_list = []
    
    operation_id = self.executor.add(
      append_to_list, ["main_processing"], [test_list, 2])
    self.executor.add(append_to_list, ["additional_processing"], [test_list, 3])
    
    self.executor.remove(operation_id, "all")
    self.assertFalse(self.executor.has_operation(operation_id, ["main_processing"]))
    self.assertFalse(self.executor.has_operation(operation_id, ["additional_processing"]))
  
  def test_remove_in_one_group_keep_in_others(self):
    operation_id = self.executor.add(
      append_test, ["main_processing", "additional_processing"])
    
    self.executor.remove(operation_id, ["main_processing"])
    self.assertFalse(self.executor.has_operation(operation_id, ["main_processing"]))
    self.assertTrue(self.executor.has_operation(operation_id, ["additional_processing"]))
  
  def test_remove_if_invalid_id(self):
    with self.assertRaises(ValueError):
      self.executor.remove(-1)
  
  def test_remove_non_existing_group(self):
    operation_id = self.executor.add(append_test, ["main_processing"])
    with self.assertRaises(ValueError):
      self.executor.remove(operation_id, ["additional_processing"])
  
  def test_remove_multiple_groups_at_once(self):
    test_list = []
    operation_id = self.executor.add(
      append_to_list, ["main_processing", "additional_processing"], [test_list, 2])
    
    self.executor.remove(operation_id, "all")
    self.assertFalse(self.executor.has_operation(operation_id))
    self.assertFalse(
      self.executor.has_matching_operation(append_to_list, ["main_processing"]))
    self.assertFalse(
      self.executor.has_matching_operation(append_to_list, ["additional_processing"]))
  
  def test_remove_groups(self):
    test_list = []
    self.executor.add(append_test, ["main_processing", "additional_processing"])
    self.executor.add(
      append_to_list_before,
      ["main_processing", "additional_processing"], [test_list, 3], foreach=True)
    self.executor.add(append_test, ["main_processing", "additional_processing"])
    
    self.executor.remove_groups(["main_processing"])
    self.assertEqual(len(self.executor.get_groups()), 1)
    self.assertIn("additional_processing", self.executor.get_groups())
    self.assertIsNone(self.executor.get_operations("main_processing"))
    
    self.executor.remove_groups(["additional_processing"])
    self.assertEqual(len(self.executor.get_groups()), 0)
    self.assertIsNone(self.executor.get_operations("main_processing"))
    self.assertIsNone(self.executor.get_operations("additional_processing"))
  
  def test_remove_all_groups(self):
    test_list = []
    self.executor.add(append_test, ["main_processing", "additional_processing"])
    self.executor.add(
      append_to_list_before,
      ["main_processing", "additional_processing"], [test_list, 3], foreach=True)
    self.executor.add(append_test, ["main_processing", "additional_processing"])
    
    self.executor.remove_groups("all")
    self.assertEqual(len(self.executor.get_groups()), 0)
    self.assertIsNone(self.executor.get_operations("main_processing"))
    self.assertIsNone(self.executor.get_operations("additional_processing"))
  
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
        operation, add_args, execute_args,
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
    self.executor.add(
      update_dict, args=[test_dict], kwargs={"one": 1, "two": 2})
    self.executor.execute(additional_kwargs={"two": "two", "three": 3})
    
    self.assertDictEqual(test_dict, {"one": 1, "two": "two", "three": 3})

  def test_execute_multiple_operations(self):
    test_list = []
    self.executor.add(append_test, args=[test_list])
    self.executor.add(extend_list, args=[test_list, 1])
    
    self.executor.execute()
    
    self.assertListEqual(test_list, ["test", 1])
  
  def test_execute_multiple_groups_multiple_operations(self):
    test_dict = {}
    self.executor.add(
      update_dict, ["main_processing", "advanced_processing"],
      [test_dict], {"one": 1, "two": 2})
    self.executor.add(
      update_dict, ["main_processing"], [test_dict], {"two": "two", "three": 3})
    
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
        operation, foreach_operation, operations_args, foreach_operation_args,
        expected_result):
    test_list = []
    
    self.executor.add(
      operation, args=[test_list] + operations_args[0])
    self.executor.add(
      operation, args=[test_list] + operations_args[1])
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
        operation, foreach_operations, operations_args, foreach_operations_args,
        expected_result):
    test_list = []
    
    self.executor.add(
      operation, args=[test_list] + operations_args[0])
    self.executor.add(
      operation, args=[test_list] + operations_args[1])
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
