# -*- coding: utf-8 -*-
#
# Copyright (C) 2014-2017 khalim19
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

from . import stubs_pgsetting
from . import stubs_pgsettinggroup
from .. import pgsetting
from .. import pgsettinggroup
from .. import pgsettingpersistor
from .. import pgconstants

#===============================================================================


class TestSettingGroupAttributes(unittest.TestCase):
  
  def setUp(self):
    self.settings = pgsettinggroup.SettingGroup(name="main")
  
  def test_get_generated_display_name(self):
    self.assertEqual(self.settings.display_name, "Main")
  
  def test_get_generated_description(self):
    settings = pgsettinggroup.SettingGroup(name="main", display_name="_Main")
    self.assertEqual(settings.description, "Main")
  
  def test_get_custom_display_name_and_description(self):
    settings = pgsettinggroup.SettingGroup(
      name="main", display_name="_Main", description="My description")
    self.assertEqual(settings.display_name, "_Main")
    self.assertEqual(settings.description, "My description")
  
  def test_get_non_existent_setting_name(self):
    with self.assertRaises(KeyError):
      unused_ = self.settings["invalid_name"]


class TestSettingGroupAddWithSettingDict(unittest.TestCase):
  
  def setUp(self):
    self.settings = pgsettinggroup.SettingGroup("main")
    self.autocrop_setting_dict = {
      "type": pgsetting.SettingTypes.boolean,
      "name": "autocrop",
      "default_value": False}
  
  def test_add(self):
    self.settings.add([self.autocrop_setting_dict])
    
    self.assertIn("autocrop", self.settings)
    self.assertIsInstance(self.settings["autocrop"], pgsetting.BoolSetting)
    self.assertEqual(self.settings["autocrop"].value, False)
  
  def test_add_with_missing_type_attribute(self):
    del self.autocrop_setting_dict["type"]
    
    with self.assertRaises(TypeError):
      self.settings.add([self.autocrop_setting_dict])
  
  def test_add_with_missing_single_mandatory_attribute(self):
    del self.autocrop_setting_dict["name"]
    
    with self.assertRaises(TypeError):
      self.settings.add([self.autocrop_setting_dict])
  
  def test_add_with_missing_multiple_mandatory_attributes(self):
    del self.autocrop_setting_dict["name"]
    del self.autocrop_setting_dict["default_value"]
    
    with self.assertRaises(TypeError):
      self.settings.add([self.autocrop_setting_dict])
  
  def test_add_with_invalid_setting_attribute(self):
    self.autocrop_setting_dict["invalid_setting_attribute"] = None
    
    with self.assertRaises(TypeError):
      self.settings.add([self.autocrop_setting_dict])
  
  def test_add_with_path_separator(self):
    self.autocrop_setting_dict["name"] = "auto/crop"
    
    with self.assertRaises(ValueError):
      self.settings.add([self.autocrop_setting_dict])
  
  def test_add_with_same_name_in_same_group(self):
    with self.assertRaises(ValueError):
      self.settings.add([self.autocrop_setting_dict, self.autocrop_setting_dict])
  
  def test_add_multiple_dicts_with_same_name_in_different_child_groups(self):
    special_settings = pgsettinggroup.SettingGroup("special")
    special_settings.add([self.autocrop_setting_dict])
    
    main_settings = pgsettinggroup.SettingGroup("main")
    main_settings.add([self.autocrop_setting_dict])
    
    self.settings.add([special_settings, main_settings])
    
    self.assertIn("autocrop", special_settings)
    self.assertIn("autocrop", main_settings)
    self.assertNotEqual(special_settings["autocrop"], main_settings["autocrop"])


class TestSettingGroupAddWithSettingDictAndSettingAttributes(unittest.TestCase):
  
  def test_add_with_group_level_attributes(self):
    settings = pgsettinggroup.SettingGroup(
      name="main", setting_attributes={"pdb_type": None})
    settings.add([
      {
       "type": pgsetting.SettingTypes.boolean,
       "name": "only_visible_layers",
       "default_value": False,
      },
      {
       "type": pgsetting.SettingTypes.boolean,
       "name": "autocrop",
       "default_value": False,
      }
    ])
    
    self.assertEqual(settings["only_visible_layers"].pdb_type, None)
    self.assertEqual(settings["autocrop"].pdb_type, None)
  
  def test_add_with_group_level_attributes_overridden_by_setting_attributes(self):
    settings = pgsettinggroup.SettingGroup(
      name="main", setting_attributes={"pdb_type": None})
    settings.add([
      {
       "type": pgsetting.SettingTypes.boolean,
       "name": "only_visible_layers",
       "default_value": False,
      },
      {
       "type": pgsetting.SettingTypes.boolean,
       "name": "autocrop",
       "default_value": False,
       "pdb_type": pgsetting.SettingPdbTypes.int16
      }
    ])
    
    self.assertEqual(settings["only_visible_layers"].pdb_type, None)
    self.assertEqual(settings["autocrop"].pdb_type, pgsetting.SettingPdbTypes.int16)
  
  def test_add_with_group_level_attributes_overridden_by_child_group_attributes(self):
    additional_settings = pgsettinggroup.SettingGroup(
      name="additional", setting_attributes={"pdb_type": pgsetting.SettingPdbTypes.int16})
    
    additional_settings.add([
        {
         "type": pgsetting.SettingTypes.boolean,
         "name": "autocrop",
         "default_value": False
        }
    ])
    
    settings = pgsettinggroup.SettingGroup(
      name="main", setting_attributes={"pdb_type": None, "display_name": "Setting name"})
    
    settings.add([
      {
       "type": pgsetting.SettingTypes.boolean,
       "name": "only_visible_layers",
       "default_value": False,
      },
      additional_settings
    ])
    
    self.assertEqual(settings["only_visible_layers"].pdb_type, None)
    self.assertEqual(
      settings["additional/autocrop"].pdb_type, pgsetting.SettingPdbTypes.int16)
    self.assertEqual(settings["only_visible_layers"].display_name, "Setting name")
    self.assertEqual(settings["additional/autocrop"].display_name, "Autocrop")


#===============================================================================


class TestSettingGroup(unittest.TestCase):
  
  def setUp(self):
    self.settings = stubs_pgsettinggroup.create_test_settings()
    
    self.first_plugin_run_setting_dict = {
      "type": pgsetting.SettingTypes.boolean,
      "name": "first_plugin_run",
      "default_value": False}
    
    self.special_settings = pgsettinggroup.SettingGroup("special")
    self.special_settings.add([self.first_plugin_run_setting_dict])
  
  def test_add_same_setting_in_same_group(self):
    with self.assertRaises(ValueError):
      self.special_settings.add([self.special_settings["first_plugin_run"]])
  
  def test_add_same_setting_in_different_child_groups(self):
    self.settings.add([self.special_settings["first_plugin_run"], self.special_settings])
    
    self.assertIn("first_plugin_run", self.settings)
    self.assertIn("first_plugin_run", self.special_settings)
    self.assertEqual(
      self.settings["first_plugin_run"], self.special_settings["first_plugin_run"])
  
  def test_add_setting_group(self):
    self.settings.add([self.special_settings])
    
    self.assertIn("special", self.settings)
    self.assertEqual(self.settings["special"], self.special_settings)
  
  def test_add_same_setting_group_in_same_parent_group(self):
    self.settings.add([self.special_settings])
    with self.assertRaises(ValueError):
      self.settings.add([self.special_settings])
  
  def test_add_same_setting_group_as_child_of_itself(self):
    with self.assertRaises(ValueError):
      self.special_settings.add([self.special_settings])
  
  def test_add_different_setting_groups_with_same_name_in_different_child_groups(self):
    main_settings = pgsettinggroup.SettingGroup("main")
    main_settings.add([self.special_settings])
    
    different_special_settings = pgsettinggroup.SettingGroup("special")
    self.settings.add([main_settings, different_special_settings])
    
    self.assertIn("special", self.settings)
    self.assertIn("special", main_settings)
    self.assertNotEqual(self.settings["special"], main_settings["special"])
  
  def test_add_same_setting_group_in_different_child_groups(self):
    main_settings = pgsettinggroup.SettingGroup("main")
    main_settings.add([self.special_settings])
    
    self.settings.add([self.special_settings, main_settings])
    
    self.assertIn("special", self.settings)
    self.assertIn("special", main_settings)
    self.assertEqual(self.settings["special"], main_settings["special"])
  
  def test_remove_settings(self):
    self.settings.remove(["file_extension", "only_visible_layers"])
    self.assertNotIn("file_extension", self.settings)
    self.assertNotIn("only_visible_layers", self.settings)
    self.assertIn("overwrite_mode", self.settings)
  
  def test_remove_setting_from_setting_group_and_then_setting_group(self):
    self.settings.add([self.special_settings])
    
    self.settings["special"].remove(["first_plugin_run"])
    self.assertNotIn("first_plugin_run", self.settings["special"])
    
    self.settings.remove(["special"])
    self.assertNotIn("special", self.settings)
  
  def test_remove_settings_raise_error_if_invalid_name(self):
    with self.assertRaises(KeyError):
      self.settings.remove(["file_extension", "invalid_setting"])
  
  def test_remove_setting_raise_error_if_already_removed(self):
    self.settings.remove(["file_extension"])
    with self.assertRaises(KeyError):
      self.settings.remove(["file_extension"])
  
  def test_reset_settings_and_nested_groups_and_ignore_specified_settings(self):
    self.settings.add([self.special_settings])
    self.settings["file_extension"].tags.add("ignore_reset")
    self.settings["overwrite_mode"].tags.update(
      ["ignore_reset", "ignore_apply_gui_value_to_setting"])
    
    self.settings["file_extension"].set_value("gif")
    self.settings["only_visible_layers"].set_value(True)
    self.settings["overwrite_mode"].set_item("skip")
    self.settings["special"]["first_plugin_run"].set_value(True)
    
    self.settings.reset()
    
    self.assertEqual(self.settings["file_extension"].value, "gif")
    self.assertEqual(
      self.settings["overwrite_mode"].value,
      self.settings["overwrite_mode"].items["skip"])
    self.assertEqual(
      self.settings["only_visible_layers"].value,
      self.settings["only_visible_layers"].default_value)
    self.assertEqual(
      self.settings["special"]["first_plugin_run"].value,
      self.settings["special"]["first_plugin_run"].default_value)
  
  def test_reset_ignore_nested_group(self):
    self.settings.add([self.special_settings])
    self.settings["special"].tags.add("ignore_reset")
    
    self.settings["special"]["first_plugin_run"].set_value(True)
    
    self.settings.reset()
    
    self.assertNotEqual(
      self.settings["special"]["first_plugin_run"].value,
      self.settings["special"]["first_plugin_run"].default_value)
  

#===============================================================================


class TestSettingGroupHierarchical(unittest.TestCase):
  
  def setUp(self):
    self.settings = stubs_pgsettinggroup.create_test_settings_hierarchical()
  
  def test_get_setting_via_paths(self):
    self.assertEqual(
      self.settings["main/file_extension"], self.settings["main"]["file_extension"])
    self.assertEqual(
      self.settings["advanced/only_visible_layers"],
      self.settings["advanced"]["only_visible_layers"])
    self.assertEqual(
      self.settings["advanced/overwrite_mode"],
      self.settings["advanced"]["overwrite_mode"])
  
  def test_get_setting_via_paths_multiple_levels(self):
    expert_settings = pgsettinggroup.SettingGroup("expert")
    expert_settings.add([
        {
         "type": pgsetting.SettingTypes.integer,
         "name": "file_extension_strip_mode",
         "default_value": 0
        }
    ])
    
    self.settings["advanced"].add([expert_settings])
    
    self.assertEqual(
      self.settings["advanced/expert/file_extension_strip_mode"],
      self.settings["advanced"]["expert"]["file_extension_strip_mode"])
    
  def test_get_setting_via_paths_invalid_group(self):
    with self.assertRaises(KeyError):
      unused_ = self.settings["advanced/invalid_group/file_extension_strip_mode"]
  
  def test_contains_via_paths(self):
    self.assertIn("main/file_extension", self.settings)
    self.assertNotIn("main/invalid_setting", self.settings)
  
  def test_walk(self):
    walked_settings = list(self.settings.walk())
    
    self.assertIn(self.settings["main"]["file_extension"], walked_settings)
    self.assertIn(self.settings["advanced"]["only_visible_layers"], walked_settings)
    self.assertIn(self.settings["advanced"]["overwrite_mode"], walked_settings)
  
  def test_walk_ignore_settings_with_tag(self):
    self.settings["main"]["file_extension"].tags.add("ignore_reset")
    self.settings["advanced"]["overwrite_mode"].tags.update(
      ["ignore_reset", "ignore_apply_gui_value_to_setting"])
    
    walked_settings = list(self.settings.walk(
      include_setting_func=lambda setting: "ignore_reset" not in setting.tags))
    
    self.assertNotIn(self.settings["main"]["file_extension"], walked_settings)
    self.assertIn(self.settings["advanced"]["only_visible_layers"], walked_settings)
    self.assertNotIn(self.settings["advanced"]["overwrite_mode"], walked_settings)
  
  def test_walk_ignore_settings_in_group_with_tag(self):
    self.settings["advanced"].tags.add("ignore_apply_gui_value_to_setting")
    
    walked_settings = list(
      self.settings.walk(include_setting_func=(
        lambda setting: "ignore_apply_gui_value_to_setting" not in setting.tags)))
    
    self.assertIn(self.settings["main"]["file_extension"], walked_settings)
    self.assertNotIn(self.settings["advanced"]["only_visible_layers"], walked_settings)
    self.assertNotIn(self.settings["advanced"]["overwrite_mode"], walked_settings)
  
  def test_walk_include_groups(self):
    walked_settings = list(self.settings.walk(include_groups=True))
    
    self.assertIn(self.settings["main"], walked_settings)
    self.assertIn(self.settings["main"]["file_extension"], walked_settings)
    self.assertIn(self.settings["advanced"], walked_settings)
    self.assertIn(self.settings["advanced"]["only_visible_layers"], walked_settings)
    self.assertIn(self.settings["advanced"]["overwrite_mode"], walked_settings)
    self.assertNotIn(self.settings, walked_settings)
  
  def test_walk_ignore_settings_in_group_with_tag_include_groups(self):
    self.settings["advanced"].tags.add("ignore_apply_gui_value_to_setting")
    
    walked_settings = list(
      self.settings.walk(
        include_setting_func=(
          lambda setting: "ignore_apply_gui_value_to_setting" not in setting.tags),
        include_groups=True))
    
    self.assertIn(self.settings["main"], walked_settings)
    self.assertIn(self.settings["main"]["file_extension"], walked_settings)
    self.assertNotIn(self.settings["advanced"], walked_settings)
    self.assertNotIn(self.settings["advanced"]["only_visible_layers"], walked_settings)
    self.assertNotIn(self.settings["advanced"]["overwrite_mode"], walked_settings)
  
  def test_walk_with_callbacks(self):
    walked_settings, walk_callbacks = self._get_test_data_for_walking_group()
    
    list(self.settings.walk(include_groups=True, walk_callbacks=walk_callbacks))
    
    self.assertEqual(
      walked_settings,
      ["main", "file_extension", "main_end",
       "advanced", "only_visible_layers", "overwrite_mode", "advanced_end"])
  
  def test_walk_with_callbacks_and_ignore_settings(self):
    self.settings["main"].tags.add("ignore_reset")
    self.settings["advanced"]["overwrite_mode"].tags.update(["ignore_reset"])
    
    walked_settings, walk_callbacks = self._get_test_data_for_walking_group()
    
    list(self.settings.walk(
      include_setting_func=lambda setting: "ignore_reset" not in setting.tags,
      include_groups=True,
      walk_callbacks=walk_callbacks))
    
    self.assertEqual(walked_settings, ["advanced", "only_visible_layers", "advanced_end"])
  
  def test_walk_with_callbacks_empty_group(self):
    self.settings["main"].remove(["file_extension"])
    
    walked_settings, walk_callbacks = self._get_test_data_for_walking_group()
    
    list(self.settings.walk(include_groups=True, walk_callbacks=walk_callbacks))
    
    self.assertEqual(
      walked_settings,
      ["main", "main_end", "advanced", "only_visible_layers", "overwrite_mode",
       "advanced_end"])
  
  @staticmethod
  def _get_test_data_for_walking_group():
    walked_settings = []
    
    def _append_setting_name(setting):
      walked_settings.append(setting.name)
    
    def _append_setting_name_and_end_group_walk_indicator(setting):
      walked_settings.append(setting.name + "_end")
    
    walk_callbacks = pgsettinggroup.SettingGroupWalkCallbacks()
    walk_callbacks.on_visit_setting = _append_setting_name
    walk_callbacks.on_visit_group = _append_setting_name
    walk_callbacks.on_end_group_walk = _append_setting_name_and_end_group_walk_indicator
    
    return walked_settings, walk_callbacks


#===============================================================================


@mock.patch(
  pgconstants.PYGIMPLIB_MODULE_PATH + ".pgsettingpersistor.SettingPersistor.save",
  return_value=(pgsettingpersistor.SettingPersistor.SUCCESS, ""))
@mock.patch(
  pgconstants.PYGIMPLIB_MODULE_PATH + ".pgsettingpersistor.SettingPersistor.load",
  return_value=(pgsettingpersistor.SettingPersistor.SUCCESS, ""))
class TestSettingGroupLoadSave(unittest.TestCase):
  
  def setUp(self):
    self.settings = stubs_pgsettinggroup.create_test_settings_load_save()
  
  def test_load_save_setting_sources_not_in_group_and_in_settings(
        self, mock_load, mock_save):
    settings = stubs_pgsettinggroup.create_test_settings()
    
    settings.load()
    self.assertEqual(mock_load.call_count, 1)
    self.assertEqual([settings["only_visible_layers"]], mock_load.call_args[0][0])
    
    settings.save()
    self.assertEqual(mock_save.call_count, 1)
    self.assertEqual([settings["only_visible_layers"]], mock_save.call_args[0][0])
  
  def test_load_save_setting_sources_in_group_and_in_settings(self, mock_load, mock_save):
    self.settings.load()
    self.assertEqual(mock_load.call_count, 3)
    self.assertEqual(
      [self.settings["main/file_extension"]], mock_load.call_args_list[0][0][0])
    self.assertEqual(
      [self.settings["advanced/only_visible_layers"]], mock_load.call_args_list[1][0][0])
    self.assertEqual(
      [self.settings["advanced/autocrop"]], mock_load.call_args_list[2][0][0])
    
    self.settings.save()
    self.assertEqual(mock_save.call_count, 3)
    self.assertEqual(
      [self.settings["main/file_extension"]], mock_save.call_args_list[0][0][0])
    self.assertEqual(
      [self.settings["advanced/only_visible_layers"]], mock_save.call_args_list[1][0][0])
    self.assertEqual(
      [self.settings["advanced/autocrop"]], mock_save.call_args_list[2][0][0])
  
  def test_load_save_return_statuses(self, mock_load, mock_save):
    load_save_calls_return_values = [
      (pgsettingpersistor.SettingPersistor.SUCCESS, ""),
      (pgsettingpersistor.SettingPersistor.SUCCESS, ""),
      (pgsettingpersistor.SettingPersistor.SUCCESS, "")]
    
    mock_load.side_effect = load_save_calls_return_values
    status, unused_ = self.settings.load()
    self.assertEqual(status, pgsettingpersistor.SettingPersistor.SUCCESS)
    
    mock_save.side_effect = load_save_calls_return_values
    status, unused_ = self.settings.save()
    self.assertEqual(status, pgsettingpersistor.SettingPersistor.SUCCESS)
    
    load_save_calls_return_values[1] = (
      pgsettingpersistor.SettingPersistor.NOT_ALL_SETTINGS_FOUND, "")
    mock_load.side_effect = load_save_calls_return_values
    status, unused_ = self.settings.load()
    self.assertEqual(status, pgsettingpersistor.SettingPersistor.NOT_ALL_SETTINGS_FOUND)
    
    load_save_calls_return_values[1] = (
      pgsettingpersistor.SettingPersistor.NOT_ALL_SETTINGS_FOUND, "")
    mock_save.side_effect = load_save_calls_return_values
    status, unused_ = self.settings.save()
    self.assertEqual(status, pgsettingpersistor.SettingPersistor.NOT_ALL_SETTINGS_FOUND)
    
    load_save_calls_return_values[2] = (
      pgsettingpersistor.SettingPersistor.READ_FAIL, "")
    mock_load.side_effect = load_save_calls_return_values
    status, unused_ = self.settings.load()
    self.assertEqual(status, pgsettingpersistor.SettingPersistor.READ_FAIL)
    
    load_save_calls_return_values[2] = (
      pgsettingpersistor.SettingPersistor.WRITE_FAIL, "")
    mock_save.side_effect = load_save_calls_return_values
    status, unused_ = self.settings.save()
    self.assertEqual(status, pgsettingpersistor.SettingPersistor.WRITE_FAIL)


#===============================================================================


class TestSettingGroupGui(unittest.TestCase):

  def setUp(self):
    self.settings = pgsettinggroup.SettingGroup("main")
    self.settings.add([
      {
        "type": stubs_pgsetting.SettingWithGuiStub,
        "name": "file_extension",
        "default_value": "bmp",
      },
      {
        "type": stubs_pgsetting.SettingWithGuiStub,
        "name": "only_visible_layers",
        "default_value": False,
      },
    ])

  def test_initialize_gui_without_custom_gui(self):
    self.settings.initialize_gui()
    
    self.assertIs(
      type(self.settings["file_extension"].gui),
      stubs_pgsetting.CheckButtonPresenterStub)
    self.assertIs(
      type(self.settings["file_extension"].gui.element),
      stubs_pgsetting.CheckButtonStub)
    self.assertIs(
      type(self.settings["only_visible_layers"].gui),
      stubs_pgsetting.CheckButtonPresenterStub)
    self.assertIs(
      type(self.settings["only_visible_layers"].gui.element),
      stubs_pgsetting.CheckButtonStub)
  
  def test_initialize_gui_with_custom_gui(self):
    file_extension_widget = stubs_pgsetting.GuiWidgetStub("png")
    
    self.settings.initialize_gui(custom_gui={
      "file_extension": [stubs_pgsetting.SettingPresenterStub, file_extension_widget]})
    
    self.assertIs(
      type(self.settings["file_extension"].gui),
      stubs_pgsetting.SettingPresenterStub)
    self.assertIs(
      type(self.settings["file_extension"].gui.element),
      stubs_pgsetting.GuiWidgetStub)
    # It's "bmp", not "png", since the setting value overrides the initial GUI
    # element value.
    self.assertEqual(file_extension_widget.value, "bmp")
    self.assertIs(
      type(self.settings["only_visible_layers"].gui),
      stubs_pgsetting.CheckButtonPresenterStub)
    self.assertIs(
      type(self.settings["only_visible_layers"].gui.element),
      stubs_pgsetting.CheckButtonStub)
  
  def test_apply_gui_values_to_settings_ignores_specified_settings(self):
    file_extension_widget = stubs_pgsetting.GuiWidgetStub(None)
    only_visible_layers_widget = stubs_pgsetting.GuiWidgetStub(None)
    self.settings["file_extension"].set_gui(
      stubs_pgsetting.SettingPresenterStub, file_extension_widget)
    self.settings["only_visible_layers"].set_gui(
      stubs_pgsetting.SettingPresenterStub, only_visible_layers_widget)
    
    file_extension_widget.set_value("gif")
    only_visible_layers_widget.set_value(True)
    
    self.settings.apply_gui_values_to_settings()
    
    self.assertEqual(self.settings["file_extension"].value, "gif")
    self.assertEqual(self.settings["only_visible_layers"].value, True)
