#-------------------------------------------------------------------------------
#
# This file is part of Export Layers.
#
# Copyright (C) 2013, 2014 khalim19 <khalim19@gmail.com>
# 
# Export Layers is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# Export Layers is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with Export Layers.  If not, see <http://www.gnu.org/licenses/>.
#
#-------------------------------------------------------------------------------

#=============================================================================== 

import unittest

from export_layers.objectfilter import ObjectFilter

#===============================================================================

class FilterableObject(object):
  
  def __init__(self, object_id, name, is_empty=False, colors=None):
    self.object_id = object_id
    self.name = name
    self.is_empty = is_empty
    self.colors = colors if colors is not None else set()

def has_uppercase_letters(obj):
  return obj.name.lower() != obj.name

def is_object_id_even(obj):
  return obj.object_id % 2 == 0

def has_matching_file_format(obj, file_format, case_sensitive=False):
  if not case_sensitive:
    obj.name = obj.name.lower()
  
  return obj.name.endswith('.' + file_format)

def is_empty(obj):
  return obj.is_empty

def has_red_color(obj):
  return "red" in obj.colors

def has_green_color(obj):
  return "green" in obj.colors

def invalid_rule_func():
  pass

#===============================================================================

class TestObjectFilter(unittest.TestCase):
  
  def setUp(self):
    self.filter = ObjectFilter()
  
  def test_has_rule(self):
    self.assertFalse(self.filter.has_rule(has_uppercase_letters))
    self.filter.add_rule(has_uppercase_letters)
    self.assertTrue(self.filter.has_rule(has_uppercase_letters))
    self.filter.remove_rule(has_uppercase_letters)
    self.assertFalse(self.filter.has_rule(has_uppercase_letters))
  
  def test_add_remove_rule(self):
    with self.assertRaises(TypeError):
      self.filter.add_rule(None)
    
    with self.assertRaises(TypeError):
      self.filter.add_rule(invalid_rule_func)
    
    with self.assertRaises(ValueError):
      self.filter.remove_rule(has_uppercase_letters)
    
    self.filter.add_rule(is_object_id_even)
    with self.assertRaises(ValueError):
      self.filter.add_rule(is_object_id_even)
  
  def test_add_rule_temp(self):
    with self.filter.add_rule_temp(has_matching_file_format, 'jpg'):
      self.assertTrue(self.filter.has_rule(has_matching_file_format))
    self.assertFalse(self.filter.has_rule(has_matching_file_format))
  
  def test_add_rule_temp_remove_upon_exception(self):
    try:
      with self.filter.add_rule_temp(has_matching_file_format):
        raise Exception("testing")
    except Exception:
      pass
    self.assertFalse(self.filter.has_rule(has_matching_file_format))
  
  def test_remove_rule_temp(self):
    self.filter.add_rule(is_object_id_even)
    with self.filter.remove_rule_temp(is_object_id_even):
      self.assertFalse(self.filter.has_rule(is_object_id_even))
    self.assertTrue(self.filter.has_rule(is_object_id_even))
    
    self.filter.remove_rule(is_object_id_even)
    with self.assertRaises(ValueError):
      with self.filter.remove_rule_temp(has_matching_file_format):
        pass
    
    self.filter.add_rule(has_matching_file_format, 'jpg')
    with self.assertRaises(TypeError):
      # remove_rule_temp must have only 1 argument
      with self.filter.remove_rule_temp(has_matching_file_format, 'jpg'):
        pass
  
  def test_remove_rule_temp_add_upon_exception(self):
    self.filter.add_rule(has_matching_file_format, 'jpg')
    try:
      with self.filter.remove_rule_temp(has_matching_file_format):
        raise Exception("testing")
    except Exception:
      pass
    self.assertTrue(self.filter.has_rule(has_matching_file_format))
    
    # Check if the filter works properly after the rule is restored.
    self.assertTrue(self.filter.is_match(FilterableObject(2, "Hi There.jpg")))
    self.assertFalse(self.filter.is_match(FilterableObject(2, "Hi There.png")))
  
  def test_get_subfilter(self):
    with self.assertRaises(ValueError):
      self.filter['subfilter_does_not_exist']
    
    with self.assertRaises(ValueError):
      # Key is not a subfilter
      self.filter[has_matching_file_format]
  
  def test_add_subfilter(self):
    self.filter.add_subfilter('subfilter', ObjectFilter())
    with self.assertRaises(ValueError):
      self.filter.add_subfilter('subfilter', ObjectFilter())
  
  def test_remove_subfilter(self):
    with self.assertRaises(ValueError):
      self.filter.remove_subfilter('subfilter_does_not_exist')
  
  def test_add_subfilter_temp(self):
    with self.filter.add_subfilter_temp('layer_types', ObjectFilter()):
      self.assertTrue(self.filter.has_subfilter('layer_types'))
    self.assertFalse(self.filter.has_subfilter('layer_types'))
    
    with self.assertRaises(TypeError):
      # Wrong number of arguments
      with self.filter.add_rule_temp(has_matching_file_format):
        self.assertTrue(self.filter.is_match(FilterableObject(2, "Hi There.jpg")))

  def test_remove_subfilter_temp(self):
    self.filter.add_subfilter('layer_types', ObjectFilter())
    with self.filter.remove_subfilter_temp('layer_types'):
      self.assertFalse(self.filter.has_subfilter('layer_types'))
    self.assertTrue(self.filter.has_subfilter('layer_types'))
  
  def test_match_all(self):
    self.filter.match_type = self.filter.MATCH_ALL
    
    self.filter.add_rule(has_uppercase_letters)
    self.filter.add_rule(is_object_id_even)
    
    self.assertTrue(self.filter.is_match(FilterableObject(2, "Hi There")))
    self.assertFalse(self.filter.is_match(FilterableObject(1, "Hi There")))
    self.assertFalse(self.filter.is_match(FilterableObject(2, "hi there")))
    self.assertFalse(self.filter.is_match(FilterableObject(1, "hi there")))
  
  def test_match_any(self):
    self.filter.match_type = self.filter.MATCH_ANY
    
    self.filter.add_rule(has_uppercase_letters)
    self.filter.add_rule(is_object_id_even)
    
    self.assertTrue(self.filter.is_match(FilterableObject(2, "Hi There")))
    self.assertTrue(self.filter.is_match(FilterableObject(1, "Hi There")))
    self.assertTrue(self.filter.is_match(FilterableObject(2, "hi there")))
    self.assertFalse(self.filter.is_match(FilterableObject(1, "hi there")))
  
  def test_match_empty_filter(self):
    self.filter.match_type = self.filter.MATCH_ALL
    self.assertTrue(self.filter.is_match(FilterableObject(2, "Hi There")))
    self.filter.match_type = self.filter.MATCH_ANY
    self.assertTrue(self.filter.is_match(FilterableObject(2, "Hi There")))
  
  def test_match_custom_args(self):
    self.filter.add_rule(has_matching_file_format, 'jpg')
    self.assertTrue(self.filter.is_match(FilterableObject(2, "Hi There.jpg")))
    self.assertTrue(self.filter.is_match(FilterableObject(2, "Hi There.Jpg")))
    self.filter.remove_rule(has_matching_file_format)
    
    self.filter.add_rule(has_matching_file_format, 'Jpg', True)
    self.assertFalse(self.filter.is_match(FilterableObject(2, "Hi There.jpg")))
    self.assertTrue(self.filter.is_match(FilterableObject(2, "Hi There.Jpg")))
    self.filter.remove_rule(has_matching_file_format)
  
  def test_match_add_rule_temp(self):
    with self.filter.add_rule_temp(has_matching_file_format, 'jpg'):
      self.assertTrue(self.filter.is_match(FilterableObject(2, "Hi There.jpg")))
      self.assertTrue(self.filter.is_match(FilterableObject(2, "Hi There.Jpg")))
  
  def test_match_remove_rule_temp(self):
    self.filter.add_rule(is_object_id_even)
    with self.filter.remove_rule_temp(is_object_id_even):
      self.assertTrue(self.filter.is_match(FilterableObject(3, "")))
      self.assertTrue(self.filter.is_match(FilterableObject(4, "")))
  
  def test_match_with_subfilters_simple(self):
    # filter - MATCH_ALL
      # * rule
      # * subfilter - MATCH_ANY
        # * rule
        # * rule
    
    self.filter.match_type = self.filter.MATCH_ALL
    self.filter.add_subfilter('obj_properties', ObjectFilter(self.filter.MATCH_ANY))
    self.filter['obj_properties'].add_rule(is_empty)
    self.filter['obj_properties'].add_rule(is_object_id_even)
    self.filter.add_rule(has_uppercase_letters)
    
    self.assertTrue(self.filter.is_match(FilterableObject(2, "Hi There.jpg", is_empty=True)))
    self.assertTrue(self.filter.is_match(FilterableObject(1, "Hi There.jpg", is_empty=True)))
    self.assertTrue(self.filter.is_match(FilterableObject(2, "Hi There.jpg", is_empty=False)))
    self.assertFalse(self.filter.is_match(FilterableObject(1, "Hi There.jpg", is_empty=False)))
    self.assertFalse(self.filter.is_match(FilterableObject(2, "hi there.jpg", is_empty=False)))
    self.assertFalse(self.filter.is_match(FilterableObject(1, "hi there.jpg", is_empty=False)))
  
  def test_match_with_subfilters_nested(self):
    # filter - MATCH_ALL
      # * rule
      # * subfilter - MATCH_ANY
        # * rule
        # * subfilter - MATCH_ALL
          # * rule
          # * rule
    
    self.filter.match_type = self.filter.MATCH_ALL
    self.filter.add_rule(is_object_id_even)
    self.filter.add_subfilter('obj_properties', ObjectFilter(self.filter.MATCH_ANY))
    self.filter['obj_properties'].add_rule(is_empty)
    self.filter['obj_properties'].add_subfilter('colors', ObjectFilter(self.filter.MATCH_ALL))
    self.filter['obj_properties']['colors'].add_rule(has_red_color)
    self.filter['obj_properties']['colors'].add_rule(has_green_color)
    
    self.assertTrue(self.filter.is_match(
      FilterableObject(2, "", is_empty=True, colors={'red', 'green'})))
    self.assertTrue(self.filter.is_match(
      FilterableObject(2, "", is_empty=True, colors={'red'})))
    self.assertTrue(self.filter.is_match(
      FilterableObject(2, "", is_empty=True, colors=None)))
    self.assertTrue(self.filter.is_match(
      FilterableObject(2, "", is_empty=False, colors={'red', 'green'})))
    self.assertFalse(self.filter.is_match(
      FilterableObject(2, "", is_empty=False, colors={'green'})))
    self.assertFalse(self.filter.is_match(
      FilterableObject(1, "", is_empty=True, colors={'red', 'green'})))
    
