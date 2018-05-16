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
This module defines a class to group settings together for their easier creation
and management.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *
import future.utils

import collections
import inspect

from . import pgsetting
from . import pgsettingpersistor
from . import pgsettingutils
from . import pgutils

#===============================================================================


@future.utils.python_2_unicode_compatible
class SettingGroup(pgsettingutils.SettingParentMixin):
  
  """
  This class:
  * allows to create a group of related settings (`Setting` objects),
  * allows to store existing setting groups,
  * can perform certain operations on all settings and nested groups at once.
    
  Unless otherwise stated, "settings" in the rest of the documentation for
  this class refers to both `Setting` and `SettingGroup` objects.
  
  Attributes:
  
  * `name` (read-only) - A name (string) that uniquely identifies the setting
    group.
  
  * `display_name` (read-only) - Setting group name in human-readable format.
  
  * `description` (read-only) - A more detailed description of the group. By
    default, description is derived from `display_name`.
  
  * `setting_attributes` (read-only) - Dictionary of (setting attribute: value)
    pairs to assign to each setting in the group. Attributes in individual
    settings override these attributes.
  
  * `tags` - A set of arbitrary tags attached to the setting. Tags can be used
    to e.g. iterate over a specific subset of settings.
  """
  
  def __init__(self, name, display_name=None, description=None, setting_attributes=None):
    super().__init__()
    
    self._name = name
    self._display_name = pgsettingutils.get_processed_display_name(
      display_name, self._name)
    self._description = pgsettingutils.get_processed_description(
      description, self._display_name)
    self._setting_attributes = (
      setting_attributes if setting_attributes is not None else {})
    
    self._settings = collections.OrderedDict()
    self._tags = set()
    
    # Used in the `_next()` method
    self._settings_iterator = None
  
  @property
  def name(self):
    return self._name
  
  @property
  def display_name(self):
    return self._display_name
  
  @property
  def description(self):
    return self._description
  
  @property
  def setting_attributes(self):
    return self._setting_attributes
  
  @property
  def tags(self):
    return self._tags
  
  def __str__(self):
    return pgutils.stringify_object(self, self.name)
  
  def __getitem__(self, setting_name_or_path):
    """
    Access the setting or group by its name (string).
    
    If a setting is inside a nested group, you can access the setting as
    follows:
      
      settings["main"]["autocrop"]
    
    As a more compact alternative, you may specify a setting path:
    
      settings["main/autocrop"]
    """
    
    if pgsettingutils.SETTING_PATH_SEPARATOR in setting_name_or_path:
      return self._get_setting_from_path(setting_name_or_path)
    else:
      return self._settings[setting_name_or_path]
  
  def __contains__(self, setting_name_or_path):
    if pgsettingutils.SETTING_PATH_SEPARATOR in setting_name_or_path:
      try:
        self._get_setting_from_path(setting_name_or_path)
      except KeyError:
        return False
      else:
        return True
    else:
      return setting_name_or_path in self._settings
  
  def _get_setting_from_path(self, setting_path):
    setting_path_components = setting_path.split(pgsettingutils.SETTING_PATH_SEPARATOR)
    current_group = self
    for group_name in setting_path_components[:-1]:
      if group_name in current_group:
        current_group = current_group._settings[group_name]
      else:
        raise KeyError("group '{0}' in path '{1}' does not exist".format(
          group_name, setting_path))
    
    try:
      setting = current_group[setting_path_components[-1]]
    except KeyError:
      raise KeyError("setting '{0}' not found in path '{1}'".format(
        setting_path_components[-1], setting_path))
    
    return setting
  
  def __iter__(self):
    """
    Iterate over settings in the order they were created or added.
    
    This method does not iterate over nested groups. Use `walk()` in that
    case.
    """
    
    for setting in self._settings.values():
      yield setting
  
  def __len__(self):
    return len(self._settings)
  
  def get_path(self, relative_path_setting_group=None):
    """
    This is a wrapper method for `pgsettingutils.get_setting_path`. Consult the
    method for more information.
    """
    
    return pgsettingutils.get_setting_path(self, relative_path_setting_group)
  
  def add(self, setting_list):
    """
    Add settings to the group.
    
    The order of settings in the list corresponds to the order in which the
    settings are iterated.
    
    `setting_list` is a list that can contain `Setting` objects, `SettingGroup`
    objects or dictionaries representing `Setting` objects to be created.
    
    Each dictionary contains (attribute name: value) pairs, where
    "attribute name" is a string that represents an argument passed when
    instantiating the setting. The following attributes must always be
    specified:
      * "type" - type of the Setting object to instantiate.
      * "name" - setting name.
      * "default_value" - default value of the setting.
    
    The "name" attribute must not contain forward slashes ("/") (which are used
    to access settings via paths).
    
    For more attributes, check the documentation of the setting classes. Some
    `Setting` subclasses may require specifying additional mandatory attributes.
    
    Multiple settings with the same name and in different nested groups are
    possible. Each such setting can be accessed like any other:
    
      settings["main"]["autocrop"]
      settings["advanced"]["autocrop"]
    
    Settings created from dictionaries are by default assigned setting
    attributes specified during the initialization of this class. These
    attributes can be overridden by attributes in individual settings.
    """
    
    for setting in setting_list:
      if isinstance(setting, (pgsetting.Setting, SettingGroup)):
        setting = self._add_setting(setting)
      else:
        setting = self._create_setting(setting)
      
      self._set_as_parent_for_setting(setting)
  
  def _add_setting(self, setting):
    if setting.name in self._settings:
      raise ValueError("{0} already exists in {1}".format(setting, self))
    
    if setting == self:
      raise ValueError("cannot add {0} as a child of itself".format(setting))
    
    self._settings[setting.name] = setting
    
    return setting
  
  def _create_setting(self, setting_data):
    try:
      setting_type = setting_data["type"]
    except KeyError:
      raise TypeError(self._get_missing_mandatory_attributes_message(["type"]))
    
    # Do not modify the original `setting_data` in case it is expected to be reused.
    setting_data_copy = {key: setting_data[key] for key in setting_data if key != "type"}
    
    try:
      setting_data_copy["name"]
    except KeyError:
      raise TypeError(self._get_missing_mandatory_attributes_message(["name"]))
    
    if pgsettingutils.SETTING_PATH_SEPARATOR in setting_data_copy["name"]:
      raise ValueError(
        "setting name '{0}' must not contain path separator '{1}'".format(
          setting_data_copy["name"], pgsettingutils.SETTING_PATH_SEPARATOR))
    
    if setting_data_copy["name"] in self._settings:
      raise ValueError("setting '{0}' already exists".format(setting_data_copy["name"]))
    
    for setting_attribute, setting_attribute_value in self._setting_attributes.items():
      if setting_attribute not in setting_data_copy:
        setting_data_copy[setting_attribute] = setting_attribute_value
    
    setting = self._instantiate_setting(setting_type, setting_data_copy)
    
    return setting
  
  def _instantiate_setting(self, setting_type, setting_data_copy):
    try:
      setting = setting_type(**setting_data_copy)
    except TypeError as e:
      missing_mandatory_arguments = self._get_missing_mandatory_arguments(
        setting_type, setting_data_copy)
      if missing_mandatory_arguments:
        message = self._get_missing_mandatory_attributes_message(
          missing_mandatory_arguments)
      else:
        message = str(e)
      raise TypeError(message)
    
    self._settings[setting_data_copy["name"]] = setting
    
    return setting
  
  def _get_missing_mandatory_arguments(self, setting_type, setting_data):
    mandatory_arg_names = self._get_mandatory_argument_names(setting_type.__init__)
    return [arg_name for arg_name in mandatory_arg_names if arg_name not in setting_data]
  
  def _get_mandatory_argument_names(self, func):
    arg_spec = inspect.getargspec(func)
    arg_default_values = arg_spec[3] if arg_spec[3] is not None else []
    num_mandatory_args = len(arg_spec[0]) - len(arg_default_values)
    
    mandatory_args = arg_spec[0][0:num_mandatory_args]
    if mandatory_args[0] == "self":
      del mandatory_args[0]
    
    return mandatory_args
  
  def _get_missing_mandatory_attributes_message(self, attribute_names):
    return "missing the following mandatory setting attributes: {0}".format(
      ", ".join(attribute_names))
  
  def remove(self, setting_names):
    """
    Remove settings from the group specified by their names.
    """
    
    for setting_name in setting_names:
      if setting_name in self._settings:
        del self._settings[setting_name]
      else:
        raise KeyError("setting '{0}' not found".format(setting_name))
  
  def walk(self, include_setting_func=None, include_groups=False, walk_callbacks=None):
    """
    Return a generator that walks (iterates over) all settings in the group,
    including settings in nested groups. The generator performs a pre-order
    traversal.
    
    If `include_setting_func` is None, iterate over all settings. Otherwise,
    `include_setting_func` is a function that should return True if a setting
    should be yielded and False if a setting should be ignored.
    
    If `include_groups` is True, yield setting groups as well.
    
    `walk_callbacks` is an `SettingGroupWalkCallbacks` instance that invokes
    additional commands during the walk of the group. By default, the callbacks
    do nothing. For more information, see the `SettingGroupWalkCallbacks` class.
    """
    
    if include_setting_func is None:
      include_setting_func = pgutils.create_empty_func(return_value=True)
    
    if walk_callbacks is None:
      walk_callbacks = SettingGroupWalkCallbacks()
    
    groups = [self]
    
    while groups:
      try:
        setting_or_group = groups[0]._next()
      except StopIteration:
        if groups[0] != self:
          walk_callbacks.on_end_group_walk(groups[0])
        
        groups.pop(0)
        continue
      
      if isinstance(setting_or_group, SettingGroup):
        if include_setting_func(setting_or_group):
          groups.insert(0, setting_or_group)
          
          if include_groups:
            walk_callbacks.on_visit_group(setting_or_group)
            yield setting_or_group
        else:
          continue
      else:
        if include_setting_func(setting_or_group):
          walk_callbacks.on_visit_setting(setting_or_group)
          yield setting_or_group
        else:
          continue
  
  def _next(self):
    """
    Return the next element when iterating the settings. Used by `walk()`.
    """
    
    if self._settings_iterator is None:
      self._settings_iterator = self._settings.itervalues()
    
    try:
      next_element = next(self._settings_iterator)
    except StopIteration:
      self._settings_iterator = None
      raise StopIteration
    else:
      return next_element
  
  def reset(self):
    """
    Reset all settings in this group. Ignore settings with the "ignore_reset"
    tag.
    """
    
    def _has_ignore_reset_tag(setting):
      return "ignore_reset" not in setting.tags
    
    for setting in self.walk(include_setting_func=_has_ignore_reset_tag):
      setting.reset()
  
  def load(self):
    """
    Load all settings in this group. Ignore settings with the "ignore_load" tag.
    If there are multiple combinations of setting sources within the group (e.g.
    some settings within this group having their own setting sources), loading
    is performed for each combination separately.
    
    Return the status and the status message as per the
    `pgsettingpersistor.SettingPersistor.load()` method. For multiple
    combinations of setting sources, return the "worst" status
    (from the "best" to the "worst": `SUCCESS`, `NOT_ALL_SETTINGS_FOUND`,
    `READ_FAIL` or `WRITE_FAIL`) and a status message containing status messages
    of all calls to `load()`.
    """
    
    return self._load_save_group(
      "ignore_load", pgsettingpersistor.SettingPersistor.load,
      "before-load-group", "after-load-group")
  
  def save(self):
    """
    Save all settings in this group. Ignore settings with the "ignore_save" tag.
    Return the status and the status message as per the
    `pgsettingpersistor.SettingPersistor.save()` method.
    
    For more information, refer to the `load()` method.
    """
    
    return self._load_save_group(
      "ignore_save", pgsettingpersistor.SettingPersistor.save,
      "before-save-group", "after-save-group")
  
  def _load_save_group(
        self, load_save_ignore_tag, load_save_func,
        before_load_save_group_event_type, after_load_save_group_event_type):
    
    def _has_ignore_tag(setting):
      return load_save_ignore_tag not in setting.tags
    
    for setting in self.walk(include_setting_func=_has_ignore_tag):
      setting.invoke_event(before_load_save_group_event_type)
    
    return_values = self._load_save(load_save_ignore_tag, load_save_func)
    
    for setting in self.walk(include_setting_func=_has_ignore_tag):
      setting.invoke_event(after_load_save_group_event_type)
    
    return return_values
  
  def _load_save(self, load_save_ignore_tag, load_save_func):
    
    def _get_worst_status(status_and_messages):
      worst_status = pgsettingpersistor.SettingPersistor.SUCCESS
      
      if (pgsettingpersistor.SettingPersistor.NOT_ALL_SETTINGS_FOUND
          in status_and_messages):
        worst_status = pgsettingpersistor.SettingPersistor.NOT_ALL_SETTINGS_FOUND
      
      if pgsettingpersistor.SettingPersistor.READ_FAIL in status_and_messages:
        worst_status = pgsettingpersistor.SettingPersistor.READ_FAIL
      elif pgsettingpersistor.SettingPersistor.WRITE_FAIL in status_and_messages:
        worst_status = pgsettingpersistor.SettingPersistor.WRITE_FAIL
      
      return worst_status
    
    setting_iterator = self.walk(
      include_setting_func=lambda setting: load_save_ignore_tag not in setting.tags)
    settings = [setting for setting in setting_iterator if setting.setting_sources]
    
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
      "file_extension": [SettingGuiTypes.text_entry, file_extension_entry]
      ...
    })
    """
    
    if custom_gui is None:
      custom_gui = {}
    
    for setting in self.walk():
      if setting.name not in custom_gui:
        setting.set_gui()
      else:
        set_gui_args = custom_gui[setting.name]
        setting.set_gui(*set_gui_args)
  
  def apply_gui_values_to_settings(self):
    """
    Apply GUI element values, entered by the user, to settings.
    Ignore settings with the "ignore_apply_gui_value_to_setting" tag.
    
    This method will not have any effect on settings with automatic
    GUI-to-setting value updating.
    
    Raises:
    
    * `SettingValueError` - One or more values are invalid. The exception
    message contains messages from all invalid settings.
    """
    
    def _has_ignore_tag(setting):
      return "ignore_apply_gui_value_to_setting" not in setting.tags
    
    exception_messages = []
    exception_settings = []
    
    for setting in self.walk(include_setting_func=_has_ignore_tag):
      try:
        setting.gui.update_setting_value()
      except pgsetting.SettingValueError as e:
        exception_messages.append(str(e))
        exception_settings.append(e.setting)
    
    if exception_messages:
      exception_message = "\n".join(exception_messages)
      raise pgsetting.SettingValueError(
        exception_message, setting=exception_settings[0],
        messages=exception_messages, settings=exception_settings)


class SettingGroupWalkCallbacks(object):
  
  """
  This class defines callbacks called during the `SettingGroup.walk()` method.
  By default, the callbacks do nothing.
  
  `on_visit_setting` is called before the current `Setting` object is yielded.
  `on_visit_group` is called before the current `SettingGroup` object is
  yielded. `on_end_group_walk` is called after all children of the current
  `SettingGroup` object were visited.
  """
  
  def __init__(self):
    self.on_visit_setting = pgutils.empty_func
    self.on_visit_group = pgutils.empty_func
    self.on_end_group_walk = pgutils.empty_func
