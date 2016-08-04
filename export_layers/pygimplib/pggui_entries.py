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

"""
This module defines the following GUI elements:
* a custom text entry for filename patterns
* a custom text entry for file extensions
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

str = unicode

import pygtk
pygtk.require("2.0")
import gtk
import gobject
import pango

import gimp

pdb = gimp.pdb

from . import pgfileformats
from . import pgpath

#===============================================================================


class CellRendererTextList(gtk.CellRendererText):
  
  """
  This is a custom text-based cell renderer that can accept a list of strings.
  """
  
  __gproperties__ = {
    b"text-list": (
      gobject.TYPE_PYOBJECT,
      b"list of strings",
      "List of strings to render",
      gobject.PARAM_READWRITE
    ),
    b"markup-list": (
      gobject.TYPE_PYOBJECT,
      b"list of strings in markup",
      "List of strings with markup to render",
      gobject.PARAM_WRITABLE
    ),
    b"text-list-separator": (
      gobject.TYPE_STRING,
      b"separator for list of strings",
      "Text separator for the list of strings (\"text-list\" and \"markup-list\" properties)",
      ", ",     # Default value
      gobject.PARAM_READWRITE
    ),
  }
  
  def __init__(self):
    gtk.CellRendererText.__init__(self)
    
    self.text_list = None
    self.markup_list = None
    self.text_list_separator = ", "
  
  def do_get_property(self, property_):
    attr_name = self._property_name_to_attr(property_.name)
    if hasattr(self, attr_name):
      return getattr(self, attr_name)
    else:
      return gtk.CellRendererText.get_property(self, property_.name)
  
  def do_set_property(self, property_, value):
    attr_name = self._property_name_to_attr(property_.name)
    if hasattr(self, attr_name):
      if (property_.name in ["text-list", "markup-list"] and
          not(isinstance(value, list) or isinstance(value, tuple))):
        raise AttributeError("not a list or tuple")
      
      setattr(self, attr_name, value)
      
      self._evaluate_text_property(property_.name)
  
  def _evaluate_text_property(self, property_name):
    """
    Change the "text" or "markup" property according to the value of
    "text-list", "markup-list" and "text-list-separator" properties.
    """
    
    def _set_text():
      new_text = self.text_list_separator.join(self.text_list)
      gtk.CellRendererText.set_property(self, "text", new_text)
    
    def _set_markup():
      new_text = self.text_list_separator.join(self.markup_list)
      gtk.CellRendererText.set_property(self, "markup", new_text)
    
    if property_name == "text-list":
      _set_text()
      self.markup_list = None
    elif property_name == "markup-list":
      _set_markup()
      self.text_list = None
    elif property_name == "text-list-separator":
      if self.text_list is not None:
        _set_text()
      elif self.markup_list is not None:
        _set_markup()
  
  def _property_name_to_attr(self, property_name):
    return property_name.replace("-", "_")


gobject.type_register(CellRendererTextList)


#===============================================================================


class EntryPopup(object):
  
  _BUTTON_MOUSE_LEFT = 1
  
  # The implementation is loosely based on the implementation of `gtk.EntryCompletion`:
  # https://github.com/GNOME/gtk/blob/gtk-2-24/gtk/gtkentrycompletion.c
  
  def __init__(self, entry, column_types, rows, row_filter_func=None,
    assign_from_selected_row_func=None, assign_last_value_func=None, on_row_left_mouse_button_press=None,
    on_entry_key_press_before_show_popup_func=None, on_entry_key_press_func=None,
    on_entry_changed_show_popup_condition_func=None,
    width=-1, height=200, max_num_visible_rows=8):
    
    self._entry = entry
    self._row_filter_func = row_filter_func
    self._width = width
    self._height = height
    self._max_num_visible_rows = max_num_visible_rows
    self._assign_from_selected_row_func = (
      assign_from_selected_row_func if assign_from_selected_row_func is not None else lambda *args: None)
    self._assign_last_value_func = (
      assign_last_value_func if assign_last_value_func is not None else self.assign_text)
    self._on_row_left_mouse_button_press = (
      on_row_left_mouse_button_press if on_row_left_mouse_button_press is not None else
      self.assign_from_selected_row)
    self._on_entry_key_press_before_show_popup_func = (
      on_entry_key_press_before_show_popup_func if on_entry_key_press_before_show_popup_func is not None else
      lambda *args: None)
    self._on_entry_key_press_func = (
      on_entry_key_press_func if on_entry_key_press_func is not None else
      lambda key_name, tree_path, stop_event_propagation: stop_event_propagation)
    self._on_entry_changed_show_popup_condition_func = (
      on_entry_changed_show_popup_condition_func if on_entry_changed_show_popup_condition_func is not None else
      lambda *args: True
    )
    
    self._last_assigned_entry_text = ""
    
    self._show_popup_first_time = True
    self._trigger_popup = True
    
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
  def popup(self):
    return self._popup
  
  @property
  def tree_view(self):
    return self._tree_view
  
  @property
  def last_assigned_entry_text(self):
    return self._last_assigned_entry_text
  
  def assign_text(self, text):
    """
    Replace the current contents of the entry with the specified text. Unlike
    `set_text()` in the entry, this method prevents the popup from showing.
    """
    
    self._trigger_popup = False
    self._entry.set_text(text)
    self._trigger_popup = True
  
  def assign_last_value(self):
    self._assign_last_value_func(self._last_assigned_entry_text)
  
  def show(self):
    if not self.is_shown() and len(self._rows_filtered) > 0:
      self._update_position()
      
      self._button_press_emission_hook_id = gobject.add_emission_hook(
        self._entry, "button-press-event", self._on_button_press_emission_hook)
      
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
      
      if self._show_popup_first_time:
        self._last_assigned_entry_text = self._entry.get_text()
        self._show_popup_first_time = False
  
  def hide(self):
    if self.is_shown():
      self._popup.hide()
      
      if self._button_press_emission_hook_id is not None:
        gobject.remove_emission_hook(self._entry, "button-press-event", self._button_press_emission_hook_id)
      
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
          self._scrolled_window.get_hadjustment().upper - self._scrolled_window.get_hadjustment().page_size)
        self._tree_view_width += vscrollbar_width * 2
    
    self._tree_view.set_size_request(self._tree_view_width, row_height * num_visible_rows)
    
    if num_rows == 0:
      self.hide()
  
  def refresh_row(self, row_path, is_path_filtered=True):
    if not is_path_filtered:
      row_path = self._rows_filtered.convert_child_path_to_path(row_path)
    
    if row_path is not None:
      self._rows_filtered.emit("row-changed", row_path, self._rows_filtered.get_iter(row_path))
  
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
      return
    
    self._assign_from_selected_row_func(tree_model, tree_iter)
  
  def select_and_assign_row(self, row_num):
    self.select_row(row_num)
    self.assign_from_selected_row()
  
  def select_and_assign_row_after_key_press(self, tree_path, next_row,
    next_row_if_no_current_selection, current_row_before_unselection,
    row_to_scroll_before_unselection=0):
    
    """
    After a particular key is pressed, select the row specified by `tree_path`
    and assign the value from the selected row to the entry.
    
    One can pass functions for `next_row` and `current_row_before_unselection`
    parameters if `tree_path` is None and `tree_path` is used to compute these
    parameters.
    """
    
    if tree_path is None:
      self.select_and_assign_row(next_row_if_no_current_selection)
    else:
      if callable(current_row_before_unselection):
        current_row_before_unselection = current_row_before_unselection(tree_path)
      
      if tree_path[0] == current_row_before_unselection:
        self._tree_view.scroll_to_cell((row_to_scroll_before_unselection,))
        self.unselect()
        self.assign_last_value()
      else:
        if callable(next_row):
          next_row = next_row(tree_path)
        self.select_and_assign_row(next_row)
  
  def _init_gui(self, column_types, rows):
    self._rows = gtk.ListStore(*column_types)
    
    for row in rows:
      self._rows.append(row)
    
    self._rows_filtered = self._rows.filter_new()
    if self._row_filter_func is not None:
      self._rows_filtered.set_visible_func(self._filter_rows)
    
    self._tree_view = gtk.TreeView(model=self._rows_filtered)
    self._tree_view.set_hover_selection(True)
    self._tree_view.set_headers_visible(False)
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
    self._tree_view.connect("button-press-event", self._on_tree_view_left_mouse_button_press)
  
  def _update_position(self):
    entry_absolute_position = self._entry.get_window().get_origin()
    entry_allocation_height = self._entry.get_allocation().height
    self._popup.move(entry_absolute_position[0], entry_absolute_position[1] + entry_allocation_height)
  
  def _filter_rows(self, rows, row_iter):
    if self._clear_filter:
      return True
    else:
      return self._row_filter_func(rows, row_iter)
  
  def _on_entry_key_press(self, entry, event):
    key_name = gtk.gdk.keyval_name(event.keyval)
    
    if (not self.is_shown() and
        key_name in ["Up", "KP_Up", "Down", "KP_Down", "Page_Up", "KP_Page_Up", "Page_Down", "KP_Page_Down"]):
      self._on_entry_key_press_before_show_popup_func()
      
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
        self._last_assigned_entry_text = self._entry.get_text()
        self.hide()
      elif key_name == "Escape":
        self.assign_last_value()
        self.hide()
      else:
        stop_event_propagation = False
      
      return self._on_entry_key_press_func(key_name, tree_path, stop_event_propagation)
    else:
      return False
  
  def _on_entry_changed(self, entry):
    if self._trigger_popup:
      self._last_assigned_entry_text = self._entry.get_text()
      
      if not self._on_entry_changed_show_popup_condition_func():
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
  
  def _on_tree_view_left_mouse_button_press(self, tree_view, event):
    if event.button == self._BUTTON_MOUSE_LEFT:
      self._on_row_left_mouse_button_press()
      
      self._last_assigned_entry_text = self._entry.get_text()
      
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
    self.hide()
  
  def _on_button_press_emission_hook(self, widget, event):
    if self._mouse_points_at_popup or self._mouse_points_at_vscrollbar or self._mouse_points_at_entry:
      return True
    else:
      self.hide()
      return False
  
  def _on_toplevel_configure_event(self, toplevel_window, event):
    self.hide()

  def _on_after_tree_view_realize(self, tree_view):
    # Set the correct initial width and height of the tree view.
    self.resize(num_rows=len(self._rows_filtered))
  

#===============================================================================


class FilenamePatternEntry(gtk.Entry):
  
  _BUTTON_MOUSE_LEFT = 1
  
  _COLUMNS = [_COLUMN_ITEM_NAMES, _COLUMN_ITEMS, _COLUMN_ITEM_ARGUMENTS] = (0, 1, 2)
  _COLUMN_TYPES = [bytes, bytes, gobject.TYPE_PYOBJECT]
  
  def __init__(self, suggested_items, *args, **kwargs):
    self._mininum_width = kwargs.pop('minimum_width', -1)
    self._maximum_width = kwargs.pop('maximum_width', -1)
    self._default_item_value = kwargs.pop('default_item', None)
    
    self._suggested_fields = self._get_suggested_fields(suggested_items)
    
    suggested_item_values = [item[1] for item in suggested_items]
    if self._default_item_value is not None and self._default_item_value not in suggested_item_values:
      raise ValueError("default item \"{0}\" not in the list of suggested items: {1}".format(
        self._default_item_value, suggested_item_values))
    
    if self._default_item_value is not None:
      self._default_item_name = suggested_items[suggested_item_values.index(self._default_item_value)][0]
    else:
      self._default_item_name = None
    
    super(FilenamePatternEntry, self).__init__(*args, **kwargs)
    
    self._cursor_position = 0
    self._cursor_position_before_assigning_from_row = None
    self._reset_cursor_position_before_assigning_from_row = True
    
    self._has_placeholder_item_assigned = False
    
    self._pango_layout = pango.Layout(self.get_pango_context())
    
    self.set_size_request(self._mininum_width, -1)
    
    self._popup = EntryPopup(
      self, self._COLUMN_TYPES, suggested_items,
      row_filter_func=self._filter_suggested_items,
      assign_from_selected_row_func=self._assign_from_selected_row,
      assign_last_value_func=self._assign_last_value,
      on_entry_changed_show_popup_condition_func=self._on_entry_changed_condition,
      on_entry_key_press_func=self._on_entry_key_press)
    
    self._create_field_tooltip()
    
    self._add_columns()
    
    self.connect("delete-text", self._on_entry_delete_text)
    self.connect("insert-text", self._on_entry_insert_text)
    self.connect("notify::cursor-position", self._on_cursor_position_changed)
    self.connect("changed", self._on_entry_changed)
    
    self.connect("focus-in-event", self._on_entry_focus_in_event)
    self.connect("focus-out-event", self._on_entry_focus_out_event)
    
    self.connect_after("realize", self._on_after_entry_realize)
    self.connect("size-allocate", self._on_entry_size_allocate)
  
  def get_text(self):
    if not self._has_placeholder_item_assigned:
      return super(FilenamePatternEntry, self).get_text()
    else:
      return ""
  
  def assign_text(self, text):
    if self.has_focus() or not self._should_assign_placeholder_text(text):
      self._popup.assign_text(text)
    else:
      self._assign_placeholder_text()
  
  def _filter_suggested_items(self, suggested_items, row_iter):
    item = suggested_items[row_iter][self._COLUMN_ITEMS]
    
    if (self._cursor_position > 0 and
        self.get_text()[self._cursor_position - 1] == "[" and item and item[0] != "["):
      return False
    else:
      return True
  
  def _assign_last_value(self, last_value):
    self._reset_cursor_position_before_assigning_from_row = False
    self._popup.assign_text(last_value)
    self._reset_cursor_position_before_assigning_from_row = True
    
    if self._cursor_position_before_assigning_from_row is not None:
      self._cursor_position = self._cursor_position_before_assigning_from_row
    self.set_position(self._cursor_position)
    self._cursor_position_before_assigning_from_row = None
  
  def _assign_from_selected_row(self, tree_model, selected_tree_iter):
    if self._cursor_position_before_assigning_from_row is None:
      self._cursor_position_before_assigning_from_row = self._cursor_position
    cursor_position = self._cursor_position_before_assigning_from_row
    
    suggested_item = str(tree_model[selected_tree_iter][self._COLUMN_ITEMS])
    if cursor_position > 0 and self._popup.last_assigned_entry_text[cursor_position - 1] == "[":
      suggested_item = suggested_item[1:]
    
    self.assign_text(
      self._popup.last_assigned_entry_text[:cursor_position] + suggested_item +
      self._popup.last_assigned_entry_text[cursor_position:])
    
    self.set_position(cursor_position + len(suggested_item))
    self._cursor_position = self.get_position()
    self._cursor_position_before_assigning_from_row = cursor_position
  
  def _update_entry_width(self):
    self._pango_layout.set_text(self.get_text())
    
    offset_pixel_width = (self.get_layout_offsets()[0] + self.get_property("scroll-offset")) * 2
    text_pixel_width = self._pango_layout.get_pixel_size()[0] + offset_pixel_width
    self.set_size_request(max(min(text_pixel_width, self._maximum_width), self._mininum_width), -1)
  
  def _on_entry_changed_condition(self):
    current_text = self.get_text()
    
    if current_text:
      if len(current_text) > 1:
        return (
          current_text[self._cursor_position - 1] == "[" and
          current_text[self._cursor_position - 2] != "[" and
          not pgpath.StringPatternGenerator.get_field_at_position(current_text, self._cursor_position - 1))
      else:
        return current_text[0] == "["
    else:
      return True
  
  def _assign_placeholder_text(self):
    if self._default_item_name is not None:
      self._has_placeholder_item_assigned = True
      
      # The font may be different before widget realization, and modifying the font
      # now may result in the font not being properly set up after the realization.
      if self.get_realized():
        self._modify_font_for_placeholder_text(gtk.STATE_INSENSITIVE, pango.STYLE_ITALIC)
      
      self._popup.assign_text(self._default_item_name)
  
  def _unassign_placeholder_text(self):
    if self._has_placeholder_item_assigned:
      self._has_placeholder_item_assigned = False
      self._modify_font_for_placeholder_text(gtk.STATE_NORMAL, pango.STYLE_NORMAL)
      self._popup.assign_text("")
  
  def _modify_font_for_placeholder_text(self, state_for_color, style):
    self.modify_text(gtk.STATE_NORMAL, self.style.fg[state_for_color])
    
    font_description = self.get_pango_context().get_font_description()
    font_description.set_style(style)
    self.modify_font(font_description)
  
  def _should_assign_placeholder_text(self, text):
    return not text or (self._default_item_value is not None and text == self._default_item_value)
  
  def _on_entry_delete_text(self, entry, start, end):
    self._cursor_position = start
  
  def _on_entry_insert_text(self, entry, new_text, new_text_length, position):
    self._cursor_position = self.get_position() + new_text_length
  
  def _on_cursor_position_changed(self, entry, property_spec):
    self._cursor_position = self.get_position()
    
    field_name = (
      pgpath.StringPatternGenerator.get_field_at_position(
        self.get_text(), self._cursor_position - 1, field_names=self._suggested_fields.keys()))
    
    if self._suggested_fields.get(field_name):
      self._show_field_tooltip(self._suggested_fields[field_name], force_modify=True)
    else:
      self._hide_field_tooltip()
  
  def _on_entry_changed(self, entry):
    if self.get_realized():
      self._update_entry_width()
    
    if self._reset_cursor_position_before_assigning_from_row:
      self._cursor_position_before_assigning_from_row = None
  
  def _on_entry_focus_in_event(self, entry, event):
    self._unassign_placeholder_text()
  
  def _on_entry_focus_out_event(self, entry, event):
    if self._should_assign_placeholder_text(self.get_text()):
      self._assign_placeholder_text()
    
    self._hide_field_tooltip()
  
  def _on_after_entry_realize(self, entry):
    if self._should_assign_placeholder_text(self.get_text()):
      self._assign_placeholder_text()
  
  def _on_entry_size_allocate(self, entry, allocation):
    self._update_entry_width()
  
  def _add_columns(self):
    self._popup.tree_view.append_column(
      gtk.TreeViewColumn(None, gtk.CellRendererText(), text=self._COLUMN_ITEM_NAMES))
  
  def _create_field_tooltip(self):
    self._field_tooltip_window = gtk.Window(type=gtk.WINDOW_POPUP)
    self._field_tooltip_window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_TOOLTIP)
    self._field_tooltip_window.set_resizable(False)
    # This copies the style of GTK tooltips.
    self._field_tooltip_window.set_name('gtk-tooltips')
    
    self._field_tooltip_text = gtk.Label()
    
    self._field_tooltip_hbox = gtk.HBox(homogeneous=False)
    self._field_tooltip_hbox.pack_start(self._field_tooltip_text, fill=False, expand=False)
    
    self._field_tooltip_frame = gtk.Frame()
    self._field_tooltip_frame.set_shadow_type(gtk.SHADOW_ETCHED_IN)
    self._field_tooltip_frame.add(self._field_tooltip_hbox)
    self._field_tooltip_frame.show_all()
    
    self._field_tooltip_window.add(self._field_tooltip_frame)
  
  def _show_field_tooltip(self, tooltip_text=None, force_modify=False):
    if not self._field_tooltip_window.get_mapped() or force_modify:
      if tooltip_text is None:
        tooltip_text = ""
      self._field_tooltip_text.set_markup(tooltip_text)
      self._update_field_tooltip_position()
      self._field_tooltip_window.show()
  
  def _hide_field_tooltip(self):
    if self._field_tooltip_window.get_mapped():
      self._field_tooltip_window.hide()
  
  def _update_field_tooltip_position(self):
    entry_absolute_position = self.get_window().get_origin()
    entry_allocation_height = self.get_allocation().height
    self._field_tooltip_window.move(
      entry_absolute_position[0], entry_absolute_position[1] - entry_allocation_height)
  
  def _get_suggested_fields(self, suggested_items):
    suggested_fields = {}
    
    for item in suggested_items:
      field_value = item[1]
      if field_value.startswith("[") and field_value.endswith("]"):
        if item[2]:
          suggested_fields[field_value[1:-1]] = "[{0}, {1}]".format(
            gobject.markup_escape_text(field_value[1:-1]), ", ".join(
              ["<i>{0}</i>".format(gobject.markup_escape_text(argument)) for argument in item[2]]))
        else:
          suggested_fields[field_value[1:-1]] = ""
    
    return suggested_fields
  
  def _on_entry_key_press(self, key_name, tree_path, stop_event_propagation):
    if key_name in ["Return", "KP_Enter", "Escape"]:
      self._hide_field_tooltip()
      return True
    
    return stop_event_propagation
  

#===============================================================================


class FileExtensionEntry(gtk.Entry):
  
  _COLUMNS = [_COLUMN_DESCRIPTION, _COLUMN_EXTENSIONS] = (0, 1)
  _COLUMN_TYPES = [bytes, gobject.TYPE_PYOBJECT]     # [string, list of strings]
  
  def __init__(self, *args, **kwargs):
    super(FileExtensionEntry, self).__init__(*args, **kwargs)
    
    self._tree_view_columns_rects = []
    
    self._cell_renderer_description = None
    self._cell_renderer_extensions = None
    
    self._highlighted_extension_row = None
    self._highlighted_extension_index = None
    self._highlighted_extension = None
    
    self._extensions_separator_text_pixel_size = None
    self._extensions_text_pixel_rects = []
    
    self._popup = EntryPopup(
      self, self._COLUMN_TYPES, self._get_file_formats(pgfileformats.file_formats),
      row_filter_func=self._filter_file_formats, assign_from_selected_row_func=self._assign_from_selected_row,
      assign_last_value_func=self.assign_text,
      on_row_left_mouse_button_press=self._on_row_left_mouse_button_press,
      on_entry_key_press_before_show_popup_func=self._on_key_press_before_show_popup,
      on_entry_key_press_func=self._on_tab_keys_pressed)
    
    self._add_columns()
    
    self._popup.tree_view.connect("motion-notify-event", self._on_tree_view_motion_notify_event)
    self._popup.tree_view.connect_after("realize", self._on_after_tree_view_realize)
    self._popup.tree_view.get_selection().connect("changed", self._on_tree_selection_changed)
  
  def assign_text(self, text):
    self._popup.assign_text(text)
    self.set_position(-1)
  
  def _on_row_left_mouse_button_press(self):
    if self._highlighted_extension_index is None:
      self._popup.assign_from_selected_row()
    else:
      self.assign_text(self._highlighted_extension)
  
  def _on_key_press_before_show_popup(self):
    self._unhighlight_extension()
  
  def _on_tab_keys_pressed(self, key_name, selected_tree_path, stop_event_propagation):
    if key_name in ["Tab", "KP_Tab", "ISO_Left_Tab"]:
      # Tree paths can sometimes point at the first row even though no row is
      # selected, hence the `tree_iter` usage.
      unused_, tree_iter = self._popup.tree_view.get_selection().get_selected()
      
      if tree_iter is not None:
        if key_name in ["Tab", "KP_Tab"]:
          self._highlight_extension_next(selected_tree_path)
        elif key_name == "ISO_Left_Tab":    # Shift + Tab
          self._highlight_extension_previous(selected_tree_path)
        
        self.assign_text(self._highlighted_extension)
        
        return True
    
    return stop_event_propagation
  
  def _assign_from_selected_row(self, tree_model, selected_tree_iter, extension_index=0):
    extensions = tree_model[selected_tree_iter][self._COLUMN_EXTENSIONS]
    if extension_index > len(extensions):
      extension_index = len(extensions) - 1
    self.assign_text(extensions[extension_index])
  
  def _filter_file_formats(self, file_formats, row_iter):
    return self._entry_text_matches_row(self.get_text(), file_formats, row_iter)
  
  def _entry_text_matches_row(self, entry_text, file_formats, row_iter, full_match=False):
    """
    Return True if the text in the entry is a substring of any file extension in
    the row.
    """
    
    extensions = file_formats[row_iter][self._COLUMN_EXTENSIONS]
    
    if full_match:
      return any(entry_text.lower() == extension.lower() for extension in extensions)
    else:
      return any(entry_text.lower() in extension.lower() for extension in extensions)
  
  def _on_tree_view_motion_notify_event(self, tree_view, event):
    self._highlight_extension_at_pos(int(event.x), int(event.y))
  
  def _on_after_tree_view_realize(self, tree_view):
    self._extensions_separator_text_pixel_size = self._get_text_pixel_size(
      self._cell_renderer_extensions.get_property("text-list-separator"),
      pango.Layout(self._popup.tree_view.get_pango_context()))
    
    self._fill_extensions_text_pixel_rects()
    
    self._tree_view_columns_rects = [
      self._popup.tree_view.get_cell_area((0,), self._popup.tree_view.get_column(column))
      for column in self._COLUMNS]
  
  def _on_tree_selection_changed(self, tree_selection):
    self._unhighlight_extension()
  
  def _highlight_extension(self, selected_row_path, extension_index_selection_func):
    if selected_row_path is not None:
      self._unhighlight_extension_proper()
      
      row_path = self._popup.rows_filtered.convert_path_to_child_path(selected_row_path)
      self._highlighted_extension_row = row_path[0]
      
      extensions = self._popup.rows[row_path][self._COLUMN_EXTENSIONS]
      if len(extensions) <= 1:
        # No good reason to highlight the only extension in the row.
        if len(extensions) == 1:
          self._highlighted_extension = extensions[0]
        elif len(extensions) == 0:
          self._highlighted_extension = ""
        
        return
      
      if self._highlighted_extension_index is None:
        self._highlighted_extension_index = 0
      
      self._highlighted_extension_index = extension_index_selection_func(
        self._highlighted_extension_index, len(extensions))
      
      self._highlight_extension_proper()
      
      self._popup.refresh_row(selected_row_path)
  
  def _highlight_extension_next(self, selected_row_path):
    def _select_next_extension(highlighted_extension_index, len_extensions):
      return (highlighted_extension_index + 1) % len_extensions
    
    self._highlight_extension(selected_row_path, _select_next_extension)
  
  def _highlight_extension_previous(self, selected_row_path):
    def _select_previous_extension(highlighted_extension_index, len_extensions):
      return (highlighted_extension_index - 1) % len_extensions
    
    self._highlight_extension(selected_row_path, _select_previous_extension)
  
  def _highlight_extension_at_pos(self, x, y):
    is_in_extensions_column = x >= self._tree_view_columns_rects[self._COLUMN_EXTENSIONS].x
    if not is_in_extensions_column:
      if self._highlighted_extension is not None:
        self._unhighlight_extension()
      return
    
    path_params = self._popup.tree_view.get_path_at_pos(x, y)
    if path_params is None:
      return
    
    selected_path_unfiltered = self._popup.rows_filtered.convert_path_to_child_path(path_params[0])
    extension_index = self._get_extension_index_at_pos(path_params[2], selected_path_unfiltered[0])
    
    if extension_index == self._highlighted_extension_index:
      return
    
    if extension_index is not None:
      self._highlight_extension_at_index(path_params[0], extension_index)
    else:
      self._unhighlight_extension()
  
  def _highlight_extension_at_index(self, selected_row_path, extension_index):
    if selected_row_path is not None:
      self._unhighlight_extension_proper()
      
      row_path = self._popup.rows_filtered.convert_path_to_child_path(selected_row_path)
      
      self._highlighted_extension_row = row_path[0]
      self._highlighted_extension_index = extension_index
      
      self._highlight_extension_proper()
      
      self._popup.refresh_row(selected_row_path)
  
  def _unhighlight_extension(self):
    self._unhighlight_extension_proper()
    
    if self._highlighted_extension_row is not None:
      self._popup.refresh_row((self._highlighted_extension_row,), is_path_filtered=False)
    
    self._highlighted_extension_row = None
    self._highlighted_extension_index = None
  
  def _highlight_extension_proper(self):
    extensions = self._popup.rows[self._highlighted_extension_row][self._COLUMN_EXTENSIONS]
    
    self._highlighted_extension = extensions[self._highlighted_extension_index]
    
    bg_color = self._popup.tree_view.style.bg[gtk.STATE_SELECTED]
    fg_color = self._popup.tree_view.style.fg[gtk.STATE_SELECTED]
    
    extensions[self._highlighted_extension_index] = (
      "<span background='{0}' foreground='{1}'>{2}</span>".format(
        bg_color.to_string(),
        fg_color.to_string(),
        extensions[self._highlighted_extension_index]))
  
  def _unhighlight_extension_proper(self):
    if self._highlighted_extension_row is not None and self._highlighted_extension_index is not None:
      extensions = self._popup.rows[self._highlighted_extension_row][self._COLUMN_EXTENSIONS]
      if self._highlighted_extension is not None:
        extensions[self._highlighted_extension_index] = self._highlighted_extension
        self._highlighted_extension = None
  
  def _fill_extensions_text_pixel_rects(self):
    pango_layout = pango.Layout(self._popup.tree_view.get_pango_context())
    
    for file_format in self._popup.rows:
      file_extensions = file_format[1]
      
      if len(file_extensions) > 1:
        text_pixel_rects = self._get_text_pixel_rects(file_extensions, pango_layout,
                                                      self._extensions_separator_text_pixel_size[0])
        for rect in text_pixel_rects:
          rect.x += self._cell_renderer_extensions.get_property("xpad")
          rect.x += self._popup.tree_view.style_get_property("horizontal-separator")
          rect.x += self._popup.tree_view.get_column(self._COLUMN_EXTENSIONS).get_spacing()
          
          # Occupy the space of the separator so that extension highlighting is
          # continuous.
          if rect == text_pixel_rects[0]:
            rect.width += self._extensions_separator_text_pixel_size[0] // 2
          elif rect == text_pixel_rects[-1]:
            rect.x -= self._extensions_separator_text_pixel_size[0] // 2
            rect.width += self._extensions_separator_text_pixel_size[0] // 2
          else:
            rect.x -= self._extensions_separator_text_pixel_size[0] // 2
            rect.width += self._extensions_separator_text_pixel_size[0]
          
        self._extensions_text_pixel_rects.append(text_pixel_rects)
      else:
        self._extensions_text_pixel_rects.append([])
  
  def _get_text_pixel_rects(self, file_extensions, pango_layout, separator_pixel_width):
    text_pixel_rects = []
    
    extension_x = 0
    for extension in file_extensions:
      extension_pixel_size = self._get_text_pixel_size(extension, pango_layout)
      text_pixel_rects.append(gtk.gdk.Rectangle(extension_x, 0, *extension_pixel_size))
      
      extension_x += extension_pixel_size[0] + separator_pixel_width
    
    return text_pixel_rects
  
  def _get_text_pixel_size(self, text, pango_layout):
    pango_layout.set_text(text)
    return pango_layout.get_pixel_size()
  
  def _get_extension_index_at_pos(self, cell_x, selected_row):
    extension_rects = self._extensions_text_pixel_rects[selected_row]
    
    if not extension_rects:
      return None
    
    extension_index = 0
    for extension_rect in extension_rects:
      if extension_rect.x <= cell_x <= extension_rect.x + extension_rect.width:
        break
      extension_index += 1
    
    matches_extension = extension_index < len(extension_rects)
    
    if matches_extension:
      return extension_index
    else:
      return None
  
  def _get_file_formats(self, file_formats):
    file_formats_to_add = []
    
    for file_format in file_formats:
      can_add_file_format = (
        file_format.save_procedure_name is None or (
          file_format.save_procedure_name is not None and
          pdb.gimp_procedural_db_proc_exists(file_format.save_procedure_name)))
      
      if can_add_file_format:
        file_formats_to_add.append([file_format.description, file_format.file_extensions])
    
    return file_formats_to_add
  
  def _add_columns(self):
    
    def _add_column(cell_renderer, cell_renderer_property, column_number, column_title=None):
      column = gtk.TreeViewColumn(column_title, cell_renderer, **{cell_renderer_property: column_number})
      self._popup.tree_view.append_column(column)
    
    self._cell_renderer_description = gtk.CellRendererText()
    self._cell_renderer_extensions = CellRendererTextList()
    _add_column(self._cell_renderer_description, "text", self._COLUMN_DESCRIPTION)
    _add_column(self._cell_renderer_extensions, "markup-list", self._COLUMN_EXTENSIONS)
