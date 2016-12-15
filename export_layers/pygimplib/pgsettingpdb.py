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
This module contains a class to generate GIMP PDB parameters out of
`pgsetting.Setting` objects.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

str = unicode

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
    return [cls._create_param(setting) for setting in settings if setting.can_be_registered_to_pdb()]
  
  @classmethod
  def list_param_values(cls, settings_or_groups, ignore_run_mode=True):
    """
    Return a list of values of settings registrable to PDB.
    
    If `ignore_run_mode` is True, ignore setting(s) named 'run_mode'. This makes
    it possible to call PDB functions with the setting values without manually
    omitting the 'run_mode' setting.
    """
    
    settings = cls._list_settings(settings_or_groups)
    
    if ignore_run_mode:
      for i, setting in enumerate(settings):
        if setting.name == 'run_mode':
          del settings[i]
          break
    
    return [setting.value for setting in settings if setting.can_be_registered_to_pdb()]
  
  @classmethod
  def _list_settings(cls, settings_or_groups):
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
  
  @classmethod
  def _create_param(cls, setting):
    return (setting.pdb_type, setting.name.encode(), setting.description.encode())
