# -*- coding: utf-8 -*-
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

from .. import pgsetting
from .. import pgsettinggroup
from .. import pgsettingutils

#===============================================================================


class TestSettingAttributeGenerators(unittest.TestCase):
  
  def test_get_processed_display_name(self):
    self.assertEqual(
      pgsettingutils.get_processed_display_name(None, 'my_setting_name'), "My setting name")
    self.assertEqual(
      pgsettingutils.get_processed_display_name("My display name", 'my_setting_name'), "My display name")
  
  def test_get_processed_description(self):
    self.assertEqual(
      pgsettingutils.get_processed_description(None, 'My _Setting Name'), "My Setting Name")
    self.assertEqual(
      pgsettingutils.get_processed_description("My description", 'My _Setting Name'), "My description")


#===============================================================================


def _create_test_settings_for_path():
  setting = pgsetting.Setting("file_extension", "png")
  main_settings = pgsettinggroup.SettingGroup("main")
  advanced_settings = pgsettinggroup.SettingGroup("advanced")
  
  advanced_settings.add([setting])
  main_settings.add([advanced_settings])
  
  return setting, advanced_settings, main_settings


class TestSettingParentMixin(unittest.TestCase):
  
  def setUp(self):
    self.setting, self.advanced_settings, self.main_settings = _create_test_settings_for_path()
  
  def test_get_parent_empty(self):
    setting = pgsetting.Setting("file_extension", "png")
    
    self.assertEqual(setting.parent, None)
  
  def test_get_parent(self):
    self.assertEqual(self.setting.parent, self.advanced_settings)
    self.assertEqual(self.advanced_settings.parent, self.main_settings)
    self.assertEqual(self.main_settings.parent, None)
  
  def test_get_parents(self):
    self.assertEqual(self.setting.parents, [self.main_settings, self.advanced_settings])
    self.assertEqual(self.advanced_settings.parents, [self.main_settings])
    self.assertEqual(self.main_settings.parents, [])


class TestSettingPath(unittest.TestCase):
  
  def setUp(self):
    self.setting, self.advanced_settings, self.main_settings = _create_test_settings_for_path()
  
  def test_get_path_no_parent(self):
    setting = pgsetting.Setting("file_extension", "png")
    self.assertEqual(pgsettingutils.get_setting_path(setting), "file_extension")
  
  def test_get_path(self):
    self.assertEqual(pgsettingutils.get_setting_path(self.setting), "main/advanced/file_extension")
    self.assertEqual(pgsettingutils.get_setting_path(self.advanced_settings), "main/advanced")
    self.assertEqual(pgsettingutils.get_setting_path(self.main_settings), "main")
  
  def test_get_path_with_relative_path_from_setting_group(self):
    self._test_get_path_with_relative_path(self.setting, self.main_settings, "advanced/file_extension")
    self._test_get_path_with_relative_path(self.setting, self.advanced_settings, "file_extension")
    self._test_get_path_with_relative_path(self.setting, self.setting, "")
    self._test_get_path_with_relative_path(self.advanced_settings, self.main_settings, "advanced")
    self._test_get_path_with_relative_path(self.advanced_settings, self.advanced_settings, "")
    self._test_get_path_with_relative_path(self.main_settings, self.main_settings, "")
  
  def test_get_path_with_relative_path_from_non_matching_setting_group(self):
    special_settings = pgsettinggroup.SettingGroup("special")
    
    self._test_get_path_with_relative_path(self.setting, special_settings, "main/advanced/file_extension")
    self._test_get_path_with_relative_path(self.advanced_settings, special_settings, "main/advanced")
    self._test_get_path_with_relative_path(self.main_settings, special_settings, "main")
  
  def _test_get_path_with_relative_path(self, setting, relative_path_setting_group, expected_path):
    self.assertEqual(
      pgsettingutils.get_setting_path(setting, relative_path_setting_group=relative_path_setting_group),
      expected_path)
