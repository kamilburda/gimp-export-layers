# -*- coding: utf-8 -*-
#
# This file is part of Export Layers.
#
# Copyright (C) 2013-2019 khalim19 <khalim19@gmail.com>
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

from export_layers import pygimplib as pg

from export_layers.pygimplib.tests import stubs_gimp

from .. import operations
from .. import placeholders


test_procedures = [
  {
    "name": "autocrop",
    "type": "procedure",
    "function": pg.utils.empty_func,
    "enabled": True,
    "display_name": "Autocrop",
    "operation_groups": ["basic"],
    "arguments": [
      {
        "type": pg.SettingTypes.integer,
        "name": "offset_x",
        "default_value": 0,
      },
      {
        "type": pg.SettingTypes.integer,
        "name": "offset_y",
        "default_value": 0,
      },
    ],
  },
  {
    "name": "autocrop_background",
    "type": "procedure",
    "function": pg.utils.empty_func,
    "enabled": False,
    "display_name": "Autocrop background layers",
  },
  {
    "name": "autocrop_foreground",
    "type": "procedure",
    "function": pg.utils.empty_func,
    "enabled": False,
    "display_name": "Autocrop foreground layers",
  },
]

test_constraints = [
  {
    "name": "only_layers",
    "type": "constraint",
    "function": pg.utils.empty_func,
    "enabled": True,
    "display_name": "Only layers",
    "subfilter": "layer_types",
  },
  {
    "name": "only_visible_layers",
    "type": "constraint",
    "function": pg.utils.empty_func,
    "enabled": False,
    "display_name": "Only visible layers",
  },
]


def get_operation_data(operations_list):
  return collections.OrderedDict(
    (operation_dict["name"], dict(operation_dict))
    for operation_dict in operations_list)


def _find_in_added_data(operations_, operation_name):
  return next(
    (dict_ for dict_ in operations_["_added_data"].value
     if dict_["name"] == operation_name),
    None)


class TestCreateOperations(unittest.TestCase):
  
  @parameterized.parameterized.expand([
    ("procedures", "procedures"),
    ("constraints", "constraints"),
  ])
  def test_create(self, test_case_name_suffix, name):
    operations_ = operations.create(name)
    
    self.assertIn("added", operations_)
    self.assertEqual(len(operations_["added"]), 0)
    self.assertFalse(operations_["_added_data"].value)
  
  @parameterized.parameterized.expand([
    ("procedure_with_default_group",
     "procedures",
     test_procedures,
     "autocrop_background",
     ["operation", "procedure"],
     {"operation_groups": [operations.DEFAULT_PROCEDURES_GROUP]}),
    
    ("procedure_with_custom_group",
     "procedures",
     test_procedures,
     "autocrop",
     ["operation", "procedure"],
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
     "only_layers",
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
    
    operations_ = operations.create(name, [initial_operation_dict])
    
    self.assertDictEqual(
      _find_in_added_data(operations_, initial_operation_name), initial_operation_dict)
    self.assertIn(initial_operation_dict["name"], operations_["added"])
    self.assertIsNot(
      _find_in_added_data(operations_, initial_operation_name), initial_operation_dict)
    
    self.assertSetEqual(operations_["added"][initial_operation_name].tags, set(tags))
    
    for attribute_name, value in additional_operation_attributes.items():
      self.assertEqual(
        operations_["added"][initial_operation_name][attribute_name].value, value)
    
    self.assertNotIn("type", operations_["added"][initial_operation_name])
    
    self.assertIn("type", _find_in_added_data(operations_, initial_operation_name))
    self.assertEqual(
      initial_operation_dict["type"],
      _find_in_added_data(operations_, initial_operation_name)["type"])
  
  def test_create_initial_operation_with_invalid_type_raises_error(self):
    initial_operation_dict = get_operation_data(test_procedures)["autocrop"]
    initial_operation_dict["type"] = "invalid_type"
    
    with self.assertRaises(ValueError):
      operations.create("procedures", [initial_operation_dict])
  
  @parameterized.parameterized.expand([
    ("missing_name", "name"),
  ])
  def test_create_missing_required_fields_raises_error(
        self, test_case_name_suffix, missing_name):
    initial_operation_dict = get_operation_data(test_procedures)["autocrop"]
    del initial_operation_dict[missing_name]
    
    with self.assertRaises(ValueError):
      operations.create("procedures", [initial_operation_dict])


class TestManageOperations(unittest.TestCase):
  
  def setUp(self):
    self.test_procedures = get_operation_data(test_procedures)
    self.autocrop_dict = self.test_procedures["autocrop"]
    self.procedures = operations.create("procedures")
    
    self.expected_dict = dict({"orig_name": "autocrop"}, **self.autocrop_dict)
  
  def test_add(self):
    operation = operations.add(self.procedures, self.autocrop_dict)
    
    self.assertIn("autocrop", self.procedures["added"])
    self.assertEqual(len(self.procedures["added"]), 1)
    self.assertDictEqual(
      _find_in_added_data(self.procedures, "autocrop"), self.expected_dict)
    self.assertIsNot(
      _find_in_added_data(self.procedures, "autocrop"), self.autocrop_dict)
    self.assertEqual(operation, self.procedures["added/autocrop"])
  
  def test_add_passing_invalid_object_raises_error(self):
    with self.assertRaises(TypeError):
      operations.add(self.procedures, "invalid_object")
  
  def test_add_existing_name_is_uniquified(self):
    added_operations = [
      operations.add(self.procedures, self.autocrop_dict) for unused_ in range(3)]
    
    orig_name = "autocrop"
    expected_names = ["autocrop", "autocrop_2", "autocrop_3"]
    expected_display_names = ["Autocrop", "Autocrop (2)", "Autocrop (3)"]
    
    for operation, expected_name, expected_display_name in zip(
          added_operations, expected_names, expected_display_names):
      self.assertIn(expected_name, self.procedures["added"])
      self.assertEqual(operation, self.procedures["added/" + expected_name])
      self.assertEqual(
        self.procedures["added/" + expected_name + "/display_name"].value,
        expected_display_name)
      self.assertEqual(
        self.procedures["added/" + expected_name + "/orig_name"].value, orig_name)
      self.assertIsNotNone(_find_in_added_data(self.procedures, expected_name))
      self.assertEqual(
        _find_in_added_data(self.procedures, expected_name)["display_name"],
        expected_display_name)
    
    self.assertEqual(len(self.procedures["added"]), 3)
    self.assertEqual(len(self.procedures["_added_data"].value), 3)
  
  def test_add_invokes_before_add_operation_event(self):
    invoked_event_args = []
    
    def on_before_add_operation(operations_, operation_dict):
      invoked_event_args.append((operations_, operation_dict))
      self.assertNotIn("autocrop", self.procedures)
    
    self.procedures.connect_event("before-add-operation", on_before_add_operation)
    
    operations.add(self.procedures, self.autocrop_dict)
    
    self.assertIs(invoked_event_args[0][0], self.procedures)
    self.assertDictEqual(invoked_event_args[0][1], self.expected_dict)
    self.assertIsNot(invoked_event_args[0][1], self.autocrop_dict)
  
  @parameterized.parameterized.expand([
    ("",
     ["autocrop"],),
    
    ("and_passes_original_operation_dict",
     ["autocrop", "autocrop"],),
  ])
  def test_add_invokes_after_add_operation_event(
        self, test_case_name_suffix, operation_names_to_add):
    invoked_event_args = []
    
    def on_after_add_operation(operations_, operation, orig_operation_dict):
      invoked_event_args.append((operations_, operation, orig_operation_dict))
    
    self.procedures.connect_event("after-add-operation", on_after_add_operation)
    
    for operation_name in operation_names_to_add:
      operation = operations.add(self.procedures, self.test_procedures[operation_name])
      
      self.assertIs(invoked_event_args[-1][0], self.procedures)
      self.assertIs(invoked_event_args[-1][1], operation)
      self.assertDictEqual(invoked_event_args[-1][2], self.autocrop_dict)
      self.assertIsNot(invoked_event_args[-1][2], self.autocrop_dict)
  
  def test_add_modifying_added_operation_modifies_nothing_else(self):
    operation = operations.add(self.procedures, self.autocrop_dict)
    operation["enabled"].set_value(False)
    operation["arguments/offset_x"].set_value(20)
    operation["arguments/offset_y"].set_value(10)
    
    self.assertNotEqual(operation["enabled"], self.autocrop_dict["enabled"])
    self.assertNotEqual(
      operation["arguments/offset_x"], self.autocrop_dict["arguments"][0])
    self.assertNotEqual(
      operation["arguments/offset_y"], self.autocrop_dict["arguments"][1])
    
    self.assertNotEqual(
      operation["enabled"], _find_in_added_data(self.procedures, "autocrop")["enabled"])
  
  def test_add_creates_separate_settings_for_custom_fields(self):
    self.autocrop_dict["custom_field"] = "value"
    
    operation = operations.add(self.procedures, self.autocrop_dict)
    
    self.assertEqual(operation["custom_field"].value, "value")
    self.assertEqual(self.procedures["added/autocrop/custom_field"].value, "value")
    self.assertEqual(
      _find_in_added_data(self.procedures, "autocrop")["custom_field"], "value")
  
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
    for operation_dict in self.test_procedures.values():
      operations.add(self.procedures, operation_dict)
    
    operations.reorder(self.procedures, operation_name, new_position)
    
    self.assertEqual(
      [operation_dict["name"] for operation_dict in self.procedures["_added_data"].value],
      expected_ordered_operation_names)
  
  def test_reorder_nonexisting_operation_name(self):
    with self.assertRaises(ValueError):
      operations.reorder(self.procedures, "invalid_operation", 0)
  
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
      operations.add(self.procedures, self.test_procedures[operation_name])
    
    for operation_name in names_to_remove:
      operations.remove(self.procedures, operation_name)
    
      self.assertNotIn(operation_name, self.procedures["added"])
      self.assertIsNone(_find_in_added_data(self.procedures, operation_name))
    
    for operation_name in names_to_keep:
      self.assertIn(operation_name, self.procedures["added"])
      self.assertIsNotNone(_find_in_added_data(self.procedures, operation_name))
    
    self.assertEqual(len(self.procedures["added"]), len(names_to_keep))
  
  def test_remove_nonexisting_operation_name(self):
    with self.assertRaises(ValueError):
      operations.remove(self.procedures, "invalid_operation")
  
  def test_clear(self):
    for operation_dict in self.test_procedures.values():
      operations.add(self.procedures, operation_dict)
    
    operations.clear(self.procedures)
    
    self.assertFalse(self.procedures["added"])
    self.assertFalse(self.procedures["_added_data"].value)
    self.assertTrue(self.test_procedures)
  
  def test_clear_resets_to_initial_operations(self):
    procedures = operations.create("procedures", [self.autocrop_dict])
    
    operations.add(procedures, self.test_procedures["autocrop_background"])
    operations.clear(procedures)
    
    self.assertIn("autocrop", procedures["added"])
    self.assertEqual(len(procedures["added"]), 1)
    self.assertNotIn("autocrop_background", procedures)
    
    self.assertEqual(len(procedures["_added_data"].value), 1)
    self.assertDictEqual(_find_in_added_data(procedures, "autocrop"), self.autocrop_dict)
    self.assertIsNot(_find_in_added_data(procedures, "autocrop"), self.autocrop_dict)


class TestWalkOperations(unittest.TestCase):
  
  def setUp(self):
    self.test_procedures = get_operation_data(test_procedures)
    self.test_constraints = get_operation_data(test_constraints)
    self.operations = operations.create("operations")
  
  @parameterized.parameterized.expand([
    ("all_types_entire_operations",
     None,
     None,
     ["autocrop",
      "autocrop_background",
      "autocrop_foreground",
      "only_layers",
      "only_visible_layers"]),
    
    ("specific_type_entire_operations",
     "procedure",
     None,
     ["autocrop",
      "autocrop_background",
      "autocrop_foreground"]),
    
    ("all_types_specific_setting",
     None,
     "enabled",
     ["autocrop/enabled",
      "autocrop_background/enabled",
      "autocrop_foreground/enabled",
      "only_layers/enabled",
      "only_visible_layers/enabled"]),
    
    ("specific_types_specific_setting",
     "procedure",
     "enabled",
     ["autocrop/enabled",
      "autocrop_background/enabled",
      "autocrop_foreground/enabled"]),
    
    ("nonexistent_setting",
     None,
     "nonexistent_setting",
     []),
  ])
  def test_walk_added(
        self,
        test_case_name_suffix,
        operation_type,
        setting_name,
        expected_setting_paths):
    for operation_dict in self.test_procedures.values():
      operations.add(self.operations, operation_dict)
    
    for operation_dict in self.test_constraints.values():
      operations.add(self.operations, operation_dict)
    
    self.assertListEqual(
      list(operations.walk(self.operations, operation_type, setting_name)),
      [self.operations["added/" + path] for path in expected_setting_paths])
  
  def test_walk_added_with_same_setting_name_as_operation_type(self):
    for operation_dict in self.test_procedures.values():
      operation_dict["procedure"] = "value"
      operations.add(self.operations, operation_dict)
    
    self.assertListEqual(
      list(operations.walk(self.operations, "procedure", "procedure")),
      [self.operations["added/" + path]
       for path in [
         "autocrop/procedure",
         "autocrop_background/procedure",
         "autocrop_foreground/procedure"]])
  
  @parameterized.parameterized.expand([
    ("reorder_first",
     [("autocrop", 1)],
     ["autocrop_background",
      "autocrop",
      "autocrop_foreground"]),
    
    ("reorder_middle",
     [("autocrop_background", 0)],
     ["autocrop_background",
      "autocrop",
      "autocrop_foreground"]),
    
    ("reorder_last",
     [("autocrop_foreground", 1)],
     ["autocrop",
      "autocrop_foreground",
      "autocrop_background"]),
  ])
  def test_walk_added_after_reordering(
        self,
        test_case_name_suffix,
        operations_to_reorder,
        expected_setting_paths):
    for operation_dict in self.test_procedures.values():
      operations.add(self.operations, operation_dict)
    
    for operation_name, new_position in operations_to_reorder:
      operations.reorder(self.operations, operation_name, new_position)
    
    self.assertListEqual(
      list(operations.walk(self.operations)),
      [self.operations["added/" + path] for path in expected_setting_paths])


@mock.patch(
  pg.PYGIMPLIB_MODULE_PATH + ".setting.sources.gimpshelf.shelf",
  new_callable=stubs_gimp.ShelfStub)
@mock.patch(
  pg.PYGIMPLIB_MODULE_PATH + ".setting.sources.gimp",
  new_callable=stubs_gimp.GimpModuleStub)
class TestLoadSaveOperations(unittest.TestCase):
  
  def setUp(self):
    self.test_procedures = get_operation_data(test_procedures)
    self.procedures = operations.create("procedures")
  
  @mock.patch(
    pg.PYGIMPLIB_MODULE_PATH + ".setting.persistor.Persistor.save",
    return_value=(pg.setting.Persistor.SUCCESS, ""))
  @mock.patch(
    pg.PYGIMPLIB_MODULE_PATH + ".setting.persistor.Persistor.load",
    return_value=(pg.setting.Persistor.SUCCESS, ""))
  def test_save_load_affects_only_added_data(
        self, mock_load, mock_save, mock_persistent_source, mock_session_source):
    self.procedures.save()
    self.procedures.load()
    
    self.assertEqual(mock_load.call_count, 1)
    self.assertEqual(len(mock_load.call_args[0][0]), 2)
    self.assertIn(self.procedures["_added_data"], mock_load.call_args[0][0])
    self.assertIn(self.procedures["_added_data_values"], mock_load.call_args[0][0])
    self.assertEqual(mock_save.call_count, 1)
    self.assertEqual(len(mock_save.call_args[0][0]), 2)
    self.assertIn(self.procedures["_added_data"], mock_save.call_args[0][0])
    self.assertIn(self.procedures["_added_data_values"], mock_save.call_args[0][0])
  
  def test_added_data_values_are_cleared_before_save(
        self,
        mock_persistent_source,
        mock_session_source):
    for operation_dict in self.test_procedures.values():
      operations.add(self.procedures, operation_dict)
    
    self.procedures.save()
    
    operations.remove(self.procedures, "autocrop")
    
    self.procedures.save()
    
    for key in self.procedures["_added_data_values"].value:
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
      operations.add(self.procedures, self.test_procedures[operation_name])
    
    added_data_before_save = self.procedures["_added_data"].value
    
    self.procedures.save()
    self.procedures.load()
    
    self.assertEqual(
      len(self.procedures["_added_data"].value), len(operation_names_to_add))
    
    for dict_before_save, dict_after_save in zip(
          added_data_before_save, self.procedures["_added_data"].value):
      self.assertDictEqual(dict_before_save, dict_after_save)
    
    self.assertEqual(len(self.procedures["added"]), len(operation_names_to_add))
    
    for added_setting, dict_after_save in zip(
          self.procedures["added"], self.procedures["_added_data"].value):
      self.assertEqual(added_setting.name, dict_after_save["name"])
  
  def test_values_are_preserved_after_load(
        self, mock_persistent_source, mock_session_source):
    for operation_dict in self.test_procedures.values():
      operations.add(self.procedures, operation_dict)
    
    self.procedures["added/autocrop_background/enabled"].set_value(True)
    self.procedures["added/autocrop_background/operation_groups"].set_value(
      ["background"])
    self.procedures["added/autocrop_foreground/enabled"].set_value(True)
    self.procedures["added/autocrop_foreground/operation_groups"].set_value(
      ["foreground"])
    self.procedures["added/autocrop/arguments/offset_x"].set_value(20)
    self.procedures["added/autocrop/arguments/offset_y"].set_value(10)
    
    self.procedures.save()
    self.procedures.load()
    
    self.assertEqual(
      self.procedures["added/autocrop_background/enabled"].value, True)
    self.assertEqual(
      self.procedures["added/autocrop_background/operation_groups"].value, ["background"])
    self.assertEqual(
      self.procedures["added/autocrop_foreground/enabled"].value, True)
    self.assertEqual(
      self.procedures["added/autocrop_foreground/operation_groups"].value, ["foreground"])
    self.assertEqual(self.procedures["added/autocrop/arguments/offset_x"].value, 20)
    self.assertEqual(self.procedures["added/autocrop/arguments/offset_y"].value, 10)
  
  def test_added_data_values_is_filled_before_save_and_reset_on_clear(
        self, mock_persistent_source, mock_session_source):
    for operation_dict in self.test_procedures.values():
      operations.add(self.procedures, operation_dict)
    
    self.procedures["added/autocrop_background/enabled"].set_value(True)
    self.procedures["added/autocrop_background/operation_groups"].set_value(
      ["background"])
    self.procedures["added/autocrop/arguments/offset_x"].set_value(20)
    self.procedures["added/autocrop/arguments/offset_y"].set_value(10)
    
    self.procedures.save()
    
    self.assertTrue(self.procedures["_added_data_values"].value)
    
    operations.clear(self.procedures)
    
    self.assertFalse(self.procedures["_added_data_values"].value)
  
  def test_load_if_added_data_not_found_sets_initial_operations(
        self, mock_persistent_source, mock_session_source):
    procedures = operations.create("procedures", [self.test_procedures["autocrop"]])
    
    for operation_name in ["autocrop_background", "autocrop_foreground"]:
      operations.add(procedures, self.test_procedures[operation_name])
    
    procedures.load()
    
    self.assertEqual(len(procedures["added"]), 1)
    self.assertIn("autocrop", procedures["added"])
    self.assertNotIn("autocrop_background", procedures["added"])
    self.assertNotIn("autocrop_foreground", procedures["added"])
  
  def test_load_if_added_data_found_overrides_initial_operations(
        self, mock_persistent_source, mock_session_source):
    procedures = operations.create("procedures", [self.test_procedures["autocrop"]])
    
    for operation_name in ["autocrop_background", "autocrop_foreground"]:
      operations.add(procedures, self.test_procedures[operation_name])
    
    operations.remove(procedures, "autocrop")
    
    procedures.save()
    procedures.load()
    
    self.assertEqual(len(procedures["added"]), 2)
    self.assertNotIn("autocrop", procedures["added"])
    self.assertIn("autocrop_background", procedures["added"])
    self.assertIn("autocrop_foreground", procedures["added"])


class TestManagePdbProceduresAsOperations(unittest.TestCase):
  
  def setUp(self):
    self.procedures = operations.create("procedures")
    self.procedure_stub = stubs_gimp.PdbProcedureStub(
      name="file-png-save",
      type_=gimpenums.PLUGIN,
      params=(
        (gimpenums.PDB_INT32, "run-mode", "The run mode"),
        (gimpenums.PDB_INT32, "num-save-options", "Number of save options"),
        (gimpenums.PDB_INT32ARRAY, "save-options", "Save options"),
        (gimpenums.PDB_STRING, "filename", "Filename to save the image in")),
      return_vals=None,
      blurb="Saves files in PNG file format")
  
  def test_add_pdb_procedure(self):
    operation = operations.add(self.procedures, self.procedure_stub)
    
    self.assertIn("file-png-save", self.procedures["added"])
    
    self.assertEqual(operation.name, "file-png-save")
    self.assertEqual(operation["function"].value, "file-png-save")
    self.assertEqual(operation["enabled"].value, True)
    self.assertEqual(operation["display_name"].value, self.procedure_stub.proc_name)
    self.assertEqual(
      operation["operation_groups"].value, [operations.DEFAULT_PROCEDURES_GROUP])
    self.assertEqual(operation["is_pdb_procedure"].value, True)
    
    self.assertEqual(operation["arguments/run-mode"].gui.get_visible(), False)
    self.assertEqual(operation["arguments/num-save-options"].gui.get_visible(), False)
    
    self.assertEqual(operation["arguments/run-mode"].value, gimpenums.RUN_NONINTERACTIVE)
    self.assertEqual(operation["arguments/num-save-options"].value, 0)
    self.assertEqual(operation["arguments/save-options"].value, ())
    self.assertEqual(operation["arguments/filename"].value, "")
    
    self.assertEqual(
      _find_in_added_data(self.procedures, "file-png-save")["name"], "file-png-save")
    self.assertEqual(
      _find_in_added_data(self.procedures, "file-png-save")["function"], "file-png-save")
  
  def test_add_pdb_procedure_array_length_setting_is_updated_automatically(self):
    operation = operations.add(self.procedures, self.procedure_stub)
    
    operation["arguments/save-options"].add_element()
    self.assertEqual(operation["arguments/num-save-options"].value, 1)
    operation["arguments/save-options"].add_element()
    self.assertEqual(operation["arguments/num-save-options"].value, 2)
    
    del operation["arguments/save-options"][-1]
    self.assertEqual(operation["arguments/num-save-options"].value, 1)
    del operation["arguments/save-options"][-1]
    self.assertEqual(operation["arguments/num-save-options"].value, 0)
  
  @mock.patch(
    pg.PYGIMPLIB_MODULE_PATH + ".setting.sources.gimpshelf.shelf",
    new_callable=stubs_gimp.ShelfStub)
  @mock.patch(
    pg.PYGIMPLIB_MODULE_PATH + ".setting.sources.gimp",
    new_callable=stubs_gimp.GimpModuleStub)
  def test_load_save_pdb_procedure_as_operation(
        self, mock_persistent_source, mock_session_source):
    operation = operations.add(self.procedures, self.procedure_stub)
    
    operation["enabled"].set_value(False)
    operation["arguments/filename"].set_value("image.png")
    
    self.procedures.save()
    self.procedures.load()
    
    self.assertEqual(operation.name, "file-png-save")
    self.assertEqual(operation["function"].value, "file-png-save")
    self.assertEqual(operation["enabled"].value, False)
    self.assertEqual(operation["is_pdb_procedure"].value, True)
    self.assertEqual(operation["arguments/filename"].value, "image.png")
    
    self.assertEqual(
      _find_in_added_data(self.procedures, "file-png-save")["function"], "file-png-save")


class TestGetOperationDictAsPdbProcedure(unittest.TestCase):
  
  def setUp(self):
    self.procedure_stub = stubs_gimp.PdbProcedureStub(
      name="file-png-save",
      type_=gimpenums.PLUGIN,
      params=(
        (gimpenums.PDB_INT32, "run-mode", "The run mode"),
        (gimpenums.PDB_INT32, "num-save-options", "Number of save options"),
        (gimpenums.PDB_INT32ARRAY, "save-options", "Save options"),
        (gimpenums.PDB_STRING, "filename", "Filename to save the image in")),
      return_vals=None,
      blurb="Saves files in PNG file format")
  
  def test_with_non_unique_param_names(self):
    self.procedure_stub.params = tuple(
      list(self.procedure_stub.params)
      + [(gimpenums.PDB_INT32ARRAY, "save-options", "More save options"),
         (gimpenums.PDB_STRING, "filename", "Another filename")])
    
    operation_dict = operations.get_operation_dict_for_pdb_procedure(self.procedure_stub)
    
    self.assertListEqual(
      [argument_dict["name"] for argument_dict in operation_dict["arguments"]],
      ["run-mode",
       "num-save-options",
       "save-options",
       "filename",
       "save-options-2",
       "filename-2"])
  
  def test_unsupported_pdb_param_type(self):
    self.procedure_stub.params = tuple(
      list(self.procedure_stub.params)
      + [("unsupported", "param-with-unsupported-type", "")])
    
    with self.assertRaises(operations.UnsupportedPdbProcedureError):
      operations.get_operation_dict_for_pdb_procedure(self.procedure_stub)
  
  def test_default_run_mode_is_noninteractive(self):
    operation_dict = operations.get_operation_dict_for_pdb_procedure(self.procedure_stub)
    self.assertEqual(
      operation_dict["arguments"][0]["default_value"], gimpenums.RUN_NONINTERACTIVE)
  
  def test_run_mode_as_not_first_parameter(self):
    self.procedure_stub.params = tuple(
      [(gimpenums.PDB_INT32, "dummy-param", "Dummy parameter")]
      + list(self.procedure_stub.params))
    
    operation_dict = operations.get_operation_dict_for_pdb_procedure(self.procedure_stub)
    self.assertNotIn("default_value", operation_dict["arguments"][0])
    self.assertNotIn("default_value", operation_dict["arguments"][1])
  
  def test_gimp_object_types_are_replaced_with_placeholders(self):
    self.procedure_stub.params = tuple(
      list(self.procedure_stub.params)
      + [(gimpenums.PDB_IMAGE, "image", "The image"),
         (gimpenums.PDB_LAYER, "layer", "The layer to export")])
    
    operation_dict = operations.get_operation_dict_for_pdb_procedure(self.procedure_stub)
    
    self.assertEqual(
      operation_dict["arguments"][-2]["type"], placeholders.PlaceholderImageSetting)
    self.assertEqual(
      operation_dict["arguments"][-1]["type"], placeholders.PlaceholderLayerSetting)
