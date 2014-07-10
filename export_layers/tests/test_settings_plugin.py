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

"""
This module:
* tests the public interface of various modules of the plug-in
"""

#===============================================================================

from __future__ import absolute_import
from __future__ import print_function
#from __future__ import unicode_literals
from __future__ import division

#=============================================================================== 

import unittest

from export_layers import settings_plugin

#===============================================================================

class TestMainSettings(unittest.TestCase):
  
  def setUp(self):
    self.main_settings = settings_plugin.MainSettings()
  
  def test_streamline_layer_groups_as_directories(self):
    self.main_settings['layer_groups_as_directories'].value = False
    changed_settings = self.main_settings['layer_groups_as_directories'].streamline()
    self.assertTrue(self.main_settings['empty_directories'] in changed_settings)
    self.assertTrue(self.main_settings['merge_layer_groups'] in changed_settings)
    self.assertEqual(self.main_settings['empty_directories'].ui_enabled, False)
    self.assertEqual(self.main_settings['empty_directories'].value, False)
    self.assertEqual(self.main_settings['merge_layer_groups'].ui_enabled, True)
    
    self.main_settings['layer_groups_as_directories'].value = True
    changed_settings = self.main_settings['layer_groups_as_directories'].streamline()
    self.assertTrue(self.main_settings['empty_directories'] in changed_settings)
    self.assertTrue(self.main_settings['merge_layer_groups'] in changed_settings)
    self.assertEqual(self.main_settings['empty_directories'].ui_enabled, True)
    self.assertEqual(self.main_settings['merge_layer_groups'].ui_enabled, False)
    self.assertEqual(self.main_settings['merge_layer_groups'].value, False)
  
  def test_streamline_file_ext_mode(self):
    self.main_settings['file_ext_mode'].value = self.main_settings['file_ext_mode'].options['no_handling']
    changed_settings = self.main_settings['file_ext_mode'].streamline()
    self.assertTrue(self.main_settings['strip_mode'] in changed_settings)
    self.assertEqual(self.main_settings['strip_mode'].ui_enabled, True)
    self.assertEqual(self.main_settings['strip_mode'].value, self.main_settings['strip_mode'].default_value)
    
    self.main_settings['file_ext_mode'].value = self.main_settings['file_ext_mode'].options['only_matching_file_format']
    changed_settings = self.main_settings['file_ext_mode'].streamline()
    self.assertTrue(self.main_settings['strip_mode'] in changed_settings)
    self.assertEqual(self.main_settings['strip_mode'].ui_enabled, False)
    self.assertEqual(self.main_settings['strip_mode'].value, self.main_settings['strip_mode'].options['never'])
    
    self.main_settings['file_ext_mode'].value = self.main_settings['file_ext_mode'].options['use_as_file_format']
    changed_settings = self.main_settings['file_ext_mode'].streamline()
    self.assertTrue(self.main_settings['strip_mode'] in changed_settings)
    self.assertEqual(self.main_settings['strip_mode'].ui_enabled, False)
    self.assertEqual(self.main_settings['strip_mode'].value, self.main_settings['strip_mode'].options['never'])
  
  def test_streamline_square_bracketed(self):
    square_bracketed_mode = self.main_settings['square_bracketed_mode']
    
    square_bracketed_mode.value = square_bracketed_mode.options['normal']
    changed_settings = self.main_settings['square_bracketed_mode'].streamline()
    self.assertTrue(self.main_settings['remove_square_brackets'] in changed_settings)
    self.assertEqual(self.main_settings['remove_square_brackets'].ui_visible, True)
    self.assertTrue(self.main_settings['crop_to_background'] in changed_settings)
    self.assertEqual(self.main_settings['crop_to_background'].ui_visible, False)
    
    square_bracketed_mode.value = square_bracketed_mode.options['background']
    changed_settings = self.main_settings['square_bracketed_mode'].streamline()
    self.assertTrue(self.main_settings['remove_square_brackets'] in changed_settings)
    self.assertEqual(self.main_settings['remove_square_brackets'].ui_visible, False)
    self.assertTrue(self.main_settings['crop_to_background'] in changed_settings)
    self.assertEqual(self.main_settings['crop_to_background'].ui_visible, True)
    
    square_bracketed_mode.value = square_bracketed_mode.options['ignore']
    changed_settings = self.main_settings['square_bracketed_mode'].streamline()
    self.assertTrue(self.main_settings['remove_square_brackets'] in changed_settings)
    self.assertEqual(self.main_settings['remove_square_brackets'].ui_visible, False)
    self.assertTrue(self.main_settings['crop_to_background'] in changed_settings)
    self.assertEqual(self.main_settings['crop_to_background'].ui_visible, False)
    
    square_bracketed_mode.value = square_bracketed_mode.options['ignore_other']
    changed_settings = self.main_settings['square_bracketed_mode'].streamline()
    self.assertTrue(self.main_settings['remove_square_brackets'] in changed_settings)
    self.assertEqual(self.main_settings['remove_square_brackets'].ui_visible, True)
    self.assertTrue(self.main_settings['crop_to_background'] in changed_settings)
    self.assertEqual(self.main_settings['crop_to_background'].ui_visible, False)
  
  def test_streamline_merge_layer_groups(self):
    merge_layer_groups = self.main_settings['merge_layer_groups']
    
    merge_layer_groups.value = True
    changed_settings = self.main_settings['merge_layer_groups'].streamline()
    self.assertTrue(self.main_settings['layer_groups_as_directories'] in changed_settings)
    self.assertEqual(self.main_settings['layer_groups_as_directories'].value, False)
    self.assertEqual(self.main_settings['layer_groups_as_directories'].ui_enabled, False)
    
    merge_layer_groups.value = False
    changed_settings = self.main_settings['merge_layer_groups'].streamline()
    self.assertTrue(self.main_settings['layer_groups_as_directories'] in changed_settings)
    self.assertEqual(self.main_settings['layer_groups_as_directories'].ui_enabled, True)
  
  def test_streamline_autocrop(self):
    autocrop = self.main_settings['autocrop']
    
    autocrop.value = True
    changed_settings = self.main_settings['autocrop'].streamline()
    self.assertTrue(self.main_settings['crop_to_background'] in changed_settings)
    self.assertTrue('ui_enabled' in changed_settings[self.main_settings['crop_to_background']])
    self.assertEqual(self.main_settings['crop_to_background'].ui_enabled, True)
    
    autocrop.value = False
    changed_settings = self.main_settings['autocrop'].streamline()
    self.assertTrue(self.main_settings['crop_to_background'] in changed_settings)
    self.assertTrue('value' in changed_settings[self.main_settings['crop_to_background']])
    self.assertTrue('ui_enabled' in changed_settings[self.main_settings['crop_to_background']])
    self.assertEqual(self.main_settings['crop_to_background'].value, False)
    self.assertEqual(self.main_settings['crop_to_background'].ui_enabled, False)
  
  def test_streamline_all(self):
    changed_settings = self.main_settings.streamline(force=True)
    
    self.assertTrue(self.main_settings['crop_to_background'] in changed_settings)
    self.assertTrue('value' in changed_settings[self.main_settings['crop_to_background']])
    self.assertTrue('ui_enabled' in changed_settings[self.main_settings['crop_to_background']])
    self.assertEqual(self.main_settings['crop_to_background'].value, False)
    self.assertEqual(self.main_settings['crop_to_background'].ui_enabled, False)
    self.assertEqual(self.main_settings['crop_to_background'].ui_visible, False)
    