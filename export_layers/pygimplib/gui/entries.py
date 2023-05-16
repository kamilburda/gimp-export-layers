# -*- coding: utf-8 -*-

"""GTK text entries (fields) with enhanced features.

Enhanced features include undo/redo history and a customizable popup.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import pygtk
pygtk.require('2.0')
import gtk
import gobject
import pango

from .. import fileformats as pgfileformats
from .. import path as pgpath
from .. import utils as pgutils

from . import cell_renderers as cell_renderers_
from . import entry_expander as entry_expander_
from . import entry_popup as entry_popup_
from . import entry_undo_context as entry_undo_context_

__all__ = [
  'ExtendedEntry',
  'FilenamePatternEntry',
  'FileExtensionEntry',
]


class ExtendedEntry(gtk.Entry):
  """
  This class is a subclass of `gtk.Entry` with additional capabilities:
  
  * undo/redo of text,
  * placeholder text,
  * expandable width of the entry.
  
  Attributes:
  
  * `undo_context` (read-only) - `EntryUndoContext` instance to handle undo/redo
    actions.
  
  * `placeholder_text` (read-only) - Placeholder text displayed if the entry is
    empty or matches the placeholder text. If `None`, the entry has no
    placeholder text.
  """
  
  def __init__(self, *args, **kwargs):
    """
    Parameters:
    
    * `minimum_width_chars` - Minimum width specified as a number of characters.
      The entry will not shrink below this width.
    
    * `maximum_width_chars` - Maximum width specified as a number of characters.
      The entry will not expand above this width.
    
    * `placeholder_text` - Text to display as a placeholder if the entry is
      empty. If `None`, do not display any placeholder.
    """
    self._minimum_width_chars = kwargs.pop('minimum_width_chars', -1)
    self._maximum_width_chars = kwargs.pop('maximum_width_chars', -1)
    self._placeholder_text = kwargs.pop('placeholder_text', None)
    
    super().__init__(*args, **kwargs)
    
    self._undo_context = entry_undo_context_.EntryUndoContext(self)
    self._popup = None
    self._expander = entry_expander_.EntryExpander(
      self, self._minimum_width_chars, self._maximum_width_chars)
    
    self._has_placeholder_text_assigned = False
    
    self.connect('focus-in-event', self._on_extended_entry_focus_in_event)
    self.connect('focus-out-event', self._on_extended_entry_focus_out_event)
    self.connect_after('realize', self._on_after_extended_entry_realize)
  
  @property
  def undo_context(self):
    return self._undo_context
  
  def assign_text(self, text, enable_undo=False):
    """
    Replace the current contents of the entry with the specified text.
    
    If the entry does not have focus and the text is empty or matches the
    placeholder text, assign the placeholder text.
     
    If `enable_undo` is `True`, add the assignment to the undo history.
    """
    if self.has_focus() or not self._should_assign_placeholder_text(text):
      self._unassign_placeholder_text()
      self._do_assign_text(text, enable_undo)
    else:
      self._assign_placeholder_text()
  
  def get_text(self):
    """
    If the entry text does not match the placeholder text, return the entry
    text (i.e. what `gtk.Entry.get_text()` would return), otherwise return an
    empty string.
    """
    if not self._has_placeholder_text_assigned:
      return super().get_text()
    else:
      return b''
  
  def _do_assign_text(self, text, enable_undo=False):
    """
    Use this method to set text instead of `assign_text()` if it is not desired
    to handle placeholder text assignment.
    """
    if self._popup is not None:
      self._popup.trigger_popup = False
    if not enable_undo:
      self._undo_context.undo_enabled = False
    
    if not isinstance(text, bytes):
      text = pgutils.safe_encode_gtk(text)
    
    self.set_text(text)
    
    if not enable_undo:
      self._undo_context.undo_enabled = True
    if self._popup is not None:
      self._popup.trigger_popup = True
  
  def _get_text_decoded(self):
    return pgutils.safe_decode_gtk(self.get_text())
  
  def _assign_placeholder_text(self):
    if self._placeholder_text is not None:
      self._has_placeholder_text_assigned = True
      
      # Delay font modification until after widget realization as the font may
      # have been different before the realization.
      if self.get_realized():
        self._modify_font_for_placeholder_text(gtk.STATE_INSENSITIVE, pango.STYLE_ITALIC)
      
      self._do_assign_text(self._placeholder_text)
  
  def _unassign_placeholder_text(self):
    if self._has_placeholder_text_assigned:
      self._has_placeholder_text_assigned = False
      self._modify_font_for_placeholder_text(gtk.STATE_NORMAL, pango.STYLE_NORMAL)
      self._do_assign_text(b'')
      self._popup.save_last_value()
  
  def _modify_font_for_placeholder_text(self, state_for_color, style):
    self.modify_text(gtk.STATE_NORMAL, self.style.fg[state_for_color])
    
    font_description = self.get_pango_context().get_font_description()
    font_description.set_style(style)
    self.modify_font(font_description)
  
  def _should_assign_placeholder_text(self, text):
    return (
      not text
      or (self._placeholder_text is not None and text == self._placeholder_text))
  
  def _on_extended_entry_focus_in_event(self, entry, event):
    self._unassign_placeholder_text()
  
  def _on_extended_entry_focus_out_event(self, entry, event):
    if self._should_assign_placeholder_text(self._get_text_decoded()):
      self._assign_placeholder_text()
  
  def _on_after_extended_entry_realize(self, entry):
    if self._should_assign_placeholder_text(self._get_text_decoded()):
      self._assign_placeholder_text()


class FilenamePatternEntry(ExtendedEntry):
  """
  This class is a subclass of `ExtendedEntry` used for the purpose of typing a
  pattern for filenames (e.g. for exported layers as separate images). A popup
  displaying the list of suggested items (components of the pattern) is
  displayed while typing.
  
  Additional attributes:
  
  * `popup` (read-only) - `EntryPopup` instance serving as the popup.
  """
  
  _BUTTON_MOUSE_LEFT = 1
  
  _COLUMNS = [
    _COLUMN_ITEM_NAMES,
    _COLUMN_ITEMS_TO_INSERT,
    _COLUMN_REGEX_TO_MATCH,
    _COLUMN_ITEM_DESCRIPTIONS] = (
      0, 1, 2, 3)
  
  _COLUMN_TYPES = [
    gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING]
  
  def __init__(self, suggested_items, *args, **kwargs):
    """
    Parameters:
    
    * `suggested_items` - List of
      `(item name displayed in popup, text to insert in entry,
        regular expression matching item name, description)`
      tuples describing each item.
    
    * `default_item` - The second element of an item from the `suggested_items`
      that is displayed as placeholder text, or `None` for no default item. This
      argument replaces the `placeholder_text` parameter from `ExtendedEntry`.
    """
    self._default_item_value = kwargs.pop('default_item', None)
    
    self._item_regexes_and_descriptions = {item[2]: item[3] for item in suggested_items}
    
    suggested_item_values = [item[1] for item in suggested_items]
    if (self._default_item_value is not None
        and self._default_item_value not in suggested_item_values):
      raise ValueError(
        'default item "{0}" not in the list of suggested items: {1}'.format(
          self._default_item_value, suggested_item_values))
    
    kwargs['placeholder_text'] = (
      suggested_items[suggested_item_values.index(self._default_item_value)][0]
      if self._default_item_value is not None else None)
    
    super().__init__(*args, **kwargs)
    
    self._cursor_position = 0
    self._cursor_position_before_assigning_from_row = None
    self._reset_cursor_position_before_assigning_from_row = True
    
    self._last_field_with_tooltip = ''
    
    self._pango_layout = pango.Layout(self.get_pango_context())
    
    self._popup = entry_popup_.EntryPopup(self, self._COLUMN_TYPES, suggested_items)
    self._popup.filter_rows_func = self._filter_suggested_items
    self._popup.on_assign_from_selected_row = self._on_assign_from_selected_row
    self._popup.on_assign_last_value = self._assign_last_value
    self._popup.on_row_left_mouse_button_press = self._on_row_left_mouse_button_press
    self._popup.on_entry_changed_show_popup_condition = self._on_entry_changed_condition
    self._popup.on_entry_key_press = self._on_entry_key_press
    self._popup.on_entry_after_assign_by_key_press = (
      self._on_entry_after_assign_by_key_press)
    
    self._create_field_tooltip()
    
    self._add_columns()
    
    self.connect('insert-text', self._on_filename_pattern_entry_insert_text)
    self.connect('delete-text', self._on_filename_pattern_entry_delete_text)
    self.connect(
      'notify::cursor-position', self._on_filename_pattern_entry_notify_cursor_position)
    self.connect('changed', self._on_filename_pattern_entry_changed)
    self.connect('focus-out-event', self._on_filename_pattern_entry_focus_out_event)
  
  @property
  def popup(self):
    return self._popup
  
  def _should_assign_placeholder_text(self, text):
    """
    Unlike the parent method, use the value of the suggested item rather than
    its display name to determine whether placeholder text should be assigned.
    """
    return (
      not text
      or (self._default_item_value is not None and text == self._default_item_value))
  
  def _create_field_tooltip(self):
    self._field_tooltip_window = gtk.Window(type=gtk.WINDOW_POPUP)
    self._field_tooltip_window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_TOOLTIP)
    self._field_tooltip_window.set_resizable(False)
    # This copies the style of GTK tooltips.
    self._field_tooltip_window.set_name('gtk-tooltips')
    
    self._field_tooltip_text = gtk.Label()
    self._field_tooltip_text.set_selectable(True)
    
    self._field_tooltip_hbox = gtk.HBox(homogeneous=False)
    self._field_tooltip_hbox.pack_start(
      self._field_tooltip_text, expand=False, fill=False)
    
    self._field_tooltip_frame = gtk.Frame()
    self._field_tooltip_frame.set_shadow_type(gtk.SHADOW_ETCHED_IN)
    self._field_tooltip_frame.add(self._field_tooltip_hbox)
    self._field_tooltip_frame.show_all()
    
    self._field_tooltip_window.add(self._field_tooltip_frame)
  
  def _add_columns(self):
    self._popup.tree_view.append_column(
      gtk.TreeViewColumn(None, gtk.CellRendererText(), text=self._COLUMN_ITEM_NAMES))
  
  def _on_filename_pattern_entry_insert_text(
        self, entry, new_text, new_text_length, position):
    self._cursor_position = self.get_position() + len(pgutils.safe_decode_gtk(new_text))
  
  def _on_filename_pattern_entry_delete_text(self, entry, start, end):
    self._cursor_position = start
  
  def _on_filename_pattern_entry_notify_cursor_position(self, entry, property_spec):
    self._cursor_position = self.get_position()
    
    field = pgpath.StringPattern.get_field_at_position(
      self._get_text_decoded(), self._cursor_position)
    
    if field is None:
      self._hide_field_tooltip()
      return
    
    matching_field_regex = pgpath.StringPattern.get_first_matching_field_regex(
      field, self._item_regexes_and_descriptions)
    
    if matching_field_regex not in self._item_regexes_and_descriptions:
      self._hide_field_tooltip()
      return
    
    if field != self._last_field_with_tooltip:
      self._last_field_with_tooltip = field
      force_update_position = True
    else:
      force_update_position = False
    
    self._show_field_tooltip(
      self._item_regexes_and_descriptions[matching_field_regex], force_update_position)
  
  def _show_field_tooltip(self, tooltip_text=None, force_update_position=False):
    if not self._field_tooltip_window.get_mapped() or force_update_position:
      if tooltip_text is None:
        tooltip_text = ''
      self._field_tooltip_text.set_markup(tooltip_text)
      self._field_tooltip_window.show()
      self._update_field_tooltip_position()
  
  def _hide_field_tooltip(self):
    if self._field_tooltip_window.get_mapped():
      self._field_tooltip_window.hide()
  
  def _update_field_tooltip_position(self):
    self._update_window_position(self._field_tooltip_window, place_above=True)
  
  def _update_window_position(
        self, window, move_with_text_cursor=True, place_above=False):
    entry_absolute_position = self.get_window().get_origin()
    
    if move_with_text_cursor:
      text_up_to_cursor_position = self._get_text_decoded()[:self._cursor_position]
      self._pango_layout.set_text(pgutils.safe_encode_gtk(text_up_to_cursor_position))
      
      x_offset = min(
        self._pango_layout.get_pixel_size()[0] + self.get_layout_offsets()[0],
        max(self.get_allocation().width - window.get_allocation().width, 0))
      
      x = entry_absolute_position[0] + x_offset
    else:
      x = entry_absolute_position[0]
    
    if not place_above:
      y = entry_absolute_position[1] + self.get_allocation().height
    else:
      y = entry_absolute_position[1] - window.get_allocation().height
    
    window.move(x, y)
  
  def _on_filename_pattern_entry_changed(self, entry):
    if self._reset_cursor_position_before_assigning_from_row:
      self._cursor_position_before_assigning_from_row = None
  
  def _on_filename_pattern_entry_focus_out_event(self, entry, event):
    self._hide_field_tooltip()
  
  def _filter_suggested_items(self, suggested_items, row_iter):
    item = suggested_items[row_iter][self._COLUMN_ITEMS_TO_INSERT]
    current_text = self._get_text_decoded()
    
    if (self._cursor_position > 0 and len(current_text) >= self._cursor_position
        and current_text[self._cursor_position - 1] == '[' and item and item[0] != '['):
      return False
    else:
      return True
  
  def _on_assign_from_selected_row(self, tree_model, selected_tree_iter):
    if self._cursor_position_before_assigning_from_row is None:
      self._cursor_position_before_assigning_from_row = self._cursor_position
    cursor_position = self._cursor_position_before_assigning_from_row
    
    suggested_item = str(tree_model[selected_tree_iter][self._COLUMN_ITEMS_TO_INSERT])
    last_assigned_entry_text = pgutils.safe_decode_gtk(self._popup.last_assigned_entry_text)
    
    if (cursor_position > 0 and len(last_assigned_entry_text) >= cursor_position
        and last_assigned_entry_text[cursor_position - 1] == '['):
      suggested_item = suggested_item[1:]
    
    self.assign_text(
      pgutils.safe_encode_gtk(
        (last_assigned_entry_text[:cursor_position] + suggested_item
         + last_assigned_entry_text[cursor_position:])))
    
    self.set_position(cursor_position + len(suggested_item))
    self._cursor_position = self.get_position()
    self._cursor_position_before_assigning_from_row = cursor_position
    
    return cursor_position, suggested_item
  
  def _assign_last_value(self, last_value):
    self._reset_cursor_position_before_assigning_from_row = False
    self._do_assign_text(last_value)
    self._reset_cursor_position_before_assigning_from_row = True
    
    if self._cursor_position_before_assigning_from_row is not None:
      self._cursor_position = self._cursor_position_before_assigning_from_row
    self.set_position(self._cursor_position)
    self._cursor_position_before_assigning_from_row = None
  
  def _on_entry_changed_condition(self):
    current_text = self._get_text_decoded()

    if current_text:
      if len(current_text) > 1 and len(current_text) >= self._cursor_position:
        return (
          current_text[self._cursor_position - 1] == '['
          and current_text[self._cursor_position - 2] != '['
          and not pgpath.StringPattern.get_field_at_position(
            current_text, self._cursor_position - 1))
      else:
        return current_text[0] == '['
    else:
      return True
  
  def _on_row_left_mouse_button_press(self):
    self._cursor_position_before_assigning_from_row = None
    
    position, text = self._popup.assign_from_selected_row()
    if position is not None and text:
      self.undo_context.undo_push([('insert', position, text)])
  
  def _on_entry_key_press(self, key_name, tree_path, stop_event_propagation):
    if key_name in ['Return', 'KP_Enter', 'Escape']:
      self._hide_field_tooltip()
      self._cursor_position_before_assigning_from_row = None
    
    return stop_event_propagation
  
  def _on_entry_after_assign_by_key_press(
        self, previous_position, previous_text, position, text):
    undo_push_list = []
    
    if previous_text:
      undo_push_list.append(('delete', previous_position, previous_text))
    
    if position is not None and text:
      undo_push_list.append(('insert', position, text))
    
    if undo_push_list:
      self.undo_context.undo_push(undo_push_list)


class FileExtensionEntry(ExtendedEntry):
  """
  This class is a subclass of `ExtendedEntry` used for the purpose of specifying
  a file extension.
  
  A popup displaying the list of available file formats in GIMP and the
  corresponding file extensions is displayed. If a row contains multiple file
  extensions, the user is able to select a particular file extension. By
  default, the first file extension in the row is used.
  
  Additional attributes:
  
  * `popup` (read-only) - `EntryPopup` instance serving as the popup.
  """
  
  _COLUMNS = [_COLUMN_DESCRIPTION, _COLUMN_EXTENSIONS] = (0, 1)
  # [string, list of strings]
  _COLUMN_TYPES = [gobject.TYPE_STRING, gobject.TYPE_PYOBJECT]
  
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    
    self._tree_view_columns_rects = []
    
    self._cell_renderer_description = None
    self._cell_renderer_extensions = None
    
    self._highlighted_extension_row = None
    self._highlighted_extension_index = None
    self._highlighted_extension = None
    
    self._extensions_separator_text_pixel_size = None
    self._extensions_text_pixel_rects = []
    
    self._popup = entry_popup_.EntryPopup(
      self, self._COLUMN_TYPES, self._get_file_formats(pgfileformats.file_formats))
    self._popup.filter_rows_func = self._filter_file_formats
    self._popup.on_assign_from_selected_row = self._on_assign_from_selected_row
    self._popup.on_assign_last_value = self._do_assign_text
    self._popup.on_row_left_mouse_button_press = self._on_row_left_mouse_button_press
    self._popup.on_entry_key_press_before_show_popup = (
      self._on_key_press_before_show_popup)
    self._popup.on_entry_key_press = self._on_tab_keys_pressed
    self._popup.on_entry_after_assign_by_key_press = (
      self._on_entry_after_assign_by_key_press)
    
    self._add_columns()
    
    self._popup.tree_view.connect(
      'motion-notify-event', self._on_tree_view_motion_notify_event)
    self._popup.tree_view.connect_after('realize', self._on_after_tree_view_realize)
    self._popup.tree_view.get_selection().connect(
      'changed', self._on_tree_selection_changed)
  
  @property
  def popup(self):
    return self._popup
  
  def _do_assign_text(self, *args, **kwargs):
    super()._do_assign_text(*args, **kwargs)
    self.set_position(-1)
  
  def _add_columns(self):
    def _add_column(
          cell_renderer, cell_renderer_property, column_number, column_title=None):
      column = gtk.TreeViewColumn(
        column_title, cell_renderer, **{cell_renderer_property: column_number})
      self._popup.tree_view.append_column(column)
    
    self._cell_renderer_description = gtk.CellRendererText()
    self._cell_renderer_extensions = cell_renderers_.CellRendererTextList()
    _add_column(self._cell_renderer_description, 'text', self._COLUMN_DESCRIPTION)
    _add_column(self._cell_renderer_extensions, 'markup-list', self._COLUMN_EXTENSIONS)
  
  def _on_tree_view_motion_notify_event(self, tree_view, event):
    self._highlight_extension_at_pos(int(event.x), int(event.y))
  
  def _on_after_tree_view_realize(self, tree_view):
    self._extensions_separator_text_pixel_size = self._get_text_pixel_size(
      self._cell_renderer_extensions.get_property('text-list-separator'),
      pango.Layout(self._popup.tree_view.get_pango_context()))
    
    self._fill_extensions_text_pixel_rects()
    
    self._tree_view_columns_rects = [
      self._popup.tree_view.get_cell_area((0,), self._popup.tree_view.get_column(column))
      for column in self._COLUMNS]
  
  def _fill_extensions_text_pixel_rects(self):
    pango_layout = pango.Layout(self._popup.tree_view.get_pango_context())
    
    for file_format in self._popup.rows:
      file_extensions = file_format[1]
      
      if len(file_extensions) > 1:
        text_pixel_rects = self._get_text_pixel_rects(
          file_extensions, pango_layout, self._extensions_separator_text_pixel_size[0])
        for rect in text_pixel_rects:
          rect.x += self._cell_renderer_extensions.get_property('xpad')
          rect.x += self._popup.tree_view.style_get_property('horizontal-separator')
          rect.x += (
            self._popup.tree_view.get_column(self._COLUMN_EXTENSIONS).get_spacing())
          
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
  
  def _on_tree_selection_changed(self, tree_selection):
    self._unhighlight_extension()
  
  def _filter_file_formats(self, file_formats, row_iter):
    return self._entry_text_matches_row(self._get_text_decoded(), file_formats, row_iter)
  
  def _entry_text_matches_row(
        self, entry_text, file_formats, row_iter, full_match=False):
    extensions = file_formats[row_iter][self._COLUMN_EXTENSIONS]
    
    if full_match:
      return any(entry_text.lower() == extension.lower() for extension in extensions)
    else:
      return any(entry_text.lower() in extension.lower() for extension in extensions)
  
  def _on_assign_from_selected_row(
        self, tree_model, selected_tree_iter, extension_index=0):
    extensions = tree_model[selected_tree_iter][self._COLUMN_EXTENSIONS]
    if extension_index > len(extensions):
      extension_index = len(extensions) - 1
    self._do_assign_text(extensions[extension_index])
    
    return 0, extensions[extension_index]
  
  def _on_row_left_mouse_button_press(self):
    previous_position, previous_text = 0, self.get_text()
    
    if self._highlighted_extension_index is None:
      position, text = self._popup.assign_from_selected_row()
    else:
      self._do_assign_text(self._highlighted_extension)
      position, text = 0, self._highlighted_extension
    
    self._undo_push(previous_position, previous_text, position, text)
  
  def _on_key_press_before_show_popup(self):
    self._unhighlight_extension()
  
  def _on_tab_keys_pressed(self, key_name, selected_tree_path, stop_event_propagation):
    if key_name in ['Tab', 'KP_Tab', 'ISO_Left_Tab']:
      # Tree paths can sometimes point at the first row even though no row is
      # selected, hence the `tree_iter` usage.
      unused_, tree_iter = self._popup.tree_view.get_selection().get_selected()
      
      if tree_iter is not None:
        if key_name in ['Tab', 'KP_Tab']:
          self._highlight_extension_next(selected_tree_path)
        elif key_name == 'ISO_Left_Tab':    # Shift + Tab
          self._highlight_extension_previous(selected_tree_path)
        
        previous_position, previous_text = 0, self.get_text()
        
        self._do_assign_text(self._highlighted_extension)
        
        self._on_entry_after_assign_by_key_press(
          previous_position, previous_text, 0, self._highlighted_extension)
        
        return True
    
    return stop_event_propagation
  
  def _on_entry_after_assign_by_key_press(
        self, previous_position, previous_text, position, text):
    self._undo_push(previous_position, previous_text, position, text)
  
  def _undo_push(self, previous_position, previous_text, position, text):
    undo_push_list = []
    
    if previous_text:
      undo_push_list.append(('delete', previous_position, previous_text))
    
    if position is not None and text:
      undo_push_list.append(('insert', position, text))
    
    if undo_push_list:
      self.undo_context.undo_push(undo_push_list)
  
  def _highlight_extension_next(self, selected_row_path):
    def _select_next_extension(highlighted_extension_index, len_extensions):
      return (highlighted_extension_index + 1) % len_extensions
    
    self._highlight_extension(selected_row_path, _select_next_extension)
  
  def _highlight_extension_previous(self, selected_row_path):
    def _select_previous_extension(highlighted_extension_index, len_extensions):
      return (highlighted_extension_index - 1) % len_extensions
    
    self._highlight_extension(selected_row_path, _select_previous_extension)
  
  def _highlight_extension(self, selected_row_path, extension_index_selection_func):
    if selected_row_path is not None:
      self._unhighlight_extension_proper()
      
      row_path = self._popup.rows_filtered.convert_path_to_child_path(selected_row_path)
      self._highlighted_extension_row = row_path[0]
      
      extensions = self._popup.rows[row_path][self._COLUMN_EXTENSIONS]
      if len(extensions) <= 1:
        # Do not highlight any extension.
        if not extensions:
          self._highlighted_extension = ''
        elif len(extensions) == 1:
          self._highlighted_extension = extensions[0]
        
        return
      
      if self._highlighted_extension_index is None:
        self._highlighted_extension_index = 0
      
      self._highlighted_extension_index = extension_index_selection_func(
        self._highlighted_extension_index, len(extensions))
      
      self._highlight_extension_proper()
      
      self._popup.refresh_row(selected_row_path)
  
  def _highlight_extension_at_pos(self, x, y):
    is_in_extensions_column = (
      x >= self._tree_view_columns_rects[self._COLUMN_EXTENSIONS].x)
    if not is_in_extensions_column:
      if self._highlighted_extension is not None:
        self._unhighlight_extension()
      return
    
    path_params = self._popup.tree_view.get_path_at_pos(x, y)
    if path_params is None:
      return
    
    selected_path_unfiltered = (
      self._popup.rows_filtered.convert_path_to_child_path(path_params[0]))
    extension_index = (
      self._get_extension_index_at_pos(path_params[2], selected_path_unfiltered[0]))
    
    if extension_index == self._highlighted_extension_index:
      return
    
    if extension_index is not None:
      self._highlight_extension_at_index(path_params[0], extension_index)
    else:
      self._unhighlight_extension()
  
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
  
  def _highlight_extension_at_index(self, selected_row_path, extension_index):
    if selected_row_path is not None:
      self._unhighlight_extension_proper()
      
      row_path = self._popup.rows_filtered.convert_path_to_child_path(selected_row_path)
      
      self._highlighted_extension_row = row_path[0]
      self._highlighted_extension_index = extension_index
      
      self._highlight_extension_proper()
      
      self._popup.refresh_row(selected_row_path)
  
  def _highlight_extension_proper(self):
    extensions = (
      self._popup.rows[self._highlighted_extension_row][self._COLUMN_EXTENSIONS])
    
    self._highlighted_extension = extensions[self._highlighted_extension_index]
    
    bg_color = self._popup.tree_view.style.bg[gtk.STATE_SELECTED]
    fg_color = self._popup.tree_view.style.fg[gtk.STATE_SELECTED]
    
    extensions[self._highlighted_extension_index] = (
      '<span background="{0}" foreground="{1}">{2}</span>'.format(
        bg_color.to_string(),
        fg_color.to_string(),
        extensions[self._highlighted_extension_index]))
  
  def _unhighlight_extension(self):
    self._unhighlight_extension_proper()
    
    if self._highlighted_extension_row is not None:
      self._popup.refresh_row((self._highlighted_extension_row,), is_path_filtered=False)
    
    self._highlighted_extension_row = None
    self._highlighted_extension_index = None
  
  def _unhighlight_extension_proper(self):
    if (self._highlighted_extension_row is not None
        and self._highlighted_extension_index is not None):
      extensions = (
        self._popup.rows[self._highlighted_extension_row][self._COLUMN_EXTENSIONS])
      if self._highlighted_extension is not None:
        extensions[self._highlighted_extension_index] = self._highlighted_extension
        self._highlighted_extension = None

  @staticmethod
  def _get_file_formats(file_formats):
    return [[file_format.description, file_format.file_extensions]
            for file_format in file_formats if file_format.is_installed()]
  
  def _get_text_pixel_size(self, text, pango_layout):
    pango_layout.set_text(text)
    return pango_layout.get_pixel_size()
  
  def _get_text_pixel_rects(self, file_extensions, pango_layout, separator_pixel_width):
    text_pixel_rects = []
    
    extension_x = 0
    for extension in file_extensions:
      extension_pixel_size = self._get_text_pixel_size(extension, pango_layout)
      text_pixel_rects.append(gtk.gdk.Rectangle(extension_x, 0, *extension_pixel_size))
      
      extension_x += extension_pixel_size[0] + separator_pixel_width
    
    return text_pixel_rects


gobject.type_register(ExtendedEntry)
gobject.type_register(FilenamePatternEntry)
gobject.type_register(FileExtensionEntry)
