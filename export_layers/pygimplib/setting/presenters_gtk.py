# -*- coding: utf-8 -*-

"""`setting.presenter.Presenter` subclasses for GTK GUI elements."""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import inspect
import sys

import pygtk
pygtk.require('2.0')
import gtk

import gimp
import gimpui

from .. import gui as pggui
from .. import utils as pgutils

from . import presenter as presenter_


class GtkPresenter(presenter_.Presenter):
  """Abstract `Presenter` subclass for GTK GUI elements."""
  
  _ABSTRACT = True
  
  def __init__(self, *args, **kwargs):
    self._event_handler_id = None
    
    presenter_.Presenter.__init__(self, *args, **kwargs)
  
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


class IntSpinButtonPresenter(GtkPresenter):
  """`Presenter` subclass for `gtk.SpinButton` elements.
  
  Value: Integer value of the spin button.
  """
  
  _VALUE_CHANGED_SIGNAL = 'value-changed'
  
  def _create_gui_element(self, setting):
    return _create_spin_button(setting)
  
  def _get_value(self):
    return self._element.get_value_as_int()
  
  def _set_value(self, value):
    self._element.set_value(value)


class FloatSpinButtonPresenter(GtkPresenter):
  """`Presenter` subclass for `gtk.SpinButton` elements.
  
  Value: Floating point value of the spin button.
  """
  
  _VALUE_CHANGED_SIGNAL = 'value-changed'
  
  def _create_gui_element(self, setting):
    return _create_spin_button(setting, digits=1)
  
  def _get_value(self):
    return self._element.get_value()
  
  def _set_value(self, value):
    self._element.set_value(value)


class CheckButtonPresenter(GtkPresenter):
  """`Presenter` subclass for `gtk.CheckButton` elements.
  
  Value: Checked state of the check button (checked/unchecked).
  """
  
  _VALUE_CHANGED_SIGNAL = 'clicked'
  
  def _create_gui_element(self, setting):
    return gtk.CheckButton(setting.display_name, use_underline=False)
  
  def _get_value(self):
    return self._element.get_active()
  
  def _set_value(self, value):
    self._element.set_active(value)


class CheckButtonNoTextPresenter(CheckButtonPresenter):
  """`Presenter` subclass for `gtk.CheckButton` elements without text next to
  the checkbox.
  
  Value: Checked state of the check button (checked/unchecked).
  """
  
  def _create_gui_element(self, setting):
    return gtk.CheckButton(None, use_underline=False)


class CheckButtonLabelPresenter(GtkPresenter):
  """`Presenter` subclass for `gtk.CheckButton` elements.
  
  Value: Label of the check button.
  """
  
  def _get_value(self):
    return pgutils.safe_decode_gtk(self._element.get_label())
  
  def _set_value(self, value):
    self._element.set_label(pgutils.safe_encode_gtk(value))


class CheckMenuItemPresenter(GtkPresenter):
  """`Presenter` subclass for `gtk.CheckMenuItem` elements.
  
  Value: Checked state of the menu item (checked/unchecked).
  """
  
  _VALUE_CHANGED_SIGNAL = 'toggled'
  
  def _create_gui_element(self, setting):
    return gtk.CheckMenuItem(setting.display_name)
  
  def _get_value(self):
    return self._element.get_active()
  
  def _set_value(self, value):
    self._element.set_active(value)


class ExpanderPresenter(GtkPresenter):
  """`Presenter` subclass for `gtk.Expander` elements.
  
  Value: `True` if the expander is expanded, `False` if collapsed.
  """
  
  _VALUE_CHANGED_SIGNAL = 'notify::expanded'
  
  def _create_gui_element(self, setting):
    expander = gtk.Expander(label=setting.display_name)
    expander.set_use_underline(True)
    return expander
  
  def _get_value(self):
    return self._element.get_expanded()
  
  def _set_value(self, value):
    self._element.set_expanded(value)


class ComboBoxPresenter(GtkPresenter):
  """`Presenter` subclass for `gimpui.IntComboBox` elements.
  
  Value: Item selected in the combo box.
  """
  
  _VALUE_CHANGED_SIGNAL = 'changed'
  
  def _create_gui_element(self, setting):
    labels_and_values = setting.get_item_display_names_and_values()
    
    for i in range(0, len(labels_and_values), 2):
      labels_and_values[i] = pgutils.safe_encode_gtk(labels_and_values[i])
    
    return gimpui.IntComboBox(tuple(labels_and_values))
  
  def _get_value(self):
    return self._element.get_active()
  
  def _set_value(self, value):
    self._element.set_active(value)
  

class EntryPresenter(GtkPresenter):
  """`Presenter` subclass for `gtk.Entry` elements.
  
  Value: Text in the entry.
  """
  
  def _create_gui_element(self, setting):
    return gtk.Entry()
  
  def _get_value(self):
    return pgutils.safe_decode_gtk(self._element.get_text())
  
  def _set_value(self, value):
    self._element.set_text(pgutils.safe_encode_gtk(value))
    # Place the cursor at the end of the text entry.
    self._element.set_position(-1)


class ImageComboBoxPresenter(GtkPresenter):
  """`Presenter` subclass for `gimpui.ImageComboBox` elements.
  
  Value: `gimp.Image` selected in the combo box.
  """
  
  _VALUE_CHANGED_SIGNAL = 'changed'
  
  def _create_gui_element(self, setting):
    return gimpui.ImageComboBox()
  
  def _get_value(self):
    return self._element.get_active_image()
  
  def _set_value(self, value):
    """Sets a `gimp.Image` instance to be selected in the combo box.
    
    Passing `None` has no effect.
    """
    if value is not None:
      self._element.set_active_image(value)


class ItemComboBoxPresenter(GtkPresenter):
  """`Presenter` subclass for `gui.GimpItemComboBox` elements.
  
  If the setting references a `gimp.Image`, only drawables from that image will
  be displayed.
  
  Value: `gimp.Item` selected in the combo box.
  """
  
  _VALUE_CHANGED_SIGNAL = 'changed'
  
  def _create_gui_element(self, setting):
    return _create_item_combo_box(pggui.GimpItemComboBox, setting)
  
  def _get_value(self):
    return self._element.get_active_item()
  
  def _set_value(self, value):
    """Sets a `gimp.Item` instance to be selected in the combo box.
    
    Passing `None` has no effect.
    """
    if value is not None:
      self._element.set_active_item(value)


class DrawableComboBoxPresenter(GtkPresenter):
  """`Presenter` subclass for `gimpui.DrawableComboBox` elements.
  
  If the setting references a `gimp.Image`, only drawables from that image will
  be displayed.
  
  Value: `gimp.Drawable` selected in the combo box.
  """
  
  _VALUE_CHANGED_SIGNAL = 'changed'
  
  def _create_gui_element(self, setting):
    return _create_item_combo_box(gimpui.DrawableComboBox, setting)
  
  def _get_value(self):
    return self._element.get_active_drawable()
  
  def _set_value(self, value):
    """Sets a `gimp.Drawable` instance to be selected in the combo box.
    
    Passing `None` has no effect.
    """
    if value is not None:
      self._element.set_active_drawable(value)


class LayerComboBoxPresenter(GtkPresenter):
  """`Presenter` subclass for `gimpui.LayerComboBox` elements.
  
  If the setting references a `gimp.Image`, only layers from that image will be
  displayed.
  
  Value: `gimp.Layer` selected in the combo box.
  """
  
  _VALUE_CHANGED_SIGNAL = 'changed'
  
  def _create_gui_element(self, setting):
    return _create_item_combo_box(gimpui.LayerComboBox, setting)
  
  def _get_value(self):
    return self._element.get_active_layer()
  
  def _set_value(self, value):
    """Sets a `gimp.Layer` instance to be selected in the combo box.
    
    Passing `None` has no effect.
    """
    if value is not None:
      self._element.set_active_layer(value)


class ChannelComboBoxPresenter(GtkPresenter):
  """`Presenter` subclass for `gimpui.ChannelComboBox` elements.
  
  If the setting references a `gimp.Image`, only channels from that image will
  be displayed.
  
  Value: `gimp.Channel` selected in the combo box.
  """
  
  _VALUE_CHANGED_SIGNAL = 'changed'
  
  def _create_gui_element(self, setting):
    return _create_item_combo_box(gimpui.ChannelComboBox, setting)
  
  def _get_value(self):
    return self._element.get_active_channel()
  
  def _set_value(self, value):
    """Sets a `gimp.Channel` instance to be selected in the combo box.
    
    Passing `None` has no effect.
    """
    if value is not None:
      self._element.set_active_channel(value)


class VectorsComboBoxPresenter(GtkPresenter):
  """`Presenter` subclass for `gimpui.VectorsComboBox` elements.
  
  If the setting references a `gimp.Image`, only vectors from that image will
  be displayed.
  
  Value: `gimp.Vectors` selected in the combo box.
  """
  
  _VALUE_CHANGED_SIGNAL = 'changed'
  
  def _create_gui_element(self, setting):
    return _create_item_combo_box(gimpui.VectorsComboBox, setting)
  
  def _get_value(self):
    return self._element.get_active_vectors()
  
  def _set_value(self, value):
    """Sets a `gimp.Vectors` instance to be selected in the combo box.
    
    Passing `None` has no effect.
    """
    if value is not None:
      self._element.set_active_vectors(value)
  

class ColorButtonPresenter(GtkPresenter):
  """`Presenter` subclass for `gimpui.ColorButton` elements.
  
  Value: `gimpcolor.RGB` instance representing color in RGB.
  """
  
  _VALUE_CHANGED_SIGNAL = 'color-changed'
  
  def _create_gui_element(self, setting):
    return gimpui.ColorButton(
      setting.display_name, 100, 20, setting.value, gimpui.COLOR_AREA_FLAT)
  
  def _get_value(self):
    return self._element.get_color()
  
  def _set_value(self, value):
    self._element.set_color(value)


class ParasiteBoxPresenter(GtkPresenter):
  """`Presenter` subclass for `gui.ParasiteBox` elements.
  
  Value: `gimp.Parasite` instance.
  """
  
  _VALUE_CHANGED_SIGNAL = 'parasite-changed'
  
  def _create_gui_element(self, setting):
    return pggui.ParasiteBox(setting.value)
  
  def _get_value(self):
    return self._element.get_parasite()
  
  def _set_value(self, value):
    self._element.set_parasite(value)


class DisplaySpinButtonPresenter(GtkPresenter):
  """`Presenter` subclass for `gtk.SpinButton` elements.
  
  Value: `gimp.Display` instance, represented by its integer ID in the spin
  button.
  """
  
  _VALUE_CHANGED_SIGNAL = 'value-changed'
  
  def _create_gui_element(self, setting):
    display_id = getattr(setting.value, 'ID', 0)
    
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


class ExtendedEntryPresenter(GtkPresenter):
  """`Presenter` subclass for `gui.ExtendedEntry` elements.
  
  Value: Text in the entry.
  """
  
  def _get_value(self):
    return pgutils.safe_decode_gtk(self._element.get_text())
  
  def _set_value(self, value):
    self._element.assign_text(pgutils.safe_encode_gtk(value))


class FileExtensionEntryPresenter(ExtendedEntryPresenter):
  """`Presenter` subclass for `gui.FileExtensionEntry` elements.
  
  Value: Text in the entry.
  """
  
  def _create_gui_element(self, setting):
    return pggui.FileExtensionEntry()


class FolderChooserWidgetPresenter(GtkPresenter):
  """`Presenter` subclass for `gtk.FileChooserWidget` elements used as folder
  choosers.
  
  Value: Current folder.
  """
  
  def __init__(self, *args, **kwargs):
    GtkPresenter.__init__(self, *args, **kwargs)
    
    self._location_toggle_button = self._get_location_toggle_button()

  def _create_gui_element(self, setting):
    return gtk.FileChooserWidget(action=gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER)
  
  def _get_value(self):
    if not self._is_location_entry_active():
      dirpath = self._element.get_current_folder()
    else:
      dirpath = self._element.get_filename()
    
    if dirpath is not None:
      return pgutils.safe_decode_gtk(dirpath)
    else:
      return None
  
  def _set_value(self, dirpath):
    self._element.set_current_folder(pgutils.safe_encode_gtk(dirpath))
  
  def _get_location_toggle_button(self):
    return (
      self._element.get_children()[0].get_children()[0].get_children()[0]
      .get_children()[0].get_children()[0])
  
  def _is_location_entry_active(self):
    return self._location_toggle_button.get_active()


class FolderChooserButtonPresenter(GtkPresenter):
  """`Presenter` subclass for `gtk.FileChooserButton` elements used as folder
  choosers.
  
  Value: Current folder.
  """

  def _create_gui_element(self, setting):
    button = gtk.FileChooserButton(title=setting.display_name)
    button.set_action(gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER)
    return button
  
  def _get_value(self):
    dirpath = self._element.get_filename()
    
    if dirpath is not None:
      return pgutils.safe_decode_gtk(dirpath)
    else:
      return None
  
  def _set_value(self, dirpath):
    self._element.set_current_folder(pgutils.safe_encode_gtk(dirpath))


class BrushSelectButtonPresenter(GtkPresenter):
  """`Presenter` subclass for `gimpui.BrushSelectButton` elements.
  
  Value: Tuple representing a brush.
  """
  
  _VALUE_CHANGED_SIGNAL = 'brush-set'
  _BRUSH_PROPERTIES = ['brush-name', 'brush-opacity', 'brush-spacing', 'brush-paint-mode']
  
  def _create_gui_element(self, setting):
    return gimpui.BrushSelectButton(setting.display_name, *setting.value)
  
  def _get_value(self):
    return self._element.get_brush()
  
  def _set_value(self, value):
    for property_name, property_value in zip(self._BRUSH_PROPERTIES, value):
      self._element.set_property(property_name, property_value)


class FontSelectButtonPresenter(GtkPresenter):
  """`Presenter` subclass for `gimpui.FontSelectButton` elements.
  
  Value: String representing a font.
  """
  
  _VALUE_CHANGED_SIGNAL = 'font-set'
  
  def _create_gui_element(self, setting):
    return gimpui.FontSelectButton(setting.display_name, setting.value)
  
  def _get_value(self):
    return self._element.get_font()
  
  def _set_value(self, value):
    self._element.set_font(value)


class GradientSelectButtonPresenter(GtkPresenter):
  """`Presenter` subclass for `gimpui.GradientSelectButton` elements.
  
  Value: String representing a gradient.
  """
  
  _VALUE_CHANGED_SIGNAL = 'gradient-set'
  
  def _create_gui_element(self, setting):
    return gimpui.GradientSelectButton(setting.display_name, setting.value)
  
  def _get_value(self):
    return self._element.get_gradient()
  
  def _set_value(self, value):
    self._element.set_gradient(value)


class PaletteSelectButtonPresenter(GtkPresenter):
  """`Presenter` subclass for `gimpui.PaletteSelectButton` elements.
  
  Value: String representing a color palette.
  """
  
  _VALUE_CHANGED_SIGNAL = 'palette-set'
  
  def _create_gui_element(self, setting):
    return gimpui.PaletteSelectButton(setting.display_name, setting.value)
  
  def _get_value(self):
    return self._element.get_palette()
  
  def _set_value(self, value):
    self._element.set_palette(value)


class PatternSelectButtonPresenter(GtkPresenter):
  """`Presenter` subclass for `gimpui.PatternSelectButton` elements.
  
  Value: String representing a pattern.
  """
  
  _VALUE_CHANGED_SIGNAL = 'pattern-set'
  
  def _create_gui_element(self, setting):
    return gimpui.PatternSelectButton(setting.display_name, setting.value)
  
  def _get_value(self):
    return self._element.get_pattern()
  
  def _set_value(self, value):
    self._element.set_pattern(value)


class ArrayBoxPresenter(GtkPresenter):
  """`Presenter` subclass for `gui.ArrayBox` elements.
  
  Value: Tuple of values of type `element_type` specified in the passed
  `gui.ArraySetting` instance.
  """
  
  _VALUE_CHANGED_SIGNAL = 'array-box-changed'
  _ITEM_CHANGED_SIGNAL = 'array-box-item-changed'
  
  def __init__(self, *args, **kwargs):
    self._item_changed_event_handler_id = None
    self._array_elements_with_events = set()
    
    GtkPresenter.__init__(self, *args, **kwargs)
  
  def update_setting_value(self):
    GtkPresenter.update_setting_value(self)
    
    for array_element in self._setting.get_elements():
      array_element.gui.update_setting_value()
  
  def _connect_value_changed_event(self):
    GtkPresenter._connect_value_changed_event(self)
    
    self._item_changed_event_handler_id = self._element.connect(
      self._ITEM_CHANGED_SIGNAL, self._on_item_changed)
  
  def _disconnect_value_changed_event(self):
    GtkPresenter._disconnect_value_changed_event(self)
    
    self._element.disconnect(self._item_changed_event_handler_id)
    self._item_changed_event_handler_id = None
  
  def _create_gui_element(self, setting):
    def _add_existing_element(array_element_value, index):
      return self._add_array_element(setting[index], array_box)
    
    def _add_new_element(array_element_value, index):
      array_element = setting.add_element(value=array_element_value)
      return self._add_array_element(array_element, array_box)
    
    def _reorder_element(orig_position, new_position):
      setting.reorder_element(orig_position, new_position)
    
    def _remove_element(position):
      self._array_elements_with_events.remove(setting[position])
      del setting[position]
    
    array_box = pggui.ArrayBox(
      setting.element_default_value, setting.min_size, setting.max_size)
    
    array_box.on_add_item = _add_existing_element
    
    for element_index in range(len(setting)):
      array_box.add_item(setting[element_index].value, element_index)
    
    array_box.on_add_item = _add_new_element
    array_box.on_reorder_item = _reorder_element
    array_box.on_remove_item = _remove_element
    
    return array_box
  
  def _get_value(self):
    return tuple(array_element.value for array_element in self._setting.get_elements())
  
  def _set_value(self, value):
    def _add_existing_element(array_element_value, index):
      return self._add_array_element(self._setting[index], self._element)
    
    orig_on_add_item = self._element.on_add_item
    self._element.on_add_item = _add_existing_element
    
    self._element.set_values(value)
    
    self._element.on_add_item = orig_on_add_item
  
  def _on_item_changed(self, *args):
    self._setting_value_synchronizer.apply_gui_value_to_setting(self._get_value())
  
  def _add_array_element(self, array_element, array_box):
    def _on_array_box_item_changed(array_element):
      array_box.emit('array-box-item-changed')
    
    array_element.set_gui()
    
    if array_element not in self._array_elements_with_events:
      array_element.connect_event('value-changed', _on_array_box_item_changed)
      self._array_elements_with_events.add(array_element)
    
    return array_element.gui.element


class WindowPositionPresenter(GtkPresenter):
  """`Presenter` subclass for window or dialog elements
  (`gtk.Window`, `gtk.Dialog`) to get/set its position.
  
  Value: Current position of the window as a tuple with 2 integers.
  """
  
  def _get_value(self):
    return self._element.get_position()
  
  def _set_value(self, value):
    """Sets a new position of the window (i.e. move the window).
    
    The window is not moved if `value` is `None` or empty.
    """
    if value:
      self._element.move(*value)


class WindowSizePresenter(GtkPresenter):
  """`Presenter` subclass for window or dialog elements
  (`gtk.Window`, `gtk.Dialog`) to get/set its size.
  
  Value: Current size of the window as a tuple with 2 integers.
  """
  
  def _get_value(self):
    return self._element.get_size()
  
  def _set_value(self, value):
    """Sets a new size of the window.
    
    The window is not resized if `value` is `None` or empty.
    """
    if value:
      self._element.resize(*value)


class PanedPositionPresenter(GtkPresenter):
  """`Presenter` subclass for `gtk.Paned` elements.
  
  Value: Position of the pane.
  """
  
  def _get_value(self):
    return self._element.get_position()
  
  def _set_value(self, value):
    self._element.set_position(value)


def _create_spin_button(setting, digits=0):
  if hasattr(setting, 'min_value') and setting.min_value is not None:
    min_value = setting.min_value
  else:
    min_value = -2**32
  
  if hasattr(setting, 'max_value') and setting.max_value is not None:
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
  if hasattr(setting.value, 'image'):
    def _image_matches_setting_image(image, item, setting_image):
      return image == setting_image
    
    return item_combo_box_type(
      constraint=_image_matches_setting_image, data=setting.value.image)
  else:
    return item_combo_box_type()


__all__ = [
  'GtkPresenter',
]

for name, class_ in inspect.getmembers(sys.modules[__name__], inspect.isclass):
  if issubclass(class_, GtkPresenter) and class_ is not GtkPresenter:
    __all__.append(name)
