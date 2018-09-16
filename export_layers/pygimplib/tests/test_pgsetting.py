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

"""
This module tests the `pgsetting` and `pgsettingpresenter` modules.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import os
import unittest

import gimpenums

import mock
import parameterized

from . import stubs_gimp
from . import stubs_pgsetting
from .. import pgconstants
from .. import pgpath
from .. import pgsetting
from .. import pgsettingpersistor
from .. import pgsettingsources


class TestSetting(unittest.TestCase):
  
  def setUp(self):
    self.setting = stubs_pgsetting.SettingStub("file_extension", "png")
  
  def test_str(self):
    self.assertEqual(str(self.setting), "<SettingStub 'file_extension'>")
  
  def test_invalid_setting_name(self):
    with self.assertRaises(ValueError):
      stubs_pgsetting.SettingStub("file/extension", "png")
    
    with self.assertRaises(ValueError):
      stubs_pgsetting.SettingStub("file.extension", "png")
  
  def test_invalid_default_value(self):
    with self.assertRaises(pgsetting.SettingDefaultValueError):
      stubs_pgsetting.SettingStub("setting", None)
  
  def test_empty_value_as_default_value(self):
    try:
      stubs_pgsetting.SettingStub("setting", "")
    except pgsetting.SettingDefaultValueError:
      self.fail(
        "SettingDefaultValueError should not be raised - default value is an empty value")
  
  def test_assign_empty_value_not_allowed(self):
    with self.assertRaises(pgsetting.SettingValueError):
      self.setting.set_value("")
  
  def test_assign_empty_value_allowed(self):
    setting = stubs_pgsetting.SettingStub("setting", "", allow_empty_values=True)
    setting.set_value("")
    self.assertEqual(setting.value, "")
  
  def test_value_invalid_assignment_operation(self):
    with self.assertRaises(AttributeError):
      self.setting.value = "jpg"
  
  def test_get_generated_display_name(self):
    self.assertEqual(self.setting.display_name, "File extension")
  
  def test_get_generated_description(self):
    setting = stubs_pgsetting.SettingStub(
      "setting", "default value", display_name="_Setting")
    self.assertEqual(setting.display_name, "_Setting")
    self.assertEqual(setting.description, "Setting")
  
  def test_get_custom_display_name_and_description(self):
    setting = stubs_pgsetting.SettingStub(
      "setting", "default value", display_name="_Setting", description="My description")
    self.assertEqual(setting.display_name, "_Setting")
    self.assertEqual(setting.description, "My description")
  
  def test_custom_error_messages(self):
    setting = stubs_pgsetting.SettingStub("setting", "")
    
    setting_with_custom_error_messages = stubs_pgsetting.SettingStub(
      "setting", "", error_messages={
        "invalid_value": "this should override the original error message",
        "custom_message": "custom message"})
    self.assertIn("custom_message", setting_with_custom_error_messages.error_messages)
    self.assertNotEqual(
      setting.error_messages["invalid_value"],
      setting_with_custom_error_messages.error_messages["invalid_value"])
  
  def test_pdb_type_automatic_is_registrable(self):
    setting = stubs_pgsetting.SettingRegistrableToPdbStub(
      "file_extension", "png", pdb_type=pgsetting.SettingPdbTypes.string)
    self.assertTrue(setting.can_be_registered_to_pdb())
  
  def test_pdb_type_automatic_is_not_registrable(self):
    self.assertFalse(self.setting.can_be_registered_to_pdb())
  
  def test_invalid_pdb_type(self):
    with self.assertRaises(ValueError):
      stubs_pgsetting.SettingStub(
        "file_extension", "png", pdb_type=pgsetting.SettingPdbTypes.string)
  
  def test_get_pdb_param_for_registrable_setting(self):
    setting = stubs_pgsetting.SettingRegistrableToPdbStub("file_extension", "png")
    self.assertEqual(
      setting.get_pdb_param(),
      [(pgsetting.SettingPdbTypes.string, b"file_extension", b"File extension")])
  
  def test_get_pdb_param_for_nonregistrable_setting(self):
    self.assertEqual(self.setting.get_pdb_param(), None)
  
  def test_reset(self):
    self.setting.set_value("jpg")
    self.setting.reset()
    self.assertEqual(self.setting.value, "png")
  
  def test_reset_with_container_as_default_value(self):
    setting = stubs_pgsetting.SettingStub("image_IDs_and_directories", {})
    setting.value[1] = "image_directory"
    
    setting.reset()
    self.assertEqual(setting.value, {})
    
    setting.value[2] = "another_image_directory"
    
    setting.reset()
    self.assertEqual(setting.value, {})
  
  @parameterized.parameterized.expand([
    ("default_source",
     ["default"], None, True, ["default"]),
    
    ("no_default_source",
     None, None, True, []),
    
    ("parameter_not_in_empty_default_sources",
     None, ["param"], True, []),
    
    ("parameter_not_in_default_sources",
     ["default"], ["param"], True, []),
    
    ("parameter_matching_a_default_source",
     ["one", "two"], ["one"], True, ["one"]),
  ])
  @mock.patch(
    pgconstants.PYGIMPLIB_MODULE_PATH + ".pgsettingpersistor.SettingPersistor.load")
  def test_load(
        self,
        test_case_name_suffix,
        sources_for_setting,
        sources_as_parameters,
        was_save_called,
        sources_in_call_args,
        mock_setting_persistor_load):
    self._test_load_save(
      sources_for_setting,
      sources_as_parameters,
      was_save_called,
      sources_in_call_args,
      mock_setting_persistor_load,
      "load")
  
  @parameterized.parameterized.expand([
    ("default_source",
     ["default"], None, True, ["default"]),
    
    ("no_default_source",
     None, None, True, []),
    
    ("parameter_not_in_empty_default_sources",
     None, ["param"], True, []),
    
    ("parameter_not_in_default_sources",
     ["default"], ["param"], True, []),
    
    ("parameter_matching_a_default_source",
     ["one", "two"], ["one"], True, ["one"]),
  ])
  @mock.patch(
    pgconstants.PYGIMPLIB_MODULE_PATH + ".pgsettingpersistor.SettingPersistor.save")
  def test_save(
        self,
        test_case_name_suffix,
        sources_for_setting,
        sources_as_parameters,
        was_save_called,
        sources_in_call_args,
        mock_setting_persistor_save):
    self._test_load_save(
      sources_for_setting,
      sources_as_parameters,
      was_save_called,
      sources_in_call_args,
      mock_setting_persistor_save,
      "save")
  
  def _test_load_save(
        self,
        sources_for_setting,
        sources_as_parameters,
        was_save_called,
        sources_in_call_args,
        mock_load_save,
        load_save_func_name):
    setting = stubs_pgsetting.SettingStub(
      "image_IDs_and_directories", {}, setting_sources=sources_for_setting)
    getattr(setting, load_save_func_name)(sources_as_parameters)
    
    if was_save_called:
      self.assertTrue(mock_load_save.called)
    else:
      self.assertFalse(mock_load_save.called)
    
    sources = (
      sources_for_setting if sources_for_setting is not None else []
      + sources_as_parameters if sources_as_parameters is not None else [])
    
    for source in sources:
      call_args = (
        mock_load_save.call_args[0][1]
        if mock_load_save.call_args[0][1] is not None else [])
      
      if source in sources_in_call_args:
        self.assertIn(source, call_args)
      else:
        self.assertNotIn(source, call_args)
  

class TestSettingEvents(unittest.TestCase):
  
  def setUp(self):
    self.setting = stubs_pgsetting.SettingStub("file_extension", "png")
    self.only_visible_layers = pgsetting.BoolSetting("only_visible_layers", False)
  
  def test_connect_value_changed_event(self):
    self.setting.connect_event(
      "value-changed",
      stubs_pgsetting.on_file_extension_changed,
      self.only_visible_layers)
    
    self.setting.set_value("jpg")
    self.assertEqual(self.only_visible_layers.value, True)
    self.assertFalse(self.only_visible_layers.gui.get_sensitive())
  
  def test_connect_value_changed_event_nested(self):
    self.setting.connect_event(
      "value-changed",
      stubs_pgsetting.on_file_extension_changed,
      self.only_visible_layers)
    
    use_image_size = pgsetting.BoolSetting("use_image_size", False)
    use_image_size.connect_event(
      "value-changed", stubs_pgsetting.on_use_image_size_changed, self.setting)
    
    use_image_size.set_value(True)
    
    self.assertEqual(self.setting.value, "jpg")
    self.assertEqual(self.only_visible_layers.value, True)
    self.assertFalse(self.only_visible_layers.gui.get_sensitive())
  
  def test_reset_triggers_value_changed_event(self):
    self.setting.connect_event(
      "value-changed",
      stubs_pgsetting.on_file_extension_changed,
      self.only_visible_layers)
    
    self.setting.set_value("jpg")
    self.setting.reset()
    self.assertEqual(
      self.only_visible_layers.value, self.only_visible_layers.default_value)
    self.assertTrue(self.only_visible_layers.gui.get_sensitive())


@mock.patch(
  pgconstants.PYGIMPLIB_MODULE_PATH + ".pgsettingsources.gimpshelf.shelf",
  new_callable=stubs_gimp.ShelfStub)
class TestSettingLoadSaveEvents(unittest.TestCase):
  
  @mock.patch(
    pgconstants.PYGIMPLIB_MODULE_PATH + ".pgsettingsources.gimpshelf.shelf",
    new=stubs_gimp.ShelfStub())
  def setUp(self):
    self.setting = stubs_pgsetting.SettingWithGuiStub("file_extension", "png")
    self.only_visible_layers = pgsetting.BoolSetting("only_visible_layers", False)
    self.session_source = pgsettingsources.SessionPersistentSettingSource("")
  
  def test_before_load_event(self, mock_session_source):
    pgsettingpersistor.SettingPersistor.save(
      [self.setting, self.only_visible_layers], [self.session_source])
    self.setting.set_value("gif")
    
    self.setting.connect_event(
      "before-load", stubs_pgsetting.on_file_extension_changed, self.only_visible_layers)
    pgsettingpersistor.SettingPersistor.load([self.setting], [self.session_source])
    
    self.assertEqual(self.setting.value, "png")
    self.assertEqual(self.only_visible_layers.value, True)
  
  def test_after_load_event(self, mock_session_source):
    self.only_visible_layers.set_value(True)
    pgsettingpersistor.SettingPersistor.save(
      [self.setting, self.only_visible_layers], [self.session_source])
    
    self.setting.connect_event(
      "after-load", stubs_pgsetting.on_file_extension_changed, self.only_visible_layers)
    pgsettingpersistor.SettingPersistor.load([self.setting], [self.session_source])
    
    self.assertEqual(self.setting.value, "png")
    self.assertEqual(self.only_visible_layers.value, False)
  
  def test_after_load_event_not_all_settings_found_invoke_for_all_settings(
        self, mock_session_source):
    self.setting.set_value("gif")
    pgsettingpersistor.SettingPersistor.save([self.setting], [self.session_source])
    
    self.setting.connect_event(
      "after-load", stubs_pgsetting.on_file_extension_changed, self.only_visible_layers)
    pgsettingpersistor.SettingPersistor.load(
      [self.setting, self.only_visible_layers], [self.session_source])
    
    self.assertEqual(self.setting.value, "gif")
    self.assertEqual(self.only_visible_layers.value, True)
  
  def test_after_load_event_read_fail(self, mock_session_source):
    self.only_visible_layers.set_value(True)
    pgsettingpersistor.SettingPersistor.save(
      [self.setting, self.only_visible_layers], [self.session_source])
    
    self.setting.connect_event(
      "after-load", stubs_pgsetting.on_file_extension_changed, self.only_visible_layers)
    
    with mock.patch(
           pgconstants.PYGIMPLIB_MODULE_PATH
           + ".pgsettingsources.gimpshelf.shelf") as temp_mock_session_source:
      temp_mock_session_source.__getitem__.side_effect = (
        pgsettingsources.SettingSourceReadError)
      pgsettingpersistor.SettingPersistor.load([self.setting], [self.session_source])
    
    self.assertEqual(self.setting.value, "png")
    self.assertEqual(self.only_visible_layers.value, True)
  
  def test_before_save_event(self, mock_session_source):
    self.setting.set_value("gif")
    
    self.setting.connect_event(
      "before-save", stubs_pgsetting.on_file_extension_changed, self.only_visible_layers)
    pgsettingpersistor.SettingPersistor.save(
      [self.setting, self.only_visible_layers], [self.session_source])
    
    self.assertEqual(self.setting.value, "gif")
    self.assertEqual(self.only_visible_layers.value, True)
    
    pgsettingpersistor.SettingPersistor.load(
      [self.setting, self.only_visible_layers], [self.session_source])
    
    self.assertEqual(self.setting.value, "gif")
    self.assertEqual(self.only_visible_layers.value, True)
  
  def test_after_save_event(self, mock_session_source):
    self.setting.set_value("gif")
    
    self.setting.connect_event(
      "after-save", stubs_pgsetting.on_file_extension_changed, self.only_visible_layers)
    pgsettingpersistor.SettingPersistor.save(
      [self.setting, self.only_visible_layers], [self.session_source])
    
    self.assertEqual(self.setting.value, "gif")
    self.assertEqual(self.only_visible_layers.value, True)
    
    pgsettingpersistor.SettingPersistor.load(
      [self.setting, self.only_visible_layers], [self.session_source])
    
    self.assertEqual(self.setting.value, "gif")
    self.assertEqual(self.only_visible_layers.value, False)
  
  def test_after_save_event_write_fail(self, mock_session_source):
    self.setting.set_value("gif")
    self.setting.connect_event(
      "after-save", stubs_pgsetting.on_file_extension_changed, self.only_visible_layers)
    
    with mock.patch(
           pgconstants.PYGIMPLIB_MODULE_PATH
           + ".pgsettingsources.gimpshelf.shelf") as temp_mock_session_source:
      temp_mock_session_source.__setitem__.side_effect = (
        pgsettingsources.SettingSourceWriteError)
      pgsettingpersistor.SettingPersistor.save([self.setting], [self.session_source])
    
    self.assertEqual(self.only_visible_layers.value, False)


class TestSettingGui(unittest.TestCase):
  
  def setUp(self):
    self.setting = stubs_pgsetting.SettingWithGuiStub("file_extension", "png")
    self.widget = stubs_pgsetting.GuiWidgetStub("")
  
  def test_set_gui_updates_gui_value(self):
    self.setting.set_gui(stubs_pgsetting.SettingPresenterStub, self.widget)
    self.assertEqual(self.widget.value, "png")
  
  def test_setting_set_value_updates_gui(self):
    self.setting.set_gui(stubs_pgsetting.SettingPresenterStub, self.widget)
    self.setting.set_value("gif")
    self.assertEqual(self.widget.value, "gif")
  
  def test_set_gui_preserves_gui_state(self):
    self.setting.gui.set_sensitive(False)
    self.setting.gui.set_visible(False)
    self.setting.set_value("gif")
    
    self.setting.set_gui(stubs_pgsetting.SettingPresenterStub, self.widget)
    
    self.assertFalse(self.setting.gui.get_sensitive())
    self.assertFalse(self.setting.gui.get_visible())
    self.assertEqual(self.widget.value, "gif")
  
  def test_setting_gui_type(self):
    setting = stubs_pgsetting.SettingWithGuiStub(
      "only_visible_layers", False, gui_type=stubs_pgsetting.CheckButtonPresenterStub)
    setting.set_gui()
    self.assertIs(type(setting.gui), stubs_pgsetting.CheckButtonPresenterStub)
    self.assertIs(type(setting.gui.element), stubs_pgsetting.CheckButtonStub)
  
  def test_setting_different_gui_type(self):
    setting = stubs_pgsetting.SettingWithGuiStub(
      "only_visible_layers", False, gui_type=stubs_pgsetting.SettingPresenterStub)
    setting.set_gui()
    self.assertIs(type(setting.gui), stubs_pgsetting.SettingPresenterStub)
    self.assertIs(type(setting.gui.element), stubs_pgsetting.GuiWidgetStub)
  
  def test_setting_invalid_gui_type_raise_error(self):
    with self.assertRaises(ValueError):
      stubs_pgsetting.SettingWithGuiStub(
        "only_visible_layers",
        False,
        gui_type=stubs_pgsetting.YesNoToggleButtonPresenterStub)
  
  def test_setting_null_gui_type(self):
    setting = stubs_pgsetting.SettingWithGuiStub(
      "only_visible_layers", False, gui_type=pgsetting.SettingGuiTypes.none)
    setting.set_gui()
    self.assertIs(type(setting.gui), pgsetting.SettingGuiTypes.none)
  
  def test_set_gui_gui_type_is_specified_gui_element_is_none_raise_error(self):
    setting = stubs_pgsetting.SettingWithGuiStub("only_visible_layers", False)
    with self.assertRaises(ValueError):
      setting.set_gui(gui_type=stubs_pgsetting.CheckButtonPresenterStub)
  
  def test_set_gui_gui_type_is_none_gui_element_is_specified_raise_error(self):
    setting = stubs_pgsetting.SettingWithGuiStub("only_visible_layers", False)
    with self.assertRaises(ValueError):
      setting.set_gui(gui_element=stubs_pgsetting.GuiWidgetStub)
  
  def test_set_gui_manual_gui_type(self):
    setting = stubs_pgsetting.SettingWithGuiStub("only_visible_layers", False)
    setting.set_gui(
      gui_type=stubs_pgsetting.YesNoToggleButtonPresenterStub,
      gui_element=stubs_pgsetting.GuiWidgetStub(None))
    self.assertIs(type(setting.gui), stubs_pgsetting.YesNoToggleButtonPresenterStub)
    self.assertIs(type(setting.gui.element), stubs_pgsetting.GuiWidgetStub)
  
  def test_set_gui_gui_element_is_none_presenter_has_no_wrapper_raise_error(self):
    setting = stubs_pgsetting.SettingWithGuiStub(
      "only_visible_layers",
      False,
      gui_type=stubs_pgsetting.SettingPresenterWithoutGuiElementCreationStub)
    with self.assertRaises(ValueError):
      setting.set_gui()
  
  def test_update_setting_value_manually(self):
    self.setting.set_gui(stubs_pgsetting.SettingPresenterStub, self.widget)
    self.widget.set_value("jpg")
    self.assertEqual(self.setting.value, "png")
    
    self.setting.gui.update_setting_value()
    self.assertEqual(self.setting.value, "jpg")
  
  def test_update_setting_value_automatically(self):
    self.setting.set_gui(
      stubs_pgsetting.SettingPresenterWithValueChangedSignalStub, self.widget)
    self.widget.set_value("jpg")
    self.assertEqual(self.setting.value, "jpg")
  
  def test_update_setting_value_triggers_value_changed_event(self):
    self.setting.set_gui(
      stubs_pgsetting.SettingPresenterWithValueChangedSignalStub, self.widget)
    
    only_visible_layers = pgsetting.BoolSetting("only_visible_layers", False)
    self.setting.connect_event(
      "value-changed", stubs_pgsetting.on_file_extension_changed, only_visible_layers)
    
    self.widget.set_value("jpg")
    self.assertEqual(self.setting.value, "jpg")
    self.assertEqual(only_visible_layers.value, True)
    self.assertFalse(only_visible_layers.gui.get_sensitive())
  
  def test_reset_updates_gui(self):
    self.setting.set_gui(stubs_pgsetting.SettingPresenterStub, self.widget)
    self.setting.set_value("jpg")
    self.setting.reset()
    self.assertEqual(self.widget.value, "png")
  
  def test_update_setting_value_manually_for_automatically_updated_settings_when_reset_to_disallowed_empty_value(self):
    setting = stubs_pgsetting.SettingWithGuiStub("file_extension", "")
    setting.set_gui(
      stubs_pgsetting.SettingPresenterWithValueChangedSignalStub, self.widget)
    setting.set_value("jpg")
    setting.reset()
    
    with self.assertRaises(pgsetting.SettingValueError):
      # Raise error because setting is reset to an empty value, while empty
      # values are disallowed (`allow_empty_values` is False).
      setting.gui.update_setting_value()
  
  def test_null_setting_presenter_has_automatic_gui(self):
    setting = stubs_pgsetting.SettingWithGuiStub("file_extension", "")
    self.assertTrue(setting.gui.gui_update_enabled)
  
  def test_manual_gui_update_enabled_is_false(self):
    setting = stubs_pgsetting.SettingWithGuiStub("file_extension", "")
    setting.set_gui(stubs_pgsetting.SettingPresenterStub, self.widget)
    self.assertFalse(setting.gui.gui_update_enabled)
  
  def test_automatic_gui_update_enabled_is_true(self):
    setting = stubs_pgsetting.SettingWithGuiStub("file_extension", "")
    setting.set_gui(
      stubs_pgsetting.SettingPresenterWithValueChangedSignalStub, self.widget)
    self.assertTrue(setting.gui.gui_update_enabled)
    
    self.widget.set_value("png")
    self.assertEqual(setting.value, "png")
  
  def test_automatic_gui_update_enabled_is_false(self):
    setting = stubs_pgsetting.SettingWithGuiStub(
      "file_extension", "", auto_update_gui_to_setting=False)
    setting.set_gui(
      stubs_pgsetting.SettingPresenterWithValueChangedSignalStub, self.widget)
    self.assertFalse(setting.gui.gui_update_enabled)
    
    self.widget.set_value("png")
    self.assertEqual(setting.value, "")
  
  def test_set_gui_disable_automatic_setting_value_update(self):
    setting = stubs_pgsetting.SettingWithGuiStub("file_extension", "")
    setting.set_gui(
      stubs_pgsetting.SettingPresenterWithValueChangedSignalStub,
      self.widget, auto_update_gui_to_setting=False)
    self.assertFalse(setting.gui.gui_update_enabled)
    
    self.widget.set_value("png")
    self.assertEqual(setting.value, "")
  
  def test_automatic_gui_update_after_being_disabled(self):
    setting = stubs_pgsetting.SettingWithGuiStub(
      "file_extension", "", auto_update_gui_to_setting=False)
    setting.set_gui(
      stubs_pgsetting.SettingPresenterWithValueChangedSignalStub, self.widget)
    setting.gui.auto_update_gui_to_setting(True)
    
    self.widget.set_value("png")
    self.assertEqual(setting.value, "png")
  
  def test_automatic_gui_update_for_manual_gui_raises_value_error(self):
    setting = stubs_pgsetting.SettingWithGuiStub("file_extension", "")
    setting.set_gui(stubs_pgsetting.SettingPresenterStub, self.widget)
    
    self.assertFalse(setting.gui.gui_update_enabled)
    
    with self.assertRaises(ValueError):
      setting.gui.auto_update_gui_to_setting(True)


#===============================================================================


class TestBoolSetting(unittest.TestCase):
  
  def test_description_from_display_name(self):
    setting = pgsetting.BoolSetting(
      "only_visible_layers", False, display_name="_Only visible layers")
    self.assertEqual(setting.description, "Only visible layers?")


class TestIntSetting(unittest.TestCase):
  
  def setUp(self):
    self.setting = pgsetting.IntSetting("count", 0, min_value=0, max_value=100)
  
  def test_value_is_below_min(self):
    with self.assertRaises(pgsetting.SettingValueError):
      self.setting.set_value(-5)
  
  def test_min_value_does_not_raise_error(self):
    try:
      self.setting.set_value(0)
    except pgsetting.SettingValueError:
      self.fail("SettingValueError should not be raised")
  
  def test_value_is_above_max(self):
    with self.assertRaises(pgsetting.SettingValueError):
      self.setting.set_value(200)
  
  def test_max_value_does_not_raise_error(self):
    try:
      self.setting.set_value(100)
    except pgsetting.SettingValueError:
      self.fail("SettingValueError should not be raised")


class TestFloatSetting(unittest.TestCase):
  
  def setUp(self):
    self.setting = pgsetting.FloatSetting(
      "clip_percent", 0.0, min_value=0.0, max_value=100.0)
  
  def test_value_below_min(self):
    with self.assertRaises(pgsetting.SettingValueError):
      self.setting.set_value(-5.0)
  
  def test_minimum_value_does_not_raise_error(self):
    try:
      self.setting.set_value(0.0)
    except pgsetting.SettingValueError:
      self.fail("SettingValueError should not be raised")
  
  def test_value_above_max(self):
    with self.assertRaises(pgsetting.SettingValueError):
      self.setting.set_value(200.0)
  
  def test_maximum_value_does_not_raise_error(self):
    try:
      self.setting.set_value(100.0)
    except pgsetting.SettingValueError:
      self.fail("SettingValueError should not be raised")


class TestEnumSettingInitialization(unittest.TestCase):
  
  def test_explicit_values(self):
    setting = pgsetting.EnumSetting(
      "overwrite_mode", "replace", [("skip", "Skip", 5), ("replace", "Replace", 6)])
    self.assertEqual(setting.items["skip"], 5)
    self.assertEqual(setting.items["replace"], 6)
  
  def test_explicit_values_wrong_number_of_elements(self):
    with self.assertRaises(ValueError):
      pgsetting.EnumSetting(
        "overwrite_mode", "replace", [("skip", "Skip", 4), ("replace", "Replace")])
    
  def test_invalid_explicit_values(self):
    with self.assertRaises(ValueError):
      pgsetting.EnumSetting(
        "overwrite_mode", "replace", [("skip", "Skip", 4), ("replace", "Replace", 4)])
  
  def test_invalid_default_value(self):
    with self.assertRaises(pgsetting.SettingDefaultValueError):
      pgsetting.EnumSetting(
        "overwrite_mode", "invalid_default_value",
        [("skip", "Skip"), ("replace", "Replace")])
  
  def test_invalid_items_length_varying(self):
    with self.assertRaises(ValueError):
      pgsetting.EnumSetting(
        "overwrite_mode", None, [("skip", "Skip", 1), ("replace", "Replace")])
  
  def test_invalid_items_length_too_many_elements(self):
    with self.assertRaises(ValueError):
      pgsetting.EnumSetting(
        "overwrite_mode", None, [("skip", "Skip", 1, 1), ("replace", "Replace", 1, 1)])
  
  def test_invalid_items_length_too_few_elements(self):
    with self.assertRaises(ValueError):
      pgsetting.EnumSetting("overwrite_mode", None, [("skip"), ("replace")])
  
  def test_no_empty_value(self):
    setting = pgsetting.EnumSetting(
      "overwrite_mode", "replace", [("skip", "Skip"), ("replace", "Replace")])
    self.assertEqual(setting.empty_value, None)
  
  def test_valid_empty_value(self):
    setting = pgsetting.EnumSetting(
      "overwrite_mode", "replace",
      [("choose", "Choose your mode"), ("skip", "Skip"), ("replace", "Replace")],
      empty_value="choose")
    self.assertEqual(setting.empty_value, setting.items["choose"])
  
  def test_invalid_empty_value(self):
    with self.assertRaises(ValueError):
      pgsetting.EnumSetting(
        "overwrite_mode", "replace",
        [("skip", "Skip"), ("replace", "Replace")], empty_value="invalid_value")
  

class TestEnumSetting(unittest.TestCase):
  
  def setUp(self):
    self.setting = pgsetting.EnumSetting(
      "overwrite_mode", "replace",
      [("skip", "Skip"), ("replace", "Replace")], display_name="Overwrite mode")
  
  def test_set_invalid_item(self):
    with self.assertRaises(pgsetting.SettingValueError):
      self.setting.set_value(4)
    with self.assertRaises(pgsetting.SettingValueError):
      self.setting.set_value(-1)
  
  def test_get_invalid_item(self):
    with self.assertRaises(KeyError):
      unused_ = self.setting.items["invalid_item"]
  
  def test_description(self):
    self.assertEqual(self.setting.description, "Overwrite mode { Skip (0), Replace (1) }")
  
  def test_description_with_mnemonics_from_item_display_names(self):
    setting = pgsetting.EnumSetting(
      "overwrite_mode", "replace",
      [("skip", "_Skip"), ("replace", "_Replace")], display_name="_Overwrite mode")
    self.assertEqual(setting.description, "Overwrite mode { Skip (0), Replace (1) }")
  
  def test_get_item_display_names_and_values(self):
    self.assertEqual(
      self.setting.get_item_display_names_and_values(), ["Skip", 0, "Replace", 1])
  
  def test_is_value_empty(self):
    setting = pgsetting.EnumSetting(
      "overwrite_mode", "replace",
      [("choose", "-Choose Your Mode-"), ("skip", "Skip"), ("replace", "Replace")],
      empty_value="choose", allow_empty_values=True)
    
    self.assertFalse(setting.is_value_empty())
    setting.set_value(setting.items["choose"])
    self.assertTrue(setting.is_value_empty())
    
  def test_set_empty_value_not_allowed(self):
    setting = pgsetting.EnumSetting(
      "overwrite_mode", "replace",
      [("choose", "-Choose Your Mode-"), ("skip", "Skip"), ("replace", "Replace")],
      empty_value="choose")
    
    with self.assertRaises(pgsetting.SettingValueError):
      setting.set_value(setting.items["choose"])


class TestImageSetting(unittest.TestCase):
  
  @mock.patch(
    pgconstants.PYGIMPLIB_MODULE_PATH + ".pgsetting.pdb", new=stubs_gimp.PdbStub())
  def test_set_invalid_image(self):
    pdb = stubs_gimp.PdbStub()
    image = pdb.gimp_image_new(2, 2, gimpenums.RGB)
    
    setting = pgsetting.ImageSetting("image", image)
    
    pdb.gimp_image_delete(image)
    with self.assertRaises(pgsetting.SettingValueError):
      setting.set_value(image)
  
  @mock.patch(
    pgconstants.PYGIMPLIB_MODULE_PATH + ".pgsetting.pdb", new=stubs_gimp.PdbStub())
  def test_empty_value_as_default_value(self):
    try:
      pgsetting.ImageSetting("image", None)
    except pgsetting.SettingDefaultValueError:
      self.fail(
        "SettingDefaultValueError should not be raised - default value is an empty value")


class TestFileExtensionSetting(unittest.TestCase):
  
  def setUp(self):
    self.setting = pgsetting.FileExtensionSetting("file_ext", "png")
  
  def test_invalid_default_value(self):
    with self.assertRaises(pgsetting.SettingDefaultValueError):
      pgsetting.FileExtensionSetting("file_ext", None)
  
  def test_custom_error_message(self):
    self.setting.error_messages[pgpath.FileValidatorErrorStatuses.IS_EMPTY] = (
      "my custom message")
    try:
      self.setting.set_value("")
    except pgsetting.SettingValueError as e:
      self.assertEqual(str(e), "my custom message")


class TestDirpathSetting(unittest.TestCase):
  
  def setUp(self):
    self.setting = pgsetting.DirpathSetting("output_directory", "/some_dir")
  
  def test_default_value_as_bytes_convert_to_unicode(self):
    setting = pgsetting.DirpathSetting("output_directory", b"/some_dir/p\xc5\x88g")
    self.assertIsInstance(setting.value, str)
  
  def test_set_value_as_bytes_convert_to_unicode(self):
    self.setting.set_value(b"/some_dir/p\xc5\x88g")
    self.assertIsInstance(self.setting.value, str)


class TestImageIDsAndDirpathsSetting(unittest.TestCase):
  
  def setUp(self):
    self.setting = pgsetting.ImageIDsAndDirpathsSetting("image_ids_and_directories", {})
    
    self.image_ids_and_filepaths = [
      (0, None), (1, "C:\\image.png"), (2, "/test/test.jpg"),
      (4, "/test/another_test.gif")]
    self.image_list = self._create_image_list(self.image_ids_and_filepaths)
    self.image_ids_and_directories = (
      self._create_image_ids_and_directories(self.image_list))
    
    self.setting.set_value(self.image_ids_and_directories)
  
  def get_image_list(self):
    # `self.image_list` is wrapped into a method so that `mock.patch.object` can
    # be called on it.
    return self.image_list
  
  def _create_image_list(self, image_ids_and_filepaths):
    return [
      self._create_image(image_id, filepath)
      for image_id, filepath in image_ids_and_filepaths]
  
  @staticmethod
  def _create_image(image_id, filepath):
    image = stubs_gimp.ImageStub()
    image.ID = image_id
    image.filename = filepath
    return image
  
  @staticmethod
  def _create_image_ids_and_directories(image_list):
    image_ids_and_directories = {}
    for image in image_list:
      image_ids_and_directories[image.ID] = (
        os.path.dirname(image.filename) if image.filename is not None else None)
    return image_ids_and_directories
  
  def test_update_image_ids_and_dirpaths_add_new_images(self):
    self.image_list.extend(
      self._create_image_list([(5, "/test/new_image.png"), (6, None)]))
    
    with mock.patch(
           pgconstants.PYGIMPLIB_MODULE_PATH + ".pgsetting.gimp.image_list",
           new=self.get_image_list):
      self.setting.update_image_ids_and_dirpaths()
    
    self.assertEqual(
      self.setting.value, self._create_image_ids_and_directories(self.image_list))
  
  def test_update_image_ids_and_dirpaths_remove_closed_images(self):
    self.image_list.pop(1)
    
    with mock.patch(
           pgconstants.PYGIMPLIB_MODULE_PATH + ".pgsetting.gimp.image_list",
           new=self.get_image_list):
      self.setting.update_image_ids_and_dirpaths()
    
    self.assertEqual(
      self.setting.value, self._create_image_ids_and_directories(self.image_list))
  
  def test_update_directory(self):
    self.setting.update_dirpath(1, "test_directory")
    self.assertEqual(self.setting.value[1], "test_directory")
  
  def test_update_directory_invalid_image_id(self):
    with self.assertRaises(KeyError):
      self.setting.update_dirpath(-1, "test_directory")
  
  def test_value_setitem_does_not_change_setting_value(self):
    image_id_to_test = 1
    self.setting.value[image_id_to_test] = "test_directory"
    self.assertNotEqual(self.setting.value[image_id_to_test], "test_directory")
    self.assertEqual(
      self.setting.value[image_id_to_test],
      self.image_ids_and_directories[image_id_to_test])


class TestCreateArraySetting(unittest.TestCase):
  
  def test_create(self):
    setting = pgsetting.ArraySetting(
      "coordinates",
      (1.0, 5.0, 10.0),
      element_type=pgsetting.SettingTypes.float,
      element_default_value=0.0)
    
    self.assertEqual(setting.name, "coordinates")
    self.assertEqual(setting.default_value, (1.0, 5.0, 10.0))
    self.assertEqual(setting.value, (1.0, 5.0, 10.0))
    self.assertEqual(setting.element_type, pgsetting.SettingTypes.float)
    self.assertEqual(setting.element_default_value, 0.0)
  
  def test_create_passing_non_tuple_as_default_value_converts_initial_value_to_tuple(
        self):
    setting = pgsetting.ArraySetting(
      "coordinates",
      [1.0, 5.0, 10.0],
      element_type=pgsetting.SettingTypes.float,
      element_default_value=0.0)
    
    self.assertEqual(setting.default_value, [1.0, 5.0, 10.0])
    self.assertEqual(setting.value, (1.0, 5.0, 10.0))
  
  def test_create_passing_array_setting_raises_error(self):
    with self.assertRaises(TypeError):
      pgsetting.ArraySetting(
        "coordinates",
        (1.0, 5.0, 10.0),
        element_type=pgsetting.SettingTypes.array,
        element_default_value=0.0)
  
  def test_create_with_additional_read_only_element_arguments(self):
    setting = pgsetting.ArraySetting(
      "coordinates",
      (1.0, 5.0, 10.0),
      element_type=pgsetting.SettingTypes.float,
      element_default_value=0.0,
      element_min_value=-100.0,
      element_max_value=100.0)
    
    self.assertEqual(setting.element_min_value, -100.0)
    self.assertEqual(setting.element_max_value, 100.0)
    
    for setting_attribute in setting.__dict__:
      if setting_attribute.startswith("element_"):
        with self.assertRaises(AttributeError):
          setattr(setting, setting_attribute, None)
  
  def test_create_passing_invalid_default_value_raises_error(self):
    with self.assertRaises(pgsetting.SettingValueError):
      pgsetting.ArraySetting(
        "coordinates",
        (-200.0, 200.0),
        element_type=pgsetting.SettingTypes.float,
        element_default_value=0.0,
        element_min_value=-100.0,
        element_max_value=100.0)
  
  @parameterized.parameterized.expand([
    ("default_value_is_empty", ()),
    ("default_value_is_not_empty", (1.0, 5.0, 10.0)),
  ])
  def test_create_invalid_element_default_value_raises_error(
        self, test_case_name_suffix, default_value):
    with self.assertRaises(pgsetting.SettingDefaultValueError):
      pgsetting.ArraySetting(
        "coordinates",
        default_value,
        element_type=pgsetting.SettingTypes.float,
        element_default_value=-200.0,
        element_min_value=-100.0,
        element_max_value=100.0)
  
  @parameterized.parameterized.expand([
    ("element_pdb_type_is_registrable",
     pgsetting.SettingPdbTypes.automatic,
     pgsetting.SettingTypes.float,
     pgsetting.SettingPdbTypes.array_float),
    
    ("element_pdb_type_is_not_registrable",
     pgsetting.SettingPdbTypes.automatic,
     pgsetting.SettingTypes.generic,
     pgsetting.SettingPdbTypes.none),
    
    ("registration_is_disabled_explicitly",
     None,
     pgsetting.SettingTypes.float,
     pgsetting.SettingPdbTypes.none),
  ])
  def test_create_with_pdb_type(
        self, test_case_name_suffix, pdb_type, element_type, expected_pdb_type):
    setting = pgsetting.ArraySetting(
      "coordinates",
      (1.0, 5.0, 10.0),
      pdb_type=pdb_type,
      element_type=element_type,
      element_default_value=0.0)
    
    self.assertEqual(setting.pdb_type, expected_pdb_type)
  
  def test_create_with_explicit_valid_element_pdb_type(self):
    setting = pgsetting.ArraySetting(
      "coordinates",
      (1, 5, 10),
      element_type=pgsetting.SettingTypes.integer,
      element_default_value=0,
      element_pdb_type=pgsetting.SettingPdbTypes.int16)
    
    self.assertEqual(setting.pdb_type, pgsetting.SettingPdbTypes.array_int16)
  
  def test_create_with_invalid_element_pdb_type(self):
    with self.assertRaises(ValueError):
      pgsetting.ArraySetting(
        "coordinates",
        (1.0, 5.0, 10.0),
        element_type=pgsetting.SettingTypes.float,
        element_default_value=0.0,
        element_pdb_type=pgsetting.SettingPdbTypes.int16)


class TestArraySetting(unittest.TestCase):
  
  def setUp(self):
    self.setting = pgsetting.ArraySetting(
      "coordinates",
      (1.0, 5.0, 10.0),
      element_type=pgsetting.SettingTypes.float,
      element_default_value=0.0,
      element_min_value=-100.0,
      element_max_value=100.0)
  
  @parameterized.parameterized.expand([
    ("with_tuple", (20.0, 50.0, 40.0), (20.0, 50.0, 40.0)),
    ("converts_value_to_tuple", [20.0, 50.0, 40.0], (20.0, 50.0, 40.0)),
  ])
  def test_set_value(self, test_case_name_suffix, input_value, expected_value):
    self.setting.set_value(input_value)
    
    self.assertEqual(self.setting.value, expected_value)
    for i, expected_element_value in enumerate(expected_value):
      self.assertEqual(self.setting[i].value, expected_element_value)
  
  def test_set_value_validates_if_value_is_iterable(self):
    with self.assertRaises(pgsetting.SettingValueError):
      self.setting.set_value(45)
  
  @parameterized.parameterized.expand([
    ("first_is_invalid", (200.0, 50.0, 40.0)),
    ("middle_is_invalid", (20.0, 200.0, 40.0)),
    ("last_is_invalid", (20.0, 50.0, 200.0)),
    ("two_are_invalid", (20.0, 200.0, 200.0)),
    ("all_are_invalid", (200.0, 200.0, 200.0)),
  ])
  def test_set_value_validates_each_element_value_individually(
        self, test_case_name_suffix, input_value):
    with self.assertRaises(pgsetting.SettingValueError):
      self.setting.set_value(input_value)
  
  def test_reset_retains_default_value(self):
    self.setting.set_value((20.0, 50.0, 40.0))
    self.setting.reset()
    self.assertEqual(self.setting.value, (1.0, 5.0, 10.0))
    self.assertEqual(self.setting.default_value, (1.0, 5.0, 10.0))
  
  @parameterized.parameterized.expand([
    ("first", 0, 1.0),
    ("middle", 1, 5.0),
    ("last", 2, 10.0),
    ("last_with_negative_index", -1, 10.0),
    ("second_to_last_with_negative_index", -2, 5.0),
  ])
  def test_getitem(self, test_case_name_suffix, index, expected_value):
    self.assertEqual(self.setting[index].value, expected_value)
  
  @parameterized.parameterized.expand([
    ("first_to_middle", None, 2, [1.0, 5.0]),
    ("middle_to_last", 1, None, [5.0, 10.0]),
    ("middle_to_last_explicit", 1, 3, [5.0, 10.0]),
    ("all", None, None, [1.0, 5.0, 10.0]),
    ("negative_last_to_middle", -1, -3, [10.0, 5.0], -1),
  ])
  def test_getitem_slice(
        self, test_case_name_suffix, index_begin, index_end, expected_value, step=None):
    self.assertEqual(
      [element.value for element in self.setting[index_begin:index_end:step]],
      expected_value)
  
  @parameterized.parameterized.expand([
    ("one_more_than_length", 3),
    ("more_than_length", 5),
  ])
  def test_getitem_out_of_bounds_raises_error(self, test_case_name_suffix, index):
    with self.assertRaises(IndexError):
      self.setting[index]
  
  @parameterized.parameterized.expand([
    ("first_element", [0]),
    ("middle_element", [1]),
    ("last_element", [2]),
    ("two_elements", [1, 1]),
    ("all_elements", [0, 0, 0]),
  ])
  def test_delitem(self, test_case_name_suffix, indexes_to_delete):
    orig_len = len(self.setting)
    
    for index in indexes_to_delete:
      del self.setting[index]
    
    self.assertEqual(len(self.setting), orig_len - len(indexes_to_delete))
  
  @parameterized.parameterized.expand([
    ("one_more_than_length", 3),
    ("more_than_length", 5),
  ])
  def test_delitem_out_of_bounds_raises_error(self, test_case_name_suffix, index):
    with self.assertRaises(IndexError):
      self.setting[index]
  
  @parameterized.parameterized.expand([
    ("append_default_value",
     None, pgsetting.ArraySetting.ELEMENT_DEFAULT_VALUE, -1, 0.0),
    
    ("insert_at_beginning_default_value",
     0, pgsetting.ArraySetting.ELEMENT_DEFAULT_VALUE, 0, 0.0),
    
    ("insert_in_middle_default_value",
     1, pgsetting.ArraySetting.ELEMENT_DEFAULT_VALUE, 1, 0.0),
    
    ("append_value",
     None, 40.0, -1, 40.0),
    
    ("insert_in_middle_value",
     1, 40.0, 1, 40.0),
  ])
  def test_add_element(
        self, test_case_name_suffix, index, value, insertion_index, expected_value):
    element = self.setting.add_element(index, value=value)
    self.assertEqual(len(self.setting), 4)
    self.assertIs(self.setting[insertion_index], element)
    self.assertEqual(self.setting[insertion_index].value, expected_value)
  
  def test_add_element_none_as_value(self):
    setting = pgsetting.ArraySetting(
      "coordinates",
      (),
      element_type=pgsetting.SettingTypes.generic,
      element_default_value=0)
    
    setting.add_element(value=None)
    self.assertEqual(setting[-1].value, None)
  
  @parameterized.parameterized.expand([
    ("middle_to_first", 1, 0, [5.0, 1.0, 10.0]),
    ("middle_to_last", 1, 2, [1.0, 10.0, 5.0]),
    ("middle_to_last_above_bounds", 1, 3, [1.0, 10.0, 5.0]),
    ("first_to_middle", 0, 1, [5.0, 1.0, 10.0]),
    ("last_to_middle", 2, 1, [1.0, 10.0, 5.0]),
    ("middle_to_last_negative_position", 1, -1, [1.0, 10.0, 5.0]),
    ("middle_to_middle_negative_position", 1, -2, [1.0, 5.0, 10.0]),
  ])
  def test_reorder_element(
        self, test_case_name_suffix, index, new_index, expected_values):
    self.setting.reorder_element(index, new_index)
    self.assertEqual(
      [element.value for element in self.setting[:]],
      expected_values)
  
  def test_set_element_value(self):
    self.setting[1].set_value(50.0)
    self.assertEqual(self.setting[1].value, 50.0)
    self.assertEqual(self.setting.value, (1.0, 50.0, 10.0))
  
  def test_set_element_value_validates_value(self):
    with self.assertRaises(pgsetting.SettingValueError):
      self.setting[1].set_value(200.0)
  
  def test_reset_element_sets_element_default_value(self):
    self.setting[1].reset()
    self.assertEqual(self.setting[1].value, 0.0)
    self.assertEqual(self.setting.value, (1.0, 0.0, 10.0))
  
  def test_connect_event_for_individual_elements_affects_those_elements_only(self):
    def _on_array_changed(array_setting):
      array_setting[2].set_value(70.0)
    
    def _on_element_changed(element, array_setting):
      array_setting[0].set_value(20.0)
    
    self.setting.connect_event("value-changed", _on_array_changed)
    
    self.setting[1].connect_event("value-changed", _on_element_changed, self.setting)
    self.setting[1].set_value(50.0)
    
    self.assertEqual(self.setting[0].value, 20.0)
    self.assertEqual(self.setting[1].value, 50.0)
    self.assertEqual(self.setting[2].value, 10.0)
    self.assertEqual(self.setting.value, (20.0, 50.0, 10.0))
    
    self.setting.set_value((60.0, 80.0, 30.0))
    self.assertEqual(self.setting.value, (60.0, 80.0, 70.0))
  
  @parameterized.parameterized.expand([
    ("default_index",
     None, pgsetting.ArraySetting.ELEMENT_DEFAULT_VALUE, None, 0.0),
    
    ("explicit_index",
     1, pgsetting.ArraySetting.ELEMENT_DEFAULT_VALUE, 1, 0.0),
  ])
  def test_before_add_element_event(
        self, test_case_name_suffix, index, value, expected_index, expected_value):
    event_args = []
    
    def _on_before_add_element(array_setting, index, value):
      event_args.append((index, value))
    
    self.setting.connect_event("before-add-element", _on_before_add_element)
    
    self.setting.add_element(index, value)
    self.assertEqual(event_args[0][0], expected_index)
    self.assertEqual(event_args[0][1], expected_value)
  
  @parameterized.parameterized.expand([
    ("default_index",
     None, pgsetting.ArraySetting.ELEMENT_DEFAULT_VALUE, -1, 0.0),
    
    ("explicit_zero_index",
     0, pgsetting.ArraySetting.ELEMENT_DEFAULT_VALUE, 0, 0.0),
    
    ("explicit_positive_index",
     1, pgsetting.ArraySetting.ELEMENT_DEFAULT_VALUE, 1, 0.0),
    
    ("explicit_negative_index",
     -1, pgsetting.ArraySetting.ELEMENT_DEFAULT_VALUE, -2, 0.0),
  ])
  def test_after_add_element_event(
        self, test_case_name_suffix, index, value, expected_index, expected_value):
    event_args = []
    
    def _on_after_add_element(array_setting, insertion_index, value):
      event_args.append((insertion_index, value))
    
    self.setting.connect_event("after-add-element", _on_after_add_element)
    
    self.setting.add_element(index, value)
    self.assertEqual(event_args[0][0], expected_index)
    self.assertEqual(event_args[0][1], expected_value)
  
  @parameterized.parameterized.expand([
    ("default_length_name_and_description",
     None,
     None,
     b"coordinates-length",
     b"Number of elements in 'coordinates'"),
    
    ("custom_length_name_and_description",
     "num-axes-coordinates",
     "The number of axes for coordinates",
     b"num-axes-coordinates",
     b"The number of axes for coordinates"),
  ])
  def test_get_pdb_param_for_registrable_setting(
        self,
        test_case_name_suffix,
        length_name,
        length_description,
        expected_length_name,
        expected_length_description):
    self.assertEqual(
      self.setting.get_pdb_param(length_name, length_description),
      [(pgsetting.SettingPdbTypes.int, expected_length_name, expected_length_description),
       (pgsetting.SettingPdbTypes.array_float, b"coordinates", b"Coordinates")])
  
  def test_get_pdb_param_for_nonregistrable_setting(self):
    setting = pgsetting.ArraySetting(
      "coordinates",
      (1.0, 5.0, 10.0),
      element_type=pgsetting.SettingTypes.generic,
      element_default_value=0.0)
    
    self.assertEqual(setting.get_pdb_param(), None)


class TestArraySettingCreateWithSize(unittest.TestCase):
  
  @parameterized.parameterized.expand([
    ("default_sizes", None, None, 0, None),
    ("min_size_zero", 0, None, 0, None),
    ("min_size_positive", 1, None, 1, None),
    ("min_size_positive_max_size_positive", 1, 5, 1, 5),
    ("max_size_equal_to_default_value_length", 1, 3, 1, 3),
    ("min_and_max_size_equal_to_default_value_length", 3, 3, 3, 3),
  ])
  def test_create_with_size(
        self,
        test_case_name_suffix,
        min_size,
        max_size,
        expected_min_size,
        expected_max_size):
    setting = pgsetting.ArraySetting(
      "coordinates",
      (1.0, 5.0, 10.0),
      element_type=pgsetting.SettingTypes.float,
      element_default_value=0.0,
      min_size=min_size,
      max_size=max_size)
    
    self.assertEqual(setting.min_size, expected_min_size)
    self.assertEqual(setting.max_size, expected_max_size)
  
  @parameterized.parameterized.expand([
    ("min_size_negative", -1, None),
    ("max_size_less_than_min_size", 5, 4),
    ("max_size_less_than_default_value_length", 0, 2),
    ("min_size_greater_than_default_value_length", 4, None),
  ])
  def test_create_raises_error_on_invalid_size(
        self, test_case_name_suffix, min_size, max_size):
    with self.assertRaises(pgsetting.SettingDefaultValueError):
      pgsetting.ArraySetting(
        "coordinates",
        (1.0, 5.0, 10.0),
        element_type=pgsetting.SettingTypes.float,
        element_default_value=0.0,
        min_size=min_size,
        max_size=max_size)


class TestArraySettingSize(unittest.TestCase):
  
  def setUp(self):
    self.setting = pgsetting.ArraySetting(
      "coordinates",
      (1.0, 5.0, 10.0),
      element_type=pgsetting.SettingTypes.float,
      element_default_value=0.0,
      element_min_value=-100.0,
      element_max_value=100.0,
      min_size=2,
      max_size=4)
  
  def test_set_value_with_respect_to_size(self):
    try:
      self.setting.set_value((5.0, 10.0))
    except pgsetting.SettingValueError:
      self.fail(
        "setting the value while satisfying size restrictions should not raise error")
  
  @parameterized.parameterized.expand([
    ("value_length_less_than_min_size", (1.0,)),
    ("value_length_greater_than_max_size", (1.0, 5.0, 10.0, 30.0, 70.0)),
  ])
  def test_set_value_invalid_size_raises_error(self, test_case_name_suffix, value):
    with self.assertRaises(pgsetting.SettingValueError):
      self.setting.set_value(value)
  
  def test_add_element_with_respect_to_size(self):
    try:
      self.setting.add_element()
    except pgsetting.SettingValueError:
      self.fail(
        "adding an element while satisfying size restrictions should not raise error")
  
  def test_add_element_more_than_max_size_raises_error(self):
    self.setting.add_element()
    with self.assertRaises(pgsetting.SettingValueError):
      self.setting.add_element()
  
  def test_delete_element_with_respect_to_size(self):
    try:
      del self.setting[-1]
    except pgsetting.SettingValueError:
      self.fail(
        "deleting an element while satisfying size restrictions should not raise error")
  
  def test_delete_element_less_then_min_size_raises_error(self):
    del self.setting[-1]
    with self.assertRaises(pgsetting.SettingValueError):
      del self.setting[-1]
