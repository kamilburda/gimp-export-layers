#-------------------------------------------------------------------------------
#
# This file is part of pygimplib.
#
# Copyright (C) 2014, 2015 khalim19 <khalim19@gmail.com>
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
* defines a class to group settings together for easier creation and management
  of settings
* defines a class to format settings as GIMP PDB parameters
"""

#===============================================================================

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division

str = unicode

#===============================================================================

import inspect
from collections import OrderedDict

from . import pgsetting

#===============================================================================


class SettingGroup(object):
  
  """
  This class
  * allows to create a group of related settings (`Setting` objects),
  * allows to store existing setting groups,
  * can perform certain operations on all settings and nested groups at once.
  """
  
  def __init__(self, name, setting_list):
    """
    Create settings (`Setting` objects) from the specified list. The list can
    also contain existing setting groups (`SettingGroup` objects).
    
    Settings and nested groups are stored in the group in the order they are
    specified in the list.
    
    Parameters:
    
    * `name` - A name (string) that uniquely identifies the setting group.
    
    * `setting_list` - See below.
    
    ---------
    
    To add a setting, use a dictionary containing (attribute name, value) pairs.
    
    "attribute name" is a string that represents an argument passed when
    instantiating the appropriate `Setting` class.
    
    The following setting attributes must always be specified:
      * 'type' - type of the Setting object to instantiate.
      * 'name' - setting name.
      * 'default_value' - default value of the setting.
    
    For more attributes, check the documentation of the `Setting` classes. There
    may also be more mandatory attributes for specific setting types.
    
    ---------
    
    To add a setting group, simply pass an existing `SettingGroup` object).
    
    ---------
    
    Unless otherwise stated, "settings" in the rest of the documentation for
    this class refers to both `Setting` and `SettingGroup` objects.
    """
    
    self._name = name
    self._settings = OrderedDict()
    
    self.add(setting_list)
    
    self._ignored_settings_and_tags = {}
    
    # Used in the `_next()` method
    self._settings_iterator = None
  
  @property
  def name(self):
    return self._name
  
  def __getitem__(self, setting_name):
    """
    Access the setting or group by its name (string).
    """
    
    return self._settings[setting_name]
  
  def __contains__(self, setting_name):
    return setting_name in self._settings
  
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
      return (setting_or_group.name in ignored_settings_and_tags and
              any(tag in ignored_settings_and_tags[setting_or_group.name] for tag in ignore_tags))
    
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
        ignored_settings_and_tags = groups[0]._ignored_settings_and_tags
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
      if self._is_setting_group(setting_or_group):
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
        raise KeyError("setting \"{0}\" not found".format(setting_name))
  
  def set_ignore_tags(self, ignored_settings_and_tags):
    """
    For the specified settings, specify a list of "ignore tags".
    
    When the `iterate_all()` method is called and the `ignore_tags` parameter is
    specified, all settings matching at least one tag from `ignore_tags` will be
    excluded from the iteration.
    
    When the tags match the method names in this class that operate on all
    settings, such as `reset()` or `apply_gui_values_to_settings()`, the methods ignore
    those settings.
    
    Parameters:
    
    * `ignored_settings_and_tags` - A dict of (setting name, tag list) pairs.
    """
    
    self._ignored_settings_and_tags = {
      setting_name: set(tags) for setting_name, tags in ignored_settings_and_tags.items() }
  
  def reset(self):
    """
    Reset all settings in this group. Ignore settings with the `reset` ignore
    tag.
    """
    
    for setting in self.iterate_all(ignore_tags=['reset']):
      setting.reset()
  
  def initialize_gui(self, custom_gui=None):
    """
    Initialize GUI for all settings.
    
    Settings that are not provided with a readily available GUI can have their
    GUI initialized using the `custom_gui` dict. `custom_gui` contains
    (setting name, [GUI type, GUI element instance, enable GUI update?]) pairs.
    The "enable GUI update?" boolean in the list is optional and defaults to
    True. For more information about parameters in the list, see the
    `Setting.create_gui` method.
    
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
        setting.create_gui()
      else:
        create_gui_params = custom_gui[setting.name]
        setting.create_gui(*create_gui_params)
  
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
    
    exception_message = ""
    
    for setting in self.iterate_all(ignore_tags=['apply_gui_values_to_settings']):
      try:
        setting.gui.update_setting_value()
      except pgsetting.SettingValueError as e:
        if not exception_message:
          exception_message += e.message + "\n"
    
    if exception_message:
      exception_message = exception_message.rstrip("\n")
      raise pgsetting.SettingValueError(exception_message)
  
  def _next(self):
    """
    Return the next element when iterating the settings. Used by `iterate_all()`.
    """
    
    # Initialize the iterator
    if self._settings_iterator is None:
      self._settings_iterator = self._settings.itervalues()
    
    try:
      next_element = self._settings_iterator.next()
    except StopIteration:
      self._settings_iterator = None
      raise StopIteration
    else:
      return next_element
  
  def _is_setting_group(self, setting_or_group):
    return isinstance(setting_or_group, SettingGroup)
  
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
    
    if setting_data['name'] in self._settings:
      raise KeyError("setting \"{0}\" already exists".format(setting_data['name']))
    
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
      raise KeyError("setting group \"{0}\" already exists".format(setting_group.name))
    
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


#===============================================================================


class PdbParamCreator(object):
  
  """
  This class creates GIMP PDB (procedural database) parameters for plug-ins
  (plug-in procedures) from `Setting` objects.
  """
  
  @classmethod
  def create_params(cls, *settings_or_groups):
    """
    Return a list of GIMP PDB parameters from the specified `Setting` or
    `SettingGroup` objects.
    """
    
    settings = cls._list_settings(settings_or_groups)
    return [cls._create_param(setting) for setting in settings
            if setting.can_be_registered_to_pdb()]
  
  @classmethod
  def list_param_values(cls, settings_or_groups, ignore_run_mode=True):
    """
    Return a list of values of settings registrable to PDB.
    
    If `ignore_run_mode` is True, ignore setting(s) named 'run_mode'. This makes
    it possible to call PDB functions with the setting values without manually
    omitting the 'run_mode' setting.
    """
    
    settings = cls._list_settings(settings_or_groups)
    
    if ignore_run_mode:
      for i, setting in enumerate(settings):
        if setting.name == 'run_mode':
          del settings[i]
          break
    
    return [setting.value for setting in settings
            if setting.can_be_registered_to_pdb()]
  
  @classmethod
  def _list_settings(cls, settings_or_groups):
    settings = []
    for setting_or_group in settings_or_groups:
      if isinstance(setting_or_group, pgsetting.Setting):
        settings.append(setting_or_group)
      elif isinstance(setting_or_group, SettingGroup):
        settings.extend(setting_or_group.iterate_all())
      else:
        raise TypeError("not a Setting or a SettingGroup object")
    
    return settings
  
  @classmethod
  def _create_param(cls, setting):
    return (setting.pdb_type, setting.name.encode(), setting.description.encode())
