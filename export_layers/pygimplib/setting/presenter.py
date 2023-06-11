# -*- coding: utf-8 -*-

"""Classes to keep settings and their associated GUI elements in sync."""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *
import future.utils

import abc

from .. import utils as pgutils

from . import meta as meta_

__all__ = [
  'Presenter',
  'NullPresenter',
]


class SettingValueSynchronizer(object):
  """Helper class allowing `Setting` and `Presenter` instance to keep their
  values in sync.
  """
  
  def __init__(self):
    self.apply_setting_value_to_gui = pgutils.empty_func
    self.apply_gui_value_to_setting = pgutils.empty_func


class Presenter(future.utils.with_metaclass(meta_.PresenterMeta, object)):
  """Wrapper of a GUI element (widget, dialog, etc.) for settings.
  
  Various GUI elements have different attributes or methods to access their
  properties. This class wraps some of these attributes/methods so that they can
  be accessed with the same name.
  
  Subclasses can wrap any attribute of a GUI element into their `_get_value()`
  and `_set_value()` methods. The value does not have to be a 'direct' value,
  e.g. the checked state of a check button, but also e.g. the label of the
  check button.
  
  Instances of this class should not be created directly. Instead, use
  `Setting.gui` to access a setting's `Presenter` instance.
  
  Attributes:
  
  * `setting (read-only)` - Setting object.
  
  * `element (read-only)` - GUI element object.
  
  * `_VALUE_CHANGED_SIGNAL` - Object that indicates the type of event to
    connect to the GUI element. Once the event is triggered, it assigns the GUI
    element value to the setting value. If this attribute is `None`, no event
    can be connected.
  """
  
  _ABSTRACT = True
  
  _VALUE_CHANGED_SIGNAL = None
  
  def __init__(
        self,
        setting,
        element=None,
        setting_value_synchronizer=None,
        old_presenter=None,
        auto_update_gui_to_setting=True):
    """
    Parameters:
    
    * `element` - A GUI element.
      
      If `element` is `None`, create a new GUI element automatically. If the
      specific `Presenter` class does not support creating a GUI element, pass
      an existing GUI element.
    
    * `setting_value_synchronizer` - `SettingValueSynchronizer` instance to
      synchronize values between `setting` and this object.
    
    * `old_presenter` - `Presenter` object that was previously assigned to
      `setting` (as the `setting.gui` attribute). The state from that
      `Presenter` object will be copied to this object. If `old_presenter` is
      `None`, only `setting.value` will be copied to this object.
    
    * `auto_update_gui_to_setting` - If `True`, automatically update the setting
      value if the GUI value is updated. This parameter does not have any effect
      if:
        
        * the `Presenter` class cannot provide automatic GUI-to-setting update,
        
        * `old_presenter` is not `None` and the automatic GUI-to-setting update
          was disabled in that presenter.
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
      
      if self._element is None:
        raise ValueError(
          'cannot instantiate class "{}": attribute "element" is None'
          ' and this class does not support the creation of a GUI element'.format(
            type(self).__name__))
    
    if old_presenter is not None:
      self._copy_state(old_presenter)
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
  def get_sensitive(self):
    """Returns the sensitive state of the GUI element."""
    pass
  
  @abc.abstractmethod
  def set_sensitive(self, sensitive):
    """Sets the sensitive state of the GUI element."""
    pass
  
  @abc.abstractmethod
  def get_visible(self):
    """Returns the visible state of the GUI element."""
    pass
  
  @abc.abstractmethod
  def set_visible(self, visible):
    """Sets the visible state of the GUI element."""
    pass
  
  def update_setting_value(self):
    """Manually assigns the GUI element value, entered by the user, to the
    setting value.
    
    This method will not have any effect if this object updates its setting
    value automatically.
    """
    # The `is_value_empty` check makes sure that settings with empty values
    # which are not allowed will be properly invalidated.
    if self._value_changed_signal is None or self._setting.is_value_empty():
      self._update_setting_value()
  
  def auto_update_gui_to_setting(self, enabled):
    """Enables or disables automatic GUI update.
    
    If `value` is `True` and the `Presenter` class does not support automatic
    GUI update, `ValueError` is raised.
    """
    if enabled and self._VALUE_CHANGED_SIGNAL is None:
      raise ValueError(
        'class "{}" does not support automatic GUI update'.format(type(self).__name__))
    
    if enabled:
      self._value_changed_signal = self._VALUE_CHANGED_SIGNAL
      self._connect_value_changed_event()
    else:
      self._value_changed_signal = None
      self._disconnect_value_changed_event()
  
  def _create_gui_element(self, setting):
    """Instantiates and returns a new GUI element using the attributes in the
    specified `Setting` instance (e.g. display name as GUI label).
    
    `None` is returned if the `Presenter` subclass does not support GUI element
    creation.
    """
    return None
  
  @abc.abstractmethod
  def _get_value(self):
    """Returns the value of the GUI element."""
    pass
  
  @abc.abstractmethod
  def _set_value(self, value):
    """Sets the value of the GUI element.
    
    If the value passed is one of the empty values allowed for the corresponding
    setting and the GUI element cannot handle the value, this method must wrap
    the empty value into a safe value (that the GUI element can handle).
    """
    pass
  
  def _copy_state(self, old_presenter):
    self._set_value(old_presenter._get_value())
    self.set_sensitive(old_presenter.get_sensitive())
    self.set_visible(old_presenter.get_visible())
    
    if not old_presenter.gui_update_enabled:
      self._value_changed_signal = None
  
  def _update_setting_value(self):
    """Assigns the GUI element value, entered by the user, to the setting value.
    """
    self._setting_value_synchronizer.apply_gui_value_to_setting(self._get_value())
  
  @abc.abstractmethod
  def _connect_value_changed_event(self):
    """Connects the `_on_value_changed` event handler to the GUI element using
    the `_value_changed_signal` attribute.
    
    Because the way event handlers are connected varies in each GUI framework,
    subclass this class and override this method for the GUI framework you use.
    """
    pass
  
  @abc.abstractmethod
  def _disconnect_value_changed_event(self):
    """Disconnects the `_on_value_changed` event handler from the GUI element.
    
    Because the way event handlers are disconnected varies in each GUI framework,
    subclass this class and override this method for the GUI framework you use.
    """
    pass
  
  def _on_value_changed(self, *args):
    """Event handler that automatically updates the value of the setting.
    
    The event is triggered when the user changes the value of the GUI element.
    """
    self._update_setting_value()
  
  def _apply_setting_value_to_gui(self, value):
    """Assigns the setting value to the GUI element. Used by the setting when
    its `set_value()` method is called.
    """
    self._set_value(value)


class NullPresenter(Presenter):
  """Empty `Presenter` class whose methods do nothing.
  
  This class is attached to `Setting` objects with no `Presenter` object
  specified upon its instantiation.
  
  This class also records the GUI state. In case a proper `Presenter` instance
  is assigned to the setting, the GUI state is copied over to the new instance.
  """
  
  # Make `NullPresenter` pretend to update GUI automatically.
  _VALUE_CHANGED_SIGNAL = 'null_signal'
  _NULL_GUI_ELEMENT = type(b'NullGuiElement', (), {})()
  
  def __init__(self, setting, element, *args, **kwargs):
    """
    `element` is ignored - its attributes are not read or set.
    """
    self._value = None
    self._sensitive = True
    self._visible = True
    
    Presenter.__init__(self, setting, self._NULL_GUI_ELEMENT, *args, **kwargs)
  
  def get_sensitive(self):
    return self._sensitive
  
  def set_sensitive(self, sensitive):
    self._sensitive = sensitive
  
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
