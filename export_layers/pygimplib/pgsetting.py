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
This module defines API that can be used to create plug-in settings and GUI
elements associated with the settings.
"""

#===============================================================================

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division

str = unicode

#===============================================================================


import os
import abc
import inspect
from collections import OrderedDict

import gimp
import gimpenums

from . import pgpath
from . import pgsettingpresenter
from .pgsettingpresenters_gtk import SettingGuiTypes

#===============================================================================

pdb = gimp.pdb

#===============================================================================


class SettingPdbTypes(object):
  int32 = gimpenums.PDB_INT32
  int16 = gimpenums.PDB_INT16
  int8 = gimpenums.PDB_INT8
  float = gimpenums.PDB_FLOAT
  string = gimpenums.PDB_STRING
  color = gimpenums.PDB_COLOR
  
  array_int32 = gimpenums.PDB_INT32ARRAY
  array_int16 = gimpenums.PDB_INT16ARRAY
  array_int8 = gimpenums.PDB_INT8ARRAY
  array_float = gimpenums.PDB_FLOATARRAY
  array_string = gimpenums.PDB_STRINGARRAY
  array_color = gimpenums.PDB_COLORARRAY
  
  image = gimpenums.PDB_IMAGE
  item = gimpenums.PDB_ITEM
  drawable = gimpenums.PDB_DRAWABLE
  layer = gimpenums.PDB_LAYER
  channel = gimpenums.PDB_CHANNEL
  selection = gimpenums.PDB_SELECTION
  vectors = gimpenums.PDB_VECTORS
  path = gimpenums.PDB_VECTORS       # alias to `vectors`
  
  parasite = gimpenums.PDB_PARASITE
  display = gimpenums.PDB_DISPLAY
  status = gimpenums.PDB_STATUS
  
  none = type(b"DoNotRegisterSettingPdbType", (), {})()
  automatic = None


#===============================================================================


class SettingValueError(Exception):
  """
  This exception class is raised when a value assigned to a `Setting` object is
  invalid.
  """
  
  pass


class SettingDefaultValueError(SettingValueError):
  """
  This exception class is raised when the default value specified during the
  `Setting` object initialization is invalid.
  """
  
  pass


#===============================================================================


class Setting(object):
  
  """
  This class holds data about a plug-in setting.
  
  Properties and methods in settings can be used in multiple scenarios, such as:
  * using setting values as variables in the main logic of plug-ins
  * registering GIMP Procedural Database (PDB) parameters to plug-ins
  * managing GUI element properties (values, labels, etc.)
  
  This class in particular can store any data. However, it is strongly
  recommended to use the appropriate `Setting` subclass for a particular data
  type, as the subclasses offer the following features:
  * setting can be registered to GIMP PDB,
  * automatic validation of input values,
  * readily available GUI element, keeping the GUI and the setting value in sync.
  
  Settings can contain an event handler that is triggered when the value
  of the setting changes (e.g. when `set_value()` method is called). This way,
  other settings and their GUI elements can be adjusted automatically.
  
  Attributes:
  
  * `name` (read-only) - A name (string) that uniquely identifies the setting.
  
  * `value` (read-only) - The setting value. To set the value, call the
    `set_value()` method. `value` is initially set to `default_value`.
  
  * `default_value` (read-only) - Default value of the setting assigned upon its
    initialization or after the `reset()` method is called.
  
  * `gui` (read-only) - `SettingPresenter` instance acting as a wrapper of a GUI
    element. With `gui`, you may modify GUI-specific attributes, such as
    visibility or sensitivity (enabled/disabled).
  
  * `display_name` (read-only) - Setting name in human-readable format. Useful
    e.g. as GUI labels. The display name may contain underscores, which can be
    interpreted by the GUI as keyboard mnemonics.
  
  * `description` (read-only) - Usually `display_name` plus additional
    information in parentheses (such as boundaries for numeric values). Useful
    as a setting description when registering the setting as a plug-in parameter
    to the GIMP Procedural Database (PDB). If the class uses `display_name` to
    generate the description and `display_name` contains underscores, they are
    removed in the description.
  
  * `pdb_type` (read-only) - GIMP PDB parameter type, used when registering the
    setting as a plug-in parameter to the PDB. In Setting subclasses, only
    specific PDB types are allowed. Refer to the documentation of the subclasses
    for the list of allowed PDB types.
  
  * `pdb_name` (read-only) - Setting name as it appears in the GIMP PDB as
    a PDB parameter name.
  
  * `error_messages` (read-only) - A dict of error messages containing
    (message name, message contents) pairs, which can be used e.g. if a value
    assigned to the setting is invalid. You can add your own error messages and
    assign them to one of the "default" error messages (such as 'invalid_value'
    in several `Setting` subclasses) depending on the context in which the value
    assigned is invalid.
  """
  
  _ALLOWED_PDB_TYPES = []
  _ALLOWED_EMPTY_VALUES = []
  _ALLOWED_GUI_TYPES = []
  
  def __init__(self, name, default_value,
               allow_empty_values=False,
               display_name=None,
               pdb_type=SettingPdbTypes.automatic,
               gui_type=SettingGuiTypes.automatic,
               auto_update_gui_to_setting=True,
               error_messages=None):
    
    """
    Described are only those parameters that do not correspond to
    any attribute in this class, or parameters requiring additional information.
    
    Parameters:
    
    * `default_value` - During Setting initialization, the default value is
      validated. If one of the so called "empty values" (specific to each
      setting class) is passed as the default value, default value validation is
      not performed.
    
    * `allow_empty_values` - If False and an empty value is passed to the
      `set_value` method, then the value is considered invalid. Otherwise, the
      value is considered valid.
    
    * `pdb_type` - one of the `SettingPdbTypes` items. If set to
      `SettingPdbTypes.automatic` (the default), the first PDB type in the list
      of allowed PDB types for a particular Setting subclass is chosen. If no
      allowed PDB types are defined for that subclass, the setting cannot be
      registered (None is assigned).
    
    * `gui_type` - Type of GUI element to be created by the `create_gui` method.
      Use the `SettingGuiTypes` enum to specify the desired GUI type.
    
      If `gui_type` is `SettingGuiTypes.automatic`, choose the first GUI type
      from the list of allowed GUI type for the corresponding `Setting`
      subclass. If there are no allowed GUI types for that subclass, no GUI is
      created for this setting.
      
      If an explicit GUI type is specified, it must be one of the types from the
      list of allowed GUI types for the corresponding `Setting` subclass. If
      not, `ValueError` is raised.
      
      If the `SettingGuiTypes.none` type is specified, no GUI is created for
      this setting.
    
    * `auto_update_gui_to_setting` - If True, automatically update the setting
      value if the GUI value is updated. If False, the setting must be updated
      manually by calling `Setting.gui.update_setting_value` when needed.
      
      This parameter does not have any effect if the GUI type used in
      this setting cannot provide automatic GUI-to-setting update.
    
    * `error_messages` - A dict containing (message name, message contents)
      pairs. Use this to pass custom error messages. This way, you may also
      override default error messages defined in classes.
    """
    
    self._name = name
    self._default_value = default_value
    
    self._value = self._default_value
    
    self._allow_empty_values = allow_empty_values
    self._allowed_empty_values = list(self._ALLOWED_EMPTY_VALUES)
    
    self._display_name = self._get_display_name(display_name)
    self._description = self._get_description(self._display_name)
    
    self._pdb_type = self._get_pdb_type(pdb_type)
    self._pdb_name = self._get_pdb_name(self._name)
    
    self._value_changed_event_handler = None
    self._value_changed_event_handler_args = []
    
    self._setting_value_synchronizer = pgsettingpresenter.SettingValueSynchronizer()
    self._setting_value_synchronizer.apply_gui_value_to_setting = self._apply_gui_value_to_setting
    
    self._gui_type = self._get_gui_type(gui_type)
    self._gui = pgsettingpresenter.NullSettingPresenter(
      self, None, self._setting_value_synchronizer, auto_update_gui_to_setting=auto_update_gui_to_setting)
    
    self._error_messages = {}
    self._init_error_messages()
    if error_messages is not None:
      self._error_messages.update(error_messages)
    
    if self._should_validate_default_value():
      self._validate_default_value()
  
  @property
  def name(self):
    return self._name
  
  @property
  def value(self):
    return self._value
  
  @property
  def default_value(self):
    return self._default_value
  
  @property
  def gui(self):
    return self._gui
  
  @property
  def display_name(self):
    return self._display_name
  
  @property
  def description(self):
    return self._description
  
  @property
  def pdb_type(self):
    return self._pdb_type
  
  @property
  def pdb_name(self):
    return self._pdb_name
  
  @property
  def error_messages(self):
    return self._error_messages
  
  def set_value(self, value):
    """
    Set the setting value.
    
    Before the assignment, validate the value. If the value is invalid, raise
    `SettingValueError`.
    
    Update the value of the GUI element. Even if the setting has no GUI element
    assigned, the value is recorded. Once a GUI element is assigned to the
    setting, the recorded value is copied over to the GUI element.
    
    If an event handler is connected (via `connect_value_changed_event()`), call
    the event handler.
    
    Note: This is a method and not a property because of the additional overhead
    introduced by validation, GUI updating and event handling. `value` still
    remains a property for the sake of brevity.
    """
    
    self._assign_and_validate_value(value)
    self._setting_value_synchronizer.apply_setting_value_to_gui(value)
    if self._is_value_changed_event_connected():
      self._trigger_value_changed_event()
  
  def reset(self):
    """
    Reset setting value to its default value.
    
    This is different from
    
      setting.set_value(setting.default_value)
    
    in that `reset()` does not validate the default value.
    
    `reset()` also updates the GUI and calls the event handler.
    """
    
    self._value = self._default_value
    self._setting_value_synchronizer.apply_setting_value_to_gui(self._default_value)
    if self._is_value_changed_event_connected():
      self._trigger_value_changed_event()
  
  def create_gui(self, gui_type=None, gui_element=None, auto_update_gui_to_setting=True):
    """
    Create a new GUI object (`SettingPresenter` instance) for this setting. The
    state of the previous GUI object is copied to the new GUI object (such as
    its value, visibility and enabled state).
    
    Parameters:
    
    * `gui_type` - `SettingPresenter` type to wrap `gui_element` around.
      
      If `gui_type` is None, create a GUI object of the type specified in the
      `gui_type` parameter in `__init__`.
      
      To specify an existing GUI element, pass a specific `gui_type` and the
      GUI element in `gui_element`. This is useful if you wish to use the GUI
      element for multiple settings or for other purposes outside this setting.
      
      If `gui_type` is specified and is not any of the allowed GUI types for the
      setting, raise `ValueError`.
    
    * `gui_element` - A GUI element (wrapped in a `SettingPresenter` instance).
    
      If `gui_type` is None, `gui_element` is ignored. If `gui_type` is not
      None and `gui_element` is None, raise `ValueError`.
    
    * `auto_update_gui_to_setting` - See `auto_update_gui_to_setting` parameter in `__init__`.
    """
    
    if gui_type is not None and gui_element is None:
      raise ValueError("gui_element cannot be None if gui_type is not None")
    if gui_type is None and gui_element is not None:
      raise ValueError("gui_type cannot be None if gui_element is not None")
    
    if gui_type is None:
      gui_type = self._gui_type
    
    self._gui = gui_type(
      self, gui_element, setting_value_synchronizer=self._setting_value_synchronizer,
      old_setting_presenter=self._gui, auto_update_gui_to_setting=auto_update_gui_to_setting)
  
  def connect_value_changed_event(self, event_handler, event_handler_args, trigger_event_now=True):
    """
    Connect an event handler that triggers when `set_value()` is called.
    
    The `event_handler` (a function) must always contain at least one argument.
    The first argument must be the setting from which the event handler is
    invoked.
    
    Parameters:
    
    * `event_handler` - Function to be called when `set_value()` from this
      setting is called.
    
    * `event_handler_args` - List of additional arguments to `event_handler`.
      Arguments can be `Setting` instances or any other objects.
    
    * `trigger_event_now` - If True, trigger the event handler upon calling this
      method. This is useful to ensure that settings have the correct initial
      values and GUI attributes.
    
    Raises:
    
    * `TypeError` - `event_handler` is not a function or the wrong number of
      arguments was passed in `event_handler_args`.
    """
    
    if not callable(event_handler):
      raise TypeError("not a function")
    
    # Subtract 1 because the first argument is always this Setting object.
    num_required_event_handler_args = len(inspect.getargspec(event_handler)[0]) - 1
    num_actual_event_handler_args = len(event_handler_args)
    
    if num_required_event_handler_args != num_actual_event_handler_args:
      raise TypeError("wrong number of arguments to the event handler (required {0}, passed {1})"
                      .format(num_required_event_handler_args, num_actual_event_handler_args))
    
    self._value_changed_event_handler = event_handler
    self._value_changed_event_handler_args = event_handler_args
    
    if trigger_event_now:
      self._trigger_value_changed_event()
  
  def remove_value_changed_event(self):
    """
    Remove the event handler set by the `connect_value_changed_event()` method.
    """
    
    if self._value_changed_event_handler is None:
      raise TypeError("no event handler was previously set")
    
    self._value_changed_event_handler = None
    self._value_changed_event_handler_args = []
  
  def is_value_empty(self):
    """
    Return True if the setting value is one of the empty values defined for the
    setting class, otherwise return False.
    """
    return self._is_value_empty(self._value)
  
  def can_be_registered_to_pdb(self):
    """
    Return True if setting can be registered as a parameter to GIMP PDB, False
    otherwise.
    """
    
    return self._pdb_type != SettingPdbTypes.none
  
  def _is_value_empty(self, value):
    return value in self._allowed_empty_values
  
  def _assign_and_validate_value(self, value):
    if not self._allow_empty_values:
      self._validate(value)
    else:
      if not self._is_value_empty(value):
        self._validate(value)
    
    self._value = value
  
  def _apply_gui_value_to_setting(self, value):
    self._assign_and_validate_value(value)
    if self._is_value_changed_event_connected():
      self._trigger_value_changed_event()
  
  def _validate(self, value):
    """
    Check whether the specified value is valid. If the value is invalid, raise
    `SettingValueError`.
    """
    
    pass
  
  def _should_validate_default_value(self):
    return not self._is_value_empty(self._default_value)
  
  def _validate_default_value(self):
    """
    Check whether the default value of the setting is valid. If the default
    value is invalid, raise `SettingDefaultValueError`.
    """
    
    try:
      self._validate(self._default_value)
    except SettingValueError as e:
      raise SettingDefaultValueError(e.message)
  
  def _is_value_changed_event_connected(self):
    return self._value_changed_event_handler is not None
  
  def _trigger_value_changed_event(self):
    self._value_changed_event_handler(self, *self._value_changed_event_handler_args)
  
  def _init_error_messages(self):
    """
    Initialize custom error messages in the `error_messages` dict.
    """
    
    pass
  
  def _get_display_name(self, display_name):
    if display_name is not None:
      return display_name
    else:
      return self._generate_display_name()
  
  def _generate_display_name(self):
    return self.name.replace("_", " ").capitalize()
  
  def _get_description(self, display_name):
    return display_name.replace("_", "")
  
  def _get_pdb_type(self, pdb_type):
    if pdb_type == SettingPdbTypes.automatic:
      return self._get_default_pdb_type()
    elif pdb_type == SettingPdbTypes.none:
      return SettingPdbTypes.none
    elif pdb_type in self._ALLOWED_PDB_TYPES:
      return pdb_type
    else:
      raise ValueError("GIMP PDB type \"" + str(pdb_type) + "\" not allowed; "
                       "for the list of allowed PDB types, refer to "
                       "the documentation of the appropriate Setting class")
  
  def _get_default_pdb_type(self):
    if self._ALLOWED_PDB_TYPES:
      return self._ALLOWED_PDB_TYPES[0]
    else:
      return SettingPdbTypes.none
  
  def _get_pdb_name(self, name):
    """
    Return mangled setting name, useful when using the name in the setting
    description (GIMP PDB automatically mangles setting names, but not
    descriptions).
    """
    
    return name.replace("_", "-")
  
  def _get_gui_type(self, gui_type):
    gui_type_to_return = None
    
    if gui_type == SettingGuiTypes.automatic:
      if self._ALLOWED_GUI_TYPES:
        gui_type_to_return = self._ALLOWED_GUI_TYPES[0]
      else:
        gui_type_to_return = SettingGuiTypes.none
    else:
      if gui_type in self._ALLOWED_GUI_TYPES:
        gui_type_to_return = gui_type
      elif gui_type in [SettingGuiTypes.none, pgsettingpresenter.NullSettingPresenter]:
        gui_type_to_return = gui_type
      else:
        raise ValueError("invalid GUI type; must be one of {0}"
                         .format([type_.__name__ for type_ in self._ALLOWED_GUI_TYPES]))
    
    return gui_type_to_return
  
  def _value_to_str(self, value):
    """
    Prepend `value` to an error message if `value` that is meant to be assigned
    to this setting is invalid.
    
    Don't prepend anything if `value` is empty or None.
    """
    
    if value:
      return '"' + str(value) + '": '
    else:
      return ""


#-------------------------------------------------------------------------------


class NumericSetting(Setting):
  
  """
  This is an abstract class for numeric settings - integers and floats.
  
  When assigning a value, it checks for the upper and lower bounds if they are set.
  
  Additional attributes:
  
  * `min_value` - Minimum allowed numeric value.
  
  * `max_value` - Maximum allowed numeric value.
  
  Raises:
  
  * `SettingValueError` - If `min_value` is not None and the value assigned is
    less than `min_value`, or if `max_value` is not None and the value assigned
    is greater than `max_value`.
  
  Error messages:
  
  * `'below_min'` - The value assigned is less than `min_value`.
  
  * `'above_max'` - The value assigned is greater than `max_value`.
  """
  
  __metaclass__ = abc.ABCMeta
  
  def __init__(self, name, default_value, min_value=None, max_value=None, **kwargs):
    self._min_value = min_value
    self._max_value = max_value
    
    super(NumericSetting, self).__init__(name, default_value, **kwargs)
  
  def _init_error_messages(self):
    self.error_messages['below_min'] = _("Value cannot be less than {0}.").format(self._min_value)
    self.error_messages['above_max'] = _("Value cannot be greater than {0}.").format(self._max_value)
  
  @property
  def min_value(self):
    return self._min_value
  
  @property
  def max_value(self):
    return self._max_value
  
  @property
  def description(self):
    if self._min_value is not None and self._max_value is None:
      return self._pdb_name + " >= " + str(self._min_value)
    elif self._min_value is None and self._max_value is not None:
      return self._pdb_name + " <= " + str(self._max_value)
    elif self._min_value is not None and self._max_value is not None:
      return str(self._min_value) + " <= " + self._pdb_name + " <= " + str(self._max_value)
    else:
      return self._display_name
  
  def _validate(self, value):
    if self._min_value is not None and value < self._min_value:
      raise SettingValueError(self._value_to_str(value) + self.error_messages['below_min'])
    if self._max_value is not None and value > self._max_value:
      raise SettingValueError(self._value_to_str(value) + self.error_messages['above_max'])


class IntSetting(NumericSetting):
  
  """
  This class can be used for integer settings.
  
  Allowed GIMP PDB types:
  
  * SettingPdbTypes.int32 (default)
  * SettingPdbTypes.int16
  * SettingPdbTypes.int8
  """
  
  _ALLOWED_PDB_TYPES = [SettingPdbTypes.int32, SettingPdbTypes.int16, SettingPdbTypes.int8]


class FloatSetting(NumericSetting):
  
  """
  This class can be used for float settings.
  
  Allowed GIMP PDB types:
  
  * SettingPdbTypes.float
  """
  
  _ALLOWED_PDB_TYPES = [SettingPdbTypes.float]
    

class BoolSetting(Setting):
  
  """
  This class can be used for boolean settings.
  
  Since GIMP does not have a boolean PDB type defined, use one of the integer
  types.
  
  Allowed GIMP PDB types:
  
  * SettingPdbTypes.int32 (default)
  * SettingPdbTypes.int16
  * SettingPdbTypes.int8
  """
  
  _ALLOWED_PDB_TYPES = [SettingPdbTypes.int32, SettingPdbTypes.int16, SettingPdbTypes.int8]
  _ALLOWED_GUI_TYPES = [SettingGuiTypes.checkbox]
  
  @property
  def description(self):
    return self._description + "?"
  
  def set_value(self, value):
    value = bool(value)
    super(BoolSetting, self).set_value(value)


class EnumSetting(Setting):
  
  """
  This class can be used for settings with a limited number of values,
  accessed by their associated names.
  
  Allowed GIMP PDB types:
  
  * SettingPdbTypes.int32 (default)
  * SettingPdbTypes.int16
  * SettingPdbTypes.int8
  
  Additional attributes:
  
  * `items` (read-only) - A dict of <item name, item value> pairs. Item name
    uniquely identifies each item. Item value is the corresponding integer value.
  
  * `items_display_names` (read-only) - A dict of <item name, item display name>
    pairs. Item display names can be used e.g. as combo box items in the GUI.
  
  * `empty_value` (read-only) - Item name designated as the empty value. By
    default, the setting does not have an empty value.
  
  To access an item value:
    setting.items[item name]
  
  To access an item display name:
    setting.items_display_names[item name]
  
  Raises:
  
  * `SettingValueError` - See `'invalid_value'` error message below.
  
  * `ValueError` - See the other error messages below.
  
  * `KeyError` - Invalid key to `items` or `items_display_names`.
  
  Error messages:
  
  * `'invalid_value'` - The value assigned is not one of the items in this
    setting.
  
  * `'invalid_default_value'` - Item name is invalid (not found in the `items`
    parameter when instantiating the object).
  """
  
  _ALLOWED_PDB_TYPES = [SettingPdbTypes.int32, SettingPdbTypes.int16, SettingPdbTypes.int8]
  _ALLOWED_GUI_TYPES = [SettingGuiTypes.combobox]
  
  def __init__(self, name, default_value, items, empty_value=None, **kwargs):
    
    """
    Additional parameters:
    
    * `default_value` - Item name (identifier). Unlike other Setting classes,
      where the default value is specified directly, EnumSetting accepts a valid
      item name instead.
    
    * `items` - A list of either (item name, item display name) tuples
      or (item name, item display name, item value) tuples.
      
      For 2-element tuples, item values are assigned automatically, starting
      with 0. Use 3-element tuples to assign explicit item values. Values must
      be unique and specified in each tuple. Use only 2- or only 3-element
      tuples, they cannot be combined.
    """
    
    self._items, self._items_display_names, self._item_values = self._create_item_attributes(items)
    
    error_messages = {}
    
    error_messages['invalid_value'] = _(
      "Invalid item value; valid values: {0}"
    ).format(list(self._item_values))
    
    error_messages['invalid_default_value'] = (
      "invalid identifier for the default value; must be one of {0}"
    ).format(self._items.keys())
    
    if 'error_messages' in kwargs:
      error_messages.update(kwargs['error_messages'])
    kwargs['error_messages'] = error_messages
    
    if default_value in self._items:
      # `default_value` is passed as a string (identifier). In order to properly
      # initialize the setting, the actual default value (integer) must be passed
      # to the Setting initialization proper.
      param_default_value = self._items[default_value]
    else:
      raise SettingDefaultValueError(error_messages['invalid_default_value'])
    
    self._empty_value = self._get_empty_value(empty_value)
    
    super(EnumSetting, self).__init__(name, param_default_value, **kwargs)
    
    self._allowed_empty_values.append(self._empty_value)
    
    self._items_description = self._get_items_description()
  
  @property
  def description(self):
    return self._description + " " + self._items_description
  
  @property
  def items(self):
    return self._items
  
  @property
  def items_display_names(self):
    return self._items_display_names
  
  @property
  def empty_value(self):
    return self._empty_value
  
  def get_item_display_names_and_values(self):
    """
    Return a list of (item display name, item value) pairs.
    """
    
    display_names_and_values = []
    for item_name, item_value in zip(self._items_display_names.values(), self._items.values()):
      display_names_and_values.extend((item_name, item_value))
    return display_names_and_values
  
  def _validate(self, value):
    if value not in self._item_values or (not self._allow_empty_values and self._is_value_empty(value)):
      raise SettingValueError(self._value_to_str(value) + self.error_messages['invalid_value'])
  
  def _get_items_description(self):
    items_description = ""
    items_sep = ", "
    
    for value, display_name in zip(self._items.values(), self._items_display_names.values()):
      description = self._get_description(display_name)
      items_description += "{0} ({1}){2}".format(description, value, items_sep)
    items_description = items_description[:-len(items_sep)]
    
    return "{ " + items_description + " }"
  
  def _create_item_attributes(self, input_items):
    items = OrderedDict()
    items_display_names = OrderedDict()
    item_values = set()
    
    if all(len(elem) == 2 for elem in input_items):
      for i, (item_name, item_display_name) in enumerate(input_items):
        items[item_name] = i
        items_display_names[item_name] = item_display_name
        item_values.add(i)
    elif all(len(elem) == 3 for elem in input_items):
      for item_name, item_display_name, item_value in input_items:
        if item_value in item_values:
          raise ValueError("cannot set the same value for multiple items - they must be unique")
        
        items[item_name] = item_value
        items_display_names[item_name] = item_display_name
        item_values.add(item_value)
    else:
      raise ValueError("wrong number of tuple elements in items - must be only 2- or only 3-element tuples")
    
    return items, items_display_names, item_values
  
  def _get_empty_value(self, empty_value_name):
    if empty_value_name is not None:
      if empty_value_name in self._items:
        return self._items[empty_value_name]
      else:
        raise ValueError(
          "invalid identifier for the empty value; must be one of {0}".format(self._items.keys())
        )
    else:
      return None


class ImageSetting(Setting):
  
  """
  This setting class can be used for `gimp.Image` objects.
  
  Allowed GIMP PDB types:
  
  * SettingPdbTypes.image
  
  Allowed empty values:
  
  * None
  
  Error messages:
  
  * `'invalid_value'` - The image assigned is invalid.
  """
  
  _ALLOWED_PDB_TYPES = [SettingPdbTypes.image]
  _ALLOWED_EMPTY_VALUES = [None]
  
  def _init_error_messages(self):
    self.error_messages['invalid_value'] = _("Invalid image.")
  
  def _validate(self, image):
    if not pdb.gimp_image_is_valid(image):
      raise SettingValueError(self._value_to_str(image) + self.error_messages['invalid_value'])


class DrawableSetting(Setting):
  
  """
  This setting class can be used for `gimp.Drawable`, `gimp.Layer`,
  `gimp.GroupLayer` or `gimp.Channel` objects.
  
  Allowed GIMP PDB types:
  
  * SettingPdbTypes.drawable
  
  Allowed empty values:
  
  * None
  
  Error messages:
  
  * `'invalid_value'` - The drawable assigned is invalid.
  """
  
  _ALLOWED_PDB_TYPES = [SettingPdbTypes.drawable]
  _ALLOWED_EMPTY_VALUES = [None]
    
  def _init_error_messages(self):
    self.error_messages['invalid_value'] = _("Invalid drawable.")
  
  def _validate(self, drawable):
    if not pdb.gimp_item_is_valid(drawable):
      raise SettingValueError(self._value_to_str(drawable) + self.error_messages['invalid_value'])


class StringSetting(Setting):
  
  """
  This class can be used for string settings.
  
  Allowed GIMP PDB types:
  
  * SettingPdbTypes.string
  """
  
  _ALLOWED_PDB_TYPES = [SettingPdbTypes.string]
  _ALLOWED_GUI_TYPES = [SettingGuiTypes.text_entry]


class ValidatableStringSetting(StringSetting):
  
  """
  This class is an abstract class for string settings which are meant to be
  validated with one of the `pgpath.StringValidator` subclasses.
  
  To determine whether the string is valid, the `is_valid()` method from the
  subclass being used is called.
  
  Allowed GIMP PDB types:
  
  * SettingPdbTypes.string
  
  Error messages:
  
  This class contains empty messages for error statuses from
  the specified `pgpath.StringValidator` subclass. Normally, if the value
  (string) assigned is invalid, status messages returned from `is_valid()`
  are used. If desired, you may fill the error messages with custom messages
  which override the status messages from the method. See `ERROR_STATUSES` in
  the specified `pgpath.StringValidator` subclass for available error statuses.
  """
  
  __metaclass__ = abc.ABCMeta
  
  def __init__(self, name, default_value, string_validator, **kwargs):
    """
    Additional parameters:
    
    * `string_validator` - `pgpath.StringValidator` subclass used to validate
      the value assigned to this object.
    """
    
    self._string_validator = string_validator
    
    super(ValidatableStringSetting, self).__init__(name, default_value, **kwargs)
    
  def _init_error_messages(self):
    for status in self._string_validator.ERROR_STATUSES:
      self.error_messages[status] = ""
  
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
        self._value_to_str(value) + "\n".join([message for message in new_status_messages])
      )
  

class FileExtensionSetting(ValidatableStringSetting):
  
  """
  This setting class can be used for file extensions.
  
  `pgpath.FileExtensionValidator` subclass is used to determine whether the file
  extension is valid.
  
  Allowed GIMP PDB types:
  
  * SettingPdbTypes.string
  
  Allowed empty values:
  
  * ""
  """
  
  _ALLOWED_EMPTY_VALUES = [""]
  _ALLOWED_GUI_TYPES = [SettingGuiTypes.text_entry]
  
  def __init__(self, name, default_value, **kwargs):
    if isinstance(default_value, bytes):
      default_value = default_value.decode()
    
    super(FileExtensionSetting, self).__init__(name, default_value, pgpath.FileExtensionValidator, **kwargs)
  
  def set_value(self, value):
    if isinstance(value, bytes):
      value = value.decode()
    
    super(FileExtensionSetting, self).set_value(value)
  

class DirectorySetting(ValidatableStringSetting):
  
  """
  This setting class can be used for directories.
  
  `pgpath.DirectoryPathValidator` subclass is used to determine whether the
  directory name is valid.
  
  Allowed GIMP PDB types:
  
  * SettingPdbTypes.string
  
  Allowed empty values:
  
  * None
  * ""
  """
  
  _ALLOWED_EMPTY_VALUES = [None, ""]
  _ALLOWED_GUI_TYPES = [SettingGuiTypes.folder_chooser]
  
  def __init__(self, name, default_value, **kwargs):
    if isinstance(default_value, bytes):
      default_value = default_value.decode()
    
    super(DirectorySetting, self).__init__(name, default_value, pgpath.DirectoryPathValidator, **kwargs)
  
  def set_value(self, value):
    if isinstance(value, bytes):
      value = value.decode()
    
    super(DirectorySetting, self).set_value(value)
  
  def update_current_directory(self, current_image, directory_for_current_image):
    """
    Set the directory (setting value) to the value according to the priority list below:
    
    1. `directory_for_current_image` if not None
    2. `current_image` - import path of the current image if not None
    
    If both directories are None, do nothing.
    """
    
    if directory_for_current_image is not None:
      self.set_value(directory_for_current_image)
      return
    
    if current_image.filename is not None:
      self.set_value(os.path.dirname(current_image.filename.decode()))
      return


#-------------------------------------------------------------------------------


class ImageIDsAndDirectoriesSetting(Setting):
  
  """
  This setting class stores the list of currently opened images and their import
  directories as a dictionary of (image ID, import directory) pairs.
  Import directory is None if image has no import directory.
  
  This setting cannot be registered to the PDB as no corresponding PDB type exists.
  """
  
  @property
  def value(self):
    # Return a copy to prevent modifying the dictionary indirectly, e.g. via
    # setting individual entries (setting.value[image.ID] = directory).
    return dict(self._value)
  
  def update_image_ids_and_directories(self):
    """
    Remove all (image ID, import directory) pairs for images no longer opened in
    GIMP. Add (image ID, import directory) pairs for new images opened in GIMP.
    """
    
    # Get the list of images currently opened in GIMP
    current_images = gimp.image_list()
    current_image_ids = set([image.ID for image in current_images])
    
    # Remove images no longer opened in GIMP
    self._value = { image_id: self._value[image_id]
                    for image_id in self._value.keys() if image_id in current_image_ids }
    
    # Add new images opened in GIMP
    for image in current_images:
      if image.ID not in self._value.keys():
        self._value[image.ID] = self._get_imported_image_path(image)
  
  def update_directory(self, image_id, directory):
    """
    Assign a new directory to the specified image ID.
    
    If the image ID does not exist in the setting, raise KeyError. 
    """
    
    if image_id not in self._value:
      raise KeyError(image_id)
    
    self._value[image_id] = directory
  
  def _get_imported_image_path(self, image):
    if image.filename is not None:
      return os.path.dirname(image.filename.decode())
    else:
      return None


#===============================================================================


class SettingTypes(object):
  
  """
  This enum maps `Setting` classes to more human-readable names.
  """
  
  generic = Setting
  integer = IntSetting
  float = FloatSetting
  boolean = BoolSetting
  enumerated = EnumSetting
  image = ImageSetting
  drawable = DrawableSetting
  string = StringSetting
  file_extension = FileExtensionSetting
  directory = DirectorySetting
  image_IDs_and_directories = ImageIDsAndDirectoriesSetting
