#
# This file is part of Export Layers.
#
# Copyright (C) 2013-2015 khalim19 <khalim19@gmail.com>
#
# Export Layers is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Export Layers is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Export Layers.  If not, see <http://www.gnu.org/licenses/>.
#

"""
This module defines the GUI for the plug-in.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

str = unicode

import collections

import pygtk
pygtk.require("2.0")
import gtk

import gimp

pdb = gimp.pdb

from export_layers import pygimplib
from export_layers.pygimplib import constants


#===============================================================================


_drag_type_id_counter = 1


class OperationsBox(object):
  
  _BUTTON_HBOX_SPACING = 6
  
  def __init__(self, label_add_text=None, spacing=0, settings=None, displayed_settings_names=None):
    self.label_add_text = label_add_text
    self._operations_spacing = spacing
    self._settings = collections.OrderedDict([(setting.name, setting) for setting in settings])
    self._displayed_settings_names = displayed_settings_names if displayed_settings_names is not None else []
    
    self._init_gui()
  
  @property
  def widget(self):
    return self._widget
  
  @property
  def displayed_settings(self):
    return self._displayed_settings
  
  @property
  def displayed_settings_names(self):
    return [setting.name for setting in self._displayed_settings]
  
  def _init_gui(self):
    if self.label_add_text is not None:
      self._button_add = gtk.Button()
      button_hbox = gtk.HBox()
      button_hbox.set_spacing(self._BUTTON_HBOX_SPACING)
      button_hbox.pack_start(
        gtk.image_new_from_stock(gtk.STOCK_ADD, gtk.ICON_SIZE_MENU), expand=False, fill=False)
      
      label_add = gtk.Label(self.label_add_text.encode(constants.GTK_CHARACTER_ENCODING))
      label_add.set_use_underline(True)
      button_hbox.pack_start(label_add, expand=False, fill=False)
      
      self._button_add.add(button_hbox)
    else:
      self._button_add = gtk.Button(stock=gtk.STOCK_ADD)
    
    self._button_add.set_relief(gtk.RELIEF_NONE)
    
    self._vbox = gtk.VBox(homogeneous=False)
    self._vbox.set_spacing(self._operations_spacing)
    self._vbox.pack_start(self._button_add, expand=False, fill=False)
    
    self._scrolled_window = gtk.ScrolledWindow()
    self._scrolled_window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    self._scrolled_window.add_with_viewport(self._vbox)
    self._scrolled_window.get_child().set_shadow_type(gtk.SHADOW_NONE)
    
    self._widget = self._scrolled_window
    
    self._init_operations_menu_popup()
    
    self._init_setting_gui_elements_dragging()
    
    for setting_name in self._displayed_settings_names:
      self._add_operation_item(self._settings[setting_name])
    
    self._button_add.connect("clicked", self._on_button_add_clicked)
  
  def _init_operations_menu_popup(self):
    self._menu_items_and_settings = {}
    self._displayed_settings = []
    self._displayed_settings_gui_elements = set()
    self._displayed_operation_items = []
    
    self._operations_menu = gtk.Menu()
    
    for setting in self._settings.values():
      menu_item = gtk.MenuItem(
        label=setting.display_name.encode(constants.GTK_CHARACTER_ENCODING), use_underline=False)
      menu_item.connect("activate", self._on_operations_menu_item_activate)
      self._operations_menu.append(menu_item)
      self._menu_items_and_settings[menu_item] = setting
    
    self._operations_menu.show_all()
  
  def _init_setting_gui_elements_dragging(self):
    # Make sure the drag type is unique for the entire box to prevent drops on
    # other widgets.
    drag_type = self._get_drag_type()
    
    self._last_setting_gui_element_dest_drag = None
    
    for setting in self._settings.values():
      setting.gui.element.connect("drag-data-get", self._on_setting_gui_element_drag_data_get, setting)
      setting.gui.element.drag_source_set(gtk.gdk.BUTTON1_MASK, [(drag_type, 0, 0)], gtk.gdk.ACTION_MOVE)
      
      setting.gui.element.connect("drag-data-received", self._on_setting_gui_element_drag_data_received, setting)
      setting.gui.element.drag_dest_set(gtk.DEST_DEFAULT_ALL, [(drag_type, 0, 0)], gtk.gdk.ACTION_MOVE)
      
      setting.gui.element.connect("drag-motion", self._on_setting_gui_element_drag_motion)
      setting.gui.element.connect("drag-failed", self._on_setting_gui_element_drag_failed)
  
  def _get_drag_type(self):
    global _drag_type_id_counter
    
    drag_type = "{0}_{1}_{2}".format(pygimplib.config.PLUGIN_NAME, self.__class__.__name__, _drag_type_id_counter)
    _drag_type_id_counter += 1
    
    return drag_type
  
  def _on_setting_gui_element_drag_data_get(self, setting_gui_element, drag_context,
                                            selection_data, info, timestamp, setting):
    selection_data.set(selection_data.target, 8, setting.name)
  
  def _on_setting_gui_element_drag_data_received(self, setting_gui_element, drag_context,
                                                 x, y, selection_data, info, timestamp, setting):
    dragged_setting_name = selection_data.data
    if dragged_setting_name not in self._settings:
      return
    
    dragged_setting = self._settings[dragged_setting_name]
    dragged_item_position = self._displayed_settings.index(dragged_setting)
    dragged_operation_item = self._displayed_operation_items[dragged_item_position]
    
    new_position = self._displayed_settings.index(setting)
    
    self._move_operation_item(dragged_operation_item, new_position)
  
  def _on_setting_gui_element_drag_motion(self, setting_gui_element, drag_context, x, y, timestamp):
    self._last_setting_gui_element_dest_drag = setting_gui_element
  
  def _on_setting_gui_element_drag_failed(self, setting_gui_element, drag_context, result):
    if self._last_setting_gui_element_dest_drag is not None:
      self._last_setting_gui_element_dest_drag.drag_unhighlight()
      self._last_setting_gui_element_dest_drag = None
  
  def _on_button_add_clicked(self, button):
    self._operations_menu.popup(None, None, None, 0, 0)
  
  def _on_operations_menu_item_activate(self, menu_item):
    setting = self._menu_items_and_settings[menu_item]
    if setting not in self._displayed_settings:
      self._add_operation_item(setting)
  
  def _on_operation_item_widget_key_press_event(self, widget, event, operation_item):
    if event.state & gtk.gdk.MOD1_MASK:     # Alt key
      key_name = gtk.gdk.keyval_name(event.keyval)
      if key_name in ["Up", "KP_Up"]:
        self._move_operation_item(operation_item, self._get_operation_item_position(operation_item) - 1)
      elif key_name in ["Down", "KP_Down"]:
        self._move_operation_item(operation_item, self._get_operation_item_position(operation_item) + 1)
  
  def _add_operation_item(self, setting):
    operation_item = _OperationItem(setting.gui.element)
    self._vbox.pack_start(operation_item.widget, expand=False, fill=False)
    self._vbox.reorder_child(self._button_add, -1)
    
    operation_item.button_remove.connect(
      "clicked", lambda *args: self._remove_operation_item(operation_item, setting))
    operation_item.widget.connect(
      "key-press-event", self._on_operation_item_widget_key_press_event, operation_item)
    
    self._displayed_settings.append(setting)
    self._displayed_settings_gui_elements.add(setting.gui.element)
    self._displayed_operation_items.append(operation_item)
  
  def _remove_operation_item(self, operation_item, setting):
    operation_item_position = self._get_operation_item_position(operation_item)
    
    if operation_item_position < len(self._displayed_operation_items) - 1:
      self._displayed_operation_items[operation_item_position + 1].setting_gui_element.grab_focus()
    else:
      self._button_add.grab_focus()
    
    self._vbox.remove(operation_item.widget)
    operation_item.remove_setting()
    
    self._displayed_settings.remove(setting)
    self._displayed_settings_gui_elements.remove(setting.gui.element)
    self._displayed_operation_items.remove(operation_item)
  
  def _move_operation_item(self, operation_item, position):
    position = min(max(position, 0), len(self._displayed_operation_items) - 1)
    
    operation_item_position = self._get_operation_item_position(operation_item)
    
    self._displayed_operation_items.pop(operation_item_position)
    self._displayed_operation_items.insert(position, operation_item)
    
    setting = self._displayed_settings.pop(operation_item_position)
    self._displayed_settings.insert(position, setting)
    
    self._vbox.reorder_child(operation_item.widget, position)
  
  def _get_operation_item_position(self, operation_item):
    return self._displayed_operation_items.index(operation_item)


#===============================================================================


class _OperationItem(object):
  
  _BUTTON_REMOVE_PADDING = 3
  
  def __init__(self, setting_gui_element):
    self._setting_gui_element = setting_gui_element
    
    self._hbox = gtk.HBox(homogeneous=False)
    self._hbox.pack_start(self._setting_gui_element, expand=True, fill=True)
    
    self._button_remove = gtk.Button()
    self._button_remove.set_relief(gtk.RELIEF_NONE)
    
    self._icon_remove = gtk.image_new_from_pixbuf(
      self._button_remove.render_icon(gtk.STOCK_CLOSE, gtk.ICON_SIZE_MENU))
    self._icon_remove.show()
    
    self._button_remove.add(self._icon_remove)
    
    self._hbox.pack_start(self._button_remove, expand=False, fill=False, padding=self._BUTTON_REMOVE_PADDING)
    
    self._event_box = gtk.EventBox()
    self._event_box.add(self._hbox)
    
    self._event_box.connect("enter-notify-event", self._on_event_box_enter_notify_event)
    self._event_box.connect("leave-notify-event", self._on_event_box_leave_notify_event)
    
    self._has_button_remove_focus = False
    self._setting_gui_element.connect("focus-in-event", self._on_setting_gui_element_focus_in_event)
    self._setting_gui_element.connect("focus-out-event", self._on_setting_gui_element_focus_out_event)
    self._button_remove.connect("grab-focus", self._on_button_remove_grab_focus)
    self._button_remove.connect("focus-out-event", self._on_button_remove_focus_out_event)
    
    self._is_event_box_allocated_size = False
    self._button_remove_allocation = None
    self._event_box.connect("size-allocate", self._on_event_box_size_allocate)
    self._button_remove.connect("size-allocate", self._on_button_remove_size_allocate)
    
    self._event_box.show_all()
  
  @property
  def widget(self):
    return self._event_box
  
  @property
  def setting_gui_element(self):
    return self._setting_gui_element
  
  @property
  def button_remove(self):
    return self._button_remove
  
  def remove_setting(self):
    self._hbox.remove(self._setting_gui_element)
  
  def _on_event_box_enter_notify_event(self, event_box, event):
    if event.detail not in [gtk.gdk.NOTIFY_INFERIOR, gtk.gdk.NOTIFY_ANCESTOR]:
      self._button_remove.show()
  
  def _on_event_box_leave_notify_event(self, event_box, event):
    if event.detail != gtk.gdk.NOTIFY_INFERIOR:
      self._button_remove.hide()
  
  def _on_setting_gui_element_focus_in_event(self, setting_gui_element, event):
    self._button_remove.show()
  
  def _on_setting_gui_element_focus_out_event(self, setting_gui_element, event):
    if not self._has_button_remove_focus:
      self._button_remove.hide()
  
  def _on_button_remove_grab_focus(self, button_remove):
    self._has_button_remove_focus = True
  
  def _on_button_remove_focus_out_event(self, button_remove, event):
    self._has_button_remove_focus = False
    self._button_remove.hide()
  
  def _on_event_box_size_allocate(self, event_box, allocation):
    if self._is_event_box_allocated_size:
      return
    
    self._is_event_box_allocated_size = True
    
    # Assign enough height to the HBox to make sure it does not resize when showing the button.
    if self._button_remove_allocation.height >= allocation.height:
      self._hbox.set_size_request(-1, allocation.height)
  
  def _on_button_remove_size_allocate(self, button, allocation):
    if self._button_remove_allocation is not None:
      return
    
    self._button_remove_allocation = allocation
    
    self._button_remove.hide()
