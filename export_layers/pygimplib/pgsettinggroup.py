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
  * persistently - using a JSON file
  * "session-persistently" (settings persist during one GIMP session) - using the GIMP shelf
"""

#===============================================================================

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division

str = unicode

#===============================================================================

import inspect
import errno
import abc
from collections import OrderedDict
import json

import gimpshelf

from . import pgsetting

#===============================================================================


class Container(object):
  
  """
  This class is an ordered, `dict`-like container to store items.
  """
  
  __metaclass__ = abc.ABCMeta
  
  def __init__(self):
    self._items = OrderedDict()
  
  def __getitem__(self, key):
    return self._items[key]
  
  def __contains__(self, key):
    return key in self._items[key]
  
  def __iter__(self):
    """
    Iterate over the objects in the order they were created.
    """
    
    for item in self._items.values():
      yield item
  
  def __len__(self):
    return len(self._items)


#-------------------------------------------------------------------------------


class SettingGroup(Container):
  
  """
  This class:
  * groups related `Setting` objects together,
  * can perform operations on all settings at once.
  """
  
  def __init__(self, setting_list):
    """
    Create settings (Setting objects) from the specified list.
    
    Each list element must contain a dictionary, which contains
    (setting_attribute, value) pairs.
    
    `setting_attribute` is a string that denotes an argument passed when
    instantiating the appropriate Setting class.
    
    The following setting attributes must always be specified:
      * 'type' - type of the Setting object to instantiate.
      * 'name' - setting name.
      * 'default_value' - default value of the setting.
    
    For more attributes, check the documentation of the Setting classes. There
    may also be more mandatory attributes for specific setting types.
    
    Settings are stored in the group in the order they are specified in the list.
    """
    
    super(SettingGroup, self).__init__()
    
    for setting_data in setting_list:
      self._create_setting(setting_data)
  
  def streamline(self, force=False):
    """
    Streamline all Setting objects in this group.
    
    Parameters:
    
    * `force` - If True, streamline settings even if the values of the other
      settings were not changed. This is useful when initializing GUI elements -
      setting up proper values, enabled/disabled state or visibility.
    
    Returns:
    
      `changed_settings` - Set of changed settings. See the `streamline()`
      method in the `Setting` object for more information.
    """
    
    changed_settings = {}
    for setting in self:
      if setting.can_streamline():
        changed = setting.streamline(force=force)
        for setting, changed_attrs in changed.items():
          if setting not in changed_settings:
            changed_settings[setting] = changed_attrs
          else:
            changed_settings[setting].update(changed_attrs)
    
    return changed_settings
  
  def reset(self):
    """
    Reset all settings in this group. Ignore settings whose
    attribute `resettable_by_group` is False.
    """
    
    for setting in self:
      if setting.resettable_by_group:
        setting.reset()
  
  def _create_setting(self, setting_data):
    try:
      setting_type = setting_data['type']
    except KeyError:
      raise TypeError(self._get_missing_mandatory_attributes_message(['type']))
    
    if isinstance(setting_type, pgsetting.SettingTypes):
      setting_type = setting_type.value
    
    del setting_data['type']
    
    try:
      self._items[setting_data['name']] = setting_type(**setting_data)
    except TypeError as e:
      missing_mandatory_arguments = self._get_missing_mandatory_arguments(setting_type, setting_data)
      if missing_mandatory_arguments:
        message = self._get_missing_mandatory_attributes_message(missing_mandatory_arguments)
      else:
        message = e.message
      raise TypeError(message)
  
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


class SettingStream(object):
  
  """
  This class provides an interface for reading and writing settings to
  permanent or semi-permanent sources.
  
  For easier usage, use the `SettingPersistor` class instead.
  
  Attributes:
  
  * `_settings_not_found` - List of settings not found in stream when the `read()`
    method is called.
  """
  
  __metaclass__ = abc.ABCMeta
  
  def __init__(self):
    self._settings_not_found = []
  
  @abc.abstractmethod
  def read(self, settings):
    """
    Read setting values from the stream and assign them to the settings
    specified in the `settings` iterable.
    
    If a setting value from the stream is invalid, the setting will be reset to
    its default value.
    
    Parameters:
    
    * `settings` - Any iterable sequence containing `Setting` objects.
    
    Raises:
    
    * `SettingsNotFoundInStreamError` - At least one of the settings is not
      found in the stream. All settings that were not found in the stream will be
      stored in the `settings_not_found` list. This list is cleared on each read()
      call.
    """
    
    pass
  
  @abc.abstractmethod
  def write(self, settings):
    """
    Write setting values from settings specified in the `settings` iterable
    to the stream.
    
    Parameters:
    
    * `settings` - Any iterable sequence containing `Setting` objects.
    """
    
    pass

  @property
  def settings_not_found(self):
    return self._settings_not_found


class SettingStreamError(Exception):
  pass


class SettingsNotFoundInStreamError(SettingStreamError):
  pass


class SettingStreamFileNotFoundError(SettingStreamError):
  pass


class SettingStreamReadError(SettingStreamError):
  pass


class SettingStreamInvalidFormatError(SettingStreamError):
  pass


class SettingStreamWriteError(SettingStreamError):
  pass


#-------------------------------------------------------------------------------


class GimpShelfSettingStream(SettingStream):
  
  """
  This class reads settings from/writes settings to the GIMP shelf,
  persisting during one GIMP session.
  
  This class stores the setting name and value in the GIMP shelf.
  
  Attributes:
  
  * `shelf_prefix` - Prefix used to distinguish entries in the GIMP shelf
    to avoid overwriting existing entries which belong to different plug-ins.
  """
  
  def __init__(self, shelf_prefix):
    super(GimpShelfSettingStream, self).__init__()
    
    self.shelf_prefix = shelf_prefix
  
  def read(self, settings):
    self._settings_not_found = []
    
    for setting in settings:
      try:
        value = gimpshelf.shelf[(self.shelf_prefix + setting.name).encode()]
      except KeyError:
        self._settings_not_found.append(setting)
      else:
        try:
          setting.set_value(value)
        except pgsetting.SettingValueError:
          setting.reset()
    
    if self._settings_not_found:
      raise SettingsNotFoundInStreamError(
        "The following settings could not be found in any sources: " +
        str([setting.name for setting in self._settings_not_found])
      )
  
  def write(self, settings):
    for setting in settings:
      gimpshelf.shelf[(self.shelf_prefix + setting.name).encode()] = setting.value


class JSONFileSettingStream(SettingStream):
  
  """
  This class reads settings from/writes settings to a JSON file.
  
  This class provides a persistent storage for settings. It stores
  the setting name and value in the file.
  """
  
  def __init__(self, filename):
    super(JSONFileSettingStream, self).__init__()
    
    self.filename = filename
  
  def read(self, settings):
    """
    Raises:
    
    * `SettingsNotFoundInStreamError` - see the `SettingStream` class.
    
    * `SettingStreamFileNotFoundError` - Could not find the specified file.
    
    * `SettingStreamReadError` - Could not read from the specified file (IOError
      or OSError was raised).
    
    * `SettingStreamInvalidFormatError` - Specified file has invalid format, i.e.
      it is not recognized as a valid JSON file.
    """
    
    self._settings_not_found = []
    
    try:
      with open(self.filename, 'r') as json_file:
        settings_from_file = json.load(json_file)
    except (IOError, OSError) as e:
      if e.errno == errno.ENOENT:
        raise SettingStreamFileNotFoundError(
          _("Could not find file with settings \"{0}\".").format(self.filename)
        )
      else:
        raise SettingStreamReadError(
          _("Could not read settings from file \"{0}\". Make sure the file can be "
            "accessed to.").format(self.filename)
        )
    except ValueError as e:
      raise SettingStreamInvalidFormatError(
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
      raise SettingsNotFoundInStreamError(
        "The following settings could not be found in any sources: " +
        str([setting.name for setting in self._settings_not_found])
      )
  
  def write(self, settings):
    """
    Write the name and value of the settings from the `settings` iterable to the
    file.
    
    Raises:
    
    * `SettingStreamWriteError` - Could not write to the specified file (IOError
      or OSError was raised).
    """
    
    settings_dict = self._to_dict(settings)
    
    try:
      with open(self.filename, 'w') as json_file:
        json.dump(settings_dict, json_file)
    except (IOError, OSError):
      raise SettingStreamWriteError(
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
  * serves as a wrapper for `SettingStream` classes
  * reads settings from multiple setting streams
  * write settings to multiple setting streams
  """
  
  __STATUSES = SUCCESS, READ_FAIL, WRITE_FAIL, NOT_ALL_SETTINGS_FOUND = (0, 1, 2, 3)
  
  @classmethod
  def load(cls, settings_or_groups, setting_streams):
    """
    Load setting values from the specified list of setting streams
    (`setting_streams`) to specified list of settings or setting groups
    (`settings_or_groups`).
    
    The order of streams in the `setting_streams` list indicates the preference
    of the streams, beginning with the first stream in the list. If not all
    settings could be found in the first stream, the second stream is read to
    assign values to the remaining settings. This continues until all settings
    are read.
    
    If settings have invalid values, their default values will be assigned.
    
    If some settings could not be found in any of the streams,
    their default values will be assigned.
    
    Parameters:
    
    * `settings_or_groups` - list of `Setting` or `SettingGroup` objects whose
      values are loaded from `setting_streams`.
    
    * `setting_streams` - list of `SettingStream` instances to read from.
    
    Returns:
    
      * `status`:
      
        * `SUCCESS` - Settings successfully loaded. This status is also returned
          if `settings_or_groups` or `setting_streams` is empty.
        
        * `NOT_ALL_SETTINGS_FOUND` - Could not find some settings from
          any of the streams. Default values are assigned to these settings.
        
        * `READ_FAIL` - Could not read data from the first stream where this
          error occurred. May occur for file streams with e.g. denied read
          permission.
      
      * `status_message` - Message describing the returned status in more detail.
    """
    
    if not settings_or_groups or not setting_streams:
      return cls._status(cls.SUCCESS)
    
    settings = cls._list_settings(settings_or_groups)
    
    for stream in setting_streams:
      try:
        stream.read(settings)
      except (SettingsNotFoundInStreamError, SettingStreamFileNotFoundError) as e:
        if type(e) == SettingsNotFoundInStreamError:
          settings = stream.settings_not_found
        
        if stream == setting_streams[-1]:
          return cls._status(cls.NOT_ALL_SETTINGS_FOUND, e.message)
        else:
          continue
      except (SettingStreamReadError, SettingStreamInvalidFormatError) as e:
        return cls._status(cls.READ_FAIL, e.message)
      else:
        break
    
    return cls._status(cls.SUCCESS)
  
  @classmethod
  def save(cls, settings_or_groups, setting_streams):
    """
    Save setting values from specified list of settings or setting groups
    (`settings_or_groups`) to the specified list of setting streams
    (`setting_streams`).
    
    Parameters:
    
    * `settings_or_groups` - list of `Setting` or `SettingGroup` objects whose
      values are saved to `setting_streams`.
    
    * `setting_streams` - list of `SettingStream` instances to write to.
    
    Returns:
    
      * `status`:
      
        * `SUCCESS` - Settings successfully saved. This status is also returned
          if `settings_or_groups` or `setting_streams` is empty.
        
        * `WRITE_FAIL` - Could not write data to the first stream where this
          error occurred. May occur for file streams with e.g. denied write
          permission.
      
      * `status_message` - Message describing the status in more detail.
    """
    
    if not settings_or_groups or not setting_streams:
      return cls._status(cls.SUCCESS)
    
    settings = cls._list_settings(settings_or_groups)
    
    for stream in setting_streams:
      try:
        stream.write(settings)
      except SettingStreamWriteError as e:
        return cls._status(cls.WRITE_FAIL, e.message)
    
    return cls._status(cls.SUCCESS)
  
  @classmethod
  def _status(cls, status, message=None):
    return status, message if message is not None else ""
  
  @classmethod
  def _list_settings(cls, settings_or_groups):
    # Put all settings into one list so that the `read()` and `write()` methods
    # are invoked only once per each stream.
    settings = []
    for setting_or_group in settings_or_groups:
      if isinstance(setting_or_group, pgsetting.Setting):
        settings.append(setting_or_group)
      else:
        settings.extend(setting_or_group)
    return settings


#===============================================================================


class SettingPresenterGroup(Container):
  
  """
  This class groups `SettingPresenter` objects together.
  
  You can access individual `SettingPresenter` objects by the corresponding
  `Setting` objects.
  
  Q: Why can't we access by `Setting.name` (like in `SettingGroup`)?
  A: Because `SettingPresenterGroup` is independent of `SettingGroup`
     and this object may contain settings from multiple `SettingGroup`
     objects with the same name.
  """
  
  __metaclass__ = abc.ABCMeta
  
  _SETTING_ATTRIBUTES_METHODS = {
    'value' : 'set_value', 
    'ui_enabled' : 'set_enabled',
    'ui_visible' : 'set_visible'
  }
  
  def __init__(self):
    super(SettingPresenterGroup, self).__init__()
    
    self._is_events_connected = False
  
  def add(self, setting_presenter):
    """
    Add a `SettingPresenter` object to the group.
    """
    
    self._items[setting_presenter.setting] = setting_presenter
  
  def assign_setting_values_to_elements(self):
    """
    Assign values from settings to GUI elements.
    
    Streamline all setting values along the way.
    
    This method is useful when it is desired to assign correct values to the GUI
    elements when initializing or resetting the GUI.
    """
    
    for presenter in self:
      presenter.set_value(presenter.setting.value)
    
    changed_settings = self._streamline(force=True)
    self._apply_changed_settings(changed_settings)
  
  def assign_element_values_to_settings(self):
    """
    Assign values from GUI elements to settings.
    
    If `connect_value_changed_events()` was called, don't streamline. Otherwise
    do.
    
    Raises:
    
    * `SettingValueError` - Value assigned to one or more settings is invalid.
      If there are multiple settings that raise `SettingValueError` upon value
      assignment, the exception message contains messages from all these
      settings. In such case, settings are not streamlined.
    """
    
    exception_message = ""
    
    for presenter in self:
      try:
        presenter.setting.set_value(presenter.get_value())
      except pgsetting.SettingValueError as e:
        if not exception_message:
          exception_message += e.message + '\n'
    
    if self._is_events_connected:
      # Settings are continuously streamlined. Since this method changes the
      # `value` attribute, clear `changed_attributes` to prevent future
      # `streamline()` calls from changing settings unnecessarily.
      for presenter in self:
        presenter.setting.changed_attributes.clear()
    else:
      if not exception_message:
        self._streamline()
    
    if exception_message:
      exception_message = exception_message.rstrip('\n')
      raise pgsetting.SettingValueError(exception_message)
  
  def connect_value_changed_events(self):
    """
    Assign event handlers to GUI elements triggered whenever their value is
    changed.
    
    For settings with streamline function assigned, use a different event
    handler that also streamlines the settings.
    """
    
    for presenter in self:
      if presenter.value_changed_signal is not None:
        if not presenter.setting.can_streamline():
          presenter.connect_event(self._gui_on_element_value_change, presenter)
        else:
          presenter.connect_event(self._gui_on_element_value_change_streamline,
                                  presenter)
    
    self._is_events_connected = True
  
  @abc.abstractmethod
  def _gui_on_element_value_change(self, *args):
    """
    Override this method in a subclass to call `_on_element_value_change()`.
    
    Since event handling is dependent on the GUI framework used, a method
    separate from `_on_element_value_change()` has to be defined so that the GUI
    framework invokes the event with the correct arguments in the correct order.
    """
    
    pass
  
  @abc.abstractmethod
  def _gui_on_element_value_change_streamline(self, *args):
    """
    Override this method in a subclass to call
    `_on_element_value_change_streamline()`.
    
    Since event handling is dependent on the GUI framework used, a method
    separate from `_gui_on_element_value_change_streamline()` has to be defined
    so that the GUI framework invokes the event with the correct arguments in
    the correct order.
    """
    
    pass
  
  def _on_element_value_change(self, presenter):
    """
    Assign value from the GUI element to the setting when the user changed the
    value of the GUI element.
    """
    
    presenter.setting.set_value(presenter.get_value())
  
  def _on_element_value_change_streamline(self, presenter):
    """
    Assign value from the GUI element to the setting when the user changed the
    value of the GUI element.
    
    Streamline the setting and change other affected GUI elements if necessary.
    """
    
    presenter.setting.set_value(presenter.get_value())
    changed_settings = presenter.setting.streamline()
    self._apply_changed_settings(changed_settings)
  
  def set_tooltips(self):
    """
    Set tooltips for all GUI elements.
    """
    
    for presenter in self:
      presenter.set_tooltip()
  
  def _streamline(self, force=False):
    """
    Streamline all `Setting` objects in this group.
    
    See the description for the `streamline()` method in the `SettingGroup`
    class for further information.
    """
    
    changed_settings = {}
    for presenter in self:
      setting = presenter.setting
      if setting.can_streamline():
        changed = setting.streamline(force=force)
        for setting, changed_attrs in changed.items():
          if setting not in changed_settings:
            changed_settings[setting] = changed_attrs
          else:
            changed_settings[setting].update(changed_attrs)
    
    return changed_settings
  
  def _apply_changed_settings(self, changed_settings):
    """
    After `streamline()` is called on a `Setting` or `SettingGroup` object,
    apply changed attributes of settings to their associated GUI elements.
    
    Parameters:
    
    * `changed_settings` - Set of changed attributes of settings to apply to the
      GUI elements.
    """
    
    for setting, changed_attributes in changed_settings.items():
      presenter = self[setting]
      for attr in changed_attributes:
        setting_attr = getattr(setting, attr)
        presenter_method = getattr(presenter, self._SETTING_ATTRIBUTES_METHODS[attr])
        presenter_method(setting_attr)


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

