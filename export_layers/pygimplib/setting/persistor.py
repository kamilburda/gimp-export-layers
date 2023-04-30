# -*- coding: utf-8 -*-

"""Wrapper of `setting.sources` module to allow easy loading/saving using
multiple setting sources.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import collections

from . import _sources_errors

__all__ = [
  'Persistor',
]


class Persistor(object):
  """Wrapper for `setting.sources.Source` classes to easily read and write
  settings to multiple sources at once.
  """
  
  _STATUSES = SUCCESS, READ_FAIL, WRITE_FAIL, NOT_ALL_SETTINGS_FOUND, NO_SOURCE = (0, 1, 2, 3, 4)
  
  DEFAULT_SETTING_SOURCES = collections.OrderedDict()
  """Dictionary of setting sources to use in methods of this class if no other
  setting sources in these methods are specified.
  
  The dictionary must contain pairs of (key, `setting.sources.Source` instance
  or list of `setting.sources.Source` instances).
  
  The key is a string that identifies a group of sources. The key can be
  specified in `setting.settings.Setting` instances within `setting_sources`
  to indicate which groups of sources the setting can be read from or written
  to. For example, if the `setting_sources` attribute of a setting contains
  [`'persistent'`], then only setting sources under the key `'persistent'`
  will be considered and other sources will be ignored. This is useful if you
  need to e.g. save settings to a different file while still ignoring settings
  not containing `'persistent'`.
  """
  
  @classmethod
  def load(cls, settings_or_groups, setting_sources=None):
    """Loads setting values from the specified dictionary of setting sources
    to the specified list of settings or setting groups (`settings_or_groups`).
    
    If `setting_sources` is `None`, `DEFAULT_SETTING_SOURCES` will be used. If
    `DEFAULT_SETTING_SOURCES` is None or an empty dictionary, `READ_FAIL` is
    returned.
    
    The order of sources in the `setting_sources` list indicates the preference
    of the sources, beginning with the first source in the list. If not all
    settings could be found in the first source, the second source is read to
    assign values to the remaining settings. This continues until all settings
    are read.
    
    If settings have invalid values, their default values will be assigned.
    
    If some settings could not be found in any of the sources,
    their default values will be assigned.
    
    Parameters:
    
    * `settings_or_groups` - List of `settings.Setting` or `group.Group`
      instances whose values are loaded from `setting_sources`.
    
    * `setting_sources` - Dictionary or list of setting sources or `None`. If a
      dictionary, it must contain (key, setting source) pairs. If a list, it
      must contain keys and all keys must have a mapping to a source in
      `DEFAULT_SETTING_SOURCES`. See `DEFAULT_SETTING_SOURCES` for more
      information on the key. If `setting_sources` is `None`,
      `DEFAULT_SETTING_SOURCES` will be used.
    
    Returns:
    
      * `status`:
      
        * `SUCCESS` - Settings successfully loaded. This status is also returned
          if `settings_or_groups` or `setting_sources` is empty or `None`.
        
        * `NOT_ALL_SETTINGS_FOUND` - Could not find some settings from
          any of the sources. Default values are assigned to these settings.
        
        * `READ_FAIL` - Could not read data from the first source where this
          error occurred. May occur for file sources with e.g. denied read
          permission.
        
        * `NO_SOURCE` - There is no source to load settings from. This occurs if
          `setting_sources` is `None` and `DEFAULT_SETTING_SOURCES` is empty, or
          if `setting_sources` is a list of source names and there is at least
          one source name not present in `DEFAULT_SETTING_SOURCES`.
      
      * `status_message` - Message describing `status` in more detail.
    """
    if not settings_or_groups:
      return cls._status(cls.SUCCESS)
    
    if setting_sources is None:
      setting_sources = cls.DEFAULT_SETTING_SOURCES
    
    if not setting_sources:
      return cls._status(cls.NO_SOURCE)
    
    setting_sources_list = cls._get_source_list(setting_sources)
    
    if not setting_sources_list:
      return cls._status(cls.NO_SOURCE)
    
    all_settings = cls._list_settings(settings_or_groups)
    all_settings_found = True
    not_all_settings_found_message = ''
    
    settings = all_settings
    
    for setting in all_settings:
      setting.invoke_event('before-load')
    
    for index, source in enumerate(setting_sources_list):
      try:
        source.read(settings)
      except (_sources_errors.SettingsNotFoundInSourceError,
              _sources_errors.SourceNotFoundError) as e:
        if isinstance(e, _sources_errors.SettingsNotFoundInSourceError):
          settings = e.settings_not_found
        
        if index == len(setting_sources_list) - 1:
          all_settings_found = False
          not_all_settings_found_message = str(e)
          break
        else:
          continue
      except (_sources_errors.SourceReadError,
              _sources_errors.SourceInvalidFormatError) as e:
        return cls._status(cls.READ_FAIL, str(e))
      else:
        break
    
    for setting in all_settings:
      setting.invoke_event('after-load')
    
    if all_settings_found:
      return cls._status(cls.SUCCESS)
    else:
      return cls._status(cls.NOT_ALL_SETTINGS_FOUND, not_all_settings_found_message)
  
  @classmethod
  def save(cls, settings_or_groups, setting_sources=None):
    """Saves setting values from specified list of settings or setting groups
    (`settings_or_groups`) to the specified setting sources.
    
    Parameters:
    
    * `settings_or_groups` - List of `settings.Setting` or `group.Group`
      instances whose values are saved to `setting_sources`.
    
    * `setting_sources` - Dictionary or list of setting sources or `None`. See
      `load()` for more information.
    
    Returns:
    
      * `status`:
      
        * `SUCCESS` - Settings successfully saved. This status is also returned
          if `settings_or_groups` or `setting_sources` is empty or `None`.
        
        * `WRITE_FAIL` - Could not write data to the first source where this
          error occurred. May occur for file sources with e.g. denied write
          permission.
        
        * `NO_SOURCE` - There is no source to save settings to. This occurs if
          `setting_sources` is `None` and `DEFAULT_SETTING_SOURCES` is empty, or
          if `setting_sources` is a list of source names and there is at least
          one source name not present in `DEFAULT_SETTING_SOURCES`.
      
      * `status_message` - Message describing `status` in more detail.
    """
    if not settings_or_groups:
      return cls._status(cls.SUCCESS)
    
    if setting_sources is None:
      setting_sources = cls.DEFAULT_SETTING_SOURCES
    
    if not setting_sources:
      return cls._status(cls.NO_SOURCE)
    
    setting_sources_list = cls._get_source_list(setting_sources)
    
    if not setting_sources_list:
      return cls._status(cls.NO_SOURCE)
    
    settings = cls._list_settings(settings_or_groups)
    
    for setting in settings:
      setting.invoke_event('before-save')
    
    for source in setting_sources_list:
      try:
        source.write(settings)
      except _sources_errors.SourceError as e:
        return cls._status(cls.WRITE_FAIL, str(e))
    
    for setting in settings:
      setting.invoke_event('after-save')
    
    return cls._status(cls.SUCCESS)
  
  @classmethod
  def clear(cls, setting_sources=None):
    """Removes all settings from all specified setting sources.
    
    Parameters:
    
    * `setting_sources` - Dictionary or list of setting sources or `None`. See
      `load()` for more information.
    """
    if setting_sources is None:
      setting_sources = cls.DEFAULT_SETTING_SOURCES
    
    setting_sources_list = cls._get_source_list(setting_sources)
    
    if setting_sources is not None:
      for source in setting_sources_list:
        source.clear()
  
  @staticmethod
  def _status(status, message=None):
    return status, message if message is not None else ''
  
  @classmethod
  def _get_source_list(cls, setting_sources):
    if not isinstance(setting_sources, dict):
      setting_sources_list = []
      
      for key in setting_sources:
        try:
          setting_sources_list.append(cls.DEFAULT_SETTING_SOURCES[key])
        except KeyError:
          return []
    else:
      setting_sources_list = list(setting_sources.values())
    
    return setting_sources_list
  
  @staticmethod
  def _list_settings(settings_or_groups):
    # Put all settings into one list so that `read()` and `write()` are invoked
    # only once per each source.
    settings = []
    for setting_or_group in settings_or_groups:
      if isinstance(setting_or_group, collections.Iterable):
        group = setting_or_group
        settings.extend(list(group.walk()))
      else:
        setting = setting_or_group
        settings.append(setting)
    return settings
