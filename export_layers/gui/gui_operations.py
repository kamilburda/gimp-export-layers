# -*- coding: utf-8 -*-
#
# This file is part of Export Layers.
#
# Copyright (C) 2013-2018 khalim19 <khalim19@gmail.com>
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
# along with Export Layers.  If not, see <https://www.gnu.org/licenses/>.

"""
This module defines the means to graphically edit a list of operations executed
in the plug-in.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import itertools

import pygtk
pygtk.require("2.0")
import gtk

from export_layers import pygimplib
from export_layers.pygimplib import pgconstants
from export_layers.pygimplib import pgutils

from .. import operations


class OperationBox(object):
  
  _drag_type_id_counter = itertools.count(start=1)
  
  _BUTTON_HBOX_SPACING = 6
  
  def __init__(self, operations_group=None, label_add_text=None, spacing=0):
    self._operations = operations_group
    self._label_add_text = label_add_text
    self._spacing_between_operations = spacing
    
    self.on_add_operation = pgutils.empty_func
    self.on_reorder_operation = pgutils.empty_func
    self.on_remove_operation = pgutils.empty_func
    
    self._menu_items_and_operation_names = {}
    
    self._operation_items = []
    
    self._drag_type_id = self._drag_type_id_counter.next()
    self._last_item_widget_dest_drag = None
    
    self._init_gui()
  
  @property
  def widget(self):
    return self._widget
  
  def _init_gui(self):
    if self._label_add_text is not None:
      self._button_add = gtk.Button()
      button_hbox = gtk.HBox()
      button_hbox.set_spacing(self._BUTTON_HBOX_SPACING)
      button_hbox.pack_start(
        gtk.image_new_from_stock(gtk.STOCK_ADD, gtk.ICON_SIZE_MENU),
        expand=False, fill=False)
      
      label_add = gtk.Label(
        self._label_add_text.encode(pgconstants.GTK_CHARACTER_ENCODING))
      label_add.set_use_underline(True)
      button_hbox.pack_start(label_add, expand=False, fill=False)
      
      self._button_add.add(button_hbox)
    else:
      self._button_add = gtk.Button(stock=gtk.STOCK_ADD)
    
    self._button_add.set_relief(gtk.RELIEF_NONE)
    
    self._vbox = gtk.VBox(homogeneous=False)
    self._vbox.set_spacing(self._spacing_between_operations)
    self._vbox.pack_start(self._button_add, expand=False, fill=False)
    
    self._scrolled_window = gtk.ScrolledWindow()
    self._scrolled_window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    self._scrolled_window.add_with_viewport(self._vbox)
    self._scrolled_window.get_child().set_shadow_type(gtk.SHADOW_NONE)
    
    self._widget = self._scrolled_window
    
    self._operations_menu = gtk.Menu()
    
    self._init_operations_menu_popup()
    
    self._button_add.connect("clicked", self._on_button_add_clicked)
  
  def _init_operations_menu_popup(self):
    for operation in operations.walk(self._operations, subgroup="builtin"):
      self._add_operation_to_menu_popup(operation)
    
    self._operations_menu.show_all()
  
  def _add_operation_to_menu_popup(self, operation):
    menu_item = gtk.MenuItem(
      label=operation["display_name"].value.encode(pgconstants.GTK_CHARACTER_ENCODING),
      use_underline=False)
    menu_item.connect("activate", self._on_operations_menu_item_activate)
    self._operations_menu.append(menu_item)
    self._menu_items_and_operation_names[menu_item] = operation.name
  
  def add_operation_item(self, operation_name):
    operation = self.on_add_operation(self._operations, operation_name)
    operation.initialize_gui()
    
    operation_item = _OperationItem(operation, operation["enabled"].gui.element)
    self._vbox.pack_start(operation_item.widget, expand=False, fill=False)
    self._vbox.reorder_child(self._button_add, -1)
    
    operation_item.button_remove.connect(
      "clicked", lambda *args: self.remove_operation_item(operation_item))
    operation_item.widget.connect(
      "key-press-event", self._on_operation_item_widget_key_press_event, operation_item)
    
    self._connect_drag_events_to_item_widget(
      operation_item, operation, self._get_unique_drag_type())
    
    self._operation_items.append(operation_item)
    
    return operation_item
  
  def _connect_drag_events_to_item_widget(self, operation_item, operation, drag_type):
    operation_enabled = operation["enabled"]
    
    operation_enabled.gui.element.connect(
      "drag-data-get", self._on_item_widget_drag_data_get, operation)
    operation_enabled.gui.element.drag_source_set(
      gtk.gdk.BUTTON1_MASK, [(drag_type, 0, 0)], gtk.gdk.ACTION_MOVE)
    
    operation_enabled.gui.element.connect(
      "drag-data-received", self._on_item_widget_drag_data_received, operation_item)
    operation_enabled.gui.element.drag_dest_set(
      gtk.DEST_DEFAULT_ALL, [(drag_type, 0, 0)], gtk.gdk.ACTION_MOVE)
    
    operation_enabled.gui.element.connect("drag-begin", self._on_item_widget_drag_begin)
    operation_enabled.gui.element.connect("drag-motion", self._on_item_widget_drag_motion)
    operation_enabled.gui.element.connect("drag-failed", self._on_item_widget_drag_failed)
  
  def _get_unique_drag_type(self):
    # Unique drag type for the entire box prevents undesired drops on other
    # widgets.
    return "{}_{}_{}".format(
      pygimplib.config.PLUGIN_NAME,
      self.__class__.__name__,
      self._drag_type_id)
  
  def reorder_operation_item(self, operation_item, position):
    new_position = min(max(position, 0), len(self._operation_items) - 1)
    
    self.on_reorder_operation(
      self._operations, operation_item.operation.name, new_position)
    
    self._operation_items.pop(self._get_operation_item_position(operation_item))
    self._operation_items.insert(new_position, operation_item)
    
    self._vbox.reorder_child(operation_item.widget, new_position)
  
  def remove_operation_item(self, operation_item):
    operation_item_position = self._get_operation_item_position(operation_item)
    
    if operation_item_position < len(self._operation_items) - 1:
      next_item_position = operation_item_position + 1
      self._operation_items[next_item_position].item_widget.grab_focus()
    else:
      self._button_add.grab_focus()
    
    self._vbox.remove(operation_item.widget)
    operation_item.remove_item_widget()
    
    self._operation_items.remove(operation_item)
    
    self.on_remove_operation(self._operations, operation_item.operation.name)
  
  def clear(self):
    for unused_ in range(len(self._vbox.get_children()) - 1):
      self.remove_operation_item(self._operation_items[0])
  
  def _on_item_widget_drag_data_get(
        self, item_widget, drag_context, selection_data, info, timestamp, operation):
    selection_data.set(selection_data.target, 8, operation.get_path(self._operations))
  
  def _on_item_widget_drag_data_received(
        self,
        item_widget,
        drag_context,
        drop_x,
        drop_y,
        selection_data,
        info,
        timestamp,
        operation_item):
    dragged_operation_name = selection_data.data
    
    if dragged_operation_name not in (
         operation.get_path(self._operations)
         for operation in operations.walk(self._operations)):
      return
    
    dragged_operation_item = next(
      (item for item in self._operation_items
       if item.operation == self._operations[dragged_operation_name]),
      None)
    
    if dragged_operation_item is not None:
      new_position = self._get_operation_item_position(operation_item)
      self.reorder_operation_item(dragged_operation_item, new_position)
  
  def _on_item_widget_drag_begin(self, item_widget, drag_context):
    drag_icon_pixbuf = self._get_drag_icon_pixbuf(item_widget)
    if drag_icon_pixbuf is not None:
      drag_context.set_icon_pixbuf(drag_icon_pixbuf, 0, 0)
  
  def _on_item_widget_drag_motion(
        self, item_widget, drag_context, drop_x, drop_y, timestamp):
    self._last_item_widget_dest_drag = item_widget
  
  def _on_item_widget_drag_failed(self, item_widget, drag_context, result):
    if self._last_item_widget_dest_drag is not None:
      self._last_item_widget_dest_drag.drag_unhighlight()
      self._last_item_widget_dest_drag = None
  
  def _on_button_add_clicked(self, button):
    self._operations_menu.popup(None, None, None, 0, 0)
  
  def _on_operations_menu_item_activate(self, menu_item):
    self.add_operation_item(self._menu_items_and_operation_names[menu_item])
  
  def _on_operation_item_widget_key_press_event(self, widget, event, operation_item):
    if event.state & gtk.gdk.MOD1_MASK:     # Alt key
      key_name = gtk.gdk.keyval_name(event.keyval)
      if key_name in ["Up", "KP_Up"]:
        self.reorder_operation_item(
          operation_item, self._get_operation_item_position(operation_item) - 1)
      elif key_name in ["Down", "KP_Down"]:
        self.reorder_operation_item(
          operation_item, self._get_operation_item_position(operation_item) + 1)
  
  def _get_operation_item_position(self, operation_item):
    return self._operation_items.index(operation_item)
  
  def _get_drag_icon_pixbuf(self, widget):
    if widget.get_window() is None:
      return
    
    if self._are_items_partially_hidden_because_of_visible_horizontal_scrollbar():
      return None
    
    self._setup_widget_to_add_border_to_drag_icon(widget)
    
    while gtk.events_pending():
      gtk.main_iteration()
    
    widget_allocation = widget.get_allocation()
    
    pixbuf = gtk.gdk.Pixbuf(
      gtk.gdk.COLORSPACE_RGB,
      False,
      8,
      widget_allocation.width,
      widget_allocation.height)
    
    drag_icon_pixbuf = pixbuf.get_from_drawable(
      widget.get_window(),
      widget.get_colormap(),
      0,
      0,
      0,
      0,
      widget_allocation.width,
      widget_allocation.height)
    
    self._restore_widget_after_creating_drag_icon(widget)
    
    return drag_icon_pixbuf
  
  def _are_items_partially_hidden_because_of_visible_horizontal_scrollbar(self):
    return (
      self._scrolled_window.get_hscrollbar() is not None
      and self._scrolled_window.get_hscrollbar().get_mapped())
  
  def _setup_widget_to_add_border_to_drag_icon(self, widget):
    self._remove_focus_outline(widget)
    self._add_border(widget)
  
  @staticmethod
  def _remove_focus_outline(widget):
    if widget.has_focus():
      widget.set_can_focus(False)
  
  @staticmethod
  def _add_border(widget):
    widget.drag_highlight()
  
  def _restore_widget_after_creating_drag_icon(self, widget):
    self._add_focus_outline(widget)
    self._remove_border(widget)
  
  @staticmethod
  def _add_focus_outline(widget):
    widget.set_can_focus(True)
  
  @staticmethod
  def _remove_border(widget):
    widget.drag_unhighlight()


class _OperationItem(object):
  
  _BUTTONS_PADDING = 3
  
  def __init__(self, operation, item_widget):
    self._operation = operation
    self._item_widget = item_widget
    
    self._hbox = gtk.HBox(homogeneous=False)
    self._hbox.pack_start(self._item_widget, expand=True, fill=True)
    
    self._button_remove = gtk.Button()
    self._button_remove.set_relief(gtk.RELIEF_NONE)
    
    self._icon_remove = gtk.image_new_from_pixbuf(
      self._button_remove.render_icon(gtk.STOCK_CLOSE, gtk.ICON_SIZE_MENU))
    self._icon_remove.show()
    
    self._button_remove.add(self._icon_remove)
    
    self._hbox_buttons = gtk.HBox(homogeneous=False)
    self._hbox_buttons.pack_start(self._button_remove, expand=False, fill=False)
    
    self._event_box_buttons = gtk.EventBox()
    self._event_box_buttons.add(self._hbox_buttons)
    
    self._hbox.pack_start(
      self._event_box_buttons, expand=False, fill=False, padding=self._BUTTONS_PADDING)
    
    self._event_box = gtk.EventBox()
    self._event_box.add(self._hbox)
    
    self._event_box.connect("enter-notify-event", self._on_event_box_enter_notify_event)
    self._event_box.connect("leave-notify-event", self._on_event_box_leave_notify_event)
    
    self._has_button_remove_focus = False
    self._item_widget.connect("focus-in-event", self._on_item_widget_focus_in_event)
    self._item_widget.connect("focus-out-event", self._on_item_widget_focus_out_event)
    self._button_remove.connect("grab-focus", self._on_button_remove_grab_focus)
    self._button_remove.connect("focus-out-event", self._on_button_remove_focus_out_event)
    
    self._is_event_box_allocated_size = False
    self._buttons_allocation = None
    self._event_box.connect("size-allocate", self._on_event_box_size_allocate)
    self._event_box_buttons.connect(
      "size-allocate", self._on_event_box_buttons_size_allocate)
    
    self._event_box.show_all()
  
  @property
  def operation(self):
    return self._operation
  
  @property
  def widget(self):
    return self._event_box
  
  @property
  def item_widget(self):
    return self._item_widget
  
  @property
  def button_remove(self):
    return self._button_remove
  
  def remove_item_widget(self):
    self._hbox.remove(self._item_widget)
  
  def _on_event_box_enter_notify_event(self, event_box, event):
    if event.detail != gtk.gdk.NOTIFY_INFERIOR:
      self._button_remove.show()
  
  def _on_event_box_leave_notify_event(self, event_box, event):
    if event.detail != gtk.gdk.NOTIFY_INFERIOR:
      self._button_remove.hide()
  
  def _on_item_widget_focus_in_event(self, item_widget, event):
    self._button_remove.show()
  
  def _on_item_widget_focus_out_event(self, item_widget, event):
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
    
    # Assign enough height to the HBox to make sure it does not resize when
    # showing buttons.
    if self._buttons_allocation.height >= allocation.height:
      self._hbox.set_size_request(-1, allocation.height)
  
  def _on_event_box_buttons_size_allocate(self, event_box, allocation):
    if self._buttons_allocation is not None:
      return
    
    self._buttons_allocation = allocation
    
    # Make sure the width allocated to the buttons remains the same even if
    # buttons are hidden. This avoids a problem with unreachable buttons when
    # the horizontal scrollbar is displayed.
    self._event_box_buttons.set_size_request(self._buttons_allocation.width, -1)
    
    self._button_remove.hide()
