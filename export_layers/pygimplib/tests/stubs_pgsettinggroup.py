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
This module provides stubs primarily to be used in the `test_pgsettinggroup`
module.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import future.standard_library
future.standard_library.install_aliases()

from future.builtins import *

from .. import pgsetting
from .. import pgsettinggroup

#===============================================================================


def create_test_settings():
  settings = pgsettinggroup.SettingGroup("main")
  settings.add([
    {
      "type": pgsetting.SettingTypes.file_extension,
      "name": "file_extension",
      "default_value": "bmp",
      "display_name": "File extension"
    },
    {
      "type": pgsetting.SettingTypes.boolean,
      "name": "only_visible_layers",
      "default_value": False,
      "display_name": "Only visible layers",
      "setting_sources": [object()]
    },
    {
      "type": pgsetting.SettingTypes.enumerated,
      "name": "overwrite_mode",
      "default_value": "rename_new",
      "items": [("replace", "Replace"),
                ("skip", "Skip"),
                ("rename_new", "Rename new file"),
                ("rename_existing", "Rename existing file")],
      "error_messages": {"invalid_value": "Invalid value. Something went wrong on our end... we are so sorry!"}
    },
  ])
  
  return settings


def create_test_settings_hierarchical():
  main_settings = pgsettinggroup.SettingGroup("main")
  main_settings.add([
    {
      "type": pgsetting.SettingTypes.file_extension,
      "name": "file_extension",
      "default_value": "bmp",
      "display_name": "File extension"
    },
  ])
  
  advanced_settings = pgsettinggroup.SettingGroup("advanced")
  advanced_settings.add([
    {
      "type": pgsetting.SettingTypes.boolean,
      "name": "only_visible_layers",
      "default_value": False,
      "display_name": "Only visible layers",
    },
    {
      "type": pgsetting.SettingTypes.enumerated,
      "name": "overwrite_mode",
      "default_value": "rename_new",
      "items": [("replace", "Replace"),
                ("skip", "Skip"),
                ("rename_new", "Rename new file"),
                ("rename_existing", "Rename existing file")],
    },
  ])
  
  settings = pgsettinggroup.SettingGroup("settings")
  settings.add([main_settings, advanced_settings])
  
  return settings


def create_test_settings_load_save():
  dummy_session_source, dummy_persistent_source = object(), object()
  
  main_settings = pgsettinggroup.SettingGroup(
    name="main", setting_attributes={"setting_sources": [dummy_session_source, dummy_persistent_source]})
  
  main_settings.add([
    {
      "type": pgsetting.SettingTypes.file_extension,
      "name": "file_extension",
      "default_value": "bmp",
    },
  ])
  
  advanced_settings = pgsettinggroup.SettingGroup(
    name="advanced", setting_attributes={"setting_sources": [dummy_session_source]})
  
  advanced_settings.add([
    {
      "type": pgsetting.SettingTypes.boolean,
      "name": "only_visible_layers",
      "default_value": False,
      "setting_sources": [dummy_persistent_source, dummy_session_source]
    },
    {
      "type": pgsetting.SettingTypes.boolean,
      "name": "autocrop",
      "default_value": False
    },
  ])
  
  settings = pgsettinggroup.SettingGroup("settings")
  settings.add([main_settings, advanced_settings])
  
  return settings
