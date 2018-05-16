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
This module defines classes to keep GUI elements and their associated settings
in sync.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *
import future.utils

import abc

#===============================================================================


class SettingValueSynchronizer(object):
  
  """
  This class allows the `Setting` and `SettingPresenter` classes to keep the
  `Setting` and `SettingPresenter` values in sync.
  """
  
  def __init__(self):
    self.apply_setting_value_to_gui = None
    self.apply_gui_value_to_setting = None


#===============================================================================


class SettingPresenter(future.utils.with_metaclass(abc.ABCMeta, object)):
  
  """
  This class wraps a GUI element (widget, dialog, etc.).
  
  Various GUI elements have different attributes or methods to access their
  properties. This class wraps some of these attributes/methods so that they can
  be accessed with the same name.
  
  Subclasses can wrap any attribute of a GUI element into their `_get_value()`
  and `_set_value()` methods. The value does not have to be a "direct" value,
  e.g. the checked state of a check button, but also e.g. the label of the
  check button.
  
  Attributes:
  
  * `setting (read-only)` - Setting object.
  
  * `element (read-only)` - GUI element object.
  
  * `_VALUE_CHANGED_SIGNAL` - Object that indicates the type of event to
    connect to the GUI element. Once the event is triggered, it assigns the GUI
    element value to the setting value. If this attribute is None, no event can
    be connected.
  """
  
  _VALUE_CHANGED_SIGNAL = None
  
  def __init__(
        self, setting, element=None, setting_value_synchronizer=None,
        old_setting_presenter=None, auto_update_gui_to_setting=True):
    """
    Parameters:
    
    * `element` - A GUI element.
    
      If `element` is None, create a new GUI element automatically. If the
      specific `SettingPresenter` class does not support creating a GUI element,
      pass an existing GUI element.
    
    * `setting_value_synchronizer` - `SettingValueSynchronizer` instance to
      synchronize values between `setting` and this object.
    
    * `old_setting_presenter` - `SettingPresenter` object that was previously
      assigned to `setting` (as the `setting.gui` attribute). The state
      from that `SettingPresenter` object will be copied to this object. If
      `old_setting_presenter` is None, only `setting.value` will be copied to
      this object.
    
    * `auto_update_gui_to_setting` - If True, automatically update the setting
      value if the GUI value is updated. This parameter does not have any effect
      if:
        
        * the `SettingPresenter` class cannot provide automatic GUI-to-setting
          update,
        
        * `old_setting_presenter` is not None and the automatic GUI-to-setting
          update was disabled in that presenter.
    """
    
    self._setting = setting
    self._element = element
    self._setting_value_synchronizer = setting_value_synchronizer
    
    if auto_update_gui_to_setting:
      self._value_changed_signal = self._VALUE_CHANGED_SIGNAL
    else:
      self._value_changed_signal = None
    
    self._setting_value_synchronizer.apply_setting_value_to_gui = (
      self._apply_setting_value_to_gui)
    
    if self._element is None:
      self._element = self._create_gui_element(setting)
      
      gui_element_creation_supported = self._element is not None
      if not gui_element_creation_supported:
        raise ValueError(
          "cannot instantiate class '{0}': attribute 'element' is None "
          "and this class does not support the creation of a GUI element".format(
            type(self).__name__))
    
    copy_state = old_setting_presenter is not None
    if copy_state:
      self._copy_state(old_setting_presenter)
    else:
      self._setting_value_synchronizer.apply_setting_value_to_gui(self._setting.value)
    
    if self._value_changed_signal is not None:
      self._connect_value_changed_event()
  
  @property
  def setting(self):
    return self._setting
  
  @property
  def element(self):
    return self._element
  
  @property
  def gui_update_enabled(self):
    return self._value_changed_signal is not None
  
  @abc.abstractmethod
  def get_enabled(self):
    """
    Return the enabled/disabled state of the GUI element.
    """
    
    pass
  
  @abc.abstractmethod
  def set_enabled(self, enabled):
    """
    Set the enabled/disabled state of the GUI element.
    """
    
    pass
  
  @abc.abstractmethod
  def get_visible(self):
    """
    Return the visible/invisible state of the GUI element.
    """
    
    pass
  
  @abc.abstractmethod
  def set_visible(self, visible):
    """
    Set the visible/invisible state of the GUI element.
    """
    
    pass
  
  def update_setting_value(self):
    """
    Manually assign the GUI element value, entered by the user, to the setting
    value.
    
    This method will not have any effect if this object updates its setting
    value automatically.
    """
    
    # The `is_value_empty` check makes sure that settings with empty values
    # which are not allowed will be properly invalidated.
    if self._value_changed_signal is None or self._setting.is_value_empty():
      self._update_setting_value()
  
  def auto_update_gui_to_setting(self, enabled):
    """
    Enable or disable automatic GUI update.
    
    If `value` is True and the `SettingPresenter` class does not support
    automatic GUI update, `ValueError` is raised.
    """
    
    if enabled and self._VALUE_CHANGED_SIGNAL is None:
      raise ValueError(
        "class '{0}' does not support automatic GUI update".format(type(self).__name__))
    
    if enabled:
      self._value_changed_signal = self._VALUE_CHANGED_SIGNAL
      self._connect_value_changed_event()
    else:
      self._value_changed_signal = None
      self._disconnect_value_changed_event()
  
  def _create_gui_element(self, setting):
    """
    Instantiate and return a new GUI element using the attributes in the
    specified `Setting` instance (e.g. display name as GUI label).
    
    Return None if the `SettingPresenter` subclass does not support GUI element
    creation.
    """
    
    return None
  
  @abc.abstractmethod
  def _get_value(self):
    """
    Return the value of the GUI element.
    """
    
    pass
  
  @abc.abstractmethod
  def _set_value(self, value):
    """
    Set the value of the GUI element.
    
    If the value passed is one of the empty values allowed for the corresponding
    setting and the GUI element cannot handle the value, this method must wrap
    the empty value into a safe value (that the GUI element can handle).
    """
    
    pass
  
  def _copy_state(self, old_setting_presenter):
    self._set_value(old_setting_presenter._get_value())
    self.set_enabled(old_setting_presenter.get_enabled())
    self.set_visible(old_setting_presenter.get_visible())
    
    if not old_setting_presenter.gui_update_enabled:
      self._value_changed_signal = None
  
  def _update_setting_value(self):
    """
    Assign the GUI element value, entered by the user, to the setting value.
    """
    
    self._setting_value_synchronizer.apply_gui_value_to_setting(self._get_value())
  
  @abc.abstractmethod
  def _connect_value_changed_event(self):
    """
    Connect the `_on_value_changed` event handler to the GUI element using the
    `_value_changed_signal` attribute.
    
    Because the way event handlers are connected varies in each GUI framework,
    subclass this class and override this method for the GUI framework you use.
    """
    
    pass
  
  @abc.abstractmethod
  def _disconnect_value_changed_event(self):
    """
    Disconnect the `_on_value_changed` event handler from the GUI element.
    
    Because the way event handlers are disconnected varies in each GUI framework,
    subclass this class and override this method for the GUI framework you use.
    """
    
    pass
  
  def _on_value_changed(self, *args):
    """
    This is an event handler that automatically updates the value of the
    setting. It is triggered when the user changes the value of the GUI element.
    """
    
    self._update_setting_value()
  
  def _apply_setting_value_to_gui(self, value):
    """
    Assign the setting value to the GUI element. Used by the setting when its
    `set_value()` method is called.
    """
    
    self._set_value(value)


#===============================================================================


class NullSettingPresenter(SettingPresenter):
  
  """
  This class acts as an empty `SettingPresenter` object whose methods do nothing.
  
  This class is attached to `Setting` objects with no `SettingPresenter` object
  specified upon its instantiation.
  
  This class also records the GUI state. In case a proper `SettingPresenter`
  object is assigned to the setting, the GUI state is copied over to the new
  object.
  """
  
  # Make `NullSettingPresenter` pretend to update GUI automatically.
  _VALUE_CHANGED_SIGNAL = "null_signal"
  _NULL_GUI_ELEMENT = type(b"NullGuiElement", (), {})()
  
  def __init__(self, setting, element, *args, **kwargs):
    """
    `element` is ignored - its attributes are not read or set.
    """
    
    self._value = None
    self._enabled = True
    self._visible = True
    
    super().__init__(setting, self._NULL_GUI_ELEMENT, *args, **kwargs)
  
  def get_enabled(self):
    return self._enabled
  
  def set_enabled(self, enabled):
    self._enabled = enabled
  
  def get_visible(self):
    return self._visible
  
  def set_visible(self, visible):
    self._visible = visible
  
  def update_setting_value(self):
    pass
  
  def _get_value(self):
    return self._value
  
  def _set_value(self, value):
    self._value = value
  
  def _connect_value_changed_event(self):
    pass
  
  def _disconnect_value_changed_event(self):
    pass
