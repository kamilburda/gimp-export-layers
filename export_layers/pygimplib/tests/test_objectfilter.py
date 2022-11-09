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
    self.assertNotIn(FilterRules.has_uppercase_letters, self.filter)
    self.filter.add(FilterRules.has_uppercase_letters)
    self.assertIn(FilterRules.has_uppercase_letters, self.filter)
    self.filter.remove(FilterRules.has_uppercase_letters)
    self.assertNotIn(FilterRules.has_uppercase_letters, self.filter)
  
  def test_getitem(self):
    self.filter.add(FilterRules.has_uppercase_letters)
    rule = self.filter[FilterRules.has_uppercase_letters]
    
    self.assertEquals(rule.function, FilterRules.has_uppercase_letters)
  
  def test_getitem_nested_filter(self):
    nested_filter = pgobjectfilter.ObjectFilter()
    self.filter.add(nested_filter, name='item_types')
    rule = self.filter['item_types']
    
    self.assertEquals(rule, nested_filter)
  
  def test_getitem_does_not_exist_raises_error(self):
    with self.assertRaises(KeyError):
      self.filter['nonexistent_nested_filter']
  
  def test_add_remove(self):
    with self.assertRaises(TypeError):
      self.filter.add(None)
    
    with self.assertRaises(ValueError):
      self.filter.remove(FilterRules.has_uppercase_letters)
    
    try:
      self.filter.remove(FilterRules.has_uppercase_letters, raise_if_not_found=False)
    except ValueError:
      self.fail('ValueError should not be raised if raise_if_not_found is False')
  
  def test_add_with_custom_name(self):
    self.filter.add(FilterRules.has_uppercase_letters, name='is_upper')
    rules = self.filter.list_rules()
    
    self.assertEqual(len(rules), 1)
    self.assertEqual(rules[0].name, 'is_upper')
  
  def test_add_invalid_type(self):
    with self.assertRaises(TypeError):
      self.filter.add('invalid')
  
  def test_list_rules(self):
    self.filter.add(FilterRules.has_uppercase_letters)
    
    nested_filter = pgobjectfilter.ObjectFilter()
    self.filter.add(nested_filter, name='item_types')
    rules = self.filter.list_rules()
    
    self.assertEqual(len(rules), 2)
    self.assertEqual(rules[0].function, FilterRules.has_uppercase_letters)
    self.assertEqual(rules[1], nested_filter)
  
  def test_add_temp(self):
    with self.filter.add_temp(FilterRules.has_uppercase_letters):
      self.assertIn(FilterRules.has_uppercase_letters, self.filter)
    self.assertNotIn(FilterRules.has_uppercase_letters, self.filter)
    
    self.filter.add(FilterRules.has_uppercase_letters)
    with self.filter.add_temp(FilterRules.has_uppercase_letters):
      pass
    self.assertIn(FilterRules.has_uppercase_letters, self.filter)
  
  def test_add_temp_nested_filter(self):
    with self.filter.add_temp(pgobjectfilter.ObjectFilter(), name='item_types'):
      self.assertIn('item_types', self.filter)
    self.assertNotIn('item_types', self.filter)
  
  def test_add_temp_remove_upon_exception(self):
    try:
      with self.filter.add_temp(FilterRules.has_matching_file_extension):
        raise RuntimeError('testing')
    except RuntimeError:
      pass
    self.assertNotIn(FilterRules.has_matching_file_extension, self.filter)
  
  def test_remove_temp(self):
    self.filter.add(FilterRules.is_object_id_even)
    with self.filter.remove_temp(FilterRules.is_object_id_even):
      self.assertNotIn(FilterRules.is_object_id_even, self.filter)
    self.assertIn(FilterRules.is_object_id_even, self.filter)
    
    self.filter.remove(FilterRules.is_object_id_even)
    with self.assertRaises(ValueError):
      with self.filter.remove_temp(FilterRules.has_matching_file_extension):
        pass
    
    try:
      with self.filter.remove_temp(
             FilterRules.has_matching_file_extension, raise_if_not_found=False):
        pass
    except ValueError:
      self.fail('ValueError should not be raised if raise_if_not_found=False')
  
  def test_remove_temp_add_upon_exception(self):
    self.filter.add(FilterRules.has_matching_file_extension, ['jpg'])
    try:
      with self.filter.remove_temp(FilterRules.has_matching_file_extension):
        raise RuntimeError('testing')
    except RuntimeError:
      pass
    self.assertIn(FilterRules.has_matching_file_extension, self.filter)
    
    # Check if the filter works properly after the rule is restored.
    self.assertTrue(self.filter.is_match(FilterableObject(2, 'Hi There.jpg')))
    self.assertFalse(self.filter.is_match(FilterableObject(2, 'Hi There.png')))
  
  def test_remove_does_not_exist(self):
    with self.assertRaises(ValueError):
      self.filter.remove(FilterRules.has_matching_file_extension)

  def test_remove_temp_nested_filter(self):
    self.filter.add(pgobjectfilter.ObjectFilter(), name='item_types')
    with self.filter.remove_temp('item_types'):
      self.assertNotIn('item_types', self.filter)
    self.assertIn('item_types', self.filter)
  
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
    self.filter.add(FilterRules.has_matching_file_extension, ['jpg'])
    self.assertTrue(self.filter.is_match(FilterableObject(2, 'Hi There.jpg')))
    self.assertTrue(self.filter.is_match(FilterableObject(2, 'Hi There.Jpg')))
    self.filter.remove(FilterRules.has_matching_file_extension)
    
    self.filter.add(FilterRules.has_matching_file_extension, ['Jpg', True])
    self.assertFalse(self.filter.is_match(FilterableObject(2, 'Hi There.jpg')))
    self.assertTrue(self.filter.is_match(FilterableObject(2, 'Hi There.Jpg')))
    self.filter.remove(FilterRules.has_matching_file_extension)
  
  def test_match_custom_kwargs(self):
    self.filter.add(
      FilterRules.has_matching_file_extension,
      func_kwargs={'file_extension': 'Jpg', 'case_sensitive': True})
    self.assertFalse(self.filter.is_match(FilterableObject(2, 'Hi There.jpg')))
    self.assertTrue(self.filter.is_match(FilterableObject(2, 'Hi There.Jpg')))
    self.filter.remove(FilterRules.has_matching_file_extension)
  
  def test_match_add_temp(self):
    with self.filter.add_temp(FilterRules.has_matching_file_extension, ['jpg']):
      self.assertTrue(self.filter.is_match(FilterableObject(2, 'Hi There.jpg')))
      self.assertTrue(self.filter.is_match(FilterableObject(2, 'Hi There.Jpg')))
  
  def test_match_remove_temp(self):
    self.filter.add(FilterRules.is_object_id_even)
    with self.filter.remove_temp(FilterRules.is_object_id_even):
      self.assertTrue(self.filter.is_match(FilterableObject(3, '')))
      self.assertTrue(self.filter.is_match(FilterableObject(4, '')))
  
  def test_match_with_nested_filter_simple(self):
    # filter - MATCH_ALL
      # * rule
      # * filter - MATCH_ANY
        # * rule
        # * rule
    
    self.filter.add(pgobjectfilter.ObjectFilter(self.filter.MATCH_ANY), name='obj_properties')
    self.filter['obj_properties'].add(FilterRules.is_empty)
    self.filter['obj_properties'].add(FilterRules.is_object_id_even)
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
    self.filter.add(pgobjectfilter.ObjectFilter(self.filter.MATCH_ANY), name='obj_properties')
    
    obj_properties_nested_filter = self.filter['obj_properties']
    obj_properties_nested_filter.add(FilterRules.is_empty)
    obj_properties_nested_filter.add(pgobjectfilter.ObjectFilter(), name='colors')
    
    color_nested_filter = obj_properties_nested_filter['colors']
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
