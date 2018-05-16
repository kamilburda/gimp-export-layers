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
This module defines a custom popup usable for GTK text entries.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import pygtk
pygtk.require("2.0")
import gtk
import gobject

from . import pgutils

#===============================================================================


class EntryPopup(object):
  
  # Implementation of the popup is loosely based on the implementation of
  # `gtk.EntryCompletion`:
  # https://github.com/GNOME/gtk/blob/gtk-2-24/gtk/gtkentrycompletion.c
  
  _BUTTON_MOUSE_LEFT = 1
  
  def __init__(
        self, entry, column_types, rows, width=-1, height=200, max_num_visible_rows=8):
    self._entry = entry
    self._width = width
    self._height = height
    self._max_num_visible_rows = max_num_visible_rows
    
    self.on_assign_from_selected_row = pgutils.create_empty_func(
      return_value=(None, None))
    self.on_assign_last_value = self._entry.assign_text
    self.on_row_left_mouse_button_press = self.assign_from_selected_row
    self.on_entry_left_mouse_button_press_func = pgutils.empty_func
    self.on_entry_key_press_before_show_popup = pgutils.empty_func
    self.on_entry_key_press = (
      lambda key_name, tree_path, stop_event_propagation: stop_event_propagation)
    self.on_entry_after_assign_by_key_press = pgutils.empty_func
    self.on_entry_changed_show_popup_condition = pgutils.create_empty_func(
      return_value=True)
    
    self.trigger_popup = True
    
    self._filter_rows_func = None
    
    self._last_assigned_entry_text = ""
    self._previous_assigned_entry_text_position = None
    self._previous_assigned_entry_text = None
    
    self._show_popup_first_time = True
    
    self._clear_filter = False
    
    self._tree_view_width = None
    
    self._mouse_points_at_entry = False
    self._mouse_points_at_popup = False
    self._mouse_points_at_vscrollbar = False
    
    self._button_press_emission_hook_id = None
    self._toplevel_configure_event_id = None
    
    self._init_gui(column_types, rows)
    
    self._connect_events()
  
  @property
  def rows(self):
    return self._rows
  
  @property
  def rows_filtered(self):
    return self._rows_filtered
  
  @property
  def filter_rows_func(self):
    return self._filter_rows_func
  
  @filter_rows_func.setter
  def filter_rows_func(self, func):
    self._filter_rows_func = func
    if func is not None:
      self._rows_filtered.set_visible_func(self._filter_rows)
    else:
      self._rows_filtered.set_visible_func(pgutils.create_empty_func(return_value=True))
  
  @property
  def popup(self):
    return self._popup
  
  @property
  def tree_view(self):
    return self._tree_view
  
  @property
  def last_assigned_entry_text(self):
    return self._last_assigned_entry_text
  
  def assign_last_value(self):
    self.on_assign_last_value(self._last_assigned_entry_text)
  
  def show(self):
    if not self.is_shown() and len(self._rows_filtered) > 0:
      self._button_press_emission_hook_id = gobject.add_emission_hook(
        self._entry, "button-press-event", self._on_emission_hook_button_press_event)
      
      toplevel_window = self._entry.get_toplevel()
      if isinstance(toplevel_window, gtk.Window):
        toplevel_window.get_group().add_window(self._popup)
        # As soon as the user starts dragging or resizing the window, hide the
        # popup. Button presses on the window decoration cannot be intercepted
        # via "button-press-event" emission hooks, hence this workaround.
        self._toplevel_configure_event_id = toplevel_window.connect(
          "configure-event", self._on_toplevel_configure_event)
      
      self._popup.set_screen(self._entry.get_screen())
      
      self._popup.show()
      
      self._update_position()
      
      if self._show_popup_first_time:
        self.save_last_value()
        self._show_popup_first_time = False
  
  def hide(self):
    if self.is_shown():
      self._popup.hide()
      
      if self._button_press_emission_hook_id is not None:
        gobject.remove_emission_hook(
          self._entry, "button-press-event", self._button_press_emission_hook_id)
      
      if self._toplevel_configure_event_id is not None:
        toplevel_window = self._entry.get_toplevel()
        if isinstance(toplevel_window, gtk.Window):
          toplevel_window.disconnect(self._toplevel_configure_event_id)
  
  def is_shown(self):
    return self._popup.get_mapped()
  
  def resize(self, num_rows):
    """
    Resize the tree view in the popup.
    
    Update the height of the tree view according to the number of rows. If the
    number of rows is 0, hide the entire popup.
    
    Determine the initial width of the tree view based on the items displayed
    in the tree view. For subsequent calls of this function, the width of the
    tree view will remain the same.
    """
    
    columns = self._tree_view.get_columns()
    if columns:
      cell_height = max(column.cell_get_size()[4] for column in columns)
    else:
      cell_height = 0
    
    vertical_spacing = self._tree_view.style_get_property("vertical-separator")
    row_height = cell_height + vertical_spacing
    num_visible_rows = min(num_rows, self._max_num_visible_rows)
    
    if self._tree_view_width is None:
      self._tree_view_width = self._tree_view.get_allocation().width
      if num_rows > self._max_num_visible_rows:
        vscrollbar_width = int(
          self._scrolled_window.get_hadjustment().upper
          - self._scrolled_window.get_hadjustment().page_size)
        self._tree_view_width += vscrollbar_width * 2
    
    self._tree_view.set_size_request(self._tree_view_width, row_height * num_visible_rows)
    
    if num_rows == 0:
      self.hide()
  
  def refresh_row(self, row_path, is_path_filtered=True):
    if not is_path_filtered:
      row_path = self._rows_filtered.convert_child_path_to_path(row_path)
    
    if row_path is not None:
      self._rows_filtered.emit(
        "row-changed", row_path, self._rows_filtered.get_iter(row_path))
  
  def select_row(self, row_num):
    self._tree_view.set_cursor((row_num,))
    # HACK: When the mouse points at the tree view and the user navigates with
    # keys, the selection jumps to the row pointed at. Selecting the row again
    # fixes this.
    self._tree_view.set_cursor((row_num,))
  
  def unselect(self):
    # Select an invalid row so that `get_cursor` returns None on the next call.
    self.tree_view.set_cursor((len(self._rows_filtered),))
    self.tree_view.get_selection().unselect_all()
  
  def assign_from_selected_row(self):
    tree_model, tree_iter = self._tree_view.get_selection().get_selected()
    if tree_iter is None:     # No row is selected
      return None, None
    
    return self.on_assign_from_selected_row(tree_model, tree_iter)
  
  def select_and_assign_row(self, row_num):
    self.select_row(row_num)
    return self.assign_from_selected_row()
  
  def select_and_assign_row_after_key_press(
        self, tree_path, next_row, next_row_if_no_current_selection,
        current_row_before_unselection, row_to_scroll_before_unselection=0):
    """
    After a particular key is pressed, select the row specified by `tree_path`
    and assign the value from the selected row to the entry.
    
    One can pass functions for `next_row` and `current_row_before_unselection`
    parameters if `tree_path` is None and `tree_path` is used to compute these
    parameters.
    """
    
    if tree_path is None:
      position, text = self.select_and_assign_row(next_row_if_no_current_selection)
    else:
      if callable(current_row_before_unselection):
        current_row_before_unselection = current_row_before_unselection(tree_path)
      
      if tree_path[0] == current_row_before_unselection:
        self._tree_view.scroll_to_cell((row_to_scroll_before_unselection,))
        self.unselect()
        self.assign_last_value()
        
        position, text = None, None
      else:
        if callable(next_row):
          next_row = next_row(tree_path)
        position, text = self.select_and_assign_row(next_row)
    
    self.on_entry_after_assign_by_key_press(
      self._previous_assigned_entry_text_position, self._previous_assigned_entry_text,
      position, text)
    
    self._previous_assigned_entry_text_position = position
    self._previous_assigned_entry_text = text
  
  def save_last_value(self):
    self._last_assigned_entry_text = self._entry.get_text()
  
  def _init_gui(self, column_types, rows):
    self._rows = gtk.ListStore(*column_types)
    
    for row in rows:
      self._rows.append(row)
    
    self._rows_filtered = self._rows.filter_new()
    
    self._tree_view = gtk.TreeView(model=self._rows_filtered)
    self._tree_view.set_hover_selection(True)
    self._tree_view.set_headers_visible(False)
    self._tree_view.set_enable_search(False)
    self._tree_view.set_size_request(self._width, self._height)
    
    self._scrolled_window = gtk.ScrolledWindow()
    self._scrolled_window.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
    self._scrolled_window.set_shadow_type(gtk.SHADOW_ETCHED_IN)
    self._scrolled_window.add(self._tree_view)
    
    # HACK: Make sure the height of the tree view can be set properly. Source:
    # https://github.com/GNOME/gtk/blob/gtk-2-24/gtk/gtkentrycompletion.c#L472
    self._scrolled_window.get_vscrollbar().set_size_request(-1, 0)
    
    # Using `gtk.WINDOW_POPUP` prevents the popup from stealing focus from the
    # text entry.
    self._popup = gtk.Window(type=gtk.WINDOW_POPUP)
    self._popup.set_resizable(False)
    self._popup.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_COMBO)
    self._popup.add(self._scrolled_window)
    
    self._scrolled_window.show_all()
  
  def _connect_events(self):
    self._entry.connect("changed", self._on_entry_changed)
    self._entry.connect("button-press-event", self._on_entry_left_mouse_button_press)
    self._entry.connect("key-press-event", self._on_entry_key_press)
    
    self._entry.connect("focus-out-event", self._on_entry_focus_out_event)
    
    self._entry.connect("enter-notify-event", self._on_entry_enter_notify_event)
    self._entry.connect("leave-notify-event", self._on_entry_leave_notify_event)
    
    self._popup.connect("enter-notify-event", self._on_popup_enter_notify_event)
    self._popup.connect("leave-notify-event", self._on_popup_leave_notify_event)
    
    self._scrolled_window.get_vscrollbar().connect(
      "enter-notify-event", self._on_vscrollbar_enter_notify_event)
    self._scrolled_window.get_vscrollbar().connect(
      "leave-notify-event", self._on_vscrollbar_leave_notify_event)
    
    self._tree_view.connect_after("realize", self._on_after_tree_view_realize)
    self._tree_view.connect(
      "button-press-event", self._on_tree_view_left_mouse_button_press)
  
  def _update_position(self):
    entry_absolute_position = self._entry.get_window().get_origin()
    entry_allocation_height = self._entry.get_allocation().height
    self._popup.move(
      entry_absolute_position[0], entry_absolute_position[1] + entry_allocation_height)
  
  def _filter_rows(self, rows, row_iter):
    if self._clear_filter:
      return True
    else:
      return self._filter_rows_func(rows, row_iter)
  
  def _on_entry_key_press(self, entry, event):
    key_name = gtk.gdk.keyval_name(event.keyval)
    
    if (not self.is_shown()
        and key_name in [
          "Up", "KP_Up", "Down", "KP_Down",
          "Page_Up", "KP_Page_Up", "Page_Down", "KP_Page_Down"]):
      self.on_entry_key_press_before_show_popup()
      
      show_popup_first_time = self._show_popup_first_time
      self.show()
      
      # This prevents the navigation keys to select the first row.
      if show_popup_first_time:
        self.unselect()
      
      return True
    
    if self.is_shown():
      tree_path, unused_ = self._tree_view.get_cursor()
      stop_event_propagation = True
      
      if key_name in ["Up", "KP_Up"]:
        self.select_and_assign_row_after_key_press(
          tree_path,
          next_row=lambda tree_path: tree_path[0] - 1,
          next_row_if_no_current_selection=len(self._rows_filtered) - 1,
          current_row_before_unselection=0)
      elif key_name in ["Down", "KP_Down"]:
        self.select_and_assign_row_after_key_press(
          tree_path,
          next_row=lambda tree_path: tree_path[0] + 1,
          next_row_if_no_current_selection=0,
          current_row_before_unselection=len(self._rows_filtered) - 1)
      elif key_name in ["Page_Up", "KP_Page_Up"]:
        self.select_and_assign_row_after_key_press(
          tree_path,
          next_row=lambda tree_path: max(tree_path[0] - self._max_num_visible_rows, 0),
          next_row_if_no_current_selection=len(self._rows_filtered) - 1,
          current_row_before_unselection=0)
      elif key_name in ["Page_Down", "KP_Page_Down"]:
        self.select_and_assign_row_after_key_press(
          tree_path,
          next_row=lambda tree_path: min(
            tree_path[0] + self._max_num_visible_rows, len(self._rows_filtered) - 1),
          next_row_if_no_current_selection=0,
          current_row_before_unselection=len(self._rows_filtered) - 1)
      elif key_name in ["Return", "KP_Enter"]:
        self.save_last_value()
        self.hide()
      elif key_name == "Escape":
        self.assign_last_value()
        self.hide()
      else:
        stop_event_propagation = False
      
      return self.on_entry_key_press(key_name, tree_path, stop_event_propagation)
    else:
      return False
  
  def _on_entry_changed(self, entry):
    if self.trigger_popup:
      self.save_last_value()
      
      self._previous_assigned_entry_text_position = None
      self._previous_assigned_entry_text = None
      
      if not self.on_entry_changed_show_popup_condition():
        self.hide()
        return
      
      show_popup_first_time = self._show_popup_first_time
      if not show_popup_first_time:
        self._rows_filtered.refilter()
        self.resize(num_rows=len(self._rows_filtered))
      
      self.unselect()
      
      self.show()
      
      # If the popup is shown for the first time, filtering after showing the
      # popup makes sure that the correct width is assigned to the tree view.
      if show_popup_first_time:
        self._rows_filtered.refilter()
        self.resize(num_rows=len(self._rows_filtered))
  
  def _on_entry_left_mouse_button_press(self, entry, event):
    if event.button == self._BUTTON_MOUSE_LEFT:
      # If the user clicks on the edge of the entry (where the text cursor isn't
      # displayed yet), set the focus on the entry, since the popup will be displayed.
      if not self._entry.has_focus():
        self._entry.grab_focus()
        self._entry.set_position(-1)
      
      self._clear_filter = True
      self._rows_filtered.refilter()
      self._clear_filter = False
      
      show_popup_first_time = self._show_popup_first_time
      if not show_popup_first_time:
        self.resize(num_rows=len(self._rows_filtered))
      
      # No need to resize the tree view after showing the popup for the first
      # time - the "realize" signal handler automatically resizes the tree view.
      self.show()
      
      self.unselect()
      
      self.on_entry_left_mouse_button_press_func()
  
  def _on_tree_view_left_mouse_button_press(self, tree_view, event):
    if event.button == self._BUTTON_MOUSE_LEFT:
      self.on_row_left_mouse_button_press()
      
      self.save_last_value()
      
      self.hide()
  
  def _on_entry_enter_notify_event(self, entry, event):
    self._mouse_points_at_entry = True
  
  def _on_entry_leave_notify_event(self, entry, event):
    self._mouse_points_at_entry = False
  
  def _on_popup_enter_notify_event(self, entry, event):
    self._mouse_points_at_popup = True
  
  def _on_popup_leave_notify_event(self, popup, event):
    self._mouse_points_at_popup = False
  
  def _on_vscrollbar_enter_notify_event(self, vscrollbar, event):
    self._mouse_points_at_vscrollbar = True
  
  def _on_vscrollbar_leave_notify_event(self, vscrollbar, event):
    self._mouse_points_at_vscrollbar = False
  
  def _on_entry_focus_out_event(self, entry, event):
    self.save_last_value()
    self.hide()
  
  def _on_emission_hook_button_press_event(self, widget, event):
    if (self._mouse_points_at_popup
        or self._mouse_points_at_vscrollbar
        or self._mouse_points_at_entry):
      return True
    else:
      self.hide()
      return False
  
  def _on_toplevel_configure_event(self, toplevel_window, event):
    self.hide()

  def _on_after_tree_view_realize(self, tree_view):
    # Set the correct initial width and height of the tree view.
    self.resize(num_rows=len(self._rows_filtered))
