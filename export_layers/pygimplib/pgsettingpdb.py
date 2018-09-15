# -*- coding: utf-8 -*-
#
# Copyright (C) 2014-2018 khalim19
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

"""
This module contains a class to generate GIMP PDB parameters out of settings
(`pgsetting.Setting` instances) and parse GIMP procedure arguments to assign
them as values to settings.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

from . import pgsetting
from . import pgsettinggroup


def create_params(*settings_or_groups):
  """
  Return a list of GIMP PDB parameters from the specified `Setting` or
  `SettingGroup` instances.
  """
  settings = _list_settings(settings_or_groups)
  
  params = []
  
  for setting in settings:
    if setting.can_be_registered_to_pdb():
      params.extend(setting.get_pdb_param())
  
  return params


def iter_args(args, settings):
  """
  Iterate over arguments (`args`) passed to a GIMP PDB procedure.
  
  `settings` is a list of `Setting` instances that may modify the iteration. For
  example, if an argument is matched by a setting of type `ArraySetting`, the
  array argument causes the preceding argument to be skipped. The preceding
  argument is the array length and does not need to exist as a separate setting
  because the length can be obtained from the array itself in Python.
  
  If there are more settings than non-skipped arguments, the remaining settings
  will be ignored.
  """
  indexes_of_array_length_settings = set()
  index = 0
  
  for setting in settings:
    if isinstance(setting, pgsetting.ArraySetting):
      index += 1
      indexes_of_array_length_settings.add(index - 1)
    
    index += 1
  
  for arg_index in range(min(len(args), index)):
    if arg_index not in indexes_of_array_length_settings:
      yield args[arg_index]


def list_param_values(settings_or_groups, ignore_run_mode=True):
  """
  Return a list of values of settings registrable to PDB.
  
  If `ignore_run_mode` is `True`, ignore setting(s) named `"run_mode"`. This
  makes it possible to call PDB functions with the setting values without
  manually omitting the `"run_mode"` setting.
  """
  settings = _list_settings(settings_or_groups)
  
  if ignore_run_mode:
    for i, setting in enumerate(settings):
      if setting.name == "run_mode":
        del settings[i]
        break
  
  return [setting.value for setting in settings if setting.can_be_registered_to_pdb()]


def _list_settings(settings_or_groups):
  settings = []
  for setting_or_group in settings_or_groups:
    if isinstance(setting_or_group, pgsetting.Setting):
      settings.append(setting_or_group)
    elif isinstance(setting_or_group, pgsettinggroup.SettingGroup):
      settings.extend(setting_or_group.walk())
    else:
      raise TypeError(
        "{} is not an object of type {} or {}".format(
          setting_or_group, pgsetting.Setting, pgsettinggroup.SettingGroup))
  
  return settings
