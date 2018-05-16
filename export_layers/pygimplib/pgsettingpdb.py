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
This module contains a class to generate GIMP PDB parameters out of
`pgsetting.Setting` objects.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

from . import pgconstants
from . import pgsetting
from . import pgsettinggroup

#===============================================================================


class PdbParamCreator(object):
  
  """
  This class creates GIMP PDB (procedural database) parameters for plug-ins
  (plug-in procedures) from `Setting` objects.
  """
  
  @classmethod
  def create_params(cls, *settings_or_groups):
    """
    Return a list of GIMP PDB parameters from the specified `Setting` or
    `SettingGroup` objects.
    """
    
    settings = cls._list_settings(settings_or_groups)
    return [
      cls._create_param(setting) for setting in settings
      if setting.can_be_registered_to_pdb()]
  
  @classmethod
  def list_param_values(cls, settings_or_groups, ignore_run_mode=True):
    """
    Return a list of values of settings registrable to PDB.
    
    If `ignore_run_mode` is True, ignore setting(s) named "run_mode". This makes
    it possible to call PDB functions with the setting values without manually
    omitting the "run_mode" setting.
    """
    
    settings = cls._list_settings(settings_or_groups)
    
    if ignore_run_mode:
      for i, setting in enumerate(settings):
        if setting.name == "run_mode":
          del settings[i]
          break
    
    return [setting.value for setting in settings if setting.can_be_registered_to_pdb()]
  
  @staticmethod
  def _list_settings(settings_or_groups):
    settings = []
    for setting_or_group in settings_or_groups:
      if isinstance(setting_or_group, pgsetting.Setting):
        settings.append(setting_or_group)
      elif isinstance(setting_or_group, pgsettinggroup.SettingGroup):
        settings.extend(setting_or_group.walk())
      else:
        raise TypeError(
          "{0} is not an object of type {1} or {2}".format(
            setting_or_group, pgsetting.Setting, pgsettinggroup.SettingGroup))
    
    return settings
  
  @staticmethod
  def _create_param(setting):
    return (
      setting.pdb_type,
      setting.name.encode(pgconstants.GIMP_CHARACTER_ENCODING),
      setting.description.encode(pgconstants.GIMP_CHARACTER_ENCODING))
