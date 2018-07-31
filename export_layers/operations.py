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

"""
This module defines the mean to create and manipulate plug-in operations
and constraints.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

from export_layers import pygimplib
from export_layers.pygimplib import pgsetting
from export_layers.pygimplib import pgsettinggroup


def create_operation(
      name, function, enabled=True, display_name=None, operation_groups=None):
  """
  Create a `SettingGroup` instance acting as an operation.
  
  Each group contains the following settings or subgroups (assuming settings
  unless otherwise stated):
  * "function" - the function executed
  * "arguments" - subgroup containing arguments to the function; each argument
    is a separate setting
  * "enabled" - whether the operation should be executed or not
  * "display_name" - the display name (human-readable name) of the operation
  * "operation_group" - list of groups the operation belongs to; used in
    `pgoperations.OperationExecutor` and `exportlayers.LayerExporter`
  """
  operation = pgsettinggroup.SettingGroup(
    name,
    tags=["operation"],
    setting_attributes={
      "pdb_type": None,
      "setting_sources": [
        pygimplib.config.SOURCE_SESSION, pygimplib.config.SOURCE_PERSISTENT]
    })
  
  arguments = pgsettinggroup.SettingGroup(
    "arguments",
    setting_attributes={
      "pdb_type": None,
      "setting_sources": [
        pygimplib.config.SOURCE_SESSION, pygimplib.config.SOURCE_PERSISTENT]
    })
  
  operation.add([
    {
      "type": pgsetting.SettingTypes.generic,
      "name": "function",
      "default_value": function,
      "setting_sources": None,
    },
    arguments,
    {
      "type": pgsetting.SettingTypes.boolean,
      "name": "enabled",
      "default_value": enabled,
    },
    {
      "type": pgsetting.SettingTypes.string,
      "name": "display_name",
      "default_value": display_name,
      "gui_type": None,
    },
    {
      "type": pgsetting.SettingTypes.generic,
      "name": "operation_groups",
      "default_value": operation_groups,
      "gui_type": None,
    },
  ])
  
  operation["enabled"].connect_event(
    "after-set-gui",
    _set_display_name_for_enabled_gui,
    operation["display_name"])
  
  return operation


def _set_display_name_for_enabled_gui(setting_enabled, setting_display_name):
  setting_display_name.set_gui(
    gui_type=pgsetting.SettingGuiTypes.check_button_label,
    gui_element=setting_enabled.gui.element
  )


def create_constraint(
      name,
      function,
      enabled=True,
      display_name=None,
      operation_groups=None,
      subfilter=None):
  constraint = create_operation(
    name,
    function,
    enabled,
    display_name,
    operation_groups)
  
  constraint.tags.add("constraint")
  
  constraint.add([
    {
      "type": pgsetting.SettingTypes.string,
      "name": "subfilter",
      "default_value": subfilter,
      "gui_type": None,
    },
  ])
  
  return constraint


def walk_operations(operations, setting_name="operation"):
  """
  Walk over a setting group containing operations.
  
  `setting_name` specifies which underlying setting or subgroup of each
  operation is returned. By default, the group representing the entire operation
  is returned. For possible values, see `create_operation`. Additional values
  include:
  * `"operation"` - the setting group if the group is an operation or constraint
  * `"constraint"` - the setting group if the group is a constraint
  """
  if setting_name in ["operation", "constraint"]:
    def has_tag(setting):
      return setting_name in setting.tags
    
    include_setting_func = has_tag
  else:
    def matches_setting_name(setting):
      return setting_name == setting.name
    
    include_setting_func = matches_setting_name
  
  return operations.walk(
    include_setting_func=include_setting_func,
    include_groups=True,
    include_if_parent_skipped=True)
