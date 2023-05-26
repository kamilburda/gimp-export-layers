# -*- coding: utf-8 -*-

"""Loading and saving settings."""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *
import future.utils

import abc
import ast
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

from .. import constants as pgconstants
from .. import utils as pgutils

from . import settings as settings_

from ._sources_errors import *

__all__ = [
  'Source',
  'GimpSessionSource',
  'GimpPersistentSource',
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
        settings_not_found=settings_not_found)
  
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
    
    Settings not belonging to `source_name` are kept intact.
    
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
      setting_dict = setting.to_dict()
      settings_dict[setting.get_path('root')] = setting_dict['value']
    
    return settings_dict


class GimpSessionSource(Source):
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


class GimpPersistentSource(Source):
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
  
  _SOURCE_NAME_CONTENTS_SEPARATOR = ' '
  
  def __init__(self, source_name, filepath):
    super().__init__(source_name)
    
    self._filepath = filepath
  
  @property
  def filepath(self):
    return self._filepath
  
  def clear(self):
    data = self.read_data()
    if data is not None and self.source_name in data:
      del data[self.source_name]
      
      self.write_data(data)
  
  def has_data(self):
    """Returns `True` if the source contains data and the data have a valid
    format, `'invalid_format'` if the source contains some data, but the data
    have an invalid format, and `False` otherwise.
    
    `'invalid_format'` represents an ambiguous value since there is no way to
    determine if there are data under `source_name` or not.
    """
    try:
      settings_from_source = self.read_dict()
    except SourceError:
      return 'invalid_format'
    else:
      return settings_from_source is not None
  
  def read_dict(self):
    data = self.read_data()
    if data is not None and self.source_name in data:
      return self._get_settings_from_pickled_data(data[self.source_name])
    else:
      return None
  
  def write_dict(self, setting_names_and_values):
    data_for_source = self._pickle_settings(setting_names_and_values)
    
    data = self.read_data()
    if data is None:
      data = collections.OrderedDict([(self.source_name, data_for_source)])
    else:
      data[self.source_name] = data_for_source
    
    self.write_data(data)
  
  def read_data(self):
    """Reads the entire file into a dictionary of (source name, contents) pairs.
    
    The dictionary also contains contents from other source names if they exist.
    """
    if not os.path.isfile(self._filepath):
      return None
    
    data = collections.OrderedDict()
    
    try:
      with io.open(self._filepath, 'r', encoding=pgconstants.TEXT_FILE_ENCODING) as f:
        for line in f:
          split = line.split(self._SOURCE_NAME_CONTENTS_SEPARATOR, 1)
          if len(split) == 2:
            source_name, contents = split
            data[source_name] = contents
    except Exception as e:
      raise SourceReadError(str(e))
    else:
      return data
  
  def write_data(self, data):
    """Writes `data` into the file, overwriting the entire file contents.
    
    `data` is a dictionary of (source name, contents) pairs.
    """
    try:
      with io.open(self._filepath, 'w', encoding=pgconstants.TEXT_FILE_ENCODING) as f:
        for source_name, contents in data.items():
          f.write(source_name + self._SOURCE_NAME_CONTENTS_SEPARATOR + contents + '\n')
    except Exception as e:
      raise SourceWriteError(str(e))
  
  def _get_settings_from_pickled_data(self, contents):
    try:
      return pickle.loads(ast.literal_eval(contents))
    except Exception as e:
      raise SourceInvalidFormatError(str(e))
  
  def _pickle_settings(self, settings):
    try:
      return repr(pickle.dumps(settings))
    except Exception as e:
      raise SourceInvalidFormatError(str(e))
