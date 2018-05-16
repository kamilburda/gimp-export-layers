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
This module defines GUI-specific settings for the plug-in.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import collections

from export_layers import pygimplib
from export_layers.pygimplib import pgsetting
from export_layers.pygimplib import pgsettinggroup
from export_layers.pygimplib import pgutils

from .. import exportlayers

#===============================================================================


def create_gui_settings():
  
  gui_settings = pgsettinggroup.SettingGroup(
    name="gui",
    setting_attributes={
      "setting_sources": [
        pygimplib.config.SOURCE_SESSION, pygimplib.config.SOURCE_PERSISTENT]})
  
  gui_settings.add([
    {
      "type": pgsetting.SettingTypes.generic,
      "name": "dialog_position",
      "default_value": ()
    },
    {
      "type": pgsetting.SettingTypes.generic,
      "name": "dialog_size",
      "default_value": ()
    },
    {
      "type": pgsetting.SettingTypes.boolean,
      "name": "show_more_settings",
      "default_value": False
    },
    {
      "type": pgsetting.SettingTypes.integer,
      "name": "paned_outside_previews_position",
      "default_value": 610
    },
    {
      "type": pgsetting.SettingTypes.float,
      "name": "paned_between_previews_position",
      "default_value": 320
    },
    {
      "type": pgsetting.SettingTypes.float,
      "name": "settings_vpane_position",
      "default_value": 450
    },
    {
      "type": pgsetting.SettingTypes.boolean,
      "name": "export_name_preview_enabled",
      "default_value": True,
      "gui_type": None
    },
    {
      "type": pgsetting.SettingTypes.boolean,
      "name": "export_image_preview_enabled",
      "default_value": True,
      "gui_type": None
    },
    {
      "type": pgsetting.SettingTypes.generic,
      "name": "displayed_tags",
      "default_value": exportlayers.LayerExporter.BUILTIN_TAGS,
      "gui_type": None
    },
    {
      "type": pgsetting.SettingTypes.generic,
      "name": "displayed_builtin_operations",
      "default_value": [],
      "gui_type": None
    },
    {
      "type": pgsetting.SettingTypes.generic,
      "name": "displayed_builtin_constraints",
      "default_value": [],
      "gui_type": None
    },
  ])
  
  session_only_gui_settings = pgsettinggroup.SettingGroup(
    name="gui_session",
    setting_attributes={"setting_sources": [pygimplib.config.SOURCE_SESSION]})
  
  session_only_gui_settings.add([
    {
      "type": pgsetting.SettingTypes.image_IDs_and_directories,
      "name": "image_ids_and_directories",
      "default_value": {}
    },
    {
      "type": pgsetting.SettingTypes.generic,
      "name": "export_name_preview_layers_collapsed_state",
      # key: image ID
      # value: set of layer IDs collapsed in the name preview
      "default_value": collections.defaultdict(set)
    },
    {
      "type": pgsetting.SettingTypes.generic,
      "name": "export_image_preview_displayed_layers",
      # key: image ID; value: ID of the layer displayed in the preview
      "default_value": collections.defaultdict(pgutils.return_none_func)
    },
  ])
  
  persistent_only_gui_settings = pgsettinggroup.SettingGroup(
    name="gui_persistent",
    setting_attributes={"setting_sources": [pygimplib.config.SOURCE_PERSISTENT]})
  
  persistent_only_gui_settings.add([
    {
      "type": pgsetting.SettingTypes.generic,
      "name": "export_name_preview_layers_collapsed_state_persistent",
      # key: image file path
      # value: set of layer names collapsed in the name preview
      "default_value": collections.defaultdict(set)
    },
    {
      "type": pgsetting.SettingTypes.generic,
      "name": "export_image_preview_displayed_layers_persistent",
      # key: image file path
      # value: name of the layer displayed in the preview
      "default_value": collections.defaultdict(pgutils.return_none_func)
    },
  ])
  
  session_only_gui_settings["image_ids_and_directories"].tags.add("ignore_reset")
  
  return gui_settings, session_only_gui_settings, persistent_only_gui_settings
