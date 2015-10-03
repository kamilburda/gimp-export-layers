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
This module defines a custom GUI text entry for file extensions, displaying a
popup with a list of supported file formats.

One can still enter a file extension not in the list in case an unrecognized
file format plug-in is used.
"""

#===============================================================================

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division

str = unicode

#===============================================================================

import pygtk

pygtk.require("2.0")

import gtk

import gobject
import pango

import gimp

from . import pgfileformats

#===============================================================================

pdb = gimp.pdb

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


class FileExtensionEntry(gtk.Entry):
  
  # The implementation is loosely based on the implementation of
  # `gtk.EntryCompletion`:
  # https://github.com/GNOME/gtk/blob/gtk-2-24/gtk/gtkentrycompletion.c
  
  _DEFAULT_TREE_VIEW_WIDTH = -1
  _DEFAULT_TREE_VIEW_HEIGHT = 200
  
  _MAX_NUM_VISIBLE_ROWS = 8
  
  _COLUMNS = [_COLUMN_DESCRIPTION, _COLUMN_EXTENSIONS] = (0, 1)
  _COLUMNS_TYPES = [bytes, gobject.TYPE_PYOBJECT]     # [string, list of strings]
  
  _BUTTON_MOUSE_LEFT = 1
  
  def __init__(self, *args, **kwargs):
    super(FileExtensionEntry, self).__init__(*args, **kwargs)
    
    self._trigger_popup = True
    self._clear_filter = False
    self._show_popup_first_time = True
    
    self._mouse_points_at_entry = False
    self._mouse_points_at_popup = False
    self._mouse_points_at_vscrollbar = False
    
    self._last_assigned_text = ""
    
    self._tree_view_width = None
    self._tree_view_columns_rects = []
    
    self._cell_renderer_description = None
    self._cell_renderer_extensions = None
    
    self._highlighted_extension_row = None
    self._highlighted_extension_index = None
    self._highlighted_extension = None
    
    self._extensions_separator_text_pixel_size = None
    self._extensions_text_pixel_rects = []
    
    self._create_popup(pgfileformats.file_formats)
    
    self.connect("button-press-event", self._on_entry_left_mouse_button_press)
    self.connect("key-press-event", self._on_entry_key_press)
    self.connect("changed", self._on_entry_changed)
    self.connect("focus-out-event", self._on_entry_focus_out)
    self.connect("size-allocate", self._on_entry_size_allocate)
    
    self.connect("enter-notify-event", self._on_entry_enter_notify_event)
    self.connect("leave-notify-event", self._on_entry_leave_notify_event)
    
    self._popup.connect("enter-notify-event", self._on_popup_enter_notify_event)
    self._popup.connect("leave-notify-event", self._on_popup_leave_notify_event)
    
    self._scrolled_window.get_vscrollbar().connect("enter-notify-event",
                                                   self._on_vscrollbar_enter_notify_event)
    self._scrolled_window.get_vscrollbar().connect("leave-notify-event",
                                                   self._on_vscrollbar_leave_notify_event)
    
    self._tree_view.connect("button-press-event", self._on_tree_view_left_mouse_button_press)
    self._tree_view.connect("motion-notify-event", self._on_tree_view_motion_notify_event)
    
    # This sets the correct initial width and height of the tree view.
    self._tree_view.connect_after("realize", self._on_after_tree_view_realize)
    
    self._tree_view.get_selection().connect("changed", self._on_tree_selection_changed)
    
    self._button_press_emission_hook_id = None
    self._entry_configure_event_id = None
    self._toplevel_configure_event_id = None
  
  def assign_text(self, text):
    """
    Replace the current contents of the entry with the specified text.
    
    Unlike `set_text()`, this method prevents the popup with file formats from
    showing. Additionally, this method places the text cursor at the end of the
    text.
    """
    
    self._trigger_popup = False
    self.set_text(text)
    self.set_position(-1)
    self._trigger_popup = True
  
  def _on_entry_left_mouse_button_press(self, entry, event):
    if event.button == self._BUTTON_MOUSE_LEFT:
      # If the user clicks on the edge of the entry (where the text cursor isn't
      # displayed yet), set the focus on the entry, since the popup will be
      # displayed.
      if not self.has_focus():
        self.grab_focus()
        self.set_position(-1)
      
      self._clear_filter = True
      self._file_formats_filtered.refilter()
      self._clear_filter = False
      
      show_popup_first_time = self._show_popup_first_time
      if not show_popup_first_time:
        self._resize_tree_view(num_rows=len(self._file_formats_filtered))
      
      # No need to resize the tree view after showing the popup for the first
      # time - the "realize" signal handler automatically resizes the tree view.
      self._show_popup()
      
      self._tree_view_unselect()
  
  def _on_entry_key_press(self, entry, event):
    key_name = gtk.gdk.keyval_name(event.keyval)
    
    if (key_name in ["Up", "KP_Up", "Down", "KP_Down",
                     "Page_Up", "KP_Page_Up", "Page_Down", "KP_Page_Down"]
        and not self._is_popup_shown()):
      self._unhighlight_extension()
      
      show_popup_first_time = self._show_popup_first_time
      
      self._show_popup()
      
      # This prevents the navigation keys to select the first row. 
      if show_popup_first_time:
        self._tree_view_unselect()
      
      return True
    
    if self._is_popup_shown():
      tree_path, unused_ = self._tree_view.get_cursor()
      
      if key_name in ["Up", "KP_Up"]:
        self._select_and_assign_row_after_key_press(
          tree_path,
          next_row=lambda tree_path: tree_path[0] - 1,
          next_row_if_no_current_selection=len(self._file_formats_filtered) - 1,
          current_row_before_unselection=0
        )
      elif key_name in ["Down", "KP_Down"]:
        self._select_and_assign_row_after_key_press(
          tree_path,
          next_row=lambda tree_path: tree_path[0] + 1,
          next_row_if_no_current_selection=0,
          current_row_before_unselection=len(self._file_formats_filtered) - 1
        )
      elif key_name in ["Page_Up", "KP_Page_Up"]:
        self._select_and_assign_row_after_key_press(
          tree_path,
          next_row=lambda tree_path: max(tree_path[0] - self._MAX_NUM_VISIBLE_ROWS,
                                         0),
          next_row_if_no_current_selection=len(self._file_formats_filtered) - 1,
          current_row_before_unselection=0
        )
      elif key_name in ["Page_Down", "KP_Page_Down"]:
        self._select_and_assign_row_after_key_press(
          tree_path,
          next_row=lambda tree_path: min(tree_path[0] + self._MAX_NUM_VISIBLE_ROWS,
                                         len(self._file_formats_filtered) - 1),
          next_row_if_no_current_selection=0,
          current_row_before_unselection=len(self._file_formats_filtered) - 1
        )
      elif key_name in ["Tab", "KP_Tab", "ISO_Left_Tab"]:
        # `tree_path` can sometimes point at the first row even though no row
        # is selected, hence the `tree_iter` usage.
        unused_, tree_iter = self._tree_view.get_selection().get_selected()
        
        if tree_iter is not None:
          if key_name in ["Tab", "KP_Tab"]:
            self._highlight_extension_next(tree_path)
          elif key_name == "ISO_Left_Tab":    # Shift+Tab
            self._highlight_extension_previous(tree_path)
          
          self.assign_text(self._highlighted_extension)
        else:
          return False
      elif key_name in ["Return", "KP_Enter"]:
        self._hide_popup()
      elif key_name == "Escape":
        self.assign_text(self._last_assigned_text)
        self._hide_popup()
      else:
        return False
      
      return True
    else:
      return False
  
  def _on_entry_changed(self, entry):
    if self._trigger_popup:
      self._last_assigned_text = self.get_text()
      
      show_popup_first_time = self._show_popup_first_time
      if not show_popup_first_time:
        self._file_formats_filtered.refilter()
        self._resize_tree_view(num_rows=len(self._file_formats_filtered))
      
      self._tree_view_unselect()
      
      self._show_popup()
      
      # If the popup is shown for the first time, filtering after showing the
      # popup makes sure that the correct width is assigned to the tree view.
      if show_popup_first_time:
        self._file_formats_filtered.refilter()
        self._resize_tree_view(num_rows=len(self._file_formats_filtered))
  
  def _on_entry_focus_out(self, entry, event):
    self._hide_popup()
  
  def _on_entry_size_allocate(self, entry, allocation):
    self._hide_popup()
  
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
  
  def _on_tree_view_left_mouse_button_press(self, tree_view, event):
    if event.button == self._BUTTON_MOUSE_LEFT:
      if self._highlighted_extension_index is None:
        self._assign_file_extension_from_selected_row()
      else:
        self.assign_text(self._highlighted_extension)
      
      self._last_assigned_text = self.get_text()
      self._hide_popup()
  
  def _on_tree_view_motion_notify_event(self, tree_view, event):
    self._highlight_extension_at_pos(int(event.x), int(event.y))
  
  def _on_after_tree_view_realize(self, tree_view):
    self._resize_tree_view(num_rows=len(self._file_formats_filtered))
    
    self._extensions_separator_text_pixel_size = self._get_text_pixel_size(
      self._cell_renderer_extensions.get_property("text-list-separator"),
      pango.Layout(self._tree_view.get_pango_context())
    )
    
    self._fill_extensions_text_pixel_rects()
    
    self._tree_view_columns_rects = [
      self._tree_view.get_cell_area((0,), self._tree_view.get_column(column))
      for column in self._COLUMNS
    ]
  
  def _on_tree_selection_changed(self, tree_selection):
    self._unhighlight_extension()
  
  def _on_button_press_emission_hook(self, widget, event):
    if (self._mouse_points_at_popup or self._mouse_points_at_vscrollbar or
        self._mouse_points_at_entry):
      return True
    else:
      self._hide_popup()
      return False
  
  def _on_toplevel_configure_event(self, toplevel_window, event):
    self._hide_popup()
  
  def _select_and_assign_row(self, row_num):
    self._tree_view.set_cursor((row_num,))
    # HACK: When the mouse points at the tree view and the user navigates with
    # keys, the selection jumps to the row pointed at. Selecting the row again
    # fixes this. 
    self._tree_view.set_cursor((row_num,))
    self._assign_file_extension_from_selected_row()
  
  def _select_and_assign_row_after_key_press(self, tree_path, next_row,
                                             next_row_if_no_current_selection,
                                             current_row_before_unselection,
                                             row_to_scroll_before_unselection=0):
    # One can pass functions for `next_row` and `current_row_before_unselection`
    # parameters if `tree_path` is None and `tree_path` is used to compute these
    # parameters.
    
    if tree_path is None:
      self._select_and_assign_row(next_row_if_no_current_selection)
    else:
      if callable(current_row_before_unselection):
        current_row_before_unselection = current_row_before_unselection(tree_path)
      
      if tree_path[0] == current_row_before_unselection:
        self._tree_view.scroll_to_cell((row_to_scroll_before_unselection,))
        self._tree_view_unselect()
        self.assign_text(self._last_assigned_text)
      else:
        if callable(next_row):
          next_row = next_row(tree_path)
        self._select_and_assign_row(next_row)
  
  def _tree_view_unselect(self):
    # Select an invalid row so that `get_cursor` returns None on the next call.
    self._tree_view.set_cursor((len(self._file_formats_filtered),))
    self._tree_view.get_selection().unselect_all()
  
  def _get_first_matching_row(self, text):
    """
    Get the first row in the list of file formats fully matching the specified
    text. Return the iterator to the first matching row. If there is no matching
    row, return None.
    """
    
    for row in self._file_formats_filtered:
      if self._entry_text_matches_row(text, self._file_formats_filtered, row.iter, full_match=True):
        return row.iter
  
  def _filter_file_formats(self, file_formats, row_iter):
    """
    Return True if the text in the entry is a substring of any file extension in
    the row.
    """
    
    if self._clear_filter:
      return True
    else:
      return self._entry_text_matches_row(self.get_text(), file_formats, row_iter)
  
  def _entry_text_matches_row(self, entry_text, file_formats, row_iter, full_match=False):
    extensions = file_formats[row_iter][self._COLUMN_EXTENSIONS]
    
    if full_match:
      return any(entry_text.lower() == extension.lower() for extension in extensions)
    else:
      return any(entry_text.lower() in extension.lower() for extension in extensions)
  
  def _assign_file_extension_from_selected_row(self, extension_index=0):
    tree_model, tree_iter = self._tree_view.get_selection().get_selected()
    if tree_iter is None:     # No row is selected
      return
    
    extensions = tree_model[tree_iter][self._COLUMN_EXTENSIONS]
    if extension_index > len(extensions):
      extension_index = len(extensions) - 1
    self.assign_text(extensions[extension_index])
  
  def _highlight_extension(self, selected_row_path, extension_index_selection_func):
    if selected_row_path is not None:
      self._unhighlight_extension_proper()
      
      row_path = self._file_formats_filtered.convert_path_to_child_path(selected_row_path)
      self._highlighted_extension_row = row_path[0]
      
      extensions = self._file_formats[row_path][self._COLUMN_EXTENSIONS]
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
      
      self._refresh_row_display(selected_row_path)
  
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
    
    path_params = self._tree_view.get_path_at_pos(x, y)
    if path_params is None:
      return
    
    selected_path_unfiltered = self._file_formats_filtered.convert_path_to_child_path(path_params[0])
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
      
      row_path = self._file_formats_filtered.convert_path_to_child_path(selected_row_path)
      
      self._highlighted_extension_row = row_path[0]
      self._highlighted_extension_index = extension_index
      
      self._highlight_extension_proper()
      
      self._refresh_row_display(selected_row_path)
  
  def _unhighlight_extension(self):
    self._unhighlight_extension_proper()
    
    if self._highlighted_extension_row is not None:
      self._refresh_row_display((self._highlighted_extension_row,), is_path_filtered=False)
    
    self._highlighted_extension_row = None
    self._highlighted_extension_index = None
  
  def _highlight_extension_proper(self):
    extensions = self._file_formats[self._highlighted_extension_row][self._COLUMN_EXTENSIONS]
    
    self._highlighted_extension = extensions[self._highlighted_extension_index]
    
    bg_color = self._tree_view.style.bg[gtk.STATE_SELECTED]
    fg_color = self._tree_view.style.fg[gtk.STATE_SELECTED]
    
    extensions[self._highlighted_extension_index] = (
      "<span background='{0}' foreground='{1}'>{2}</span>".format(
        bg_color.to_string(),
        fg_color.to_string(),
        extensions[self._highlighted_extension_index]
      )
    )
  
  def _unhighlight_extension_proper(self):
    if self._highlighted_extension_row is not None and self._highlighted_extension_index is not None:
      extensions = self._file_formats[self._highlighted_extension_row][self._COLUMN_EXTENSIONS]
      if self._highlighted_extension is not None:
        extensions[self._highlighted_extension_index] = self._highlighted_extension
        self._highlighted_extension = None
  
  def _refresh_row_display(self, row_path, is_path_filtered=True):
    if not is_path_filtered:
      row_path = self._file_formats_filtered.convert_child_path_to_path(row_path)
    
    if row_path is not None:
      self._file_formats_filtered.emit("row-changed", row_path,
                                       self._file_formats_filtered.get_iter(row_path))
  
  def _show_popup(self):
    if not self._is_popup_shown() and len(self._file_formats_filtered) > 0:
      self._update_popup_position()
      
      self._button_press_emission_hook_id = gobject.add_emission_hook(
        self, "button-press-event", self._on_button_press_emission_hook)
      
      toplevel_window = self.get_toplevel()
      if isinstance(toplevel_window, gtk.Window):
        toplevel_window.get_group().add_window(self._popup)
        # As soon as the user starts dragging or resizing the window, hide the
        # popup. Button presses on the window decoration cannot be intercepted
        # via "button-press-event" emission hooks, hence this workaround.
        self._toplevel_configure_event_id = toplevel_window.connect("configure-event",
                                                                    self._on_toplevel_configure_event)
      
      self._popup.set_screen(self.get_screen())
      
      self._popup.show()
      
      if self._show_popup_first_time:
        self._last_assigned_text = self.get_text()
        self._show_popup_first_time = False
  
  def _hide_popup(self):
    if self._is_popup_shown():
      self._popup.hide()
      
      if self._button_press_emission_hook_id is not None:
        gobject.remove_emission_hook(self, "button-press-event", self._button_press_emission_hook_id)
      
      if self._toplevel_configure_event_id is not None:
        toplevel_window = self.get_toplevel()
        if isinstance(toplevel_window, gtk.Window):
          toplevel_window.disconnect(self._toplevel_configure_event_id)
  
  def _is_popup_shown(self):
    return self._popup.get_mapped()
  
  def _update_popup_position(self):
    entry_absolute_position = self.get_window().get_origin()
    entry_allocation = self.get_allocation()
    self._popup.move(entry_absolute_position[0],
                     entry_absolute_position[1] + entry_allocation.height)
  
  def _resize_tree_view(self, num_rows):
    """
    Resize the tree view.
    
    Update the height of the tree view according to the number of rows. If the 
    number of rows is 0, hide the entire popup.
    
    Determine the initial width of the tree view based on the items displayed
    in the tree view. For subsequent calls of this function, the width of the
    tree view will remain the same.
    """
    
    cell_height = max(column.cell_get_size()[4] for column in self._tree_view.get_columns())
    vertical_spacing = self._tree_view.style_get_property("vertical-separator")
    row_height = cell_height + vertical_spacing
    num_visible_rows = min(num_rows, self._MAX_NUM_VISIBLE_ROWS)
    
    if self._tree_view_width is None:
      self._tree_view_width = self._tree_view.get_allocation().width
      if num_rows > self._MAX_NUM_VISIBLE_ROWS:
        vscrollbar_width = int(self._scrolled_window.get_hadjustment().upper -
                               self._scrolled_window.get_hadjustment().page_size)
        self._tree_view_width += vscrollbar_width * 2
    
    self._tree_view.set_size_request(self._tree_view_width, row_height * num_visible_rows)
    
    if num_rows == 0:
      self._hide_popup()
  
  def _create_popup(self, file_formats):
    self._file_formats = gtk.ListStore(*self._COLUMNS_TYPES)
    self._fill_file_formats(file_formats)
    
    self._file_formats_filtered = self._file_formats.filter_new()
    self._file_formats_filtered.set_visible_func(self._filter_file_formats)
    
    self._tree_view = gtk.TreeView(model=self._file_formats_filtered)
    self._tree_view.set_hover_selection(True)
    self._tree_view.set_headers_visible(False)
    self._tree_view.set_size_request(self._DEFAULT_TREE_VIEW_WIDTH, self._DEFAULT_TREE_VIEW_HEIGHT)
    self._add_file_format_columns()
    
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
  
  def _fill_file_formats(self, file_formats):
    for file_format in file_formats:
      can_add_file_format = (
        file_format.save_procedure_name is None or (
          file_format.save_procedure_name is not None and
          pdb.gimp_procedural_db_proc_exists(file_format.save_procedure_name)))
      
      if can_add_file_format:
        self._file_formats.append([file_format.description, file_format.file_extensions])
  
  def _add_file_format_columns(self):
    
    def _add_column(cell_renderer, cell_renderer_property, column_number, column_title=None):
      column = gtk.TreeViewColumn(column_title, cell_renderer, **{cell_renderer_property: column_number})
      self._tree_view.append_column(column)
    
    self._cell_renderer_description = gtk.CellRendererText()
    self._cell_renderer_extensions = CellRendererTextList()
    _add_column(self._cell_renderer_description, "text", self._COLUMN_DESCRIPTION)
    _add_column(self._cell_renderer_extensions, "markup-list", self._COLUMN_EXTENSIONS)
  
  def _fill_extensions_text_pixel_rects(self):
    pango_layout = pango.Layout(self._tree_view.get_pango_context())
    
    for file_format in self._file_formats:
      file_extensions = file_format[1]
      
      if len(file_extensions) > 1:
        text_pixel_rects = self._get_text_pixel_rects(file_extensions, pango_layout,
                                                      self._extensions_separator_text_pixel_size[0])
        for rect in text_pixel_rects:
          rect.x += self._cell_renderer_extensions.get_property("xpad")
          rect.x += self._tree_view.style_get_property("horizontal-separator")
          rect.x += self._tree_view.get_column(self._COLUMN_EXTENSIONS).get_spacing()
          
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
  