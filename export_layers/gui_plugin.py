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

import array
import collections
import contextlib
import functools
import os
import traceback

import pygtk
pygtk.require("2.0")
import gtk
import gobject
import pango

import gimp
import gimpenums
import gimpui

pdb = gimp.pdb

import export_layers.pygimplib as pygimplib

from export_layers.pygimplib import constants
from export_layers.pygimplib import overwrite
from export_layers.pygimplib import pggui
from export_layers.pygimplib import pgsetting
from export_layers.pygimplib import pgsettinggroup
from export_layers.pygimplib import pgsettingpersistor

from export_layers import exportlayers
from export_layers import settings_plugin

#===============================================================================


def display_message(message, message_type, parent=None, buttons=gtk.BUTTONS_OK, message_in_text_view=False):
  return pggui.display_message(
    message,
    message_type,
    title=pygimplib.config.PLUGIN_TITLE,
    parent=parent,
    buttons=buttons,
    message_in_text_view=message_in_text_view
  )


def display_exception_message(exception_message, parent=None):
  pggui.display_exception_message(
    exception_message,
    plugin_title=pygimplib.config.PLUGIN_TITLE,
    report_uri_list=pygimplib.config.BUG_REPORT_URI_LIST,
    parent=parent
  )


def _format_export_error_message(exception):
  error_message = _(
    "Sorry, but the export was unsuccessful. You can try exporting again if you fix the issue described below.")
  if not exception.message.endswith("."):
    exception.message += "."
  error_message += "\n" + str(exception)
  return error_message


def _return_none_func(*args, **kwargs):
  return None


#===============================================================================


@contextlib.contextmanager
def _handle_gui_in_export(run_mode, image, layer, output_filename, window):
  should_manipulate_window = run_mode == gimpenums.RUN_INTERACTIVE
  
  if should_manipulate_window:
    window.hide()
  while gtk.events_pending():
    gtk.main_iteration()
  
  try:
    yield
  finally:
    if should_manipulate_window:
      window.show()
    while gtk.events_pending():
      gtk.main_iteration()


#===============================================================================


class ExportPreview(object):
  
  def __init__(self):
    self._update_locked = False
    self._lock_keys = set()
  
  def update(self):
    """
    Update the export preview if update is not locked (see `lock_update`).
    """
    
    pass
  
  def lock_update(self, lock, key=None):
    """
    If `lock` is True, calling `update` will have no effect. Passing False to
    `lock` will enable updating the preview again.
    
    If `key` is specified to lock the update, the same key must be specified to
    unlock the preview. Multiple keys can be used to lock the preview; to unlock
    the preview, call this method with each of the keys.
    
    If `key` is specified and `lock` is False and the key was not used to lock
    the preview before, nothing happens.
    
    If `key` is None, lock/unlock the preview regardless of which function
    called this method. Passing None also removes previous keys that were used
    to lock the preview.
    """
    
    if key is None:
      self._lock_keys.clear()
      self._update_locked = lock
    else:
      if lock:
        self._lock_keys.add(key)
      else:
        if key in self._lock_keys:
          self._lock_keys.remove(key)
      
      self._update_locked = bool(self._lock_keys)


#===============================================================================


class ExportNamePreview(ExportPreview):
  
  _VBOX_PADDING = 5
  
  _COLUMNS = (
    _COLUMN_ICON_LAYER, _COLUMN_ICON_TAG_VISIBLE, _COLUMN_LAYER_NAME_SENSITIVE, _COLUMN_LAYER_NAME,
    _COLUMN_LAYER_ID) = ([0, gtk.gdk.Pixbuf], [1, bool], [2, bool], [3, bytes], [4, int])
  
  _ICON_IMAGE_PATH = os.path.join(pygimplib.config.PLUGIN_PATH, "icon_image.png")
  _ICON_TAG_PATH = os.path.join(pygimplib.config.PLUGIN_PATH, "icon_tag.png")
  
  def __init__(self, layer_exporter, initial_layer_tree=None, collapsed_items=None, selected_items=None,
               on_selection_changed_func=None, on_after_update_func=None, on_after_edit_tags_func=None):
    super(ExportNamePreview, self).__init__()
    
    self._layer_exporter = layer_exporter
    self._initial_layer_tree = initial_layer_tree
    self._collapsed_items = collapsed_items if collapsed_items is not None else set()
    self._selected_items = selected_items if selected_items is not None else []
    self._on_selection_changed_func = (
      on_selection_changed_func if on_selection_changed_func is not None else lambda *args: None)
    self._on_after_update_func = on_after_update_func if on_after_update_func is not None else lambda *args: None
    self._on_after_edit_tags_func = (
      on_after_edit_tags_func if on_after_edit_tags_func is not None else lambda *args: None)
    
    self._tree_iters = collections.defaultdict(lambda: None)
    
    self._row_expand_collapse_interactive = True
    self._toggle_tag_interactive = True
    self._clearing_preview = False
    self._row_select_interactive = True
    self._initial_scroll_to_selection = True
    
    self._init_gui()
    
    self._widget = self._vbox
  
  def update(self, reset_completely=False):
    """
    Update the preview (filter layers, modify layer tree, etc.).
    
    If `reset_completely` is True, perform full update (add new layers, remove
    non-existent layers, etc.).
    """
    
    if not self._update_locked:
      self.clear()
      self._fill_preview(reset_completely)
      self._set_expanded_items()
      self._set_selection()
      self._tree_view.columns_autosize()
      
      self._on_after_update_func()
  
  def clear(self):
    """
    Clear the entire preview.
    """
    
    self._clearing_preview = True
    self._tree_model.clear()
    self._clearing_preview = False
  
  def set_collapsed_items(self, collapsed_items):
    """
    Set the collapsed state of items in the preview.
    """
    
    self._collapsed_items = collapsed_items
    self._set_expanded_items()
  
  def set_selected_items(self, selected_items):
    """
    Set the selection of items in the preview.
    """
    
    self._selected_items = selected_items
    self._set_selection()
  
  def get_layer_elems_from_selected_rows(self):
    return [self._layer_exporter.layer_tree[layer_id]
            for layer_id in self._get_layer_ids_in_current_selection()]
  
  def get_layer_elem_from_cursor(self):
    tree_path, _unused = self._tree_view.get_cursor()
    if tree_path is not None:
      layer_id = self._get_layer_id(self._tree_model.get_iter(tree_path))
      return self._layer_exporter.layer_tree[layer_id]
    else:
      return None
  
  @property
  def widget(self):
    return self._widget
  
  @property
  def tree_view(self):
    return self._tree_view
  
  @property
  def collapsed_items(self):
    return self._collapsed_items
  
  @property
  def selected_items(self):
    return self._selected_items
  
  def _init_gui(self):
    self._tree_model = gtk.TreeStore(*[column[1] for column in self._COLUMNS])
    
    self._tree_view = gtk.TreeView(model=self._tree_model)
    self._tree_view.set_headers_visible(False)
    self._tree_view.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
    
    self._init_icons()
    
    self._init_tags_menu()
    
    column = gtk.TreeViewColumn(b"")
    
    cell_renderer_icon_layer = gtk.CellRendererPixbuf()
    column.pack_start(cell_renderer_icon_layer, expand=False)
    column.set_attributes(cell_renderer_icon_layer, pixbuf=self._COLUMN_ICON_LAYER[0])
    
    cell_renderer_icon_tag = gtk.CellRendererPixbuf()
    cell_renderer_icon_tag.set_property("pixbuf", self._icons['tag'])
    column.pack_start(cell_renderer_icon_tag, expand=False)
    column.set_attributes(cell_renderer_icon_tag, visible=self._COLUMN_ICON_TAG_VISIBLE[0])
    
    cell_renderer_layer_name = gtk.CellRendererText()
    column.pack_start(cell_renderer_layer_name, expand=False)
    column.set_attributes(
      cell_renderer_layer_name, text=self._COLUMN_LAYER_NAME[0], sensitive=self._COLUMN_LAYER_NAME_SENSITIVE[0])
    
    self._tree_view.append_column(column)
    
    self._preview_label = gtk.Label(_("Preview"))
    self._preview_label.set_alignment(0.02, 0.5)
    
    self._scrolled_window = gtk.ScrolledWindow()
    self._scrolled_window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    self._scrolled_window.add(self._tree_view)
    
    self._vbox = gtk.VBox(homogeneous=False)
    self._vbox.pack_start(self._preview_label, expand=False, fill=False, padding=self._VBOX_PADDING)
    self._vbox.pack_start(self._scrolled_window)
    
    self._tree_view.connect("row-collapsed", self._on_tree_view_row_collapsed)
    self._tree_view.connect("row-expanded", self._on_tree_view_row_expanded)
    self._tree_view.get_selection().connect("changed", self._on_tree_selection_changed)
    self._tree_view.connect("event", self._on_tree_view_right_button_press)
  
  def _init_icons(self):
    self._icons = {}
    self._icons['layer_group'] = self._tree_view.render_icon(gtk.STOCK_DIRECTORY, gtk.ICON_SIZE_MENU)
    self._icons['layer'] = gtk.gdk.pixbuf_new_from_file_at_size(
      self._ICON_IMAGE_PATH, -1, self._icons['layer_group'].props.height)
    self._icons['tag'] = gtk.gdk.pixbuf_new_from_file_at_size(
      self._ICON_TAG_PATH, -1, self._icons['layer_group'].props.height)
    
    self._icons['merged_layer_group'] = self._icons['layer'].copy()
    
    scaling_factor = 0.8
    width_unscaled = self._icons['layer_group'].props.width
    width = int(width_unscaled * scaling_factor)
    height_unscaled = self._icons['layer_group'].props.height
    height = int(height_unscaled * scaling_factor)
    x_offset_unscaled = self._icons['merged_layer_group'].props.width - self._icons['layer_group'].props.width
    x_offset = x_offset_unscaled + width_unscaled - width
    y_offset_unscaled = self._icons['merged_layer_group'].props.height - self._icons['layer_group'].props.height
    y_offset = y_offset_unscaled + height_unscaled - height
    
    self._icons['layer_group'].composite(self._icons['merged_layer_group'],
      x_offset, y_offset, width, height, x_offset, y_offset,
      scaling_factor, scaling_factor, gtk.gdk.INTERP_BILINEAR, 255)
  
  def _init_tags_menu(self):
    self._tags_menu = gtk.Menu()
    self._tags_menu_items = {}
    self._tags_names = {}
    
    for tag, tag_name in self._layer_exporter.SUPPORTED_TAGS.items():
      self._tags_menu_items[tag] = gtk.CheckMenuItem(tag_name)
      self._tags_names[tag_name] = tag
      self._tags_menu_items[tag].connect("toggled", self._on_tags_menu_item_toggled)
      self._tags_menu.append(self._tags_menu_items[tag])
    
    self._tags_menu.show_all()
  
  def _on_tree_view_row_collapsed(self, widget, tree_iter, tree_path):
    if self._row_expand_collapse_interactive:
      self._collapsed_items.add(self._get_layer_id(tree_iter))
      self._tree_view.columns_autosize()
  
  def _on_tree_view_row_expanded(self, widget, tree_iter, tree_path):
    if self._row_expand_collapse_interactive:
      layer_id = self._get_layer_id(tree_iter)
      if layer_id in self._collapsed_items:
        self._collapsed_items.remove(layer_id)
      
      self._set_expanded_items(tree_path)
      
      self._tree_view.columns_autosize()
  
  def _on_tree_selection_changed(self, widget):
    if not self._clearing_preview and self._row_select_interactive:
      self._selected_items = self._get_layer_ids_in_current_selection()
      self._on_selection_changed_func()
  
  def _on_tree_view_right_button_press(self, widget, event):
    if event.type == gtk.gdk.BUTTON_PRESS and event.button == 3:
      layer_ids = []
      stop_event_propagation = False
      
      # Get the current selection. We can't use `TreeSelection.get_selection()`
      # because this event is fired before the selection is updated.
      selection_at_pos = self._tree_view.get_path_at_pos(int(event.x), int(event.y))
      
      if selection_at_pos is not None and self._tree_view.get_selection().count_selected_rows() > 1:
        layer_ids = self._get_layer_ids_in_current_selection()
        stop_event_propagation = True
      else:
        if selection_at_pos is not None:
          tree_iter = self._tree_model.get_iter(selection_at_pos[0])
          layer_ids = [self._get_layer_id(tree_iter)]
      
      self._toggle_tag_interactive = False
      
      if len(layer_ids) == 1:
        layer_id = layer_ids[0]
        layer_elem = self._layer_exporter.layer_tree[layer_id]
        for tag in self._layer_exporter.SUPPORTED_TAGS:
          self._tags_menu_items[tag].set_active(tag in layer_elem.tags)
      elif len(layer_ids) > 1:
        layer_elems = [
          self._layer_exporter.layer_tree[layer_id] for layer_id in layer_ids]
        for tag, tags_menu_item in self._tags_menu_items.items():
          tags_menu_item.set_active(all(tag in layer_elem.tags for layer_elem in layer_elems))
      
      self._toggle_tag_interactive = True
      
      if len(layer_ids) >= 1:
        self._tags_menu.popup(None, None, None, event.button, event.time)
      
      return stop_event_propagation
  
  def _on_tags_menu_item_toggled(self, tags_menu_item):
    if self._toggle_tag_interactive:
      pdb.gimp_image_undo_group_start(self._layer_exporter.image)
      
      for layer_id in self._get_layer_ids_in_current_selection():
        layer_elem = self._layer_exporter.layer_tree[layer_id]
        tag = self._tags_names[tags_menu_item.get_label()]
        
        if tags_menu_item.get_active():
          self._layer_exporter.layer_tree.add_tag(layer_elem, tag)
        else:
          self._layer_exporter.layer_tree.remove_tag(layer_elem, tag)
      
      pdb.gimp_image_undo_group_end(self._layer_exporter.image)
      
      # Modifying just one layer could result in renaming other layers differently,
      # hence update the whole preview.
      self.update()
      
      self._on_after_edit_tags_func()
  
  def _get_layer_ids_in_current_selection(self):
    _unused, tree_paths = self._tree_view.get_selection().get_selected_rows()
    return [self._get_layer_id(self._tree_model.get_iter(tree_path)) for tree_path in tree_paths]
  
  def _get_layer_id(self, tree_iter):
    return self._tree_model.get_value(tree_iter, column=self._COLUMN_LAYER_ID[0])
  
  def _fill_preview(self, reset_completely=False):
    if not reset_completely:
      if self._initial_layer_tree is not None:
        layer_tree = self._initial_layer_tree
        self._initial_layer_tree = None
      else:
        if self._layer_exporter.layer_tree is not None:
          self._layer_exporter.layer_tree.reset_item_elements()
        layer_tree = self._layer_exporter.layer_tree
    else:
      layer_tree = None
    
    with self._layer_exporter.modify_export_settings({'export_only_selected_layers': False}):
      self._layer_exporter.export_layers(operations=['layer_name'], layer_tree=layer_tree)
    
    self._tree_iters.clear()
    
    self._enable_tagged_layers()
    
    for layer_elem in self._layer_exporter.layer_tree:
      if self._layer_exporter.export_settings['layer_groups_as_folders'].value:
        self._insert_parent_item_elems(layer_elem)
      self._insert_item_elem(layer_elem)
    
    self._set_sensitive_tagged_layers()
  
  def _insert_item_elem(self, item_elem):
    if item_elem.parent:
      parent_tree_iter = self._tree_iters[item_elem.parent.item.ID]
    else:
      parent_tree_iter = None
    
    tree_iter = self._tree_model.append(
      parent_tree_iter,
      [self._get_icon_from_item_elem(item_elem),
       self._has_supported_tags(item_elem),
       True,
       item_elem.name.encode(constants.GTK_CHARACTER_ENCODING),
       item_elem.item.ID])
    self._tree_iters[item_elem.item.ID] = tree_iter
    
    return tree_iter
  
  def _insert_parent_item_elems(self, item_elem):
    for parent_elem in item_elem.parents:
      if not self._tree_iters[parent_elem.item.ID]:
        self._insert_item_elem(parent_elem)
  
  def _enable_tagged_layers(self):
    if self._layer_exporter.export_settings['tagged_layers_mode'].is_item('special'):
      self._layer_exporter.layer_tree.filter.remove_rule(
        exportlayers.LayerFilterRules.has_no_tags, raise_if_not_found=False)
  
  def _set_sensitive_tagged_layers(self):
    if self._layer_exporter.export_settings['tagged_layers_mode'].is_item('special'):
      with self._layer_exporter.layer_tree.filter.add_rule_temp(
        exportlayers.LayerFilterRules.has_tags, *self._layer_exporter.SUPPORTED_TAGS.keys()):
        
        for layer_elem in self._layer_exporter.layer_tree:
          self._set_item_elem_sensitive(layer_elem, False)
          if self._layer_exporter.export_settings['layer_groups_as_folders'].value:
            self._set_parent_item_elem_sensitive(layer_elem)
  
  def _get_item_elem_sensitive(self, item_elem):
    return self._tree_model.get_value(self._tree_iters[item_elem.item.ID], self._COLUMN_LAYER_NAME_SENSITIVE[0])
  
  def _set_item_elem_sensitive(self, item_elem, sensitive):
    self._tree_model.set_value(
      self._tree_iters[item_elem.item.ID], self._COLUMN_LAYER_NAME_SENSITIVE[0], sensitive)
  
  def _set_parent_item_elem_sensitive(self, item_elem):
    for parent_elem in reversed(item_elem.parents):
      parent_sensitive = any(
        self._get_item_elem_sensitive(child_elem) for child_elem in parent_elem.children
        if child_elem.item.ID in self._tree_iters)
      self._set_item_elem_sensitive(parent_elem, parent_sensitive)
  
  def _get_icon_from_item_elem(self, item_elem):
    if item_elem.item_type == item_elem.ITEM:
      return self._icons['layer']
    elif item_elem.item_type in [item_elem.NONEMPTY_GROUP, item_elem.EMPTY_GROUP]:
      if not self._layer_exporter.export_settings['merge_layer_groups'].value:
        return self._icons['layer_group']
      else:
        return self._icons['merged_layer_group']
    else:
      return None
  
  def _has_supported_tags(self, item_elem):
    return bool(item_elem.tags) and any(tag in self._layer_exporter.SUPPORTED_TAGS for tag in item_elem.tags)
  
  def _set_expanded_items(self, tree_path=None):
    """
    Set the expanded state of items in the tree view.
    
    If `tree_path` is specified, set the states only for the child elements in
    the tree path, otherwise set the states in the whole tree view.
    """
    
    self._row_expand_collapse_interactive = False
    
    if tree_path is None:
      self._tree_view.expand_all()
    else:
      self._tree_view.expand_row(tree_path, True)
    
    self._remove_no_longer_valid_collapsed_items()
    
    for layer_id in self._collapsed_items:
      if layer_id in self._tree_iters:
        layer_elem_tree_iter = self._tree_iters[layer_id]
        if layer_elem_tree_iter is None:
          continue
        
        layer_elem_tree_path = self._tree_model.get_path(layer_elem_tree_iter)
        if tree_path is None or self._tree_view.row_expanded(layer_elem_tree_path):
          self._tree_view.collapse_row(layer_elem_tree_path)
    
    self._row_expand_collapse_interactive = True
  
  def _remove_no_longer_valid_collapsed_items(self):
    if self._layer_exporter.layer_tree is None:
      return
    
    self._layer_exporter.layer_tree.is_filtered = False
    self._collapsed_items = set(
      [collapsed_item for collapsed_item in self._collapsed_items
       if collapsed_item in self._layer_exporter.layer_tree])
    self._layer_exporter.layer_tree.is_filtered = True
  
  def _set_selection(self):
    self._row_select_interactive = False
    
    self._selected_items = [item for item in self._selected_items if item in self._tree_iters]
    
    for item in self._selected_items:
      tree_iter = self._tree_iters[item]
      if tree_iter is not None:
        self._tree_view.get_selection().select_iter(tree_iter)
    
    if self._initial_scroll_to_selection:
      self._set_initial_scroll_to_selection()
      self._initial_scroll_to_selection = False
    
    self._row_select_interactive = True
  
  def _set_initial_scroll_to_selection(self):
    if self._selected_items:
      first_selected_item_path = self._tree_model.get_path(self._tree_iters[self._selected_items[0]])
      if first_selected_item_path is not None:
        self._tree_view.scroll_to_cell(first_selected_item_path, None, True, 0.5, 0.0)


#===============================================================================


class ExportImagePreview(ExportPreview):
  
  _BOTTOM_WIDGETS_PADDING = 5
  _IMAGE_PREVIEW_PADDING = 3
  
  _MAX_PREVIEW_SIZE_PIXELS = 1024
  
  _PREVIEW_ALPHA_CHECK_SIZE = 4
  
  def __init__(self, layer_exporter, initial_layer_tree=None, initial_previered_layer_id=None):
    super(ExportImagePreview, self).__init__()
    
    self._layer_exporter = layer_exporter
    self._initial_layer_tree = initial_layer_tree
    self._initial_previewed_layer_id = initial_previered_layer_id
    
    self._layer_elem = None
    
    self._preview_pixbuf = None
    self._previous_preview_pixbuf_width = None
    self._previous_preview_pixbuf_height = None
    
    self.draw_checkboard_alpha_background = True
    
    self._is_allocated_size = False
    self._is_updating = False
    
    self._preview_width = None
    self._preview_height = None
    self._preview_scaling_factor = None
    
    self._init_gui()
    
    self._PREVIEW_ALPHA_CHECK_COLOR_FIRST, self._PREVIEW_ALPHA_CHECK_COLOR_SECOND = (
      int(hex(shade)[2:] * 4, 16) for shade in gimp.checks_get_shades(gimp.check_type()))
    
    self._placeholder_image_size = gtk.icon_size_lookup(self._placeholder_image.get_property("icon-size"))
    
    self._preview_image.connect("size-allocate", self._on_preview_image_size_allocate)
    self._vbox.connect("size-allocate", self._on_vbox_size_allocate)
    
    self._widget = self._vbox
  
  def update(self):
    if self._update_locked:
      return
    
    self.layer_elem = self._set_initial_layer_elem(self.layer_elem)
    if self.layer_elem is None:
      return
    
    if not self._layer_elem_matches_filter(self.layer_elem):
      return
    
    if not pdb.gimp_item_is_valid(self.layer_elem.item):
      self.clear()
      return
    
    self._is_updating = True
    
    self._placeholder_image.hide()
    self._preview_image.show()
    self._set_layer_name_label(self.layer_elem.name)
    
    # Make sure that the correct size is allocated to the image.
    while gtk.events_pending():
      gtk.main_iteration()
    
    with self._redirect_messages():
      preview_pixbuf = self._get_in_memory_preview(self.layer_elem.item)
    
    if preview_pixbuf is not None:
      self._preview_image.set_from_pixbuf(preview_pixbuf)
    
    self._is_updating = False
  
  def clear(self):
    self.layer_elem = None
    self._preview_image.clear()
    self._preview_image.hide()
    self._show_placeholder_image()
  
  def resize(self, update_when_larger_than_image_size=False):
    """
    Resize the preview if the widget is smaller than the previewed image so that
    the image fits the widget. If the widget is larger than the image and
    `update_when_larger_than_image_size` is True, call `update()`.
    """
    
    allocation = self._preview_image.get_allocation()
    
    if self._preview_pixbuf is None:
      return
    
    if (update_when_larger_than_image_size and
        (allocation.width > self._preview_pixbuf.get_width() and
         allocation.height > self._preview_pixbuf.get_height())):
      self.update()
    else:
      if not self._is_updating and self._preview_image.get_mapped():
        self._resize_preview(allocation, self._preview_pixbuf)
  
  def update_layer_elem(self):
    if (self.layer_elem is not None and
        self._layer_exporter.layer_tree is not None and
        self.layer_elem.item.ID in self._layer_exporter.layer_tree):
      layer_elem = self._layer_exporter.layer_tree[self.layer_elem.item.ID]
      if self._layer_exporter.layer_tree.filter.is_match(layer_elem):
        self.layer_elem = layer_elem
        self._set_layer_name_label(self.layer_elem.name)
  
  @property
  def layer_elem(self):
    return self._layer_elem
  
  @layer_elem.setter
  def layer_elem(self, value):
    self._layer_elem = value
    if value is None:
      self._preview_pixbuf = None
      self._previous_preview_pixbuf_width = None
      self._previous_preview_pixbuf_height = None
  
  @property
  def widget(self):
    return self._widget
  
  def _init_gui(self):
    self._preview_image = gtk.Image()
    self._preview_image.set_no_show_all(True)
    
    self._placeholder_image = gtk.Image()
    self._placeholder_image.set_from_stock(gtk.STOCK_DIALOG_QUESTION, gtk.ICON_SIZE_DIALOG)
    self._placeholder_image.set_no_show_all(True)
    
    self._label_layer_name = gtk.Label()
    self._label_layer_name.set_ellipsize(pango.ELLIPSIZE_MIDDLE)
    
    self._vbox = gtk.VBox(homogeneous=False)
    self._vbox.pack_start(self._preview_image, expand=True, fill=True, padding=self._IMAGE_PREVIEW_PADDING)
    self._vbox.pack_start(self._placeholder_image, expand=True, fill=True, padding=self._IMAGE_PREVIEW_PADDING)
    self._vbox.pack_start(self._label_layer_name, expand=False, fill=True, padding=self._BOTTOM_WIDGETS_PADDING)
    
    self._show_placeholder_image()
  
  def _set_initial_layer_elem(self, layer_elem):
    if layer_elem is None:
      if (self._layer_exporter.layer_tree is not None and
          self._initial_previewed_layer_id in self._layer_exporter.layer_tree):
        layer_elem = self._layer_exporter.layer_tree[self._initial_previewed_layer_id]
        self._initial_previewed_layer_id = None
        return layer_elem
      else:
        self._initial_previewed_layer_id = None
        return None
    else:
      return layer_elem
  
  def _layer_elem_matches_filter(self, layer_elem):
    def _not_treated_specially_and_has_tags(layer_elem):
      return not (self._layer_exporter.export_settings['tagged_layers_mode'].is_item('special') and
                  layer_elem.tags)
    
    with self._layer_exporter.layer_tree.filter.add_rule_temp(_not_treated_specially_and_has_tags):
      if self._layer_exporter.export_settings['export_only_selected_layers'].value:
        with self._layer_exporter.layer_tree.filter['layer_types'].add_rule_temp(
          exportlayers.LayerFilterRules.is_nonempty_group):
          return self._layer_exporter.layer_tree.filter.is_match(layer_elem)
      else:
        return self._layer_exporter.layer_tree.filter.is_match(layer_elem)
  
  def _get_in_memory_preview(self, layer):
    self._preview_width, self._preview_height = self._get_preview_size(layer.width, layer.height)
    self._preview_scaling_factor = self._preview_width / layer.width
    
    image_preview = self._get_image_preview()
    if image_preview is None:
      return None
    
    if image_preview.base_type != gimpenums.RGB:
      pdb.gimp_image_convert_rgb(image_preview)
    
    layer_preview = image_preview.layers[0]
    
    if layer_preview.mask is not None:
      layer_preview.remove_mask(gimpenums.MASK_APPLY)
    
    # The layer may have been resized during the export, hence recompute the size.
    self._preview_width, self._preview_height = self._get_preview_size(
      layer_preview.width, layer_preview.height)
    
    self._preview_width, self._preview_height, preview_data = self._get_preview_data(
      layer_preview, self._preview_width, self._preview_height)
    
    layer_preview_pixbuf = self._get_preview_pixbuf(
      layer_preview, self._preview_width, self._preview_height, preview_data)
    
    self._cleanup(image_preview)
    
    return layer_preview_pixbuf
  
  @contextlib.contextmanager
  def _redirect_messages(self, message_handler=gimpenums.ERROR_CONSOLE):
    orig_message_handler = pdb.gimp_message_get_handler()
    pdb.gimp_message_set_handler(message_handler)
    
    try:
      yield
    finally:
      pdb.gimp_message_set_handler(orig_message_handler)
  
  def _get_image_preview(self):
    if self._initial_layer_tree is not None:
      layer_tree = self._initial_layer_tree
      self._initial_layer_tree = None
    else:
      layer_tree = self._layer_exporter.layer_tree
    
    layer_tree_filter = layer_tree.filter if layer_tree is not None else None
    
    with self._layer_exporter.modify_export_settings(
      {'export_only_selected_layers': True,
       'selected_layers': {self._layer_exporter.image.ID: set([self.layer_elem.item.ID])}}):
      try:
        image_preview = self._layer_exporter.export_layers(
          operations=['layer_contents'], layer_tree=layer_tree, keep_exported_layers=True,
          on_after_create_image_copy_func=self._layer_exporter_on_after_create_image_copy,
          on_after_insert_layer_func=self._layer_exporter_on_after_insert_layer)
      except Exception:
        image_preview = None
    
    if layer_tree_filter is not None:
      self._layer_exporter.layer_tree.filter = layer_tree_filter
    
    return image_preview
  
  def _layer_exporter_on_after_create_image_copy(self, image_copy):
    pdb.gimp_image_resize(
      image_copy,
      int(round(image_copy.width * self._preview_scaling_factor)),
      int(round(image_copy.height * self._preview_scaling_factor)),
      0, 0)
    
    pdb.gimp_context_set_interpolation(gimpenums.INTERPOLATION_NONE)
  
  def _layer_exporter_on_after_insert_layer(self, layer):
    if not pdb.gimp_item_is_group(layer):
      pdb.gimp_layer_scale(
        layer,
        int(round(layer.width * self._preview_scaling_factor)),
        int(round(layer.height * self._preview_scaling_factor)),
        False)
  
  def _get_preview_pixbuf(self, layer, preview_width, preview_height, preview_data):
    # The following code is largely based on the implementation of `gimp_pixbuf_from_data`
    # from: https://github.com/GNOME/gimp/blob/gimp-2-8/libgimp/gimppixbuf.c
    layer_preview_pixbuf = gtk.gdk.pixbuf_new_from_data(
      preview_data, gtk.gdk.COLORSPACE_RGB, layer.has_alpha, 8, preview_width,
      preview_height, preview_width * layer.bpp)
    
    self._preview_pixbuf = layer_preview_pixbuf
    
    if layer.has_alpha:
      layer_preview_pixbuf = self._add_alpha_background_to_pixbuf(
        layer_preview_pixbuf, layer.opacity, self.draw_checkboard_alpha_background,
        self._PREVIEW_ALPHA_CHECK_SIZE,
        self._PREVIEW_ALPHA_CHECK_COLOR_FIRST, self._PREVIEW_ALPHA_CHECK_COLOR_SECOND)
    
    return layer_preview_pixbuf
  
  def _add_alpha_background_to_pixbuf(self, pixbuf, opacity, use_checkboard_background=False, check_size=None,
                                      check_color_first=None, check_color_second=None):
    if use_checkboard_background:
      pixbuf_with_alpha_background = gtk.gdk.Pixbuf(
        gtk.gdk.COLORSPACE_RGB, False, 8,
        pixbuf.get_width(), pixbuf.get_height())
      
      pixbuf.composite_color(
        pixbuf_with_alpha_background, 0, 0,
        pixbuf.get_width(), pixbuf.get_height(),
        0, 0, 1.0, 1.0, gtk.gdk.INTERP_NEAREST,
        int(round((opacity / 100.0) * 255)),
        0, 0, check_size, check_color_first, check_color_second)
    else:
      pixbuf_with_alpha_background = gtk.gdk.Pixbuf(
        gtk.gdk.COLORSPACE_RGB, True, 8,
        pixbuf.get_width(), pixbuf.get_height())
      pixbuf_with_alpha_background.fill(0xffffff00)
      
      pixbuf.composite(
        pixbuf_with_alpha_background, 0, 0,
        pixbuf.get_width(), pixbuf.get_height(),
        0, 0, 1.0, 1.0, gtk.gdk.INTERP_NEAREST,
        int(round((opacity / 100.0) * 255)))
    
    return pixbuf_with_alpha_background
  
  def _get_preview_data(self, layer, preview_width, preview_height):
    actual_preview_width, actual_preview_height, _unused, _unused, preview_data = (
      pdb.gimp_drawable_thumbnail(layer, preview_width, preview_height))
    
    return actual_preview_width, actual_preview_height, array.array(b"B", preview_data).tostring()
  
  def _get_preview_size(self, width, height):
    preview_widget_allocation = self._preview_image.get_allocation()
    preview_widget_width = preview_widget_allocation.width
    preview_widget_height = preview_widget_allocation.height
    
    if preview_widget_width > preview_widget_height:
      preview_height = min(preview_widget_height, height, self._MAX_PREVIEW_SIZE_PIXELS)
      preview_width = int(round((preview_height / height) * width))
      
      if preview_width > preview_widget_width:
        preview_width = preview_widget_width
        preview_height = int(round((preview_width / width) * height))
    else:
      preview_width = min(preview_widget_width, width, self._MAX_PREVIEW_SIZE_PIXELS)
      preview_height = int(round((preview_width / width) * height))
      
      if preview_height > preview_widget_height:
        preview_height = preview_widget_height
        preview_width = int(round((preview_height / height) * width))
    
    if preview_width == 0:
      preview_width = 1
    if preview_height == 0:
      preview_height = 1
    
    return preview_width, preview_height
  
  def _resize_preview(self, preview_allocation, preview_pixbuf):
    if preview_pixbuf is None:
      return
    
    if (preview_allocation.width >= preview_pixbuf.get_width() and
        preview_allocation.height >= preview_pixbuf.get_height()):
      return
      
    scaled_preview_width, scaled_preview_height = self._get_preview_size(
      preview_pixbuf.get_width(), preview_pixbuf.get_height())
    
    if (self._previous_preview_pixbuf_width == scaled_preview_width and
        self._previous_preview_pixbuf_height == scaled_preview_height):
      return
    
    scaled_preview_pixbuf = preview_pixbuf.scale_simple(
      scaled_preview_width, scaled_preview_height, gtk.gdk.INTERP_NEAREST)
    
    scaled_preview_pixbuf = self._add_alpha_background_to_pixbuf(
      scaled_preview_pixbuf, 100, self.draw_checkboard_alpha_background,
      self._PREVIEW_ALPHA_CHECK_SIZE,
      self._PREVIEW_ALPHA_CHECK_COLOR_FIRST, self._PREVIEW_ALPHA_CHECK_COLOR_SECOND)
    
    self._preview_image.set_from_pixbuf(scaled_preview_pixbuf)
    
    self._previous_preview_pixbuf_width = scaled_preview_width
    self._previous_preview_pixbuf_height = scaled_preview_height
  
  def _cleanup(self, image_preview):
    pdb.gimp_image_delete(image_preview)
  
  def _on_preview_image_size_allocate(self, image_widget, allocation):
    self._is_allocated_size = True
    
    if not self._is_updating and self._preview_image.get_mapped():
      self._resize_preview(allocation, self._preview_pixbuf)
  
  def _on_vbox_size_allocate(self, image_widget, allocation):
    if not self._is_updating and not self._preview_image.get_mapped():
      preview_widget_allocated_width = allocation.width - self._IMAGE_PREVIEW_PADDING * 2
      preview_widget_allocated_height = (
        allocation.height - self._label_layer_name.get_allocation().height -
        self._BOTTOM_WIDGETS_PADDING * 2 - self._IMAGE_PREVIEW_PADDING * 2)
      
      if (preview_widget_allocated_width < self._placeholder_image_size[0] or
          preview_widget_allocated_height < self._placeholder_image_size[1]):
        self._placeholder_image.hide()
      else:
        self._placeholder_image.show()
  
  def _show_placeholder_image(self):
    self._placeholder_image.show()
    self._set_layer_name_label(_("No selection"))
  
  def _set_layer_name_label(self, layer_name):
    self._label_layer_name.set_markup("<i>{0}</i>".format(gobject.markup_escape_text(layer_name)))
  

#===============================================================================


class _ExportLayersGenericGui(object):
  
  _PROGRESS_BARS_SPACING = 3
  _PROGRESS_BAR_INDIVIDUAL_OPERATIONS_HEIGHT = 10
  
  def __init__(self):
    self._layer_exporter = None
    
    self._progress_bar = gtk.ProgressBar()
    self._progress_bar.set_ellipsize(pango.ELLIPSIZE_MIDDLE)
    
    self._progress_bar_individual_operations = gtk.ProgressBar()
    self._progress_bar_individual_operations.set_size_request(-1, self._PROGRESS_BAR_INDIVIDUAL_OPERATIONS_HEIGHT)
    
    self._vbox_progress_bars = gtk.VBox()
    self._vbox_progress_bars.set_spacing(self._PROGRESS_BARS_SPACING)
    self._vbox_progress_bars.pack_start(self._progress_bar, expand=False, fill=False)
    self._vbox_progress_bars.pack_start(self._progress_bar_individual_operations, expand=False, fill=False)
  
  def _stop(self, *args):
    if self._layer_exporter is not None:
      self._layer_exporter.should_stop = True
      return True
    else:
      return False
  
  def _install_gimp_progress(self, progress_set_value, progress_reset_value):
    self._progress_callback = gimp.progress_install(
      progress_reset_value, progress_reset_value, lambda *args: None, progress_set_value)
  
  def _uninstall_gimp_progress(self):
    gimp.progress_uninstall(self._progress_callback)
    del self._progress_callback


#===============================================================================


def add_gui_settings(settings):
  
  gui_settings = pgsettinggroup.SettingGroup('gui', [
    {
      'type': pgsetting.SettingTypes.generic,
      'name': 'dialog_position',
      'default_value': ()
    },
    {
      'type': pgsetting.SettingTypes.boolean,
      'name': 'show_more_settings',
      'default_value': False
    },
    {
      'type': pgsetting.SettingTypes.integer,
      'name': 'chooser_and_previews_hpane_position',
      'default_value': 620
    },
    {
      'type': pgsetting.SettingTypes.float,
      'name': 'previews_vpane_position',
      'default_value': 300
    },
    {
      'type': pgsetting.SettingTypes.boolean,
      'name': 'export_name_preview_enabled',
      'default_value': True,
      'gui_type': None
    },
    {
      'type': pgsetting.SettingTypes.boolean,
      'name': 'export_image_preview_enabled',
      'default_value': True,
      'gui_type': None
    },
  ], setting_sources=[pygimplib.config.SOURCE_SESSION, pygimplib.config.SOURCE_PERSISTENT])
  
  session_only_gui_settings = pgsettinggroup.SettingGroup('gui_session', [
    {
      'type': pgsetting.SettingTypes.image_IDs_and_directories,
      'name': 'image_ids_and_directories',
      'default_value': {}
    },
    {
      'type': pgsetting.SettingTypes.generic,
      'name': 'export_name_preview_layers_collapsed_state',
      # key: image ID; value: set of layer IDs collapsed in the name preview
      'default_value': collections.defaultdict(set)
    },
    {
      'type': pgsetting.SettingTypes.generic,
      'name': 'export_image_preview_displayed_layers',
      # key: image ID; value: ID of the layer displayed in the preview
      'default_value': collections.defaultdict(_return_none_func)
    },
  ], setting_sources=[pygimplib.config.SOURCE_SESSION])
  
  persistent_only_gui_settings = pgsettinggroup.SettingGroup('gui_persistent', [
    {
      'type': pgsetting.SettingTypes.generic,
      'name': 'export_name_preview_layers_collapsed_state_persistent',
      # key: image filename; value: set of layer names collapsed in the name preview
      'default_value': collections.defaultdict(set)
    },
    {
      'type': pgsetting.SettingTypes.generic,
      'name': 'export_image_preview_displayed_layers_persistent',
      # key: image filename; value: name of the layer displayed in the preview
      'default_value': collections.defaultdict(_return_none_func)
    },
  ], setting_sources=[pygimplib.config.SOURCE_PERSISTENT])
  
  settings.add([gui_settings, session_only_gui_settings, persistent_only_gui_settings])
  
  settings.set_ignore_tags({
    'gui_session/image_ids_and_directories': ['reset'],
  })
  

#===============================================================================


def _set_settings(func):
  """
  This is a decorator for `SettingGroup.apply_gui_values_to_settings()` that
  prevents the decorated function from being executed if there are invalid
  setting values. For the invalid values, an error message is displayed.
  
  This decorator is meant to be used in the `_ExportLayersGui` class.
  """
  
  @functools.wraps(func)
  def func_wrapper(self, *args, **kwargs):
    try:
      self._settings['main'].apply_gui_values_to_settings()
      self._settings['gui'].apply_gui_values_to_settings()
      
      self._current_directory_setting.gui.update_setting_value()
      self._settings['main/output_directory'].set_value(self._current_directory_setting.value)
      
      self._settings['gui_session/export_name_preview_layers_collapsed_state'].value[self._image.ID] = (
        self._export_name_preview.collapsed_items)
      self._settings['main/selected_layers'].value[self._image.ID] = self._export_name_preview.selected_items
      self._settings['gui_session/export_image_preview_displayed_layers'].value[self._image.ID] = (
        self._export_image_preview.layer_elem.item.ID
        if self._export_image_preview.layer_elem is not None else None)
    except pgsetting.SettingValueError as e:
      self._display_message_label(e.message, message_type=gtk.MESSAGE_ERROR, setting=e.setting)
      return
    
    func(self, *args, **kwargs)
  
  return func_wrapper


#===============================================================================


def _update_directory(setting, current_image, directory_for_current_image):
  """
  Set the directory to the setting according to the priority list below:
  
  1. `directory_for_current_image` if not None
  2. `current_image` - import path of the current image if not None
  
  If update was performed, return True, otherwise return False.
  """
  
  if directory_for_current_image is not None:
    if isinstance(directory_for_current_image, bytes):
      directory_for_current_image = directory_for_current_image.decode(constants.GTK_CHARACTER_ENCODING)
    
    setting.set_value(directory_for_current_image)
    return True
  
  if current_image.filename is not None:
    setting.set_value(os.path.dirname(current_image.filename.decode(constants.GTK_CHARACTER_ENCODING)))
    return True
  
  return False


def _setup_image_ids_and_directories_and_initial_directory(settings, current_directory_setting, current_image):
  """
  Set up the initial directory for the current image according to the
  following priority list:
  
    1. Last export directory of the current image
    2. Import directory of the current image
    3. Last export directory of any image (i.e. the current value of 'main/output_directory')
    4. The default directory (default value) for 'main/output_directory'
  
  Notes:
  
    Directory 3. is set upon loading 'main/output_directory' from a persistent source.
    Directory 4. is set upon the instantiation of 'main/output_directory'.
  """
  
  settings['gui_session/image_ids_and_directories'].update_image_ids_and_directories()
  
  update_performed = _update_directory(
    current_directory_setting, current_image,
    settings['gui_session/image_ids_and_directories'].value[current_image.ID])
  
  if not update_performed:
    current_directory_setting.set_value(settings['main/output_directory'].value)


def _setup_output_directory_changed(settings, current_image):
  def on_output_directory_changed(output_directory, image_ids_and_directories, current_image_id):
    image_ids_and_directories.update_directory(current_image_id, output_directory.value)
  
  settings['main/output_directory'].connect_event('value-changed',
    on_output_directory_changed, settings['gui_session/image_ids_and_directories'], current_image.ID)


#===============================================================================


class _ExportLayersGui(_ExportLayersGenericGui):
  
  _HBOX_EXPORT_LABELS_NAME_SPACING = 15
  _HBOX_EXPORT_NAME_ENTRIES_SPACING = 3
  _HBOX_HORIZONTAL_SPACING = 8
  
  _MORE_SETTINGS_HORIZONTAL_SPACING = 12
  _MORE_SETTINGS_VERTICAL_SPACING = 6
  
  _DIALOG_SIZE = (900, 610)
  _DIALOG_BORDER_WIDTH = 8
  _DIALOG_VBOX_SPACING = 5
  _DIALOG_BOTTOM_SEPARATOR_PADDING = 5
  _DIALOG_BUTTONS_HORIZONTAL_SPACING = 6
  
  _FILE_EXTENSION_ENTRY_WIDTH_CHARS = 8
  _FILENAME_PATTERN_ENTRY_MIN_WIDTH_CHARS = 15
  _FILENAME_PATTERN_ENTRY_MAX_WIDTH_CHARS = 50
  
  _DELAY_PREVIEWS_UPDATE_MILLISECONDS = 50
  _DELAY_NAME_PREVIEW_UPDATE_TEXT_ENTRIES_MILLISECONDS = 100
  _DELAY_CLEAR_LABEL_MESSAGE_MILLISECONDS = 10000
  
  def __init__(self, initial_layer_tree, settings):
    super(_ExportLayersGui, self).__init__()
    
    self._initial_layer_tree = initial_layer_tree
    self._image = self._initial_layer_tree.image
    self._settings = settings
    
    self._is_exporting = False
    
    self._suppress_gimp_progress()
    
    self._layer_exporter_for_previews = exportlayers.LayerExporter(
      gimpenums.RUN_NONINTERACTIVE, self._image, self._settings['main'],
      overwrite_chooser=overwrite.NoninteractiveOverwriteChooser(
        self._settings['main/overwrite_mode'].items['replace']),
      layer_tree=self._initial_layer_tree)
    
    self._init_settings()
    
    self._hpaned_previous_position = self._settings['gui/chooser_and_previews_hpane_position'].value
    self._vpaned_previous_position = self._settings['gui/previews_vpane_position'].value
    
    self._init_gui()
    
    pggui.set_gui_excepthook_parent(self._dialog)
    
    gtk.main()
  
  def _init_settings(self):
    add_gui_settings(self._settings)
    
    settings_plugin.setup_image_ids_and_filenames_settings(
      self._settings['gui_session/export_name_preview_layers_collapsed_state'],
      self._settings['gui_persistent/export_name_preview_layers_collapsed_state_persistent'],
      settings_plugin.convert_set_of_layer_ids_to_names, [self._layer_exporter_for_previews.layer_tree],
      settings_plugin.convert_set_of_layer_names_to_ids, [self._layer_exporter_for_previews.layer_tree])
    
    settings_plugin.setup_image_ids_and_filenames_settings(
      self._settings['gui_session/export_image_preview_displayed_layers'],
      self._settings['gui_persistent/export_image_preview_displayed_layers_persistent'],
      settings_plugin.convert_layer_id_to_name, [self._layer_exporter_for_previews.layer_tree],
      settings_plugin.convert_layer_name_to_id, [self._layer_exporter_for_previews.layer_tree])
    
    status, status_message = self._settings.load()
    if status == pgsettingpersistor.SettingPersistor.READ_FAIL:
      display_message(status_message, gtk.MESSAGE_WARNING)
    
    # Needs to be string to avoid strict directory validation
    self._current_directory_setting = pgsetting.StringSetting(
      'current_directory', self._settings['main/output_directory'].default_value)
    self._message_setting = None
    
    _setup_image_ids_and_directories_and_initial_directory(
      self._settings, self._current_directory_setting, self._image)
    _setup_output_directory_changed(self._settings, self._image)
  
  def _init_gui(self):
    self._dialog = gimpui.Dialog(title=pygimplib.config.PLUGIN_TITLE, role=pygimplib.config.PLUGIN_NAME)
    self._dialog.set_transient()
    self._dialog.set_default_size(*self._DIALOG_SIZE)
    self._dialog.set_border_width(self._DIALOG_BORDER_WIDTH)
    
    self._folder_chooser_label = gtk.Label()
    self._folder_chooser_label.set_markup("<b>" + _("Save in folder:") + "</b>")
    self._folder_chooser_label.set_alignment(0.0, 0.5)
    
    self._folder_chooser = gtk.FileChooserWidget(action=gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER)
    
    self._export_name_preview = ExportNamePreview(
      self._layer_exporter_for_previews,
      self._initial_layer_tree,
      self._settings['gui_session/export_name_preview_layers_collapsed_state'].value[self._image.ID],
      self._settings['main/selected_layers'].value[self._image.ID],
      on_selection_changed_func=self._on_name_preview_selection_changed,
      on_after_update_func=self._on_name_preview_after_update,
      on_after_edit_tags_func=self._on_name_preview_after_edit_tags)
    
    self._export_image_preview = ExportImagePreview(
      self._layer_exporter_for_previews,
      self._initial_layer_tree,
      self._settings['gui_session/export_image_preview_displayed_layers'].value[self._image.ID])
    
    self._vbox_folder_chooser = gtk.VBox(homogeneous=False)
    self._vbox_folder_chooser.set_spacing(self._DIALOG_VBOX_SPACING * 2)
    self._vbox_folder_chooser.pack_start(self._folder_chooser_label, expand=False, fill=False)
    self._vbox_folder_chooser.pack_start(self._folder_chooser)
    
    self._vpaned_previews = gtk.VPaned()
    self._vpaned_previews.pack1(self._export_name_preview.widget, resize=True, shrink=True)
    self._vpaned_previews.pack2(self._export_image_preview.widget, resize=True, shrink=True)
    
    self._frame_previews = gtk.Frame()
    self._frame_previews.set_shadow_type(gtk.SHADOW_ETCHED_OUT)
    self._frame_previews.add(self._vpaned_previews)
    
    self._hpaned_chooser_and_previews = gtk.HPaned()
    self._hpaned_chooser_and_previews.pack1(self._vbox_folder_chooser, resize=True, shrink=False)
    self._hpaned_chooser_and_previews.pack2(self._frame_previews, resize=True, shrink=True)
    
    self._file_extension_label = gtk.Label()
    self._file_extension_label.set_markup("<b>" + self._settings['main/file_extension'].display_name + ":</b>")
    self._file_extension_label.set_alignment(0.0, 0.5)
    
    self._file_extension_entry = pggui.FileExtensionEntry()
    self._file_extension_entry.set_width_chars(self._FILE_EXTENSION_ENTRY_WIDTH_CHARS)
    
    self._save_as_label = gtk.Label()
    self._save_as_label.set_markup("<b>" + _("Save as") + ":</b>")
    self._save_as_label.set_alignment(0.0, 0.5)
    
    self._dot_label = gtk.Label(".")
    self._dot_label.set_alignment(0.0, 1.0)
    
    self._filename_pattern_entry = pggui.FilenamePatternEntry(
      exportlayers.LayerExporter.SUGGESTED_LAYER_FILENAME_PATTERNS,
      minimum_width_chars=self._FILENAME_PATTERN_ENTRY_MIN_WIDTH_CHARS,
      maximum_width_chars=self._FILENAME_PATTERN_ENTRY_MAX_WIDTH_CHARS,
      default_item=self._settings['main/layer_filename_pattern'].default_value)
    
    self._label_message = gtk.Label()
    self._label_message.set_alignment(0.0, 0.5)
    self._label_message.set_ellipsize(pango.ELLIPSIZE_MIDDLE)
    
    self._file_extension_mode_label = gtk.Label(
      self._settings['main/file_extension_mode'].display_name + ":")
    self._file_extension_mode_label.set_alignment(0, 0.5)
    
    self._tagged_layers_mode_label = gtk.Label(
      self._settings['main/tagged_layers_mode'].display_name + ":")
    self._tagged_layers_mode_label.set_alignment(0, 0.5)
    
    self._show_more_settings_button = gtk.CheckButton()
    self._show_more_settings_button.set_use_underline(True)
    self._show_more_settings_button.set_label(_("Show _More Settings"))
    
    self._settings.initialize_gui({
      'file_extension': [pgsetting.SettingGuiTypes.extended_text_entry, self._file_extension_entry],
      'dialog_position': [pgsetting.SettingGuiTypes.window_position, self._dialog],
      'show_more_settings': [pgsetting.SettingGuiTypes.checkbox, self._show_more_settings_button],
      'chooser_and_previews_hpane_position': [
        pgsetting.SettingGuiTypes.paned_position, self._hpaned_chooser_and_previews],
      'previews_vpane_position': [
        pgsetting.SettingGuiTypes.paned_position, self._vpaned_previews],
      'layer_filename_pattern': [pgsetting.SettingGuiTypes.extended_text_entry, self._filename_pattern_entry]
    })
    
    self._current_directory_setting.set_gui(pgsetting.SettingGuiTypes.folder_chooser, self._folder_chooser)
    
    self._hbox_export_name_labels = gtk.HBox(homogeneous=False)
    self._hbox_export_name_labels.pack_start(self._file_extension_label, expand=False, fill=True)
    self._hbox_export_name_labels.pack_start(self._save_as_label, expand=False, fill=True)
    
    self._hbox_export_name_entries = gtk.HBox(homogeneous=False)
    self._hbox_export_name_entries.set_spacing(self._HBOX_EXPORT_NAME_ENTRIES_SPACING)
    self._hbox_export_name_entries.pack_start(self._filename_pattern_entry, expand=False, fill=True)
    self._hbox_export_name_entries.pack_start(self._dot_label, expand=False, fill=True)
    self._hbox_export_name_entries.pack_start(self._file_extension_entry, expand=False, fill=True)
    
    self._hbox_export_name = gtk.HBox(homogeneous=False)
    self._hbox_export_name.set_spacing(self._HBOX_EXPORT_LABELS_NAME_SPACING)
    self._hbox_export_name.pack_start(self._hbox_export_name_labels, expand=False, fill=True)
    self._hbox_export_name.pack_start(self._hbox_export_name_entries, expand=False, fill=True)
    
    self._hbox_export_name_and_message = gtk.HBox(homogeneous=False)
    self._hbox_export_name_and_message.set_spacing(self._HBOX_HORIZONTAL_SPACING)
    self._hbox_export_name_and_message.pack_start(self._hbox_export_name, expand=False, fill=True)
    self._hbox_export_name_and_message.pack_start(self._label_message, expand=True, fill=True)
    
    self._hbox_export_settings = gtk.HBox(homogeneous=False)
    self._hbox_export_settings.pack_start(self._settings['main/layer_groups_as_folders'].gui.element)
    self._hbox_export_settings.pack_start(self._settings['main/ignore_invisible'].gui.element)
    self._hbox_export_settings.pack_start(self._settings['main/autocrop'].gui.element)
    self._hbox_export_settings.pack_start(self._settings['main/use_image_size'].gui.element)
    
    self._table_labels = gtk.Table(rows=2, columns=1, homogeneous=False)
    self._table_labels.set_row_spacings(self._MORE_SETTINGS_VERTICAL_SPACING)
    self._table_labels.attach(self._file_extension_mode_label, 0, 1, 0, 1)
    self._table_labels.attach(self._tagged_layers_mode_label, 0, 1, 1, 2)
    
    self._table_combo_boxes = gtk.Table(rows=2, columns=1, homogeneous=False)
    self._table_combo_boxes.set_row_spacings(self._MORE_SETTINGS_VERTICAL_SPACING)
    self._table_combo_boxes.attach(
      self._settings['main/file_extension_mode'].gui.element, 0, 1, 0, 1, yoptions=0)
    self._table_combo_boxes.attach(
      self._settings['main/tagged_layers_mode'].gui.element, 0, 1, 1, 2, yoptions=0)
    
    tagged_layers_description = _(
      "To use a layer as a background for other layers, right-click in the preview on the layer "
      "and select \"{0}\"."
      "\nFor foreground layers, select \"{1}\"."
      "\nTo enable handling of tagged layers, select \"{2}\".").format(
        exportlayers.LayerExporter.SUPPORTED_TAGS['background'],
        exportlayers.LayerExporter.SUPPORTED_TAGS['foreground'],
        self._settings['main/tagged_layers_mode'].items_display_names['special'])
    
    self._tagged_layers_mode_label.set_tooltip_text(tagged_layers_description)
    self._settings['main/tagged_layers_mode'].gui.element.set_tooltip_text(tagged_layers_description)
    
    self._table_additional_elems = gtk.Table(rows=2, columns=1, homogeneous=False)
    self._table_additional_elems.set_row_spacings(self._MORE_SETTINGS_VERTICAL_SPACING)
    self._table_additional_elems.attach(self._settings['main/strip_mode'].gui.element, 0, 1, 0, 1, yoptions=0)
    self._table_additional_elems.attach(self._settings['main/crop_mode'].gui.element, 0, 1, 1, 2)
    
    self._hbox_tables = gtk.HBox(homogeneous=False)
    self._hbox_tables.set_spacing(self._MORE_SETTINGS_HORIZONTAL_SPACING)
    self._hbox_tables.pack_start(self._table_labels, expand=False, fill=True)
    self._hbox_tables.pack_start(self._table_combo_boxes, expand=False, fill=True)
    self._hbox_tables.pack_start(self._table_additional_elems, expand=False, fill=True)
    
    self._hbox_more_settings_checkbuttons = gtk.HBox(homogeneous=False)
    self._hbox_more_settings_checkbuttons.set_spacing(self._MORE_SETTINGS_HORIZONTAL_SPACING)
    self._hbox_more_settings_checkbuttons.pack_start(
      self._settings['main/merge_layer_groups'].gui.element, expand=False, fill=True)
    self._hbox_more_settings_checkbuttons.pack_start(
      self._settings['main/empty_folders'].gui.element, expand=False, fill=True)
    self._hbox_more_settings_checkbuttons.pack_start(
      self._settings['main/ignore_layer_modes'].gui.element, expand=False, fill=True)
    self._hbox_more_settings_checkbuttons.pack_start(
      self._settings['main/export_only_selected_layers'].gui.element, expand=False, fill=True)
    self._hbox_more_settings_checkbuttons.pack_start(
      self._settings['main/inherit_transparency_from_groups'].gui.element, expand=False, fill=True)
    
    self._vbox_more_settings = gtk.VBox(homogeneous=False)
    self._vbox_more_settings.set_spacing(self._MORE_SETTINGS_VERTICAL_SPACING)
    self._vbox_more_settings.pack_start(self._hbox_tables, expand=False, fill=False)
    self._vbox_more_settings.pack_start(self._hbox_more_settings_checkbuttons, expand=False, fill=False)
    
    self._export_button = gtk.Button()
    self._export_button.set_label(_("_Export"))
    
    self._cancel_button = gtk.Button()
    self._cancel_button.set_label(_("_Cancel"))
    
    self._stop_button = gtk.Button()
    self._stop_button.set_label(_("_Stop"))
    
    self._save_settings_button = gtk.Button()
    self._save_settings_button.set_label(_("Save Settings"))
    self._save_settings_button.set_tooltip_text(
      _("Save settings permanently. "
        "If you start GIMP again, the saved settings will be loaded "
        "when {0} is first opened.").format(pygimplib.config.PLUGIN_TITLE))
    self._reset_settings_button = gtk.Button()
    self._reset_settings_button.set_label(_("Reset Settings"))
    
    self._dialog_buttons = gtk.HButtonBox()
    self._dialog_buttons.set_layout(gtk.BUTTONBOX_END)
    self._dialog_buttons.set_spacing(self._DIALOG_BUTTONS_HORIZONTAL_SPACING)
    
    if not gtk.alternative_dialog_button_order():
      main_dialog_buttons = [self._cancel_button, self._export_button]
    else:
      main_dialog_buttons = [self._export_button, self._cancel_button]
    
    for button in main_dialog_buttons:
      self._dialog_buttons.pack_end(button, expand=False, fill=True)
    
    self._dialog_buttons.pack_end(self._stop_button, expand=False, fill=True)
    self._dialog_buttons.pack_start(self._save_settings_button, expand=False, fill=True)
    self._dialog_buttons.pack_start(self._reset_settings_button, expand=False, fill=True)
    self._dialog_buttons.set_child_secondary(self._save_settings_button, True)
    self._dialog_buttons.set_child_secondary(self._reset_settings_button, True)
    
    self._action_area = gtk.HBox(homogeneous=False)
    self._action_area.set_spacing(self._HBOX_HORIZONTAL_SPACING)
    self._action_area.pack_start(self._show_more_settings_button, expand=False, fill=True)
    self._action_area.pack_start(self._dialog_buttons, expand=True, fill=True)
    
    self._dialog.vbox.set_spacing(self._DIALOG_VBOX_SPACING)
    self._dialog.vbox.pack_start(self._hpaned_chooser_and_previews)
    self._dialog.vbox.pack_start(self._hbox_export_name_and_message, expand=False, fill=False)
    self._dialog.vbox.pack_start(self._hbox_export_settings, expand=False, fill=False)
    self._dialog.vbox.pack_start(self._vbox_more_settings, expand=False, fill=False)
    self._dialog.vbox.pack_start(
      gtk.HSeparator(), expand=False, fill=True, padding=self._DIALOG_BOTTOM_SEPARATOR_PADDING)
    self._dialog.vbox.pack_start(self._action_area, expand=False, fill=True)
    self._dialog.vbox.pack_end(self._vbox_progress_bars, expand=False, fill=True)
    
    self._export_button.connect("clicked", self._on_export_click)
    self._cancel_button.connect("clicked", self._cancel)
    self._stop_button.connect("clicked", self._stop)
    self._dialog.connect("key-press-event", self._on_dialog_key_press)
    self._dialog.connect("delete-event", self._close)
    
    self._save_settings_button.connect("clicked", self._on_save_settings_clicked)
    self._reset_settings_button.connect("clicked", self._on_reset_settings_clicked)
    
    self._file_extension_entry.connect(
      "changed", self._on_text_entry_changed,
      self._settings['main/file_extension'], "invalid_file_extension")
    self._filename_pattern_entry.connect(
      "changed", self._on_text_entry_changed,
      self._settings['main/layer_filename_pattern'], "invalid_layer_filename_pattern")
    self._show_more_settings_button.connect("toggled", self._on_show_more_settings_button_toggled)
    
    self._dialog.connect("notify::is-active", self._on_dialog_is_active_changed)
    self._hpaned_chooser_and_previews.connect("event", self._on_hpaned_left_button_up)
    self._hpaned_chooser_and_previews.connect("move-handle", self._on_hpaned_move_handle)
    self._vpaned_previews.connect("event", self._on_vpaned_left_button_up)
    self._vpaned_previews.connect("move-handle", self._on_vpaned_move_handle)
    
    self._connect_setting_changes_to_previews()
    
    self._dialog.set_default_response(gtk.RESPONSE_CANCEL)
    
    self._dialog.vbox.show_all()
    
    self._vbox_progress_bars.hide()
    self._stop_button.hide()
    # Action area is unused and leaves unnecessary empty space.
    self._dialog.action_area.hide()
    
    self._connect_visible_changed_for_previews()
    
    self._show_hide_more_settings()
    
    self._init_previews()
    
    self._dialog.set_focus(self._file_extension_entry)
    self._export_button.set_flags(gtk.CAN_DEFAULT)
    self._export_button.grab_default()
    self._filename_pattern_entry.set_activates_default(True)
    self._file_extension_entry.set_activates_default(True)
    # Place the cursor at the end of the text entry.
    self._file_extension_entry.set_position(-1)
    
    self._dialog.show()
  
  def _init_previews(self):
    self._export_name_preview.update()
    self._export_image_preview.update()
  
  def _reset_settings(self):
    self._settings.reset()
    pgsettingpersistor.SettingPersistor.clear(
      [pygimplib.config.SOURCE_SESSION, pygimplib.config.SOURCE_PERSISTENT])
  
  def _save_settings(self):
    status, status_message = self._settings.save()
    if status == pgsettingpersistor.SettingPersistor.WRITE_FAIL:
      display_message(status_message, gtk.MESSAGE_WARNING, parent=self._dialog)
  
  def _on_text_entry_changed(self, widget, setting, name_preview_lock_update_key=None):
    try:
      setting.gui.update_setting_value()
    except pgsetting.SettingValueError as e:
      pggui.timeout_add_strict(
        self._DELAY_NAME_PREVIEW_UPDATE_TEXT_ENTRIES_MILLISECONDS, self._export_name_preview.clear)
      self._display_message_label(e.message, message_type=gtk.MESSAGE_ERROR, setting=setting)
      self._export_name_preview.lock_update(True, name_preview_lock_update_key)
    else:
      self._export_name_preview.lock_update(False, name_preview_lock_update_key)
      if self._message_setting == setting:
        self._display_message_label(None)
      
      pggui.timeout_add_strict(
        self._DELAY_NAME_PREVIEW_UPDATE_TEXT_ENTRIES_MILLISECONDS, self._export_name_preview.update)
  
  def _on_show_more_settings_button_toggled(self, widget):
    self._show_hide_more_settings()
  
  def _show_hide_more_settings(self):
    if self._show_more_settings_button.get_active():
      self._vbox_more_settings.show()
      self._frame_previews.show()
      self._export_name_preview.widget.show()
      self._export_image_preview.widget.show()
      
      self._file_extension_label.hide()
      self._save_as_label.show()
      self._dot_label.show()
      self._filename_pattern_entry.show()
    else:
      self._vbox_more_settings.hide()
      self._frame_previews.hide()
      self._export_name_preview.widget.hide()
      self._export_image_preview.widget.hide()
      
      self._file_extension_label.show()
      self._save_as_label.hide()
      self._dot_label.hide()
      self._filename_pattern_entry.hide()
  
  def _on_dialog_is_active_changed(self, widget, property_spec):
    if self._initial_layer_tree is not None:
      self._initial_layer_tree = None
      return
    
    if self._dialog.is_active() and not self._is_exporting:
      self._export_name_preview.update(reset_completely=True)
      self._export_image_preview.update()
  
  def _connect_setting_changes_to_previews(self):
    def _on_setting_changed(setting):
      pggui.timeout_add_strict(self._DELAY_PREVIEWS_UPDATE_MILLISECONDS, self._export_name_preview.update)
      pggui.timeout_add_strict(self._DELAY_PREVIEWS_UPDATE_MILLISECONDS, self._export_image_preview.update)
    
    for setting in self._settings['main']:
      if setting.name not in [
          'file_extension', 'output_directory', 'overwrite_mode', 'layer_filename_pattern',
          'export_only_selected_layers', 'selected_layers', 'selected_layers_persistent']:
        setting.connect_event('value-changed', _on_setting_changed)
    
    self._settings['gui_session/export_name_preview_layers_collapsed_state'].connect_event(
      'after-reset',
      lambda setting: self._export_name_preview.set_collapsed_items(setting.value[self._image.ID]))
    self._settings['main/selected_layers'].connect_event(
      'after-reset',
      lambda setting: self._export_name_preview.set_selected_items(setting.value[self._image.ID]))
    
    def _reset_image_in_preview(setting):
      self._export_image_preview.clear()
    
    self._settings['gui_session/export_image_preview_displayed_layers'].connect_event(
      'after-reset', _reset_image_in_preview)
  
  def _connect_visible_changed_for_previews(self):
    def _connect_visible_changed(preview, setting):
      preview.widget.connect("notify::visible", self._on_preview_visible_changed, preview)
      if not setting.value:
        preview.lock_update(True, "previews_enabled")
    
    _connect_visible_changed(self._export_name_preview, self._settings['gui/export_name_preview_enabled'])
    _connect_visible_changed(self._export_image_preview, self._settings['gui/export_image_preview_enabled'])
  
  def _on_preview_visible_changed(self, widget, property_spec, preview):
    preview_visible = preview.widget.get_visible()
    preview.lock_update(not preview_visible, "preview_visible")
    if preview_visible:
      preview.update()
  
  def _on_hpaned_left_button_up(self, widget, event):
    if event.type == gtk.gdk.BUTTON_RELEASE and event.button == 1:
      self._on_hpaned_move(resize=True)
  
  def _on_vpaned_left_button_up(self, widget, event):
    if event.type == gtk.gdk.BUTTON_RELEASE and event.button == 1:
      self._on_vpaned_move(resize=True)
  
  def _on_hpaned_move_handle(self, widget, scroll_type):
    self._on_hpaned_move()
  
  def _on_vpaned_move_handle(self, widget, scroll_type):
    self._on_vpaned_move()
  
  def _on_hpaned_move(self, resize=False):
    current_position = self._hpaned_chooser_and_previews.get_position()
    max_position = self._hpaned_chooser_and_previews.get_property("max-position")
    
    if current_position == max_position and self._hpaned_previous_position != max_position:
      self._disable_preview_on_paned_drag(
        self._export_name_preview, self._settings['gui/export_name_preview_enabled'], "previews_enabled")
      self._disable_preview_on_paned_drag(
        self._export_image_preview, self._settings['gui/export_image_preview_enabled'], "previews_enabled")
    elif current_position != max_position and self._hpaned_previous_position == max_position:
      self._enable_preview_on_paned_drag(
        self._export_name_preview, self._settings['gui/export_name_preview_enabled'], "previews_enabled")
      self._enable_preview_on_paned_drag(
        self._export_image_preview, self._settings['gui/export_image_preview_enabled'], "previews_enabled")
    elif resize and current_position != self._hpaned_previous_position:
      self._export_image_preview.resize(update_when_larger_than_image_size=True)
    
    self._hpaned_previous_position = current_position
  
  def _on_vpaned_move(self, resize=True):
    current_position = self._vpaned_previews.get_position()
    max_position = self._vpaned_previews.get_property("max-position")
    min_position = self._vpaned_previews.get_property("min-position")
    
    if current_position == max_position and self._vpaned_previous_position != max_position:
      self._disable_preview_on_paned_drag(
        self._export_image_preview, self._settings['gui/export_image_preview_enabled'],
        "vpaned_preview_enabled", clear=False)
    elif current_position != max_position and self._vpaned_previous_position == max_position:
      self._enable_preview_on_paned_drag(
        self._export_image_preview, self._settings['gui/export_image_preview_enabled'],
        "vpaned_preview_enabled")
    elif current_position == min_position and self._vpaned_previous_position != min_position:
      self._disable_preview_on_paned_drag(
        self._export_name_preview, self._settings['gui/export_name_preview_enabled'],
        "vpaned_preview_enabled")
    elif current_position != min_position and self._vpaned_previous_position == min_position:
      self._enable_preview_on_paned_drag(
        self._export_name_preview, self._settings['gui/export_name_preview_enabled'],
        "vpaned_preview_enabled")
    elif resize and current_position != self._vpaned_previous_position:
      self._export_image_preview.resize(update_when_larger_than_image_size=True)
    
    self._vpaned_previous_position = current_position
  
  def _enable_preview_on_paned_drag(self, preview, preview_enabled_setting, update_lock_key):
    preview.lock_update(False, update_lock_key)
    preview.update()
    preview_enabled_setting.set_value(True)
  
  def _disable_preview_on_paned_drag(self, preview, preview_enabled_setting, update_lock_key, clear=True):
    if clear:
      preview.clear()
    preview.lock_update(True, update_lock_key)
    preview_enabled_setting.set_value(False)
  
  def _on_name_preview_selection_changed(self):
    layer_elem_from_cursor = self._export_name_preview.get_layer_elem_from_cursor()
    if layer_elem_from_cursor is not None:
      if (self._export_image_preview.layer_elem is None or
          layer_elem_from_cursor.item.ID != self._export_image_preview.layer_elem.item.ID):
        self._export_image_preview.layer_elem = layer_elem_from_cursor
        self._export_image_preview.update()
    else:
      layer_elems_from_selected_rows = self._export_name_preview.get_layer_elems_from_selected_rows()
      if layer_elems_from_selected_rows:
        self._export_image_preview.layer_elem = layer_elems_from_selected_rows[0]
        self._export_image_preview.update()
      else:
        self._export_image_preview.clear()
  
  def _on_name_preview_after_update(self):
    self._export_image_preview.update_layer_elem()
  
  def _on_name_preview_after_edit_tags(self):
    self._on_name_preview_selection_changed()
  
  def _on_dialog_key_press(self, widget, event):
    if gtk.gdk.keyval_name(event.keyval) == "Escape":
      export_stopped = self._stop()
      return export_stopped
  
  @_set_settings
  def _on_save_settings_clicked(self, widget):
    self._save_settings()
    self._display_message_label(_("Settings successfully saved."), message_type=gtk.MESSAGE_INFO)
  
  def _on_reset_settings_clicked(self, widget):
    response_id = display_message(
      _("Do you really want to reset settings?"), gtk.MESSAGE_WARNING, parent=self._dialog,
      buttons=gtk.BUTTONS_YES_NO)
    
    if response_id == gtk.RESPONSE_YES:
      self._reset_settings()
      self._save_settings()
      self._display_message_label(_("Settings reset."), message_type=gtk.MESSAGE_INFO)
  
  def _suppress_gimp_progress(self):
    gimp.progress_install(lambda *args: None, lambda *args: None, lambda *args: None, lambda *args: None)
  
  def _progress_set_value(self, fraction):
    self._progress_bar_individual_operations.set_fraction(fraction)
    
    # Without this workaround, the main dialog would not appear until the export of the second layer.
    if not self._dialog.get_mapped():
      self._dialog.show()
    
    while gtk.events_pending():
      gtk.main_iteration()
  
  def _progress_reset_value(self, *args):
    self._progress_set_value(0.0)
  
  @_set_settings
  def _on_export_click(self, widget):
    self._setup_gui_before_export()
    
    self._install_gimp_progress(self._progress_set_value, self._progress_reset_value)
    
    overwrite_chooser = pggui.GtkDialogOverwriteChooser(
      # Don't insert the Cancel item as a button.
      zip(
        self._settings['main/overwrite_mode'].items.values()[:-1],
        self._settings['main/overwrite_mode'].items_display_names.values()[:-1]),
      default_value=self._settings['main/overwrite_mode'].items['replace'],
      default_response=self._settings['main/overwrite_mode'].items['cancel'],
      title=pygimplib.config.PLUGIN_TITLE,
      parent=self._dialog)
    progress_updater = pggui.GtkProgressUpdater(self._progress_bar)
    
    self._layer_exporter = exportlayers.LayerExporter(
      gimpenums.RUN_INTERACTIVE, self._image, self._settings['main'], overwrite_chooser, progress_updater,
      export_context_manager=_handle_gui_in_export, export_context_manager_args=[self._dialog])
    
    should_quit = True
    self._is_exporting = True
    
    try:
      self._layer_exporter.export_layers()
    except exportlayers.ExportLayersCancelError as e:
      should_quit = False
    except exportlayers.ExportLayersError as e:
      display_message(
        _format_export_error_message(e), message_type=gtk.MESSAGE_WARNING, parent=self._dialog,
        message_in_text_view=True)
      should_quit = False
    except Exception as e:
      display_exception_message(traceback.format_exc(), parent=self._dialog)
    else:
      self._settings['special/first_plugin_run'].set_value(False)
      self._settings['special/first_plugin_run'].save()
      
      if not self._layer_exporter.exported_layers:
        display_message(_("No layers were exported."), gtk.MESSAGE_INFO, parent=self._dialog)
        should_quit = False
    finally:
      self._uninstall_gimp_progress()
      self._layer_exporter = None
      self._is_exporting = False
    
    self._settings['main/overwrite_mode'].set_value(overwrite_chooser.overwrite_mode)
    pgsettingpersistor.SettingPersistor.save(
      [self._settings['main'], self._settings['gui'], self._settings['gui_session']],
      [pygimplib.config.SOURCE_SESSION])
    
    if should_quit:
      gtk.main_quit()
    else:
      self._restore_gui_after_export()
      progress_updater.reset()
  
  def _setup_gui_before_export(self):
    self._display_message_label(None)
    self._set_gui_enabled(False)
  
  def _restore_gui_after_export(self):
    self._set_gui_enabled(True)
  
  def _set_gui_enabled(self, enabled):
    self._vbox_progress_bars.set_visible(not enabled)
    self._stop_button.set_visible(not enabled)
    self._cancel_button.set_visible(enabled)
    
    for child in self._dialog.vbox:
      if child not in (self._action_area, self._progress_bar, self._progress_bar_individual_operations):
        child.set_sensitive(enabled)
    
    self._show_more_settings_button.set_sensitive(enabled)
    
    for button in self._dialog_buttons:
      if button != self._stop_button:
        button.set_sensitive(enabled)
    
    if enabled:
      self._dialog.set_focus(self._file_extension_entry)
      self._file_extension_entry.set_position(-1)
    else:
      self._dialog.set_focus(self._stop_button)
  
  def _close(self, widget, event):
    gtk.main_quit()
  
  def _cancel(self, widget):
    gtk.main_quit()
  
  def _display_message_label(self, text, message_type=gtk.MESSAGE_ERROR, setting=None):
    self._message_setting = setting
    
    if not text:
      self._label_message.set_text("")
    else:
      text = text[0].upper() + text[1:]
      if not text.endswith("."):
        text += "."
      
      if message_type == gtk.MESSAGE_ERROR:
        color = "red"
      else:
        color = "blue"
      
      self._label_message.set_markup("<span foreground=\"{0}\"><b>{1}</b></span>".format(
        gobject.markup_escape_text(color), gobject.markup_escape_text(text)))
      
      if color == "blue":
        pggui.timeout_add_strict(
          self._DELAY_CLEAR_LABEL_MESSAGE_MILLISECONDS, self._display_message_label, None)


#===============================================================================


class _ExportLayersRepeatGui(_ExportLayersGenericGui):
  
  _HBOX_HORIZONTAL_SPACING = 8
  _DIALOG_WIDTH = 500
  
  def __init__(self, layer_tree, settings):
    super(_ExportLayersRepeatGui, self).__init__()

    self._init_gui()
    
    self._layer_tree = layer_tree
    self._image = self._layer_tree.image
    self._settings = settings
    
    pgsettingpersistor.SettingPersistor.load([self._settings['main']], [pygimplib.config.SOURCE_SESSION])
    
    pggui.set_gui_excepthook_parent(self._dialog)
    
    gtk.main_iteration()
    self.show()
    self.export_layers()
  
  def _init_gui(self):
    self._dialog = gimpui.Dialog(title=pygimplib.config.PLUGIN_TITLE, role=None)
    self._dialog.set_transient()
    self._dialog.set_border_width(8)
    self._dialog.set_default_size(self._DIALOG_WIDTH, -1)
    
    self._stop_button = gtk.Button()
    self._stop_button.set_label(_("_Stop"))
    
    self._buttonbox = gtk.HButtonBox()
    self._buttonbox.pack_start(self._stop_button, expand=False, fill=True)
    
    self._hbox_action_area = gtk.HBox(homogeneous=False)
    self._hbox_action_area.set_spacing(self._HBOX_HORIZONTAL_SPACING)
    self._hbox_action_area.pack_start(self._vbox_progress_bars, expand=True, fill=True)
    self._hbox_action_area.pack_end(self._buttonbox, expand=False, fill=True)
    
    self._dialog.vbox.pack_end(self._hbox_action_area, expand=False, fill=False)
    
    self._stop_button.connect("clicked", self._stop)
    self._dialog.connect("delete-event", self._stop)
  
  def _progress_set_value(self, fraction):
    self._progress_bar_individual_operations.set_fraction(fraction)
    while gtk.events_pending():
      gtk.main_iteration()
  
  def _progress_reset_value(self, *args):
    self._progress_set_value(0.0)
  
  def export_layers(self):
    self._install_gimp_progress(self._progress_set_value, self._progress_reset_value)
    
    self._layer_exporter = exportlayers.LayerExporter(
      gimpenums.RUN_WITH_LAST_VALS, self._image, self._settings['main'],
      overwrite.NoninteractiveOverwriteChooser(self._settings['main/overwrite_mode'].value),
      pggui.GtkProgressUpdater(self._progress_bar),
      export_context_manager=_handle_gui_in_export, export_context_manager_args=[self._dialog])
    try:
      self._layer_exporter.export_layers(layer_tree=self._layer_tree)
    except exportlayers.ExportLayersCancelError:
      pass
    except exportlayers.ExportLayersError as e:
      display_message(
        _format_export_error_message(e), message_type=gtk.MESSAGE_WARNING, parent=self._dialog,
        message_in_text_view=True)
    else:
      if not self._layer_exporter.exported_layers:
        display_message(_("No layers were exported."), gtk.MESSAGE_INFO, parent=self._dialog)
    finally:
      self._uninstall_gimp_progress()
  
  def show(self):
    self._dialog.vbox.show_all()
    self._dialog.action_area.hide()
    self._dialog.show()
  
  def hide(self):
    self._dialog.hide()


#===============================================================================


def export_layers_gui(image, settings):
  _ExportLayersGui(image, settings)


def export_layers_repeat_gui(image, settings):
  _ExportLayersRepeatGui(image, settings)
