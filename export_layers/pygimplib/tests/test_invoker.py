# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import unittest

import parameterized

from .. import invoker as pginvoker


def append_test(list_):
  list_.append('test')


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


def append_to_list_via_generator(list_, arg):
  list_.append(1)
  
  while True:
    (list_, arg), unused_ = yield
    list_.append(arg)


def append_to_list_via_generator_finite(list_, arg):
  list_.append(1)
  
  (list_, arg), unused_ = yield
  list_.append(arg)


def append_to_list_before(list_, arg):
  list_.append(arg)
  yield


def append_to_list_before_and_after(list_, arg):
  list_.append(arg)
  yield
  list_.append(arg)


def append_to_list_before_and_after_invoke_twice(list_, arg):
  list_.append(arg)
  yield
  yield
  list_.append(arg)

def append_to_list_before_middle_after_invoke_twice(list_, arg):
  list_.append(arg)
  yield
  list_.append(arg)
  yield
  list_.append(arg)


def append_to_list_again(list_):
  arg = yield
  list_.append(arg)


class InvokerTestCase(unittest.TestCase):
  
  def setUp(self):
    self.invoker = pginvoker.Invoker()


class TestInvoker(InvokerTestCase):
  
  @parameterized.parameterized.expand([
    ('default_group',
     None, ['default']
     ),
    
    ('default_group_explicit_name',
     'default', ['default']
     ),
    
    ('specific_groups',
     ['main', 'additional'],
     ['main', 'additional']
     ),
  ])
  def test_add(self, test_case_name_suffix, groups, list_actions_groups):
    test_list = []
    
    self.invoker.add(append_test, groups, args=[test_list])
    
    for list_actions_group in list_actions_groups:
      self.assertEqual(len(self.invoker.list_actions(list_actions_group)), 1)
  
  def test_add_to_all_groups(self):
    test_list = []
    
    self.invoker.add(append_test, ['main', 'additional'], [test_list])
    self.invoker.add(append_test, 'all', [test_list])
    
    self.assertEqual(len(self.invoker.list_actions('main')), 2)
    self.assertEqual(len(self.invoker.list_actions('additional')), 2)
    self.assertFalse('default' in self.invoker.list_groups())
    
    self.invoker.add(append_test, args=[test_list])
    self.invoker.add(append_test, 'all', [test_list])
    
    self.assertEqual(len(self.invoker.list_actions('main')), 3)
    self.assertEqual(len(self.invoker.list_actions('additional')), 3)
    self.assertEqual(len(self.invoker.list_actions()), 2)
  
  def test_add_return_unique_ids_within_same_invoker(self):
    test_list = []
    action_ids = []
    
    action_ids.append(self.invoker.add(append_to_list, args=[test_list, 2]))
    action_ids.append(self.invoker.add(append_to_list, args=[test_list, 3]))
    action_ids.append(self.invoker.add(append_to_list, args=[test_list, 2]))
    action_ids.append(
      self.invoker.add(append_to_list_before, args=[test_list, 3], foreach=True))
    action_ids.append(
      self.invoker.add(append_to_list_before, args=[test_list, 3], foreach=True))
    
    additional_invoker = pginvoker.Invoker()
    action_ids.append(self.invoker.add(additional_invoker))
    action_ids.append(self.invoker.add(additional_invoker))
    
    self.assertEqual(len(action_ids), len(set(action_ids)))
  
  def test_add_return_unique_ids_across_multiple_invokers(self):
    action_id = self.invoker.add(append_test)
    
    additional_invoker = pginvoker.Invoker()
    additional_action_id = additional_invoker.add(append_test)
    
    self.assertNotEqual(action_id, additional_action_id)
  
  def test_add_return_same_id_for_multiple_groups(self):
    test_list = []
    action_id = self.invoker.add(
      append_to_list, ['main', 'additional'], [test_list, 2])
    
    self.assertTrue(self.invoker.has_action(action_id, 'all'))
    self.assertTrue(self.invoker.has_action(action_id, ['main']))
    self.assertTrue(self.invoker.has_action(action_id, ['additional']))
  
  def test_add_to_groups(self):
    test_list = []
    action_id = self.invoker.add(append_to_list, ['main'], [test_list, 2])
    
    self.invoker.add_to_groups(action_id, ['additional'])
    self.assertTrue(self.invoker.has_action(action_id, ['main']))
    self.assertTrue(self.invoker.has_action(action_id, ['additional']))
    
    self.invoker.add_to_groups(action_id, ['main'])
    self.assertEqual(len(self.invoker.list_actions('main')), 1)
    self.assertEqual(len(self.invoker.list_actions('main', foreach=True)), 0)
    
    foreach_action_id = self.invoker.add(
      append_to_list_before, ['main'], [test_list, 2], foreach=True)
    
    self.invoker.add_to_groups(foreach_action_id, ['additional'])
    self.assertTrue(self.invoker.has_action(foreach_action_id, ['main']))
    self.assertTrue(self.invoker.has_action(foreach_action_id, ['additional']))
    
    self.invoker.add_to_groups(foreach_action_id, ['main'])
    self.assertEqual(len(self.invoker.list_actions('main')), 1)
    self.assertEqual(len(self.invoker.list_actions('main', foreach=True)), 1)
    
    additional_invoker = pginvoker.Invoker()
    invoker_id = self.invoker.add(additional_invoker, ['main'])
    
    self.invoker.add_to_groups(invoker_id, ['additional'])
    self.assertTrue(self.invoker.has_action(invoker_id, ['main']))
    self.assertTrue(self.invoker.has_action(invoker_id, ['additional']))
    
    self.invoker.add_to_groups(invoker_id, ['main'])
    self.assertEqual(len(self.invoker.list_actions('main')), 2)
    self.assertEqual(len(self.invoker.list_actions('main', foreach=True)), 1)
  
  def test_add_to_groups_same_group(self):
    test_list = []
    action_id = self.invoker.add(append_to_list, ['main'], [test_list, 2])
    
    self.invoker.add_to_groups(action_id, ['main'])
    self.assertEqual(len(self.invoker.list_actions('main')), 1)
  
  def test_add_ignore_if_exists(self):
    test_list = []
    self.invoker.add(append_to_list, args=[test_list, 1], ignore_if_exists=True)
    self.assertEqual(len(self.invoker.list_actions()), 1)
    
    action_id = self.invoker.add(
      append_to_list, args=[test_list, 2], ignore_if_exists=True)
    self.assertEqual(len(self.invoker.list_actions()), 1)
    self.assertIsNone(action_id)
  
  def test_add_different_order(self):
    test_list = []
    self.invoker.add(append_to_list, args=[test_list, 1])
    self.invoker.add(append_to_list, args=[test_list, 2], position=0)
    
    self.assertListEqual(
      self.invoker.list_actions(),
      [(append_to_list, [test_list, 2], {}), (append_to_list, [test_list, 1], {})])
  
  def test_add_foreach_action_different_order(self):
    test_list = []
    self.invoker.add(append_to_list_before, args=[test_list, 1], foreach=True)
    self.invoker.add(append_to_list_before, args=[test_list, 2], foreach=True, position=0)
    
    self.assertListEqual(
      self.invoker.list_actions(foreach=True),
      [(append_to_list_before, [test_list, 2], {}),
       (append_to_list_before, [test_list, 1], {})])
  
  def test_add_invoker_different_order(self):
    additional_invoker = pginvoker.Invoker()
    additional_invoker_2 = pginvoker.Invoker()
    
    self.invoker.add(additional_invoker)
    self.invoker.add(additional_invoker_2, position=0)
    
    self.assertListEqual(
      self.invoker.list_actions(),
      [additional_invoker_2, additional_invoker])
  
  def test_has_action(self):
    action_id = self.invoker.add(append_to_list)
    self.assertTrue(self.invoker.has_action(action_id))
  
  def test_contains(self):
    test_list = []
    
    self.invoker.add(append_test, args=[test_list])
    self.assertTrue(self.invoker.contains(append_test))
    
    additional_invoker = pginvoker.Invoker()
    self.invoker.add(additional_invoker)
    self.assertTrue(self.invoker.contains(additional_invoker))
    
    self.invoker.add(append_to_list_again, args=[test_list], foreach=True)
    self.assertTrue(self.invoker.contains(append_to_list_again, foreach=True))
  
  def test_list_actions_non_existing_group(self):
    self.assertIsNone(self.invoker.list_actions('non_existing_group'))
  
  def test_list_actions(self):
    test_list = []
    self.invoker.add(append_to_list, args=[test_list, 1])
    self.invoker.add(append_to_list, args=[test_list, 2])
    
    self.assertListEqual(
      self.invoker.list_actions(),
      [(append_to_list, [test_list, 1], {}), (append_to_list, [test_list, 2], {})])
    
    self.assertEqual(self.invoker.list_actions(foreach=True), [])
  
  def test_get_foreach_actions(self):
    test_list = []
    self.invoker.add(append_to_list_before, args=[test_list, 1], foreach=True)
    self.invoker.add(append_to_list_before, args=[test_list, 2], foreach=True)
    
    self.assertListEqual(
      self.invoker.list_actions(foreach=True),
      [(append_to_list_before, [test_list, 1], {}),
       (append_to_list_before, [test_list, 2], {})])
    
    self.assertEqual(self.invoker.list_actions(), [])
  
  def test_get_foreach_actions_non_existing_group(self):
    self.assertIsNone(self.invoker.list_actions('non_existing_group', foreach=True))
  
  def test_list_groups(self):
    test_list = []
    self.invoker.add(append_to_list, ['main'], [test_list, 2])
    self.invoker.add(append_to_list, ['additional'], [test_list, 3])
    
    self.assertEqual(len(self.invoker.list_groups()), 2)
    self.assertIn('main', self.invoker.list_groups())
    self.assertIn('additional', self.invoker.list_groups())
  
  def test_list_groups_without_empty_groups(self):
    test_list = []
    action_ids = []
    
    action_ids.append(
      self.invoker.add(append_to_list, ['main', 'additional'], [test_list, 2]))
    
    action_ids.append(
      self.invoker.add(
        append_to_list_before, ['main', 'additional'], [test_list, 2], foreach=True))
    
    additional_invoker = pginvoker.Invoker()
    action_ids.append(self.invoker.add(additional_invoker, ['main']))
    
    self.invoker.remove(action_ids[2], ['main'])
    self.assertEqual(len(self.invoker.list_groups(include_empty_groups=False)), 2)
    
    self.invoker.remove(action_ids[1], ['main'])
    self.assertEqual(len(self.invoker.list_groups(include_empty_groups=False)), 2)
    
    self.invoker.remove(action_ids[0], ['main'])
    non_empty_groups = self.invoker.list_groups(include_empty_groups=False)
    self.assertEqual(len(non_empty_groups), 1)
    self.assertNotIn('main', non_empty_groups)
    self.assertIn('additional', non_empty_groups)
    
    self.invoker.remove(action_ids[1], ['additional'])
    non_empty_groups = self.invoker.list_groups(include_empty_groups=False)
    self.assertEqual(len(non_empty_groups), 1)
    self.assertNotIn('main', non_empty_groups)
    self.assertIn('additional', non_empty_groups)
    
    self.invoker.remove(action_ids[0], ['additional'])
    self.assertEqual(len(self.invoker.list_groups(include_empty_groups=False)), 0)
  
  def test_get_action(self):
    test_list = []
    action_ids = []
    action_ids.append(
      self.invoker.add(append_to_list, ['main'], [test_list, 2]))
    action_ids.append(
      self.invoker.add(append_to_list, ['additional'], [test_list, 3]))
    action_ids.append(
      self.invoker.add(
        append_to_list_before, ['additional'], [test_list, 4], foreach=True))
    
    additional_invoker = pginvoker.Invoker()
    action_ids.append(self.invoker.add(additional_invoker, ['main']))
    
    self.assertEqual(
      self.invoker.get_action(action_ids[0]),
      (append_to_list, [test_list, 2], {}))
    self.assertEqual(
      self.invoker.get_action(action_ids[1]),
      (append_to_list, [test_list, 3], {}))
    self.assertEqual(
      self.invoker.get_action(action_ids[2]),
      (append_to_list_before, [test_list, 4], {}))
    
    self.assertEqual(self.invoker.get_action(action_ids[3]), additional_invoker)
  
  def test_get_action_invalid_id(self):
    self.assertIsNone(self.invoker.get_action(-1))
  
  def test_get_position(self):
    test_list = []
    action_ids = []
    
    action_ids.append(self.invoker.add(append_to_list, args=[test_list, 2]))
    action_ids.append(self.invoker.add(append_to_list, args=[test_list, 3]))
    action_ids.append(self.invoker.add(append_to_list, args=[test_list, 4]))
    
    self.assertEqual(self.invoker.get_position(action_ids[0]), 0)
    self.assertEqual(self.invoker.get_position(action_ids[1]), 1)
    self.assertEqual(self.invoker.get_position(action_ids[2]), 2)
  
  def test_get_position_invalid_id(self):
    self.invoker.add(append_test)
    with self.assertRaises(ValueError):
      self.invoker.get_position(-1)
  
  def test_get_position_action_not_in_group(self):
    action_id = self.invoker.add(append_test, ['main'])
    with self.assertRaises(ValueError):
      self.invoker.get_position(action_id, 'additional')
  
  def test_find(self):
    test_list = []
    action_ids = []
    
    action_ids.append(
      self.invoker.add(append_to_list, args=[test_list, 2]))
    action_ids.append(
      self.invoker.add(append_to_list, args=[test_list, 3]))
    action_ids.append(
      self.invoker.add(append_to_list, ['additional'], [test_list, 3]))
    
    action_ids.append(
      self.invoker.add(append_to_list_before, args=[test_list, 3], foreach=True))
    
    additional_invoker = pginvoker.Invoker()
    action_ids.append(self.invoker.add(additional_invoker))
    
    self.assertEqual(
      self.invoker.find(append_to_list),
      [action_ids[0], action_ids[1]])
    self.assertEqual(
      self.invoker.find(append_to_list, foreach=True), [])
    
    self.assertEqual(
      self.invoker.find(append_to_list_before), [])
    self.assertEqual(
      self.invoker.find(append_to_list_before, foreach=True),
      [action_ids[3]])
    
    self.assertEqual(
      self.invoker.find(additional_invoker),
      [action_ids[4]])
    self.assertEqual(
      self.invoker.find(additional_invoker, foreach=True), [])
  
  def test_find_non_existing_group(self):
    action_id = self.invoker.add(append_test)
    self.assertEqual(
      self.invoker.find(append_test, ['non_existing_group']),
      [])
    
    self.assertEqual(
      self.invoker.find(append_test, ['default', 'non_existing_group']),
      [action_id])
  
  def test_reorder(self):
    action_ids = []
    action_ids.append(self.invoker.add(append_test))
    action_ids.append(self.invoker.add(append_test))
    action_ids.append(self.invoker.add(append_test))
    action_ids.append(self.invoker.add(append_test))
    
    self.invoker.reorder(action_ids[3], 0)
    self.invoker.reorder(action_ids[2], 1)
    self.invoker.reorder(action_ids[1], 2)
    
    self.assertEqual(len(self.invoker.list_actions()), 4)
    self.assertEqual(self.invoker.get_position(action_ids[0]), 3)
    self.assertEqual(self.invoker.get_position(action_ids[1]), 2)
    self.assertEqual(self.invoker.get_position(action_ids[2]), 1)
    self.assertEqual(self.invoker.get_position(action_ids[3]), 0)
    
    self.invoker.reorder(action_ids[2], 5)
    self.assertEqual(self.invoker.get_position(action_ids[2]), 3)
    
    self.invoker.reorder(action_ids[3], -1)
    self.invoker.reorder(action_ids[1], -3)
    self.invoker.reorder(action_ids[0], -4)
    
    self.assertEqual(len(self.invoker.list_actions()), 4)
    self.assertEqual(self.invoker.get_position(action_ids[0]), 0)
    self.assertEqual(self.invoker.get_position(action_ids[1]), 1)
    self.assertEqual(self.invoker.get_position(action_ids[2]), 2)
    self.assertEqual(self.invoker.get_position(action_ids[3]), 3)
  
  def test_reorder_invalid_id(self):
    with self.assertRaises(ValueError):
      self.invoker.reorder(-1, 0)
  
  def test_reorder_non_existing_group(self):
    action_id = self.invoker.add(append_test)
    with self.assertRaises(ValueError):
      self.invoker.reorder(action_id, 0, 'non_existing_group')
  
  def test_reorder_action_not_in_group(self):
    action_id = self.invoker.add(append_test, ['main'])
    self.invoker.add(append_test, ['additional'])
    with self.assertRaises(ValueError):
      self.invoker.reorder(action_id, 0, 'additional')
  
  def test_remove(self):
    test_list = []
    action_ids = []
    
    action_ids.append(self.invoker.add(append_to_list, args=[test_list, 2]))
    action_ids.append(
      self.invoker.add(append_to_list_before, args=[test_list, 3], foreach=True))
    
    additional_invoker = pginvoker.Invoker()
    action_ids.append(self.invoker.add(additional_invoker))
    
    self.invoker.remove(action_ids[0])
    self.assertFalse(self.invoker.has_action(action_ids[0]))
    self.assertFalse(self.invoker.contains(append_to_list))
    
    self.invoker.remove(action_ids[1])
    self.assertFalse(self.invoker.has_action(action_ids[1]))
    self.assertFalse(self.invoker.contains(append_to_list_before))
    
    self.invoker.remove(action_ids[2])
    self.assertFalse(self.invoker.has_action(action_ids[2]))
    self.assertFalse(self.invoker.contains(additional_invoker))
  
  def test_remove_multiple_actions(self):
    test_list = []
    action_ids = []
    
    action_ids.append(self.invoker.add(append_to_list, args=[test_list, 2]))
    action_ids.append(self.invoker.add(append_to_list, args=[test_list, 3]))
    
    self.invoker.remove(action_ids[0])
    self.assertFalse(self.invoker.has_action(action_ids[0]))
    self.assertTrue(self.invoker.contains(append_to_list))
    
    self.invoker.remove(action_ids[1])
    self.assertFalse(self.invoker.has_action(action_ids[1]))
    self.assertFalse(self.invoker.contains(append_to_list))
    
    action_ids.append(
      self.invoker.add(append_to_list_before, args=[test_list, 4], foreach=True))
    action_ids.append(
      self.invoker.add(append_to_list_before, args=[test_list, 5], foreach=True))
    
    self.invoker.remove(action_ids[2])
    self.assertFalse(self.invoker.has_action(action_ids[2]))
    self.assertTrue(self.invoker.contains(append_to_list_before, foreach=True))
    
    self.invoker.remove(action_ids[3])
    self.assertFalse(self.invoker.has_action(action_ids[3]))
    self.assertFalse(self.invoker.contains(append_to_list_before, foreach=True))
    
    additional_invoker = pginvoker.Invoker()
    action_ids.append(self.invoker.add(additional_invoker))
    action_ids.append(self.invoker.add(additional_invoker))
    
    self.invoker.remove(action_ids[4])
    self.assertFalse(self.invoker.has_action(action_ids[4]))
    self.assertTrue(self.invoker.contains(additional_invoker))
    
    self.invoker.remove(action_ids[5])
    self.assertFalse(self.invoker.has_action(action_ids[5]))
    self.assertFalse(self.invoker.contains(additional_invoker))
  
  def test_remove_from_all_groups_action_only_in_one_group(self):
    test_list = []
    
    action_id = self.invoker.add(append_to_list, ['main'], [test_list, 2])
    self.invoker.add(append_to_list, ['additional'], [test_list, 3])
    
    self.invoker.remove(action_id, 'all')
    self.assertFalse(self.invoker.has_action(action_id, ['main']))
    self.assertFalse(self.invoker.has_action(action_id, ['additional']))
  
  def test_remove_in_one_group_keep_in_others(self):
    action_id = self.invoker.add(append_test, ['main', 'additional'])
    
    self.invoker.remove(action_id, ['main'])
    self.assertFalse(self.invoker.has_action(action_id, ['main']))
    self.assertTrue(self.invoker.has_action(action_id, ['additional']))
  
  def test_remove_if_invalid_id(self):
    with self.assertRaises(ValueError):
      self.invoker.remove(-1)
  
  def test_remove_non_existing_group(self):
    action_id = self.invoker.add(append_test, ['main'])
    with self.assertRaises(ValueError):
      self.invoker.remove(action_id, ['additional'])
  
  def test_remove_ignore_if_not_exists(self):
    try:
      self.invoker.remove(-1, ignore_if_not_exists=True)
    except ValueError:
      self.fail(
        'removing actions when `ignore_if_not_exists=True` should not raise error')
  
  def test_remove_multiple_groups_at_once(self):
    test_list = []
    action_id = self.invoker.add(
      append_to_list, ['main', 'additional'], [test_list, 2])
    
    self.invoker.remove(action_id, 'all')
    self.assertFalse(self.invoker.has_action(action_id))
    self.assertFalse(self.invoker.contains(append_to_list, ['main']))
    self.assertFalse(self.invoker.contains(append_to_list, ['additional']))
  
  def test_remove_groups(self):
    test_list = []
    self.invoker.add(append_test, ['main', 'additional'])
    self.invoker.add(
      append_to_list_before, ['main', 'additional'], [test_list, 3], foreach=True)
    self.invoker.add(append_test, ['main', 'additional'])
    
    self.invoker.remove_groups(['main'])
    self.assertEqual(len(self.invoker.list_groups()), 1)
    self.assertIn('additional', self.invoker.list_groups())
    self.assertIsNone(self.invoker.list_actions('main'))
    
    self.invoker.remove_groups(['additional'])
    self.assertEqual(len(self.invoker.list_groups()), 0)
    self.assertIsNone(self.invoker.list_actions('main'))
    self.assertIsNone(self.invoker.list_actions('additional'))
  
  def test_remove_all_groups(self):
    test_list = []
    self.invoker.add(append_test, ['main', 'additional'])
    self.invoker.add(
      append_to_list_before, ['main', 'additional'], [test_list, 3], foreach=True)
    self.invoker.add(append_test, ['main', 'additional'])
    
    self.invoker.remove_groups('all')
    self.assertEqual(len(self.invoker.list_groups()), 0)
    self.assertIsNone(self.invoker.list_actions('main'))
    self.assertIsNone(self.invoker.list_actions('additional'))
  
  def test_remove_groups_non_existing_group(self):
    try:
      self.invoker.remove_groups(['non_existing_group'])
    except Exception:
      self.fail('removing a non-existent group should not raise exception')


class TestInvokerInvokeActions(InvokerTestCase):
  
  @parameterized.parameterized.expand([
    ('default',
     append_test, [], [],
     ['test']),
    
    ('invoke_args',
     append_to_list, [], [1],
     [1]),
    
    ('add_and_invoke_args',
     extend_list, [1], [2, 3],
     [1, 2, 3]),
  ])
  def test_invoke_single_action(
        self,
        test_case_name_suffix,
        action,
        add_args,
        invoke_args,
        expected_result):
    test_list = []
    
    self.invoker.add(action, args=[test_list] + add_args)
    self.invoker.invoke(additional_args=invoke_args)
    
    self.assertEqual(test_list, expected_result)
  
  def test_invoke_invalid_number_of_args(self):
    test_list = []
    self.invoker.add(append_to_list, args=[test_list, 1, 2])
    
    with self.assertRaises(TypeError):
      self.invoker.invoke()
  
  def test_invoke_additional_args_invalid_number_of_args(self):
    test_list = []
    self.invoker.add(append_to_list, args=[test_list])
    
    with self.assertRaises(TypeError):
      self.invoker.invoke()
    
    with self.assertRaises(TypeError):
      self.invoker.invoke(additional_args=[1, 2])
  
  def test_invoke_additional_kwargs_override_former_kwargs(self):
    test_dict = {}
    self.invoker.add(update_dict, args=[test_dict], kwargs={'one': 1, 'two': 2})
    self.invoker.invoke(additional_kwargs={'two': 'two', 'three': 3})
    
    self.assertDictEqual(test_dict, {'one': 1, 'two': 'two', 'three': 3})
  
  def test_invoke_additional_args_position_at_beginning(self):
    test_list = []
    self.invoker.add(append_to_list, args=[1])
    self.invoker.invoke(additional_args=[test_list], additional_args_position=0)
    
    self.assertEqual(test_list, [1])
  
  def test_invoke_additional_args_position_in_middle(self):
    test_list = []
    self.invoker.add(append_to_list_multiple_args, args=[test_list, 1, 3])
    self.invoker.invoke(additional_args=[2], additional_args_position=2)
    
    self.assertEqual(test_list, [1, 2, 3])
  
  def test_invoke_multiple_actions(self):
    test_list = []
    self.invoker.add(append_test, args=[test_list])
    self.invoker.add(extend_list, args=[test_list, 1])
    
    self.invoker.invoke()
    
    self.assertListEqual(test_list, ['test', 1])
  
  def test_invoke_multiple_groups_multiple_actions(self):
    test_dict = {}
    self.invoker.add(
      update_dict, ['main', 'additional'], [test_dict], {'one': 1, 'two': 2})
    self.invoker.add(
      update_dict, ['main'], [test_dict], {'two': 'two', 'three': 3})
    
    self.invoker.invoke(['main'])
    self.assertDictEqual(test_dict, {'one': 1, 'two': 'two', 'three': 3})
    
    self.invoker.invoke(['additional'])
    self.assertDictEqual(test_dict, {'one': 1, 'two': 2, 'three': 3})
    
    test_dict.clear()
    self.invoker.invoke(['main', 'additional'])
    self.assertDictEqual(test_dict, {'one': 1, 'two': 2, 'three': 3})
    
    test_dict.clear()
    self.invoker.invoke(['additional', 'main'])
    self.assertDictEqual(test_dict, {'one': 1, 'two': 'two', 'three': 3})
    
  def test_invoke_empty_group(self):
    try:
      self.invoker.invoke()
    except Exception:
      self.fail('invoking no actions for the given group should not raise exception')
  
  def test_invoke_while_deleting_past_or_present_action_inside_action(self):
    def append_to_list_and_remove_action(list_, arg):
      list_.append(arg)
      self.invoker.remove(action_2_id, ['main'])
    
    test_list = []
    self.invoker.add(append_to_list, ['main'], args=[test_list, 'one'])
    action_2_id = self.invoker.add(
      append_to_list_and_remove_action, ['main'], args=[test_list, 'two'])
    self.invoker.add(append_to_list, ['main'], args=[test_list, 'three'])
    
    self.invoker.invoke(['main'])
    
    self.assertEqual(test_list, ['one', 'two', 'three'])
  
  def test_invoke_while_deleting_future_action_inside_action(self):
    def append_to_list_and_remove_action(list_, arg):
      list_.append(arg)
      self.invoker.remove(action_3_id, ['main'])
    
    test_list = []
    self.invoker.add(append_to_list, ['main'], args=[test_list, 'one'])
    self.invoker.add(append_to_list_and_remove_action, ['main'], args=[test_list, 'two'])
    action_3_id = self.invoker.add(append_to_list, ['main'], args=[test_list, 'three'])
    self.invoker.add(append_to_list, ['main'], args=[test_list, 'four'])
    
    self.invoker.invoke(['main'])
    
    self.assertEqual(test_list, ['one', 'two', 'four'])
  
  def test_invoke_with_generator(self):
    test_list = []
    
    self.invoker.add(append_to_list_via_generator, args=[test_list])
    self.invoker.invoke(additional_args=[2])  # Should be ignored for this (first) call
    self.invoker.invoke(additional_args=[2])
    self.invoker.invoke(additional_args=[3])
    
    self.assertEqual(test_list, [1, 2, 3])
  
  def test_invoke_with_generator_without_running_generator(self):
    test_list = []
    
    self.invoker.add(append_to_list_via_generator, args=[test_list], run_generator=False)
    self.invoker.invoke(additional_args=[2])
    self.invoker.invoke(additional_args=[2])
    self.invoker.invoke(additional_args=[3])
    
    self.assertEqual(test_list, [])
  
  def test_invoke_with_generator_wrapped_in_regular_function(self):
    def _func(*args):
      return append_to_list_via_generator(*args)
    
    test_list = []
    
    self.invoker.add(_func, args=[test_list])
    self.invoker.invoke(additional_args=[2])  # Should be ignored for this (first) call
    self.invoker.invoke(additional_args=[2])
    self.invoker.invoke(additional_args=[3])
    
    self.assertEqual(test_list, [1, 2, 3])
  
  def test_invoke_with_generator_finite(self):
    test_list = []
    
    self.invoker.add(append_to_list_via_generator_finite, args=[test_list])
    self.invoker.invoke(additional_args=[2])  # Should be ignored for this (first) call
    self.invoker.invoke(additional_args=[2])
    self.invoker.invoke(additional_args=[3])  # Should do nothing
    
    self.assertEqual(test_list, [1, 2])
  
  def test_invoke_with_generator_finite_multiple_groups(self):
    test_list = []
    
    self.invoker.add(append_to_list_via_generator_finite, groups=['a', 'b'], args=[test_list])
    self.invoker.invoke(['a'], additional_args=[2])
    self.invoker.invoke(['a'], additional_args=[2])
    self.invoker.invoke(['a'], additional_args=[3])  # Should do nothing
    
    # Should do nothing - generator is "finished" regardless of the group
    self.invoker.invoke(['b'], additional_args=[4])
    self.invoker.invoke(['b'], additional_args=[5])
    self.invoker.invoke(['b'], additional_args=[5])
    
    self.assertEqual(test_list, [1, 2, 1, 5])


class TestInvokerInvokeForeachActions(InvokerTestCase):
  
  @parameterized.parameterized.expand([
    ('default',
     append_to_list, append_to_list, [[1], [2]], [3],
     [1, 3, 2, 3]),
    
    ('before_action',
     append_to_list, append_to_list_before, [[1], [2]], [3],
     [3, 1, 3, 2]),
    
    ('before_and_after_action',
     append_to_list, append_to_list_before_and_after, [[1], [2]], [3],
     [3, 1, 3, 3, 2, 3]),
    
    ('before_and_after_action_multiple_times',
     append_to_list, append_to_list_before_and_after_invoke_twice, [[1], [2]], [3],
     [3, 1, 1, 3, 3, 2, 2, 3]),
  ])
  def test_invoke_single_foreach(
        self,
        test_case_name_suffix,
        action,
        foreach_action,
        actions_args,
        foreach_action_args,
        expected_result):
    test_list = []
    
    self.invoker.add(action, args=[test_list] + actions_args[0])
    self.invoker.add(action, args=[test_list] + actions_args[1])
    self.invoker.add(
      foreach_action, args=[test_list] + foreach_action_args, foreach=True)
    
    self.invoker.invoke()
    
    self.assertListEqual(test_list, expected_result)
  
  @parameterized.parameterized.expand([
    ('simple',
     append_to_list, [append_to_list_before, append_to_list],
     [[1], [2]], [[3], [4]],
     [3, 1, 4, 3, 2, 4]),
    
    ('complex',
     append_to_list,
     [append_to_list_before_and_after, append_to_list_before_and_after_invoke_twice],
     [[1], [2]], [[3], [4]],
     [3, 4, 1, 3, 1, 4,
      3, 4, 2, 3, 2, 4]),
    
    ('even_more_complex',
     append_to_list,
     [append_to_list_before_and_after, append_to_list_before_middle_after_invoke_twice],
     [[1], [2]], [[3], [4]],
     [3, 4, 1, 3, 4, 1, 4,
      3, 4, 2, 3, 4, 2, 4]),
  ])
  def test_invoke_multiple_foreachs(
        self,
        test_case_name_suffix,
        action,
        foreach_actions,
        actions_args,
        foreach_actions_args,
        expected_result):
    test_list = []
    
    self.invoker.add(action, args=[test_list] + actions_args[0])
    self.invoker.add(action, args=[test_list] + actions_args[1])
    self.invoker.add(
      foreach_actions[0], args=[test_list] + foreach_actions_args[0], foreach=True)
    self.invoker.add(
      foreach_actions[1], args=[test_list] + foreach_actions_args[1], foreach=True)
    
    self.invoker.invoke()
    
    self.assertListEqual(test_list, expected_result)
  
  def test_invoke_foreach_use_return_value_from_action(self):
    test_list = []
    self.invoker.add(append_to_list, args=[test_list, 1])
    self.invoker.add(append_to_list, args=[test_list, 2])
    self.invoker.add(append_to_list_again, args=[test_list], foreach=True)
    
    self.invoker.invoke()
    
    self.assertListEqual(test_list, [1, 1, 2, 2])
  
  def test_invoke_foreach_does_nothing_in_another_invoker(self):
    test_list = []
    another_invoker = pginvoker.Invoker()
    another_invoker.add(append_to_list, args=[test_list, 1])
    another_invoker.add(append_to_list, args=[test_list, 2])
    
    self.invoker.add(another_invoker)
    self.invoker.add(append_to_list, args=[test_list, 3])
    self.invoker.add(append_to_list_again, args=[test_list], foreach=True)
    
    self.invoker.invoke()
    
    self.assertListEqual(test_list, [1, 2, 3, 3])
  
  def test_invoke_foreach_invoker(self):
    test_list = []
    
    def append_to_list_before_from_invoker():
      another_invoker.invoke()
      yield
    
    self.invoker.add(append_to_list, args=[test_list, 1])
    self.invoker.add(append_to_list, args=[test_list, 2])
    
    another_invoker = pginvoker.Invoker()
    another_invoker.add(append_to_list, args=[test_list, 3])
    another_invoker.add(append_to_list, args=[test_list, 4])
    
    self.invoker.add(append_to_list_before_from_invoker, foreach=True)
    
    self.invoker.invoke()
    
    self.assertListEqual(test_list, [3, 4, 1, 3, 4, 2])


class TestInvokerInvokeWithInvoker(InvokerTestCase):
  
  def test_invoke(self):
    test_list = []
    another_invoker = pginvoker.Invoker()
    another_invoker.add(append_to_list, args=[test_list, 1])
    another_invoker.add(append_test, args=[test_list])
    
    self.invoker.add(append_to_list, args=[test_list, 2])
    self.invoker.add(another_invoker)
    
    self.invoker.invoke()
    
    self.assertListEqual(test_list, [2, 1, 'test'])
  
  def test_invoke_after_adding_actions_to_invoker(self):
    test_list = []
    another_invoker = pginvoker.Invoker()
    
    self.invoker.add(append_to_list, args=[test_list, 2])
    self.invoker.add(another_invoker)
    
    another_invoker.add(append_to_list, args=[test_list, 1])
    another_invoker.add(append_test, args=[test_list])
    
    self.invoker.invoke()
    
    self.assertListEqual(test_list, [2, 1, 'test'])
  
  def test_invoke_multiple_invokers_after_adding_actions_to_them(self):
    test_list = []
    more_invokers = [pginvoker.Invoker(), pginvoker.Invoker()]
    
    self.invoker.add(append_to_list, args=[test_list, 2])
    self.invoker.add(more_invokers[0])
    self.invoker.add(more_invokers[1])
    
    more_invokers[0].add(append_to_list, args=[test_list, 1])
    more_invokers[0].add(append_test, args=[test_list])
    
    more_invokers[1].add(append_to_list, args=[test_list, 3])
    more_invokers[1].add(append_to_list, args=[test_list, 4])
    
    self.invoker.invoke()
    
    self.assertListEqual(test_list, [2, 1, 'test', 3, 4])
  
  def test_invoke_empty_group(self):
    another_invoker = pginvoker.Invoker()
    try:
      self.invoker.add(another_invoker, ['invalid_group'])
    except Exception:
      self.fail('adding actions from an empty group from another'
                ' Invoker instance should not raise exception')
