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
This module:
* provides simple interface to load and save settings using setting sources
* defines exceptions usable in setting sources
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

str = unicode

import collections

#===============================================================================


class SettingSourceError(Exception):
  pass


class SettingsNotFoundInSourceError(SettingSourceError):
  pass


class SettingSourceNotFoundError(SettingSourceError):
  pass


class SettingSourceReadError(SettingSourceError):
  pass


class SettingSourceInvalidFormatError(SettingSourceError):
  pass


class SettingSourceWriteError(SettingSourceError):
  pass


#===============================================================================


class SettingPersistor(object):
  
  """
  This class:
  * serves as a wrapper for `SettingSource` classes
  * reads settings from multiple setting sources
  * write settings to multiple setting sources
  """
  
  _STATUSES = SUCCESS, READ_FAIL, WRITE_FAIL, NOT_ALL_SETTINGS_FOUND = (0, 1, 2, 3)
  
  @classmethod
  def load(cls, settings_or_groups, setting_sources):
    """
    Load setting values from the specified list of setting sources
    (`setting_sources`) to specified list of settings or setting groups
    (`settings_or_groups`).
    
    The order of sources in the `setting_sources` list indicates the preference
    of the sources, beginning with the first source in the list. If not all
    settings could be found in the first source, the second source is read to
    assign values to the remaining settings. This continues until all settings
    are read.
    
    If settings have invalid values, their default values will be assigned.
    
    If some settings could not be found in any of the sources,
    their default values will be assigned.
    
    Parameters:
    
    * `settings_or_groups` - list of `Setting` or `SettingGroup` objects whose
      values are loaded from `setting_sources`.
    
    * `setting_sources` - list of `SettingSource` instances to read from.
    
    Returns:
    
      * `status`:
      
        * `SUCCESS` - Settings successfully loaded. This status is also returned
          if `settings_or_groups` or `setting_sources` is empty.
        
        * `NOT_ALL_SETTINGS_FOUND` - Could not find some settings from
          any of the sources. Default values are assigned to these settings.
        
        * `READ_FAIL` - Could not read data from the first source where this
          error occurred. May occur for file sources with e.g. denied read
          permission.
      
      * `status_message` - Message describing the returned status in more detail.
    """
    
    if not settings_or_groups or not setting_sources:
      return cls._status(cls.SUCCESS)
    
    all_settings = cls._list_settings(settings_or_groups)
    all_settings_found = True
    settings = all_settings
    
    for setting in all_settings:
      setting.invoke_event('before-load')
    
    for source in setting_sources:
      try:
        source.read(settings)
      except (SettingsNotFoundInSourceError, SettingSourceNotFoundError) as e:
        if type(e) == SettingsNotFoundInSourceError:
          settings = source.settings_not_found
        
        if source == setting_sources[-1]:
          all_settings_found = False
          break
        else:
          continue
      except (SettingSourceReadError, SettingSourceInvalidFormatError) as e:
        return cls._status(cls.READ_FAIL, e.message)
      else:
        break
    
    for setting in all_settings:
      setting.invoke_event('after-load')
    
    if all_settings_found:
      return cls._status(cls.SUCCESS)
    else:
      return cls._status(cls.NOT_ALL_SETTINGS_FOUND, e.message)
  
  @classmethod
  def save(cls, settings_or_groups, setting_sources):
    """
    Save setting values from specified list of settings or setting groups
    (`settings_or_groups`) to the specified list of setting sources
    (`setting_sources`).
    
    Parameters:
    
    * `settings_or_groups` - list of `Setting` or `SettingGroup` objects whose
      values are saved to `setting_sources`.
    
    * `setting_sources` - list of `SettingSource` instances to write to.
    
    Returns:
    
      * `status`:
      
        * `SUCCESS` - Settings successfully saved. This status is also returned
          if `settings_or_groups` or `setting_sources` is empty.
        
        * `WRITE_FAIL` - Could not write data to the first source where this
          error occurred. May occur for file sources with e.g. denied write
          permission.
      
      * `status_message` - Message describing the status in more detail.
    """
    
    if not settings_or_groups or not setting_sources:
      return cls._status(cls.SUCCESS)
    
    settings = cls._list_settings(settings_or_groups)
    
    for setting in settings:
      setting.invoke_event('before-save')
    
    for source in setting_sources:
      try:
        source.write(settings)
      except SettingSourceError as e:
        return cls._status(cls.WRITE_FAIL, e.message)
    
    for setting in settings:
      setting.invoke_event('after-save')
    
    return cls._status(cls.SUCCESS)
  
  @classmethod
  def clear(cls, setting_sources):
    """
    Remove all settings from all the specified setting sources. Note that some
    sources may do nothing because they do not implement this method.
    """
    
    for source in setting_sources:
      source.clear()
  
  @classmethod
  def _status(cls, status, message=None):
    return status, message if message is not None else ""
  
  @classmethod
  def _list_settings(cls, settings_or_groups):
    # Put all settings into one list so that the `read()` and `write()` methods
    # are invoked only once per each source.
    settings = []
    for setting_or_group in settings_or_groups:
      if isinstance(setting_or_group, collections.Iterable):
        group = setting_or_group
        settings.extend(list(group.walk()))
      else:
        setting = setting_or_group
        settings.append(setting)
    return settings
