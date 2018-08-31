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

import gimp
import gimpui

from . import pgconstants
from . import pggui
from . import pgsettingpresenter


class GtkSettingPresenter(
        future.utils.with_metaclass(abc.ABCMeta, pgsettingpresenter.SettingPresenter)):
  """
  This class is a `SettingPresenter` subclass for GTK GUI elements.
  """
  
  def __init__(self, *args, **kwargs):
    self._event_handler_id = None
    
    super().__init__(*args, **kwargs)
  
  def get_sensitive(self):
    return self._element.get_sensitive()
  
  def set_sensitive(self, sensitive):
    self._element.set_sensitive(sensitive)
  
  def get_visible(self):
    return self._element.get_visible()
  
  def set_visible(self, visible):
    self._element.set_visible(visible)
  
  def _connect_value_changed_event(self):
    self._event_handler_id = self._element.connect(
      self._VALUE_CHANGED_SIGNAL, self._on_value_changed)
  
  def _disconnect_value_changed_event(self):
    self._element.disconnect(self._event_handler_id)
    self._event_handler_id = None


class GtkIntSpinButtonPresenter(GtkSettingPresenter):
  """
  This class is a `SettingPresenter` for `gtk.SpinButton` elements.
  
  Value: Integer value of the spin button.
  """
  
  _VALUE_CHANGED_SIGNAL = "value-changed"
  
  def _create_gui_element(self, setting):
    return _create_spin_button(setting)
  
  def _get_value(self):
    return self._element.get_value_as_int()
  
  def _set_value(self, value):
    self._element.set_value(value)


class GtkFloatSpinButtonPresenter(GtkSettingPresenter):
  """
  This class is a `SettingPresenter` for `gtk.SpinButton` elements.
  
  Value: Floating point value of the spin button.
  """
  
  _VALUE_CHANGED_SIGNAL = "value-changed"
  
  def _create_gui_element(self, setting):
    return _create_spin_button(setting, digits=1)
  
  def _get_value(self):
    return self._element.get_value()
  
  def _set_value(self, value):
    self._element.set_value(value)


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


class GtkCheckButtonLabelPresenter(GtkSettingPresenter):
  """
  This class is a `SettingPresenter` for `gtk.CheckButton` elements.
  
  Value: Label of the check button.
  """
  
  def _get_value(self):
    return self._element.get_label()
  
  def _set_value(self, value):
    self._element.set_label(value)


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


class GimpUiIntComboBoxPresenter(GtkSettingPresenter):
  """
  This class is a `SettingPresenter` for `gimpui.IntComboBox` elements.
  
  Value: Item selected in the combo box.
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


class GimpUiImageComboBoxPresenter(GtkSettingPresenter):
  """
  This class is a `SettingPresenter` for `gimpui.ImageComboBox` elements.
  
  Value: `gimp.Image` selected in the combo box.
  """
  
  _VALUE_CHANGED_SIGNAL = "changed"
  
  def _create_gui_element(self, setting):
    return gimpui.ImageComboBox()
  
  def _get_value(self):
    return self._element.get_active_image()
  
  def _set_value(self, value):
    self._element.set_active_image(value)


class GimpUiDrawableComboBoxPresenter(GtkSettingPresenter):
  """
  This class is a `SettingPresenter` for `gimpui.DrawableComboBox` elements.
  Only drawables from the image referenced by the setting are displayed.
  
  Value: `gimp.Drawable` selected in the combo box.
  """
  
  _VALUE_CHANGED_SIGNAL = "changed"
  
  def _create_gui_element(self, setting):
    return _create_item_combo_box(gimpui.DrawableComboBox, setting)
  
  def _get_value(self):
    return self._element.get_active_drawable()
  
  def _set_value(self, value):
    self._element.set_active_drawable(value)


class GimpUiLayerComboBoxPresenter(GtkSettingPresenter):
  """
  This class is a `SettingPresenter` for `gimpui.LayerComboBox` elements.
  Only layers from the image referenced by the setting are displayed.
  
  Value: `gimp.Layer` selected in the combo box.
  """
  
  _VALUE_CHANGED_SIGNAL = "changed"
  
  def _create_gui_element(self, setting):
    return _create_item_combo_box(gimpui.LayerComboBox, setting)
  
  def _get_value(self):
    return self._element.get_active_layer()
  
  def _set_value(self, value):
    self._element.set_active_layer(value)


class GimpUiChannelComboBoxPresenter(GtkSettingPresenter):
  """
  This class is a `SettingPresenter` for `gimpui.ChannelComboBox` elements.
  Only channels from the image referenced by the setting are displayed.
  
  Value: `gimp.Channel` selected in the combo box.
  """
  
  _VALUE_CHANGED_SIGNAL = "changed"
  
  def _create_gui_element(self, setting):
    return _create_item_combo_box(gimpui.ChannelComboBox, setting)
  
  def _get_value(self):
    return self._element.get_active_channel()
  
  def _set_value(self, value):
    self._element.set_active_channel(value)


class GimpUiVectorsComboBoxPresenter(GtkSettingPresenter):
  """
  This class is a `SettingPresenter` for `gimpui.VectorsComboBox` elements.
  Only instances of vectors (paths) from the image referenced by the setting are
  displayed.
  
  Value: `gimp.Vectors` selected in the combo box.
  """
  
  _VALUE_CHANGED_SIGNAL = "changed"
  
  def _create_gui_element(self, setting):
    return _create_item_combo_box(gimpui.VectorsComboBox, setting)
  
  def _get_value(self):
    return self._element.get_active_vectors()
  
  def _set_value(self, value):
    self._element.set_active_vectors(value)
  

class GimpUiColorButtonPresenter(GtkSettingPresenter):
  """
  This class is a `SettingPresenter` for `gimpui.ColorButton` elements.
  
  Value: `gimpcolor.RGB` instance representing color in RGB.
  """
  
  _VALUE_CHANGED_SIGNAL = "color-changed"
  
  def _create_gui_element(self, setting):
    return gimpui.ColorButton(
      setting.display_name, 100, 20, setting.value, gimpui.COLOR_AREA_FLAT)
  
  def _get_value(self):
    return self._element.get_color()
  
  def _set_value(self, value):
    self._element.set_color(value)


class ParasiteBoxPresenter(GtkSettingPresenter):
  """
  This class is a `SettingPresenter` for `pggui.ParasiteBox` elements.
  
  Value: `gimp.Parasite` instance.
  """
  
  _VALUE_CHANGED_SIGNAL = "parasite-changed"
  
  def _create_gui_element(self, setting):
    return pggui.ParasiteBox(setting.value)
  
  def _get_value(self):
    return self._element.get_parasite()
  
  def _set_value(self, value):
    self._element.set_parasite(value)


class GtkDisplaySpinButtonPresenter(GtkSettingPresenter):
  """
  This class is a `SettingPresenter` for `gtk.SpinButton` elements.
  
  Value: `gimp.Display` instance, represented by its integer ID in the spin
  button.
  """
  
  _VALUE_CHANGED_SIGNAL = "value-changed"
  
  def _create_gui_element(self, setting):
    display_id = getattr(setting.value, "ID", 0)
    
    spin_button = gtk.SpinButton(
      gtk.Adjustment(
        value=display_id,
        lower=0,
        upper=2**32,
        step_incr=1,
        page_incr=10,
      ),
      digits=0)
    
    spin_button.set_numeric(True)
    spin_button.set_value(display_id)
    
    return spin_button
  
  def _get_value(self):
    return gimp._id2display(self._element.get_value_as_int())
  
  def _set_value(self, value):
    self._element.set_value(value.ID)


class ExtendedEntryPresenter(GtkSettingPresenter):
  """
  This class is a `SettingPresenter` for `pggui.ExtendedEntry` elements.
  
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


class GimpUiBrushSelectButtonPresenter(GtkSettingPresenter):
  """
  This class is a `SettingPresenter` for `gimpui.BrushSelectButton` elements.
  
  Value: Tuple representing a brush.
  """
  
  _VALUE_CHANGED_SIGNAL = "brush-set"
  _BRUSH_PROPERTIES = ["brush-name", "brush-opacity", "brush-spacing", "brush-paint-mode"]
  
  def _create_gui_element(self, setting):
    return gimpui.BrushSelectButton(setting.display_name, *setting.value)
  
  def _get_value(self):
    return self._element.get_brush()
  
  def _set_value(self, value):
    for property_name, property_value in zip(self._BRUSH_PROPERTIES, value):
      self._element.set_property(property_name, property_value)


class GimpUiFontSelectButtonPresenter(GtkSettingPresenter):
  """
  This class is a `SettingPresenter` for `gimpui.FontSelectButton` elements.
  
  Value: String representing a font.
  """
  
  _VALUE_CHANGED_SIGNAL = "font-set"
  
  def _create_gui_element(self, setting):
    return gimpui.FontSelectButton(setting.display_name, setting.value)
  
  def _get_value(self):
    return self._element.get_font()
  
  def _set_value(self, value):
    self._element.set_font(value)


class GimpUiGradientSelectButtonPresenter(GtkSettingPresenter):
  """
  This class is a `SettingPresenter` for `gimpui.GradientSelectButton` elements.
  
  Value: String representing a gradient.
  """
  
  _VALUE_CHANGED_SIGNAL = "gradient-set"
  
  def _create_gui_element(self, setting):
    return gimpui.GradientSelectButton(setting.display_name, setting.value)
  
  def _get_value(self):
    return self._element.get_gradient()
  
  def _set_value(self, value):
    self._element.set_gradient(value)


class GimpUiPaletteSelectButtonPresenter(GtkSettingPresenter):
  """
  This class is a `SettingPresenter` for `gimpui.PaletteSelectButton` elements.
  
  Value: String representing a color palette.
  """
  
  _VALUE_CHANGED_SIGNAL = "palette-set"
  
  def _create_gui_element(self, setting):
    return gimpui.PaletteSelectButton(setting.display_name, setting.value)
  
  def _get_value(self):
    return self._element.get_palette()
  
  def _set_value(self, value):
    self._element.set_palette(value)


class GimpUiPatternSelectButtonPresenter(GtkSettingPresenter):
  """
  This class is a `SettingPresenter` for `gimpui.PatternSelectButton` elements.
  
  Value: String representing a pattern.
  """
  
  _VALUE_CHANGED_SIGNAL = "pattern-set"
  
  def _create_gui_element(self, setting):
    return gimpui.PatternSelectButton(setting.display_name, setting.value)
  
  def _get_value(self):
    return self._element.get_pattern()
  
  def _set_value(self, value):
    self._element.set_pattern(value)


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
    
    Do not move the window if `value` is `None` or empty.
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
    
    Do not resize the window if `value` is `None` or empty.
    """
    if value:
      self._element.resize(*value)


class GtkExpanderPresenter(GtkSettingPresenter):
  """
  This class is a `SettingPresenter` for `gtk.Expander` elements.
  
  Value: `True` if the expander is expanded, `False` if collapsed.
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


def _create_spin_button(setting, digits=0):
  if hasattr(setting, "min_value") and setting.min_value is not None:
    min_value = setting.min_value
  else:
    min_value = -2**32
  
  if hasattr(setting, "max_value") and setting.max_value is not None:
    max_value = setting.max_value
  else:
    max_value = 2**32
  
  spin_button = gtk.SpinButton(
    gtk.Adjustment(
      value=setting.value,
      lower=min_value,
      upper=max_value,
      step_incr=1,
      page_incr=10,
    ),
    digits=digits)
  
  spin_button.set_numeric(True)
  spin_button.set_value(setting.value)
  
  return spin_button


def _create_item_combo_box(item_combo_box_type, setting):
  if hasattr(setting.value, "image"):
    def _image_matches_setting_image(image, item, setting_image):
      return image == setting_image
    
    return item_combo_box_type(
      constraint=_image_matches_setting_image, data=setting.value.image)
  else:
    return item_combo_box_type()


class SettingGuiTypes(object):
  """
  This enum maps `SettingPresenter` classes to more human-readable names.
  """
  
  int_spin_button = GtkIntSpinButtonPresenter
  float_spin_button = GtkFloatSpinButtonPresenter
  check_button = GtkCheckButtonPresenter
  check_button_label = GtkCheckButtonLabelPresenter
  check_menu_item = GtkCheckMenuItemPresenter
  combo_box = GimpUiIntComboBoxPresenter
  text_entry = GtkEntryPresenter
  
  image_combo_box = GimpUiImageComboBoxPresenter
  drawable_combo_box = GimpUiDrawableComboBoxPresenter
  layer_combo_box = GimpUiLayerComboBoxPresenter
  channel_combo_box = GimpUiChannelComboBoxPresenter
  vectors_combo_box = GimpUiVectorsComboBoxPresenter
  
  color_button = GimpUiColorButtonPresenter
  parasite_box = ParasiteBoxPresenter
  display_spin_button = GtkDisplaySpinButtonPresenter
  
  extended_entry = ExtendedEntryPresenter
  folder_chooser = GtkFolderChooserPresenter
  
  brush_select_button = GimpUiBrushSelectButtonPresenter
  font_select_button = GimpUiFontSelectButtonPresenter
  gradient_select_button = GimpUiGradientSelectButtonPresenter
  palette_select_button = GimpUiPaletteSelectButtonPresenter
  pattern_select_button = GimpUiPatternSelectButtonPresenter
  
  window_position = GtkWindowPositionPresenter
  window_size = GtkWindowSizePresenter
  expander = GtkExpanderPresenter
  paned_position = GtkPanedPositionPresenter
  
  automatic = type(b"AutomaticGuiType", (), {})()
  none = pgsettingpresenter.NullSettingPresenter
