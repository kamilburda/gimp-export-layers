# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import unittest

from .. import objectfilter as pgobjectfilter


class FilterableObject(object):
  
  def __init__(self, object_id, name, is_empty=False, colors=None):
    self.object_id = object_id
    self.name = name
    self.is_empty = is_empty
    self.colors = colors if colors is not None else set()


class FilterRules(object):
  
  @staticmethod
  def has_uppercase_letters(obj):
    return obj.name.lower() != obj.name
  
  @staticmethod
  def is_object_id_even(obj):
    return obj.object_id % 2 == 0
  
  @staticmethod
  def has_matching_file_extension(obj, file_extension, case_sensitive=False):
    if not case_sensitive:
      obj.name = obj.name.lower()
    
    return obj.name.endswith('.' + file_extension)
  
  @staticmethod
  def is_empty(obj):
    return obj.is_empty
  
  @staticmethod
  def has_red_color(obj):
    return 'red' in obj.colors
  
  @staticmethod
  def has_green_color(obj):
    return 'green' in obj.colors


class TestObjectFilter(unittest.TestCase):
  
  def setUp(self):
    self.filter = pgobjectfilter.ObjectFilter(pgobjectfilter.ObjectFilter.MATCH_ALL)
  
  def test_is_filter_nonempty(self):
    self.assertFalse(bool(self.filter))
    self.filter.add(FilterRules.has_uppercase_letters)
    self.assertTrue(bool(self.filter))
  
  def test_contains(self):
    rule = self.filter.add(FilterRules.has_uppercase_letters)
    self.assertIn(rule.id, self.filter)
    self.filter.remove(rule.id)
    self.assertNotIn(rule.id, self.filter)
  
  def test_getitem(self):
    rule = self.filter.add(FilterRules.has_uppercase_letters)
    self.assertEquals(self.filter[rule.id], rule)
  
  def test_getitem_nested_filter(self):
    nested_filter = pgobjectfilter.ObjectFilter(name='item_types')
    nested_filter_id = self.filter.add(nested_filter)
    
    self.assertEquals(self.filter[nested_filter_id], nested_filter)
  
  def test_getitem_does_not_exist_raises_error(self):
    with self.assertRaises(KeyError):
      self.filter[42]
  
  def test_len(self):
    self.filter.add(FilterRules.has_uppercase_letters)
    nested_filter = pgobjectfilter.ObjectFilter()
    nested_filter.add(FilterRules.is_object_id_even)
    nested_filter.add(FilterRules.is_empty)
    nested_filter.add(FilterRules.has_red_color)
    self.filter.add(nested_filter)
    
    self.assertEquals(len(self.filter), 2)
    self.assertEquals(len(nested_filter), 3)
  
  def test_add_with_the_same_callable(self):
    rule = self.filter.add(FilterRules.has_uppercase_letters)
    rule_2 = self.filter.add(FilterRules.has_uppercase_letters)
  
    rules = list(self.filter.list_rules().values())
    self.assertEqual(len(rules), 2)
    self.assertEqual(rules[0].function, FilterRules.has_uppercase_letters)
    self.assertEqual(rules[1].function, FilterRules.has_uppercase_letters)
    self.assertEqual(rules[0].id, rule.id)
    self.assertEqual(rules[1].id, rule_2.id)
    self.assertNotEqual(rules[0].id, rules[1].id)
  
  def test_add_invalid_type_raises_error(self):
    with self.assertRaises(TypeError):
      self.filter.add('invalid_type')
  
  def test_remove_no_criteria_raises_error(self):
    with self.assertRaises(ValueError):
      self.filter.remove()
  
  def test_remove_no_match_does_not_raise_error(self):
    try:
      self.filter.remove(42)
    except Exception:
      self.fail('No exception should not be raised if there are no matching rules to remove')
  
  def test_remove_by_name_or_rule(self):
    rule = self.filter.add(FilterRules.has_uppercase_letters, name='custom_name')
    rule_2 = self.filter.add(FilterRules.has_uppercase_letters, name='another_name')
    rule_3 = self.filter.add(FilterRules.is_empty, name='another_name')
    
    obj_properties_filter = pgobjectfilter.ObjectFilter(name='custom_name')
    obj_properties_filter_id = self.filter.add(obj_properties_filter)
    
    rules, rule_ids = self.filter.remove(
      name='custom_name', func_or_filter=FilterRules.has_uppercase_letters)
    
    self.assertEqual(rules, [rule, rule_2, obj_properties_filter])
    self.assertEqual(rule_ids, [rule.id, rule_2.id, obj_properties_filter_id])
    
    rules, rule_ids = self.filter.remove(func_or_filter=FilterRules.is_empty)
    
    self.assertEqual(rules, [rule_3])
    self.assertEqual(rule_ids, [rule_3.id])
    
    self.assertFalse(self.filter)
  
  def test_add_with_custom_name(self):
    self.filter.add(FilterRules.has_uppercase_letters, name='is_upper')
    rules = list(self.filter.list_rules().values())
    
    self.assertEqual(len(rules), 1)
    self.assertEqual(rules[0].name, 'is_upper')
  
  def test_list_rules(self):
    self.filter.add(FilterRules.has_uppercase_letters)
    
    nested_filter = pgobjectfilter.ObjectFilter(name='item_types')
    self.filter.add(nested_filter)
    rules = list(self.filter.list_rules().values())
    
    self.assertEqual(len(rules), 2)
    self.assertEqual(rules[0].function, FilterRules.has_uppercase_letters)
    self.assertEqual(rules[1], nested_filter)
  
  def test_add_temp(self):
    with self.filter.add_temp(FilterRules.has_uppercase_letters) as rule:
      self.assertIn(rule.id, self.filter)
    self.assertNotIn(rule.id, self.filter)
  
  def test_add_temp_with_the_same_callable(self):
    rule = self.filter.add(FilterRules.has_uppercase_letters)
    
    with self.filter.add_temp(FilterRules.has_uppercase_letters) as rule_2:
      rules = list(self.filter.list_rules().values())
      self.assertEqual(len(rules), 2)
      self.assertEqual(rules[0].function, FilterRules.has_uppercase_letters)
      self.assertEqual(rules[1].function, FilterRules.has_uppercase_letters)
      self.assertEqual(rules[0].id, rule.id)
      self.assertEqual(rules[1].id, rule_2.id)
      self.assertNotEqual(rules[0].id, rules[1].id)
    
    rules = list(self.filter.list_rules().values())
    self.assertEqual(len(rules), 1)
    self.assertEqual(rules[0].id, rule.id)
    self.assertNotIn(rule_2.id, self.filter)
  
  def test_add_temp_nested_filter(self):
    with self.filter.add_temp(pgobjectfilter.ObjectFilter(name='item_types')) as filter_id:
      self.assertIn(filter_id, self.filter)
    self.assertNotIn(filter_id, self.filter)
  
  def test_add_temp_remove_upon_exception(self):
    try:
      with self.filter.add_temp(FilterRules.has_uppercase_letters) as rule:
        raise RuntimeError('testing')
    except RuntimeError:
      pass
    self.assertNotIn(rule.id, self.filter)
  
  def test_remove_temp(self):
    rule = self.filter.add(FilterRules.has_uppercase_letters)
    with self.filter.remove_temp(rule.id) as rules_and_ids:
      self.assertEqual(len(rules_and_ids[0]), 1)
      self.assertEqual(len(rules_and_ids[1]), 1)
      self.assertNotIn(rule.id, self.filter)
    self.assertIn(rule.id, self.filter)
    self.assertEqual(len(self.filter), 1)
    self.assertEqual(self.filter[rule.id], rule)
  
  def test_remove_temp_no_match_does_not_raise_error(self):
    try:
      with self.filter.remove_temp(42):
        pass
    except Exception:
      self.fail('No exception should not be raised if there are no matching rules to remove')
  
  def test_remove_temp_add_upon_exception(self):
    rule = self.filter.add(FilterRules.has_uppercase_letters)
    try:
      with self.filter.remove_temp(rule.id) as rules_and_ids:
        raise RuntimeError('testing')
    except RuntimeError:
      pass
    
    self.assertIn(rule.id, self.filter)
    self.assertEqual(len(self.filter), 1)
    self.assertEqual(self.filter[rule.id], rules_and_ids[0][0])

  def test_remove_temp_by_name_or_rule(self):
    rule = self.filter.add(FilterRules.has_uppercase_letters, name='custom_name')
    rule_2 = self.filter.add(FilterRules.has_uppercase_letters, name='another_name')
    self.filter.add(FilterRules.is_empty, name='another_name')
    
    obj_properties_filter = pgobjectfilter.ObjectFilter(name='custom_name')
    obj_properties_filter_id = self.filter.add(obj_properties_filter)
    
    with self.filter.remove_temp(
          name='custom_name',
          func_or_filter=FilterRules.has_uppercase_letters) as rules_and_ids:
      rules, rule_ids = rules_and_ids
      
      self.assertEqual(rules, [rule, rule_2, obj_properties_filter])
      self.assertEqual(rule_ids, [rule.id, rule_2.id, obj_properties_filter_id])
    
    self.assertEqual(len(self.filter), 4)
    for rule, rule_id in zip(*rules_and_ids):
      self.assertIn(rule_id, self.filter)
      self.assertEqual(self.filter[rule_id], rule)
  
  def test_match_all(self):
    self.filter.add(FilterRules.has_uppercase_letters)
    self.filter.add(FilterRules.is_object_id_even)
    
    self.assertTrue(self.filter.is_match(FilterableObject(2, 'Hi There')))
    self.assertFalse(self.filter.is_match(FilterableObject(1, 'Hi There')))
    self.assertFalse(self.filter.is_match(FilterableObject(2, 'hi there')))
    self.assertFalse(self.filter.is_match(FilterableObject(1, 'hi there')))
  
  def test_match_any(self):
    filter_match_any = pgobjectfilter.ObjectFilter(pgobjectfilter.ObjectFilter.MATCH_ANY)
    filter_match_any.add(FilterRules.has_uppercase_letters)
    filter_match_any.add(FilterRules.is_object_id_even)
    
    self.assertTrue(filter_match_any.is_match(FilterableObject(2, 'Hi There')))
    self.assertTrue(filter_match_any.is_match(FilterableObject(1, 'Hi There')))
    self.assertTrue(filter_match_any.is_match(FilterableObject(2, 'hi there')))
    self.assertFalse(filter_match_any.is_match(FilterableObject(1, 'hi there')))
  
  def test_match_empty_filter(self):
    filter_match_any = pgobjectfilter.ObjectFilter(pgobjectfilter.ObjectFilter.MATCH_ANY)
    
    self.assertTrue(self.filter.is_match(FilterableObject(2, 'Hi There')))
    self.assertTrue(filter_match_any.is_match(FilterableObject(2, 'Hi There')))
  
  def test_match_custom_args(self):
    rule = self.filter.add(FilterRules.has_matching_file_extension, ['jpg'])
    self.assertTrue(self.filter.is_match(FilterableObject(2, 'Hi There.jpg')))
    self.assertTrue(self.filter.is_match(FilterableObject(2, 'Hi There.Jpg')))
    self.filter.remove(rule.id)
    
    self.filter.add(FilterRules.has_matching_file_extension, ['Jpg', True])
    self.assertFalse(self.filter.is_match(FilterableObject(2, 'Hi There.jpg')))
    self.assertTrue(self.filter.is_match(FilterableObject(2, 'Hi There.Jpg')))
  
  def test_match_custom_kwargs(self):
    self.filter.add(
      FilterRules.has_matching_file_extension,
      kwargs={'file_extension': 'Jpg', 'case_sensitive': True})
    self.assertFalse(self.filter.is_match(FilterableObject(2, 'Hi There.jpg')))
    self.assertTrue(self.filter.is_match(FilterableObject(2, 'Hi There.Jpg')))
  
  def test_match_add_temp(self):
    with self.filter.add_temp(FilterRules.has_matching_file_extension, ['jpg']):
      self.assertTrue(self.filter.is_match(FilterableObject(2, 'Hi There.jpg')))
      self.assertTrue(self.filter.is_match(FilterableObject(2, 'Hi There.Jpg')))
  
  def test_match_remove_temp(self):
    rule = self.filter.add(FilterRules.is_object_id_even)
    with self.filter.remove_temp(rule.id):
      self.assertTrue(self.filter.is_match(FilterableObject(3, '')))
      self.assertTrue(self.filter.is_match(FilterableObject(4, '')))
  
  def test_match_with_nested_filter_simple(self):
    # filter - MATCH_ALL
      # * rule
      # * filter - MATCH_ANY
        # * rule
        # * rule
    
    obj_properties_filter_id = self.filter.add(pgobjectfilter.ObjectFilter(
      self.filter.MATCH_ANY, name='obj_properties'))
    self.filter[obj_properties_filter_id].add(FilterRules.is_empty)
    self.filter[obj_properties_filter_id].add(FilterRules.is_object_id_even)
    self.filter.add(FilterRules.has_uppercase_letters)
    
    self.assertTrue(
      self.filter.is_match(FilterableObject(2, 'Hi There.jpg', is_empty=True)))
    self.assertTrue(
      self.filter.is_match(FilterableObject(1, 'Hi There.jpg', is_empty=True)))
    self.assertTrue(
      self.filter.is_match(FilterableObject(2, 'Hi There.jpg', is_empty=False)))
    self.assertFalse(
      self.filter.is_match(FilterableObject(1, 'Hi There.jpg', is_empty=False)))
    self.assertFalse(
      self.filter.is_match(FilterableObject(2, 'hi there.jpg', is_empty=False)))
    self.assertFalse(
      self.filter.is_match(FilterableObject(1, 'hi there.jpg', is_empty=False)))
  
  def test_match_with_nested_filter_nested(self):
    # filter - MATCH_ALL
      # * rule
      # * filter - MATCH_ANY
        # * rule
        # * filter - MATCH_ALL
          # * rule
          # * rule
    
    self.filter.add(FilterRules.is_object_id_even)
    obj_properties_filter_id = self.filter.add(pgobjectfilter.ObjectFilter(
      self.filter.MATCH_ANY, name='obj_properties'))
    
    obj_properties_nested_filter = self.filter[obj_properties_filter_id]
    obj_properties_nested_filter.add(FilterRules.is_empty)
    colors_filter_id = obj_properties_nested_filter.add(
      pgobjectfilter.ObjectFilter(name='colors'))
    
    color_nested_filter = obj_properties_nested_filter[colors_filter_id]
    color_nested_filter.add(FilterRules.has_red_color)
    color_nested_filter.add(FilterRules.has_green_color)
    
    self.assertTrue(self.filter.is_match(
      FilterableObject(2, '', is_empty=True, colors={'red', 'green'})))
    self.assertTrue(self.filter.is_match(
      FilterableObject(2, '', is_empty=True, colors={'red'})))
    self.assertTrue(self.filter.is_match(
      FilterableObject(2, '', is_empty=True, colors=None)))
    self.assertTrue(self.filter.is_match(
      FilterableObject(2, '', is_empty=False, colors={'red', 'green'})))
    self.assertFalse(self.filter.is_match(
      FilterableObject(2, '', is_empty=False, colors={'green'})))
    self.assertFalse(self.filter.is_match(
      FilterableObject(1, '', is_empty=True, colors={'red', 'green'})))
  
  def test_find_by_name(self):
    rule = self.filter.add(FilterRules.has_uppercase_letters, name='custom_name')
    self.filter.add(FilterRules.is_empty, name='another_name')
    
    obj_properties_filter = pgobjectfilter.ObjectFilter(name='custom_name')
    obj_properties_filter_id = self.filter.add(obj_properties_filter)
    self.filter[obj_properties_filter_id].add(FilterRules.is_empty)
    
    rule_ids = self.filter.find(name='custom_name')
    self.assertEqual(len(rule_ids), 2)
    self.assertEqual(rule_ids[0], rule.id)
    self.assertEqual(self.filter[rule_ids[0]].function, FilterRules.has_uppercase_letters)
    self.assertEqual(self.filter[rule_ids[0]].name, 'custom_name')
    self.assertEqual(rule_ids[1], obj_properties_filter_id)
    self.assertEqual(self.filter[rule_ids[1]], obj_properties_filter)
    self.assertEqual(self.filter[rule_ids[1]].name, 'custom_name')
    
  def test_find_by_rule(self):
    rule = self.filter.add(FilterRules.has_uppercase_letters, name='custom_name')
    rule_2 = self.filter.add(FilterRules.has_uppercase_letters, name='another_name')
    
    self.filter.add(pgobjectfilter.ObjectFilter(name='custom_name'))
    
    rule_ids = self.filter.find(func_or_filter=FilterRules.has_uppercase_letters)
    self.assertEqual(len(rule_ids), 2)
    self.assertEqual(rule_ids[0], rule.id)
    self.assertEqual(self.filter[rule_ids[0]].function, FilterRules.has_uppercase_letters)
    self.assertEqual(self.filter[rule_ids[0]].name, 'custom_name')
    self.assertEqual(rule_ids[1], rule_2.id)
    self.assertEqual(self.filter[rule_ids[1]].function, FilterRules.has_uppercase_letters)
    self.assertEqual(self.filter[rule_ids[1]].name, 'another_name')
  
  def test_find_by_name_or_rule(self):
    rule = self.filter.add(FilterRules.has_uppercase_letters, name='custom_name')
    rule_2 = self.filter.add(FilterRules.has_uppercase_letters, name='another_name')
    self.filter.add(FilterRules.is_empty, name='another_name')
    
    obj_properties_filter = pgobjectfilter.ObjectFilter(name='custom_name')
    obj_properties_filter_id = self.filter.add(obj_properties_filter)
    self.filter[obj_properties_filter_id].add(FilterRules.is_empty)
    
    rule_ids = self.filter.find(
      name='custom_name', func_or_filter=FilterRules.has_uppercase_letters)
    self.assertEqual(len(rule_ids), 3)
    self.assertEqual(rule_ids[0], rule.id)
    self.assertEqual(self.filter[rule_ids[0]].function, FilterRules.has_uppercase_letters)
    self.assertEqual(self.filter[rule_ids[0]].name, 'custom_name')
    self.assertEqual(rule_ids[1], rule_2.id)
    self.assertEqual(self.filter[rule_ids[1]].function, FilterRules.has_uppercase_letters)
    self.assertEqual(self.filter[rule_ids[1]].name, 'another_name')
    self.assertEqual(rule_ids[2], obj_properties_filter_id)
    self.assertEqual(self.filter[rule_ids[2]], obj_properties_filter)
    self.assertEqual(self.filter[rule_ids[2]].name, 'custom_name')
  
  def test_find_no_match(self):
    self.filter.add(FilterRules.has_uppercase_letters, name='custom_name')
    self.filter.add(FilterRules.is_empty, name='another_name')
    
    obj_properties_filter_id = self.filter.add(pgobjectfilter.ObjectFilter(name='custom_name'))
    self.filter[obj_properties_filter_id].add(FilterRules.is_empty)
    
    rule_ids = self.filter.find(name='no_matching_name')
    self.assertEqual(len(rule_ids), 0)
  
  def test_find_limit_count_first_matches(self):
    rule = self.filter.add(FilterRules.has_uppercase_letters, name='custom_name')
    self.filter.add(FilterRules.has_uppercase_letters, name='custom_name')
    self.filter.add(FilterRules.has_uppercase_letters, name='custom_name')
    
    rule_ids = self.filter.find(name='custom_name', count=1)
    self.assertEqual(len(rule_ids), 1)
    self.assertEqual(rule_ids[0], rule.id)
  
  def test_find_limit_count_last_matches(self):
    self.filter.add(FilterRules.has_uppercase_letters, name='custom_name')
    rule_2 = self.filter.add(FilterRules.has_uppercase_letters, name='custom_name')
    rule_3 = self.filter.add(FilterRules.has_uppercase_letters, name='custom_name')
    
    rule_ids = self.filter.find(name='custom_name', count=-2)
    self.assertEqual(len(rule_ids), 2)
    self.assertEqual(rule_ids[0], rule_2.id)
    self.assertEqual(rule_ids[1], rule_3.id)
  
  def test_find_missing_criteria_raises_error(self):
    with self.assertRaises(ValueError):
      self.filter.find()
  
  def test_reset(self):
    self.filter.reset()
    self.assertFalse(bool(self.filter))
    
    self.filter.add(FilterRules.is_object_id_even)
    self.filter.add(FilterRules.has_uppercase_letters)
    self.filter.reset()
    self.assertFalse(bool(self.filter))
