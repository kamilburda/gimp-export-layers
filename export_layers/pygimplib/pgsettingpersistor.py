#-------------------------------------------------------------------------------
#
# This file is part of pygimplib.
#
# Copyright (C) 2014 khalim19 <khalim19@gmail.com>
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
#-------------------------------------------------------------------------------

"""
This module:
* defines the means to load and save settings:
  * persistently
  * "semi-persistently" - settings persist during one GIMP session
"""

#===============================================================================

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division

str = unicode

#===============================================================================

import errno
import abc
from collections import OrderedDict
import json

import gimpshelf

from . import pgsetting

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
    to the source.
    
    Parameters:
    
    * `settings` - Any iterable sequence containing `Setting` objects.
    """
    
    pass

  @property
  def settings_not_found(self):
    return self._settings_not_found


class SettingSourceError(Exception):
  pass


class SettingsNotFoundInSourceError(SettingSourceError):
  pass


class SettingSourceFileNotFoundError(SettingSourceError):
  pass


class SettingSourceReadError(SettingSourceError):
  pass


class SettingSourceInvalidFormatError(SettingSourceError):
  pass


class SettingSourceWriteError(SettingSourceError):
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
  
  def read(self, settings):
    self._settings_not_found = []
    
    for setting in settings:
      try:
        value = gimpshelf.shelf[(self.source_name + setting.name).encode()]
      except KeyError:
        self._settings_not_found.append(setting)
      else:
        try:
          setting.set_value(value)
        except pgsetting.SettingValueError:
          setting.reset()
    
    if self._settings_not_found:
      raise SettingsNotFoundInSourceError(
        "The following settings could not be found in any sources: " +
        str([setting.name for setting in self._settings_not_found])
      )
  
  def write(self, settings):
    for setting in settings:
      gimpshelf.shelf[(self.source_name + setting.name).encode()] = setting.value


class PersistentSettingSource(SettingSource):
  
  """
  This class reads settings from/writes settings to a persistent source.
  
  This class stores settings in a JSON file, containing the name and last used
  value of each setting.
  
  Attributes:
  
  * `filename` - Filename of the persistent source.
  """
  
  def __init__(self, filename):
    super(PersistentSettingSource, self).__init__()
    
    self.filename = filename
  
  def read(self, settings):
    """
    Raises:
    
    * `SettingsNotFoundInSourceError` - see the `SettingSource` class.
    
    * `SettingSourceFileNotFoundError` - Could not find the specified file.
    
    * `SettingSourceReadError` - Could not read from the specified file (IOError
      or OSError was raised).
    
    * `SettingSourceInvalidFormatError` - Specified file has invalid format, i.e.
      it is not recognized as a valid JSON file.
    """
    
    self._settings_not_found = []
    
    try:
      with open(self.filename, 'r') as json_file:
        settings_from_file = json.load(json_file)
    except (IOError, OSError) as e:
      if e.errno == errno.ENOENT:
        raise SettingSourceFileNotFoundError(
          _("Could not find file with settings \"{0}\".").format(self.filename)
        )
      else:
        raise SettingSourceReadError(
          _("Could not read settings from file \"{0}\". Make sure the file can be "
            "accessed to.").format(self.filename)
        )
    except ValueError as e:
      raise SettingSourceInvalidFormatError(
        _("File with settings \"{0}\" is corrupt. This could happen if the file "
          "was edited manually.\n"
          "To fix this, save the settings again (to overwrite the file) "
          "or delete the file.").format(self.filename)
      )
    
    for setting in settings:
      try:
        value = settings_from_file[setting.name]
      except KeyError:
        self._settings_not_found.append(setting)
      else:
        try:
          setting.set_value(value)
        except pgsetting.SettingValueError:
          setting.reset()
    
    if self._settings_not_found:
      raise SettingsNotFoundInSourceError(
        "The following settings could not be found in any sources: " +
        str([setting.name for setting in self._settings_not_found])
      )
  
  def write(self, settings):
    """
    Write the name and value of the settings from the `settings` iterable to the
    file.
    
    Raises:
    
    * `SettingSourceWriteError` - Could not write to the specified file (IOError
      or OSError was raised).
    """
    
    settings_dict = self._to_dict(settings)
    
    try:
      with open(self.filename, 'w') as json_file:
        json.dump(settings_dict, json_file)
    except (IOError, OSError):
      raise SettingSourceWriteError(
        _("Could not write settings to file \"{0}\". "
          "Make sure the file can be accessed to.").format(self.filename)
      )
  
  def _to_dict(self, settings):
    """
    Format the setting name and value to a dict, which the `json` module can
    properly serialize and de-serialize.
    """
    
    settings_dict = OrderedDict()
    for setting in settings:
      settings_dict[setting.name] = setting.value
    
    return settings_dict


#===============================================================================


class SettingPersistor(object):
  
  """
  This class:
  * serves as a wrapper for `SettingSource` classes
  * reads settings from multiple setting sources
  * write settings to multiple setting sources
  """
  
  __STATUSES = SUCCESS, READ_FAIL, WRITE_FAIL, NOT_ALL_SETTINGS_FOUND = (0, 1, 2, 3)
  
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
    
    settings = cls._list_settings(settings_or_groups)
    
    for source in setting_sources:
      try:
        source.read(settings)
      except (SettingsNotFoundInSourceError, SettingSourceFileNotFoundError) as e:
        if type(e) == SettingsNotFoundInSourceError:
          settings = source.settings_not_found
        
        if source == setting_sources[-1]:
          return cls._status(cls.NOT_ALL_SETTINGS_FOUND, e.message)
        else:
          continue
      except (SettingSourceReadError, SettingSourceInvalidFormatError) as e:
        return cls._status(cls.READ_FAIL, e.message)
      else:
        break
    
    return cls._status(cls.SUCCESS)
  
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
    
    for source in setting_sources:
      try:
        source.write(settings)
      except SettingSourceWriteError as e:
        return cls._status(cls.WRITE_FAIL, e.message)
    
    return cls._status(cls.SUCCESS)
  
  @classmethod
  def _status(cls, status, message=None):
    return status, message if message is not None else ""
  
  @classmethod
  def _list_settings(cls, settings_or_groups):
    # Put all settings into one list so that the `read()` and `write()` methods
    # are invoked only once per each source.
    settings = []
    for setting_or_group in settings_or_groups:
      if isinstance(setting_or_group, pgsetting.Setting):
        setting = setting_or_group
        settings.append(setting)
      else:
        group = setting_or_group
        settings.extend(list(group.iterate_all()))
    return settings
