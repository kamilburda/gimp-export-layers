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

try:
  import json
except ImportError:
  _json_module_found = False
else:
  _json_module_found = True

import gimp
import gimpenums
import gimpshelf

from .. import constants as pgconstants
from .. import utils as pgutils

from . import group as group_
from . import settings as settings_

from ._sources_errors import *

__all__ = [
  'Source',
  'GimpShelfSource',
  'GimpParasiteSource',
  'PickleFileSource',
  'JsonFileSource',
]


class Source(future.utils.with_metaclass(abc.ABCMeta, object)):
  """Abstract class for reading and writing settings to a source.
  
  Attributes:
  
  * `source_name` - A unique identifier to distinguish entries from different
    GIMP plug-ins or procedures.
  
  * `source_type` - If `'persistent'`, this indicates that the setting source
    should store settings permanently. If `'session'`, this indicates that the
    source should store settings within a single GIMP session (i.e. until the
    currently running GIMP instance is closed).
  """
  
  def __init__(self, source_name, source_type):
    self.source_name = source_name
    self.source_type = source_type
  
  def read(self, settings_or_groups):
    """Reads setting attributes from data and assigns them to existing settings
    specified in the `settings_or_groups` iterable, or creates settings within
    groups specified in `settings_or_groups`.
    
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
    settings_from_source = self.read_data_from_source()
    if settings_from_source is None:
      raise SourceNotFoundError(
        _('Could not find setting source "{}".').format(self.source_name))
    
    settings_not_found = []
    
    for setting_or_group in settings_or_groups:
      try:
        value = settings_from_source[setting_or_group.get_path('root')]
      except KeyError:
        settings_not_found.append(setting_or_group)
      else:
        try:
          setting_or_group.set_value(value)
        except settings_.SettingValueError:
          setting_or_group.reset()
    
    if settings_not_found:
      raise SettingsNotFoundInSourceError(
        _('The following settings could not be found:\n{}').format(
          '\n'.join(setting.get_path() for setting in settings_not_found)),
        settings_not_found=settings_not_found)
  
  def write(self, settings_or_groups):
    """Writes data representing settings specified in the `settings_or_groups`
    iterable.
    
    Settings in the source but not specified in `settings_or_groups` are kept
    intact.
    """
    data = self.read_data_from_source()
    if data is None:
      data = collections.OrderedDict()
    
    if self.source_name not in data:
      data[self.source_name] = []
    
    self._update_data_for_source(settings_or_groups, data[self.source_name])
    
    self.write_data_to_source(data)
  
  def _update_data_for_source(self, settings_or_groups, data_for_source):
    for setting_or_group in settings_or_groups:
      # Create all parent groups if they do not exist.
      # `current_list` at the end of the loop will hold the immediate parent of
      # `setting_or_group`.
      current_list = data_for_source
      for parent in setting_or_group.parents:
        parent_dict = self._find_dict(current_list, parent)[0]
        
        if parent_dict is None:
          parent_dict = {'name': parent.name, 'settings': []}
          current_list.append(parent_dict)
        
        current_list = parent_dict['settings']
      
      if isinstance(setting_or_group, settings_.Setting):
        self._setting_to_data(current_list, setting_or_group)
      elif isinstance(setting_or_group, group_.Group):
        self._group_to_data(current_list, setting_or_group)
      else:
        raise TypeError('settings_or_groups must contain only Setting or Group instances')
  
  def _setting_to_data(self, group_list, setting):
    setting_dict, index = self._find_dict(group_list, setting)
    
    if setting_dict is not None:
      # Overwrite the original setting dict
      group_list[index] = setting.to_dict(source_type=self.source_type)
    else:
      group_list.append(setting.to_dict(source_type=self.source_type))
  
  def _group_to_data(self, group_list, group):
    settings_or_groups_and_dicts = [(group, group_list)]
    
    while settings_or_groups_and_dicts:
      setting_or_group, parent_list = settings_or_groups_and_dicts.pop(0)
      
      if isinstance(setting_or_group, settings_.Setting):
        self._setting_to_data(parent_list, setting_or_group)
      elif isinstance(setting_or_group, group_.Group):
        current_group_dict = self._find_dict(parent_list, setting_or_group)[0]
        
        if current_group_dict is None:
          current_group_dict = {'name': setting_or_group.name, 'settings': []}
          parent_list.append(current_group_dict)
        
        for child_setting_or_group in reversed(setting_or_group):
          settings_or_groups_and_dicts.insert(
            0, (child_setting_or_group, current_group_dict['settings']))
      else:
        raise TypeError('only Setting or Group instances are allowed as the first element')
  
  def _find_dict(self, data_list, setting_or_group):
    if isinstance(setting_or_group, settings_.Setting):
      key = 'value'
    else:
      key = 'settings'
    
    for i, dict_ in enumerate(data_list):
      if dict_.get('name', None) == setting_or_group.name and key in dict_:
        return dict_, i
    
    return None, None
  
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
  def read_data_from_source(self):
    """Reads data representing settings from the source.
    
    Usually you do not need to call this method. Use `read()` instead which
    assigns values to existing settings or creates settings dynamically from the
    data.
    
    If the source does not exist, `None` is returned.
    
    Raises:
    
    * `SourceInvalidFormatError` - Data could not be read due to being corrupt.
    """
    pass
  
  @abc.abstractmethod
  def write_data_to_source(self, data):
    """Writes data representing settings to the source.
    
    The entire setting source is overwritten by the specified data.
    Settings not specified thus will be removed.
    
    Usually you do not need to call this method. Use `write()` instead which
    creates an appropriate persistent representation of the settings that can
    later be loaded via `read()`.
    """
    pass


class GimpShelfSource(Source):
  """Class for reading and writing settings to the GIMP shelf.
  
  This class is appropriate to maintain settings within a single GIMP session
  as the GIMP shelf is reset when closing GIMP.
  """
  
  def __init__(self, source_name, source_type='session'):
    super().__init__(source_name, source_type)
  
  def clear(self):
    gimpshelf.shelf[self._get_key()] = None
  
  def has_data(self):
    return (
      gimpshelf.shelf.has_key(self._get_key())
      and gimpshelf.shelf[self._get_key()] is not None)
  
  def read_data_from_source(self):
    try:
      return gimpshelf.shelf[self._get_key()]
    except KeyError:
      return None
    except Exception:
      raise SourceInvalidFormatError(
        _('Session-wide settings for this plug-in may be corrupt.\n'
          'To fix this, save the settings again or reset them.'))
  
  def write_data_to_source(self, data):
    gimpshelf.shelf[self._get_key()] = data
  
  def _get_key(self):
    return pgutils.safe_encode_gimp(self.source_name)


class GimpParasiteSource(Source):
  """Class reading and writing settings to the `parasiterc` file maintained by
  GIMP.
  
  This class is useful as a persistent source (i.e. permanent storage) of
  settings.
  """
  
  def __init__(self, source_name, source_type='persistent'):
    super().__init__(source_name, source_type)
    
    self._parasite_filepath = os.path.join(gimp.directory, 'parasiterc')
  
  def clear(self):
    if gimp.parasite_find(self.source_name) is None:
      return
    
    gimp.parasite_detach(self.source_name)
  
  def has_data(self):
    return gimp.parasite_find(self.source_name) is not None
  
  def read_data_from_source(self):
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
  
  def write_data_to_source(self, data):
    gimp.parasite_attach(
      gimp.Parasite(self.source_name, gimpenums.PARASITE_PERSISTENT, pickle.dumps(data)))


class PickleFileSource(Source):
  """Class reading and writing settings to a file, formatted using the Python
  `pickle` module.
  
  This class is useful as a persistent source (i.e. permanent storage) of
  settings. This class is appropriate to use when saving settings to a file path
  chosen by the user.
  """
  
  _SOURCE_NAME_CONTENTS_SEPARATOR = ' '
  
  def __init__(self, source_name, filepath, source_type='persistent'):
    super().__init__(source_name, source_type)
    
    self._filepath = filepath
  
  @property
  def filepath(self):
    return self._filepath
  
  def clear(self):
    all_data = self.read_all_data()
    if all_data is not None and self.source_name in all_data:
      del all_data[self.source_name]
      
      self.write_all_data(all_data)
  
  def has_data(self):
    """Returns `True` if the source contains data and the data have a valid
    format, `'invalid_format'` if the source contains some data, but the data
    have an invalid format, and `False` otherwise.
    
    `'invalid_format'` represents an ambiguous value since there is no way to
    determine if there are data under `source_name` or not.
    """
    try:
      settings_from_source = self.read_data_from_source()
    except SourceError:
      return 'invalid_format'
    else:
      return settings_from_source is not None
  
  def read_data_from_source(self):
    all_data = self.read_all_data()
    if all_data is not None and self.source_name in all_data:
      return self._get_settings_from_pickled_data(all_data[self.source_name])
    else:
      return None
  
  def write_data_to_source(self, data):
    raw_data = self._pickle_settings(data)
    
    all_data = self.read_all_data()
    if all_data is None:
      all_data = collections.OrderedDict([(self.source_name, raw_data)])
    else:
      all_data[self.source_name] = raw_data
    
    self.write_all_data(all_data)
  
  def read_all_data(self):
    """Reads the contents of the entire file into a dictionary of
    (source name, contents) pairs.
    
    The dictionary also contains contents from other source names if they exist.
    """
    if not os.path.isfile(self._filepath):
      return None
    
    all_data = collections.OrderedDict()
    
    try:
      with io.open(self._filepath, 'r', encoding=pgconstants.TEXT_FILE_ENCODING) as f:
        for line in f:
          split = line.split(self._SOURCE_NAME_CONTENTS_SEPARATOR, 1)
          if len(split) == 2:
            source_name, contents = split
            all_data[source_name] = contents
    except Exception as e:
      raise SourceReadError(str(e))
    else:
      return all_data
  
  def write_all_data(self, all_data):
    """Writes `all_data` into the file, overwriting the entire file contents.
    
    `all_data` is a dictionary of (source name, contents) pairs.
    """
    try:
      with io.open(self._filepath, 'w', encoding=pgconstants.TEXT_FILE_ENCODING) as f:
        for source_name, contents in all_data.items():
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


class JsonFileSource(Source):
  """Class reading and writing settings to a JSON file.
  
  This class is useful as a persistent source (i.e. permanent storage) of
  settings. This class is appropriate to use when saving settings to a file path
  chosen by the user.
  
  Compared to `PickleFileSource`, JSON files are more readable and, if need be,
  easy to modify by hand.
  """
  
  def __init__(self, source_name, filepath, source_type='persistent'):
    if not _json_module_found:
      raise RuntimeError('"json" module not found')
    
    super().__init__(source_name, source_type)
    
    self._filepath = filepath
  
  @property
  def filepath(self):
    return self._filepath
  
  def clear(self):
    all_data = self.read_all_data()
    if all_data is not None and self.source_name in all_data:
      del all_data[self.source_name]
      
      self.write_all_data(all_data)
  
  def has_data(self):
    """Returns `True` if the source contains data and the data have a valid
    format, `'invalid_format'` if the source contains some data, but the data
    have an invalid format, and `False` otherwise.
    
    `'invalid_format'` represents an ambiguous value since there is no way to
    determine if there are data under `source_name` or not.
    """
    try:
      settings_from_source = self.read_data_from_source()
    except SourceError:
      return 'invalid_format'
    else:
      return settings_from_source is not None
  
  def read_data_from_source(self):
    all_data = self.read_all_data()
    if all_data is not None and self.source_name in all_data:
      return all_data[self.source_name]
    else:
      return None
  
  def write_data_to_source(self, data):
    all_data = self.read_all_data()
    if all_data is None:
      all_data = collections.OrderedDict([(self.source_name, data)])
    else:
      all_data[self.source_name] = data
    
    self.write_all_data(all_data)
  
  def read_all_data(self):
    """Reads the contents of the entire file into a dictionary of
    (source name, contents) pairs.
    
    The dictionary also contains contents from other source names if they exist.
    """
    if not os.path.isfile(self._filepath):
      return None
    
    all_data = collections.OrderedDict()
    
    try:
      with io.open(self._filepath, 'r', encoding=pgconstants.TEXT_FILE_ENCODING) as f:
        all_data = json.load(f)
    except Exception as e:
      raise SourceReadError(str(e))
    else:
      return all_data
  
  def write_all_data(self, all_data):
    """Writes `all_data` into the file, overwriting the entire file contents.
    
    `all_data` is a dictionary of (source name, contents) pairs.
    """
    try:
      with io.open(self._filepath, 'w', encoding=pgconstants.TEXT_FILE_ENCODING) as f:
        # Workaround for Python 2 code to properly handle Unicode strings
        raw_data = json.dumps(all_data, f, sort_keys=False, indent=4, separators=(',', ': '))
        f.write(unicode(raw_data))
    except Exception as e:
      raise SourceWriteError(str(e))
