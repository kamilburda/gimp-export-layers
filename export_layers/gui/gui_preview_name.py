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
This module defines a preview widget displaying the names of layers to be
exported.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import collections
import os

import pygtk
pygtk.require("2.0")
import gtk
import gobject

from gimp import pdb

from export_layers import pygimplib
from export_layers.pygimplib import pgconstants
from export_layers.pygimplib import pggui
from export_layers.pygimplib import pgutils

from .. import builtin_constraints
from . import gui_preview_base

#===============================================================================


class ExportNamePreview(gui_preview_base.ExportPreview):
  
  _VBOX_PADDING = 5
  _ADD_TAG_POPUP_HBOX_SPACING = 5
  _ADD_TAG_POPUP_BORDER_WIDTH = 5
  
  _COLUMNS = (
    _COLUMN_ICON_LAYER, _COLUMN_ICON_TAG_VISIBLE, _COLUMN_LAYER_NAME_SENSITIVE,
    _COLUMN_LAYER_NAME, _COLUMN_LAYER_ID) = (
    [0, gtk.gdk.Pixbuf], [1, gobject.TYPE_BOOLEAN], [2, gobject.TYPE_BOOLEAN],
    [3, gobject.TYPE_STRING], [4, gobject.TYPE_INT])
  
  def __init__(
        self, layer_exporter, initial_layer_tree=None, collapsed_items=None,
        selected_items=None, displayed_tags_setting=None):
    super().__init__()
    
    self._layer_exporter = layer_exporter
    self._initial_layer_tree = initial_layer_tree
    self._collapsed_items = collapsed_items if collapsed_items is not None else set()
    self._selected_items = selected_items if selected_items is not None else []
    self._displayed_tags_setting = displayed_tags_setting
    
    self.on_selection_changed = pgutils.empty_func
    self.on_after_update = pgutils.empty_func
    self.on_after_edit_tags = pgutils.empty_func
    
    self._tree_iters = collections.defaultdict(pgutils.return_none_func)
    
    self._row_expand_collapse_interactive = True
    self._toggle_tag_interactive = True
    self._clearing_preview = False
    self._row_select_interactive = True
    self._initial_scroll_to_selection = True
    
    self._icon_image_filepath = os.path.join(
      pygimplib.config.PLUGIN_SUBDIRPATH, "images", "icon_image.png")
    self._icon_tag_filepath = os.path.join(
      pygimplib.config.PLUGIN_SUBDIRPATH, "images", "icon_tag.png")
    
    self._init_gui()
    
    self._widget = self._vbox
  
  def update(self, reset_items=False, update_existing_contents_only=False):
    """
    Update the preview (add/remove layer, move layer to a different parent layer
    group, etc.).
    
    If `reset_items` is True, perform full update - add new layers, remove
    non-existent layers, etc. Note that setting this to True may introduce a
    performance penalty for hundreds of items.
    
    If `update_existing_contents_only` is True, only update the contents of the
    existing items. Note that the items will not be reparented,
    expanded/collapsed or added/removed even if they need to be. This option is
    useful if you know the item structure will be preserved.
    """
    
    update_locked = super().update()
    if update_locked:
      return
    
    if not update_existing_contents_only:
      self.clear()
    
    self._process_items(reset_items=reset_items)
    
    self._enable_filtered_items(enabled=True)
    
    if not update_existing_contents_only:
      self._insert_items()
      self._set_expanded_items()
    else:
      self._update_items()
    
    self._set_selection()
    self._set_items_sensitive()
    
    self._enable_filtered_items(enabled=False)
    
    self._update_displayed_tags()
    
    self._tree_view.columns_autosize()
    
    self.on_after_update()
  
  def clear(self):
    """
    Clear the entire preview.
    """
    
    self._clearing_preview = True
    self._tree_model.clear()
    self._tree_iters.clear()
    self._clearing_preview = False
  
  def set_sensitive(self, sensitive):
    self._widget.set_sensitive(sensitive)
  
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
    tree_path, unused_ = self._tree_view.get_cursor()
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
    self._tree_view.set_enable_search(False)
    self._tree_view.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
    
    self._init_icons()
    
    self._init_tags_menu()
    
    column = gtk.TreeViewColumn(b"")
    
    cell_renderer_icon_layer = gtk.CellRendererPixbuf()
    column.pack_start(cell_renderer_icon_layer, expand=False)
    column.set_attributes(cell_renderer_icon_layer, pixbuf=self._COLUMN_ICON_LAYER[0])
    
    cell_renderer_icon_tag = gtk.CellRendererPixbuf()
    cell_renderer_icon_tag.set_property("pixbuf", self._icons["tag"])
    column.pack_start(cell_renderer_icon_tag, expand=False)
    column.set_attributes(
      cell_renderer_icon_tag, visible=self._COLUMN_ICON_TAG_VISIBLE[0])
    
    cell_renderer_layer_name = gtk.CellRendererText()
    column.pack_start(cell_renderer_layer_name, expand=False)
    column.set_attributes(
      cell_renderer_layer_name, text=self._COLUMN_LAYER_NAME[0],
      sensitive=self._COLUMN_LAYER_NAME_SENSITIVE[0])
    
    self._tree_view.append_column(column)
    
    self._preview_label = gtk.Label(_("Preview"))
    self._preview_label.set_alignment(0.02, 0.5)
    
    self._scrolled_window = gtk.ScrolledWindow()
    self._scrolled_window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    self._scrolled_window.add(self._tree_view)
    
    self._vbox = gtk.VBox(homogeneous=False)
    self._vbox.pack_start(
      self._preview_label, expand=False, fill=False, padding=self._VBOX_PADDING)
    self._vbox.pack_start(self._scrolled_window)
    
    self._tree_view.connect("row-collapsed", self._on_tree_view_row_collapsed)
    self._tree_view.connect("row-expanded", self._on_tree_view_row_expanded)
    self._tree_view.get_selection().connect("changed", self._on_tree_selection_changed)
    self._tree_view.connect("event", self._on_tree_view_right_button_press)
  
  def _init_icons(self):
    self._icons = {}
    self._icons["layer_group"] = self._tree_view.render_icon(
      gtk.STOCK_DIRECTORY, gtk.ICON_SIZE_MENU)
    self._icons["layer"] = gtk.gdk.pixbuf_new_from_file_at_size(
      self._icon_image_filepath, -1, self._icons["layer_group"].props.height)
    self._icons["tag"] = gtk.gdk.pixbuf_new_from_file_at_size(
      self._icon_tag_filepath, -1, self._icons["layer_group"].props.height)
    
    self._icons["exported_layer_group"] = self._icons["layer"].copy()
    
    scaling_factor = 0.8
    width_unscaled = self._icons["layer_group"].props.width
    width = int(width_unscaled * scaling_factor)
    height_unscaled = self._icons["layer_group"].props.height
    height = int(height_unscaled * scaling_factor)
    x_offset_unscaled = (
      self._icons["exported_layer_group"].props.width
      - self._icons["layer_group"].props.width)
    x_offset = x_offset_unscaled + width_unscaled - width
    y_offset_unscaled = (
      self._icons["exported_layer_group"].props.height
      - self._icons["layer_group"].props.height)
    y_offset = y_offset_unscaled + height_unscaled - height
    
    self._icons["layer_group"].composite(self._icons["exported_layer_group"],
      x_offset, y_offset, width, height, x_offset, y_offset,
      scaling_factor, scaling_factor, gtk.gdk.INTERP_BILINEAR, 255)
  
  def _init_tags_menu(self):
    self._tags_menu_items = {}
    self._tags_remove_submenu_items = {}
    
    self._tags_menu_relative_position = None
    
    self._tags_menu = gtk.Menu()
    self._tags_remove_submenu = gtk.Menu()
    
    self._tags_menu.append(gtk.SeparatorMenuItem())
    
    self._menu_item_add_tag = gtk.MenuItem(_("Add tag..."))
    self._menu_item_add_tag.connect("activate", self._on_tags_menu_item_add_tag_activate)
    self._tags_menu.append(self._menu_item_add_tag)
    
    self._menu_item_remove_tag = gtk.MenuItem(_("Remove tag"))
    self._menu_item_remove_tag.set_submenu(self._tags_remove_submenu)
    self._tags_menu.append(self._menu_item_remove_tag)
    
    for tag, tag_display_name in self._displayed_tags_setting.default_value.items():
      self._add_tag_menu_item(tag, tag_display_name)
    
    self._tags_menu.show_all()
  
  def _update_displayed_tags(self):
    self._layer_exporter.layer_tree.is_filtered = False
    
    used_tags = set()
    for layer_elem in self._layer_exporter.layer_tree:
      for tag in layer_elem.tags:
        used_tags.add(tag)
        if tag not in self._tags_menu_items:
          self._add_tag_menu_item(tag, tag)
          self._add_remove_tag_menu_item(tag, tag)
    
    self._layer_exporter.layer_tree.is_filtered = True
    
    for tag, menu_item in self._tags_remove_submenu_items.items():
      menu_item.set_sensitive(tag not in used_tags)
    
    for tag in self._displayed_tags_setting.value:
      if tag not in self._tags_menu_items:
        self._add_tag_menu_item(tag, tag)
        self._add_remove_tag_menu_item(tag, tag)
    
    self._menu_item_remove_tag.set_sensitive(
      bool(self._tags_remove_submenu.get_children()))
    
    self._sort_tags_menu_items()
    
    for tag in self._tags_menu_items:
      if tag not in self._displayed_tags_setting.value:
        self._displayed_tags_setting.value[tag] = tag
    
    self._displayed_tags_setting.save()
  
  def _sort_tags_menu_items(self):
    for new_tag_position, tag in (
          enumerate(sorted(self._tags_menu_items, key=lambda tag: tag.lower()))):
      self._tags_menu.reorder_child(self._tags_menu_items[tag], new_tag_position)
      if tag in self._tags_remove_submenu_items:
        self._tags_remove_submenu.reorder_child(
          self._tags_remove_submenu_items[tag], new_tag_position)
  
  def _add_tag_menu_item(self, tag, tag_display_name):
    self._tags_menu_items[tag] = gtk.CheckMenuItem(tag_display_name)
    self._tags_menu_items[tag].connect("toggled", self._on_tags_menu_item_toggled, tag)
    self._tags_menu_items[tag].show()
    self._tags_menu.prepend(self._tags_menu_items[tag])
  
  def _add_remove_tag_menu_item(self, tag, tag_display_name):
    self._tags_remove_submenu_items[tag] = gtk.MenuItem(tag_display_name)
    self._tags_remove_submenu_items[tag].connect(
      "activate", self._on_tags_remove_submenu_item_activate, tag)
    self._tags_remove_submenu_items[tag].show()
    self._tags_remove_submenu.prepend(self._tags_remove_submenu_items[tag])
  
  def _on_tree_view_right_button_press(self, widget, event):
    if event.type == gtk.gdk.BUTTON_PRESS and event.button == 3:
      layer_ids = []
      stop_event_propagation = False
      
      # Get the current selection. We can't use `TreeSelection.get_selection()`
      # because this event is fired before the selection is updated.
      selection_at_pos = self._tree_view.get_path_at_pos(int(event.x), int(event.y))
      
      if (selection_at_pos is not None
          and self._tree_view.get_selection().count_selected_rows() > 1):
        layer_ids = self._get_layer_ids_in_current_selection()
        stop_event_propagation = True
      else:
        if selection_at_pos is not None:
          tree_iter = self._tree_model.get_iter(selection_at_pos[0])
          layer_ids = [self._get_layer_id(tree_iter)]
      
      self._toggle_tag_interactive = False
      
      layer_elems = [self._layer_exporter.layer_tree[layer_id] for layer_id in layer_ids]
      for tag, tags_menu_item in self._tags_menu_items.items():
        tags_menu_item.set_active(
          all(tag in layer_elem.tags for layer_elem in layer_elems))
      
      self._toggle_tag_interactive = True
      
      if len(layer_ids) >= 1:
        self._tags_menu.popup(None, None, None, event.button, event.time)
        
        toplevel_window = pggui.get_toplevel_window(self._widget)
        if toplevel_window is not None:
          self._tags_menu_relative_position = toplevel_window.get_window().get_pointer()
      
      return stop_event_propagation
  
  def _on_tags_menu_item_toggled(self, tags_menu_item, tag):
    if self._toggle_tag_interactive:
      pdb.gimp_image_undo_group_start(self._layer_exporter.image)
      
      for layer_id in self._get_layer_ids_in_current_selection():
        layer_elem = self._layer_exporter.layer_tree[layer_id]
        
        if tags_menu_item.get_active():
          layer_elem.add_tag(tag)
        else:
          layer_elem.remove_tag(tag)
      
      pdb.gimp_image_undo_group_end(self._layer_exporter.image)
      
      # Modifying just one layer could result in renaming other layers differently,
      # hence update the whole preview.
      self.update(update_existing_contents_only=True)
      
      self.on_after_edit_tags()
  
  def _on_tags_menu_item_add_tag_activate(self, menu_item_add_tag):
    def _on_popup_focus_out_event(popup, event):
      popup.destroy()
    
    def _on_popup_key_press_event(popup, event):
      key_name = gtk.gdk.keyval_name(event.keyval)
      if key_name in ["Return", "KP_Enter"]:
        entry_text = entry_add_tag.get_text()
        if entry_text and entry_text not in self._tags_menu_items:
          self._add_tag_menu_item(entry_text, entry_text)
          self._add_remove_tag_menu_item(entry_text, entry_text)
        
        popup.destroy()
        return True
      elif key_name == "Escape":
        popup.destroy()
        return True
    
    def _set_popup_position(popup, window):
      if self._tags_menu_relative_position is not None:
        window_absolute_position = window.get_window().get_origin()
        popup.move(
          window_absolute_position[0] + self._tags_menu_relative_position[0],
          window_absolute_position[1] + self._tags_menu_relative_position[1])
        
        self._tags_menu_relative_position = None
    
    popup_add_tag = gtk.Window(gtk.WINDOW_TOPLEVEL)
    popup_add_tag.set_decorated(False)
    popup_add_tag.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_POPUP_MENU)
    
    toplevel_widget = self._widget.get_toplevel()
    if toplevel_widget.flags() & gtk.TOPLEVEL:
      popup_add_tag.set_transient_for(toplevel_widget)
    
    _set_popup_position(popup_add_tag, toplevel_widget)
    
    label_tag_name = gtk.Label(_("Tag name:"))
    
    entry_add_tag = gtk.Entry()
    
    hbox = gtk.HBox()
    hbox.set_spacing(self._ADD_TAG_POPUP_HBOX_SPACING)
    hbox.pack_start(label_tag_name, expand=False, fill=False)
    hbox.pack_start(entry_add_tag, expand=False, fill=False)
    hbox.set_border_width(self._ADD_TAG_POPUP_BORDER_WIDTH)
    
    frame = gtk.Frame()
    frame.add(hbox)
    
    popup_add_tag.add(frame)
    
    popup_add_tag.connect("focus-out-event", _on_popup_focus_out_event)
    popup_add_tag.connect("key-press-event", _on_popup_key_press_event)
    
    popup_add_tag.show_all()
  
  def _on_tags_remove_submenu_item_activate(self, tags_remove_submenu_item, tag):
    self._tags_remove_submenu.remove(tags_remove_submenu_item)
    self._tags_menu.remove(self._tags_menu_items[tag])
    
    del self._tags_menu_items[tag]
    del self._tags_remove_submenu_items[tag]
    del self._displayed_tags_setting.value[tag]
    
    self._menu_item_remove_tag.set_sensitive(
      bool(self._tags_remove_submenu.get_children()))
    
    self._displayed_tags_setting.save()
  
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
      previous_selected_items = self._selected_items
      self._selected_items = self._get_layer_ids_in_current_selection()
      
      if self._layer_exporter.export_settings["constraints/only_selected_layers"].value:
        if self._selected_items != previous_selected_items:
          self.update(update_existing_contents_only=True)
      
      self.on_selection_changed()
  
  def _get_layer_ids_in_current_selection(self):
    unused_, tree_paths = self._tree_view.get_selection().get_selected_rows()
    return [
      self._get_layer_id(self._tree_model.get_iter(tree_path))
      for tree_path in tree_paths]
  
  def _get_layer_id(self, tree_iter):
    return self._tree_model.get_value(tree_iter, column=self._COLUMN_LAYER_ID[0])
  
  def _process_items(self, reset_items=False):
    if not reset_items:
      if self._initial_layer_tree is not None:
        layer_tree = self._initial_layer_tree
        self._initial_layer_tree = None
      else:
        if self._layer_exporter.layer_tree is not None:
          self._layer_exporter.layer_tree.reset_all_names()
        layer_tree = self._layer_exporter.layer_tree
    else:
      layer_tree = None
    
    with self._layer_exporter.modify_export_settings(
           {"selected_layers": {self._layer_exporter.image.ID: self._selected_items}},
           self._settings_events_to_temporarily_disable):
      self._layer_exporter.export(processing_groups=["layer_name"], layer_tree=layer_tree)
  
  def _update_items(self):
    for layer_elem in self._layer_exporter.layer_tree:
      self._update_parent_item_elems(layer_elem)
      self._update_item_elem(layer_elem)
  
  def _insert_items(self):
    for layer_elem in self._layer_exporter.layer_tree:
      self._insert_parent_item_elems(layer_elem)
      self._insert_item_elem(layer_elem)
  
  def _insert_item_elem(self, item_elem):
    if item_elem.parent:
      parent_tree_iter = self._tree_iters[item_elem.parent.item.ID]
    else:
      parent_tree_iter = None
    
    tree_iter = self._tree_model.append(
      parent_tree_iter,
      [self._get_icon_from_item_elem(item_elem),
       bool(item_elem.tags),
       True,
       item_elem.name.encode(pgconstants.GTK_CHARACTER_ENCODING),
       item_elem.item.ID])
    self._tree_iters[item_elem.item.ID] = tree_iter
    
    return tree_iter
  
  def _update_item_elem(self, item_elem):
    self._tree_model.set(
      self._tree_iters[item_elem.item.ID],
      self._COLUMN_ICON_TAG_VISIBLE[0],
      bool(item_elem.tags),
      self._COLUMN_LAYER_NAME_SENSITIVE[0],
      True,
      self._COLUMN_LAYER_NAME[0],
      item_elem.name.encode(pgconstants.GTK_CHARACTER_ENCODING))
  
  def _insert_parent_item_elems(self, item_elem):
    for parent_elem in item_elem.parents:
      if not self._tree_iters[parent_elem.item.ID]:
        self._insert_item_elem(parent_elem)
  
  def _update_parent_item_elems(self, item_elem):
    for parent_elem in item_elem.parents:
      self._update_item_elem(parent_elem)
  
  def _enable_filtered_items(self, enabled):
    if self._layer_exporter.export_settings["constraints/only_selected_layers"].value:
      if not enabled:
        self._layer_exporter.layer_tree.filter.add_rule(
          builtin_constraints.is_layer_in_selected_layers, self._selected_items)
      else:
        self._layer_exporter.layer_tree.filter.remove_rule(
          builtin_constraints.is_layer_in_selected_layers, raise_if_not_found=False)
  
  def _set_items_sensitive(self):
    if self._layer_exporter.export_settings["constraints/only_selected_layers"].value:
      self._set_item_elems_sensitive(self._layer_exporter.layer_tree, False)
      self._set_item_elems_sensitive(
        [self._layer_exporter.layer_tree[item_id] for item_id in self._selected_items],
        True)
  
  def _get_item_elem_sensitive(self, item_elem):
    return self._tree_model.get_value(
      self._tree_iters[item_elem.item.ID], self._COLUMN_LAYER_NAME_SENSITIVE[0])
  
  def _set_item_elem_sensitive(self, item_elem, sensitive):
    if self._tree_iters[item_elem.item.ID] is not None:
      self._tree_model.set_value(
        self._tree_iters[item_elem.item.ID],
        self._COLUMN_LAYER_NAME_SENSITIVE[0],
        sensitive)
  
  def _set_parent_item_elems_sensitive(self, item_elem):
    for parent_elem in reversed(list(item_elem.parents)):
      parent_sensitive = any(
        self._get_item_elem_sensitive(child_elem) for child_elem in parent_elem.children
        if child_elem.item.ID in self._tree_iters)
      self._set_item_elem_sensitive(parent_elem, parent_sensitive)
  
  def _set_item_elems_sensitive(self, item_elems, sensitive):
    for item_elem in item_elems:
      self._set_item_elem_sensitive(item_elem, sensitive)
      self._set_parent_item_elems_sensitive(item_elem)
  
  def _get_icon_from_item_elem(self, item_elem):
    if item_elem.item_type == item_elem.ITEM:
      return self._icons["layer"]
    elif item_elem.item_type == item_elem.NONEMPTY_GROUP:
      if not self._layer_exporter.has_exported_layer(item_elem.item):
        return self._icons["layer_group"]
      else:
        return self._icons["exported_layer_group"]
    elif item_elem.item_type == item_elem.EMPTY_GROUP:
      return self._icons["layer_group"]
    else:
      return None
  
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
    
    self._selected_items = [
      item for item in self._selected_items if item in self._tree_iters]
    
    for item in self._selected_items:
      tree_iter = self._tree_iters[item]
      if tree_iter is not None:
        self._tree_view.get_selection().select_iter(tree_iter)
    
    if self._initial_scroll_to_selection:
      self._set_initial_scroll_to_selection()
      self._initial_scroll_to_selection = False
    
    self._row_select_interactive = True
  
  def _set_cursor(self, previous_cursor=None):
    self._row_select_interactive = False
    
    if (previous_cursor is not None
        and self._tree_model.get_iter(previous_cursor) is not None):
      self._tree_view.set_cursor(previous_cursor)
    
    self._row_select_interactive = True
  
  def _set_initial_scroll_to_selection(self):
    if self._selected_items:
      tree_iter = self._tree_iters[self._selected_items[0]]
      if tree_iter is not None:
        first_selected_item_path = (
          self._tree_model.get_path(self._tree_iters[self._selected_items[0]]))
        if first_selected_item_path is not None:
          self._tree_view.scroll_to_cell(first_selected_item_path, None, True, 0.5, 0.0)
