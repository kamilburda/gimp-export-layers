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
This module defines the mean to create and manipulate plug-in operations.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

from export_layers import pygimplib
from export_layers.pygimplib import pgsetting
from export_layers.pygimplib import pgsettinggroup


def create_operation(name, function, enabled=True, display_name=None):
  operation_group = pgsettinggroup.SettingGroup(
    name,
    tags=["operation"],
    setting_attributes={
      "pdb_type": None,
      "setting_sources": [
        pygimplib.config.SOURCE_SESSION, pygimplib.config.SOURCE_PERSISTENT]
    })
  
  operation_arguments_group = pgsettinggroup.SettingGroup(
    "arguments",
    tags=["arguments"],
    setting_attributes={
      "pdb_type": None,
      "setting_sources": [
        pygimplib.config.SOURCE_SESSION, pygimplib.config.SOURCE_PERSISTENT]
    })
  
  operation_group.add([
    {
      "type": pgsetting.SettingTypes.generic,
      "name": "function",
      "default_value": function,
      "tags": ["function"],
    },
    operation_arguments_group,
    {
      "type": pgsetting.SettingTypes.boolean,
      "name": "enabled",
      "default_value": enabled,
      "display_name": display_name,
      "tags": ["enabled"],
    },
    {
      "type": pgsetting.SettingTypes.string,
      "name": "display_name",
      "default_value": display_name,
      "gui_type": None,
      "tags": ["display_name"],
    },
  ])
  
  return operation_group
