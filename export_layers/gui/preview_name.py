# -*- coding: utf-8 -*-

"""Preview widget displaying the names of items to be batch-processed."""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import collections
import os
import traceback

import pygtk
pygtk.require('2.0')
import gtk
import gobject

from gimp import pdb

from export_layers import pygimplib as pg

from export_layers import exceptions
from export_layers import utils as utils_
from export_layers.gui import preview_base as preview_base_

from export_layers.gui import messages as messages_


class NamePreview(preview_base_.Preview):
  """A widget displaying a preview of batch-processed items - names and their
  folder structure.
  
  Additional features:
  * toggling "filter mode" - unselected items are not sensitive.
  * assigning tags to items.
  
  Attributes:
  
  * `is_filtering` - If enabled, unselected items are not sensitive.
  
  Signals:
  
  * `'preview-selection-changed'` - The selection in the preview was modified
    by the user or by calling `set_selected_items()`.
  * `'preview-updated'` - The preview was updated by calling `update()`. This
    signal is not emitted if the update is locked.
    
    Arguments:
    
    * `error` - If `None`, the preview was updated successfully. Otherwise,
      this is an `Exception` object describing the error that occurred during
      the update.
  * `'preview-tags-changed'` - An existing tag was added to or removed from an
    item.
  """
  
  __gsignals__ = {
    b'preview-selection-changed': (gobject.SIGNAL_RUN_FIRST, None, ()),
    b'preview-updated': (gobject.SIGNAL_RUN_FIRST, None, (gobject.TYPE_PYOBJECT,)),
    b'preview-tags-changed': (gobject.SIGNAL_RUN_FIRST, None, ()),
  }
  
  _ADD_TAG_POPUP_HBOX_SPACING = 5
  _ADD_TAG_POPUP_BORDER_WIDTH = 5
  
  _COLUMNS = (
    _COLUMN_ICON_ITEM,
    _COLUMN_ICON_TAG_VISIBLE,
    _COLUMN_ITEM_NAME_SENSITIVE,
    _COLUMN_ITEM_NAME,
    _COLUMN_ITEM_ID,
    _COLUMN_ITEM_TYPE) = (
    [0, gtk.gdk.Pixbuf],
    [1, gobject.TYPE_BOOLEAN],
    [2, gobject.TYPE_BOOLEAN],
    [3, gobject.TYPE_STRING],
    [4, gobject.TYPE_INT],
    [5, gobject.TYPE_INT])
  
  def __init__(
        self,
        batcher,
        settings,
        initial_item_tree=None,
        collapsed_items=None,
        selected_items=None,
        selected_items_filter_name='selected_in_preview',
        available_tags_setting=None):
    super().__init__()
    
    self._batcher = batcher
    self._settings = settings
    self._initial_item_tree = initial_item_tree
    self._collapsed_items = collapsed_items if collapsed_items is not None else set()
    self._selected_items = selected_items if selected_items is not None else []
    self._selected_items_filter_name = selected_items_filter_name
    self._available_tags_setting = available_tags_setting
    
    self.is_filtering = False
    
    # key: `Item.raw.ID` or (`Item.raw.ID`, 'folder') instance
    # value: `gtk.TreeIter` instance
    self._tree_iters = collections.defaultdict(pg.utils.return_none_func)
    
    self._row_expand_collapse_interactive = True
    self._toggle_tag_interactive = True
    self._clearing_preview = False
    self._row_select_interactive = True
    self._initial_scroll_to_selection = True
    
    self._icon_image_filepath = os.path.join(
      pg.config.PLUGIN_SUBDIRPATH, 'images', 'icon_image.png')
    self._icon_tag_filepath = os.path.join(
      pg.config.PLUGIN_SUBDIRPATH, 'images', 'icon_tag.png')
    
    self._init_gui()
  
  @property
  def batcher(self):
    return self._batcher
  
  @property
  def tree_view(self):
    return self._tree_view
  
  @property
  def collapsed_items(self):
    return self._collapsed_items
  
  @property
  def selected_items(self):
    return self._selected_items
  
  def update(self, reset_items=False, update_existing_contents_only=False):
    """Updates the preview (add/remove item, move item to a different parent
    item group, etc.).
    
    If `reset_items` is `True`, perform full update - add new items, remove
    non-existent items, etc. Note that setting this to `True` may introduce a
    performance penalty for hundreds of items.
    
    If `update_existing_contents_only` is `True`, only update the contents of
    the existing items. Note that the items will not be reparented,
    expanded/collapsed or added/removed even if they need to be. This option is
    useful if you know the item structure will be preserved.
    
    If an exception was captured during the update, the method is terminated
    prematurely. It is the responsibility of the caller to handle the error
    (e.g. lock or clear the preview).
    """
    update_locked = super().update()
    if update_locked:
      return
    
    if not update_existing_contents_only:
      self.clear()
    
    error = self._process_items(reset_items=reset_items)
    
    if error:
      self.emit('preview-updated', error)
      return
    
    items = self._get_items_to_process()
    
    if not update_existing_contents_only:
      self._insert_items(items)
      self._set_expanded_items()
    else:
      self._update_items(items)
    
    self._set_selection()
    self._set_item_tree_sensitive_for_selected(items)
    
    self._update_available_tags()
    
    self._tree_view.columns_autosize()
    
    self.emit('preview-updated', None)
  
  def clear(self):
    """
    Clear the entire preview.
    """
    self._clearing_preview = True
    self._tree_model.clear()
    self._tree_iters.clear()
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
    self.emit('preview-selection-changed')
  
  def get_items_from_selected_rows(self):
    return [self._batcher.item_tree[item_key]
            for item_key in self._get_keys_from_current_selection()]
  
  def get_item_from_cursor(self):
    tree_path, unused_ = self._tree_view.get_cursor()
    if tree_path is not None:
      item_key = self._get_key_from_tree_iter(self._tree_model.get_iter(tree_path))
      return self._batcher.item_tree[item_key]
    else:
      return None
  
  def _init_gui(self):
    self._tree_model = gtk.TreeStore(*[column[1] for column in self._COLUMNS])
    
    self._tree_view = gtk.TreeView(model=self._tree_model)
    self._tree_view.set_headers_visible(False)
    self._tree_view.set_enable_search(False)
    self._tree_view.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
    
    self._init_icons()
    
    self._init_tags_menu()
    
    column = gtk.TreeViewColumn(b'')
    
    cell_renderer_icon_item = gtk.CellRendererPixbuf()
    column.pack_start(cell_renderer_icon_item, expand=False)
    column.set_attributes(cell_renderer_icon_item, pixbuf=self._COLUMN_ICON_ITEM[0])
    
    cell_renderer_icon_tag = gtk.CellRendererPixbuf()
    cell_renderer_icon_tag.set_property('pixbuf', self._icons['tag'])
    column.pack_start(cell_renderer_icon_tag, expand=False)
    column.set_attributes(
      cell_renderer_icon_tag,
      visible=self._COLUMN_ICON_TAG_VISIBLE[0])
    
    cell_renderer_item_name = gtk.CellRendererText()
    column.pack_start(cell_renderer_item_name, expand=False)
    column.set_attributes(
      cell_renderer_item_name,
      text=self._COLUMN_ITEM_NAME[0],
      sensitive=self._COLUMN_ITEM_NAME_SENSITIVE[0])
    
    self._tree_view.append_column(column)
    
    self._scrolled_window = gtk.ScrolledWindow()
    self._scrolled_window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    self._scrolled_window.add(self._tree_view)
    
    self.pack_start(self._scrolled_window)
    
    self._tree_view.connect('row-collapsed', self._on_tree_view_row_collapsed)
    self._tree_view.connect('row-expanded', self._on_tree_view_row_expanded)
    self._tree_view.get_selection().connect('changed', self._on_tree_selection_changed)
    self._tree_view.connect('event', self._on_tree_view_right_button_press_event)
  
  def _init_icons(self):
    self._icons = {}
    self._icons['folder'] = self._tree_view.render_icon(
      gtk.STOCK_DIRECTORY, gtk.ICON_SIZE_MENU)
    self._icons['item'] = gtk.gdk.pixbuf_new_from_file_at_size(
      self._icon_image_filepath, -1, self._icons['folder'].props.height)
    self._icons['tag'] = gtk.gdk.pixbuf_new_from_file_at_size(
      self._icon_tag_filepath, -1, self._icons['folder'].props.height)
    
    self._icons['group'] = self._icons['item'].copy()
    
    scaling_factor = 0.8
    width_unscaled = self._icons['folder'].props.width
    width = int(width_unscaled * scaling_factor)
    height_unscaled = self._icons['folder'].props.height
    height = int(height_unscaled * scaling_factor)
    x_offset_unscaled = self._icons['group'].props.width - self._icons['folder'].props.width
    x_offset = x_offset_unscaled + width_unscaled - width
    y_offset_unscaled = self._icons['group'].props.height - self._icons['folder'].props.height
    y_offset = y_offset_unscaled + height_unscaled - height
    
    self._icons['folder'].composite(
      self._icons['group'],
      x_offset, y_offset, width, height, x_offset, y_offset,
      scaling_factor, scaling_factor, gtk.gdk.INTERP_BILINEAR, 255)
  
  def _init_tags_menu(self):
    self._tags_menu_items = {}
    self._tags_remove_submenu_items = {}
    
    self._tags_menu_relative_position = None
    
    self._tags_menu = gtk.Menu()
    self._tags_remove_submenu = gtk.Menu()
    
    self._tags_menu.append(gtk.SeparatorMenuItem())
    
    self._menu_item_add_tag = gtk.MenuItem(_('Add New Tag...'))
    self._menu_item_add_tag.connect('activate', self._on_menu_item_add_tag_activate)
    self._tags_menu.append(self._menu_item_add_tag)
    
    self._menu_item_remove_tag = gtk.MenuItem(_('Remove Tag'))
    self._menu_item_remove_tag.set_submenu(self._tags_remove_submenu)
    self._tags_menu.append(self._menu_item_remove_tag)
    
    for tag, tag_display_name in self._available_tags_setting.default_value.items():
      self._add_tag_menu_item(tag, tag_display_name)
    
    self._tags_menu.show_all()
  
  def _update_available_tags(self):
    used_tags = set()
    for item in self._batcher.item_tree.iter(filtered=False):
      for tag in item.tags:
        used_tags.add(tag)
        if tag not in self._tags_menu_items:
          self._add_tag_menu_item(tag, tag)
          self._add_remove_tag_menu_item(tag, tag)
    
    for tag, menu_item in self._tags_remove_submenu_items.items():
      menu_item.set_sensitive(tag not in used_tags)
    
    for tag in self._available_tags_setting.value:
      if tag not in self._tags_menu_items:
        self._add_tag_menu_item(tag, tag)
        self._add_remove_tag_menu_item(tag, tag)
    
    self._menu_item_remove_tag.set_sensitive(
      bool(self._tags_remove_submenu.get_children()))
    
    self._sort_tags_menu_items()
    
    for tag in self._tags_menu_items:
      if tag not in self._available_tags_setting.value:
        self._available_tags_setting.value[tag] = tag
    
    self._available_tags_setting.save()
  
  def _sort_tags_menu_items(self):
    for new_tag_position, tag in (
          enumerate(sorted(self._tags_menu_items, key=lambda tag: tag.lower()))):
      self._tags_menu.reorder_child(self._tags_menu_items[tag], new_tag_position)
      if tag in self._tags_remove_submenu_items:
        self._tags_remove_submenu.reorder_child(
          self._tags_remove_submenu_items[tag], new_tag_position)
  
  def _add_tag_menu_item(self, tag, tag_display_name):
    self._tags_menu_items[tag] = gtk.CheckMenuItem(tag_display_name)
    self._tags_menu_items[tag].connect('toggled', self._on_tags_menu_item_toggled, tag)
    self._tags_menu_items[tag].show()
    self._tags_menu.prepend(self._tags_menu_items[tag])
    
    return self._tags_menu_items[tag]
  
  def _add_remove_tag_menu_item(self, tag, tag_display_name):
    self._tags_remove_submenu_items[tag] = gtk.MenuItem(tag_display_name)
    self._tags_remove_submenu_items[tag].connect(
      'activate', self._on_tags_remove_submenu_item_activate, tag)
    self._tags_remove_submenu_items[tag].show()
    self._tags_remove_submenu.prepend(self._tags_remove_submenu_items[tag])
  
  def _on_tree_view_right_button_press_event(self, tree_view, event):
    if event.type == gtk.gdk.BUTTON_PRESS and event.button == 3:
      item_keys = []
      stop_event_propagation = False
      
      # Get the current selection. We cannot use `TreeSelection.get_selection()`
      # because this event is fired before the selection is updated.
      selection_at_pos = self._tree_view.get_path_at_pos(int(event.x), int(event.y))
      
      if (selection_at_pos is not None
          and self._tree_view.get_selection().count_selected_rows() > 1):
        item_keys = self._get_keys_from_current_selection()
        stop_event_propagation = True
      else:
        if selection_at_pos is not None:
          tree_iter = self._tree_model.get_iter(selection_at_pos[0])
          item_keys = [self._get_key_from_tree_iter(tree_iter)]
      
      self._toggle_tag_interactive = False
      
      items = [self._batcher.item_tree[item_key] for item_key in item_keys]
      for tag, tags_menu_item in self._tags_menu_items.items():
        tags_menu_item.set_active(all(tag in item.tags for item in items))
      
      self._toggle_tag_interactive = True
      
      if len(item_keys) >= 1:
        self._tags_menu.popup(None, None, None, event.button, event.time)
        
        toplevel_window = pg.gui.get_toplevel_window(self)
        if toplevel_window is not None:
          self._tags_menu_relative_position = toplevel_window.get_window().get_pointer()
      
      return stop_event_propagation
  
  def _on_tags_menu_item_toggled(self, tags_menu_item, tag):
    if self._toggle_tag_interactive:
      pdb.gimp_image_undo_group_start(self._batcher.input_image)
      
      for item_key in self._get_keys_from_current_selection():
        item = self._batcher.item_tree[item_key]
        
        if tags_menu_item.get_active():
          item.add_tag(tag)
        else:
          item.remove_tag(tag)
      
      pdb.gimp_image_undo_group_end(self._batcher.input_image)
      
      # Modifying just one item could result in renaming other items
      # differently, hence update the whole preview.
      self.update(update_existing_contents_only=True)
      
      self.emit('preview-tags-changed')
  
  def _on_menu_item_add_tag_activate(self, menu_item_add_tag):
    def _on_popup_focus_out_event(popup, event):
      popup.destroy()
    
    def _on_popup_key_press_event(popup, event):
      key_name = gtk.gdk.keyval_name(event.keyval)
      if key_name in ['Return', 'KP_Enter']:
        entry_text = entry_add_tag.get_text()
        if entry_text and entry_text not in self._tags_menu_items:
          menu_item = self._add_tag_menu_item(entry_text, entry_text)
          menu_item.set_active(True)
          self._add_remove_tag_menu_item(entry_text, entry_text)
        
        popup.destroy()
        return True
      elif key_name == 'Escape':
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
    
    toplevel = pg.gui.get_toplevel_window(self)
    if toplevel is not None:
      popup_add_tag.set_transient_for(toplevel)
    
    _set_popup_position(popup_add_tag, toplevel)
    
    label_tag_name = gtk.Label(_('Tag Name:'))
    
    entry_add_tag = gtk.Entry()
    
    hbox = gtk.HBox()
    hbox.set_spacing(self._ADD_TAG_POPUP_HBOX_SPACING)
    hbox.pack_start(label_tag_name, expand=False, fill=False)
    hbox.pack_start(entry_add_tag, expand=False, fill=False)
    hbox.set_border_width(self._ADD_TAG_POPUP_BORDER_WIDTH)
    
    frame = gtk.Frame()
    frame.add(hbox)
    
    popup_add_tag.add(frame)
    
    popup_add_tag.connect('focus-out-event', _on_popup_focus_out_event)
    popup_add_tag.connect('key-press-event', _on_popup_key_press_event)
    
    popup_add_tag.show_all()
  
  def _on_tags_remove_submenu_item_activate(self, tags_remove_submenu_item, tag):
    self._tags_remove_submenu.remove(tags_remove_submenu_item)
    self._tags_menu.remove(self._tags_menu_items[tag])
    
    del self._tags_menu_items[tag]
    del self._tags_remove_submenu_items[tag]
    del self._available_tags_setting.value[tag]
    
    self._menu_item_remove_tag.set_sensitive(
      bool(self._tags_remove_submenu.get_children()))
    
    self._available_tags_setting.save()
  
  def _on_tree_view_row_collapsed(self, tree_view, tree_iter, tree_path):
    if self._row_expand_collapse_interactive:
      self._collapsed_items.add(self._get_key_from_tree_iter(tree_iter))
      self._tree_view.columns_autosize()
  
  def _on_tree_view_row_expanded(self, tree_view, tree_iter, tree_path):
    if self._row_expand_collapse_interactive:
      item_key = self._get_key_from_tree_iter(tree_iter)
      if item_key in self._collapsed_items:
        self._collapsed_items.remove(item_key)
      
      self._set_expanded_items(tree_path)
      
      self._tree_view.columns_autosize()
  
  def _on_tree_selection_changed(self, tree_selection):
    if not self._clearing_preview and self._row_select_interactive:
      previous_selected_items = self._selected_items
      self._selected_items = self._get_keys_from_current_selection()
      
      self.emit('preview-selection-changed')
      
      if self.is_filtering and self._selected_items != previous_selected_items:
        self.update()
  
  def _get_keys_from_current_selection(self):
    unused_, tree_paths = self._tree_view.get_selection().get_selected_rows()
    return [
      self._get_key_from_tree_iter(self._tree_model.get_iter(tree_path))
      for tree_path in tree_paths]
  
  def _get_key(self, item):
    if item.type != pg.itemtree.TYPE_FOLDER:
      return item.raw.ID
    else:
      return (item.raw.ID, pg.itemtree.FOLDER_KEY)
  
  def _get_key_from_tree_iter(self, tree_iter):
    item_id = self._tree_model.get_value(tree_iter, column=self._COLUMN_ITEM_ID[0])
    item_type = self._tree_model.get_value(tree_iter, column=self._COLUMN_ITEM_TYPE[0])
    
    if item_type != pg.itemtree.TYPE_FOLDER:
      return item_id
    else:
      return (item_id, pg.itemtree.FOLDER_KEY)
  
  def _get_items_to_process(self):
    if self.is_filtering:
      with self._batcher.item_tree.filter.remove_temp(name=self._selected_items_filter_name):
        return list(self._batcher.item_tree)
    else:
      return list(self._batcher.item_tree)
  
  def _process_items(self, reset_items=False):
    if not reset_items:
      if self._initial_item_tree is not None:
        item_tree = self._initial_item_tree
        self._initial_item_tree = None
      else:
        item_tree = self._batcher.item_tree
    else:
      item_tree = None
    
    if item_tree is not None:
      # We need to reset item attributes explicitly before processing since
      # existing item trees are not automatically refreshed.
      for item in item_tree.iter_all():
        item.reset()
    
    error = None
    
    try:
      self._batcher.run(
        item_tree=item_tree,
        is_preview=True,
        process_contents=False,
        process_names=True,
        process_export=False,
        **utils_.get_settings_for_batcher(self._settings['main']))
    except exceptions.BatcherCancelError as e:
      pass
    except exceptions.ActionError as e:
      messages_.display_failure_message(
        messages_.get_failing_action_message(e),
        failure_message=str(e),
        details=traceback.format_exc(),
        parent=pg.gui.get_toplevel_window(self))
      
      error = e
    except Exception as e:
      messages_.display_failure_message(
        _('There was a problem with updating the name preview:'),
        failure_message=str(e),
        details=traceback.format_exc(),
        parent=pg.gui.get_toplevel_window(self))
      
      error = e
    
    return error
  
  def _update_items(self, items):
    updated_parents = set()
    for item in items:
      self._update_parent_items(item, updated_parents)
      self._update_item(item)
  
  def _insert_items(self, items):
    inserted_parents = set()
    for item in items:
      self._insert_parent_items(item, inserted_parents)
      self._insert_item(item)
  
  def _insert_item(self, item):
    if item.parent:
      parent_tree_iter = self._tree_iters[self._get_key(item.parent)]
    else:
      parent_tree_iter = None
    
    tree_iter = self._tree_model.append(
      parent_tree_iter,
      [self._get_icon_from_item(item),
       bool(item.tags),
       True,
       pg.utils.safe_encode_gtk(item.name),
       item.raw.ID,
       item.type])
    
    self._tree_iters[self._get_key(item)] = tree_iter
    
    return tree_iter
  
  def _update_item(self, item):
    self._tree_model.set(
      self._tree_iters[self._get_key(item)],
      self._COLUMN_ICON_TAG_VISIBLE[0],
      bool(item.tags),
      self._COLUMN_ITEM_NAME_SENSITIVE[0],
      True,
      self._COLUMN_ITEM_NAME[0],
      pg.utils.safe_encode_gtk(item.name))
  
  def _insert_parent_items(self, item, inserted_parents):
    for parent in item.parents:
      if parent not in inserted_parents:
        self._insert_item(parent)
        inserted_parents.add(parent)
  
  def _update_parent_items(self, item, updated_parents):
    for parent in item.parents:
      if parent not in updated_parents:
        self._update_item(parent)
        updated_parents.add(parent)
  
  def _set_item_tree_sensitive_for_selected(self, items):
    if self.is_filtering:
      self._set_items_sensitive(items, False)
      self._set_items_sensitive(
        [self._batcher.item_tree[item_key] for item_key in self._selected_items], True)
  
  def _get_item_sensitive(self, item):
    return self._tree_model.get_value(
      self._tree_iters[self._get_key(item)], self._COLUMN_ITEM_NAME_SENSITIVE[0])
  
  def _set_items_sensitive(self, items, sensitive):
    processed_parents = set()
    for item in items:
      self._set_item_sensitive(item, sensitive)
      self._set_parent_items_sensitive(item, processed_parents)
  
  def _set_item_sensitive(self, item, sensitive):
    if self._get_key(item) in self._tree_iters:
      self._tree_model.set_value(
        self._tree_iters[self._get_key(item)],
        self._COLUMN_ITEM_NAME_SENSITIVE[0],
        sensitive)
  
  def _set_parent_items_sensitive(self, item, processed_parents):
    for parent in reversed(list(item.parents)):
      if parent not in processed_parents:
        parent_sensitive = any(
          self._get_item_sensitive(child) for child in parent.children
          if self._get_key(child) in self._tree_iters)
        self._set_item_sensitive(parent, parent_sensitive)
        
        processed_parents.add(parent)
  
  def _get_icon_from_item(self, item):
    if item.type == pg.itemtree.TYPE_ITEM:
      return self._icons['item']
    elif item.type == pg.itemtree.TYPE_GROUP:
      return self._icons['group']
    elif item.type == pg.itemtree.TYPE_FOLDER:
      return self._icons['folder']
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
    
    for item_key in self._collapsed_items:
      if item_key in self._tree_iters:
        item_tree_iter = self._tree_iters[item_key]
        if item_tree_iter is None:
          continue
        
        item_tree_path = self._tree_model.get_path(item_tree_iter)
        if tree_path is None or self._tree_view.row_expanded(item_tree_path):
          self._tree_view.collapse_row(item_tree_path)
    
    self._row_expand_collapse_interactive = True
  
  def _remove_no_longer_valid_collapsed_items(self):
    if self._batcher.item_tree is None:
      return
    
    self._collapsed_items = set(
      [item_key for item_key in self._collapsed_items if item_key in self._batcher.item_tree])
  
  def _set_selection(self):
    self._row_select_interactive = False
    
    self._selected_items = [
      item_key for item_key in self._selected_items if item_key in self._tree_iters]
    
    for item_key in self._selected_items:
      tree_iter = self._tree_iters[item_key]
      if tree_iter is not None:
        self._tree_view.get_selection().select_iter(tree_iter)
    
    if self._initial_scroll_to_selection and self._selected_items:
      self._set_initial_scroll_to_selection()
      self._initial_scroll_to_selection = False
    
    self._row_select_interactive = True
  
  def _set_cursor(self, previous_cursor=None):
    self._row_select_interactive = False
    
    if previous_cursor is not None and self._tree_model.get_iter(previous_cursor) is not None:
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


gobject.type_register(NamePreview)
