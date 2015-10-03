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
This module defines SettingPresenter subclasses for GTK elements.
"""

#===============================================================================

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division

str = unicode

#===============================================================================

import abc

import pygtk

pygtk.require("2.0")

import gtk

import gimp

from . import pgsettingpresenter
from .pggui import IntComboBox
from .pggui import FileExtensionEntry

#===============================================================================

pdb = gimp.pdb

GTK_CHARACTER_ENCODING = "utf-8"

#===============================================================================


class GtkSettingPresenter(pgsettingpresenter.SettingPresenter):
  
  """
  This class is a `SettingPresenter` subclass for GTK GUI elements.
  """
  
  __metaclass__ = abc.ABCMeta
  
  def __init__(self, *args, **kwargs):
    self._event_handler_id = None
    
    super(GtkSettingPresenter, self).__init__(*args, **kwargs)
  
  def get_enabled(self):
    return self._element.get_sensitive()
  
  def set_enabled(self, value):
    self._element.set_sensitive(value)
  
  def get_visible(self):
    return self._element.get_visible()
  
  def set_visible(self, value):
    self._element.set_visible(value)
  
  def _connect_value_changed_event(self):
    self._event_handler_id = self._element.connect(self._VALUE_CHANGED_SIGNAL, self._on_value_changed)
  
  def _disconnect_value_changed_event(self):
    self._element.disconnect(self._event_handler_id)
    self._event_handler_id = None


#-------------------------------------------------------------------------------


class GtkCheckButtonPresenter(GtkSettingPresenter):
  
  """
  This class is a `SettingPresenter` for `gtk.CheckButton` elements.
  
  Value: Checked state of the checkbox (checked/unchecked).
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
    return IntComboBox(setting.get_item_display_names_and_values())
  
  def _get_value(self):
    return self._element.get_active()
  
  def _set_value(self, value):
    self._element.set_active(value)


class GtkEntryPresenter(GtkSettingPresenter):
  
  """
  This class is a `SettingPresenter` for `gtk.Entry` elements (text fields).
  
  Value: Text in the text field.
  """

  def _create_gui_element(self, setting):
    return gtk.Entry()
  
  def _get_value(self):
    return self._element.get_text().decode(GTK_CHARACTER_ENCODING)
  
  def _set_value(self, value):
    self._element.set_text(value.encode(GTK_CHARACTER_ENCODING))
    # Place the cursor at the end of the text entry.
    self._element.set_position(-1)


class FileExtensionEntryPresenter(GtkSettingPresenter):
  
  """
  This class is a `SettingPresenter` for `FileExtensionEntry` (text fields
  containing file extensions).
  
  Value: Text (file extension) in the text field.
  """

  def _create_gui_element(self, setting):
    return FileExtensionEntry()
  
  def _get_value(self):
    return self._element.get_text().decode(GTK_CHARACTER_ENCODING)
  
  def _set_value(self, value):
    self._element.assign_text(value.encode(GTK_CHARACTER_ENCODING))


class GtkFolderChooserPresenter(GtkSettingPresenter):
  
  """
  This class is a `SettingPresenter` for `gtk.FileChooserWidget` elements
  used as folder choosers.
  
  Value: Current folder.
  """
  
  def __init__(self, *args, **kwargs):
    super(GtkFolderChooserPresenter, self).__init__(*args, **kwargs)
    
    self._location_toggle_button = self._get_location_toggle_button()

  def _create_gui_element(self, setting):
    return gtk.FileChooserWidget(action=gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER)
  
  def _get_value(self):
    if not self._is_location_entry_active():
      folder = self._element.get_current_folder()
    else:
      folder = self._element.get_filename()
    
    if folder is not None:
      return folder.decode(GTK_CHARACTER_ENCODING)
    else:
      return None
  
  def _set_value(self, folder):
    if folder is not None:
      encoded_folder = folder.encode(GTK_CHARACTER_ENCODING)
    else:
      encoded_folder = None
    
    self._element.set_current_folder(encoded_folder)
  
  def _get_location_toggle_button(self):
    return self._element.get_children()[0].get_children()[0].get_children()[0].get_children()[0].get_children()[0]
  
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


class GtkExpanderPresenter(GtkSettingPresenter):
  
  """
  This class is a `SettingPresenter` for `gtk.Expander` elements.
  
  Value: True if the expander is expanded, False if collapsed.
  """
  
  def _get_value(self):
    return self._element.get_expanded()
  
  def _set_value(self, value):
    self._element.set_expanded(value)


#===============================================================================


class SettingGuiTypes(object):
  
  """
  This enum maps `SettingPresenter` classes to more human-readable names.
  """
  
  checkbox = GtkCheckButtonPresenter
  combobox = GimpUiIntComboBoxPresenter
  text_entry = GtkEntryPresenter
  file_extension_entry = FileExtensionEntryPresenter
  folder_chooser = GtkFolderChooserPresenter
  window_position = GtkWindowPositionPresenter
  expander = GtkExpanderPresenter
  
  none = pgsettingpresenter.NullSettingPresenter
  automatic = None
