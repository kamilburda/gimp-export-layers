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
This module defines setting sources - the means to load and save settings:
  * "session-persistently" - i.e. settings persist during one GIMP session
  * persistently
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

str = unicode

import abc
import collections

try:
  import cPickle as pickle
except ImportError:
  import pickle

import gimp
import gimpenums
import gimpshelf

from . import pgsetting
from . import pgsettingpersistor

#===============================================================================


class SettingSource(object):
  
  """
  This class provides an interface for reading and writing settings to
  permanent or semi-permanent sources.
  
  For easier usage, use the `SettingPersistor` class instead.
  
  Attributes:
  
  * `_settings_not_found` - List of settings not found in source when the `read()`
    method is called.
  """
  
  __metaclass__ = abc.ABCMeta
  
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
      found in the source. All settings that were not found in the source will be
      stored in the `settings_not_found` list. This list is cleared on each read()
      call.
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
    calling `clear()` does nothing.
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


#-------------------------------------------------------------------------------


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
    super(SessionPersistentSettingSource, self).__init__()
    
    self.source_name = source_name
    self._separator = "_"
  
  def read(self, settings):
    self._read(settings)
  
  def write(self, settings):
    for setting in settings:
      gimpshelf.shelf[(self.source_name + self._separator + setting.name).encode()] = setting.value
  
  def _retrieve_setting_value(self, setting_name):
    return gimpshelf.shelf[(self.source_name + self._separator + setting_name).encode()]


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
    super(PersistentSettingSource, self).__init__()
    
    self.source_name = source_name
    self._parasite_filename = "parasiterc"
  
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
        _("Could not find persistent setting source \"{0}\".").format(self.source_name))
    
    self._read(settings)
    
    del self._settings_from_parasite
  
  def write(self, settings):
    settings_from_parasite = self._read_from_parasite(self.source_name)
    if settings_from_parasite is not None:
      settings_to_write = settings_from_parasite
      settings_to_write.update(self._to_dict(settings))
    else:
      settings_to_write = self._to_dict(settings)
    
    settings_data = pickle.dumps(settings_to_write)
    gimp.parasite_attach(gimp.Parasite(self.source_name, gimpenums.PARASITE_PERSISTENT, settings_data))
  
  def clear(self):
    parasite = gimp.parasite_find(self.source_name)
    if parasite is None:
      return
    
    gimp.parasite_detach(self.source_name)
  
  def _read_from_parasite(self, parasite_name):
    parasite = gimp.parasite_find(parasite_name)
    if parasite is None:
      return None
    
    try:
      settings_from_parasite = pickle.loads(parasite.data)
    except (pickle.UnpicklingError, AttributeError, EOFError):
      raise pgsettingpersistor.SettingSourceInvalidFormatError(
        _("Settings for this plug-in stored in the \"{0}\" file may be corrupt. "
          "This could happen if the file was edited manually.\n"
          "To fix this, save the settings again or reset them.").format(self._parasite_filename))
    
    return settings_from_parasite
  
  def _retrieve_setting_value(self, setting_name):
    return self._settings_from_parasite[setting_name]
  
  def _to_dict(self, settings):
    """
    Format the setting name and value to a dict, which the `pickle` module can
    properly serialize and de-serialize.
    """
    
    settings_dict = collections.OrderedDict()
    for setting in settings:
      settings_dict[setting.name] = setting.value
    
    return settings_dict
