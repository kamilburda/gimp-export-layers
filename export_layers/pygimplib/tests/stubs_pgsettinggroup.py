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

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

str = unicode

from .. import pgsetting
from .. import pgsettinggroup

#===============================================================================


def create_test_settings():
  settings = pgsettinggroup.SettingGroup('main', [
    {
      'type': pgsetting.SettingTypes.file_extension,
      'name': 'file_extension',
      'default_value': 'bmp',
      'display_name': "File extension"
    },
    {
      'type': pgsetting.SettingTypes.boolean,
      'name': 'only_visible_layers',
      'default_value': False,
      'display_name': "Only visible layers",
      'setting_sources': [object()]
    },
    {
      'type': pgsetting.SettingTypes.enumerated,
      'name': 'overwrite_mode',
      'default_value': 'rename_new',
      'items': [('replace', "Replace"),
                ('skip', "Skip"),
                ('rename_new', "Rename new file"),
                ('rename_existing', "Rename existing file")],
      'error_messages': {'invalid_value': "Invalid value. Something went wrong on our end... we are so sorry!"}
    },
  ])
  
  settings.set_ignore_tags({
    'file_extension': ['reset'],
    'overwrite_mode': ['reset', 'apply_gui_values_to_settings'],
  })
  
  return settings


def create_test_settings_hierarchical():
  main_settings = pgsettinggroup.SettingGroup('main', [
    {
      'type': pgsetting.SettingTypes.file_extension,
      'name': 'file_extension',
      'default_value': 'bmp',
      'display_name': "File extension"
    },
  ])
  
  advanced_settings = pgsettinggroup.SettingGroup('advanced', [
    {
      'type': pgsetting.SettingTypes.boolean,
      'name': 'only_visible_layers',
      'default_value': False,
      'display_name': "Only visible layers",
    },
    {
      'type': pgsetting.SettingTypes.enumerated,
      'name': 'overwrite_mode',
      'default_value': 'rename_new',
      'items': [('replace', "Replace"),
                ('skip', "Skip"),
                ('rename_new', "Rename new file"),
                ('rename_existing', "Rename existing file")],
    },
  ])
  
  settings = pgsettinggroup.SettingGroup('settings', [main_settings, advanced_settings])
  
  return settings


def create_test_settings_load_save():
  dummy_session_source, dummy_persistent_source = (object(), object())
  
  main_settings = pgsettinggroup.SettingGroup('main', [
    {
      'type': pgsetting.SettingTypes.file_extension,
      'name': 'file_extension',
      'default_value': 'bmp',
    },
  ], setting_sources=[dummy_session_source, dummy_persistent_source])
  
  advanced_settings = pgsettinggroup.SettingGroup('advanced', [
    {
      'type': pgsetting.SettingTypes.boolean,
      'name': 'only_visible_layers',
      'default_value': False,
      'setting_sources': [dummy_persistent_source, dummy_session_source]
    },
    {
      'type': pgsetting.SettingTypes.boolean,
      'name': 'autocrop',
      'default_value': False
    },
  ], setting_sources=[dummy_session_source])
  
  settings = pgsettinggroup.SettingGroup('settings', [main_settings, advanced_settings])
  
  return settings
