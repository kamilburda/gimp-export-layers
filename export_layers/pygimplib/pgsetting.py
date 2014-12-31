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
* defines setting classes that can be used to create plug-in settings
"""

#===============================================================================

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division

str = unicode

#===============================================================================

import abc
from collections import OrderedDict

import gimp
import gimpenums

from . import pgpath

#===============================================================================

pdb = gimp.pdb

#===============================================================================


class SettingValueError(Exception):
  """
  This exception class is raised when a value assigned to the `value` attribute
  of a `Setting` object is invalid.
  """
  
  pass


class SettingDefaultValueError(SettingValueError):
  """
  This exception class is raised when the default value specified during the
  `Setting` object initialization is invalid.
  """
  
  def __init__(self, message):
    self._message_invalid_default_value = _(
      "If you need to turn off validation of the default value, "
      "pass `validate_default_value=False` when creating a Setting object."
    )
    self.message = '\n'.join((message,self._message_invalid_default_value))
    
  def __str__(self):
    return self.message


#===============================================================================


class Setting(object):
  
  """
  This class holds data about a plug-in setting.
  
  Attributes and methods in this class can be used in multiple scenarios, such as:
  * variables used in the main ("business"?) logic of plug-ins
  * parameters registered to plug-ins
  * properties of GUI elements (values, labels, tooltips, etc.)
  
  It is recommended to use an appropriate subclass for a setting. If there is no
  appropriate subclass, use this class.
  
  Attributes:
  
  * `name` (read-only) - A name (string) that uniquely identifies the setting.
  
  * `value` (read-only) - The setting value. To set the value, call the
    `set_value()` method. `value` is initially set to `default_value`.
  
  * `default_value` (read-only) - Default value of the setting assigned upon its
    initialization or after the `reset()` method is called.
  
  * `display_name` - Setting name in human-readable format. Useful as GUI labels.
  
  * `description` - Describes the setting in more detail. Useful for
    documentation purposes as well as GUI tooltips.
  
  * `short_description` (read-only) - Usually `display_name` plus additional
    information in parentheses (such as boundaries for numeric values). Useful
    as setting description when registering the setting as a plug-in parameter
    to the PDB.
  
  * `gimp_pdb_type` - GIMP Procedural Database (PDB) type, used when registering
    the setting as a plug-in parameter to the PDB. `_allowed_pdb_types` list,
    which is class-specific, determines whether the PDB type assigned is valid.
    `_allowed_pdb_types` in this class is None, which means that any PDB type
    can be assigned.
  
  * `registrable_to_pdb` - Indicates whether the setting can be registered
    as a parameter to a plug-in. Automatically set to True if `gimp_pdb_type` is
    assigned to a valid value that is not None.
  
  * `resettable_by_group` - If True, the setting is reset to its default
    value if the `reset()` method from the corresponding `SettingGroup` is
    called. False by default.
  
  * `ui_enabled` - Indicates whether the setting should be enabled (respond
    to user input) in the GUI. True by default. This attribute is only an
    indication, it does not modify a GUI element (use the appropriate
    `SettingPresenter` subclass for that purpose).
  
  * `ui_visible` - Indicates whether the setting should be visible in the GUI.
    True by default. This attribute is only an indication, it does not modify a
    GUI element (use the appropriate `SettingPresenter` subclass for that purpose).
  
  * `error_messages` - A dict of error messages, which can be used e.g. if a value
    assigned to the setting is invalid. You can add your own error messages and
    assign them to one of the "default" error messages (such as 'invalid_value'
    in several `Setting` subclasses) depending on the context in which the value
    assigned is invalid.
  
  * `changed_attributes` (read-only) - Contains a set of attribute names of the
    setting object that were changed. This attribute is used in the
    `streamline()` method. If any of the following attributes are assigned a
    value, they are added to the set:
    * `value`
    * `ui_enabled`
    * `ui_visible`
    
    `changed_attributes` is cleared if `streamline()` is called.
  """
  
  def __init__(self, name, default_value, validate_default_value=True):
    
    """
    Parameters:
    
    * `name` - Setting name as a string.
    
    * `default_value` - Default value of the setting.
    
    * `validate_default_value` - If True, check whether the default value of the
       setting is valid. If it is invalid, raise `SettingDefaultValueError`. If
       you need to skip the validation, e.g. because you need to specify an
       "empty" value as the default value (e.g. an empty string for
       FileExtensionSetting), set this to False.
    """
    
    self._name = name
    self._default_value = default_value
    
    if validate_default_value:
      self._validate_default_value()
    
    self._value = self._default_value
    
    self._mangled_name = self._get_mangled_name(self._name)
    
    self._display_name = ""
    self._description = ""
    
    self._gimp_pdb_type = None
    self._registrable_to_pdb = False
    self._allowed_pdb_types = None
    
    self._resettable_by_group = True
    
    self._error_messages = {}
    
    self._ui_enabled = True
    self._ui_visible = True
    
    self._changed_attributes = set()
    
    self._streamline_func = None
    self._streamline_args = []
  
  @property
  def name(self):
    return self._name
  
  @property
  def value(self):
    return self._value
  
  def set_value(self, value):
    """
    Set the setting value.
    
    This is a method and not a property because the subclasses of `Setting`
    override `set_value()` and perform additional operations than mere value
    assignment, such as value validation.
    
    `value` still remains a property for the sake of brevity.
    """
    
    self._validate(value)
    self._value = value
    self._changed_attributes.add('value')
  
  @property
  def default_value(self):
    return self._default_value
  
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
  def short_description(self):
    return self.display_name
  
  @property
  def gimp_pdb_type(self):
    return self._gimp_pdb_type
  
  @gimp_pdb_type.setter
  def gimp_pdb_type(self, value):
    if self._allowed_pdb_types is None or value in self._allowed_pdb_types:
      self._gimp_pdb_type = value
      self.registrable_to_pdb = value is not None
    else:
      raise ValueError("GIMP PDB type " + str(value) + " not allowed")
  
  @property
  def registrable_to_pdb(self):
    return self._registrable_to_pdb
  
  @registrable_to_pdb.setter
  def registrable_to_pdb(self, value):
    if value and self._gimp_pdb_type is None:
      raise ValueError("setting cannot be registered to PDB because it has no "
                       "PDB type set (attribute gimp_pdb_type)")
    self._registrable_to_pdb = value
  
  @property
  def resettable_by_group(self):
    return self._resettable_by_group
  
  @resettable_by_group.setter
  def resettable_by_group(self, value):
    self._resettable_by_group = value
  
  @property
  def ui_enabled(self):
    return self._ui_enabled
  
  @ui_enabled.setter
  def ui_enabled(self, value):
    self._ui_enabled = value
    self._changed_attributes.add('ui_enabled')
  
  @property
  def ui_visible(self):
    return self._ui_visible
  
  @ui_visible.setter
  def ui_visible(self, value):
    self._ui_visible = value
    self._changed_attributes.add('ui_visible')
  
  @property
  def changed_attributes(self):
    return self._changed_attributes
  
  @property
  def error_messages(self):
    return self._error_messages
  
  def reset(self):
    """
    Reset setting value to its default value.
    
    This is different from
    
      setting.set_value(setting.default_value)
    
    in that this method does not raise an exception if the default value is
    invalid and does not add the `value` attribute to `changed_attributes`.
    """
    
    self._value = self._default_value
  
  def streamline(self, force=False):
    """
    Change attributes of this and other settings based on the value
    of this setting, the other settings or additional arguments.
    
    Parameters:
    
    * `force` - If True, streamline settings even if the values of the other
      settings were not changed. This is useful when initializing GUI elements -
      setting up proper values, enabled/disabled state or visibility.
    
    Returns:
    
      `changed_settings` - Set of changed settings. A setting is considered
      changed if at least one of the following attributes were assigned a value:
      * `value`
      * `ui_enabled`
      * `ui_visible`
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
    Set a function to be called by the `streamline()` method.
    
    A streamline function must always contain at least one argument. The first
    argument is the setting from which the streamline function is invoked.
    This argument should therefore not be specified in `streamline_args`.
    
    Parameters:
    
    * `streamline_func` - Streamline function to be called by `streamline()`.
    
    * `streamline_args` - Additional arguments to `streamline_func`. Can be
      any arguments, including `Setting` objects.
    """
    
    if not callable(streamline_func):
      raise TypeError("not a function")
    
    self._streamline_func = streamline_func
    self._streamline_args = streamline_args
  
  def remove_streamline_func(self):
    """
    Remove streamline function set by the `set_streamline_func()` method.
    """
    
    if self._streamline_func is None:
      raise TypeError("no streamline function was previously set")
    
    self._streamline_func = None
    self._streamline_args = []
  
  def can_streamline(self):
    """
    Return True if a streamline function is set, False otherwise.
    """
    
    return self._streamline_func is not None
  
  def _validate(self, value):
    """
    Check whether the specified value is valid. If the value is invalid, raise
    `SettingValueError`.
    """
    
    pass
  
  def _validate_default_value(self):
    """
    Check whether the default value of the setting is valid. If the default
    value is invalid, raise `SettingDefaultValueError`.
    """
    
    try:
      self._validate(self._default_value)
    except SettingValueError as e:
      raise SettingDefaultValueError(e.message)
  
  def _value_to_str(self, value):
    """
    Use this method in subclasses to prepend `value` to an error message
    if `value` that is meant to be assigned to a setting is invalid.
    
    Don't prepend anything if the value is empty.
    """
    
    if value:
      return '"' + str(value) + '": '
    else:
      return ""
  
  def _get_mangled_name(self, name):
    """
    Return mangled setting name, useful when using the name in the short
    description (GIMP PDB automatically mangles setting names, but not
    descriptions).
    """
    
    return name.replace('_', '-')


#-------------------------------------------------------------------------------


class NumericSetting(Setting):
  
  """
  This is an abstract class for numeric settings - integers and floats.
  
  When assigning a value, it checks for the upper and lower bounds if they are set.
  
  Additional attributes:
  
  * `min_value` - Minimum numeric value.
  
  * `max_value` - Maximum numeric value.
  
  Raises:
  
  * `SettingValueError` - If `min_value` is not None and the value assigned is
    less than `min_value`, or if `max_value` is not None and the value assigned
    is greater than `max_value`.
  
  Error messages:
  
  * `'below_min'` - The value assigned is less than `min_value`.
  
  * `'above_max'` - The value assigned is greater than `max_value`.
  """
  
  __metaclass__ = abc.ABCMeta
  
  def __init__(self, name, default_value, **kwargs):
    self.min_value = None
    self.max_value = None
    
    super(NumericSetting, self).__init__(name, default_value, **kwargs)
    
    self.error_messages['below_min'] = _("Value cannot be less than {0}.").format(self.min_value)
    self.error_messages['above_max'] = _("Value cannot be greater than {0}.").format(self.max_value)
  
  @property
  def short_description(self):
    if self.min_value is not None and self.max_value is None:
      return self._mangled_name + " >= " + str(self.min_value)
    elif self.min_value is None and self.max_value is not None:
      return self._mangled_name + " <= " + str(self.max_value)
    elif self.min_value is not None and self.max_value is not None:
      return str(self.min_value) + " <= " + self._mangled_name + " <= " + str(self.max_value)
    else:
      return self.display_name
  
  def _validate(self, value):
    if self.min_value is not None and value < self.min_value:
      raise SettingValueError(self._value_to_str(value) + self.error_messages['below_min'])
    if self.max_value is not None and value > self.max_value:
      raise SettingValueError(self._value_to_str(value) + self.error_messages['above_max'])


class IntSetting(NumericSetting):
  
  """
  This class can be used for integer settings.
  
  Allowed GIMP PDB types:
  
  * PDB_INT32 (default)
  * PDB_INT16
  * PDB_INT8
  """
  
  def __init__(self, name, default_value, **kwargs):
    super(IntSetting, self).__init__(name, default_value, **kwargs)
    
    self._allowed_pdb_types = [gimpenums.PDB_INT32, gimpenums.PDB_INT16, gimpenums.PDB_INT8]
    self.gimp_pdb_type = gimpenums.PDB_INT32


class FloatSetting(NumericSetting):
  
  """
  This class can be used for float settings.
  
  Allowed GIMP PDB types:
  
  * PDB_FLOAT
  """
  
  def __init__(self, name, default_value, **kwargs):
    super(FloatSetting, self).__init__(name, default_value, **kwargs)
    
    self._allowed_pdb_types = [gimpenums.PDB_FLOAT]
    self.gimp_pdb_type = gimpenums.PDB_FLOAT
    

class BoolSetting(Setting):
  
  """
  This class can be used for boolean settings.
  
  Since GIMP does not have a boolean PDB type defined, use one of the integer
  types.
  
  Allowed GIMP PDB types:
  
  * PDB_INT32 (default)
  * PDB_INT16
  * PDB_INT8
  """
  
  def __init__(self, name, default_value, **kwargs):
    super(BoolSetting, self).__init__(name, default_value, **kwargs)
    
    self._allowed_pdb_types = [gimpenums.PDB_INT32, gimpenums.PDB_INT16, gimpenums.PDB_INT8]
    self.gimp_pdb_type = gimpenums.PDB_INT32
  
  @property
  def short_description(self):
    return self.display_name + "?"
  
  def set_value(self, value):
    value = bool(value)
    super(BoolSetting, self).set_value(value)


class EnumSetting(Setting):
  
  """
  This class can be used for settings with a limited number of values,
  accessed by their associated names.
  
  Allowed GIMP PDB types:
  
  * PDB_INT32 (default)
  * PDB_INT16
  * PDB_INT8
  
  Additional attributes:
  
  * `options` (read-only) - A dict of <option name, option value> pairs. Option name
    uniquely identifies each option. Option value is the corresponding integer value.
  
  * `options_display_names` (read-only) - A dict of <option name, option display name> pairs.
    Option display names can be used e.g. as combo box items in the GUI.
  
  To access an option value:
    setting.options[option name]
  
  To access an option display name:
    setting.options_display_names[option name]
  
  Raises:
  
  * `SettingValueError` - See `'invalid_value'` error message below.
  
  * `ValueError` - See the other error messages below.
  
  * `KeyError` - Invalid key to `options` or `options_display_names`.
  
  Error messages:
  
  * `'invalid_value'` - The value assigned is not one of the options in this setting.
  
  * `'invalid_default_value'` - Option name is invalid (not found in the `options` parameter
    when instantiating the object).
  
  * `'wrong_options_len'` - Wrong number of elements in tuples in the `options` parameter
    when initializing the object.
  
  * `'duplicate_option_value'` - When the object was being initialized, some
    option values in the 3-element tuples were specified multiple times.
  """
  
  def __init__(self, name, default_value, options, validate_default_value=True, **kwargs):
    
    """
    Additional parameters:
    
    * `default_value` - Option name (identifier). Unlike other Setting classes,
      where the default value is specified directly, EnumSetting accepts a valid
      option name instead.
    
    * `options` - A list of either (option name, option display name) tuples
      or (option name, option display name, option value) tuples.
      
      For 2-element tuples, option values are assigned automatically, starting
      with 0. Use 3-element tuples to assign explicit option values. Values must be
      unique and specified in each tuple. You cannot combine 2- and 3- element
      tuples - use only 2- or only 3-element tuples.
    """
    
    orig_validate_default_value = validate_default_value
    
    super(EnumSetting, self).__init__(name, default_value, validate_default_value=False, **kwargs)
    
    self._allowed_pdb_types = [gimpenums.PDB_INT32, gimpenums.PDB_INT16, gimpenums.PDB_INT8]
    self.gimp_pdb_type = gimpenums.PDB_INT32
    
    self.error_messages['wrong_options_len'] = (
      "Wrong number of tuple elements in options - must be only 2- or only 3-element tuples"
    )
    self.error_messages['duplicate_option_value'] = (
      "Cannot set the same value for multiple options - they must be unique"
    )
    
    self._options, self._options_display_names, self._option_values = self._create_option_attributes(options)
    
    self.error_messages['invalid_value'] = _(
      "Invalid option value; valid values: {0}"
    ).format(list(self._option_values))
    
    self.error_messages['invalid_default_value'] = (
      "invalid identifier for the default value; must be one of {0}"
    ).format(self._options.keys())
    
    if default_value in self._options:
      self._default_value = self._options[default_value]
      self._value = self._default_value
    else:
      if orig_validate_default_value:
        raise SettingDefaultValueError(self.error_messages['invalid_default_value'])
      else:
        self._default_value = default_value
        self._value = self._default_value
    
    self._options_str = self._stringify_options()
  
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
    """
    Return a list of (option display name, option value) pairs.
    """
    
    display_names_and_values = []
    for option_name, option_value in zip(self._options_display_names.values(), self._options.values()):
      display_names_and_values.extend((option_name, option_value))
    return display_names_and_values
  
  def _validate(self, value):
    if value not in self._option_values:
      raise SettingValueError(self._value_to_str(value) + self.error_messages['invalid_value'])
  
  def _create_option_attributes(self, input_options):
    options = OrderedDict()
    options_display_names = OrderedDict()
    option_values = set()
    
    if all(len(elem) == 2 for elem in input_options):
      for i, (option_name, option_display_name) in enumerate(input_options):
        options[option_name] = i
        options_display_names[option_name] = option_display_name
        option_values.add(i)
    elif all(len(elem) == 3 for elem in input_options):
      for option_name, option_display_name, option_value in input_options:
        if option_value in option_values:
          raise ValueError(self.error_messages['duplicate_option_value'])
        
        options[option_name] = option_value
        options_display_names[option_name] = option_display_name
        option_values.add(option_value)
    else:
      raise ValueError(self.error_messages['wrong_options_len'])
    
    return options, options_display_names, option_values
  
  def _stringify_options(self):
    options_str = ""
    options_sep = ", "
    
    for value, display_name in zip(self._options.values(), self._options_display_names.values()):
      options_str += '{0} ({1}){2}'.format(display_name, value, options_sep)
    options_str = options_str[:-len(options_sep)]
    
    return "{ " + options_str + " }"


class ImageSetting(Setting):
  
  """
  This setting class can be used for `gimp.Image` objects.
  
  Allowed GIMP PDB types:
  
  * PDB_IMAGE
  
  Error messages:
  
  * `'invalid_value'` - The image assigned is invalid.
  """
  
  def __init__(self, name, default_value, **kwargs):
    super(ImageSetting, self).__init__(name, default_value, **kwargs)
    
    self._allowed_pdb_types = [gimpenums.PDB_IMAGE]
    self.gimp_pdb_type = gimpenums.PDB_IMAGE
    
    self.error_messages['invalid_value'] = _("Invalid image.")
  
  def _validate(self, image):
    if not pdb.gimp_image_is_valid(image):
      raise SettingValueError(self._value_to_str(image) + self.error_messages['invalid_value'])


class DrawableSetting(Setting):
  
  """
  This setting class can be used for `gimp.Drawable`, `gimp.Layer`,
  `gimp.GroupLayer` or `gimp.Channel` objects.
  
  Allowed GIMP PDB types:
  
  * PDB_DRAWABLE
  
  Error messages:
  
  * `'invalid_value'` - The drawable assigned is invalid.
  """
  
  def __init__(self, name, default_value, **kwargs):
    super(DrawableSetting, self).__init__(name, default_value, **kwargs)
    
    self._allowed_pdb_types = [gimpenums.PDB_DRAWABLE]
    self.gimp_pdb_type = gimpenums.PDB_DRAWABLE
    
    self.error_messages['invalid_value'] = _("Invalid drawable.")
  
  def _validate(self, drawable):
    if not pdb.gimp_item_is_valid(drawable):
      raise SettingValueError(self._value_to_str(drawable) + self.error_messages['invalid_value'])


class StringSetting(Setting):
  
  """
  This class can be used for string settings.
  
  Allowed GIMP PDB types:
  
  * PDB_STRING
  """
  
  def __init__(self, name, default_value, **kwargs):
    super(StringSetting, self).__init__(name, default_value, **kwargs)
    
    self._allowed_pdb_types = [gimpenums.PDB_STRING]
    self.gimp_pdb_type = gimpenums.PDB_STRING


class ValidatableStringSetting(StringSetting):
  
  """
  This class is an abstract class for string settings which are meant to be
  validated with one of the `pgpath.StringValidator` subclasses.
  
  To determine whether the string is valid, the `is_valid()` method from the
  subclass being used is called.
  
  Allowed GIMP PDB types:
  
  * PDB_STRING
  
  Error messages:
  
  This class contains empty messages for error statuses from
  the specified `pgpath.StringValidator` subclass. Normally, if the value
  (string) assigned is invalid, status messages returned from `is_valid()`
  are used. If desired, you may fill the error messages with custom messages
  which override the status messages from the method. See `ERROR_STATUSES` in
  the specified `pgpath.StringValidator` subclass for available error statuses.
  """
  
  __metaclass__ = abc.ABCMeta
  
  def __init__(self, name, default_value, string_validator, validate_default_value=True, **kwargs):
    """
    Additional parameters:
    
    * `string_validator` - `pgpath.StringValidator` subclass used to validate
      the value assigned to this object.
    """
    
    orig_validate_default_value = validate_default_value
    
    super(ValidatableStringSetting, self).__init__(name, default_value, validate_default_value=False, **kwargs)
    
    self._string_validator = string_validator
    
    for status in self._string_validator.ERROR_STATUSES:
      self.error_messages[status] = ""
    
    if orig_validate_default_value:
      self._validate_default_value()
  
  def _validate(self, value):
    is_valid, status_messages = self._string_validator.is_valid(value)
    if not is_valid:
      new_status_messages = []
      for status, status_message in status_messages:
        if self.error_messages[status]:
          new_status_messages.append(self.error_messages[status])
        else:
          new_status_messages.append(status_message)
      
      raise SettingValueError(
        self._value_to_str(value) + '\n'.join([message for message in new_status_messages])
      )
  

class FileExtensionSetting(ValidatableStringSetting):
  
  """
  This setting class can be used for file extensions.
  
  `pgpath.FileExtensionValidator` subclass is used to determine whether
   the file extension is valid.
  
  Allowed GIMP PDB types:
  
  * PDB_STRING
  """
  
  def __init__(self, name, default_value, **kwargs):
    super(FileExtensionSetting, self).__init__(name, default_value, pgpath.FileExtensionValidator, **kwargs)
  

class DirectorySetting(ValidatableStringSetting):
  
  """
  This setting class can be used for directories.
  
  `pgpath.FilePathValidator` subclass is used to determine whether
   the directory name is valid.
  
  Allowed GIMP PDB types:
  
  * PDB_STRING
  """
  
  def __init__(self, name, default_value, **kwargs):
    super(DirectorySetting, self).__init__(name, default_value, pgpath.FilePathValidator, **kwargs)


class IntArraySetting(Setting):
    
  """
  This setting class can be used for integer arrays.
    
  Allowed GIMP PDB types:
    
  * PDB_INT32ARRAY (default)
  * PDB_INT16ARRAY
  * PDB_INT8ARRAY
    
  TODO:
  * validation - value must be an iterable sequence
    - this applies to any array setting
  """
  
  def __init__(self, name, default_value, **kwargs):
    super(IntArraySetting, self).__init__(name, default_value, **kwargs)
     
    self._allowed_pdb_types = [gimpenums.PDB_INT32ARRAY, gimpenums.PDB_INT16ARRAY, gimpenums.PDB_INT8ARRAY]
    self.gimp_pdb_type = gimpenums.PDB_INT32ARRAY
