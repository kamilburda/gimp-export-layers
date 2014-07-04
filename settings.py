#-------------------------------------------------------------------------------
#
# This file is part of libgimpplugin.
#
# Copyright (C) 2014 khalim19 <khalim19@gmail.com>
# 
# libgimpplugin is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# libgimpplugin is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with libgimpplugin.  If not, see <http://www.gnu.org/licenses/>.
#
#-------------------------------------------------------------------------------

"""
This module:
* defines API for settings
* defines the means to load/save settings:
  * permanently - to a JSON file
    - settings persist even after closing GIMP
  * semi-permanently - to the GIMP shelf
    - settings persist during one GIMP session
"""

#=============================================================================== 

import errno
import abc
from collections import OrderedDict
import json

import gimp
from gimpshelf import shelf
import gimpenums

import container

#===============================================================================

pdb = gimp.pdb

#===============================================================================

class Setting(object):
  
  """
  Attributes:
  
  * name (read-only): Setting name to uniquely identify a setting.
  
  * default_value: Default value of a setting when the setting is instantiated
    or when the reset() method was called.
  
  * value: The setting value. Subclasses of Setting can override the value.setter
    property to e.g. validate input value and raise ValueError if the value assigned is invalid.
  
  * gimp_pdb_type: GIMP Procedural Database (PDB) type, used when registering
    parameters in plug-ins. `_allowed_pdb_types` list, which is class-specific, determines
    whether the PDB type assigned is valid. `_allowed_pdb_types` in this class is None,
    which means that any PDB type can be assigned.
  
  * can_be_registered_to_pdb: Indicates whether a setting can be registered
    as a parameter to a plug-in. Automatically set to True if gimp_pdb_type is
    assigned to a valid value that is not None.
  
  * display_name: Setting name in human-readable format. Useful as GUI labels.
  
  * short_description (read-only): Usually `display_name` plus additional information
    in parentheses. Useful as setting description when registering parameters in plug-ins.
  
  * description: Describes a setting in more detail. Useful for documentation
    purposes as well as GUI tooltips.
  
  * error_messages: A dict of error messages, which can be used e.g. when a value
    assigned to a setting is invalid. You can add your own error messages and
    assign them to one of the "default" error messages (such as 'invalid_value'
    in ImageSetting) depending on the context in which the value assigned is invalid.
  
  * ui_enabled: Indicates whether a setting should be enabled (respond to user input)
    in the GUI. True by default.
  
  * ui_visible: Indicates whether a setting should be visible in the GUI. True by default.
  
  * can_be_reset_by_container: If True, setting is reset to its default value if
    the reset() method from the corresponding SettingContainer is called. False by default.
    
  * changed_attributes (read-only): Contains a set of Setting attribute names that were changed.
    Currently, it can contain the following attribute names: `value`, `ui_enabled` or `ui_visible`.
    Assigning to any of the attributes causes the corresponding attribute name
    to be added to the set. `changed_attributes` is cleared if streamline() is called.
  """
  
  def __init__(self, name, default_value):
    
    self._attrs_that_trigger_change = { 'value', 'ui_enabled', 'ui_visible' }
    self._changed_attributes = set()
    
    self._name = name
    self.default_value = default_value
    
    self._value = self.default_value
    
    self._gimp_pdb_type = None
    self._can_be_registered_to_pdb = False
    self._allowed_pdb_types = None
    
    self._display_name = ""
    self._description = ""
    
    self._error_messages = {}
    
    self.ui_enabled = True
    self.ui_visible = True
    
    self.can_be_reset_by_container = True
    
    self._streamline_func = None
    self._streamline_args = []
    
    # Some attributes may now be in _changed_attributes because of __setattr__,
    # hence it must be cleared.
    self._changed_attributes.clear()
  
  def __setattr__(self, name, value):
    super(Setting, self).__setattr__(name, value)
    if name in self._attrs_that_trigger_change:
      self._changed_attributes.add(name)
  
  @property
  def name(self):
    return self._name
  
  @property
  def value(self):
    return self._value
  @value.setter
  def value(self, value_):
    self._set_value(value_)
  
  def _set_value(self, value_):
    self._value = value_
  
  @property
  def gimp_pdb_type(self):
    return self._gimp_pdb_type
  @gimp_pdb_type.setter
  def gimp_pdb_type(self, value):
    if self._allowed_pdb_types is None or value in self._allowed_pdb_types:
      self._gimp_pdb_type = value
      self.can_be_registered_to_pdb = value is not None
    else:
      raise ValueError("GIMP PDB type " + str(value) + " not allowed")
  
  @property
  def can_be_registered_to_pdb(self):
    return self._can_be_registered_to_pdb
  @can_be_registered_to_pdb.setter
  def can_be_registered_to_pdb(self, value):
    if value and self._gimp_pdb_type is None:
      raise ValueError("setting cannot be registered to PDB because it has no PDB type set (attribute gimp_pdb_type)")
    self._can_be_registered_to_pdb = value
  
  @property
  def display_name(self):
    return self._display_name
  @display_name.setter
  def display_name(self, value):
    self._display_name = value if value is not None else ""
  
  @property
  def description(self):
    return self._description
  @description.setter
  def description(self, value):
    self._description = value if value is not None else ""
  
  @property
  def changed_attributes(self):
    return self._changed_attributes
  
  @property
  def short_description(self):
    return self.display_name
  
  @property
  def error_messages(self):
    return self._error_messages
  
  def reset(self):
    """
    Set the setting value to its default value.
    
    This is different from
      setting.value = setting.default_value
    in that this method does not raise an exception if the default value is invalid.
    """
    self._value = self.default_value
  
  def streamline(self, force=False):
    """
    Adjust attributes of this setting based on the attributes of other settings or arguments.
    Return a list of changed settings. A setting is considered changed if at least one of the
    following attributes were assigned a value:
    * `value`
    * `ui_enabled`
    * `ui_visible`
    
    If force is True, streamline settings even if the values of the other
    settings were not changed. This is useful when initializing GUI elements -
    setting up proper values, enabled/disabled state or visibility.
    """
    
    if self._streamline_func is None:
      raise TypeError("streamline() cannot be called because there is no streamline function set")
    
    changed_settings = OrderedDict()
    
    if self._changed_attributes or force:
      self._streamline_func(self, *self._streamline_args)
      
      # Create copies of the changed attributes since the sets are cleared
      # in the objects afterwards.
      changed_settings[self] = set(self._changed_attributes)
      self._changed_attributes.clear()
      
      for arg in self._streamline_args:
        if isinstance(arg, Setting) and arg.changed_attributes:
          changed_settings[arg] = set(arg.changed_attributes)
          arg.changed_attributes.clear()
    
    return changed_settings
  
  def set_streamline_func(self, streamline_func, *streamline_args):
    """
    Set a function to be called by the streamline() method.
    
    streamline_args are additional arguments to the streamline function.
    
    A streamline function must always contain at least one argument. The first
    argument is the setting from which the streamline function is invoked.
    This argument should not be specified in streamline_args.
    """
    
    if not callable(streamline_func):
      raise TypeError("not a function")
    
    self._streamline_func = streamline_func
    self._streamline_args = streamline_args
  
  def remove_streamline_func(self):
    if self._streamline_func is None:
      raise TypeError("no streamline function was previously set")
    
    self._streamline_func = None
    self._streamline_args = []
  
  def can_streamline(self):
    return self._streamline_func is not None


class NumericSetting(Setting):
  
  """
  Additional attributes:
  
  * min_value: Minimum numeric value. If not None and the value assigned is less
    than min_value, ValueError is raised.
    
  * max_value: Maximum numeric value. If not None and the value assigned is greater
    than max_value, ValueError is raised.
  
  
  Error messages:
  
  * below_min: Used if a value assigned is less than min_value.
  
  * above_max: Used if a value assigned is greater than min_value.
  """
  
  __metaclass__ = abc.ABCMeta
  
  def __init__(self, name, default_value):
    super(NumericSetting, self).__init__(name, default_value)
    
    self.min_value = None
    self.max_value = None
    
    self.error_messages['below_min'] = "value cannot be less than the minimum value " + str(self.min_value)
    self.error_messages['above_max'] = "value cannot be greater than the maximum value " + str(self.max_value)
  
  @property
  def value(self):
    return self._value

  @value.setter
  def value(self, val):
    if self.min_value is not None and val < self.min_value:
      raise ValueError(self.error_messages['below_min'])
    if self.max_value is not None and val > self.max_value:
      raise ValueError(self.error_messages['above_max'])
    
    super(NumericSetting, self)._set_value(val)


class IntSetting(NumericSetting):
  
  def __init__(self, name, default_value):
    super(IntSetting, self).__init__(name, default_value)
    
    self._allowed_pdb_types = [gimpenums.PDB_INT8, gimpenums.PDB_INT16, gimpenums.PDB_INT32]
    self.gimp_pdb_type = gimpenums.PDB_INT32


# Use BoolSetting to indicate that a setting is a boolean.
# No need for a separate subclass, since the functionality is the same as IntSetting.
BoolSetting = IntSetting


class FloatSetting(NumericSetting):
  
  def __init__(self, name, default_value):
    super(FloatSetting, self).__init__(name, default_value)
    
    self._allowed_pdb_types = [gimpenums.PDB_FLOAT]
    self.gimp_pdb_type = gimpenums.PDB_FLOAT


class EnumSetting(Setting):
  
  """
  This class can be used for settings with a limited number of values.
  
  Additional attributes:
  
  * options (read-only): A dict of <option name, option value> pairs. Option name
    uniquely identifies each option. Option value is the corresponding integer value.
  
  * options_display_names (read-only): A dict of <option name, option display name> pairs.
    Option display names can be used e.g. as combo box items in the GUI.
  
  To access an option value:
    setting.options[option name]
  
  To access an option display name:
    setting.options_display_names[option name]
  
  
  Error messages:
  
  * invalid_value: Used if a value assigned is invalid.
  
  * invalid_default_value: Option name is invalid (not found in the `options` parameter).
  
  * wrong_options_len: Wrong number of elements in tuples in the `options` parameter.
  
  * duplicate_option_value: Some option values in the 3-element tuples were specified multiple times.
  """
  
  def __init__(self, name, default_value, options):
    
    """
    Parameters:
    
    * name: Setting name.
    
    * default_value: Option name (identifier). Unlike other Setting classes, where
      the value is specified directly, EnumSetting accepts a valid option
      identifier instead.
    
    * options: A list of either (option name, option display name) tuples
      or (option name, option display name, option value) tuples.
      For 2-element tuples, option values are assigned automatically, starting with 0.
      Use 3-element tuples to assign explicit option values. Values must be unique
      and specified in each tuple.
    """
    
    super(EnumSetting, self).__init__(name, default_value)
    
    self._allowed_pdb_types = [gimpenums.PDB_INT8, gimpenums.PDB_INT16, gimpenums.PDB_INT32]
    self.gimp_pdb_type = gimpenums.PDB_INT32
    
    self._options = OrderedDict()
    self._options_display_names = OrderedDict()
    self._option_values = set()
    
    self.error_messages['wrong_options_len'] = "Wrong number of tuple elements in options - must be 2 or 3"
    self.error_messages['duplicate_option_value'] = ("Cannot set the same value for multiple options "
                                                     "- they must be unique")
    
    if len(options[0]) == 2:
      for i, (option_name, option_display_name) in enumerate(options):
        self._options[option_name] = i
        self._options_display_names[option_name] = option_display_name
        self._option_values.add(i)
    elif len(options[0]) == 3:
      for option_name, option_display_name, option_value in options:
        if option_value in self._option_values:
          raise ValueError(self.error_messages['duplicate_option_value'])
        
        self._options[option_name] = option_value
        self._options_display_names[option_name] = option_display_name
        self._option_values.add(option_value)
    else:
      raise ValueError(self.error_messages['wrong_options_len'])
    
    self.error_messages['invalid_value'] = "invalid option value; valid values: " + str(list(self._option_values))
    self.error_messages['invalid_default_value'] = ("invalid identifier for the default value; "
                                                    "must be one of " + str(self._options.keys()))
    
    if default_value in self._options:
      self.default_value = self._options[default_value]
      self._value = self.default_value
    else:
      raise ValueError(self.error_messages['invalid_default_value'])
    
    self._options_str = self._stringify_options()
  
  @property
  def value(self):
    return self._value
  @value.setter
  def value(self, value_):
    if value_ not in self._option_values:
      raise ValueError(self.error_messages['invalid_value'])
    
    super(EnumSetting, self)._set_value(value_)
  
  @property
  def short_description(self):
    return self.display_name + " " + self._options_str
  
  @property
  def options(self):
    return self._options
  
  @property
  def options_display_names(self):
    return self._options_display_names
  
  def get_option_display_names_and_values(self):
    display_names_and_values = []
    for option_name, option_value in zip(self._options_display_names.values(), self._options.values()):
      display_names_and_values.extend((option_name, option_value))
    return display_names_and_values
  
  def _stringify_options(self):
    options_str = ""
    options_sep = ", "
    
    for value, display_name in zip(self._options.values(), self._options_display_names.values()):
      options_str += '{0} ({1})'.format(display_name, str(value)) + options_sep
    options_str = options_str[:-len(options_sep)]
    
    return "{ " + options_str + " }"


class ImageSetting(Setting):
  
  """
  Error messages:
  
  * invalid_value: Used if a value assigned is invalid.
  """
  
  def __init__(self, name, default_value):
    super(ImageSetting, self).__init__(name, default_value)
    
    self._allowed_pdb_types = [gimpenums.PDB_IMAGE]
    self.gimp_pdb_type = gimpenums.PDB_IMAGE
    
    self.error_messages['invalid_value'] = "invalid image"
  
  @property
  def value(self):
    return self._value
  
  @value.setter
  def value(self, image):
    if not pdb.gimp_image_is_valid(image):
      raise ValueError(self.error_messages['invalid_value'])
    
    super(ImageSetting, self)._set_value(image)


class DrawableSetting(Setting):
  
  """
  Error messages:
  
  * invalid_value: Used if a value assigned is invalid.
  """
  
  def __init__(self, name, default_value):
    super(DrawableSetting, self).__init__(name, default_value)
    
    self._allowed_pdb_types = [gimpenums.PDB_DRAWABLE]
    self.gimp_pdb_type = gimpenums.PDB_DRAWABLE
    
    self.error_messages['invalid_value'] = "invalid drawable"
  
  @property
  def value(self):
    return self._value
  
  @value.setter
  def value(self, drawable):
    if not pdb.gimp_item_is_valid(drawable):
      raise ValueError(self.error_messages['invalid_value'])
    
    super(DrawableSetting, self)._set_value(drawable)


class StringSetting(Setting):
  
  def __init__(self, name, default_value):
    super(StringSetting, self).__init__(name, default_value)
    
    self._allowed_pdb_types = [gimpenums.PDB_STRING]
    self.gimp_pdb_type = gimpenums.PDB_STRING


class NonEmptyStringSetting(StringSetting):
  
  """
  Error messages:
  
  * invalid_value: Used if a value assigned is invalid.
  """
  
  def __init__(self, name, default_value):
    super(NonEmptyStringSetting, self).__init__(name, default_value)
    
    self.error_messages['invalid_value'] = "string is empty or not specified"
  
  @property
  def value(self):
    return self._value
  
  @value.setter
  def value(self, value_):
    if value_ is None or not value_:
      raise ValueError(self.error_messages['invalid_value'])
    
    super(NonEmptyStringSetting, self)._set_value(value_)
  
#===============================================================================

class SettingContainer(container.Container):
  """
  This class:
  * groups Setting objects together
  * can perform operations on all settings at once, such as streamline() or reset()
  """
  
  __metaclass__ = abc.ABCMeta
  
  def __init__(self):
    super(SettingContainer, self).__init__()
    
    self._create_settings()
  
  @abc.abstractmethod
  def _create_settings(self):
    """
    Override this method in subclasses to create settings.
    
    To create a setting, instantiate a Setting object and then call the _add() method.
    
    To adjust setting attributes (after creating the setting):
      self[<setting name>].<attribute> = <value>
    
    Q: Why can't we simply do
         self[<setting name>] = Setting(<setting name>, args...)
       to create settings?
    A: Because it's error-prone. <setting name>, which must be the same in both places,
       would have to be typed twice. If, by accident, they were different strings,
       things could get messy...
    """
    pass
    
  def _add(self, setting):
    self._items[setting.name] = setting
  
  def __setitem__(self, key, value):
    raise TypeError("replacing a Setting object or creating a new one is not allowed")
  
  def __delitem__(self, key):
    raise TypeError("deleting a Setting object is not allowed")
  
  def streamline(self, force=False):
    """
    Streamline all Setting objects in this container.
    
    If force is True, streamline settings even if the values of the other
    settings were not changed. This is useful e.g. for setting proper values and
    enabled state when initializing GUI elements.
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
    Reset settings to their default values.
    
    Ignore settings whose attribute `can_be_reset_by_container` is False.
    """
    for setting in self:
      if setting.can_be_reset_by_container:
        setting.reset()
  
#===============================================================================

class SettingStream(object):
  
  """
  This class provides an interface for reading and writing settings to
  permanent or semi-permanent sources.
  
  For easier usage, use the SettingPersistor class instead.
  """
  
  __metaclass__ = abc.ABCMeta
  
  def __init__(self):
    self._settings_not_found = []
  
  @abc.abstractmethod
  def read(self, settings):
    """
    Read setting values from the stream and write the values to the settings
    specified in the `settings` iterable.
    
    If any of the specified settings is not found in the stream,
    SettingsNotFoundInStreamError will be raised.
    
    All settings that were not found in the stream will be stored in the
    `settings_not_found` list. This list is cleared on each read() call.
    
    If a setting value from the stream is invalid,
    the setting will be reset to its default value.
    """
    pass
  
  @abc.abstractmethod
  def write(self, settings):
    """
    Write setting values from settings specified in the `settings` iterable into the stream.
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
  This setting stream reads settings from/writes settings to the GIMP shelf,
  persisting during one GIMP session.
  """
  
  def __init__(self, shelf_prefix):
    super(GimpShelfSettingStream, self).__init__()
    
    self.shelf_prefix = shelf_prefix
  
  def read(self, settings):
    self._settings_not_found = []
    
    for setting in settings:
      try:
        value = shelf[self.shelf_prefix + setting.name]
      except KeyError:
        self._settings_not_found.append(setting)
      else:
        try:
          setting.value = value
        except ValueError:
          setting.reset()
    
    if self._settings_not_found:
      raise SettingsNotFoundInStreamError("The following settings could not be found in any sources: " +
                                          str([setting.name for setting in self._settings_not_found]))
  
  def write(self, settings):
    for setting in settings:
      shelf[self.shelf_prefix + setting.name] = setting.value


class JSONFileSettingStream(SettingStream):
  
  """
  This setting stream reads setting values from/writes settings to a JSON file.
  """
  
  def __init__(self, filename):
    super(JSONFileSettingStream, self).__init__()
    
    self.filename = filename
  
  def read(self, settings):
    self._settings_not_found = []
    
    try:
      with open(self.filename, 'r') as json_file:
        settings_from_file = json.load(json_file)
    except (IOError, OSError) as e:
      if e.errno == errno.ENOENT:
        raise SettingStreamFileNotFoundError("Could not find file with settings \"" + self.filename + "\".")
      else:
        raise SettingStreamReadError(("Could not read settings from file \"" + self.filename + "\". "
                                      "Make sure the file can be accessed to."))
    except ValueError as e:
      raise SettingStreamInvalidFormatError(("File with settings \"" + self.filename + "\" is corrupt. "
                                             "This could happen if the file was edited manually.\n"
                                             "To fix this, save the settings again (to overwrite the file) "
                                             "or delete the file."))
    
    for setting in settings:
      try:
        value = settings_from_file[setting.name]
      except KeyError:
        self._settings_not_found.append(setting)
      else:
        try:
          setting.value = value
        except ValueError:
          setting.reset()
    
    if self._settings_not_found:
      raise SettingsNotFoundInStreamError("The following settings could not be found in any sources: " +
                                          str([setting.name for setting in self._settings_not_found]))
  
  def write(self, settings):
    settings_dict = self._to_dict(settings)
    
    try:
      with open(self.filename, 'w') as json_file:
        json.dump(settings_dict, json_file)
    except (IOError, OSError):
      raise SettingStreamWriteError("Could not write settings to file \"" + self.filename + "\". "
                                    "Make sure the file can be accessed to.")
  
  def _to_dict(self, settings):
    settings_dict = OrderedDict()
    for setting in settings:
      settings_dict[setting.name] = setting.value
    
    return settings_dict

#===============================================================================

class SettingPersistor(object):
  
  """
  This class:
  * serves as a wrapper for SettingStream classes to read from or
    write to multiple settings streams (SettingStream instances) at once,
  * reads from/writes to multiple setting containers or iterables.
  
  Attributes:
  
  * status_message (read-only): Status message describing status returned from
    load() or save() methods in more detail.
  """
  
  _STATUSES = SUCCESS, READ_FAIL, WRITE_FAIL, NOT_ALL_SETTINGS_FOUND = (0, 1, 2, 3)
  
  def __init__(self, read_setting_streams, write_setting_streams):
    self.read_setting_streams = read_setting_streams
    self.write_setting_streams = write_setting_streams
    
    self._status_message = ""
  
  @property
  def status_message(self):
    return self._status_message
  
  def load(self, *setting_containers):
    """
    Load settings from streams in `read_setting_streams` to specified setting
    containers or iterables.
    
    The order of streams in the `read_setting_streams` list indicates the preference
    of the streams, beginning with the first stream in the list. If not all settings
    could be found in the first stream, the second stream is read to assign values
    to the remaining settings. This continues until all settings are read.
    
    If some settings could not be found in any of the streams,
    their default values are used.
    
    Return values:
    
    * status:
      - SUCCESS: Settings successfully loaded. If settings had invalid values,
        their default values were assigned.
      
      - NOT_ALL_SETTINGS_FOUND: Could not load all specified settings from any of
        the streams. Default values are assigned to these settings.
      
      - READ_FAIL: Could not read data from the first stream where this error occurred.
        For files, this means that IOError or OSError exception was raised, or
        the file has invalid format.
    """
    
    if not setting_containers or self.read_setting_streams is None or not self.read_setting_streams:
      return self._status(self.SUCCESS)
    
    settings = []
    for container in setting_containers:
      settings.extend(container)
    
    for stream in self.read_setting_streams:
      try:
        stream.read(settings)
      except (SettingsNotFoundInStreamError, SettingStreamFileNotFoundError) as e:
        if type(e) == SettingsNotFoundInStreamError:
          settings = stream.settings_not_found
        
        if stream == self.read_setting_streams[-1]:
          return self._status(self.NOT_ALL_SETTINGS_FOUND, e.message)
        else:
          continue
      except (SettingStreamReadError, SettingStreamInvalidFormatError) as e:
        return self._status(self.READ_FAIL, e.message)
      else:
        break
    
    return self._status(self.SUCCESS)
  
  def save(self, *setting_containers):
    """
    Save settings from specified setting containers or iterables to all streams
    specified in write_setting_streams.
    
    Return values:
    
    * status:
      - SUCCESS: Settings successfully saved.
      
      - WRITE_FAIL: Could not write data to the first stream where this error occurred.
        For files, this means that IOError or OSError exception was raised.
    """
    
    if not setting_containers or self.write_setting_streams is None or not self.write_setting_streams:
      return self._status(self.SUCCESS)
    
    # Put all settings into one list so that the write() method is invoked
    # only once per each stream.
    settings = []
    for container in setting_containers:
      settings.extend(container)
    
    for stream in self.write_setting_streams:
      try:
        stream.write(settings)
      except SettingStreamWriteError as e:
        return self._status(self.WRITE_FAIL, e.message)
    
    return self._status(self.SUCCESS)
  
  def _status(self, status, message=None):
    self._status_message = message if message is not None else ""
    return status

#===============================================================================

class SettingPresenter(object):
  
  """
  This class wraps a Setting object and a GUI element together.
  
  Various GUI elements have different attributes or methods to access their
  properties. This class wraps some of these attributes/methods so that they can
  be accessed with the same name.
  """
  
  __metaclass__ = abc.ABCMeta
  
  def __init__(self, setting, element):
    self._setting = setting
    self._element = element
    self.value_changed_signal = None
  
  @property
  def setting(self):
    return self._setting
  
  @property
  def element(self):
    return self._element
  
  @abc.abstractmethod
  def value(self):
    pass
  
  @abc.abstractmethod
  def enabled(self):
    pass
  
  @abc.abstractmethod
  def visible(self):
    pass

  @abc.abstractmethod
  def connect(self, *args):
    pass


class SettingPresenterContainer(container.Container):
  """
  This class:
  * groups SettingPresenter objects together
  """
  
  _SETTING_ATTRIBUTES = {'value' : 'value', 
                         'ui_enabled' : 'enabled',
                         'ui_visible' : 'visible'}
  
  def __init__(self):
    super(SettingPresenterContainer, self).__init__()
    
    self._items_gui_elements = OrderedDict()
  
  def __getitem__(self, key):
    """
    Get SettingPresenter object.
    
    Key can be Setting name or a GUI element.
    """
    value = None
    try:
      value = self._items[key]
    except KeyError:
      value = self._items_gui_elements[key]
    
    return value
  
  def __setitem__(self, key, value):
    raise TypeError("replacing a SettingPresenter object or creating a new one is not allowed; "
                    "use the add() method instead")
  
  def __delitem__(self, key):
    raise TypeError("deleting a SettingPresenter object is not allowed")
  
  def add(self, setting_presenter):
    """
    Add a SettingPresenter object to the container.
    
    The object can then be accessed by SettingPresenter.Setting.name or SettingPresenter.element.
    """
    self._items[setting_presenter.setting.name] = setting_presenter
    self._items_gui_elements[setting_presenter.element] = setting_presenter
  
  def apply_changed_settings(self, changed_settings):
    """
    After streamline() is called on a Setting or a SettingContainer object,
    apply changed attributes of Setting objects in `changed_settings`
    to GUI elements.
    """
    for setting, changed_attributes in changed_settings.items():
      for attr in changed_attributes:
        setattr(self[setting.name], self._SETTING_ATTRIBUTES[attr], getattr(setting, attr))
  
