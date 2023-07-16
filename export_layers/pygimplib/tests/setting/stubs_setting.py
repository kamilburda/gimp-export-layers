# -*- coding: utf-8 -*-

"""Stubs primarily to be used in the `test_setting` module."""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

from ...setting import presenter as presenter_
from ...setting import settings as settings_


class GuiWidgetStub(object):
  
  def __init__(self, value):
    self.value = value
    self.sensitive = True
    self.visible = True
    
    self._signal = None
    self._event_handler = None
  
  def connect(self, signal, event_handler):
    self._signal = signal
    self._event_handler = event_handler
  
  def disconnect(self):
    self._signal = None
    self._event_handler = None
  
  def set_value(self, value):
    self.value = value
    if self._event_handler is not None:
      self._event_handler()


class CheckButtonStub(GuiWidgetStub):
  pass


class StubPresenter(presenter_.Presenter):
  
  def get_sensitive(self):
    return self._element.sensitive
  
  def set_sensitive(self, sensitive):
    self._element.sensitive = sensitive

  def get_visible(self):
    return self._element.visible
  
  def set_visible(self, visible):
    self._element.visible = visible
  
  def _create_gui_element(self, setting):
    return GuiWidgetStub(setting.value)
  
  def _get_value(self):
    return self._element.value
  
  def _set_value(self, value):
    self._element.value = value
  
  def _connect_value_changed_event(self):
    self._element.connect(self._VALUE_CHANGED_SIGNAL, self._on_value_changed)
  
  def _disconnect_value_changed_event(self):
    self._element.disconnect()


class StubWithValueChangedSignalPresenter(StubPresenter):
  
  _VALUE_CHANGED_SIGNAL = 'changed'


class StubWithoutGuiElementCreationPresenter(StubPresenter):
  
  def _create_gui_element(self, setting):
    return None


class CheckButtonStubPresenter(StubPresenter):
  
  def _create_gui_element(self, setting):
    return CheckButtonStub(setting.value)


class YesNoToggleButtonStubPresenter(StubPresenter):
  pass


class StubSetting(settings_.Setting):
  
  _DEFAULT_DEFAULT_VALUE = 0
  _EMPTY_VALUES = ['']
  
  def _init_error_messages(self):
    self._error_messages['invalid_value'] = 'value cannot be None or an empty string'
  
  def _validate(self, value):
    if value is None or value == '':
      raise settings_.SettingValueError(self._error_messages['invalid_value'])


class StubWithCallableDefaultDefaultValueSetting(StubSetting):
  
  _DEFAULT_DEFAULT_VALUE = lambda self: '_' + self._name


class StubRegistrableToPdbSetting(StubSetting):

  _ALLOWED_PDB_TYPES = [settings_.SettingPdbTypes.string]


class StubWithGuiSetting(StubSetting):
  
  _ALLOWED_GUI_TYPES = [
    CheckButtonStubPresenter,
    StubPresenter,
    StubWithValueChangedSignalPresenter,
    StubWithoutGuiElementCreationPresenter]


def on_file_extension_changed(file_extension, flatten):
  if file_extension.value == 'png':
    flatten.set_value(False)
    flatten.gui.set_sensitive(True)
  else:
    flatten.set_value(True)
    flatten.gui.set_sensitive(False)


def on_file_extension_changed_with_use_layer_size(file_extension, use_layer_size):
  if file_extension.value == 'png':
    use_layer_size.gui.set_visible(True)
  else:
    use_layer_size.gui.set_visible(False)


def on_use_layer_size_changed(use_layer_size, file_extension, file_extension_value='jpg'):
  if use_layer_size.value:
    file_extension.set_value(file_extension_value)
