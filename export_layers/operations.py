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

"""
This module defines the means to create and manipulate plug-in operations -
procedures and constraints.

Most functions take a setting group containing operations as its first argument.

Many functions define events invoked on the setting group containing operations.
These events include:

* `"before-add-operation"` - invoked when:
  * calling `add()` before adding an operation,
  * calling `setting.Group.load()` or `setting.Persistor.load()` before loading
    an operation (loading an operation counts as adding),
  * calling `clear()` before resetting operations (due to initial operations
    being added back).
  
  Arguments: operation dictionary to be added

* `"after-add-operation"` - invoked when:
  * calling `add()` after adding an operation,
  * calling `setting.Group.load()` or `setting.Persistor.load()` after loading
    an operation (loading an operation counts as adding),
  * calling `clear()` after resetting operations (due to initial operations
    being added back).
  
  Arguments: created operation, original operation dictionary (same as in
  `"before-add-operation"`)

* `"before-reorder-operation"` - invoked when calling `reorder()` before
  reordering an operation.
  
  Arguments: operation, position before reordering

* `"after-reorder-operation"` - invoked when calling `reorder()` after reordering
  an operation.
  
  Arguments: operation, position before reordering, new position

* `"before-remove-operation"` - invoked when calling `remove()` before removing an
  operation.
  
  Arguments: operation to be removed

* `"after-remove-operation"` - invoked when calling `remove()` after removing an
  operation.
  
  Arguments: name of the removed operation

* `"before-clear-operations"` - invoked when calling `clear()` before clearing
  operations.

* `"after-clear-operations"` - invoked when calling `clear()` after clearing
  operations.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import gimpenums

from export_layers import pygimplib as pg

from . import placeholders


BUILTIN_TAGS = {
  "background": _("Background"),
  "foreground": _("Foreground"),
}

DEFAULT_PROCEDURES_GROUP = "default_procedures"
DEFAULT_CONSTRAINTS_GROUP = "default_constraints"

_DEFAULT_OPERATION_TYPE = "procedure"
_REQUIRED_OPERATION_FIELDS = ["name"]


def create(name, initial_operations=None):
  """
  Create a `setting.Group` instance containing operations.
  
  Parameters:
  * `name` - name of the `setting.Group` instance.
  * `initial_operations` - list of dictionaries describing operations to be
    added by default. Calling `clear()` will reset the operations returned by
    this function to the initial operations. By default, no initial operations
    are added.
  
  The resulting `setting.Group` instance contains the following subgroups:
  * `"added"` - Contains operations added via `add()` or created in this
    function via `initial_operations` dictionary.
  * `"_added_data"` - Operations stored as dictionaries, used when loading or
    saving operations persistently. As indicated by the leading underscore, this
    subgroup is only for internal use and should not be modified outside
    `operations`.
  * `"_added_data_values"` - Values of operations stored as dictionaries, used
    when loading or saving operations persistently. As indicated by the leading
    underscore, this subgroup is only for internal use and should not be
    modified outside `operations`.
  
  Each created operation in the returned group is a nested `setting.Group`. Each
  operation contains the following settings or subgroups:
  * `"function"` - The function to execute.
  * `"arguments"` - Arguments to `"function"` as a `setting.Group` instance
    containing arguments as separate `Setting` instances.
  * `"enabled"` - Whether the operation should be executed or not.
  * `"display_name"` - The display name (human-readable name) of the operation.
  * `"operation_group"` - List of groups the operation belongs to, used in
    `pygimplib.executor.Executor` and `exportlayers.LayerExporter`.
  * `"orig_name"` - The original name of the operation. If an operation with the
    same `"name"` field (see below) was previously added, the name of the new
    operation is made unique to allow lookup of both operations. Otherwise,
    `"orig_name"` is equal to `"name"`.
  
  Each dictionary in the `initial_operations` list may contain the following
  fields:
  * `"name"` - This field is required. This is the `name` attribute of the
    created operation.
  * `"type"` - Operation type. See below for details.
  * `"function"` - The function to execute.
  * `"arguments"` - Specified as list of dictionaries defining settings. Each
    dictionary must contain required attributes and can contain optional
    attributes as stated in `setting.Group.add()`.
  * `"enabled"`
  * `"display_name"`
  * `"operation_group"`
  
  Depending on the specified `"type"`, the dictionary may contain additional
  fields and `create` may generate additional settings.
  
  Allowed values for `"type"`:
  * `"procedure"` (default) - Represents a procedure. `"operation_group"`
    defaults to `DEFAULT_PROCEDURES_GROUP` if not defined.
  * `"constraint"` - Represents a constraint. `"operation_group"` defaults to
    `DEFAULT_CONSTRAINTS_GROUP` if not defined.
  
  Additional allowed fields for type `"constraint"` include:
  * `"subfilter"` - The name of a subfilter for an `ObjectFilter` instance
    where constraints should be added. By default, `"subfilter"` is `None` (no
    subfilter is assumed).
  
  Custom fields are accepted as well. For each field, a separate setting is
  created, using the field name as the setting name.
  
  Raises:
  * `ValueError` - invalid `"type"` or missing required fields in
    `initial_operations`.
  """
  operations = pg.setting.Group(
    name=name,
    setting_attributes={
      "pdb_type": None,
      "setting_sources": None,
    })
  
  added_operations = pg.setting.Group(
    name="added",
    setting_attributes={
      "pdb_type": None,
      "setting_sources": None,
    })
  
  operations.add([
    added_operations,
    {
      "type": pg.SettingTypes.generic,
      "name": "_added_data",
      "default_value": _get_initial_added_data(initial_operations),
      "setting_sources": [pg.config.SESSION_SOURCE, pg.config.PERSISTENT_SOURCE]
    },
    {
      "type": pg.SettingTypes.generic,
      "name": "_added_data_values",
      "default_value": {},
      "setting_sources": [pg.config.SESSION_SOURCE, pg.config.PERSISTENT_SOURCE]
    },
  ])
  
  _create_operations_from_added_data(operations)
  
  operations.connect_event(
    "after-clear-operations",
    _create_operations_from_added_data)
  
  operations["_added_data"].connect_event(
    "before-load",
    _clear_operations_before_load_without_adding_initial_operations,
    operations)
  
  operations["_added_data"].connect_event(
    "after-load",
    lambda added_data_setting: (
      _create_operations_from_added_data(added_data_setting.parent)))
  
  operations["_added_data_values"].connect_event(
    "before-save",
    _get_values_from_operations,
    operations["added"])
  
  operations["_added_data_values"].connect_event(
    "after-load",
    _set_values_for_operations,
    operations["added"])
  
  return operations


def _get_initial_added_data(initial_operations):
  if not initial_operations:
    return []
  else:
    return [dict(operation_dict) for operation_dict in initial_operations]


def _clear_operations_before_load_without_adding_initial_operations(
      added_data_setting, operations_group):
  _clear(operations_group)


def _create_operations_from_added_data(operations):
  for operation_dict in operations["_added_data"].value:
    operations.invoke_event("before-add-operation", operation_dict)
    
    operation = _create_operation_by_type(**dict(operation_dict))
    operations["added"].add([operation])
    
    operations.invoke_event("after-add-operation", operation, operation_dict)


def _create_operation_by_type(**kwargs):
  type_ = kwargs.pop("type", _DEFAULT_OPERATION_TYPE)
  
  if type_ not in _OPERATION_TYPES_AND_FUNCTIONS:
    raise ValueError(
      "invalid type '{}'; valid values: {}".format(
        type_, list(_OPERATION_TYPES_AND_FUNCTIONS)))
  
  for required_field in _REQUIRED_OPERATION_FIELDS:
    if required_field not in kwargs:
      raise ValueError("missing required field: '{}'".format(required_field))
  
  return _OPERATION_TYPES_AND_FUNCTIONS[type_](**kwargs)


def _get_values_from_operations(added_data_values_setting, added_operations_group):
  added_data_values_setting.reset()
  
  for setting in added_operations_group.walk():
    added_data_values_setting.value[
      setting.get_path(added_operations_group)] = setting.value


def _set_values_for_operations(added_data_values_setting, added_operations_group):
  for setting in added_operations_group.walk():
    if setting.get_path(added_operations_group) in added_data_values_setting.value:
      setting.set_value(
        added_data_values_setting.value[setting.get_path(added_operations_group)])


def _create_procedure(
      name,
      function=None,
      arguments=None,
      enabled=True,
      display_name=None,
      operation_groups=None,
      **custom_fields):
  
  def _set_display_name_for_enabled_gui(setting_enabled, setting_display_name):
    setting_display_name.set_gui(
      gui_type=pg.setting.SettingGuiTypes.check_button_label,
      gui_element=setting_enabled.gui.element)
  
  operation = pg.setting.Group(
    name,
    tags=["operation", "procedure"],
    setting_attributes={
      "pdb_type": None,
      "setting_sources": None,
    })
  
  arguments_group = pg.setting.Group(
    "arguments",
    setting_attributes={
      "pdb_type": None,
      "setting_sources": None,
    })
  
  if arguments:
    arguments_group.add(arguments)
  
  if operation_groups is None:
    operation_groups = [DEFAULT_PROCEDURES_GROUP]
  
  operation.add([
    {
      "type": pg.SettingTypes.generic,
      "name": "function",
      "default_value": function,
      "setting_sources": None,
    },
    arguments_group,
    {
      "type": pg.SettingTypes.boolean,
      "name": "enabled",
      "default_value": enabled,
    },
    {
      "type": pg.SettingTypes.string,
      "name": "display_name",
      "default_value": display_name,
      "gui_type": None,
      "tags": ["ignore_initialize_gui"],
    },
    {
      "type": pg.SettingTypes.generic,
      "name": "operation_groups",
      "default_value": operation_groups,
      "gui_type": None,
    },
  ])
  
  orig_name_value = custom_fields.pop("orig_name", name)
  operation.add([
    {
      "type": pg.SettingTypes.string,
      "name": "orig_name",
      "default_value": orig_name_value,
      "gui_type": None,
    },
  ])
  
  for field_name, field_value in custom_fields.items():
    operation.add([
      {
        "type": pg.SettingTypes.generic,
        "name": field_name,
        "default_value": field_value,
        "gui_type": None,
      },
    ])
  
  operation["enabled"].connect_event(
    "after-set-gui",
    _set_display_name_for_enabled_gui,
    operation["display_name"])
  
  if operation.get_value("is_pdb_procedure", True):
    _connect_events_to_sync_array_and_array_length_arguments(operation)
    _hide_gui_for_run_mode_and_array_length_arguments(operation)
  
  return operation


def _create_constraint(name, function, subfilter=None, **create_operation_kwargs):
  if create_operation_kwargs.get("operation_groups", None) is None:
    create_operation_kwargs["operation_groups"] = [DEFAULT_CONSTRAINTS_GROUP]
  
  constraint = _create_procedure(name, function, **create_operation_kwargs)
  
  constraint.tags.remove("procedure")
  constraint.tags.add("constraint")
  
  constraint.add([
    {
      "type": pg.SettingTypes.string,
      "name": "subfilter",
      "default_value": subfilter,
      "gui_type": None,
    },
  ])
  
  return constraint


def _connect_events_to_sync_array_and_array_length_arguments(operation):
  
  def _increment_array_length(
        array_setting, insertion_index, value, array_length_setting):
    array_length_setting.set_value(array_length_setting.value + 1)
  
  def _decrement_array_length(
        array_setting, insertion_index, array_length_setting):
    array_length_setting.set_value(array_length_setting.value - 1)
  
  for length_setting, array_setting in _get_array_length_and_array_settings(operation):
    array_setting.connect_event(
      "after-add-element", _increment_array_length, length_setting)
    array_setting.connect_event(
      "before-delete-element", _decrement_array_length, length_setting)


def _hide_gui_for_run_mode_and_array_length_arguments(operation):
  first_argument = next(iter(operation["arguments"]), None)
  if first_argument is not None and first_argument.display_name == "run-mode":
    first_argument.gui.set_visible(False)
  
  for length_setting, unused_ in _get_array_length_and_array_settings(operation):
    length_setting.gui.set_visible(False)


def _get_array_length_and_array_settings(operation):
  array_length_and_array_settings = []
  previous_setting = None
  
  for setting in operation["arguments"]:
    if isinstance(setting, pg.setting.ArraySetting) and previous_setting is not None:
      array_length_and_array_settings.append((previous_setting, setting))
    
    previous_setting = setting
  
  return array_length_and_array_settings


_OPERATION_TYPES_AND_FUNCTIONS = {
  "procedure": _create_procedure,
  "constraint": _create_constraint
}


def add(operations, operation_dict_or_function):
  """
  Add an operation to the `operations` setting group.
  
  `operation_dict_or_function` can be one of the following:
  * a dictionary - see `create()` for required and accepted fields.
  * a PDB procedure.
  
  Objects of other types passed to `operation_dict_or_function` raise
  `TypeError`.
  
  The same operation can be added multiple times. Each operation will be
  assigned a unique name and display name (e.g. `"autocrop"` and `"Autocrop"`
  for the first operation, `"autocrop_2"` and `"Autocrop (2)"` for the second
  operation, and so on).
  """
  if isinstance(operation_dict_or_function, dict):
    operation_dict = dict(operation_dict_or_function)
  else:
    if pg.pdbutils.is_pdb_procedure(operation_dict_or_function):
      operation_dict = get_operation_dict_for_pdb_procedure(operation_dict_or_function)
    else:
      raise TypeError(
        "'{}' is not a valid object - pass a dict or a PDB procedure".format(
          operation_dict_or_function))
  
  orig_operation_dict = dict(operation_dict)
  
  operations.invoke_event("before-add-operation", operation_dict)
  
  _uniquify_name_and_display_name(operations, operation_dict)
  
  operation = _create_operation_by_type(**operation_dict)
  
  operations["added"].add([operation])
  operations["_added_data"].value.append(operation_dict)
  
  operations.invoke_event("after-add-operation", operation, orig_operation_dict)
  
  return operation


def get_operation_dict_for_pdb_procedure(pdb_procedure):
  """
  Return a dictionary representing the specified GIMP PDB procedure that can be
  added to a setting group for operations via `add()`.
  
  The `"function"` field contains the PDB procedure name instead of the function
  itself in order for the dictionary to allow loading/saving to a persistent
  source.
  
  If the procedure contains arguments with the same name, each subsequent
  identical name is made unique (since arguments are internally represented as
  `pygimplib.setting.Setting` instances, whose names must be unique within a
  setting group).
  """
  
  def _generate_unique_pdb_procedure_argument_name():
    i = 2
    while True:
      yield "-{}".format(i)
      i += 1
  
  operation_dict = {
    "name": pdb_procedure.proc_name.decode(pg.GTK_CHARACTER_ENCODING),
    "function": pdb_procedure.proc_name.decode(pg.GTK_CHARACTER_ENCODING),
    "arguments": [],
    "display_name": pdb_procedure.proc_name.decode(pg.GTK_CHARACTER_ENCODING),
    "is_pdb_procedure": True,
  }
  
  pdb_procedure_argument_names = []
  
  for index, (pdb_param_type, pdb_param_name, unused_) in enumerate(pdb_procedure.params):
    processed_pdb_param_name = pdb_param_name.decode(pg.GTK_CHARACTER_ENCODING)
    
    try:
      setting_type = pg.setting.PDB_TYPES_TO_SETTING_TYPES_MAP[pdb_param_type]
    except KeyError:
      raise UnsupportedPdbProcedureError(operation_dict["name"], pdb_param_type)
    
    unique_pdb_param_name = pg.path.uniquify_string(
      processed_pdb_param_name,
      pdb_procedure_argument_names,
      uniquifier_generator=_generate_unique_pdb_procedure_argument_name())
    
    pdb_procedure_argument_names.append(unique_pdb_param_name)
    
    if isinstance(setting_type, dict):
      arguments_dict = dict(setting_type)
      arguments_dict["name"] = unique_pdb_param_name
      arguments_dict["display_name"] = processed_pdb_param_name
    else:
      arguments_dict = {
        "type": setting_type,
        "name": unique_pdb_param_name,
        "display_name": processed_pdb_param_name,
      }
    
    if pdb_param_type in placeholders.PDB_TYPES_TO_PLACEHOLDER_SETTING_TYPES_MAP:
      arguments_dict["type"] = (
        placeholders.PDB_TYPES_TO_PLACEHOLDER_SETTING_TYPES_MAP[pdb_param_type])
    
    if index == 0 and processed_pdb_param_name == "run-mode":
      arguments_dict["default_value"] = gimpenums.RUN_NONINTERACTIVE
    
    operation_dict["arguments"].append(arguments_dict)
  
  return operation_dict


def _uniquify_name_and_display_name(operations, operation_dict):
  operation_dict["orig_name"] = operation_dict["name"]
  
  operation_dict["name"] = _uniquify_operation_name(
    operations, operation_dict["name"])
  
  operation_dict["display_name"] = _uniquify_operation_display_name(
    operations, operation_dict["display_name"])


def _uniquify_operation_name(operations, name):
  """
  Return `name` modified to not match the name of any existing operation in
  `operations`.
  """
  
  def _generate_unique_operation_name():
    i = 2
    while True:
      yield "_{}".format(i)
      i += 1
  
  return (
    pg.path.uniquify_string(
      name,
      [operation.name for operation in walk(operations)],
      uniquifier_generator=_generate_unique_operation_name()))


def _uniquify_operation_display_name(operations, display_name):
  """
  Return `display_name` modified to not match the display name of any existing
  operation in `operations`.
  """
  
  def _generate_unique_display_name():
    i = 2
    while True:
      yield " ({})".format(i)
      i += 1
  
  return (
    pg.path.uniquify_string(
      display_name,
      [operation["display_name"].value for operation in walk(operations)],
      uniquifier_generator=_generate_unique_display_name()))


def reorder(operations, operation_name, new_position):
  """
  Modify the position of the added operation given by its name to the new
  position specified as an integer.
  
  A negative position functions as an n-th to last position (-1 for last, -2
  for second to last, etc.).
  
  Raises:
  * `ValueError` - `operation_name` not found in `operations`.
  """
  current_position = _find_index_in_added_data(operations, operation_name)
  
  if current_position is None:
    raise ValueError("operation '{}' not found in operations named '{}'".format(
      operation_name, operations.name))
  
  operation = operations["added"][operation_name]
  
  operations.invoke_event("before-reorder-operation", operation, current_position)
  
  operation_dict = operations["_added_data"].value.pop(current_position)
  
  if new_position < 0:
    new_position = max(len(operations["_added_data"].value) + new_position + 1, 0)
  
  operations["_added_data"].value.insert(new_position, operation_dict)
  
  operations.invoke_event(
    "after-reorder-operation", operation, current_position, new_position)


def remove(operations, operation_name):
  """
  Remove the operation specified by its name from `operations`.
  
  Raises:
  * `ValueError` - `operation_name` not found in `operations`.
  """
  operation_index = _find_index_in_added_data(operations, operation_name)
  
  if operation_index is None:
    raise ValueError("operation '{}' not found in operations named '{}'".format(
      operation_name, operations.name))
  
  operation = operations["added"][operation_name]
  
  operations.invoke_event("before-remove-operation", operation)
  
  operations["added"].remove([operation_name])
  del operations["_added_data"].value[operation_index]
  
  operations.invoke_event("after-remove-operation", operation_name)


def _find_index_in_added_data(operations, operation_name):
  return next(
    (index for index, dict_ in enumerate(operations["_added_data"].value)
     if dict_["name"] == operation_name),
    None)


def clear(operations):
  """
  Remove all added operations.
  """
  operations.invoke_event("before-clear-operations")
  
  _clear(operations)
  
  operations.invoke_event("after-clear-operations")


def _clear(operations):
  operations["added"].remove([operation.name for operation in walk(operations)])
  operations["_added_data"].reset()
  operations["_added_data_values"].reset()


def walk(operations, operation_type=None, setting_name=None):
  """
  Walk (iterate over) a setting group containing operations.
  
  The value of `operation_type` determines what types of operations to iterate
  over. If `operation_type` is `None`, iterate over all operations. For allowed
  operation types, see `create()`. Invalid values for `operation_type` raise
  `ValueError`.
  
  If `setting_name` is `None`, iterate over each setting group representing the
  entire operation.
  
  If `setting_name` is not `None`, iterate over each setting or subgroup inside
  each operation. For example, `"enabled"` yields the `"enabled"` setting for
  each operation. For the list of possible names of settings and subgroups, see
  `create()`.
  """
  operation_types = list(_OPERATION_TYPES_AND_FUNCTIONS)
  
  if operation_type is not None and operation_type not in operation_types:
    raise ValueError("invalid operation type '{}'".format(operation_type))
  
  def has_matching_type(setting):
    if operation_type is None:
      return any(type_ in setting.tags for type_ in operation_types)
    else:
      return operation_type in setting.tags
  
  listed_operations = {
    setting.name: setting
    for setting in operations["added"].walk(
      include_setting_func=has_matching_type,
      include_groups=True,
      include_if_parent_skipped=True)}
  
  for operation_dict in operations["_added_data"].value:
    if operation_dict["name"] in listed_operations:
      operation = listed_operations[operation_dict["name"]]
      
      if setting_name is None:
        yield operation
      else:
        if setting_name in operation:
          yield operation[setting_name]


class UnsupportedPdbProcedureError(Exception):
  
  def __init__(self, procedure_name, unsupported_param_type):
    self.procedure_name = procedure_name
    self.unsupported_param_type = unsupported_param_type
