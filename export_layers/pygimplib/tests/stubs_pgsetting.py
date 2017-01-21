# -*- coding: utf-8 -*-
#
# This file is part of pygimplib.
#
# Copyright (C) 2014-2016 khalim19 <khalim19@gmail.com>
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

"""
This module provides stubs primarily to be used in the `test_pgsetting` module.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

from .. import pgsetting
from .. import pgsettingpresenter

#===============================================================================


class GuiWidgetStub(object):
  
  def __init__(self, value):
    self.value = value
    self.enabled = True
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
  
  def get_enabled(self):
    return self._element.enabled
  
  def set_enabled(self, value):
    self._element.enabled = value

  def get_visible(self):
    return self._element.visible
  
  def set_visible(self, value):
    self._element.visible = value
  
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


#===============================================================================


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
    only_visible_layers.gui.set_enabled(True)
  else:
    only_visible_layers.set_value(True)
    only_visible_layers.gui.set_enabled(False)


def on_file_extension_changed_with_autocrop(file_extension, autocrop):
  if file_extension.value == "png":
    autocrop.gui.set_visible(True)
  else:
    autocrop.gui.set_visible(False)


def on_autocrop_changed(autocrop, file_extension, file_extension_value="jpg"):
  if autocrop.value:
    file_extension.set_value(file_extension_value)
