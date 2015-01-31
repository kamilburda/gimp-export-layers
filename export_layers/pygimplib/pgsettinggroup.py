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
* defines a class to group settings together for easier management
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
  
  def __init__(self, setting_list):
    """
    Create settings (`Setting` objects) from the specified list. The list can
    also contain existing setting groups (`SettingGroup` objects).
    
    Settings and nested groups are stored in the group in the order they are
    specified in the list.
    
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
    
    To add a setting group, use a two-element tuple (group name, `SettingGroup`
    object). "group name" is an arbitrary string that uniquely identifies the
    group within the parent group.
    
    ---------
    
    Unless otherwise stated, "settings" in the rest of the documentation for
    this class refers to both `Setting` and `SettingGroup` objects.
    """
    
    self._settings = OrderedDict()
    
    self.add(setting_list)
  
  def __getitem__(self, setting_name):
    return self._settings[setting_name]
  
  def __contains__(self, setting_name):
    return setting_name in self._settings
  
  def __iter__(self):
    """
    Iterate over the settings in the order they were created.
    """
    
    for setting in self._settings.values():
      yield setting
  
  def __len__(self):
    return len(self._settings)
  
  def add(self, setting_list):
    """
    Add settings to the group. For details about the format of `setting_list`,
    refer to the documentation for the `__init__()` method.
    """
    
    for element in setting_list:
      if self._is_setting_group(element):
        self._add_setting_group(element)
      else:
        self._create_setting(element)
  
  def remove(self, setting_names):
    for setting_name in setting_names:
      if setting_name in self._settings:
        del self._settings[setting_name]
      else:
        raise KeyError("setting '{0}' not found".format(setting_name))
  
  def reset(self):
    """
    Reset all settings in this group. Ignore settings whose attribute
    `resettable_by_group` is False.
    """
    
    for setting in self:
      if setting.resettable_by_group:
        setting.reset()
  
  def set_gui_tooltips(self):
    for setting in self:
      setting.gui.set_tooltip()
  
  def update_setting_values(self):
    """
    Manually assign the GUI element values, entered by the user, to the setting
    values.
    
    This method will not have any effect on settings with automatic
    GUI-to-setting value updating.
    
    Raises:
    
    * `SettingValueError` - One or more values are invalid. The exception
    message contains messages from all invalid settings.
    """
    
    exception_message = ""
    
    for setting in self:
      try:
        setting.gui.update_setting_value()
      except pgsetting.SettingValueError as e:
        if not exception_message:
          exception_message += e.message + '\n'
    
    if exception_message:
      exception_message = exception_message.rstrip('\n')
      raise pgsetting.SettingValueError(exception_message)
  
  def _is_setting_group(self, element):
    return not isinstance(element, dict) and len(element) == 2 and isinstance(element[1], SettingGroup)
  
  def _create_setting(self, setting_data):
    try:
      setting_type = setting_data['type']
    except KeyError:
      raise TypeError(self._get_missing_mandatory_attributes_message(['type']))
    
    if isinstance(setting_type, pgsetting.SettingTypes):
      setting_type = setting_type.value
    
    del setting_data['type']
    
    try:
      setting_data['name']
    except KeyError:
      raise TypeError(self._get_missing_mandatory_attributes_message(['name']))
    
    if setting_data['name'] in self._settings:
      raise KeyError("setting '{0}' already exists".format(setting_data['name']))
    
    try:
      self._settings[setting_data['name']] = setting_type(**setting_data)
    except TypeError as e:
      missing_mandatory_arguments = self._get_missing_mandatory_arguments(setting_type, setting_data)
      if missing_mandatory_arguments:
        message = self._get_missing_mandatory_attributes_message(missing_mandatory_arguments)
      else:
        message = e.message
      raise TypeError(message)
  
  def _add_setting_group(self, setting_group_data):
    if setting_group_data[0] in self._settings:
      raise KeyError("setting group '{0}' already exists".format(setting_group_data[0]))
    
    self._settings[setting_group_data[0]] = setting_group_data[1]
  
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
    
    settings = []
    for setting_or_group in settings_or_groups:
      if isinstance(setting_or_group, pgsetting.Setting):
        settings.append(setting_or_group)
      elif isinstance(setting_or_group, SettingGroup):
        settings.extend(setting_or_group)
      else:
        raise TypeError("not a Setting or a SettingGroup object")
    
    return [cls._create_param(setting) for setting in settings
            if setting.pdb_registration_mode == pgsetting.PdbRegistrationModes.registrable]
  
  @classmethod
  def _create_param(cls, setting):
    return (setting.pdb_type, setting.name.encode(), setting.short_description.encode())
