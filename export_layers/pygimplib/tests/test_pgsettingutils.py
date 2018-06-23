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

from .. import pgsetting
from .. import pgsettinggroup
from .. import pgsettingutils


class TestSettingAttributeGenerators(unittest.TestCase):
  
  def test_get_processed_display_name(self):
    self.assertEqual(
      pgsettingutils.get_processed_display_name(
        None, "my_setting_name"), "My setting name")
    self.assertEqual(
      pgsettingutils.get_processed_display_name(
        "My display name", "my_setting_name"), "My display name")
  
  def test_get_processed_description(self):
    self.assertEqual(
      pgsettingutils.get_processed_description(
        None, "My _Setting Name"), "My Setting Name")
    self.assertEqual(
      pgsettingutils.get_processed_description(
        "My description", "My _Setting Name"), "My description")


def _create_test_settings_for_path():
  setting = pgsetting.Setting("file_extension", "png")
  main_settings = pgsettinggroup.SettingGroup("main")
  advanced_settings = pgsettinggroup.SettingGroup("advanced")
  
  advanced_settings.add([setting])
  main_settings.add([advanced_settings])
  
  return setting, advanced_settings, main_settings


class TestSettingParentMixin(unittest.TestCase):
  
  def setUp(self):
    self.setting, self.advanced_settings, self.main_settings = (
      _create_test_settings_for_path())
  
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
    self.setting, self.advanced_settings, self.main_settings = (
      _create_test_settings_for_path())
  
  def test_get_path_no_parent(self):
    setting = pgsetting.Setting("file_extension", "png")
    self.assertEqual(pgsettingutils.get_setting_path(setting), "file_extension")
  
  def test_get_path(self):
    self.assertEqual(
      pgsettingutils.get_setting_path(self.setting), "main/advanced/file_extension")
    self.assertEqual(
      pgsettingutils.get_setting_path(self.advanced_settings), "main/advanced")
    self.assertEqual(
      pgsettingutils.get_setting_path(self.main_settings), "main")
  
  def test_get_path_with_relative_path_from_setting_group(self):
    self._test_get_path_with_relative_path(
      self.setting, self.main_settings, "advanced/file_extension")
    self._test_get_path_with_relative_path(
      self.setting, self.advanced_settings, "file_extension")
    self._test_get_path_with_relative_path(
      self.setting, self.setting, "")
    self._test_get_path_with_relative_path(
      self.advanced_settings, self.main_settings, "advanced")
    self._test_get_path_with_relative_path(
      self.advanced_settings, self.advanced_settings, "")
    self._test_get_path_with_relative_path(
      self.main_settings, self.main_settings, "")
  
  def test_get_path_with_relative_path_from_non_matching_setting_group(self):
    special_settings = pgsettinggroup.SettingGroup("special")
    
    self._test_get_path_with_relative_path(
      self.setting, special_settings, "main/advanced/file_extension")
    self._test_get_path_with_relative_path(
      self.advanced_settings, special_settings, "main/advanced")
    self._test_get_path_with_relative_path(
      self.main_settings, special_settings, "main")
  
  def _test_get_path_with_relative_path(
        self, setting, relative_path_setting_group, expected_path):
    self.assertEqual(
      pgsettingutils.get_setting_path(
        setting, relative_path_setting_group=relative_path_setting_group),
      expected_path)
