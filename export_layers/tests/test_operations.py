# -*- coding: utf-8 -*-
#
# This file is part of Export Layers.
#
# Copyright (C) 2013-2018 khalim19 <khalim19@gmail.com>
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
# along with Export Layers.  If not, see <https://www.gnu.org/licenses/>.

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import unittest

import mock
import parameterized

from export_layers import pygimplib
from export_layers.pygimplib import pgconstants
from export_layers.pygimplib import pgsetting
from export_layers.pygimplib import pgsettingpersistor
from export_layers.pygimplib import pgutils

from export_layers.pygimplib.tests import stubs_gimp

from .. import operations

pygimplib.init()


def get_builtin_operations_list():
  return [
    {
      "name": "autocrop",
      "function": pgutils.empty_func,
      "enabled": True,
      "display_name": "Autocrop",
      "operation_groups": ["basic"],
      "arguments": [
        {
          "type": pgsetting.SettingTypes.integer,
          "name": "offset_x",
          "default_value": 0,
        },
        {
          "type": pgsetting.SettingTypes.integer,
          "name": "offset_y",
          "default_value": 0,
        },
      ]
    },
    {
      "name": "autocrop_background",
      "function": pgutils.empty_func,
      "enabled": False,
      "display_name": "Autocrop background layers",
    },
    {
      "name": "autocrop_foreground",
      "function": pgutils.empty_func,
      "enabled": False,
      "display_name": "Autocrop foreground layers",
    },
  ]


def get_builtin_constraints_list():
  return [
    {
      "name": "only_visible_layers",
      "function": pgutils.empty_func,
      "enabled": False,
      "display_name": "Only visible layers",
    },
    {
      "name": "include_layers",
      "function": pgutils.empty_func,
      "enabled": True,
      "display_name": "Include layers",
      "subfilter": "layer_types",
    },
  ]


def _find_in_added_data(operations, operation_name):
  return next(
    (dict_ for dict_ in operations["added_data"].value
     if dict_["name"] == operation_name),
    None)


class TestCreateOperations(unittest.TestCase):
  
  @parameterized.parameterized.expand([
    ("operations",
     "operations",
     get_builtin_operations_list,
     "operation",
     ["operation"],
     {"operation_groups": {
        "autocrop": ["basic"],
        "autocrop_background": None,
        "autocrop_foreground": None}}),
    
    ("constraints",
     "constraints",
     get_builtin_constraints_list,
     "constraint",
     ["operation", "constraint"],
     {"subfilter": {
        "only_visible_layers": None,
        "include_layers": "layer_types"}}),
  ])
  def test_create(
        self,
        test_case_name_suffix,
        name,
        builtin_operations_data_func,
        type_,
        tags,
        additional_builtin_data):
    builtin_operations_list = builtin_operations_data_func()
    
    settings = operations.create(name, builtin_operations_list, type_=type_)
    
    self.assertIn("added", settings)
    self.assertEqual(len(settings["added"]), 0)
    self.assertIn("builtin", settings)
    self.assertIn("builtin_data", settings)
    
    for operation_dict in builtin_operations_list:
      self.assertEqual(operation_dict["operation_type"], type_)
    
    self.assertFalse(settings["added_data"].value)
    
    builtin_operations_dict = {
      operation_dict["name"]: operation_dict
      for operation_dict in builtin_operations_list}
    
    for operation_name, operation_dict in builtin_operations_dict.items():
      operation = settings["builtin"][operation_name]
      
      self.assertIn(operation_name, settings["builtin"])
      
      self.assertEqual(operation.name, operation_name)
      self.assertEqual(operation["function"].value, operation_dict["function"])
      self.assertEqual(operation["enabled"].value, operation_dict["enabled"])
      self.assertEqual(operation["display_name"].value, operation_dict["display_name"])
      self.assertSetEqual(operation.tags, set(tags))
      
      if "arguments" in operation_dict:
        self.assertEqual(len(operation["arguments"]), len(operation_dict["arguments"]))
        
        for argument_setting, argument_dict in zip(
              operation["arguments"], operation_dict["arguments"]):
          self.assertEqual(type(argument_setting), argument_dict["type"])
          self.assertEqual(argument_setting.name, argument_dict["name"])
          self.assertEqual(argument_setting.value, argument_dict["default_value"])
    
    for attribute_name, attribute_dict in additional_builtin_data.items():
      for operation_name, attribute_value in attribute_dict.items():
        operation = settings["builtin"][operation_name]
        self.assertEqual(operation[attribute_name].value, attribute_value)
  
  def test_create_invalid_type(self):
    with self.assertRaises(ValueError):
      operations.create(
        "operations", get_builtin_operations_list(), type_="invalid_type")
  
  @parameterized.parameterized.expand([
    ("by_index",
     0,
     "autocrop"),
    
    ("by_name",
     "autocrop",
     "autocrop"),
  ])
  def test_create_builtin_initial_operations_are_added(
        self,
        test_case_name_suffix,
        builtin_initial_operation_index_or_name,
        expected_operation_name):
    builtin_operations = get_builtin_operations_list()
    
    try:
      initial_operation = builtin_operations[builtin_initial_operation_index_or_name]
    except TypeError:
      initial_operation = builtin_initial_operation_index_or_name
    
    settings = operations.create(
      "operations",
      builtin_operations,
      initial_operations=[initial_operation])
    
    self.assertDictEqual(
      _find_in_added_data(settings, expected_operation_name),
      settings["builtin_data"].value[expected_operation_name])
    
    self.assertIn(expected_operation_name, settings["added"])
    
    self.assertIsNot(
      settings["builtin_data"].value["autocrop"],
      _find_in_added_data(settings, "autocrop"))


class TestManageOperations(unittest.TestCase):
  
  def setUp(self):
    self.settings = operations.create("operations", get_builtin_operations_list())
  
  def test_add(self):
    operation = operations.add(self.settings, "autocrop")
    
    self.assertIn("autocrop", self.settings["added"])
    self.assertNotEqual(
      self.settings["added/autocrop"],
      self.settings["builtin/autocrop"])
    
    self.assertEqual(operation, self.settings["added/autocrop"])
    
    self.assertDictEqual(
      self.settings["builtin_data"].value["autocrop"],
      _find_in_added_data(self.settings, "autocrop"))
    
    self.assertIsNot(
      self.settings["builtin_data"].value["autocrop"],
      _find_in_added_data(self.settings, "autocrop"))
  
  def test_add_existing_name_is_uniquified(self):
    operation = operations.add(self.settings, "autocrop")
    operation_2 = operations.add(self.settings, "autocrop")
    
    self.assertIn("autocrop", self.settings["added"])
    self.assertIn("autocrop_2", self.settings["added"])
    self.assertEqual(
      self.settings["added/autocrop_2/display_name"].value, "Autocrop (2)")
    
    self.assertEqual(operation, self.settings["added/autocrop"])
    self.assertEqual(operation_2, self.settings["added/autocrop_2"])
    
    self.assertIsNotNone(_find_in_added_data(self.settings, "autocrop"))
    self.assertIsNotNone(_find_in_added_data(self.settings, "autocrop_2"))
    self.assertEqual(
      _find_in_added_data(self.settings, "autocrop_2")["display_name"],
      "Autocrop (2)")
    
    self.assertEqual(len(self.settings["added"]), 2)
    self.assertEqual(len(self.settings["added_data"].value), 2)
  
  def test_add_invokes_before_add_operation_event(self):
    invoked_event_args = []
    
    def on_before_add_operation(operations, operation_name):
      invoked_event_args.append((operations, operation_name))
      self.assertNotIn("autocrop", self.settings)
    
    self.settings.connect_event("before-add-operation", on_before_add_operation)
    
    operations.add(self.settings, "autocrop")
    
    self.assertIs(invoked_event_args[0][0], self.settings)
    self.assertEqual(invoked_event_args[0][1], "autocrop")
  
  @parameterized.parameterized.expand([
    ("",
     ["autocrop"],),
    
    ("and_passes_original_operation_name",
     ["autocrop", "autocrop"],),
  ])
  def test_add_invokes_after_add_operation_event(
        self, test_case_name_suffix, names_to_add):
    invoked_event_args = []
    
    def on_after_add_operation(operations, operation, orig_operation_name):
      invoked_event_args.append((operations, operation, orig_operation_name))
    
    self.settings.connect_event("after-add-operation", on_after_add_operation)
    
    for operation_name in names_to_add:
      operation = operations.add(self.settings, operation_name)
      
      self.assertIs(invoked_event_args[-1][0], self.settings)
      self.assertIs(invoked_event_args[-1][1], operation)
      self.assertEqual(invoked_event_args[-1][2], operation_name)
  
  def test_add_modifying_added_operation_modifies_nothing_else(self):
    operation = operations.add(self.settings, "autocrop")
    builtin_operation = self.settings["builtin/autocrop"]
    
    operation["enabled"].set_value(False)
    operation["arguments/offset_x"].set_value(20)
    operation["arguments/offset_y"].set_value(10)
    
    self.assertNotEqual(operation["enabled"], builtin_operation["enabled"])
    self.assertNotEqual(
      operation["arguments/offset_x"], builtin_operation["arguments/offset_x"])
    self.assertNotEqual(
      operation["arguments/offset_y"], builtin_operation["arguments/offset_y"])
    
    self.assertNotEqual(
      operation["enabled"], self.settings["builtin_data"].value["autocrop"]["enabled"])
    self.assertNotEqual(
      operation["enabled"], _find_in_added_data(self.settings, "autocrop")["enabled"])
  
  @parameterized.parameterized.expand([
    ("middle_to_first",
     "autocrop_background",
     0,
     ["autocrop_background", "autocrop", "autocrop_foreground"]),
    
    ("middle_to_last",
     "autocrop_background",
     2,
     ["autocrop", "autocrop_foreground", "autocrop_background"]),
    
    ("middle_to_last_above_bounds",
     "autocrop_background",
     3,
     ["autocrop", "autocrop_foreground", "autocrop_background"]),
    
    ("first_to_middle",
     "autocrop",
     1,
     ["autocrop_background", "autocrop", "autocrop_foreground"]),
    
    ("last_to_middle",
     "autocrop_foreground",
     1,
     ["autocrop", "autocrop_foreground", "autocrop_background"]),
    
    ("middle_to_last_negative_position",
     "autocrop_background",
     -1,
     ["autocrop", "autocrop_foreground", "autocrop_background"]),
    
    ("middle_to_middle_negative_position",
     "autocrop_background",
     -2,
     ["autocrop", "autocrop_background", "autocrop_foreground"]),
  ])
  def test_reorder(
        self,
        test_case_name_suffix,
        operation_name,
        new_position,
        expected_ordered_operation_names):
    for operation in self.settings["builtin"]:
      operations.add(self.settings, operation.name)
    
    operations.reorder(self.settings, operation_name, new_position)
    
    self.assertEqual(
      [operation_dict["name"] for operation_dict in self.settings["added_data"].value],
      expected_ordered_operation_names)
  
  def test_reorder_nonexisting_operation_name(self):
    with self.assertRaises(ValueError):
      operations.reorder(self.settings, "invalid_operation", 0)
  
  @parameterized.parameterized.expand([
    ("single_setting",
     ["autocrop", "autocrop_background", "autocrop_foreground"],
     ["autocrop"],
     ["autocrop_background", "autocrop_foreground"]),
    
    ("setting_added_twice_removed_both",
     ["autocrop", "autocrop", "autocrop_background", "autocrop_foreground"],
     ["autocrop", "autocrop_2"],
     ["autocrop_background", "autocrop_foreground"]),
    
    ("setting_added_twice_removed_first",
     ["autocrop", "autocrop", "autocrop_background", "autocrop_foreground"],
     ["autocrop"],
     ["autocrop_background", "autocrop_2", "autocrop_foreground"]),
  ])
  def test_remove(
        self,
        test_case_name_suffix,
        names_to_add,
        names_to_remove,
        names_to_keep):
    for operation_name in names_to_add:
      operations.add(self.settings, operation_name)
    
    for operation_name in names_to_remove:
      operations.remove(self.settings, operation_name)
    
      self.assertNotIn(operation_name, self.settings["added"])
      self.assertIsNone(_find_in_added_data(self.settings, operation_name))
    
    for operation_name in names_to_keep:
      self.assertIn(operation_name, self.settings["added"])
      self.assertIsNotNone(_find_in_added_data(self.settings, operation_name))
    
    for operation_name in list(set(names_to_add)):
      self.assertIn(operation_name, self.settings["builtin"])
  
  def test_remove_nonexisting_operation_name(self):
    with self.assertRaises(ValueError):
      operations.remove(self.settings, "invalid_operation")
  
  def test_clear(self):
    for operation in self.settings["builtin"]:
      operations.add(self.settings, operation.name)
    
    operations.clear(self.settings)
    
    self.assertFalse(self.settings["added"])
    self.assertFalse(self.settings["added_data"].value)
    self.assertTrue(self.settings["builtin"])
    self.assertTrue(self.settings["builtin_data"])
  
  def test_clear_resets_to_initial_operations(self):
    settings = operations.create(
      "operations",
      get_builtin_operations_list(),
      initial_operations=["autocrop"])
    
    operations.add(settings, "autocrop_background")
    operations.clear(settings)
    
    self.assertIn("autocrop", settings["added"])
    self.assertEqual(len(settings["added"]), 1)
    self.assertNotIn("autocrop_background", settings)
    
    self.assertEqual(len(settings["added_data"].value), 1)
    self.assertDictEqual(
      _find_in_added_data(settings, "autocrop"),
      settings["builtin_data"].value["autocrop"])


class TestWalkOperations(unittest.TestCase):
  
  _walk_parameters = [
    ("operations",
     "operation",
     ["autocrop",
      "autocrop_background",
      "autocrop_foreground"]),
    
    ("constraints",
     "constraint",
     []),
    
    ("enabled",
     "enabled",
     ["autocrop/enabled",
      "autocrop_background/enabled",
      "autocrop_foreground/enabled"]),
    
    ("nonexistent_setting",
     "nonexistent_setting",
     []),
  ]
  
  def setUp(self):
    self.settings = operations.create("operations", get_builtin_operations_list())
  
  @parameterized.parameterized.expand(_walk_parameters)
  def test_walk_builtin(
        self, test_case_name_suffix, setting_name, expected_setting_paths):
    self.assertListEqual(
      list(operations.walk(
        self.settings, setting_name=setting_name, subgroup="builtin")),
      [self.settings["builtin/" + path] for path in expected_setting_paths])
  
  @parameterized.parameterized.expand(_walk_parameters)
  def test_walk_added(
        self, test_case_name_suffix, setting_name, expected_setting_paths):
    for operation in self.settings["builtin"]:
      operations.add(self.settings, operation.name)
    
    self.assertListEqual(
      list(operations.walk(
        self.settings, setting_name=setting_name, subgroup="added")),
      [self.settings["added/" + path] for path in expected_setting_paths])
  
  @parameterized.parameterized.expand([
    ("operations",
     "operation",
     [("autocrop", 1)],
     ["autocrop_background",
      "autocrop",
      "autocrop_foreground"]),
    
    ("operations",
     "operation",
     [("autocrop_foreground", 1)],
     ["autocrop",
      "autocrop_foreground",
      "autocrop_background"]),
    
    ("enabled",
     "enabled",
     [("autocrop", 1)],
     ["autocrop_background/enabled",
      "autocrop/enabled",
      "autocrop_foreground/enabled"]),
    
    ("enabled",
     "enabled",
     [("autocrop_foreground", 1)],
     ["autocrop/enabled",
      "autocrop_foreground/enabled",
      "autocrop_background/enabled"]),
  ])
  def test_walk_added_after_reordering(
        self,
        test_case_name_suffix,
        setting_name,
        operations_to_reorder,
        expected_setting_paths):
    for operation in self.settings["builtin"]:
      operations.add(self.settings, operation.name)
    
    for operation_name, new_position in operations_to_reorder:
      operations.reorder(self.settings, operation_name, new_position)
    
    self.assertListEqual(
      list(operations.walk(
        self.settings, setting_name=setting_name, subgroup="added")),
      [self.settings["added/" + path] for path in expected_setting_paths])


@mock.patch(
  pgconstants.PYGIMPLIB_MODULE_PATH + ".pgsettingsources.gimpshelf.shelf",
  new_callable=stubs_gimp.ShelfStub)
@mock.patch(
  pgconstants.PYGIMPLIB_MODULE_PATH + ".pgsettingsources.gimp",
  new_callable=stubs_gimp.GimpModuleStub)
class TestLoadSaveOperations(unittest.TestCase):
  
  def setUp(self):
    self.settings = operations.create("operations", get_builtin_operations_list())
  
  @mock.patch(
    pgconstants.PYGIMPLIB_MODULE_PATH + ".pgsettingpersistor.SettingPersistor.save",
    return_value=(pgsettingpersistor.SettingPersistor.SUCCESS, ""))
  @mock.patch(
    pgconstants.PYGIMPLIB_MODULE_PATH + ".pgsettingpersistor.SettingPersistor.load",
    return_value=(pgsettingpersistor.SettingPersistor.SUCCESS, ""))
  def test_save_load_affects_only_added_data(
        self, mock_load, mock_save, mock_persistent_source, mock_session_source):
    self.settings.save()
    self.settings.load()
    
    self.assertEqual(mock_load.call_count, 1)
    self.assertEqual(len(mock_load.call_args[0][0]), 2)
    self.assertIn(self.settings["added_data"], mock_load.call_args[0][0])
    self.assertIn(self.settings["added_data_values"], mock_load.call_args[0][0])
    self.assertEqual(mock_save.call_count, 1)
    self.assertEqual(len(mock_save.call_args[0][0]), 2)
    self.assertIn(self.settings["added_data"], mock_save.call_args[0][0])
    self.assertIn(self.settings["added_data_values"], mock_save.call_args[0][0])
  
  def test_added_data_values_are_cleared_before_save(
        self,
        mock_persistent_source,
        mock_session_source):
    for operation_name in ["autocrop", "autocrop_background", "autocrop_foreground"]:
      operations.add(self.settings, operation_name)
    
    self.settings.save()
    
    operations.remove(self.settings, "autocrop")
    
    self.settings.save()
    
    for key in self.settings["added_data_values"].value:
      self.assertNotIn("autocrop/", key)
  
  @parameterized.parameterized.expand([
    ("",
     ["autocrop", "autocrop_background", "autocrop_foreground"]),
    
    ("preserves_uniquified_names",
     ["autocrop", "autocrop", "autocrop_background", "autocrop_foreground"]),
  ])
  def test_clears_before_load_creates_added_operations_after_load(
        self,
        mock_persistent_source,
        mock_session_source,
        test_case_name_suffix,
        names_to_add):
    for operation_name in names_to_add:
      operations.add(self.settings, operation_name)
    
    added_data_before_save = self.settings["added_data"].value
    
    self.settings.save()
    self.settings.load()
    
    self.assertEqual(len(self.settings["added_data"].value), len(names_to_add))
    for dict_before_save, dict_after_save in zip(
          added_data_before_save, self.settings["added_data"].value):
      self.assertDictEqual(dict_before_save, dict_after_save)
    
    self.assertEqual(len(self.settings["added"]), len(names_to_add))
    for added_setting, dict_after_save in zip(
          self.settings["added"], self.settings["added_data"].value):
      self.assertEqual(added_setting.name, dict_after_save["name"])
  
  def test_values_are_preserved_after_load(
        self, mock_persistent_source, mock_session_source):
    for operation in self.settings["builtin"]:
      operations.add(self.settings, operation.name)
    
    self.settings["added/autocrop_background/enabled"].set_value(True)
    self.settings["added/autocrop_background/operation_groups"].set_value(["background"])
    self.settings["added/autocrop_foreground/enabled"].set_value(True)
    self.settings["added/autocrop_foreground/operation_groups"].set_value(["foreground"])
    self.settings["added/autocrop/arguments/offset_x"].set_value(20)
    self.settings["added/autocrop/arguments/offset_y"].set_value(10)
    
    self.settings.save()
    self.settings.load()
    
    self.assertEqual(
      self.settings["added/autocrop_background/enabled"].value, True)
    self.assertEqual(
      self.settings["added/autocrop_background/operation_groups"].value, ["background"])
    self.assertEqual(
      self.settings["added/autocrop_foreground/enabled"].value, True)
    self.assertEqual(
      self.settings["added/autocrop_foreground/operation_groups"].value, ["foreground"])
    self.assertEqual(self.settings["added/autocrop/arguments/offset_x"].value, 20)
    self.assertEqual(self.settings["added/autocrop/arguments/offset_y"].value, 10)
  
  def test_added_data_values_is_filled_before_save_and_reset_on_clear(
        self, mock_persistent_source, mock_session_source):
    for operation in self.settings["builtin"]:
      operations.add(self.settings, operation.name)
    
    self.settings["added/autocrop_background/enabled"].set_value(True)
    self.settings["added/autocrop_background/operation_groups"].set_value(["background"])
    self.settings["added/autocrop/arguments/offset_x"].set_value(20)
    self.settings["added/autocrop/arguments/offset_y"].set_value(10)
    
    self.settings.save()
    
    self.assertTrue(self.settings["added_data_values"].value)
    
    operations.clear(self.settings)
    
    self.assertFalse(self.settings["added_data_values"].value)
  
  def test_load_if_added_data_not_found_sets_initial_operations(
        self, mock_persistent_source, mock_session_source):
    settings = operations.create(
      "operations",
      get_builtin_operations_list(),
      initial_operations=["autocrop"])
    
    for operation_name in ["autocrop_background", "autocrop_foreground"]:
      operations.add(settings, operation_name)
    
    settings.load()
    
    self.assertEqual(len(settings["added"]), 1)
    self.assertIn("autocrop", settings["added"])
    self.assertNotIn("autocrop_background", settings["added"])
    self.assertNotIn("autocrop_foreground", settings["added"])
  
  def test_load_if_added_data_found_overrides_initial_operations(
        self, mock_persistent_source, mock_session_source):
    settings = operations.create(
      "operations",
      get_builtin_operations_list(),
      initial_operations=["autocrop"])
    
    for operation_name in ["autocrop_background", "autocrop_foreground"]:
      operations.add(settings, operation_name)
    
    operations.remove(settings, "autocrop")
    
    settings.save()
    settings.load()
    
    self.assertEqual(len(settings["added"]), 2)
    self.assertNotIn("autocrop", settings["added"])
    self.assertIn("autocrop_background", settings["added"])
    self.assertIn("autocrop_foreground", settings["added"])
