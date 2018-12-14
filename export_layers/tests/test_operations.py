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

import collections
import unittest

import mock
import parameterized

import gimpenums

from export_layers import pygimplib
from export_layers.pygimplib import pgconstants
from export_layers.pygimplib import pgsetting
from export_layers.pygimplib import pgsettingpersistor
from export_layers.pygimplib import pgutils

from export_layers.pygimplib.tests import stubs_gimp

from .. import operations

pygimplib.init()


test_operations = [
  {
    "name": "autocrop",
    "type": "operation",
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
    ],
  },
  {
    "name": "autocrop_background",
    "type": "operation",
    "function": pgutils.empty_func,
    "enabled": False,
    "display_name": "Autocrop background layers",
  },
  {
    "name": "autocrop_foreground",
    "type": "operation",
    "function": pgutils.empty_func,
    "enabled": False,
    "display_name": "Autocrop foreground layers",
  },
]

test_constraints = [
  {
    "name": "only_visible_layers",
    "type": "constraint",
    "function": pgutils.empty_func,
    "enabled": False,
    "display_name": "Only visible layers",
  },
  {
    "name": "include_layers",
    "type": "constraint",
    "function": pgutils.empty_func,
    "enabled": True,
    "display_name": "Include layers",
    "subfilter": "layer_types",
  },
]


def get_operation_data(operations_list):
  return collections.OrderedDict(
    (operation_dict["name"], dict(operation_dict))
    for operation_dict in operations_list)


def _find_in_added_data(operations, operation_name):
  return next(
    (dict_ for dict_ in operations["added_data"].value
     if dict_["name"] == operation_name),
    None)


class TestCreateOperations(unittest.TestCase):
  
  @parameterized.parameterized.expand([
    ("operations", "operations"),
    ("constraints", "constraints"),
  ])
  def test_create(self, test_case_name_suffix, name):
    settings = operations.create(name)
    
    self.assertIn("added", settings)
    self.assertEqual(len(settings["added"]), 0)
    self.assertFalse(settings["added_data"].value)
  
  @parameterized.parameterized.expand([
    ("operation_with_default_group",
     "operations",
     test_operations,
     "autocrop_background",
     ["operation"],
     {"operation_groups": [operations.DEFAULT_OPERATIONS_GROUP]}),
    
    ("operation_with_custom_group",
     "operations",
     test_operations,
     "autocrop",
     ["operation"],
     {"operation_groups": ["basic"]}),
    
    ("constraint_with_default_subfilter",
     "constraints",
     test_constraints,
     "only_visible_layers",
     ["operation", "constraint"],
     {
       "operation_groups": [operations.DEFAULT_CONSTRAINTS_GROUP],
       "subfilter": None
     }),
    
    ("constraint_with_custom_subfilter",
     "constraints",
     test_constraints,
     "include_layers",
     ["operation", "constraint"],
     {
       "operation_groups": [operations.DEFAULT_CONSTRAINTS_GROUP],
       "subfilter": "layer_types",
     }),
  ])
  def test_create_initial_operations_are_added(
        self,
        test_case_name_suffix,
        name,
        test_operations_list,
        initial_operation_name,
        tags,
        additional_operation_attributes):
    initial_operation_dict = get_operation_data(
      test_operations_list)[initial_operation_name]
    
    settings = operations.create(name, [initial_operation_dict])
    
    self.assertDictEqual(
      _find_in_added_data(settings, initial_operation_name), initial_operation_dict)
    self.assertIn(initial_operation_dict["name"], settings["added"])
    self.assertIsNot(
      _find_in_added_data(settings, initial_operation_name), initial_operation_dict)
    
    self.assertSetEqual(settings["added"][initial_operation_name].tags, set(tags))
    
    for attribute_name, value in additional_operation_attributes.items():
      self.assertEqual(
        settings["added"][initial_operation_name][attribute_name].value, value)
    
    self.assertNotIn("type", settings["added"][initial_operation_name])
    
    self.assertIn("type", _find_in_added_data(settings, initial_operation_name))
    self.assertEqual(
      initial_operation_dict["type"],
      _find_in_added_data(settings, initial_operation_name)["type"])
  
  def test_create_initial_operation_with_invalid_type_raises_error(self):
    initial_operation_dict = get_operation_data(test_operations)["autocrop"]
    initial_operation_dict["type"] = "invalid_type"
    
    with self.assertRaises(ValueError):
      operations.create("operations", [initial_operation_dict])


class TestManageOperations(unittest.TestCase):
  
  def setUp(self):
    self.test_operations = get_operation_data(test_operations)
    self.autocrop_operation_dict = self.test_operations["autocrop"]
    self.settings = operations.create("operations")
  
  def test_add(self):
    operation = operations.add(self.settings, self.autocrop_operation_dict)
    
    self.assertIn("autocrop", self.settings["added"])
    self.assertEqual(len(self.settings["added"]), 1)
    self.assertDictEqual(
      _find_in_added_data(self.settings, "autocrop"), self.autocrop_operation_dict)
    self.assertIsNot(
      _find_in_added_data(self.settings, "autocrop"), self.autocrop_operation_dict)
    self.assertEqual(operation, self.settings["added/autocrop"])
  
  def test_add_passing_invalid_object_raises_error(self):
    with self.assertRaises(TypeError):
      operations.add(self.settings, "invalid_object")
  
  def test_add_existing_name_is_uniquified(self):
    operation = operations.add(self.settings, self.autocrop_operation_dict)
    operation_2 = operations.add(self.settings, self.autocrop_operation_dict)
    
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
    
    def on_before_add_operation(operations, operation_dict):
      invoked_event_args.append((operations, operation_dict))
      self.assertNotIn("autocrop", self.settings)
    
    self.settings.connect_event("before-add-operation", on_before_add_operation)
    
    operations.add(self.settings, self.autocrop_operation_dict)
    
    self.assertIs(invoked_event_args[0][0], self.settings)
    self.assertDictEqual(invoked_event_args[0][1], self.autocrop_operation_dict)
    self.assertIsNot(invoked_event_args[0][1], self.autocrop_operation_dict)
  
  @parameterized.parameterized.expand([
    ("",
     ["autocrop"],),
    
    ("and_passes_original_operation_dict",
     ["autocrop", "autocrop"],),
  ])
  def test_add_invokes_after_add_operation_event(
        self, test_case_name_suffix, operation_names_to_add):
    invoked_event_args = []
    
    def on_after_add_operation(operations, operation, orig_operation_dict):
      invoked_event_args.append((operations, operation, orig_operation_dict))
    
    self.settings.connect_event("after-add-operation", on_after_add_operation)
    
    for operation_name in operation_names_to_add:
      operation = operations.add(self.settings, self.test_operations[operation_name])
      
      self.assertIs(invoked_event_args[-1][0], self.settings)
      self.assertIs(invoked_event_args[-1][1], operation)
      self.assertDictEqual(invoked_event_args[-1][2], self.autocrop_operation_dict)
      self.assertIsNot(invoked_event_args[-1][2], self.autocrop_operation_dict)
  
  def test_add_modifying_added_operation_modifies_nothing_else(self):
    operation = operations.add(self.settings, self.autocrop_operation_dict)
    operation["enabled"].set_value(False)
    operation["arguments/offset_x"].set_value(20)
    operation["arguments/offset_y"].set_value(10)
    
    self.assertNotEqual(operation["enabled"], self.autocrop_operation_dict["enabled"])
    self.assertNotEqual(
      operation["arguments/offset_x"], self.autocrop_operation_dict["arguments"][0])
    self.assertNotEqual(
      operation["arguments/offset_y"], self.autocrop_operation_dict["arguments"][1])
    
    self.assertNotEqual(
      operation["enabled"], _find_in_added_data(self.settings, "autocrop")["enabled"])
  
  def test_add_creates_separate_settings_for_custom_fields(self):
    self.autocrop_operation_dict["custom_field"] = "value"
    
    operation = operations.add(self.settings, self.autocrop_operation_dict)
    
    self.assertEqual(operation["custom_field"].value, "value")
    self.assertEqual(self.settings["added/autocrop/custom_field"].value, "value")
    self.assertEqual(
      _find_in_added_data(self.settings, "autocrop")["custom_field"], "value")
  
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
    for operation_dict in self.test_operations.values():
      operations.add(self.settings, operation_dict)
    
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
        operation_names_to_add,
        names_to_remove,
        names_to_keep):
    for operation_name in operation_names_to_add:
      operations.add(self.settings, self.test_operations[operation_name])
    
    for operation_name in names_to_remove:
      operations.remove(self.settings, operation_name)
    
      self.assertNotIn(operation_name, self.settings["added"])
      self.assertIsNone(_find_in_added_data(self.settings, operation_name))
    
    for operation_name in names_to_keep:
      self.assertIn(operation_name, self.settings["added"])
      self.assertIsNotNone(_find_in_added_data(self.settings, operation_name))
    
    self.assertEqual(len(self.settings["added"]), len(names_to_keep))
  
  def test_remove_nonexisting_operation_name(self):
    with self.assertRaises(ValueError):
      operations.remove(self.settings, "invalid_operation")
  
  def test_clear(self):
    for operation_dict in self.test_operations.values():
      operations.add(self.settings, operation_dict)
    
    operations.clear(self.settings)
    
    self.assertFalse(self.settings["added"])
    self.assertFalse(self.settings["added_data"].value)
    self.assertTrue(self.test_operations)
  
  def test_clear_resets_to_initial_operations(self):
    settings = operations.create("operations", [self.autocrop_operation_dict])
    
    operations.add(settings, self.test_operations["autocrop_background"])
    operations.clear(settings)
    
    self.assertIn("autocrop", settings["added"])
    self.assertEqual(len(settings["added"]), 1)
    self.assertNotIn("autocrop_background", settings)
    
    self.assertEqual(len(settings["added_data"].value), 1)
    self.assertDictEqual(
      _find_in_added_data(settings, "autocrop"),
      self.autocrop_operation_dict)
    self.assertIsNot(
      _find_in_added_data(settings, "autocrop"),
      self.autocrop_operation_dict)


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
    self.test_operations = get_operation_data(test_operations)
    self.settings = operations.create("operations")
  
  @parameterized.parameterized.expand(_walk_parameters)
  def test_walk_added(
        self, test_case_name_suffix, setting_name, expected_setting_paths):
    for operation_dict in self.test_operations.values():
      operations.add(self.settings, operation_dict)
    
    self.assertListEqual(
      list(operations.walk(self.settings, setting_name=setting_name)),
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
    for operation_dict in self.test_operations.values():
      operations.add(self.settings, operation_dict)
    
    for operation_name, new_position in operations_to_reorder:
      operations.reorder(self.settings, operation_name, new_position)
    
    self.assertListEqual(
      list(operations.walk(self.settings, setting_name=setting_name)),
      [self.settings["added/" + path] for path in expected_setting_paths])


@mock.patch(
  pgconstants.PYGIMPLIB_MODULE_PATH + ".pgsettingsources.gimpshelf.shelf",
  new_callable=stubs_gimp.ShelfStub)
@mock.patch(
  pgconstants.PYGIMPLIB_MODULE_PATH + ".pgsettingsources.gimp",
  new_callable=stubs_gimp.GimpModuleStub)
class TestLoadSaveOperations(unittest.TestCase):
  
  def setUp(self):
    self.test_operations = get_operation_data(test_operations)
    self.settings = operations.create("operations")
  
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
    for operation_dict in self.test_operations.values():
      operations.add(self.settings, operation_dict)
    
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
        operation_names_to_add):
    for operation_name in operation_names_to_add:
      operations.add(self.settings, self.test_operations[operation_name])
    
    added_data_before_save = self.settings["added_data"].value
    
    self.settings.save()
    self.settings.load()
    
    self.assertEqual(len(self.settings["added_data"].value), len(operation_names_to_add))
    
    for dict_before_save, dict_after_save in zip(
          added_data_before_save, self.settings["added_data"].value):
      self.assertDictEqual(dict_before_save, dict_after_save)
    
    self.assertEqual(len(self.settings["added"]), len(operation_names_to_add))
    
    for added_setting, dict_after_save in zip(
          self.settings["added"], self.settings["added_data"].value):
      self.assertEqual(added_setting.name, dict_after_save["name"])
  
  def test_values_are_preserved_after_load(
        self, mock_persistent_source, mock_session_source):
    for operation_dict in self.test_operations.values():
      operations.add(self.settings, operation_dict)
    
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
    for operation_dict in self.test_operations.values():
      operations.add(self.settings, operation_dict)
    
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
    settings = operations.create("operations", [self.test_operations["autocrop"]])
    
    for operation_name in ["autocrop_background", "autocrop_foreground"]:
      operations.add(settings, self.test_operations[operation_name])
    
    settings.load()
    
    self.assertEqual(len(settings["added"]), 1)
    self.assertIn("autocrop", settings["added"])
    self.assertNotIn("autocrop_background", settings["added"])
    self.assertNotIn("autocrop_foreground", settings["added"])
  
  def test_load_if_added_data_found_overrides_initial_operations(
        self, mock_persistent_source, mock_session_source):
    settings = operations.create("operations", [self.test_operations["autocrop"]])
    
    for operation_name in ["autocrop_background", "autocrop_foreground"]:
      operations.add(settings, self.test_operations[operation_name])
    
    operations.remove(settings, "autocrop")
    
    settings.save()
    settings.load()
    
    self.assertEqual(len(settings["added"]), 2)
    self.assertNotIn("autocrop", settings["added"])
    self.assertIn("autocrop_background", settings["added"])
    self.assertIn("autocrop_foreground", settings["added"])


class TestManagePdbProceduresAsOperations(unittest.TestCase):
  
  def setUp(self):
    self.test_operations = get_operation_data(test_operations)
    self.settings = operations.create("operations")
    self.procedure_stub = stubs_gimp.PdbProcedureStub(
      name="file-png-save",
      type_=gimpenums.PLUGIN,
      params=(
        (gimpenums.PDB_INT32, "run-mode", "The run mode"),
        (gimpenums.PDB_INT32ARRAY, "save-options", "Save options"),
        (gimpenums.PDB_STRING, "filename", "Filename to save the image in")),
      return_vals=None,
      blurb="Saves files in PNG file format")
  
  def test_get_operation_dict_for_pdb_procedure_with_non_unique_param_names(self):
    self.procedure_stub.params = tuple(
      list(self.procedure_stub.params)
      + [(gimpenums.PDB_INT32ARRAY, "save-options", "More save options"),
         (gimpenums.PDB_STRING, "filename", "Another filename")])
    
    operation_dict = operations.get_operation_dict_for_pdb_procedure(self.procedure_stub)
    
    self.assertListEqual(
      [argument_dict["name"] for argument_dict in operation_dict["arguments"]],
      ["run-mode", "save-options", "filename", "save-options-2", "filename-2"])
  
  def test_get_operation_dict_for_pdb_procedure_unsupported_pdb_param_type(self):
    self.procedure_stub.params = tuple(
      list(self.procedure_stub.params)
      + [("unsupported", "param-with-unsupported-type", "")])
    
    with self.assertRaises(operations.UnsupportedPdbProcedureError):
      operations.get_operation_dict_for_pdb_procedure(self.procedure_stub)
  
  def test_get_operation_dict_for_pdb_procedure_default_run_mode_is_noninteractive(self):
    operation_dict = operations.get_operation_dict_for_pdb_procedure(self.procedure_stub)
    self.assertEqual(
      operation_dict["arguments"][0]["default_value"], gimpenums.RUN_NONINTERACTIVE)
  
  def test_get_operation_dict_for_pdb_procedure_run_mode_as_not_first_parameter(self):
    self.procedure_stub.params = tuple(
      [(gimpenums.PDB_INT32, "dummy-param", "Dummy paramter")]
      + list(self.procedure_stub.params))
    
    operation_dict = operations.get_operation_dict_for_pdb_procedure(self.procedure_stub)
    self.assertNotIn("default_value", operation_dict["arguments"][0])
    self.assertNotIn("default_value", operation_dict["arguments"][1])
  
  def test_add_pdb_procedure_as_operation(self):
    operation = operations.add(self.settings, self.procedure_stub)
    
    self.assertIn("file-png-save", self.settings["added"])
    
    self.assertEqual(operation.name, "file-png-save")
    self.assertEqual(operation["function"].value, "file-png-save")
    self.assertEqual(operation["enabled"].value, True)
    self.assertEqual(operation["display_name"].value, self.procedure_stub.proc_name)
    self.assertEqual(
      operation["operation_groups"].value, [operations.DEFAULT_OPERATIONS_GROUP])
    self.assertEqual(operation["is_pdb_procedure"].value, True)
    
    self.assertEqual(operation["arguments/run-mode"].value, gimpenums.RUN_NONINTERACTIVE)
    self.assertEqual(operation["arguments/save-options"].value, ())
    self.assertEqual(operation["arguments/filename"].value, "")
    
    self.assertEqual(
      _find_in_added_data(self.settings, "file-png-save")["name"], "file-png-save")
    self.assertEqual(
      _find_in_added_data(self.settings, "file-png-save")["function"], "file-png-save")
  
  @mock.patch(
    pgconstants.PYGIMPLIB_MODULE_PATH + ".pgsettingsources.gimpshelf.shelf",
    new_callable=stubs_gimp.ShelfStub)
  @mock.patch(
    pgconstants.PYGIMPLIB_MODULE_PATH + ".pgsettingsources.gimp",
    new_callable=stubs_gimp.GimpModuleStub)
  def test_load_save_pdb_procedure_as_operation(
        self, mock_persistent_source, mock_session_source):
    operation = operations.add(self.settings, self.procedure_stub)
    
    operation["enabled"].set_value(False)
    operation["arguments/filename"].set_value("image.png")
    
    self.settings.save()
    self.settings.load()
    
    self.assertEqual(operation.name, "file-png-save")
    self.assertEqual(operation["function"].value, "file-png-save")
    self.assertEqual(operation["enabled"].value, False)
    self.assertEqual(operation["is_pdb_procedure"].value, True)
    self.assertEqual(operation["arguments/filename"].value, "image.png")
    
    self.assertEqual(
      _find_in_added_data(self.settings, "file-png-save")["function"], "file-png-save")
