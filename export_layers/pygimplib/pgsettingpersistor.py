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
This module:
* provides simple interface to load and save settings using setting sources
* defines exceptions usable in setting sources
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

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
    not_all_settings_found_message = ""
    
    settings = all_settings
    
    for setting in all_settings:
      setting.invoke_event("before-load")
    
    for source in setting_sources:
      try:
        source.read(settings)
      except (SettingsNotFoundInSourceError, SettingSourceNotFoundError) as e:
        if isinstance(e, SettingsNotFoundInSourceError):
          settings = source.settings_not_found
        
        if source == setting_sources[-1]:
          all_settings_found = False
          not_all_settings_found_message = str(e)
          break
        else:
          continue
      except (SettingSourceReadError, SettingSourceInvalidFormatError) as e:
        return cls._status(cls.READ_FAIL, str(e))
      else:
        break
    
    for setting in all_settings:
      setting.invoke_event("after-load")
    
    if all_settings_found:
      return cls._status(cls.SUCCESS)
    else:
      return cls._status(cls.NOT_ALL_SETTINGS_FOUND, not_all_settings_found_message)
  
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
      setting.invoke_event("before-save")
    
    for source in setting_sources:
      try:
        source.write(settings)
      except SettingSourceError as e:
        return cls._status(cls.WRITE_FAIL, str(e))
    
    for setting in settings:
      setting.invoke_event("after-save")
    
    return cls._status(cls.SUCCESS)
  
  @staticmethod
  def clear(setting_sources):
    """
    Remove all settings from all the specified setting sources. Note that some
    sources may do nothing because they do not implement this method.
    """
    
    for source in setting_sources:
      source.clear()
  
  @staticmethod
  def _status(status, message=None):
    return status, message if message is not None else ""
  
  @staticmethod
  def _list_settings(settings_or_groups):
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
