# -*- coding: utf-8 -*-

"""Loading and saving settings."""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *
import future.utils

import abc
import collections
import io
import os

try:
  import cPickle as pickle
except ImportError:
  import pickle

import gimp
import gimpenums
import gimpshelf

from .. import utils as pgutils

from . import settings as settings_

from ._sources_errors import *

__all__ = [
  'Source',
  'SessionSource',
  'PersistentSource',
]


class Source(future.utils.with_metaclass(abc.ABCMeta, object)):
  """Abstract class for reading and writing settings to a source.
  
  Attributes:
  
  * `source_name` - A unique identifier to distinguish entries from different
    GIMP plug-ins or procedures.
  """
  
  def __init__(self, source_name):
    self.source_name = source_name
  
  def read(self, settings):
    """Reads setting values and assigns them to the settings specified in the
    `settings` iterable.
    
    If a setting value from the source is invalid, the setting will be reset to
    its default value.
    
    Raises:
    
    * `SettingsNotFoundInSourceError` - At least one of the settings is not
      found in the source. All settings that were not found in the source will
      be stored in this exception in the `settings_not_found` attribute.
    
    * `SourceNotFoundError` - Could not find the source.
    
    * `SourceInvalidFormatError` - The source has an invalid format. This could
      happen if the source was directly edited manually.
    """
    settings_from_source = self.read_dict()
    if settings_from_source is None:
      raise SourceNotFoundError(
        _('Could not find setting source "{}".').format(self.source_name))
    
    settings_not_found = []
    
    for setting in settings:
      try:
        value = settings_from_source[setting.get_path('root')]
      except KeyError:
        settings_not_found.append(setting)
      else:
        try:
          setting.set_value(value)
        except settings_.SettingValueError:
          setting.reset()
    
    if settings_not_found:
      raise SettingsNotFoundInSourceError(
        _('The following settings could not be found:\n{}').format(
          '\n'.join(setting.get_path() for setting in settings_not_found)),
        settings_not_found)
  
  def write(self, settings):
    """Writes setting values from settings specified in the `settings` iterable.
    
    Settings in the source but not specified in `settings` are kept intact.
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
    """Removes all settings from the source.
    
    This method is useful if settings are renamed, since the old settings would
    not be removed and would thus lead to bloating the source.
    """
    pass
  
  @abc.abstractmethod
  def has_data(self):
    """Returns `True` if the source contains data, `False` otherwise."""
    pass
  
  @abc.abstractmethod
  def read_dict(self):
    """Reads all setting values from the source to a dictionary of
    `(setting name, setting value)` pairs and returns the dictionary.
    
    If the source does not exist, `None` is returned.
    
    This method is useful in the unlikely case it is more convenient to directly
    modify or remove settings from the source.
    
    Raises:
    
    * `SourceInvalidFormatError` - Data could not be read due to likely being
      corrupt.
    """
    pass
  
  @abc.abstractmethod
  def write_dict(self, setting_names_and_values):
    """Writes setting names and values to the source specified in the
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
      settings_dict[setting.get_path('root')] = setting.value
    
    return settings_dict


class SessionSource(Source):
  """Class reading and writing settings to a source that persists within a
  single GIMP session.
  
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
      raise SourceInvalidFormatError(
        _('Session-wide settings for this plug-in may be corrupt.\n'
          'To fix this, save the settings again or reset them.'))
  
  def write_dict(self, setting_names_and_values):
    gimpshelf.shelf[self._get_key()] = setting_names_and_values
  
  def _get_key(self):
    return pgutils.safe_encode_gimp(self.source_name)


class PersistentSource(Source):
  """Class reading and writing settings to a persistent source (i.e. permanent
  storage) maintained by GIMP.
  
  The persistent source in this case is the the `parasiterc` file maintained by
  GIMP. The file contains the name and the last used value of each setting.
  """
  
  def __init__(self, source_name):
    super().__init__(source_name)
    
    self._parasite_filepath = os.path.join(gimp.directory, 'parasiterc')
  
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
      raise SourceInvalidFormatError(
        _('Settings for this plug-in stored in "{}" may be corrupt.'
          ' This could happen if the file was edited manually.'
          '\nTo fix this, save the settings again or reset them.').format(
            self._parasite_filepath))
    
    return settings_from_source
  
  def write_dict(self, setting_names_and_values):
    data = pickle.dumps(setting_names_and_values)
    gimp.parasite_attach(
      gimp.Parasite(self.source_name, gimpenums.PARASITE_PERSISTENT, data))


class PickleFileSource(Source):
  """Class reading and writing settings permanently to a filename, formatted
  with the Python `pickle` module.
  """
  
  def __init__(self, source_name, filepath):
    super().__init__(source_name)
    
    self._filepath = filepath
  
  @property
  def filepath(self):
    return self._filepath
  
  def clear(self):
    data_dict = self._read_all_data()
    if data_dict is not None and self.source_name in data_dict:
      del data_dict[self.source_name]
      
      self.write_dict(data_dict)
  
  def has_data(self):
    return self.read_dict() is not None
  
  def write(self, settings):
    data_dict = self._read_all_data()
    
    if data_dict is not None and self.source_name in data_dict:
      setting_names_and_values = data_dict[self.source_name]
      setting_names_and_values.update(self._settings_to_dict(settings))
      
      data_dict[self.source_name] = setting_names_and_values
      
      self.write_dict(data_dict)
    else:
      setting_names_and_values = self._settings_to_dict(settings)
      
      if data_dict is None:
        data_dict = {self.source_name: setting_names_and_values}
      else:
        data_dict[self.source_name] = setting_names_and_values
        
      self.write_dict(data_dict)
  
  def read_dict(self):
    data_dict = self._read_all_data()
    if data_dict is not None and self.source_name in data_dict:
      return data_dict[self.source_name]
    else:
      return None
  
  def write_dict(self, setting_names_and_values):
    try:
      with io.open(self._filepath, 'wb') as f:
        pickle.dump(setting_names_and_values, f)
    except Exception as e:
      raise SourceInvalidFormatError(str(e), self._filepath)
  
  def _read_all_data(self):
    if not os.path.isfile(self._filepath):
      return None
    
    try:
      with io.open(self._filepath, 'rb') as f:
        data_dict = pickle.load(f)
    except Exception as e:
      raise SourceInvalidFormatError(str(e), self._filepath)
    else:
      return data_dict
