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
This module defines SettingPresenter subclasses for GTK elements.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *
import future.utils

import abc

import pygtk
pygtk.require("2.0")
import gtk

import gimpui

from . import pgconstants
from . import pgsettingpresenter

#===============================================================================


class GtkSettingPresenter(
        future.utils.with_metaclass(abc.ABCMeta, pgsettingpresenter.SettingPresenter)):
  
  """
  This class is a `SettingPresenter` subclass for GTK GUI elements.
  """
  
  def __init__(self, *args, **kwargs):
    self._event_handler_id = None
    
    super().__init__(*args, **kwargs)
  
  def get_enabled(self):
    return self._element.get_sensitive()
  
  def set_enabled(self, value):
    self._element.set_sensitive(value)
  
  def get_visible(self):
    return self._element.get_visible()
  
  def set_visible(self, value):
    self._element.set_visible(value)
  
  def _connect_value_changed_event(self):
    self._event_handler_id = self._element.connect(
      self._VALUE_CHANGED_SIGNAL, self._on_value_changed)
  
  def _disconnect_value_changed_event(self):
    self._element.disconnect(self._event_handler_id)
    self._event_handler_id = None


#===============================================================================


class GtkCheckButtonPresenter(GtkSettingPresenter):
  
  """
  This class is a `SettingPresenter` for `gtk.CheckButton` elements.
  
  Value: Checked state of the check button (checked/unchecked).
  """
  
  _VALUE_CHANGED_SIGNAL = "clicked"
  
  def _create_gui_element(self, setting):
    return gtk.CheckButton(setting.display_name)
    
  def _get_value(self):
    return self._element.get_active()
  
  def _set_value(self, value):
    self._element.set_active(value)


class GimpUiIntComboBoxPresenter(GtkSettingPresenter):
  
  """
  This class is a `SettingPresenter` for `gimpui.IntComboBox` elements.
  
  Value: Item selected in the combobox.
  """
  
  _VALUE_CHANGED_SIGNAL = "changed"

  def _create_gui_element(self, setting):
    labels_and_values = setting.get_item_display_names_and_values()
    
    for i in range(0, len(labels_and_values), 2):
      labels_and_values[i] = (
        labels_and_values[i].encode(pgconstants.GTK_CHARACTER_ENCODING))
    
    return gimpui.IntComboBox(tuple(labels_and_values))
  
  def _get_value(self):
    return self._element.get_active()
  
  def _set_value(self, value):
    self._element.set_active(value)


class GtkEntryPresenter(GtkSettingPresenter):
  
  """
  This class is a `SettingPresenter` for `gtk.Entry` elements.
  
  Value: Text in the entry.
  """

  def _create_gui_element(self, setting):
    return gtk.Entry()
  
  def _get_value(self):
    return self._element.get_text().decode(pgconstants.GTK_CHARACTER_ENCODING)
  
  def _set_value(self, value):
    self._element.set_text(value.encode(pgconstants.GTK_CHARACTER_ENCODING))
    # Place the cursor at the end of the text entry.
    self._element.set_position(-1)


class ExtendedEntryPresenter(GtkSettingPresenter):
  
  """
  This class is a `SettingPresenter` for `pggui_entries.ExtendedEntry` elements.
  
  Value: Text in the entry.
  """
  
  def _get_value(self):
    return self._element.get_text().decode(pgconstants.GTK_CHARACTER_ENCODING)
  
  def _set_value(self, value):
    self._element.assign_text(value.encode(pgconstants.GTK_CHARACTER_ENCODING))


class GtkFolderChooserPresenter(GtkSettingPresenter):
  
  """
  This class is a `SettingPresenter` for `gtk.FileChooserWidget` elements
  used as folder choosers.
  
  Value: Current folder.
  """
  
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    
    self._location_toggle_button = self._get_location_toggle_button()

  def _create_gui_element(self, setting):
    return gtk.FileChooserWidget(action=gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER)
  
  def _get_value(self):
    if not self._is_location_entry_active():
      dirpath = self._element.get_current_folder()
    else:
      dirpath = self._element.get_filename()
    
    if dirpath is not None:
      return dirpath.decode(pgconstants.GTK_CHARACTER_ENCODING)
    else:
      return None
  
  def _set_value(self, dirpath):
    if dirpath is not None:
      encoded_dirpath = dirpath.encode(pgconstants.GTK_CHARACTER_ENCODING)
    else:
      encoded_dirpath = b""
    
    self._element.set_current_folder(encoded_dirpath)
  
  def _get_location_toggle_button(self):
    return (
      self._element.get_children()[0].get_children()[0].get_children()[0]
      .get_children()[0].get_children()[0])
  
  def _is_location_entry_active(self):
    return self._location_toggle_button.get_active()


class GtkWindowPositionPresenter(GtkSettingPresenter):
  
  """
  This class is a `SettingPresenter` for window or dialog elements
  (`gtk.Window`, `gtk.Dialog`) to get/set its position.
  
  Value: Current position of the window as a tuple with 2 integers.
  """
  
  def _get_value(self):
    return self._element.get_position()
  
  def _set_value(self, value):
    """
    Set new position of the window (i.e. move the window).
    
    Don't move the window if `value` is None or empty.
    """
    
    if value:
      self._element.move(*value)


class GtkWindowSizePresenter(GtkSettingPresenter):
  
  """
  This class is a `SettingPresenter` for window or dialog elements
  (`gtk.Window`, `gtk.Dialog`) to get/set its size.
  
  Value: Current size of the window as a tuple with 2 integers.
  """
  
  def _get_value(self):
    return self._element.get_size()
  
  def _set_value(self, value):
    """
    Set new size of the window.
    
    Don't resize the window if `value` is None or empty.
    """
    
    if value:
      self._element.resize(*value)


class GtkExpanderPresenter(GtkSettingPresenter):
  
  """
  This class is a `SettingPresenter` for `gtk.Expander` elements.
  
  Value: True if the expander is expanded, False if collapsed.
  """
  
  def _get_value(self):
    return self._element.get_expanded()
  
  def _set_value(self, value):
    self._element.set_expanded(value)


class GtkPanedPositionPresenter(GtkSettingPresenter):
  
  """
  This class is a `SettingPresenter` for `gtk.Paned` elements.
  
  Value: Position of the pane.
  """
  
  def _get_value(self):
    return self._element.get_position()
  
  def _set_value(self, value):
    self._element.set_position(value)


class GtkCheckMenuItemPresenter(GtkSettingPresenter):
  
  """
  This class is a `SettingPresenter` for `gtk.CheckMenuItem` elements.
  
  Value: Checked state of the menu item (checked/unchecked).
  """
  
  _VALUE_CHANGED_SIGNAL = "toggled"
  
  def _create_gui_element(self, setting):
    return gtk.CheckMenuItem(setting.display_name)
  
  def _get_value(self):
    return self._element.get_active()
  
  def _set_value(self, value):
    self._element.set_active(value)


#===============================================================================


class SettingGuiTypes(object):
  
  """
  This enum maps `SettingPresenter` classes to more human-readable names.
  """
  
  check_button = GtkCheckButtonPresenter
  combobox = GimpUiIntComboBoxPresenter
  text_entry = GtkEntryPresenter
  extended_entry = ExtendedEntryPresenter
  folder_chooser = GtkFolderChooserPresenter
  window_position = GtkWindowPositionPresenter
  window_size = GtkWindowSizePresenter
  expander = GtkExpanderPresenter
  paned_position = GtkPanedPositionPresenter
  check_menu_item = GtkCheckMenuItemPresenter
  
  automatic = type(b"AutomaticGuiType", (), {})()
  none = pgsettingpresenter.NullSettingPresenter
