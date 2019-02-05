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

from ... import constants as pgconstants

from ...setting import persistor as settingpersistor
from ...setting import sources as settingsources

from .. import stubs_gimp
from . import stubs_group


@mock.patch(
  pgconstants.PYGIMPLIB_MODULE_PATH + ".setting.sources.gimpshelf.shelf",
  new_callable=stubs_gimp.ShelfStub)
@mock.patch(
  pgconstants.PYGIMPLIB_MODULE_PATH + ".setting.sources.gimp",
  new_callable=stubs_gimp.GimpModuleStub)
class TestSettingPersistor(unittest.TestCase):
  
  @mock.patch(
    pgconstants.PYGIMPLIB_MODULE_PATH + ".setting.sources.gimpshelf.shelf",
    new=stubs_gimp.ShelfStub())
  @mock.patch(
    pgconstants.PYGIMPLIB_MODULE_PATH + ".setting.sources.gimp.directory",
    new="gimp_directory")
  def setUp(self):
    self.settings = stubs_group.create_test_settings()
    self.session_source = settingsources.SessionWideSettingSource("")
    self.persistent_source = settingsources.PersistentSettingSource("")
  
  def test_load_save(self, mock_persistent_source, mock_session_source):
    self.settings["file_extension"].set_value("png")
    self.settings["only_visible_layers"].set_value(True)
    
    status, unused_ = settingpersistor.SettingPersistor.save(
      [self.settings], [self.session_source, self.persistent_source])
    self.assertEqual(status, settingpersistor.SettingPersistor.SUCCESS)
    
    self.settings["file_extension"].set_value("jpg")
    self.settings["only_visible_layers"].set_value(False)
    
    status, unused_ = settingpersistor.SettingPersistor.load(
      [self.settings], [self.session_source, self.persistent_source])
    self.assertEqual(status, settingpersistor.SettingPersistor.SUCCESS)
    self.assertEqual(self.settings["file_extension"].value, "png")
    self.assertEqual(self.settings["only_visible_layers"].value, True)
  
  def test_load_combine_settings_from_multiple_sources(
        self, mock_persistent_source, mock_session_source):
    self.settings["file_extension"].set_value("png")
    self.settings["only_visible_layers"].set_value(True)
    self.session_source.write([self.settings["file_extension"]])
    self.settings["file_extension"].set_value("jpg")
    self.persistent_source.write(
      [self.settings["only_visible_layers"], self.settings["file_extension"]])
    self.settings["file_extension"].set_value("gif")
    self.settings["only_visible_layers"].set_value(False)
    
    settingpersistor.SettingPersistor.load(
      [self.settings], [self.session_source, self.persistent_source])
    
    self.assertEqual(self.settings["file_extension"].value, "png")
    self.assertEqual(self.settings["only_visible_layers"].value, True)
    
    for setting in self.settings:
      if setting not in [
           self.settings["file_extension"], self.settings["only_visible_layers"]]:
        self.assertEqual(setting.value, setting.default_value)
  
  def test_load_setting_groups(self, mock_persistent_source, mock_session_source):
    settings = stubs_group.create_test_settings_hierarchical()
    
    settings["main/file_extension"].set_value("png")
    settings["advanced/only_visible_layers"].set_value(True)
    self.session_source.write(settings.walk())
    settings["main/file_extension"].set_value("gif")
    settings["advanced/only_visible_layers"].set_value(False)
    
    settingpersistor.SettingPersistor.load([settings], [self.session_source])
    
    self.assertEqual(settings["main/file_extension"].value, "png")
    self.assertEqual(settings["advanced/only_visible_layers"].value, True)
  
  def test_load_settings_source_not_found(
        self, mock_persistent_source, mock_session_source):
    status, unused_ = settingpersistor.SettingPersistor.load(
      [self.settings], [self.session_source, self.persistent_source])
    self.assertEqual(status, settingpersistor.SettingPersistor.NOT_ALL_SETTINGS_FOUND)
  
  def test_load_settings_not_found(self, mock_persistent_source, mock_session_source):
    self.session_source.write([self.settings["only_visible_layers"]])
    self.persistent_source.write(
      [self.settings["file_extension"], self.settings["only_visible_layers"]])
    
    status, unused_ = settingpersistor.SettingPersistor.load(
      [self.settings["overwrite_mode"]], [self.session_source, self.persistent_source])
    self.assertEqual(status, settingpersistor.SettingPersistor.NOT_ALL_SETTINGS_FOUND)
  
  def test_load_read_fail(self, mock_persistent_source, mock_session_source):
    self.persistent_source.write(self.settings)
    
    # Simulate formatting error
    parasite = settingsources.gimp.parasite_find(self.persistent_source.source_name)
    parasite.data = parasite.data[:-1]
    settingsources.gimp.parasite_attach(parasite)
    
    status, unused_ = settingpersistor.SettingPersistor.load(
      [self.settings], [self.session_source, self.persistent_source])
    self.assertEqual(status, settingpersistor.SettingPersistor.READ_FAIL)
  
  def test_load_write_fail(self, mock_persistent_source, mock_session_source):
    with mock.patch(
           pgconstants.PYGIMPLIB_MODULE_PATH
           + ".setting.sources.gimp") as temp_mock_persistent_source:
      temp_mock_persistent_source.parasite_find.side_effect = (
        settingsources.SettingSourceWriteError)
      status, unused_ = settingpersistor.SettingPersistor.save(
        [self.settings], [self.session_source, self.persistent_source])
    
    self.assertEqual(status, settingpersistor.SettingPersistor.WRITE_FAIL)
