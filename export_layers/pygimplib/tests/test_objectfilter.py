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
  
  def test_add_with_the_same_function(self):
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
  
  def test_remove_invalid_id_raises_error(self):
    with self.assertRaises(ValueError):
      self.filter.remove(42)
  
  def test_remove_invalid_id_without_raise_if_not_found(self):
    try:
      self.filter.remove(42, raise_if_not_found=False)
    except ValueError:
      self.fail('ValueError should not be raised if raise_if_not_found is False')
  
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
  
  def test_add_temp_with_the_same_function(self):
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
    with self.filter.remove_temp(rule.id) as rule:
      self.assertNotIn(rule.id, self.filter)
    self.assertIn(rule.id, self.filter)
    self.assertEqual(len(self.filter), 1)
    self.assertEqual(self.filter[rule.id], rule)
  
  def test_remove_temp_invalid_id_raises_error(self):
    with self.assertRaises(ValueError):
      with self.filter.remove_temp(42):
        pass
  
  def test_remove_temp_invalid_id_without_raise_if_not_found(self):
    try:
      with self.filter.remove_temp(42, raise_if_not_found=False):
        pass
    except ValueError:
      self.fail('ValueError should not be raised if raise_if_not_found=False')
  
  def test_remove_temp_add_upon_exception(self):
    rule = self.filter.add(FilterRules.has_uppercase_letters)
    try:
      with self.filter.remove_temp(rule.id) as rule_or_filter:
        raise RuntimeError('testing')
    except RuntimeError:
      pass
    
    self.assertIn(rule.id, self.filter)
    self.assertEqual(len(self.filter), 1)
    self.assertEqual(self.filter[rule.id], rule_or_filter)

  def test_remove_temp_nested_filter(self):
    nested_filter_id = self.filter.add(pgobjectfilter.ObjectFilter(name='item_types'))
    with self.filter.remove_temp(nested_filter_id) as nested_filter:
      self.assertNotIn(nested_filter_id, self.filter)
    self.assertIn(nested_filter_id, self.filter)
    self.assertEqual(self.filter[nested_filter_id], nested_filter)
  
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
  
  def test_reset(self):
    self.filter.reset()
    self.assertFalse(bool(self.filter))
    
    self.filter.add(FilterRules.is_object_id_even)
    self.filter.add(FilterRules.has_uppercase_letters)
    self.filter.reset()
    self.assertFalse(bool(self.filter))
