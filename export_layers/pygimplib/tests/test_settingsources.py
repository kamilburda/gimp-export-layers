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

import mock

from . import stubs_gimp
from . import stubs_settinggroup
from .. import setting as pgsetting
from .. import settingsources as pgsettingsources
from .. import constants as pgconstants


@mock.patch(
  pgconstants.PYGIMPLIB_MODULE_PATH + ".settingsources.gimpshelf.shelf",
  new_callable=stubs_gimp.ShelfStub)
class TestSessionWideSettingSource(unittest.TestCase):
  
  @mock.patch(
    pgconstants.PYGIMPLIB_MODULE_PATH + ".settingsources.gimpshelf.shelf",
    new=stubs_gimp.ShelfStub())
  def setUp(self):
    self.source_name = "test_settings"
    self.source = pgsettingsources.SessionWideSettingSource(self.source_name)
    self.settings = stubs_settinggroup.create_test_settings()
  
  def test_write(self, mock_session_source):
    self.settings["file_extension"].set_value("png")
    self.settings["only_visible_layers"].set_value(True)
    
    self.source.write(self.settings)
    
    self.assertEqual(
      pgsettingsources.gimpshelf.shelf[self.source_name][
        self.settings["file_extension"].get_path("root")],
      "png")
    self.assertEqual(
      pgsettingsources.gimpshelf.shelf[self.source_name][
        self.settings["only_visible_layers"].get_path("root")],
      True)
  
  def test_write_multiple_settings_separately(self, mock_session_source):
    self.settings["file_extension"].set_value("jpg")
    self.source.write([self.settings["file_extension"]])
    self.settings["only_visible_layers"].set_value(True)
    
    self.source.write([self.settings["only_visible_layers"]])
    self.source.read([self.settings["file_extension"]])
    self.source.read([self.settings["only_visible_layers"]])
    
    self.assertEqual(self.settings["file_extension"].value, "jpg")
    self.assertEqual(self.settings["only_visible_layers"].value, True)
  
  def test_read(self, mock_session_source):
    data = {}
    data[self.settings["file_extension"].get_path("root")] = "png"
    data[self.settings["only_visible_layers"].get_path("root")] = True
    pgsettingsources.gimpshelf.shelf[self.source_name] = data
    
    self.source.read(
      [self.settings["file_extension"], self.settings["only_visible_layers"]])
    
    self.assertEqual(self.settings["file_extension"].value, "png")
    self.assertEqual(self.settings["only_visible_layers"].value, True)
  
  def test_read_settings_not_found(self, mock_session_source):
    self.source.write([self.settings["file_extension"]])
    with self.assertRaises(pgsettingsources.SettingsNotFoundInSourceError):
      self.source.read(self.settings)
  
  def test_read_settings_invalid_format(self, mock_session_source):
    with mock.patch(
           pgconstants.PYGIMPLIB_MODULE_PATH
           + ".settingsources.gimpshelf.shelf") as temp_mock_session_source:
      temp_mock_session_source.__getitem__.side_effect = Exception
      
      with self.assertRaises(pgsettingsources.SettingSourceInvalidFormatError):
        self.source.read(self.settings)
  
  def test_read_invalid_setting_value_set_to_default_value(self, mock_session_source):
    setting_with_invalid_value = pgsetting.IntSetting("int", default_value=-1)
    self.source.write([setting_with_invalid_value])
    
    setting = pgsetting.IntSetting("int", default_value=2, min_value=0)
    self.source.read([setting])
    
    self.assertEqual(setting.value, setting.default_value)
  
  def test_clear(self, mock_session_source):
    self.source.write(self.settings)
    self.source.clear()
    
    with self.assertRaises(pgsettingsources.SettingSourceNotFoundError):
      self.source.read(self.settings)
  
  def test_has_data_with_no_data(self, mock_session_source):
    self.assertFalse(self.source.has_data())
  
  def test_has_data_with_data(self, mock_session_source):
    self.source.write([self.settings["file_extension"]])
    self.assertTrue(self.source.has_data())


@mock.patch(
  pgconstants.PYGIMPLIB_MODULE_PATH + ".settingsources.gimp",
  new_callable=stubs_gimp.GimpModuleStub)
class TestPersistentSettingSource(unittest.TestCase):
  
  @mock.patch(
    pgconstants.PYGIMPLIB_MODULE_PATH + ".settingsources.gimp.directory",
    new="gimp_directory")
  def setUp(self):
    self.source_name = "test_settings"
    self.source = pgsettingsources.PersistentSettingSource(self.source_name)
    self.settings = stubs_settinggroup.create_test_settings()
  
  def test_write_read(self, mock_persistent_source):
    self.settings["file_extension"].set_value("jpg")
    self.settings["only_visible_layers"].set_value(True)
    
    self.source.write(self.settings)
    self.source.read(self.settings)
    
    self.assertEqual(self.settings["file_extension"].value, "jpg")
    self.assertEqual(self.settings["only_visible_layers"].value, True)
  
  def test_write_multiple_settings_separately(self, mock_persistent_source):
    self.settings["file_extension"].set_value("jpg")
    self.source.write([self.settings["file_extension"]])
    self.settings["only_visible_layers"].set_value(True)
    
    self.source.write([self.settings["only_visible_layers"]])
    self.source.read([self.settings["file_extension"]])
    self.source.read([self.settings["only_visible_layers"]])
    
    self.assertEqual(self.settings["file_extension"].value, "jpg")
    self.assertEqual(self.settings["only_visible_layers"].value, True)
  
  def test_write_read_same_setting_name_in_different_groups(self, mock_persistent_source):
    settings = stubs_settinggroup.create_test_settings_hierarchical()
    file_extension_advanced_setting = pgsetting.FileExtensionSetting(
      "file_extension", default_value="png")
    settings["advanced"].add([file_extension_advanced_setting])
    
    self.source.write(settings.walk())
    self.source.read(settings.walk())
    
    self.assertEqual(settings["main/file_extension"].value, "bmp")
    self.assertEqual(settings["advanced/file_extension"].value, "png")
  
  def test_read_source_not_found(self, mock_persistent_source):
    with self.assertRaises(pgsettingsources.SettingSourceNotFoundError):
      self.source.read(self.settings)
  
  def test_read_settings_not_found(self, mock_persistent_source):
    self.source.write([self.settings["file_extension"]])
    with self.assertRaises(pgsettingsources.SettingsNotFoundInSourceError):
      self.source.read(self.settings)
  
  def test_read_settings_invalid_format(self, mock_persistent_source):
    self.source.write(self.settings)
    
    # Simulate formatting error
    parasite = pgsettingsources.gimp.parasite_find(self.source_name)
    parasite.data = parasite.data[:-1]
    pgsettingsources.gimp.parasite_attach(parasite)
    
    with self.assertRaises(pgsettingsources.SettingSourceInvalidFormatError):
      self.source.read(self.settings)
  
  def test_read_invalid_setting_value_set_to_default_value(self, mock_persistent_source):
    setting_with_invalid_value = pgsetting.IntSetting("int", default_value=-1)
    self.source.write([setting_with_invalid_value])
    
    setting = pgsetting.IntSetting("int", default_value=2, min_value=0)
    self.source.read([setting])
    
    self.assertEqual(setting.value, setting.default_value)
  
  def test_clear(self, mock_persistent_source):
    self.source.write(self.settings)
    self.source.clear()
    
    with self.assertRaises(pgsettingsources.SettingSourceNotFoundError):
      self.source.read(self.settings)
  
  def test_has_data_with_no_data(self, mock_persistent_source):
    self.assertFalse(self.source.has_data())
  
  def test_has_data_with_data(self, mock_persistent_source):
    self.source.write([self.settings["file_extension"]])
    self.assertTrue(self.source.has_data())


@mock.patch(
  pgconstants.PYGIMPLIB_MODULE_PATH + ".settingsources.gimpshelf.shelf",
  new_callable=stubs_gimp.ShelfStub)
@mock.patch(
  pgconstants.PYGIMPLIB_MODULE_PATH + ".settingsources.gimp",
  new_callable=stubs_gimp.GimpModuleStub)
class TestSettingSourceReadWriteDict(unittest.TestCase):
  
  @mock.patch(
    pgconstants.PYGIMPLIB_MODULE_PATH + ".settingsources.gimp.directory",
    new="gimp_directory")
  def setUp(self):
    self.source_name = "test_settings"
    self.source_session = (
      pgsettingsources.SessionWideSettingSource(self.source_name))
    self.source_persistent = pgsettingsources.PersistentSettingSource(self.source_name)
    self.settings = stubs_settinggroup.create_test_settings()
  
  def test_read_dict(self, mock_persistent_source, mock_session_source):
    for source in [self.source_session, self.source_persistent]:
      self._test_read_dict(source)
  
  def test_read_dict_nonexistent_source(
        self, mock_persistent_source, mock_session_source):
    for source in [self.source_session, self.source_persistent]:
      self._test_read_dict_nonexistent_source(source)
  
  def test_write_dict(self, mock_persistent_source, mock_session_source):
    for source in [self.source_session, self.source_persistent]:
      self._test_write_dict(source)
  
  def _test_read_dict(self, source):
    source.write(self.settings)
    
    data_dict = source.read_dict()
    self.assertDictEqual(
      data_dict,
      {
        "file_extension": self.settings["file_extension"].value,
        "only_visible_layers": self.settings["only_visible_layers"].value,
        "overwrite_mode": self.settings["overwrite_mode"].value,
      })
  
  def _test_read_dict_nonexistent_source(self, source):
    self.assertIsNone(source.read_dict())
  
  def _test_write_dict(self, source):
    data_dict = {
      "file_extension": self.settings["file_extension"].default_value,
      "only_visible_layers": self.settings["only_visible_layers"].default_value,
    }
    
    self.settings["file_extension"].set_value("jpg")
    self.settings["only_visible_layers"].set_value(True)
    
    source.write_dict(data_dict)
    
    source.read(
      [self.settings["file_extension"], self.settings["only_visible_layers"]])
    
    self.assertEqual(
      self.settings["file_extension"].value,
      self.settings["file_extension"].default_value)
    self.assertEqual(
      self.settings["only_visible_layers"].value,
      self.settings["only_visible_layers"].default_value)
