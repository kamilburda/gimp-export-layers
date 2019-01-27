# -*- coding: utf-8 -*-
#
# Copyright (C) 2014-2019 khalim19
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
* persistently
* session-wide - settings persist during one GIMP session
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

from ._pgsettingsources_errors import *


class SettingSource(future.utils.with_metaclass(abc.ABCMeta, object)):
  """
  This class provides an interface for reading and writing settings to
  setting sources. For easier usage, use the `SettingPersistor` class instead.
  
  Attributes:
  
  * `_settings_not_found` - List of settings not found in the source when
    `read()` is called.
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
      `read()` call.
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
  
  @abc.abstractmethod
  def read_dict(self, setting_names):
    """
    Read setting values from the source specified by their names in the
    `setting_names` list. Return a dictionary of
    `(setting name, setting value)` pairs.
    
    Settings that do not exist in the source are skipped. If the source does not
    exist, return an empty dictionary.
    
    This method is useful in the unlikely case the settings must be modified
    directly in the source or removed from the source.
    """
    pass
  
  @abc.abstractmethod
  def write_dict(self, setting_names_and_values):
    """
    Write setting names and values to the source specified in the
    `setting_names_and_values` dictionary containing
    `(setting name, setting value)` pairs.
    
    Depending on the subclass, the entire setting source may be overwritten by
    the specified dictionary. Therefore, do not assume unspecified settings to
    be preserved in the source after calling this method.
    
    This method is useful in the unlikely case the settings must be modified
    directly in the source or removed from the source.
    """
    pass
  
  @property
  def settings_not_found(self):
    return self._settings_not_found
  
  def _read(self, settings):
    """
    Read setting values from the source into the settings.
    
    To read a single value, `_read_setting_value` is called.
    
    Raises:
    
    * `SettingsNotFoundInSourceError` - one or more settings could not be found
      in the source. These settings are stored in the `settings_not_found` list.
    """
    self._settings_not_found = []
    
    for setting in settings:
      try:
        value = self._read_setting_value(setting.get_path("root"))
      except KeyError:
        self._settings_not_found.append(setting)
      else:
        try:
          setting.set_value(value)
        except pgsetting.SettingValueError:
          setting.reset()
    
    if self._settings_not_found:
      raise SettingsNotFoundInSourceError(
        _("The following settings could not be found in any sources:\n{}").format(
          "\n".join(setting.get_path() for setting in self._settings_not_found)))
  
  @abc.abstractmethod
  def _read_setting_value(self, setting_name):
    """
    Read a single setting value from the source given the setting name.
    
    This method must be defined in subclasses.
    """
    pass


class SessionPersistentSettingSource(SettingSource):
  """
  This class reads settings from/writes settings to a source that persists
  during one GIMP session.
  
  Internally, the GIMP shelf is used as the session-wide source and contains the
  name and the last used value of each setting.
  
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
  
  def write(self, settings):
    for setting in settings:
      self._write_setting_value(setting.get_path("root"), setting.value)
  
  def read_dict(self, setting_names):
    setting_names_and_values = {}
    
    for name in setting_names:
      try:
        setting_names_and_values[name] = self._read_setting_value(name)
      except KeyError:
        pass
    
    return setting_names_and_values
  
  def write_dict(self, setting_names_and_values):
    for name, value in setting_names_and_values.items():
      self._write_setting_value(name, value)
  
  def _read_setting_value(self, setting_name):
    return gimpshelf.shelf[self._get_key(setting_name)]
  
  def _write_setting_value(self, setting_name, setting_value):
    gimpshelf.shelf[self._get_key(setting_name)] = setting_value
  
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
    self._settings_from_parasite = None
  
  def read(self, settings):
    """
    Raises:
    
    * `SettingsNotFoundInSourceError` - See the `SettingSource` class.
    
    * `SettingSourceNotFoundError` - Could not find the specified source.
    
    * `SettingSourceInvalidFormatError` - Specified source has invalid format.
      This could happen if the source was edited manually.
    """
    self._settings_from_parasite = self._read_from_parasite(self.source_name)
    if self._settings_from_parasite is None:
      raise SettingSourceNotFoundError(
        _('Could not find persistent setting source "{}".').format(self.source_name))
    
    self._read(settings)
    
    self._settings_from_parasite = None
  
  def write(self, settings):
    settings_from_parasite = self._read_from_parasite(self.source_name)
    if settings_from_parasite is not None:
      setting_names_and_values = settings_from_parasite
      setting_names_and_values.update(self._to_dict(settings))
    else:
      setting_names_and_values = self._to_dict(settings)
    
    self.write_dict(setting_names_and_values)
  
  def clear(self):
    parasite = gimp.parasite_find(self.source_name)
    if parasite is None:
      return
    
    gimp.parasite_detach(self.source_name)
  
  def read_dict(self, setting_names):
    setting_names_and_values = {}
    
    self._settings_from_parasite = self._read_from_parasite(self.source_name)
    if self._settings_from_parasite is None:
      return setting_names_and_values
    
    for name in setting_names:
      try:
        setting_names_and_values[name] = self._read_setting_value(name)
      except KeyError:
        pass
    
    self._settings_from_parasite = None
    
    return setting_names_and_values
  
  def write_dict(self, setting_names_and_values):
    data = pickle.dumps(setting_names_and_values)
    gimp.parasite_attach(
      gimp.Parasite(self.source_name, gimpenums.PARASITE_PERSISTENT, data))
  
  def has_data(self):
    """
    Return `True` if the setting source contains data for the `source_name`
    identifier, `False` otherwise.
    """
    return gimp.parasite_find(self.source_name) is not None
  
  def _read_setting_value(self, setting_name):
    return self._settings_from_parasite[setting_name]
  
  def _read_from_parasite(self, parasite_name):
    parasite = gimp.parasite_find(parasite_name)
    if parasite is None:
      return None
    
    try:
      settings_from_parasite = pickle.loads(parasite.data)
    except Exception:
      raise SettingSourceInvalidFormatError(
        _('Settings for this plug-in stored in "{}" may be corrupt. '
          "This could happen if the file was edited manually.\n"
          "To fix this, save the settings again or reset them.").format(
            self._parasite_filepath))
    
    return settings_from_parasite
  
  def _to_dict(self, settings):
    """
    Format the setting name and value to a dict that can be serialized by the
    `pickle` module.
    """
    settings_dict = collections.OrderedDict()
    for setting in settings:
      settings_dict[setting.get_path("root")] = setting.value
    
    return settings_dict
