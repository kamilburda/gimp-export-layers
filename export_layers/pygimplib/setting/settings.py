# -*- coding: utf-8 -*-
#
# Copyright (C) 2014-2019 khalim19
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
This module defines API that can be used to create plug-in settings and GUI
elements associated with the settings.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *
import future.utils

import abc
import collections
import copy
import os
import types

import gimp
from gimp import pdb
import gimpcolor
import gimpenums

from .. import constants as pgconstants
from .. import path as pgpath
from .. import utils as pgutils

from . import persistor as persistor_
from . import presenter as presenter_
from . import utils as utils_

from .presenters_gtk import SettingGuiTypes

__all__ = [
  "SettingPdbTypes",
  "Setting",
  "IntSetting",
  "FloatSetting",
  "BoolSetting",
  "EnumSetting",
  "StringSetting",
  "ImageSetting",
  "ItemSetting",
  "DrawableSetting",
  "LayerSetting",
  "ChannelSetting",
  "SelectionSetting",
  "VectorsSetting",
  "ColorSetting",
  "ParasiteSetting",
  "DisplaySetting",
  "PdbStatusSetting",
  "FileExtensionSetting",
  "DirpathSetting",
  "BrushSetting",
  "FontSetting",
  "GradientSetting",
  "PaletteSetting",
  "PatternSetting",
  "ImageIDsAndDirpathsSetting",
  "ArraySetting",
  "SettingValueError",
  "SettingDefaultValueError",
  "SettingTypes",
  "PDB_TYPES_TO_SETTING_TYPES_MAP",
]


class SettingPdbTypes(object):
  int32 = gimpenums.PDB_INT32
  int16 = gimpenums.PDB_INT16
  int8 = gimpenums.PDB_INT8
  int = int32
  float = gimpenums.PDB_FLOAT
  string = gimpenums.PDB_STRING
  
  image = gimpenums.PDB_IMAGE
  item = gimpenums.PDB_ITEM
  drawable = gimpenums.PDB_DRAWABLE
  layer = gimpenums.PDB_LAYER
  channel = gimpenums.PDB_CHANNEL
  selection = gimpenums.PDB_SELECTION
  vectors = gimpenums.PDB_VECTORS
  path = vectors
  
  color = gimpenums.PDB_COLOR
  parasite = gimpenums.PDB_PARASITE
  display = gimpenums.PDB_DISPLAY
  pdb_status = gimpenums.PDB_STATUS
  
  array_int32 = gimpenums.PDB_INT32ARRAY
  array_int16 = gimpenums.PDB_INT16ARRAY
  array_int8 = gimpenums.PDB_INT8ARRAY
  array_int = array_int32
  array_float = gimpenums.PDB_FLOATARRAY
  array_string = gimpenums.PDB_STRINGARRAY
  array_color = gimpenums.PDB_COLORARRAY
  
  none = None
  automatic = "automatic"


@future.utils.python_2_unicode_compatible
class Setting(utils_.SettingParentMixin, utils_.SettingEventsMixin):
  """
  This class holds data about a plug-in setting.
  
  Properties and methods in settings can be used in multiple scenarios, such as:
  * using setting values as variables in the main logic of plug-ins
  * registering GIMP Procedural Database (PDB) parameters to plug-ins
  * managing GUI element properties (values, labels, etc.)
  
  This class in particular can store any data. However, it is strongly
  recommended to use the appropriate `Setting` subclass for a particular data
  type, as the subclasses offer the following benefits:
  * setting can be registered to the GIMP procedural database (PDB),
  * automatic validation of input values,
  * readily available GUI element, keeping the GUI and the setting value in
    sync.
  
  Settings can contain event handlers that are triggered when a setting property
  changes, e.g. `value` (when `set_value()` is called). This way, for example,
  other settings can be updated automatically according to the new value of the
  modified setting.

  The following specific event types are invoked for settings:
  
    * `"value-changed"` - invoked after `set_value()` or `reset()` is called
      and before events of type `"after-set-value"` or `"after-reset"`.
    
    * `"before-set-value"` - invoked before `set_value()` is called.
    
    * `"after-set-value"` - invoked after `set_value()` is called.
    
    * `"before-reset"` - invoked before `reset()` is called.
    
    * `"after-reset"` - invoked after `reset()` is called.
    
    * `"before-set-gui"` - invoked before `set_gui()` is called.
    
    * `"after-set-gui"` - invoked after `set_gui()` is called.
    
    * `"before-load"` - invoked before loading a setting via
      `setting.persistor.Persistor.load()`.
    
    * `"after-load"` - invoked after loading a setting via
      `setting.persistor.Persistor.load()`. Events will not be invoked if
      loading settings failed (i.e. `Persistor` returns `READ_FAIL` status).
      Events will be invoked for all settings, even if some of them were not
      found in setting sources (i.e. `Persistor` returns
      `NOT_ALL_SETTINGS_FOUND` status).
    
    * `"before-save"` - invoked before saving a setting via
      `setting.persistor.Persistor.save()`.
    
    * `"after-save"` - invoked after saving a setting via
      `setting.persistor.Persistor.save()`. Events will not be invoked if saving
      settings failed (i.e. `Persistor` returns `SAVE_FAIL` status).
    
    * `"before-load-group"` - invoked before loading settings in a group via
      `Group.load()`.
    
    * `"after-load-group"` - invoked after loading settings in a group via
      `Group.load()`. This is useful if the group contains settings with
      different setting sources so that the event is invoked only once after
      all settings from different sources are loaded. This also applies to
      other related events (`"before-load-group"`, `"before-save-group"`,
      `"after-save-group"`).
    
    * `"before-save-group"` - invoked before saving settings in a group via
      `Group.load()`.
    
    * `"after-save-group"` - invoked after saving settings in a group via
      `Group.load()`.
  
  If a setting subclass supports "empty" values, such values will not be
  considered invalid when used as default values. However, empty values will be
  treated as invalid when assigning the setting one of such values after
  instantiation. Examples of empty values include `None` for an image object, or
  "Choose an item" for an enumerated setting. Empty values are useful when users
  must choose a different value, yet no valid value is a good candidate for a
  default value.
  
  Attributes:
  
  * `name` (read-only) - A name (string) that uniquely identifies the setting.
  
  * `value` (read-only) - The setting value. To set the value, call
    `set_value()`. `value` is initially set to `default_value`.
  
  * `default_value` (read-only) - Default value of the setting assigned upon its
    initialization or after `reset()` is called. If not specified or if
    `DEFAULT_VALUE` is passed explicitly, a default value is assigned
    automatically. The value depends on the particular setting subclass. This
    class uses `None` as the default value. Note that it is still a good
    practice to specify default values explicitly.
  
  * `gui` (read-only) - `setting.presenter.Presenter` instance acting as a
    wrapper of a GUI element. With `gui`, you may modify GUI-specific
    attributes, such as visibility or sensitivity.
  
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
  
  * `setting_sources` (read-only) - Default setting sources to use when loading
    or saving the setting. If `None`, no default sources are specified.
  
  * `error_messages` (read-only) - A dictionary of error messages containing
    (message name, message contents) pairs, which can be used e.g. if a value
    assigned to the setting is invalid. You can add your own error messages and
    assign them to one of the "default" error messages (such as "invalid_value"
    in several `Setting` subclasses) depending on the context in which the value
    assigned is invalid.
  
  * `tags` - A set of arbitrary tags attached to the setting. Tags can be used
    to e.g. iterate over a specific subset of settings.
  """
  
  DEFAULT_VALUE = type(b"DefaultValue", (), {})()
  
  _ALLOWED_PDB_TYPES = []
  _ALLOWED_GUI_TYPES = []
  _DEFAULT_DEFAULT_VALUE = None
  _EMPTY_VALUES = []
  
  def __init__(
        self,
        name,
        default_value=DEFAULT_VALUE,
        display_name=None,
        description=None,
        pdb_type=SettingPdbTypes.automatic,
        gui_type=SettingGuiTypes.automatic,
        allow_empty_values=False,
        auto_update_gui_to_setting=True,
        setting_sources=None,
        error_messages=None,
        tags=None):
    """
    Described are only those parameters that do not correspond to
    any attribute in this class, or parameters requiring additional information.
    
    Parameters:
    
    * `default_value` - During Setting initialization, the default value is
      validated. If one of the so called "empty values" (specific to each
      setting class) is passed as the default value, default value validation is
      not performed.
    
    * `pdb_type` - one of the `SettingPdbTypes` items. If set to
      `SettingPdbTypes.automatic` (the default), the first PDB type in the list
      of allowed PDB types for a particular Setting subclass is chosen. If no
      allowed PDB types are defined for that subclass, the setting cannot be
      registered (`None` is assigned).
    
    * `gui_type` - Type of GUI element to be created by `set_gui()`. Use the
      members of the `SettingGuiTypes` class to specify the desired GUI type.
    
      If `gui_type` is `SettingGuiTypes.automatic`, choose the first GUI type
      from the list of allowed GUI type for the corresponding `Setting`
      subclass. If there are no allowed GUI types for that subclass, no GUI is
      created for this setting.
      
      If an explicit GUI type is specified, it must be one of the types from the
      list of allowed GUI types for the corresponding `Setting` subclass. If
      not, `ValueError` is raised.
      
      If the `gui_type` is `None`, no GUI is created for this setting.
    
    * `allow_empty_values` - If `False` and an empty value is passed to
      `set_value()`, then the value is considered invalid. Otherwise, the value
      is considered valid.
    
    * `auto_update_gui_to_setting` - If `True`, automatically update the setting
      value if the GUI value is updated. If `False`, the setting must be updated
      manually by calling `Setting.gui.update_setting_value()` when needed.
      
      This parameter does not have any effect if the GUI type used in
      this setting cannot provide automatic GUI-to-setting update.
    
    * `error_messages` - A dictionary containing (message name, message
      contents) pairs. Use this to pass custom error messages. This way, you may
      also override default error messages defined in classes.
    
    * `tags` - An iterable container (list, set, etc.) of arbitrary tags
      attached to the setting. Tags can be used to e.g. iterate over a specific
      subset of settings.
    """
    super().__init__()
    
    self._name = name
    utils_.check_setting_name(self._name)
    
    self._default_value = self._get_default_value(default_value)
    
    self._value = self._copy_value(self._default_value)
    
    self._allow_empty_values = allow_empty_values
    self._empty_values = list(self._EMPTY_VALUES)
    
    self._display_name = utils_.get_processed_display_name(
      display_name, self._name)
    self._description = utils_.get_processed_description(
      description, self._display_name)
    
    self._pdb_type = self._get_pdb_type(pdb_type)
    self._pdb_name = utils_.get_pdb_name(self._name)
    
    self._setting_sources = setting_sources
    
    self._setting_value_synchronizer = presenter_.SettingValueSynchronizer()
    self._setting_value_synchronizer.apply_gui_value_to_setting = (
      self._apply_gui_value_to_setting)
    
    self._gui_type = self._get_gui_type(gui_type)
    self._gui = presenter_.NullPresenter(
      self,
      None,
      self._setting_value_synchronizer,
      auto_update_gui_to_setting=auto_update_gui_to_setting)
    
    self._error_messages = {}
    self._init_error_messages()
    if error_messages is not None:
      self._error_messages.update(error_messages)
    
    self._tags = set(tags) if tags is not None else set()
    
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
  def setting_sources(self):
    return self._setting_sources
  
  @property
  def error_messages(self):
    return self._error_messages
  
  @property
  def tags(self):
    return self._tags
  
  @classmethod
  def get_allowed_pdb_types(cls):
    """
    Return the list of allowed PDB types for this setting type.
    """
    return list(cls._ALLOWED_PDB_TYPES)
  
  @classmethod
  def get_allowed_gui_types(cls):
    """
    Return the list of allowed GUI types for this setting type.
    """
    return list(cls._ALLOWED_GUI_TYPES)
  
  def __str__(self):
    return pgutils.stringify_object(self, self.name)
  
  def get_path(self, relative_path_group=None):
    """
    This is a wrapper method for `setting.utils.get_setting_path()`. Consult the
    method for more information.
    """
    return utils_.get_setting_path(self, relative_path_group)
  
  def set_value(self, value):
    """
    Set the setting value.
    
    Before the assignment, validate the value. If the value is invalid, raise
    `SettingValueError`.
    
    Update the value of the GUI element. Even if the setting has no GUI element
    assigned, the value is recorded. Once a GUI element is assigned to the
    setting, the recorded value is copied over to the GUI element.
    
    Invoke event handlers of types `"before-set-value"` before assigning the
    value and `"value-changed"` and `"after-set-value"` (in this order) after
    assigning the value.
    
    Note: This is a method and not a property because of the additional overhead
    introduced by validation, GUI updating and event handling. `value` still
    remains a property for the sake of brevity.
    """
    self.invoke_event("before-set-value")
    
    self._validate_and_assign_value(value)
    self._setting_value_synchronizer.apply_setting_value_to_gui(value)
    
    self.invoke_event("value-changed")
    self.invoke_event("after-set-value")
  
  def reset(self):
    """
    Reset setting value to its default value.
    
    This is different from
    
      setting.set_value(setting.default_value)
    
    in that `reset()` does not validate the default value.
    
    Invoke event handlers of types `"before-reset"` before resetting and
    `"value-changed"` and `"after-reset"` (in this order) after resetting.
    
    `reset()` also updates the GUI.
    
    If the default value is an empty container (list, dict, ...), resetting
    works properly. If the default value is a non-empty container, it is the
    responsibility of the caller to ensure that the default value does not get
    modified, for example by connecting a `"before-reset"` event that sets the
    value to the correct default value before resetting.
    """
    self.invoke_event("before-reset")
    
    self._value = self._copy_value(self._default_value)
    self._setting_value_synchronizer.apply_setting_value_to_gui(self._value)
    
    self.invoke_event("value-changed")
    self.invoke_event("after-reset")
  
  def set_gui(
        self,
        gui_type=SettingGuiTypes.automatic,
        gui_element=None,
        auto_update_gui_to_setting=True):
    """
    Create a new GUI object (`Presenter` instance) for this setting or remove
    the GUI. The state of the previous GUI object is copied to the new GUI
    object (such as its value, visibility and sensitivity).
    
    Parameters:
    
    * `gui_type` - `Presenter` type to wrap `gui_element` around.
      
      When calling this method, `gui_type` does not have to be one of the
      allowed GUI types specified in the setting.
      
      If `gui_type` is `SettingGuiTypes.automatic`, create a GUI object of the
      type specified in the `gui_type` parameter in `__init__()`.
      
      To specify an existing GUI element, pass a specific `gui_type` and the
      GUI element in `gui_element`. This is useful if you wish to use the GUI
      element for multiple settings or for other purposes outside this setting.
      
      If `gui_type` is `None`, remove the GUI and disconnect any events the GUI
      had. The state of the old GUI is still preserved.
    
    * `gui_element` - A GUI element (wrapped in a `Presenter` instance).
    
      If `gui_type` is `SettingGuiTypes.automatic`, `gui_element` is ignored.
      If `gui_type` is not `SettingGuiTypes.automatic` and `gui_element` is
      `None`, raise `ValueError`.
    
    * `auto_update_gui_to_setting` - See `auto_update_gui_to_setting` parameter
      in `__init__()`.
    """
    if gui_type != SettingGuiTypes.automatic and gui_element is None:
      raise ValueError("gui_element cannot be None if gui_type is automatic")
    if gui_type == SettingGuiTypes.automatic and gui_element is not None:
      raise ValueError("gui_type cannot be automatic if gui_element is not None")
    
    self.invoke_event("before-set-gui")
    
    if gui_type == SettingGuiTypes.automatic:
      gui_type = self._gui_type
    elif gui_type is None:
      gui_type = presenter_.NullPresenter
      # We need to disconnect the "GUI changed" event before removing the GUI.
      self._gui.auto_update_gui_to_setting(False)
    
    self._gui = gui_type(
      self,
      gui_element,
      setting_value_synchronizer=self._setting_value_synchronizer,
      old_presenter=self._gui,
      auto_update_gui_to_setting=auto_update_gui_to_setting)
    
    self.invoke_event("after-set-gui")
  
  def load(self, setting_sources=None):
    """
    Load setting value from the specified setting source(s). See
    `setting.persistor.Persistor.load()` for more information about setting
    sources.
    
    If `setting_sources` is `None`, use the default setting sources. If
    specified, use a subset of sources matching the default sources. For
    example, if the default sources contain a persistent and a
    session-persistent source and `setting_sources` contains a
    session-persistent source, the setting value is loaded from the
    session-persistent source only.
    
    If there are no default setting sources or `setting_sources` does not match
    any of the default sources, this method has no effect.
    """
    return self._load_save(setting_sources, persistor_.Persistor.load)
  
  def save(self, setting_sources=None):
    """
    Save setting value to the specified setting source(s). See
    `setting.persistor.Persistor.save()` for more information about setting
    sources.
    
    If `setting_sources` is `None`, use the default setting sources. If
    specified, use a subset of sources matching the default sources. For
    example, if the default sources contain a persistent and a
    session-persistent source and `setting_sources` contains a
    session-persistent source, the setting value is loaded from the
    session-persistent source only.
    
    If there are no default setting sources or `setting_sources` does not match
    any of the default sources, this method has no effect.
    """
    return self._load_save(setting_sources, persistor_.Persistor.save)
  
  def is_value_empty(self):
    """
    Return `True` if the setting value is one of the empty values defined for
    the setting class, otherwise return `False`.
    """
    return self._is_value_empty(self._value)
  
  def can_be_registered_to_pdb(self):
    """
    Return `True` if setting can be registered as a parameter to GIMP PDB,
    `False` otherwise.
    """
    return self._pdb_type != SettingPdbTypes.none
  
  def get_pdb_param(self):
    """
    Return a list of tuples, each tuple containing data describing the setting
    as a GIMP PDB parameter - PDB type, PDB name and description.
    
    If the setting does not support any PDB type, return `None`.
    
    Most setting classes return a list of only one tuple, meaning the setting is
    represented by one PDB parameter.
    """
    if self.can_be_registered_to_pdb():
      return [(
        self.pdb_type,
        self.pdb_name.encode(pgconstants.GIMP_CHARACTER_ENCODING),
        self.description.encode(pgconstants.GIMP_CHARACTER_ENCODING))]
    else:
      return None
  
  def _validate(self, value):
    """
    Check whether the specified value is valid. If the value is invalid, raise
    `SettingValueError`.
    """
    pass
  
  def _init_error_messages(self):
    """
    Initialize custom error messages in the `error_messages` dictionary.
    """
    pass
  
  def _copy_value(self, value):
    """
    Create a shallow copy of the specified value. By default, iterables (except
    strings) are copied, otherwise the original objects are returned.
    
    Override this method in subclasses in case copying must be handled
    differently.
    """
    if (isinstance(value, collections.Iterable)
        and not isinstance(value, types.StringTypes)):
      return copy.copy(value)
    else:
      return value
  
  def _assign_value(self, value):
    """
    Assign specified value to the `_value` attribute after validation.
    
    Override this method in subclasses if other modifications to the `_value`
    attribute must be made other than mere assignment.
    """
    self._value = value
  
  def _is_value_empty(self, value):
    return value in self._empty_values
  
  def _validate_and_assign_value(self, value):
    if not self._allow_empty_values:
      self._validate_setting(value)
    else:
      if not self._is_value_empty(value):
        self._validate_setting(value)
    
    self._assign_value(value)
  
  def _apply_gui_value_to_setting(self, value):
    self._validate_and_assign_value(value)
    self.invoke_event("value-changed")
  
  def _validate_setting(self, value):
    try:
      self._validate(value)
    except SettingValueError as e:
      raise SettingValueError(str(e), setting=self)
  
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
      raise SettingDefaultValueError(str(e), setting=self)
  
  def _get_default_value(self, default_value):
    if isinstance(default_value, type(self.DEFAULT_VALUE)):
      if not callable(self._DEFAULT_DEFAULT_VALUE):
        return self._DEFAULT_DEFAULT_VALUE
      else:
        return self._DEFAULT_DEFAULT_VALUE()
    else:
      return default_value
  
  def _get_pdb_type(self, pdb_type):
    if pdb_type == SettingPdbTypes.automatic:
      return self._get_default_pdb_type()
    elif pdb_type is None or pdb_type == SettingPdbTypes.none:
      return SettingPdbTypes.none
    elif pdb_type in self._ALLOWED_PDB_TYPES:
      return pdb_type
    else:
      raise ValueError(
        "GIMP PDB type '{}' not allowed; for the list of allowed PDB types, refer to "
        "the documentation of the appropriate Setting class".format(pdb_type))
  
  def _get_default_pdb_type(self):
    if self._ALLOWED_PDB_TYPES:
      return self._ALLOWED_PDB_TYPES[0]
    else:
      return SettingPdbTypes.none
  
  def _get_gui_type(self, gui_type):
    gui_type_to_return = None
    
    if gui_type is None:
      gui_type_to_return = SettingGuiTypes.none
    elif gui_type == SettingGuiTypes.automatic:
      if self._ALLOWED_GUI_TYPES:
        gui_type_to_return = self._ALLOWED_GUI_TYPES[0]
      else:
        gui_type_to_return = SettingGuiTypes.none
    else:
      if gui_type in self._ALLOWED_GUI_TYPES:
        gui_type_to_return = gui_type
      elif gui_type in [SettingGuiTypes.none, presenter_.NullPresenter]:
        gui_type_to_return = gui_type
      else:
        raise ValueError(
          "{}: invalid GUI type '{}'; must be one of {}".format(
            self.name,
            gui_type,
            [type_.__name__ for type_ in self._ALLOWED_GUI_TYPES]))
    
    return gui_type_to_return
  
  def _load_save(self, setting_sources, load_save_func):
    if setting_sources is None:
      setting_sources = self._setting_sources
    else:
      if self._setting_sources is not None:
        setting_sources = [
          source for source in setting_sources if source in self._setting_sources]
      else:
        setting_sources = None
    
    return load_save_func([self], setting_sources)


class NumericSetting(future.utils.with_metaclass(abc.ABCMeta, Setting)):
  """
  This is an abstract class for numeric settings - integers and floats.
  
  When assigning a value, this class checks for the upper and lower bounds if
  they are set.
  
  Additional attributes:
  
  * `min_value` - Minimum allowed numeric value.
  
  * `max_value` - Maximum allowed numeric value.
  
  Raises:
  
  * `SettingValueError` - If `min_value` is not `None` and the value assigned is
    less than `min_value`, or if `max_value` is not `None` and the value
    assigned is greater than `max_value`.
  
  Error messages:
  
  * `"below_min"` - The value assigned is less than `min_value`.
  
  * `"above_max"` - The value assigned is greater than `max_value`.
  """
  
  def __init__(self, name, min_value=None, max_value=None, **kwargs):
    self._min_value = min_value
    self._max_value = max_value
    
    super().__init__(name, **kwargs)
  
  def _init_error_messages(self):
    self.error_messages["below_min"] = (
      _("Value cannot be less than {}.").format(self._min_value))
    self.error_messages["above_max"] = (
      _("Value cannot be greater than {}.").format(self._max_value))
  
  @property
  def min_value(self):
    return self._min_value
  
  @property
  def max_value(self):
    return self._max_value
  
  @property
  def description(self):
    if self._min_value is not None and self._max_value is None:
      return "{} >= {}".format(self._pdb_name, self._min_value)
    elif self._min_value is None and self._max_value is not None:
      return "{} <= {}".format(self._pdb_name, self._max_value)
    elif self._min_value is not None and self._max_value is not None:
      return "{} <= {} <= {}".format(self._min_value, self._pdb_name, self._max_value)
    else:
      return self._display_name
  
  def _validate(self, value):
    if self._min_value is not None and value < self._min_value:
      raise SettingValueError(
        utils_.value_to_str_prefix(value) + self.error_messages["below_min"])
    if self._max_value is not None and value > self._max_value:
      raise SettingValueError(
        utils_.value_to_str_prefix(value) + self.error_messages["above_max"])


class IntSetting(NumericSetting):
  """
  This class can be used for integer settings.
  
  Allowed GIMP PDB types:
  
  * `SettingPdbTypes.int32` (default)
  * `SettingPdbTypes.int16`
  * `SettingPdbTypes.int8`
  
  Default value: 0
  """
  
  _ALLOWED_PDB_TYPES = [
    SettingPdbTypes.int32, SettingPdbTypes.int16, SettingPdbTypes.int8]
  _ALLOWED_GUI_TYPES = [SettingGuiTypes.int_spin_button]
  _DEFAULT_DEFAULT_VALUE = 0


class FloatSetting(NumericSetting):
  """
  This class can be used for float settings.
  
  Allowed GIMP PDB types:
  
  * `SettingPdbTypes.float`
  
  Default value: 0.0
  """
  
  _ALLOWED_PDB_TYPES = [SettingPdbTypes.float]
  _ALLOWED_GUI_TYPES = [SettingGuiTypes.float_spin_button]
  _DEFAULT_DEFAULT_VALUE = 0.0


class BoolSetting(Setting):
  """
  This class can be used for boolean settings.
  
  Since GIMP does not have a boolean PDB type defined, use one of the integer
  types.
  
  Allowed GIMP PDB types:
  
  * `SettingPdbTypes.int32` (default)
  * `SettingPdbTypes.int16`
  * `SettingPdbTypes.int8`
  
  Default value: `False`
  """
  
  _ALLOWED_PDB_TYPES = [
    SettingPdbTypes.int32, SettingPdbTypes.int16, SettingPdbTypes.int8]
  _ALLOWED_GUI_TYPES = [
    SettingGuiTypes.check_button,
    SettingGuiTypes.check_menu_item,
    SettingGuiTypes.expander]
  _DEFAULT_DEFAULT_VALUE = False
  
  @property
  def description(self):
    return self._description + "?"
  
  def _assign_value(self, value):
    self._value = bool(value)


class EnumSetting(Setting):
  """
  This class can be used for settings with a limited number of values,
  accessed by their associated names.
  
  Allowed GIMP PDB types:
  
  * `SettingPdbTypes.int32` (default)
  * `SettingPdbTypes.int16`
  * `SettingPdbTypes.int8`
  
  Default value: Name of the first item passed to the `items` parameter during
  initialization.
  
  Additional attributes:
  
  * `items` (read-only) - A dictionary of <item name, item value> pairs. Item
    name uniquely identifies each item. Item value is the corresponding integer
    value.
  
  * `items_display_names` (read-only) - A dictionary of <item name, item display
    name> pairs. Item display names can be used e.g. as combo box items in the
    GUI.
  
  * `empty_value` (read-only) - Item name designated as the empty value. By
    default, the setting does not have an empty value.
  
  To access an item value:
    setting.items[item name]
  
  To access an item display name:
    setting.items_display_names[item name]
  
  Raises:
  
  * `SettingValueError` - See `"invalid_value"` error message below.
  
  * `SettingDefaultValueError` - See `"invalid_default_value"` error message
    below.
  
  * `ValueError` - no items were specified, the same value was assigned to
    multiple items, or uneven number of elements was passed to the `items`
    parameter during initialization.
  
  * `KeyError` - Invalid key to `items` or `items_display_names`.
  
  Error messages:
  
  * `"invalid_value"` - The value assigned is not one of the items in this
    setting.
  
  * `"invalid_default_value"` - Item name is invalid (not found in the `items`
    parameter when instantiating the object).
  """
  
  _ALLOWED_PDB_TYPES = [
    SettingPdbTypes.int32, SettingPdbTypes.int16, SettingPdbTypes.int8]
  _ALLOWED_GUI_TYPES = [SettingGuiTypes.combo_box]
  _DEFAULT_DEFAULT_VALUE = lambda self: next((name for name in self._items), None)
  
  def __init__(self, name, items, empty_value=None, **kwargs):
    """
    Additional parameters:
    
    * `items` - A list of either (item name, item display name) tuples
      or (item name, item display name, item value) tuples. For 2-element
      tuples, item values are assigned automatically, starting with 0. Use
      3-element tuples to assign explicit item values. Values must be unique
      and specified in each tuple. Use only 2- or only 3-element tuples, they
      cannot be combined.
    
    * `default_value` - Item name (identifier). Unlike other Setting classes,
      where the default value is specified directly, `EnumSetting` accepts a
      valid item name instead.
    """
    self._items, self._items_display_names, self._item_values = (
      self._create_item_attributes(items))
    
    # This member gets overridden during parent class instantiation, but can
    # still be accessible before the instantiation if need be.
    self._error_messages = {}
    
    self._error_messages["invalid_value"] = (
      _("Invalid item value; valid values: {}").format(list(self._item_values)))
    
    self._error_messages["invalid_default_value"] = (
      "invalid identifier for the default value; must be one of {}").format(
        list(self._items))
    
    if "error_messages" in kwargs:
      self._error_messages.update(kwargs["error_messages"])
    kwargs["error_messages"] = self._error_messages
    
    self._empty_value = self._get_empty_value(empty_value)
    
    super().__init__(name, **kwargs)
    
    self._empty_values.append(self._empty_value)
    
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
  
  def is_item(self, *item_names):
    """
    Return `True` if the setting value is set to one the specified items,
    otherwise return `False`.
    
    If only one item is specified, this is a more convenient and less verbose
    alternative to
      
      setting.value == setting.items[item_name]
    
    If multiple items are specified, this is equivalent to
    
      setting.value in (setting.items[name1], setting.items[name2], ...)
    """
    return any(self.value == self.items[item_name] for item_name in item_names)
  
  def set_item(self, item_name):
    """
    Set the specified item as the setting value.
    
    This is a more convenient and less verbose alternative to
      
      setting.set_value(setting.items[item_name])
    """
    self.set_value(self.items[item_name])
  
  def get_item_display_names_and_values(self):
    """
    Return a list of (item display name, item value) pairs.
    """
    display_names_and_values = []
    for item_name, item_value in zip(
          self._items_display_names.values(), self._items.values()):
      display_names_and_values.extend((item_name, item_value))
    return display_names_and_values
  
  def _get_default_value(self, default_value):
    if isinstance(default_value, type(Setting.DEFAULT_VALUE)):
      default_default_value = super()._get_default_value(default_value)
      if default_default_value is not None:
        return self._items[default_default_value]
      else:
        return default_default_value
    else:
      if default_value in self._items:
        # `default_value` is passed as a string (identifier), while the actual
        # value (integer) must be passed to the setting initialization.
        return self._items[default_value]
      else:
        raise SettingDefaultValueError(self._error_messages["invalid_default_value"])
  
  def _validate(self, value):
    if (value not in self._item_values
        or (not self._allow_empty_values and self._is_value_empty(value))):
      raise SettingValueError(
        utils_.value_to_str_prefix(value) + self.error_messages["invalid_value"])
  
  def _get_items_description(self):
    items_description = ""
    items_sep = ", "
    
    for value, display_name in zip(
          self._items.values(), self._items_display_names.values()):
      description = utils_.get_processed_description(None, display_name)
      items_description += "{} ({}){}".format(description, value, items_sep)
    items_description = items_description[:-len(items_sep)]
    
    return "{ " + items_description + " }"
  
  def _create_item_attributes(self, input_items):
    items = collections.OrderedDict()
    items_display_names = collections.OrderedDict()
    item_values = set()
    
    if not input_items:
      raise ValueError("must specify at least one item")
    if all(len(elem) == 2 for elem in input_items):
      for i, (item_name, item_display_name) in enumerate(input_items):
        items[item_name] = i
        items_display_names[item_name] = item_display_name
        item_values.add(i)
    elif all(len(elem) == 3 for elem in input_items):
      for item_name, item_display_name, item_value in input_items:
        if item_value in item_values:
          raise ValueError(
            "cannot set the same value for multiple items - they must be unique")
        
        items[item_name] = item_value
        items_display_names[item_name] = item_display_name
        item_values.add(item_value)
    else:
      raise ValueError(
        "wrong number of tuple elements in items - must be only 2- "
        "or only 3-element tuples")
    
    return items, items_display_names, item_values
  
  def _get_empty_value(self, empty_value_name):
    if empty_value_name is not None:
      if empty_value_name in self._items:
        return self._items[empty_value_name]
      else:
        raise ValueError(
          "invalid identifier for the empty value; must be one of {}".format(
            list(self._items)))
    else:
      return None


class StringSetting(Setting):
  """
  This class can be used for string settings.
  
  Allowed GIMP PDB types:
  
  * `SettingPdbTypes.string`
  
  Default value: `""`
  """
  
  _ALLOWED_PDB_TYPES = [SettingPdbTypes.string]
  _ALLOWED_GUI_TYPES = [SettingGuiTypes.text_entry]
  _DEFAULT_DEFAULT_VALUE = ""
  
  def set_value(self, value):
    if isinstance(value, bytes):
      value = value.decode(pgconstants.GIMP_CHARACTER_ENCODING)
    
    super().set_value(value)


class ImageSetting(Setting):
  """
  This setting class can be used for `gimp.Image` objects.
  
  Allowed GIMP PDB types:
  
  * `SettingPdbTypes.image`
  
  Empty values:
  
  * `None`
  
  Error messages:
  
  * `"invalid_value"` - The image assigned is invalid.
  """
  
  _ALLOWED_PDB_TYPES = [SettingPdbTypes.image]
  _ALLOWED_GUI_TYPES = [SettingGuiTypes.image_combo_box]
  _EMPTY_VALUES = [None]
  
  def _copy_value(self, value):
    return value
  
  def _init_error_messages(self):
    self.error_messages["invalid_value"] = _("Invalid image.")
  
  def _validate(self, image):
    if not pdb.gimp_image_is_valid(image):
      raise SettingValueError(
        utils_.value_to_str_prefix(image) + self.error_messages["invalid_value"])


class ItemSetting(Setting):
  """
  This setting class can be used for `gimp.Item` objects.
  
  Allowed GIMP PDB types:
  
  * `SettingPdbTypes.item`
  
  Empty values:
  
  * `None`
  
  Error messages:
  
  * `"invalid_value"` - The item assigned is invalid.
  """
  
  _ALLOWED_PDB_TYPES = [SettingPdbTypes.item]
  _ALLOWED_GUI_TYPES = [SettingGuiTypes.item_combo_box]
  _EMPTY_VALUES = [None]
  
  def _copy_value(self, value):
    return value
  
  def _init_error_messages(self):
    self.error_messages["invalid_value"] = _("Invalid item.")
  
  def _validate(self, item):
    if not isinstance(item, gimp.Item):
      raise SettingValueError(
        utils_.value_to_str_prefix(item) + self.error_messages["invalid_value"])


class DrawableSetting(Setting):
  """
  This setting class can be used for `gimp.Drawable` objects.
  
  Allowed GIMP PDB types:
  
  * `SettingPdbTypes.drawable`
  
  Empty values:
  
  * `None`
  
  Error messages:
  
  * `"invalid_value"` - The drawable assigned is invalid.
  """
  
  _ALLOWED_PDB_TYPES = [SettingPdbTypes.drawable]
  _ALLOWED_GUI_TYPES = [SettingGuiTypes.drawable_combo_box]
  _EMPTY_VALUES = [None]
  
  def _copy_value(self, value):
    return value
    
  def _init_error_messages(self):
    self.error_messages["invalid_value"] = _("Invalid drawable.")
  
  def _validate(self, drawable):
    if not pdb.gimp_item_is_drawable(drawable):
      raise SettingValueError(
        utils_.value_to_str_prefix(drawable) + self.error_messages["invalid_value"])


class LayerSetting(Setting):
  """
  This setting class can be used for `gimp.Layer` or `gimp.GroupLayer` objects.
  
  Allowed GIMP PDB types:
  
  * `SettingPdbTypes.layer`
  
  Empty values:
  
  * `None`
  
  Error messages:
  
  * `"invalid_value"` - The layer assigned is invalid.
  """
  
  _ALLOWED_PDB_TYPES = [SettingPdbTypes.layer]
  _ALLOWED_GUI_TYPES = [SettingGuiTypes.layer_combo_box]
  _EMPTY_VALUES = [None]
  
  def _copy_value(self, value):
    return value
  
  def _init_error_messages(self):
    self.error_messages["invalid_value"] = _("Invalid layer.")
  
  def _validate(self, layer):
    if not pdb.gimp_item_is_layer(layer):
      raise SettingValueError(
        utils_.value_to_str_prefix(layer) + self.error_messages["invalid_value"])


class ChannelSetting(Setting):
  """
  This setting class can be used for `gimp.Channel` objects.
  
  Allowed GIMP PDB types:
  
  * `SettingPdbTypes.channel`
  
  Empty values:
  
  * `None`
  
  Error messages:
  
  * `"invalid_value"` - The channel assigned is invalid.
  """
  
  _ALLOWED_PDB_TYPES = [SettingPdbTypes.channel]
  _ALLOWED_GUI_TYPES = [SettingGuiTypes.channel_combo_box]
  _EMPTY_VALUES = [None]
  
  def _copy_value(self, value):
    return value
  
  def _init_error_messages(self):
    self.error_messages["invalid_value"] = _("Invalid channel.")
  
  def _validate(self, channel):
    if not pdb.gimp_item_is_channel(channel):
      raise SettingValueError(
        utils_.value_to_str_prefix(channel) + self.error_messages["invalid_value"])


class SelectionSetting(ChannelSetting):
  """
  This setting class can be used to store the current selection. Selection in
  GIMP is internally represented as a `gimp.Channel` object. Unlike
  `ChannelSetting`, this setting does not support GUI (there is no need for
  GUI).
  
  Allowed GIMP PDB types:
  
  * `SettingPdbTypes.selection`
  
  Empty values:
  
  * `None`
  
  Error messages:
  
  * `"invalid_value"` - The channel assigned is invalid.
  """
  
  _ALLOWED_PDB_TYPES = [SettingPdbTypes.selection]
  _ALLOWED_GUI_TYPES = []


class VectorsSetting(Setting):
  """
  This setting class can be used for `gimp.Vectors` objects.
  
  Allowed GIMP PDB types:
  
  * `SettingPdbTypes.vectors` (default)
  * `SettingPdbTypes.path` (alias to `SettingPdbTypes.vectors`)
  
  Empty values:
  
  * `None`
  
  Error messages:
  
  * `"invalid_value"` - The vectors instance assigned is invalid.
  """
  
  _ALLOWED_PDB_TYPES = [SettingPdbTypes.vectors, SettingPdbTypes.path]
  _ALLOWED_GUI_TYPES = [SettingGuiTypes.vectors_combo_box]
  _EMPTY_VALUES = [None]
  
  def _copy_value(self, value):
    return value
  
  def _init_error_messages(self):
    self.error_messages["invalid_value"] = _("Invalid vectors.")
  
  def _validate(self, vectors):
    if not pdb.gimp_item_is_vectors(vectors):
      raise SettingValueError(
        utils_.value_to_str_prefix(vectors) + self.error_messages["invalid_value"])


class ColorSetting(Setting):
  """
  This setting class can be used for `gimpcolor.RGB` objects.
  
  Allowed GIMP PDB types:
  
  * `SettingPdbTypes.color`
  
  Default value: `gimpcolor.RGB` instance with black color (`(0, 0, 0)`).
  
  Error messages:
  
  * `"invalid_value"` - The color assigned is invalid.
  """
  
  _ALLOWED_PDB_TYPES = [SettingPdbTypes.color]
  _ALLOWED_GUI_TYPES = [SettingGuiTypes.color_button]
  # Create default value dynamically to avoid potential errors on GIMP startup.
  _DEFAULT_DEFAULT_VALUE = lambda self: gimpcolor.RGB(0, 0, 0)
  
  def _init_error_messages(self):
    self.error_messages["invalid_value"] = _("Invalid color.")
  
  def _validate(self, color):
    if not isinstance(color, gimpcolor.RGB):
      raise SettingValueError(
        utils_.value_to_str_prefix(color) + self.error_messages["invalid_value"])


class DisplaySetting(Setting):
  """
  This class can be used for `gimp.Display` objects.
  
  Allowed GIMP PDB types:
  
  * `SettingPdbTypes.display`
  
  Error messages:
  
  * `"invalid_value"` - The display assigned is invalid.
  
  Empty values:
  
  * `None`
  """
  
  _ALLOWED_PDB_TYPES = [SettingPdbTypes.display]
  _ALLOWED_GUI_TYPES = [SettingGuiTypes.display_spin_button]
  _EMPTY_VALUES = [None]
  
  def _copy_value(self, value):
    return value
  
  def _init_error_messages(self):
    self.error_messages["invalid_value"] = _("Invalid display.")
  
  def _validate(self, display):
    if not pdb.gimp_display_is_valid(display):
      raise SettingValueError(
        utils_.value_to_str_prefix(display) + self.error_messages["invalid_value"])


class ParasiteSetting(Setting):
  """
  This setting class can be used for `gimp.Parasite` objects.
  
  Allowed GIMP PDB types:
  
  * `SettingPdbTypes.parasite`
  
  Default value: `gimp.Parasite` instance whose name is equal to the setting
  name, all flags are disabled (i.e. equal to 0) and data are empty (`""`).
  
  Error messages:
  
  * `"invalid_value"` - The value is not a `gimp.Parasite` instance.
  """
  
  _ALLOWED_PDB_TYPES = [SettingPdbTypes.parasite]
  _ALLOWED_GUI_TYPES = [SettingGuiTypes.parasite_box]
  _DEFAULT_DEFAULT_VALUE = lambda self: gimp.Parasite(self.name, 0, "")
  
  def _copy_value(self, value):
    return value
  
  def _init_error_messages(self):
    self.error_messages["invalid_value"] = _("Invalid parasite.")
  
  def _validate(self, parasite):
    if not isinstance(parasite, gimp.Parasite):
      raise SettingValueError(
        utils_.value_to_str_prefix(parasite) + self.error_messages["invalid_value"])


class PdbStatusSetting(EnumSetting):
  """
  This class is an `EnumSetting` subclass with fixed items - exit statuses of
  GIMP PDB procedures.
  
  Allowed GIMP PDB types:
  
  * `SettingPdbTypes.pdb_status` (default)
  * `SettingPdbTypes.int32`
  * `SettingPdbTypes.int16`
  * `SettingPdbTypes.int8`
  """
  
  _ALLOWED_PDB_TYPES = [
    SettingPdbTypes.pdb_status,
    SettingPdbTypes.int32,
    SettingPdbTypes.int16,
    SettingPdbTypes.int8]
  _ALLOWED_GUI_TYPES = [SettingGuiTypes.combo_box]
  
  def __init__(self, name, **kwargs):
    self._pdb_statuses = [
      ("PDB_EXECUTION_ERROR", "PDB_EXECUTION_ERROR", gimpenums.PDB_EXECUTION_ERROR),
      ("PDB_CALLING_ERROR", "PDB_CALLING_ERROR", gimpenums.PDB_CALLING_ERROR),
      ("PDB_PASS_THROUGH", "PDB_PASS_THROUGH", gimpenums.PDB_PASS_THROUGH),
      ("PDB_SUCCESS", "PDB_SUCCESS", gimpenums.PDB_SUCCESS),
      ("PDB_CANCEL", "PDB_CANCEL", gimpenums.PDB_CANCEL)]
    
    super().__init__(name, self._pdb_statuses, empty_value=None, **kwargs)


class ValidatableStringSetting(future.utils.with_metaclass(abc.ABCMeta, StringSetting)):
  """
  This class is an abstract class for string settings which are meant to be
  validated with one of the `path.StringValidator` subclasses.
  
  To determine whether the string is valid, `is_valid()` from the corresponding
  subclass is called.
  
  Allowed GIMP PDB types:
  
  * `SettingPdbTypes.string`
  
  Error messages:
  
  This class contains empty messages for error statuses from the specified
  `path.StringValidator` subclass. Normally, if the value (string) assigned is
  invalid, status messages returned from `is_valid()` are used. If desired, you
  may fill the error messages with custom messages which override the status
  messages from the method. See `path.FileValidatorErrorStatuses` for available
  error statuses.
  """
  
  def __init__(self, name, string_validator, **kwargs):
    """
    Additional parameters:
    
    * `string_validator` - `path.StringValidator` subclass used to validate the
      value assigned to this object.
    """
    self._string_validator = string_validator
    
    if "default_value" in kwargs and isinstance(kwargs["default_value"], bytes):
      kwargs["default_value"] = (
        kwargs["default_value"].decode(pgconstants.GIMP_CHARACTER_ENCODING))
    
    super().__init__(name, **kwargs)
  
  def _init_error_messages(self):
    for status in pgpath.FileValidatorErrorStatuses.ERROR_STATUSES:
      self.error_messages[status] = ""
  
  def _validate(self, string_):
    is_valid, status_messages = self._string_validator.is_valid(string_)
    if not is_valid:
      new_status_messages = []
      for status, status_message in status_messages:
        if self.error_messages[status]:
          new_status_messages.append(self.error_messages[status])
        else:
          new_status_messages.append(status_message)
      
      raise SettingValueError(
        utils_.value_to_str_prefix(string_)
        + "\n".join([message for message in new_status_messages]))
  

class FileExtensionSetting(ValidatableStringSetting):
  """
  This setting class can be used for file extensions.
  
  The `path.FileExtensionValidator` subclass is used to determine whether the
  file extension is valid.
  
  Allowed GIMP PDB types:
  
  * SettingPdbTypes.string
  
  Empty values:
  
  * `""`
  """
  
  _ALLOWED_GUI_TYPES = [SettingGuiTypes.text_entry]
  _EMPTY_VALUES = [""]
  
  def __init__(self, name, **kwargs):
    super().__init__(name, pgpath.FileExtensionValidator, **kwargs)
  

class DirpathSetting(ValidatableStringSetting):
  """
  This setting class can be used for directory paths.
  
  The `path.DirpathValidator` subclass is used to determine whether the
  directory path is valid.
  
  Allowed GIMP PDB types:
  
  * SettingPdbTypes.string
  
  Empty values:
  
  * `None`
  * `""`
  """
  
  _ALLOWED_GUI_TYPES = [SettingGuiTypes.folder_chooser]
  _EMPTY_VALUES = [None, ""]
  
  def __init__(self, name, **kwargs):
    super().__init__(name, pgpath.DirpathValidator, **kwargs)


class BrushSetting(Setting):
  """
  This setting class can be used for brushes. Each brush is represented by a
  tuple `(brush name: string, opacity: float, spacing: int, layer mode: int)`.
  
  When calling `set_value`, brush name may be passed without being wrapped in a
  tuple that gets then converted to a tuple of one element containing the brush
  name.
  
  Allowed GIMP PDB types:
  
  * SettingPdbTypes.string
  
  Default value: `()`
  
  Empty values:
  
  * `()`
  
  Error messages:
  
  * `"invalid_value"` - Invalid number of tuple elements.
  """
  
  _ALLOWED_PDB_TYPES = [SettingPdbTypes.string]
  _ALLOWED_GUI_TYPES = [SettingGuiTypes.brush_select_button]
  _DEFAULT_DEFAULT_VALUE = ()
  _EMPTY_VALUES = [()]
  
  _MAX_NUM_TUPLE_ELEMENTS = 4
  
  def set_value(self, value):
    if isinstance(value, types.StringTypes):
      value = (value,)
    
    super().set_value(value)
  
  def _init_error_messages(self):
    self.error_messages["invalid_value"] = _(
      "Invalid number of tuple elements (must be at most {}).".format(
        self._MAX_NUM_TUPLE_ELEMENTS))
  
  def _validate(self, brush_tuple):
    if len(brush_tuple) > self._MAX_NUM_TUPLE_ELEMENTS:
      raise SettingValueError(
        utils_.value_to_str_prefix(brush_tuple) + self.error_messages["invalid_value"])


class FontSetting(Setting):
  """
  This setting class can be used for fonts. Fonts are considered strings.
  
  Allowed GIMP PDB types:
  
  * SettingPdbTypes.string
  
  Default value: `""`
  
  Empty values:
  
  * `""`
  """
  
  _ALLOWED_PDB_TYPES = [SettingPdbTypes.string]
  _ALLOWED_GUI_TYPES = [SettingGuiTypes.font_select_button]
  _DEFAULT_DEFAULT_VALUE = ""
  _EMPTY_VALUES = [""]


class GradientSetting(Setting):
  """
  This setting class can be used for gradients. Gradients are considered
  strings.
  
  Allowed GIMP PDB types:
  
  * SettingPdbTypes.string
  
  Default value: `""`
  
  Empty values:
  
  * `""`
  """
  
  _ALLOWED_PDB_TYPES = [SettingPdbTypes.string]
  _ALLOWED_GUI_TYPES = [SettingGuiTypes.gradient_select_button]
  _DEFAULT_DEFAULT_VALUE = ""
  _EMPTY_VALUES = [""]


class PaletteSetting(Setting):
  """
  This setting class can be used for color palettes. Palettes are considered
  strings.
  
  Allowed GIMP PDB types:
  
  * SettingPdbTypes.string
  
  Default value: `""`
  
  Empty values:
  
  * `""`
  """
  
  _ALLOWED_PDB_TYPES = [SettingPdbTypes.string]
  _ALLOWED_GUI_TYPES = [SettingGuiTypes.palette_select_button]
  _DEFAULT_DEFAULT_VALUE = ""
  _EMPTY_VALUES = [""]


class PatternSetting(Setting):
  """
  This setting class can be used for patterns. Patterns are considered strings.
  
  Allowed GIMP PDB types:
  
  * SettingPdbTypes.string
  
  Default value: `""`
  
  Empty values:
  
  * `""`
  """
  
  _ALLOWED_PDB_TYPES = [SettingPdbTypes.string]
  _ALLOWED_GUI_TYPES = [SettingGuiTypes.pattern_select_button]
  _DEFAULT_DEFAULT_VALUE = ""
  _EMPTY_VALUES = [""]


class ImageIDsAndDirpathsSetting(Setting):
  """
  This setting class stores the list of currently opened images and their import
  directory paths as a dictionary of (image ID, import directory path) pairs.
  The import directory path is None if the image does not have any.
  
  This setting cannot be registered to the PDB as no corresponding PDB type
  exists.
  
  Default value: `{}`
  """
  
  _DEFAULT_DEFAULT_VALUE = {}
  
  @property
  def value(self):
    # Return a copy to prevent modifying the dictionary indirectly by assigning
    # to individual items (`setting.value[image.ID] = dirpath`).
    return dict(self._value)
  
  def update_image_ids_and_dirpaths(self):
    """
    Remove all (image ID, import directory path) pairs for images no longer
    opened in GIMP. Add (image ID, import directory path) pairs for new images
    opened in GIMP.
    """
    current_images, current_image_ids = self._get_currently_opened_images()
    self._filter_images_no_longer_opened(current_image_ids)
    self._add_new_opened_images(current_images)
  
  def update_dirpath(self, image_id, dirpath):
    """
    Assign a new directory path to the specified image ID.
    
    If the image ID does not exist in the setting, raise KeyError.
    """
    if image_id not in self._value:
      raise KeyError(image_id)
    
    self._value[image_id] = dirpath
  
  def _get_currently_opened_images(self):
    current_images = gimp.image_list()
    current_image_ids = set([image.ID for image in current_images])
    
    return current_images, current_image_ids
  
  def _filter_images_no_longer_opened(self, current_image_ids):
    self._value = {
      image_id: self._value[image_id] for image_id in self._value
      if image_id in current_image_ids}
  
  def _add_new_opened_images(self, current_images):
    for image in current_images:
      if image.ID not in self._value:
        self._value[image.ID] = self._get_image_import_dirpath(image)
  
  def _get_image_import_dirpath(self, image):
    if image.filename is not None:
      return os.path.dirname(image.filename.decode(pgconstants.GIMP_CHARACTER_ENCODING))
    else:
      return None


class ArraySetting(Setting):
  """
  This setting class can be used for PDB array types.
  
  Values of array settings are tuples whose elements are of the specified
  setting type.
  
  Any setting type can be passed on initialization of the array setting.
  However, only specific setting types can be registered to the GIMP PDB or have
  their own GUI - consult the documentation of individual setting classes for
  more information.
  
  Validation of setting values is performed for each element individually.
  
  Array settings are useful for manipulating PDB array parameters or for
  storing a collection of values of the same type. For more fine-grained control
  (collection of values of different type, different GUI, etc.), use
  `setting.group.Group` instead.
  
  If the `element_type` specified during instantiation has a matching `array_*`
  type in `SettingPdbTypes` (e.g. `float` and `array_float`), then the array
  setting can be registered to the GIMP PDB. To disable registration, pass
  `None` to `pdb_type` during instantiation as one normally would.
  
  Additional attributes:
  
  * `element_type` - Setting type of array elements.
  
  * `min_size` - The minimum array size.
  
  * `max_size` - The maximum array size.
  
  Default value: `()`
  
  Error messages:
  
  * `"invalid_value"` - The value is not a tuple or an iterable container.
  
  * `"negative_min_size"` - `min_size` is negative.
  
  * `"min_size_greater_than_max_size"` - `min_size` is greater than `max_size`.
  
  * `"min_size_greater_than_value_length"` - `min_size` is greater than the
    length of the value.
  
  * `"max_size_less_than_value_length"` - `max_size` is less than the length of
    the value.
  
  * `"delete_below_min_size"` - deleting an element causes the array to have
    fewer than `min_size` elements.
  
  * `"add_above_max_size"` - adding an element causes the array to have more
    than `max_size` elements.
  """
  
  ELEMENT_DEFAULT_VALUE = type(b"DefaultElementValue", (), {})()
  
  _ALLOWED_GUI_TYPES = [SettingGuiTypes.array_box]
  _DEFAULT_DEFAULT_VALUE = ()
  
  _ARRAY_PDB_TYPES = {
    gimpenums.PDB_INT32: gimpenums.PDB_INT32ARRAY,
    gimpenums.PDB_INT16: gimpenums.PDB_INT16ARRAY,
    gimpenums.PDB_INT8: gimpenums.PDB_INT8ARRAY,
    gimpenums.PDB_FLOAT: gimpenums.PDB_FLOATARRAY,
    gimpenums.PDB_STRING: gimpenums.PDB_STRINGARRAY,
    gimpenums.PDB_COLOR: gimpenums.PDB_COLORARRAY,
  }
  
  def __init__(self, name, element_type, min_size=0, max_size=None, **kwargs):
    """
    Additional parameters include all parameters that would be passed to the
    setting class this array is composed of (i.e. array elements). These
    parameters must be prefixed with `"element_"` (e.g.
    `element_default_value`). Required parameters for the basic setting classes
    include:
    * `element_type` - setting type of each array element. Passing
      `ArraySetting` is also possible, allowing to create multidimensional
      arrays. Note that in that case, required parameters for elements of each
      subsequent dimension must be specified and must have an extra `"element_"`
      prefix. For example, for the second dimension of a 2D array,
      `element_element_type` must also be specified.
    * all other required parameters as per individual setting classes.
    
    All parameters prefixed with `"element_"` will be created in the array
    setting as read-only properties. `element_default_value` will always be
    created.
    
    Array-specific additional parameters:
    * `min_size` - minimum array size (0 by default).
    * `max_size` - maximum array size (`None` by default, meaning size is
      unlimited).
    """
    
    self._element_type = element_type
    self._min_size = min_size if min_size is not None else 0
    self._max_size = max_size
    
    self._element_kwargs = {
      key[len("element_"):]: value for key, value in kwargs.items()
      if key.startswith("element_")}
    
    self._reference_element = self._create_reference_element()
    
    if "default_value" not in self._element_kwargs:
      self._element_kwargs["default_value"] = self._reference_element.default_value
    
    for key, value in self._element_kwargs.items():
      pgutils.create_read_only_property(self, "element_" + key, value)
    
    self._elements = []
    
    array_kwargs = {
      key: value for key, value in kwargs.items() if not key.startswith("element_")}
    
    super().__init__(name, **array_kwargs)
  
  @property
  def value(self):
    # This ensures that this property is always up-to-date no matter what events
    # are connected to individual elements.
    self._value = self._get_element_values()
    return self._value
  
  @property
  def element_type(self):
    return self._element_type
  
  @property
  def min_size(self):
    return self._min_size
  
  @property
  def max_size(self):
    return self._max_size
  
  def __getitem__(self, index):
    """
    Return a setting representing the the array element at the specified index.
    """
    return self._elements[index]
  
  def __delitem__(self, index):
    if len(self._elements) == self._min_size:
      raise SettingValueError(
        self.error_messages["delete_below_min_size"].format(self._min_size))
    
    self.invoke_event("before-delete-element", index)
    
    del self._elements[index]
    
    self.invoke_event("after-delete-element")
  
  def __len__(self):
    """
    Return the number of elements of the array.
    """
    return len(self._elements)
  
  def add_element(self, index=None, value=ELEMENT_DEFAULT_VALUE):
    """
    Add a new element with the specified value at the specified index (starting
    from 0).
    
    If `index` is `None`, append the value. If `value` is
    `ELEMENT_DEFAULT_VALUE`, use the default value of the underlying element.
    """
    if len(self._elements) == self._max_size:
      raise SettingValueError(
        self.error_messages["add_above_max_size"].format(self._max_size))
    
    if isinstance(value, type(self.ELEMENT_DEFAULT_VALUE)):
      value = self._reference_element.default_value
    
    self.invoke_event("before-add-element", index, value)
    
    element = self._create_element(value)
    
    if index is None:
      self._elements.append(element)
      insertion_index = -1
    else:
      self._elements.insert(index, element)
      insertion_index = index if index >= 0 else index - 1
    
    self.invoke_event("after-add-element", insertion_index, value)
    
    return element
  
  def reorder_element(self, index, new_index):
    """
    Change the order of an array element at `index` to a new position specified
    by `new_index`. Both indexes start from 0.
    """
    self.invoke_event("before-reorder-element", index)
    
    element = self._elements.pop(index)
  
    if new_index < 0:
      new_index = max(len(self._elements) + new_index + 1, 0)
    
    self._elements.insert(new_index, element)
    
    self.invoke_event("after-reorder-element", index, new_index)
  
  def remove_element(self, index):
    """
    Remove an element at the specified index. This method is an alias to
    `__delitem__`.
    """
    self.__delitem__(index)
  
  def get_elements(self):
    """
    Return a list of array elements in this setting.
    """
    return list(self._elements)
  
  def get_pdb_param(self, length_name=None, length_description=None):
    """
    Return a list of two tuples, describing the length of the array and the
    array itself, as GIMP PDB parameters - PDB type, name and description.
    
    If the underlying `element_type` does not support any PDB type, return
    `None`.
    
    To customize the name and description of the length parameter, pass
    `length_name` and `length_description`, respectively. Passing `None` creates
    the name and description automatically.
    """
    if self.can_be_registered_to_pdb():
      if length_name is None:
        length_name = "{}-length".format(self.name)
      
      if not isinstance(length_name, bytes):
        length_name = length_name.encode(pgconstants.GIMP_CHARACTER_ENCODING)
      
      if length_description is None:
        length_description = _("Number of elements in '{}'").format(self.name)
      
      if not isinstance(length_description, bytes):
        length_description = length_description.encode(
          pgconstants.GIMP_CHARACTER_ENCODING)
      
      return [
        (SettingPdbTypes.int32, length_name, length_description),
        (self.pdb_type,
         self.name.encode(pgconstants.GIMP_CHARACTER_ENCODING),
         self.description.encode(pgconstants.GIMP_CHARACTER_ENCODING))
      ]
    else:
      return None
  
  def _init_error_messages(self):
    self.error_messages["invalid_value"] = _("Not an array.")
    self.error_messages["negative_min_size"] = _(
      "Minimum array size ({}) cannot be negative.")
    self.error_messages["min_size_greater_than_max_size"] = _(
      "Minimum array size ({}) cannot be greater than maximum array size ({}).")
    self.error_messages["min_size_greater_than_value_length"] = _(
      "Minimum array size ({}) cannot be greater than the length of the value ({}).")
    self.error_messages["max_size_less_than_value_length"] = _(
      "Maximum array size ({}) cannot be less than the length of the value ({}).")
    self.error_messages["delete_below_min_size"] = _(
      "Cannot delete any more elements - array must have at least {} elements.")
    self.error_messages["add_above_max_size"] = _(
      "Cannot add any more elements - array must have at most {} elements.")
  
  def _validate(self, value_array):
    if (not isinstance(value_array, collections.Iterable)
        or isinstance(value_array, types.StringTypes)):
      raise SettingValueError(
        utils_.value_to_str_prefix(value_array) + self.error_messages["invalid_value"])
    
    if self._min_size < 0:
      raise SettingValueError(
        self.error_messages["negative_min_size"].format(self._min_size))
    elif self._max_size is not None and self._min_size > self._max_size:
      raise SettingValueError(
        self.error_messages["min_size_greater_than_max_size"].format(
          self._min_size, self._max_size))
    elif self._min_size > len(value_array):
      raise SettingValueError(
        self.error_messages["min_size_greater_than_value_length"].format(
          self._min_size, len(value_array)))
    elif self._max_size is not None and self._max_size < len(value_array):
      raise SettingValueError(
        self.error_messages["max_size_less_than_value_length"].format(
          self._max_size, len(value_array)))
  
  def _assign_value(self, value_array):
    elements = []
    exceptions = []
    exception_occurred = False
    
    for value in value_array:
      try:
        elements.append(self._create_element(value))
      except SettingValueError as e:
        exceptions.append(e)
        exception_occurred = True
    
    if exception_occurred:
      raise SettingValueError("\n".join([str(e) for e in exceptions]))
    
    self._elements = elements
    self._value = self._get_element_values()
  
  def _apply_gui_value_to_setting(self, value):
    # No assignment takes place to prevent breaking the sync between the array
    # and the GUI.
    self.invoke_event("value-changed")
  
  def _copy_value(self, value):
    self._elements = [self._create_element(element_value) for element_value in value]
    return self._get_element_values()
  
  def _get_default_pdb_type(self):
    if hasattr(self, "_element_pdb_type"):
      if self._element_pdb_type in self._ARRAY_PDB_TYPES:
        return self._ARRAY_PDB_TYPES[self._element_pdb_type]
    elif self._element_type._ALLOWED_PDB_TYPES:
      return self._ARRAY_PDB_TYPES[self._element_type._ALLOWED_PDB_TYPES[0]]
    
    return SettingPdbTypes.none
  
  def _create_reference_element(self):
    """
    Create a reference element to access and validate the element default value.
    """
    # Rely on the underlying element setting type to perform validation of the
    # default value.
    return self._element_type(name="element", **dict(self._element_kwargs, gui_type=None))
  
  def _create_element(self, value):
    kwargs = dict(
      dict(
        name="element",
        display_name="",
        pdb_type=None),
      **self._element_kwargs)
    
    setting = self._element_type(**kwargs)
    setting.set_value(value)
    
    return setting
  
  def _get_element_values(self):
    return tuple(setting.value for setting in self._elements)


class SettingValueError(Exception):
  """
  This exception class is raised when a value assigned to a `Setting` object is
  invalid.
  """
  
  def __init__(self, *args, **kwargs):
    for kwarg in ["setting", "settings", "messages"]:
      setattr(self, kwarg, kwargs.pop(kwarg, None))
    
    super().__init__(*args, **kwargs)


class SettingDefaultValueError(SettingValueError):
  """
  This exception class is raised when the default value specified during the
  `Setting` object initialization is invalid.
  """
  
  pass


class SettingTypes(object):
  """
  This enum maps `Setting` classes to more human-readable names.
  """
  
  generic = Setting
  integer = IntSetting
  float = FloatSetting
  boolean = BoolSetting
  enumerated = EnumSetting
  string = StringSetting
  
  image = ImageSetting
  item = ItemSetting
  drawable = DrawableSetting
  layer = LayerSetting
  channel = ChannelSetting
  selection = SelectionSetting
  vectors = VectorsSetting
  path = vectors
  
  color = ColorSetting
  parasite = ParasiteSetting
  display = DisplaySetting
  pdb_status = PdbStatusSetting
  
  file_extension = FileExtensionSetting
  directory = DirpathSetting
  
  brush = BrushSetting
  font = FontSetting
  gradient = GradientSetting
  palette = PaletteSetting
  pattern = PatternSetting
  
  image_IDs_and_directories = ImageIDsAndDirpathsSetting
  
  array = ArraySetting


PDB_TYPES_TO_SETTING_TYPES_MAP = {
  gimpenums.PDB_INT32: IntSetting,
  gimpenums.PDB_INT16: IntSetting,
  gimpenums.PDB_INT8: IntSetting,
  gimpenums.PDB_FLOAT: FloatSetting,
  gimpenums.PDB_STRING: StringSetting,
  
  gimpenums.PDB_IMAGE: ImageSetting,
  gimpenums.PDB_ITEM: ItemSetting,
  gimpenums.PDB_DRAWABLE: DrawableSetting,
  gimpenums.PDB_LAYER: LayerSetting,
  gimpenums.PDB_CHANNEL: ChannelSetting,
  gimpenums.PDB_SELECTION: SelectionSetting,
  gimpenums.PDB_VECTORS: VectorsSetting,
  
  gimpenums.PDB_COLOR: ColorSetting,
  gimpenums.PDB_PARASITE: ParasiteSetting,
  gimpenums.PDB_DISPLAY: DisplaySetting,
  gimpenums.PDB_STATUS: PdbStatusSetting,
  
  gimpenums.PDB_INT32ARRAY: {"type": ArraySetting, "element_type": IntSetting},
  gimpenums.PDB_INT16ARRAY: {"type": ArraySetting, "element_type": IntSetting},
  gimpenums.PDB_INT8ARRAY: {"type": ArraySetting, "element_type": IntSetting},
  gimpenums.PDB_FLOATARRAY: {"type": ArraySetting, "element_type": FloatSetting},
  gimpenums.PDB_STRINGARRAY: {"type": ArraySetting, "element_type": StringSetting},
  gimpenums.PDB_COLORARRAY: {"type": ArraySetting, "element_type": ColorSetting},
}
