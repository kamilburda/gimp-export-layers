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
This module provides stubs primarily to be used in the `test_pgsetting` module.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

from .. import pgsetting
from .. import pgsettingpresenter


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


class SettingPresenterStub(pgsettingpresenter.SettingPresenter):
  
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


class SettingPresenterWithValueChangedSignalStub(SettingPresenterStub):
  
  _VALUE_CHANGED_SIGNAL = "changed"


class SettingPresenterWithoutGuiElementCreationStub(SettingPresenterStub):
  
  def _create_gui_element(self, setting):
    return None


class CheckButtonPresenterStub(SettingPresenterStub):
  
  def _create_gui_element(self, setting):
    return CheckButtonStub(setting.value)


class YesNoToggleButtonPresenterStub(SettingPresenterStub):
  pass


class SettingStub(pgsetting.Setting):
  
  _ALLOWED_EMPTY_VALUES = [""]
  
  def _init_error_messages(self):
    self._error_messages["invalid_value"] = "value cannot be None or an empty string"
  
  def _validate(self, value):
    if value is None or value == "":
      raise pgsetting.SettingValueError(self._error_messages["invalid_value"])


class SettingRegistrableToPdbStub(SettingStub):

  _ALLOWED_PDB_TYPES = [pgsetting.SettingPdbTypes.string]


class SettingWithGuiStub(SettingStub):
  
  _ALLOWED_GUI_TYPES = [
    CheckButtonPresenterStub, SettingPresenterStub,
    SettingPresenterWithValueChangedSignalStub,
    SettingPresenterWithoutGuiElementCreationStub]


def on_file_extension_changed(file_extension, only_visible_layers):
  if file_extension.value == "png":
    only_visible_layers.set_value(False)
    only_visible_layers.gui.set_sensitive(True)
  else:
    only_visible_layers.set_value(True)
    only_visible_layers.gui.set_sensitive(False)


def on_file_extension_changed_with_autocrop(file_extension, autocrop):
  if file_extension.value == "png":
    autocrop.gui.set_visible(True)
  else:
    autocrop.gui.set_visible(False)


def on_autocrop_changed(autocrop, file_extension, file_extension_value="jpg"):
  if autocrop.value:
    file_extension.set_value(file_extension_value)
