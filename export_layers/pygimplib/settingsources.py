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

from . import constants as pgconstants
from . import setting as pgsetting

from ._settingsources_errors import *


class SettingSource(future.utils.with_metaclass(abc.ABCMeta, object)):
  """
  This class provides an interface for reading and writing settings to setting
  sources. For easier usage, is is highly recommended to use the
  `SettingPersistor` class instead.
  
  Attributes:
  
  * `source_name` - A unique identifier to distinguish entries from different
    plug-ins in this source.
  """
  
  def __init__(self, source_name):
    self.source_name = source_name
  
  def read(self, settings):
    """
    Read setting values from the source and assign them to the settings
    specified in the `settings` iterable.
    
    If a setting value from the source is invalid, the setting will be reset to
    its default value.
    
    Raises:
    
    * `SettingsNotFoundInSourceError` - At least one of the settings is not
      found in the source. All settings that were not found in the source will
      be stored in this exception in the `settings_not_found` attribute.
    
    * `SettingSourceNotFoundError` - Could not find the source.
    
    * `SettingSourceInvalidFormatError` - The source has an invalid format. This
      could happen if the source was directly edited manually.
    """
    settings_from_source = self.read_dict()
    if settings_from_source is None:
      raise SettingSourceNotFoundError(
        _('Could not find setting source "{}".').format(self.source_name))
    
    settings_not_found = []
    
    for setting in settings:
      try:
        value = settings_from_source[setting.get_path("root")]
      except KeyError:
        settings_not_found.append(setting)
      else:
        try:
          setting.set_value(value)
        except pgsetting.SettingValueError:
          setting.reset()
    
    if settings_not_found:
      raise SettingsNotFoundInSourceError(
        _("The following settings could not be found:\n{}").format(
          "\n".join(setting.get_path() for setting in settings_not_found)),
        settings_not_found)
  
  def write(self, settings):
    """
    Write setting values from settings specified in the `settings` iterable
    to the source. Settings in the source but not specified in `settings` are
    kept intact.
    """
    settings_from_source = self.read_dict()
    if settings_from_source is not None:
      setting_names_and_values = settings_from_source
      setting_names_and_values.update(self._settings_to_dict(settings))
    else:
      setting_names_and_values = self._settings_to_dict(settings)
    
    self.write_dict(setting_names_and_values)
  
  @abc.abstractmethod
  def clear(self):
    """
    Remove all settings from the source.
    
    This method is useful if settings are renamed, since the old settings would
    not be removed and would thus lead to bloating the source.
    """
    pass
  
  @abc.abstractmethod
  def has_data(self):
    """
    Return `True` if the setting source contains data, `False` otherwise.
    """
    pass
  
  @abc.abstractmethod
  def read_dict(self):
    """
    Read all setting values from the source to a dictionary of
    `(setting name, setting value)` pairs. Return the dictionary.
    
    If the source does not exist, return `None`.
    
    This method is useful in the unlikely case it is more convenient to directly
    modify or remove settings from the source.
    
    Raises:
    
    * `SettingSourceInvalidFormatError` - Data could not be read due to likely
      being corrupt.
    """
    pass
  
  @abc.abstractmethod
  def write_dict(self, setting_names_and_values):
    """
    Write setting names and values to the source specified in the
    `setting_names_and_values` dictionary containing
    `(setting name, setting value)` pairs.
    
    The entire setting source is overwritten by the specified dictionary.
    Settings not specified in `setting_names_and_values` thus will be removed.
    
    This method is useful in the unlikely case it is more convenient to directly
    modify or remove settings from the source.
    """
    pass
  
  def _settings_to_dict(self, settings):
    settings_dict = collections.OrderedDict()
    for setting in settings:
      settings_dict[setting.get_path("root")] = setting.value
    
    return settings_dict


class SessionWideSettingSource(SettingSource):
  """
  This class reads settings from/writes settings to a source that persists
  during one GIMP session.
  
  Internally, the GIMP shelf is used as the session-wide source and contains the
  name and the last used value of each setting.
  """
  
  def clear(self):
    gimpshelf.shelf[self._get_key()] = None
  
  def has_data(self):
    return (
      gimpshelf.shelf.has_key(self._get_key())
      and gimpshelf.shelf[self._get_key()] is not None)
  
  def read_dict(self):
    try:
      return gimpshelf.shelf[self._get_key()]
    except KeyError:
      return None
    except Exception:
      raise SettingSourceInvalidFormatError(
        _("Session-wide settings for this plug-in may be corrupt.\n"
          "To fix this, save the settings again or reset them."))
  
  def write_dict(self, setting_names_and_values):
    gimpshelf.shelf[self._get_key()] = setting_names_and_values
  
  def _get_key(self):
    return self.source_name.encode(pgconstants.GIMP_CHARACTER_ENCODING)


class PersistentSettingSource(SettingSource):
  """
  This class reads settings from/writes settings to a persistent source.
  
  The persistent source in this case is the the `parasiterc` file maintained by
  GIMP store data that persist between GIMP sessions. The file contains the name
  and the last used value of each setting.
  """
  
  def __init__(self, source_name):
    super().__init__(source_name)
    
    self._parasite_filepath = os.path.join(gimp.directory, "parasiterc")
  
  def clear(self):
    if gimp.parasite_find(self.source_name) is None:
      return
    
    gimp.parasite_detach(self.source_name)
  
  def has_data(self):
    return gimp.parasite_find(self.source_name) is not None
  
  def read_dict(self):
    parasite = gimp.parasite_find(self.source_name)
    if parasite is None:
      return None
    
    try:
      settings_from_source = pickle.loads(parasite.data)
    except Exception:
      raise SettingSourceInvalidFormatError(
        _('Settings for this plug-in stored in "{}" may be corrupt. '
          "This could happen if the file was edited manually.\n"
          "To fix this, save the settings again or reset them.").format(
            self._parasite_filepath))
    
    return settings_from_source
  
  def write_dict(self, setting_names_and_values):
    data = pickle.dumps(setting_names_and_values)
    gimp.parasite_attach(
      gimp.Parasite(self.source_name, gimpenums.PARASITE_PERSISTENT, data))
