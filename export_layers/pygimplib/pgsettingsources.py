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
This module defines setting sources - the means to load and save settings:
  * "session-persistently" - i.e. settings persist during one GIMP session
  * persistently
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *
import future.utils

import abc
import collections
import os

try:
  import cPickle as pickle
except ImportError:
  import pickle

import gimp
import gimpenums
import gimpshelf

from . import pgconstants
from . import pgsetting
from . import pgsettingpersistor

#===============================================================================


class SettingSource(future.utils.with_metaclass(abc.ABCMeta, object)):
  
  """
  This class provides an interface for reading and writing settings to
  permanent or semi-permanent sources.
  
  For easier usage, use the `SettingPersistor` class instead.
  
  Attributes:
  
  * `_settings_not_found` - List of settings not found in source when the
    `read()` method is called.
  """
  
  def __init__(self):
    self._settings_not_found = []
  
  @abc.abstractmethod
  def read(self, settings):
    """
    Read setting values from the source and assign them to the settings
    specified in the `settings` iterable.
    
    If a setting value from the source is invalid, the setting will be reset to
    its default value.
    
    Parameters:
    
    * `settings` - Any iterable sequence containing `Setting` objects.
    
    Raises:
    
    * `SettingsNotFoundInSourceError` - At least one of the settings is not
      found in the source. All settings that were not found in the source will
      be stored in the `settings_not_found` list. This list is cleared on each
      read() call.
    """
    
    pass
  
  @abc.abstractmethod
  def write(self, settings):
    """
    Write setting values from settings specified in the `settings` iterable
    to the source. Settings in the source but not specified in `settings` are
    kept intact.
    
    Parameters:
    
    * `settings` - Any iterable sequence containing `Setting` objects.
    """
    
    pass
  
  def clear(self):
    """
    Remove all settings from the setting source.
    
    This is useful if you rename settings, since the old settings would not be
    removed and would thus lead to bloating the source.
    
    Some `SettingSource` subclasses may not implement this method, in which case
    calling `clear()` has no effect.
    """
    
    pass
  
  @property
  def settings_not_found(self):
    return self._settings_not_found
  
  def _read(self, settings):
    """
    Read setting values from the source into the settings.
    
    To retrieve a single value, `_retrieve_setting_value` is called.
    
    Raises:
    
    * `SettingsNotFoundInSourceError` - one or more settings could not be found
      in the source. These settings are stored in the `settings_not_found` list.
    """
    
    self._settings_not_found = []
    
    for setting in settings:
      try:
        value = self._retrieve_setting_value(setting.name)
      except KeyError:
        self._settings_not_found.append(setting)
      else:
        try:
          setting.set_value(value)
        except pgsetting.SettingValueError:
          setting.reset()
    
    if self._settings_not_found:
      raise pgsettingpersistor.SettingsNotFoundInSourceError(
        _("The following settings could not be found in any sources:\n{0}").format(
          "\n".join(setting.name for setting in self._settings_not_found)))
  
  @abc.abstractmethod
  def _retrieve_setting_value(self, setting_name):
    """
    Retrieve a single setting value from the source given the setting name.
    
    This method must be defined in subclasses.
    """
    
    pass


#===============================================================================


class SessionPersistentSettingSource(SettingSource):
  
  """
  This class reads settings from/writes settings to a source that persists
  during one GIMP session.
  
  GIMP shelf is used as the session-persistent source and contains the
  name and last used value of each setting.
  
  Attributes:
  
  * `source_name` - Unique identifier to distinguish entries from different
    plug-ins in this source.
  """
  
  def __init__(self, source_name):
    super().__init__()
    
    self.source_name = source_name
    self._separator = "_"
  
  def read(self, settings):
    self._read(settings)
  
  def _retrieve_setting_value(self, setting_name):
    return gimpshelf.shelf[self._get_key(setting_name)]
  
  def write(self, settings):
    for setting in settings:
      gimpshelf.shelf[self._get_key(setting.name)] = setting.value
  
  def _get_key(self, setting_name):
    key = self.source_name + self._separator + setting_name
    return key.encode(pgconstants.GIMP_CHARACTER_ENCODING)


class PersistentSettingSource(SettingSource):
  
  """
  This class reads settings from/writes settings to a persistent source.
  
  This class stores settings in what can be referred to as the "globally
  persistent parasite", which is the `parasiterc` file maintained by GIMP to
  store persistent data. The file contains the name and the last used value of
  each setting.
  
  Attributes:
  
  * `source_name` - Unique identifier to distinguish entries from different
    plug-ins in this source.
  """
  
  def __init__(self, source_name):
    super().__init__()
    
    self.source_name = source_name
    self._parasite_filepath = os.path.join(gimp.directory, "parasiterc")
  
  def read(self, settings):
    """
    Raises:
    
    * `SettingsNotFoundInSourceError` - see the `SettingSource` class.
    
    * `SettingSourceNotFoundError` - Could not find the specified source.
    
    * `SettingSourceInvalidFormatError` - Specified source has invalid format.
      This could happen if the source was edited manually.
    """
    
    self._settings_from_parasite = self._read_from_parasite(self.source_name)
    if self._settings_from_parasite is None:
      raise pgsettingpersistor.SettingSourceNotFoundError(
        _('Could not find persistent setting source "{0}".').format(self.source_name))
    
    self._read(settings)
    
    del self._settings_from_parasite
  
  def _retrieve_setting_value(self, setting_name):
    return self._settings_from_parasite[setting_name]
  
  def write(self, settings):
    settings_from_parasite = self._read_from_parasite(self.source_name)
    if settings_from_parasite is not None:
      settings_to_write = settings_from_parasite
      settings_to_write.update(self._to_dict(settings))
    else:
      settings_to_write = self._to_dict(settings)
    
    settings_data = pickle.dumps(settings_to_write)
    gimp.parasite_attach(
      gimp.Parasite(self.source_name, gimpenums.PARASITE_PERSISTENT, settings_data))
  
  def _read_from_parasite(self, parasite_name):
    parasite = gimp.parasite_find(parasite_name)
    if parasite is None:
      return None
    
    try:
      settings_from_parasite = pickle.loads(parasite.data)
    except Exception:
      raise pgsettingpersistor.SettingSourceInvalidFormatError(
        _('Settings for this plug-in stored in "{0}" may be corrupt. '
          "This could happen if the file was edited manually.\n"
          "To fix this, save the settings again or reset them.").format(
            self._parasite_filepath))
    
    return settings_from_parasite
  
  def clear(self):
    parasite = gimp.parasite_find(self.source_name)
    if parasite is None:
      return
    
    gimp.parasite_detach(self.source_name)
  
  def _to_dict(self, settings):
    """
    Format the setting name and value to a dict, which the `pickle` module can
    properly serialize and de-serialize.
    """
    
    settings_dict = collections.OrderedDict()
    for setting in settings:
      settings_dict[setting.name] = setting.value
    
    return settings_dict
