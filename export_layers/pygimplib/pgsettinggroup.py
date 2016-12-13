# -*- coding: utf-8 -*-
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
This module defines a class to group settings together for their easier creation
and management.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

str = unicode

import collections
import inspect

from . import pgsetting
from . import pgsettingpersistor

#===============================================================================


class SettingGroup(object):
  
  """
  This class
  * allows to create a group of related settings (`Setting` objects),
  * allows to store existing setting groups,
  * can perform certain operations on all settings and nested groups at once.
    
  Unless otherwise stated, "settings" in the rest of the documentation for
  this class refers to both `Setting` and `SettingGroup` objects.
  """
  
  _SETTING_PATH_SEPARATOR = "/"
  
  def __init__(self, name, setting_list, **setting_params):
    """
    Create settings from the specified list. The list can contain both `Setting`
    and `SettingGroup` objects.
    
    The order of settings in the list corresponds to the order in which the
    settings are iterated.
    
    Parameters:
    
    * `name` - A name (string) that uniquely identifies the setting group.
    
    * `setting_list` - List of settings (`Setting` or `SettingGroup` objects).
    
    * `**setting_params` - (setting attribute: value) pairs to assign to
      each setting in the group. Attributes in individual settings override
      these attributes.
    
    ---------
    
    To add a setting, use a dictionary containing (attribute name, value) pairs.
    "attribute name" is a string that represents an argument passed when
    instantiating the appropriate `Setting` class.
    
    The following attributes must always be specified:
      * 'type' - type of the Setting object to instantiate.
      * 'name' - setting name.
      * 'default_value' - default value of the setting.
    
    The 'name' attribute must not contain forward slashes ('/') to allow
    accessing settings via setting paths.
    
    For more attributes, check the documentation of the setting classes. Some
    subclasses may require specifying additional mandatory attributes.
    
    Multiple settings with the same name and in different nested groups are
    possible. Each such setting can be accessed like any other:
    
      settings['main']['autocrop']
      settings['advanced']['autocrop']
    """
    
    self._name = name
    self._setting_params = setting_params
    self._settings = collections.OrderedDict()
    
    self.add(setting_list)
    
    # key: `Setting` or `SettingGroup` instance; value: set of ignore tags (strings)
    self._ignored_settings_and_tags = {}
    
    # Used in the `_next()` method
    self._settings_iterator = None
  
  @property
  def name(self):
    return self._name
  
  def __str__(self):
    return "<{0} '{1}'>".format(type(self).__name__, self.name)
  
  def __getitem__(self, setting_name_or_path):
    """
    Access the setting or group by its name (string).
    
    If a setting is inside a nested group, you can access the setting as follows:
      
      settings['main']['autocrop']
    
    Or by a setting path:
    
      settings['main/autocrop']
    """
    
    if self._SETTING_PATH_SEPARATOR in setting_name_or_path:
      return self._get_setting_from_path(setting_name_or_path)
    else:
      return self._settings[setting_name_or_path]
  
  def __contains__(self, setting_name_or_path):
    if self._SETTING_PATH_SEPARATOR in setting_name_or_path:
      try:
        self._get_setting_from_path(setting_name_or_path)
      except KeyError:
        return False
      else:
        return True
    else:
      return setting_name_or_path in self._settings
  
  def __iter__(self):
    """
    Iterate over settings in the order they were created or added.
    
    This method does not iterate over nested groups. Use `iterate_all()` in that
    case.
    """
    
    for setting in self._settings.values():
      yield setting
  
  def __len__(self):
    return len(self._settings)
  
  def iterate_all(self, ignore_tags=None):
    """
    Iterate over all settings in the group, including settings in nested groups.
    
    `ignore_tags` is a list of strings indicating that settings having one of
    these tags attached are ignored. Ignore tags are attached to the settings by
    calling the `set_ignore_tags()` method.
    """
    
    def _should_ignore_func(setting_or_group, ignored_settings_and_tags, ignore_tags):
      return (setting_or_group in ignored_settings_and_tags
              and any(tag in ignored_settings_and_tags[setting_or_group] for tag in ignore_tags))
    
    def _never_ignore(*args):
      return False
    
    if ignore_tags is not None:
      _should_ignore = _should_ignore_func
    else:
      _should_ignore = _never_ignore
    
    groups = [self]
    ignored_settings_and_tags = self._ignored_settings_and_tags
    
    while groups:
      try:
        setting_or_group = groups[0]._next()
        ignored_settings_and_tags.update(groups[0]._ignored_settings_and_tags)
      except StopIteration:
        groups.pop(0)
        continue
      
      if isinstance(setting_or_group, SettingGroup):
        setting_group = setting_or_group
        if not _should_ignore(setting_group, ignored_settings_and_tags, ignore_tags):
          groups.insert(0, setting_group)
        else:
          continue
      else:
        setting = setting_or_group
        if not _should_ignore(setting, ignored_settings_and_tags, ignore_tags):
          yield setting
        else:
          continue
  
  def add(self, setting_list):
    """
    Add settings to the group. For details about the format of `setting_list`,
    refer to the documentation for the `__init__()` method.
    """
    
    for setting_or_group in setting_list:
      if isinstance(setting_or_group, SettingGroup):
        self._add_setting_group(setting_or_group)
      else:
        self._create_setting(setting_or_group)
  
  def remove(self, setting_names):
    """
    Remove settings from the group specified by their names.
    """
    
    for setting_name in setting_names:
      if setting_name in self._settings:
        del self._settings[setting_name]
      else:
        raise KeyError("setting '{0}' not found".format(setting_name))
  
  def set_ignore_tags(self, settings_and_tags):
    """
    For the specified settings, specify a list of "ignore tags".
    
    When the `iterate_all()` method is called and the `ignore_tags` parameter is
    specified, all settings matching at least one tag from `ignore_tags` will be
    excluded from the iteration.
    
    When the tags match the method names in this class that operate on all
    settings, such as `reset()` or `apply_gui_values_to_settings()`, the methods
    ignore those settings.
    
    Parameters:
    
    * `settings_and_tags` - A dict of (setting path, tag list) pairs.
    
    Raises:
    
    * `KeyError` - Setting does not exist.
    """
    
    self._ignored_settings_and_tags.update({
      self._get_setting_from_path(setting_path): set(tags)
      for setting_path, tags in settings_and_tags.items()
    })
  
  def unset_ignore_tags(self, settings_and_tags):
    """
    Unset specified ignore tags for the specified settings. For more
    information, see the `set_ignore_tags()` method.
    
    Parameters:
    
    * `settings_and_tags` - A dict of (setting path, tag list) pairs to unset.
    
    Raises:
    
    * `KeyError` - Setting does not exist.
    
    * `ValueError` - Ignore tags were not set for the setting.
    """
    
    def _check_ignore_tags_exist(setting, ignore_tags):
      if setting not in self._ignored_settings_and_tags:
        raise ValueError("no tags were set for setting '{0}'".format(setting.name))
      
      invalid_ignore_tags = []
      for tag in ignore_tags:
        if tag not in self._ignored_settings_and_tags[setting]:
          invalid_ignore_tags.append(tag)
      
      if invalid_ignore_tags:
        raise ValueError("the following tags were not set for setting '{0}': {1}".format(
          setting.name, invalid_ignore_tags))
    
    for setting_path, ignore_tags in settings_and_tags.items():
      setting = self._get_setting_from_path(setting_path)
      _check_ignore_tags_exist(setting, ignore_tags)
      for tag in ignore_tags:
        self._ignored_settings_and_tags[setting].remove(tag)
      if not self._ignored_settings_and_tags[setting]:
        del self._ignored_settings_and_tags[setting]
  
  def reset(self):
    """
    Reset all settings in this group. Ignore settings with the `reset` ignore
    tag.
    """
    
    for setting in self.iterate_all(ignore_tags=['reset']):
      setting.reset()
  
  def load(self):
    """
    Load all settings in this group. Ignore settings with the `load` ignore
    tag. If there are multiple combinations of setting sources within the group
    (e.g. some settings within this group having their own setting sources),
    loading is performed for each combination separately.
    
    Return the status and the status message as per the
    `pgsettingpersistor.SettingPersistor.load()` method. For multiple
    combinations of setting sources, return the "worst" status
    (`READ_FAIL` or `WRITE_FAIL` > `NOT_ALL_SETTINGS_FOUND` > `SUCCESS`) and
    a status message containing status messages of all calls to `load()`.
    """
    
    for setting in self.iterate_all(ignore_tags=['load']):
      setting.invoke_event('before-load-group')
    
    return_values = self._load_save('load', pgsettingpersistor.SettingPersistor.load)
    
    for setting in self.iterate_all(ignore_tags=['load']):
      setting.invoke_event('after-load-group')
    
    return return_values
  
  def save(self):
    """
    Save all settings in this group. Ignore settings with the `save` ignore
    tag. Return the status and the status message as per the
    `pgsettingpersistor.SettingPersistor.save()` method.
    
    For more information, refer to the `load()` method.
    """
    
    for setting in self.iterate_all(ignore_tags=['save']):
      setting.invoke_event('before-save-group')
    
    return_values = self._load_save('save', pgsettingpersistor.SettingPersistor.save)
    
    for setting in self.iterate_all(ignore_tags=['save']):
      setting.invoke_event('after-save-group')
    
    return return_values
  
  def initialize_gui(self, custom_gui=None):
    """
    Initialize GUI for all settings.
    
    Settings that are not provided with a readily available GUI can have their
    GUI initialized using the `custom_gui` dict. `custom_gui` contains
    (setting name, list of arguments to `pgsetting.Setting.set_gui`) pairs. The
    "enable GUI update?" boolean in the list is optional and defaults to True.
    For more information about parameters in the list, see the `Setting.set_gui`
    method.
    
    Example:
    
    file_extension_entry = gtk.Entry()
    ...
    main_settings.initialize_gui({
      'file_extension': [SettingGuiTypes.text_entry, file_extension_entry]
      ...
    })
    """
    
    if custom_gui is None:
      custom_gui = {}
    
    for setting in self.iterate_all():
      if setting.name not in custom_gui:
        setting.set_gui()
      else:
        set_gui_args = custom_gui[setting.name]
        setting.set_gui(*set_gui_args)
  
  def apply_gui_values_to_settings(self):
    """
    Apply GUI element values, entered by the user, to settings.
    Ignore settings with the `apply_gui_values_to_settings` ignore tag.
    
    This method will not have any effect on settings with automatic
    GUI-to-setting value updating.
    
    Raises:
    
    * `SettingValueError` - One or more values are invalid. The exception
    message contains messages from all invalid settings.
    """
    
    exception_messages = []
    exception_settings = []
    
    for setting in self.iterate_all(ignore_tags=['apply_gui_values_to_settings']):
      try:
        setting.gui.update_setting_value()
      except pgsetting.SettingValueError as e:
        exception_messages.append(e.message)
        exception_settings.append(e.setting)
    
    if exception_messages:
      exception_message = "\n".join(exception_messages)
      raise pgsetting.SettingValueError(
        exception_message, setting=exception_settings[0], messages=exception_messages, settings=exception_settings)
  
  def _next(self):
    """
    Return the next element when iterating the settings. Used by `iterate_all()`.
    """
    
    if self._settings_iterator is None:
      self._settings_iterator = self._settings.itervalues()
    
    try:
      next_element = self._settings_iterator.next()
    except StopIteration:
      self._settings_iterator = None
      raise StopIteration
    else:
      return next_element
  
  def _load_save(self, load_save_ignore_tag, load_save_func):
    
    def _get_worst_status(status_and_messages):
      worst_status = pgsettingpersistor.SettingPersistor.SUCCESS
      
      if pgsettingpersistor.SettingPersistor.NOT_ALL_SETTINGS_FOUND in status_and_messages:
        worst_status = pgsettingpersistor.SettingPersistor.NOT_ALL_SETTINGS_FOUND
      
      if pgsettingpersistor.SettingPersistor.READ_FAIL in status_and_messages:
        worst_status = pgsettingpersistor.SettingPersistor.READ_FAIL
      elif pgsettingpersistor.SettingPersistor.WRITE_FAIL in status_and_messages:
        worst_status = pgsettingpersistor.SettingPersistor.WRITE_FAIL
      
      return worst_status
    
    settings = self.iterate_all(ignore_tags=[load_save_ignore_tag])
    settings = [setting for setting in settings if setting.setting_sources]
    
    settings_per_sources = collections.OrderedDict()
    
    for setting in settings:
      sources = tuple(setting.setting_sources)
      if sources not in settings_per_sources:
        settings_per_sources[sources] = []
      
      settings_per_sources[sources].append(setting)
    
    status_and_messages = collections.OrderedDict()
    
    for sources, settings in settings_per_sources.items():
      status, message = load_save_func(settings, sources)
      status_and_messages[status] = message
    
    worst_status = _get_worst_status(status_and_messages)
    
    return worst_status, status_and_messages.get(worst_status, "")
  
  def _create_setting(self, setting_data):
    try:
      setting_type = setting_data['type']
    except KeyError:
      raise TypeError(self._get_missing_mandatory_attributes_message(['type']))
    
    del setting_data['type']
    
    try:
      setting_data['name']
    except KeyError:
      raise TypeError(self._get_missing_mandatory_attributes_message(['name']))
    
    if self._SETTING_PATH_SEPARATOR in setting_data['name']:
      raise ValueError(
        "'{0}': setting name must not contain '{1}'".format(setting_data['name'], self._SETTING_PATH_SEPARATOR))
    
    if setting_data['name'] in self._settings:
      raise KeyError("setting '{0}' already exists".format(setting_data['name']))
    
    for setting_attribute, setting_attribute_value in self._setting_params.items():
      if setting_attribute not in setting_data:
        setting_data[setting_attribute] = setting_attribute_value
    
    try:
      self._settings[setting_data['name']] = setting_type(**setting_data)
    except TypeError as e:
      missing_mandatory_arguments = self._get_missing_mandatory_arguments(setting_type, setting_data)
      if missing_mandatory_arguments:
        message = self._get_missing_mandatory_attributes_message(missing_mandatory_arguments)
      else:
        message = e.message
      raise TypeError(message)
  
  def _add_setting_group(self, setting_group):
    if setting_group.name in self._settings:
      raise KeyError("setting group '{0}' already exists".format(setting_group.name))
    
    self._settings[setting_group.name] = setting_group
  
  def _get_missing_mandatory_arguments(self, setting_type, setting_data):
    mandatory_arg_names = self._get_mandatory_argument_names(setting_type.__init__)
    return [arg_name for arg_name in mandatory_arg_names if arg_name not in setting_data]
  
  def _get_mandatory_argument_names(self, func):
    arg_spec = inspect.getargspec(func)
    arg_default_values = arg_spec[3] if arg_spec[3] is not None else []
    num_mandatory_args = len(arg_spec[0]) - len(arg_default_values)
    
    mandatory_args = arg_spec[0][0:num_mandatory_args]
    if mandatory_args[0] == 'self':
      del mandatory_args[0]
    
    return mandatory_args
  
  def _get_missing_mandatory_attributes_message(self, attribute_names):
    return "missing the following mandatory setting attributes: {0}".format(', '.join(attribute_names))
  
  def _get_setting_from_path(self, setting_path):
    setting_path_components = setting_path.split(self._SETTING_PATH_SEPARATOR)
    current_group = self
    for group_name in setting_path_components[:-1]:
      if group_name in current_group:
        current_group = current_group._settings[group_name]
      else:
        raise KeyError("group '{0}' in path '{1}' does not exist".format(group_name, setting_path))
    
    try:
      setting = current_group[setting_path_components[-1]]
    except KeyError:
      raise KeyError("setting '{0}' not found in path '{1}'".format(setting_path_components[-1], setting_path))
    
    return setting
