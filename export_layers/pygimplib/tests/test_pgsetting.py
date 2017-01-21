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

"""
This module tests the `pgsetting` and `pgsettingpresenter` modules.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import os
import unittest

import gimpenums

import mock

from . import stubs_gimp
from . import stubs_pgsetting
from .. import pgpath
from .. import pgsetting
from .. import pgsettingpersistor
from .. import pgsettingsources
from .. import pgconstants

#===============================================================================


class TestSetting(unittest.TestCase):
  
  def setUp(self):
    self.setting = stubs_pgsetting.SettingStub("file_extension", "png")
  
  def test_str(self):
    self.assertEqual(str(self.setting), "<SettingStub 'file_extension'>")
  
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
  
  @mock.patch(
    pgconstants.PYGIMPLIB_MODULE_PATH + ".pgsettingpersistor.SettingPersistor.load")
  def test_load(self, mock_setting_persistor_load):
    dummy_setting_source = object()
    self.setting.load([dummy_setting_source])
    self.assertTrue(mock_setting_persistor_load.called)
  
  @mock.patch(
    pgconstants.PYGIMPLIB_MODULE_PATH + ".pgsettingpersistor.SettingPersistor.load")
  def test_load_default_source(self, mock_setting_persistor_load):
    dummy_setting_source = object()
    setting = stubs_pgsetting.SettingStub(
      "image_IDs_and_directories", {}, setting_sources=[dummy_setting_source])
    setting.load()
    self.assertTrue(mock_setting_persistor_load.called)
  
  @mock.patch(
    pgconstants.PYGIMPLIB_MODULE_PATH + ".pgsettingpersistor.SettingPersistor.load")
  def test_load_default_source_overridden_by_parameter(self, mock_setting_persistor_load):
    dummy_setting_source_default = object()
    setting = stubs_pgsetting.SettingStub(
      "image_IDs_and_directories", {}, setting_sources=[dummy_setting_source_default])
    dummy_setting_source_parameter = object()
    
    setting.load([dummy_setting_source_parameter])
    
    self.assertTrue(mock_setting_persistor_load.called)
    self.assertIn(
      dummy_setting_source_parameter, mock_setting_persistor_load.call_args[0][1])
    self.assertNotIn(
      dummy_setting_source_default, mock_setting_persistor_load.call_args[0][1])
  
  def test_load_no_default_source_no_parameter(self):
    with self.assertRaises(ValueError):
      self.setting.load()
  
  @mock.patch(
    pgconstants.PYGIMPLIB_MODULE_PATH + ".pgsettingpersistor.SettingPersistor.save")
  def test_save(self, mock_setting_persistor_save):
    dummy_setting_source = object()
    self.setting.save([dummy_setting_source])
    self.assertTrue(mock_setting_persistor_save.called)
  
  @mock.patch(
    pgconstants.PYGIMPLIB_MODULE_PATH + ".pgsettingpersistor.SettingPersistor.save")
  def test_save_default_source(self, mock_setting_persistor_save):
    dummy_setting_source = object()
    setting = stubs_pgsetting.SettingStub(
      "image_IDs_and_directories", {}, setting_sources=[dummy_setting_source])
    setting.save()
    self.assertTrue(mock_setting_persistor_save.called)
  
  @mock.patch(
    pgconstants.PYGIMPLIB_MODULE_PATH + ".pgsettingpersistor.SettingPersistor.save")
  def test_save_default_source_overridden_by_parameter(self, mock_setting_persistor_save):
    dummy_setting_source_default = object()
    setting = stubs_pgsetting.SettingStub(
      "image_IDs_and_directories", {}, setting_sources=[dummy_setting_source_default])
    dummy_setting_source_parameter = object()
    
    setting.save([dummy_setting_source_parameter])
    
    self.assertTrue(mock_setting_persistor_save.called)
    self.assertIn(
      dummy_setting_source_parameter, mock_setting_persistor_save.call_args[0][1])
    self.assertNotIn(
      dummy_setting_source_default, mock_setting_persistor_save.call_args[0][1])
  
  def test_save_no_default_source_no_parameter(self):
    with self.assertRaises(ValueError):
      self.setting.save()
  

#===============================================================================


class TestSettingEvents(unittest.TestCase):
  
  def setUp(self):
    self.setting = stubs_pgsetting.SettingStub("file_extension", "png")
    self.only_visible_layers = pgsetting.BoolSetting("only_visible_layers", False)

  def test_connect_event_argument_is_not_callable(self):
    with self.assertRaises(TypeError):
      self.setting.connect_event("value-changed", None)
  
  def test_connect_event_keyword_arguments(self):
    autocrop = pgsetting.BoolSetting("autocrop", False)
    autocrop.connect_event(
      "value-changed", stubs_pgsetting.on_autocrop_changed, self.setting,
      file_extension_value="tiff")
    
    autocrop.set_value(True)
    self.assertEqual(self.setting.value, "tiff")
  
  def test_connect_value_changed_event(self):
    self.setting.connect_event(
      "value-changed", stubs_pgsetting.on_file_extension_changed,
      self.only_visible_layers)
    
    self.setting.set_value("jpg")
    self.assertEqual(self.only_visible_layers.value, True)
    self.assertFalse(self.only_visible_layers.gui.get_enabled())
  
  def test_connect_value_changed_event_nested(self):
    self.setting.connect_event(
      "value-changed", stubs_pgsetting.on_file_extension_changed,
      self.only_visible_layers)
    
    autocrop = pgsetting.BoolSetting("autocrop", False)
    autocrop.connect_event(
      "value-changed", stubs_pgsetting.on_autocrop_changed, self.setting)
    
    autocrop.set_value(True)
    
    self.assertEqual(self.setting.value, "jpg")
    self.assertEqual(self.only_visible_layers.value, True)
    self.assertFalse(self.only_visible_layers.gui.get_enabled())
  
  def test_connect_event_multiple_events_on_single_setting(self):
    self.setting.connect_event(
      "value-changed", stubs_pgsetting.on_file_extension_changed,
      self.only_visible_layers)
    
    autocrop = pgsetting.BoolSetting("autocrop", False)
    self.setting.connect_event(
      "value-changed", stubs_pgsetting.on_file_extension_changed_with_autocrop, autocrop)
    
    self.setting.set_value("jpg")
    self.assertEqual(self.setting.value, "jpg")
    self.assertEqual(self.only_visible_layers.value, True)
    self.assertFalse(autocrop.gui.get_visible())
  
  def test_remove_event(self):
    event_id = self.setting.connect_event(
      "value-changed", stubs_pgsetting.on_file_extension_changed,
      self.only_visible_layers)
    self.setting.remove_event(event_id)
    
    self.setting.set_value("jpg")
    self.assertEqual(
      self.only_visible_layers.value, self.only_visible_layers.default_value)
    self.assertTrue(self.only_visible_layers.gui.get_enabled())
  
  def test_remove_event_with_id_non_last_event(self):
    event_id = self.setting.connect_event(
      "value-changed", stubs_pgsetting.on_file_extension_changed,
      self.only_visible_layers)
    
    autocrop = pgsetting.BoolSetting("autocrop", False)
    self.setting.connect_event(
      "value-changed", stubs_pgsetting.on_file_extension_changed_with_autocrop, autocrop)
    
    self.setting.remove_event(event_id)
    
    self.setting.set_value("jpg")
    self.assertEqual(self.only_visible_layers.value, False)
    self.assertFalse(autocrop.gui.get_visible())
  
  def test_remove_event_invalid_id(self):
    self.setting.connect_event(
      "value-changed", stubs_pgsetting.on_file_extension_changed,
      self.only_visible_layers)
    with self.assertRaises(ValueError):
      self.setting.remove_event(-1)
  
  def test_has_event(self):
    self.assertFalse(self.setting.has_event(-1))
    event_id = self.setting.connect_event(
      "value-changed", stubs_pgsetting.on_file_extension_changed,
      self.only_visible_layers)
    self.assertTrue(self.setting.has_event(event_id))
    self.setting.remove_event(event_id)
    self.assertFalse(self.setting.has_event(event_id))
  
  def test_set_event_enabled(self):
    with self.assertRaises(ValueError):
      self.setting.set_event_enabled(-1, False)
    
    event_id = self.setting.connect_event(
      "value-changed", stubs_pgsetting.on_file_extension_changed,
      self.only_visible_layers)
    
    self.setting.set_event_enabled(event_id, False)
    self.setting.set_value("jpg")
    self.assertFalse(self.only_visible_layers.value)
    
    self.setting.set_event_enabled(event_id, True)
    self.setting.set_value("jpg")
    self.assertEqual(self.only_visible_layers.value, True)
  
  def test_invoke_event(self):
    self.only_visible_layers.set_value(True)
    self.setting.connect_event(
      "value-changed", stubs_pgsetting.on_file_extension_changed,
      self.only_visible_layers)
    
    self.setting.invoke_event("value-changed")
    self.assertEqual(self.setting.value, "png")
    self.assertEqual(self.only_visible_layers.value, False)
  
  def test_reset_triggers_value_changed_event(self):
    self.setting.connect_event(
      "value-changed", stubs_pgsetting.on_file_extension_changed,
      self.only_visible_layers)
    
    self.setting.set_value("jpg")
    self.setting.reset()
    self.assertEqual(
      self.only_visible_layers.value, self.only_visible_layers.default_value)
    self.assertTrue(self.only_visible_layers.gui.get_enabled())


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
        pgsettingpersistor.SettingSourceReadError)
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
        pgsettingpersistor.SettingSourceWriteError)
      pgsettingpersistor.SettingPersistor.save([self.setting], [self.session_source])
    
    self.assertEqual(self.only_visible_layers.value, False)
  
  
#===============================================================================


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
    self.setting.gui.set_enabled(False)
    self.setting.gui.set_visible(False)
    self.setting.set_value("gif")
    
    self.setting.set_gui(stubs_pgsetting.SettingPresenterStub, self.widget)
    
    self.assertFalse(self.setting.gui.get_enabled())
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
        "only_visible_layers", False,
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
      "only_visible_layers", False,
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
    self.assertFalse(only_visible_layers.gui.get_enabled())
  
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


class TestDirectorySetting(unittest.TestCase):
  
  def setUp(self):
    self.setting = pgsetting.DirectorySetting("output_directory", "/some_dir")
  
  def test_default_value_as_bytes_convert_to_unicode(self):
    setting = pgsetting.DirectorySetting("output_directory", b"/some_dir/p\xc5\x88g")
    self.assertIsInstance(setting.value, str)
  
  def test_set_value_as_bytes_convert_to_unicode(self):
    self.setting.set_value(b"/some_dir/p\xc5\x88g")
    self.assertIsInstance(self.setting.value, str)


class TestImageIDsAndDirectoriesSetting(unittest.TestCase):
  
  def setUp(self):
    self.setting = pgsetting.ImageIDsAndDirectoriesSetting(
      "image_ids_and_directories", {})
    
    self.image_ids_and_filenames = [
      (0, None), (1, "C:\\image.png"), (2, "/test/test.jpg"),
      (4, "/test/another_test.gif")]
    self.image_list = self._create_image_list(self.image_ids_and_filenames)
    self.image_ids_and_directories = (
      self._create_image_ids_and_directories(self.image_list))
    
    self.setting.set_value(self.image_ids_and_directories)
  
  def get_image_list(self):
    # `self.image_list` is wrapped into a method so that `mock.patch.object` can
    # be called on it.
    return self.image_list
  
  def _create_image_list(self, image_ids_and_filenames):
    return [
      self._create_image(image_id, filename)
      for image_id, filename in image_ids_and_filenames]
  
  @staticmethod
  def _create_image(image_id, filename):
    image = stubs_gimp.ImageStub()
    image.ID = image_id
    image.filename = filename
    return image
  
  @staticmethod
  def _create_image_ids_and_directories(image_list):
    image_ids_and_directories = {}
    for image in image_list:
      directory = os.path.dirname(image.filename) if image.filename is not None else None
      image_ids_and_directories[image.ID] = directory
    return image_ids_and_directories
  
  def test_update_image_ids_and_directories_add_new_images(self):
    self.image_list.extend(
      self._create_image_list([(5, "/test/new_image.png"), (6, None)]))
    
    with mock.patch(
           pgconstants.PYGIMPLIB_MODULE_PATH + ".pgsetting.gimp.image_list",
           new=self.get_image_list):
      self.setting.update_image_ids_and_directories()
    
    self.assertEqual(
      self.setting.value, self._create_image_ids_and_directories(self.image_list))
  
  def test_update_image_ids_and_directories_remove_closed_images(self):
    self.image_list.pop(1)
    
    with mock.patch(
           pgconstants.PYGIMPLIB_MODULE_PATH + ".pgsetting.gimp.image_list",
           new=self.get_image_list):
      self.setting.update_image_ids_and_directories()
    
    self.assertEqual(
      self.setting.value, self._create_image_ids_and_directories(self.image_list))
  
  def test_update_directory(self):
    directory = "test_directory"
    self.setting.update_directory(1, directory)
    self.assertEqual(self.setting.value[1], directory)
  
  def test_update_directory_invalid_image_id(self):
    with self.assertRaises(KeyError):
      self.setting.update_directory(-1, "test_directory")
  
  def test_value_setitem_does_not_change_setting_value(self):
    image_id_to_test = 1
    test_directory = "test_directory"
    self.setting.value[image_id_to_test] = test_directory
    self.assertNotEqual(self.setting.value[image_id_to_test], test_directory)
    self.assertEqual(
      self.setting.value[image_id_to_test],
      self.image_ids_and_directories[image_id_to_test])
