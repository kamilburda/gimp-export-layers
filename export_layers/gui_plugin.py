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
import contextlib
import functools
import os
import traceback

import pygtk
pygtk.require("2.0")
import gtk
import pango

import gimp
import gimpenums
import gimpui

pdb = gimp.pdb

from export_layers.pygimplib import overwrite
from export_layers.pygimplib import pggui
from export_layers.pygimplib import pgsetting
from export_layers.pygimplib import pgsettinggroup
from export_layers.pygimplib import pgsettingpersistor

from export_layers import constants
from export_layers import exportlayers

#===============================================================================


def display_message(message, message_type, parent=None, buttons=gtk.BUTTONS_OK,
                    message_in_text_view=False):
  return pggui.display_message(
    message,
    message_type,
    title=_(constants.PLUGIN_TITLE),
    parent=parent,
    buttons=buttons,
    message_in_text_view=message_in_text_view
  )


def display_exception_message(exception_message, parent=None):
  pggui.display_exception_message(
    exception_message,
    plugin_title=_(constants.PLUGIN_TITLE),
    report_uri_list=constants.BUG_REPORT_URI_LIST,
    parent=parent
  )


def _format_export_error_message(exception):
  error_message = _("Sorry, but the export was unsuccessful."
                    " You can try exporting again if you fix the issue described below.")
  if not exception.message.endswith("."):
    exception.message += "."
  error_message += "\n" + str(exception)
  return error_message


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
      'name': 'advanced_settings_expanded',
      'default_value': False
    },
    {
      'type': pgsetting.SettingTypes.integer,
      'name': 'export_preview_pane_position',
      'default_value': 620
    },
    {
      'type': pgsetting.SettingTypes.boolean,
      'name': 'export_name_preview_enabled',
      'default_value': True,
      'gui_type': None
    },
  ])
  
  session_only_gui_settings = pgsettinggroup.SettingGroup('gui_session', [
    {
      'type': pgsetting.SettingTypes.image_IDs_and_directories,
      'name': 'image_ids_and_directories',
      'default_value': {}
    },
    {
      'type': pgsetting.SettingTypes.generic,
      'name': 'export_name_preview_layers_collapsed_state',
      # key: image ID; value: set of layer names collapsed in the name preview
      'default_value': collections.defaultdict(set)
    },
  ])
  
  settings.add([gui_settings, session_only_gui_settings])
  
  settings.set_ignore_tags({
    'gui': ['reset'],
    'gui_session': ['reset'],
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
      self.settings['main'].apply_gui_values_to_settings()
      self.settings['gui'].apply_gui_values_to_settings()
      
      self.current_directory_setting.gui.update_setting_value()
      self.settings['main']['output_directory'].set_value(self.current_directory_setting.value)
    except pgsetting.SettingValueError as e:
      self.display_message_label(e.message, message_type=gtk.MESSAGE_ERROR, setting=e.setting)
      return
    
    func(self, *args, **kwargs)
  
  return func_wrapper


def _update_directory(setting, current_image, directory_for_current_image):
  """
  Set the directory to the setting according to the priority list below:
  
  1. `directory_for_current_image` if not None
  2. `current_image` - import path of the current image if not None
  
  If update was performed, return True, otherwise return False.
  """
  
  if directory_for_current_image is not None:
    if isinstance(directory_for_current_image, bytes):
      directory_for_current_image = directory_for_current_image.decode()
    
    setting.set_value(directory_for_current_image)
    return True
  
  if current_image.filename is not None:
    setting.set_value(os.path.dirname(current_image.filename.decode()))
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
  
  settings['gui_session']['image_ids_and_directories'].update_image_ids_and_directories()
  
  update_performed = _update_directory(
    current_directory_setting, current_image,
    settings['gui_session']['image_ids_and_directories'].value[current_image.ID])
  
  if not update_performed:
    current_directory_setting.set_value(settings['main']['output_directory'].value)


def _setup_output_directory_changed(settings, current_image):

  def on_output_directory_changed(output_directory, image_ids_and_directories, current_image_id):
    image_ids_and_directories.update_directory(current_image_id, output_directory.value)
  
  settings['main']['output_directory'].connect_value_changed_event(
    on_output_directory_changed, settings['gui_session']['image_ids_and_directories'], current_image.ID)


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


class ExportNamePreview(object):
  
  _VBOX_SPACING = 5
  
  _COLUMNS = (_COLUMN_ICON_LAYER, _COLUMN_ICON_TAG_VISIBLE, _COLUMN_LAYER_NAME_SENSITIVE, _COLUMN_LAYER_NAME,
    _COLUMN_LAYER_ORIG_NAME) = ([0, gtk.gdk.Pixbuf], [1, bool], [2, bool], [3, bytes], [4, bytes])
  
  def __init__(self, layer_exporter, collapsed_items=None):
    self._layer_exporter = layer_exporter
    self._collapsed_items = collapsed_items if collapsed_items is not None else set()
    
    self._update_locked = False
    self._lock_keys = set()
    
    self._tree_iters = collections.defaultdict(lambda: None)
    self._selected_items = []
    
    self._row_expand_collapse_interactive = True
    self._toggle_tag_interactive = True
    self._clearing_preview = False
    
    self._init_gui()
    
    self.widget = self._preview_frame
  
  def update(self):
    """
    Update the export preview (add new layers, remove nonexistent layers, modify
    layer tree, etc.).
    """
    
    if not self._update_locked:
      self.clear()
      self._fill_preview()
      self._set_expanded_items()
      self._set_selection()
      self._tree_view.columns_autosize()
  
  def clear(self):
    """
    Clear the entire export preview.
    """
    
    self._clearing_preview = True
    self._tree_model.clear()
    self._clearing_preview = False
  
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
    self._vbox.pack_start(self._preview_label, expand=False, fill=False, padding=self._VBOX_SPACING)
    self._vbox.pack_start(self._scrolled_window)
    
    self._preview_frame = gtk.Frame()
    self._preview_frame.set_shadow_type(gtk.SHADOW_ETCHED_OUT)
    self._preview_frame.add(self._vbox)
    
    self._tree_view.connect("row-collapsed", self._on_tree_view_row_collapsed)
    self._tree_view.connect("row-expanded", self._on_tree_view_row_expanded)
    self._tree_view.get_selection().connect("changed", self._on_tree_selection_changed)
    self._tree_view.connect("event", self._on_tree_view_right_button_press)
  
  def _init_icons(self):
    self._icons = {}
    self._icons['layer_group'] = self._tree_view.render_icon(gtk.STOCK_DIRECTORY, gtk.ICON_SIZE_MENU)
    self._icons['layer'] = gtk.gdk.pixbuf_new_from_file_at_size(
      os.path.join(constants.PLUGIN_PATH, "image_icon.png"), -1, self._icons['layer_group'].props.height)
    self._icons['tag'] = gtk.gdk.pixbuf_new_from_file_at_size(
      os.path.join(constants.PLUGIN_PATH, "tag_icon.png"), -1, self._icons['layer_group'].props.height)
    
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
      self._collapsed_items.add(self._get_layer_orig_name(tree_iter))
      self._tree_view.columns_autosize()
  
  def _on_tree_view_row_expanded(self, widget, tree_iter, tree_path):
    if self._row_expand_collapse_interactive:
      layer_elem_orig_name = self._get_layer_orig_name(tree_iter)
      if layer_elem_orig_name in self._collapsed_items:
        self._collapsed_items.remove(layer_elem_orig_name)
      
      self._set_expanded_items(tree_path)
      
      self._tree_view.columns_autosize()
  
  def _on_tree_selection_changed(self, widget):
    if not self._clearing_preview:
      self._selected_items = self._get_layer_orig_names_in_current_selection()
  
  def _on_tree_view_right_button_press(self, widget, event):
    if event.type == gtk.gdk.BUTTON_PRESS and event.button == 3:
      layer_elem_orig_names = []
      stop_event_propagation = False
      
      # Get the current selection. We can't use `TreeSelection.get_selection()`
      # because this event is fired before the selection is updated.
      selection_at_pos = self._tree_view.get_path_at_pos(int(event.x), int(event.y))
      
      if selection_at_pos is not None and self._tree_view.get_selection().count_selected_rows() > 1:
        layer_elem_orig_names = self._get_layer_orig_names_in_current_selection()
        stop_event_propagation = True
      else:
        if selection_at_pos is not None:
          tree_iter = self._tree_model.get_iter(selection_at_pos[0])
          layer_elem_orig_names = [self._get_layer_orig_name(tree_iter)]
      
      self._toggle_tag_interactive = False
      
      if len(layer_elem_orig_names) == 1:
        layer_elem_orig_name = layer_elem_orig_names[0]
        layer_elem = self._layer_exporter.layer_data[layer_elem_orig_name]
        for tag in self._layer_exporter.SUPPORTED_TAGS:
          self._tags_menu_items[tag].set_active(tag in layer_elem.tags)
      elif len(layer_elem_orig_names) > 1:
        layer_elems = [self._layer_exporter.layer_data[layer_elem_orig_name]
                       for layer_elem_orig_name in layer_elem_orig_names]
        for tag, tags_menu_item in self._tags_menu_items.items():
          tags_menu_item.set_active(all(tag in layer_elem.tags for layer_elem in layer_elems))
      
      self._toggle_tag_interactive = True
      
      if len(layer_elem_orig_names) >= 1:
        self._tags_menu.popup(None, None, None, event.button, event.time)
      
      return stop_event_propagation
  
  def _on_tags_menu_item_toggled(self, tags_menu_item):
    if self._toggle_tag_interactive:
      should_update = False
      treat_tagged_layers_specially = self._layer_exporter.export_settings['tagged_layers_mode'].is_item('special')
      
      pdb.gimp_image_undo_group_start(self._layer_exporter.image)
      
      for layer_elem_orig_name in self._get_layer_orig_names_in_current_selection():
        layer_elem = self._layer_exporter.layer_data[layer_elem_orig_name]
        tag = self._tags_names[tags_menu_item.get_label()]
        
        had_previously_supported_tags = self._has_supported_tags(layer_elem)
        was_selected = self._tree_view.get_selection().iter_is_selected(self._tree_iters[layer_elem_orig_name])
        
        if tags_menu_item.get_active():
          new_layer_elem, modified_externally = self._layer_exporter.layer_data.add_tag(layer_elem, tag)
        else:
          new_layer_elem, modified_externally = self._layer_exporter.layer_data.remove_tag(layer_elem, tag)
        
        has_supported_tags = self._has_supported_tags(new_layer_elem)
        should_set_sensitivity = (has_supported_tags != had_previously_supported_tags and
                                  treat_tagged_layers_specially and new_layer_elem.item_type == new_layer_elem.ITEM)
        should_update = should_update or modified_externally or should_set_sensitivity
        
        if was_selected:
          self._selected_items.append(new_layer_elem.orig_name)
        
        self._set_layer_orig_name(self._tree_iters[layer_elem_orig_name],
                                  layer_elem_orig_name, new_layer_elem.orig_name)
        self._tree_model.set_value(self._tree_iters[new_layer_elem.orig_name], self._COLUMN_ICON_TAG_VISIBLE[0],
                                   has_supported_tags)
        if should_set_sensitivity:
          self._tree_model.set_value(
            self._tree_iters[new_layer_elem.orig_name], self._COLUMN_LAYER_NAME_SENSITIVE[0], not has_supported_tags)
      
      pdb.gimp_image_undo_group_end(self._layer_exporter.image)
      
      if should_update:
        # Modifying just one layer could result in renaming other layers differently,
        # hence update the whole preview.
        self.update()
  
  def _get_layer_orig_name(self, tree_iter):
    return self._tree_model.get_value(tree_iter, column=self._COLUMN_LAYER_ORIG_NAME[0]).decode(
      pggui.GTK_CHARACTER_ENCODING)
  
  def _set_layer_orig_name(self, tree_iter, old_orig_name, new_orig_name):
    self._tree_model.set_value(tree_iter, self._COLUMN_LAYER_ORIG_NAME[0],
                               new_orig_name.encode(pggui.GTK_CHARACTER_ENCODING))
    del self._tree_iters[old_orig_name]
    self._tree_iters[new_orig_name] = tree_iter
  
  def _get_layer_orig_names_in_current_selection(self):
    unused_, tree_paths = self._tree_view.get_selection().get_selected_rows()
    return [self._get_layer_orig_name(self._tree_model.get_iter(tree_path)) for tree_path in tree_paths]
  
  def _fill_preview(self):
    self._layer_exporter.export_layers(operations=['layer_name'])
    
    self._tree_iters.clear()
    
    self._enable_tagged_layers()
    
    for layer_elem in self._layer_exporter.layer_data:
      if self._layer_exporter.export_settings['layer_groups_as_folders'].value:
        self._insert_parent_item_elems(layer_elem)
      self._insert_item_elem(layer_elem)
    
    self._set_sensitive_tagged_layers()
  
  def _insert_item_elem(self, item_elem):
    if item_elem.parent:
      parent_tree_iter = self._tree_iters[item_elem.parent.orig_name]
    else:
      parent_tree_iter = None
    
    tree_iter = self._tree_model.append(parent_tree_iter,
      [self._get_icon_from_item_elem(item_elem),
       self._has_supported_tags(item_elem),
       True,
       item_elem.name.encode(pggui.GTK_CHARACTER_ENCODING),
       item_elem.orig_name.encode(pggui.GTK_CHARACTER_ENCODING)])
    self._tree_iters[item_elem.orig_name] = tree_iter
    
    return tree_iter
  
  def _insert_parent_item_elems(self, item_elem):
    for parent_elem in item_elem.parents:
      if not self._tree_iters[parent_elem.orig_name]:
        self._insert_item_elem(parent_elem)
  
  def _enable_tagged_layers(self):
    if self._layer_exporter.export_settings['tagged_layers_mode'].is_item('special'):
      self._layer_exporter.layer_data.filter.remove_rule(
        exportlayers.LayerFilterRules.has_no_tag, raise_if_not_found=False)
  
  def _set_sensitive_tagged_layers(self):
    if self._layer_exporter.export_settings['tagged_layers_mode'].is_item('special'):
      with self._layer_exporter.layer_data.filter.add_rule_temp(
             exportlayers.LayerFilterRules.has_tag, *self._layer_exporter.SUPPORTED_TAGS.keys()):
        for layer_elem in self._layer_exporter.layer_data:
          self._tree_model.set_value(
            self._tree_iters[layer_elem.orig_name], self._COLUMN_LAYER_NAME_SENSITIVE[0], False)
  
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
    
    for layer_elem_orig_name in self._collapsed_items:
      if layer_elem_orig_name in self._tree_iters:
        layer_elem_tree_iter = self._tree_iters[layer_elem_orig_name]
        if layer_elem_tree_iter is None:
          continue
        
        layer_elem_tree_path = self._tree_model.get_path(layer_elem_tree_iter)
        if tree_path is None or self._tree_view.row_expanded(layer_elem_tree_path):
          self._tree_view.collapse_row(layer_elem_tree_path)
    
    self._row_expand_collapse_interactive = True
  
  def _set_selection(self):
    self._selected_items = [item for item in self._selected_items if item in self._tree_iters]
    
    for item in self._selected_items:
      tree_iter = self._tree_iters[item]
      if tree_iter is not None:
        self._tree_view.get_selection().select_iter(tree_iter)


#===============================================================================


class _ExportLayersGui(object):
  
  HBOX_HORIZONTAL_SPACING = 8
  
  ADVANCED_SETTINGS_HORIZONTAL_SPACING = 12
  ADVANCED_SETTINGS_VERTICAL_SPACING = 6
  ADVANCED_SETTINGS_LEFT_MARGIN = 15
  
  DIALOG_SIZE = (900, 660)
  DIALOG_BORDER_WIDTH = 8
  DIALOG_VBOX_SPACING = 5
  ACTION_AREA_BORDER_WIDTH = 4
  
  def __init__(self, image, settings, session_source, persistent_source):
    self.image = image
    self.settings = settings
    self.session_source = session_source
    self.persistent_source = persistent_source
    
    self._message_setting = None
    
    add_gui_settings(settings)
    
    status, status_message = pgsettingpersistor.SettingPersistor.load(
      [self.settings['main'], self.settings['gui']], [self.session_source, self.persistent_source])
    if status == pgsettingpersistor.SettingPersistor.READ_FAIL:
      display_message(status_message, gtk.MESSAGE_WARNING)
    
    pgsettingpersistor.SettingPersistor.load([self.settings['gui_session']], [self.session_source])
    
    # Needs to be string to avoid strict directory validation
    self.current_directory_setting = pgsetting.StringSetting(
      'current_directory', settings['main']['output_directory'].default_value)
    
    _setup_image_ids_and_directories_and_initial_directory(
      self.settings, self.current_directory_setting, self.image)
    _setup_output_directory_changed(self.settings, self.image)
    
    self.layer_exporter = None
    
    self._init_gui()
    
    pggui.set_gui_excepthook_parent(self.dialog)
    
    gtk.main()
  
  def _init_gui(self):
    self.dialog = gimpui.Dialog(title=_(constants.PLUGIN_TITLE), role=constants.PLUGIN_PROGRAM_NAME)
    self.dialog.set_transient()
    
    self.dialog.set_default_size(*self.DIALOG_SIZE)
    self.dialog.set_border_width(self.DIALOG_BORDER_WIDTH)
    
    self.folder_chooser_label = gtk.Label()
    self.folder_chooser_label.set_markup("<b>" + _("Save in folder:") + "</b>")
    self.folder_chooser_label.set_alignment(0.0, 0.5)
    
    self.folder_chooser = gtk.FileChooserWidget(action=gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER)
    
    self.export_name_preview = ExportNamePreview(
      exportlayers.LayerExporter(gimpenums.RUN_NONINTERACTIVE, self.image, self.settings['main']),
      self.settings['gui_session']['export_name_preview_layers_collapsed_state'].value[self.image.ID])
    
    self.vbox_folder_chooser = gtk.VBox(homogeneous=False)
    self.vbox_folder_chooser.set_spacing(self.DIALOG_VBOX_SPACING * 2)
    self.vbox_folder_chooser.pack_start(self.folder_chooser_label, expand=False, fill=False)
    self.vbox_folder_chooser.pack_start(self.folder_chooser)
    
    self.hpaned_chooser_and_previews = gtk.HPaned()
    self.hpaned_chooser_and_previews.pack1(self.vbox_folder_chooser, resize=True, shrink=False)
    self.hpaned_chooser_and_previews.pack2(self.export_name_preview.widget)
    self.hpaned_previous_position = self.settings['gui']['export_preview_pane_position'].value
        
    self.file_extension_label = gtk.Label()
    self.file_extension_label.set_markup("<b>" + self.settings['main']['file_extension'].display_name + ":</b>")
    self.file_extension_label.set_alignment(0.0, 0.5)
    
    self.file_extension_entry = pggui.FileExtensionEntry()
    self.file_extension_entry.set_size_request(100, -1)
    
    self.label_message = gtk.Label()
    self.label_message.set_alignment(0.0, 0.5)
    self.label_message.set_ellipsize(pango.ELLIPSIZE_MIDDLE)
    
    self.expander_advanced_settings = gtk.Expander()
    self.expander_advanced_settings.set_use_markup(True)
    self.expander_advanced_settings.set_use_underline(True)
    self.expander_advanced_settings.set_label("<b>" + _("_Advanced Settings") + "</b>")
    self.expander_advanced_settings.set_spacing(self.ADVANCED_SETTINGS_VERTICAL_SPACING // 2)
    
    self.advanced_settings_file_extension_mode_label = gtk.Label(
      self.settings['main']['file_extension_mode'].display_name + ":")
    self.advanced_settings_file_extension_mode_label.set_alignment(0, 0.5)
    
    self.advanced_settings_tagged_layers_mode_label = gtk.Label(
      self.settings['main']['tagged_layers_mode'].display_name + ":")
    self.advanced_settings_tagged_layers_mode_label.set_alignment(0, 0.5)
    
    self.settings.initialize_gui({
      'file_extension': [pgsetting.SettingGuiTypes.file_extension_entry, self.file_extension_entry],
      'dialog_position': [pgsetting.SettingGuiTypes.window_position, self.dialog],
      'advanced_settings_expanded': [pgsetting.SettingGuiTypes.expander, self.expander_advanced_settings],
      'export_preview_pane_position': [pgsetting.SettingGuiTypes.paned_position, self.hpaned_chooser_and_previews],
    })
    
    self.current_directory_setting.set_gui(pgsetting.SettingGuiTypes.folder_chooser, self.folder_chooser)
    
    self.hbox_file_extension_entry = gtk.HBox(homogeneous=False)
    self.hbox_file_extension_entry.set_spacing(30)
    self.hbox_file_extension_entry.pack_start(self.file_extension_label, expand=False, fill=True)
    self.hbox_file_extension_entry.pack_start(self.file_extension_entry, expand=False, fill=True)
    
    self.hbox_file_extension = gtk.HBox(homogeneous=False)
    self.hbox_file_extension.set_spacing(self.HBOX_HORIZONTAL_SPACING)
    self.hbox_file_extension.pack_start(self.hbox_file_extension_entry, expand=False, fill=True)
    self.hbox_file_extension.pack_start(self.label_message, expand=True, fill=True)
    
    self.hbox_export_settings = gtk.HBox(homogeneous=False)
    self.hbox_export_settings.pack_start(self.settings['main']['layer_groups_as_folders'].gui.element)
    self.hbox_export_settings.pack_start(self.settings['main']['ignore_invisible'].gui.element)
    self.hbox_export_settings.pack_start(self.settings['main']['autocrop'].gui.element)
    self.hbox_export_settings.pack_start(self.settings['main']['use_image_size'].gui.element)
    
    self.table_labels = gtk.Table(rows=2, columns=1, homogeneous=False)
    self.table_labels.set_row_spacings(self.ADVANCED_SETTINGS_VERTICAL_SPACING)
    self.table_labels.attach(self.advanced_settings_file_extension_mode_label, 0, 1, 0, 1)
    self.table_labels.attach(self.advanced_settings_tagged_layers_mode_label, 0, 1, 1, 2)
    
    self.table_combo_boxes = gtk.Table(rows=2, columns=1, homogeneous=False)
    self.table_combo_boxes.set_row_spacings(self.ADVANCED_SETTINGS_VERTICAL_SPACING)
    self.table_combo_boxes.attach(
      self.settings['main']['file_extension_mode'].gui.element, 0, 1, 0, 1, yoptions=0)
    self.table_combo_boxes.attach(
      self.settings['main']['tagged_layers_mode'].gui.element, 0, 1, 1, 2, yoptions=0)
    
    tagged_layers_description = _(
      "To use a layer as a background for other layers, right-click in the preview on the layer "
      "and select \"{0}\"."
      "\nFor foreground layers, select \"{1}\"."
      "\nTo enable handling of tagged layers, select \"{2}\".").format(
        exportlayers.LayerExporter.SUPPORTED_TAGS['background'],
        exportlayers.LayerExporter.SUPPORTED_TAGS['foreground'],
        self.settings['main']['tagged_layers_mode'].items_display_names['special'])
    
    self.advanced_settings_tagged_layers_mode_label.set_tooltip_text(tagged_layers_description)
    self.settings['main']['tagged_layers_mode'].gui.element.set_tooltip_text(tagged_layers_description)
    
    self.table_additional_elems = gtk.Table(rows=2, columns=1, homogeneous=False)
    self.table_additional_elems.set_row_spacings(self.ADVANCED_SETTINGS_VERTICAL_SPACING)
    self.table_additional_elems.attach(self.settings['main']['strip_mode'].gui.element, 0, 1, 0, 1, yoptions=0)
    self.table_additional_elems.attach(self.settings['main']['crop_mode'].gui.element, 0, 1, 1, 2)
    
    self.hbox_tables = gtk.HBox(homogeneous=False)
    self.hbox_tables.set_spacing(self.ADVANCED_SETTINGS_HORIZONTAL_SPACING)
    self.hbox_tables.pack_start(self.table_labels, expand=False, fill=True)
    self.hbox_tables.pack_start(self.table_combo_boxes, expand=False, fill=True)
    self.hbox_tables.pack_start(self.table_additional_elems, expand=False, fill=True)
    
    self.hbox_advanced_settings_checkbuttons = gtk.HBox(homogeneous=False)
    self.hbox_advanced_settings_checkbuttons.set_spacing(self.ADVANCED_SETTINGS_HORIZONTAL_SPACING)
    self.hbox_advanced_settings_checkbuttons.pack_start(
      self.settings['main']['merge_layer_groups'].gui.element, expand=False, fill=True)
    self.hbox_advanced_settings_checkbuttons.pack_start(
      self.settings['main']['empty_folders'].gui.element, expand=False, fill=True)
    self.hbox_advanced_settings_checkbuttons.pack_start(
      self.settings['main']['ignore_layer_modes'].gui.element, expand=False, fill=True)
    
    self.vbox_advanced_settings = gtk.VBox(homogeneous=False)
    self.vbox_advanced_settings.set_spacing(self.ADVANCED_SETTINGS_VERTICAL_SPACING)
    self.vbox_advanced_settings.pack_start(self.hbox_tables, expand=False, fill=False)
    self.vbox_advanced_settings.pack_start(self.hbox_advanced_settings_checkbuttons, expand=False, fill=False)
    
    self.alignment_advanced_settings = gtk.Alignment()
    self.alignment_advanced_settings.set_padding(0, 0, self.ADVANCED_SETTINGS_LEFT_MARGIN, 0)
    self.alignment_advanced_settings.add(self.vbox_advanced_settings)
    self.expander_advanced_settings.add(self.alignment_advanced_settings)
    
    self.export_layers_button = self.dialog.add_button(_("_Export"), gtk.RESPONSE_OK)
    self.export_layers_button.grab_default()
    self.cancel_button = self.dialog.add_button(_("_Cancel"), gtk.RESPONSE_CANCEL)
    self.dialog.set_alternative_button_order([gtk.RESPONSE_OK, gtk.RESPONSE_CANCEL])
    
    self.stop_button = gtk.Button()
    self.stop_button.set_label(_("_Stop"))
    
    self.save_settings_button = gtk.Button()
    self.save_settings_button.set_label(_("Save Settings"))
    self.save_settings_button.set_tooltip_text(
      _("Save settings permanently. "
        "If you start GIMP again, the saved settings will be loaded "
        "when {0} is first opened.").format(constants.PLUGIN_TITLE)
    )
    self.reset_settings_button = gtk.Button()
    self.reset_settings_button.set_label(_("Reset Settings"))
    
    self.progress_bar = gtk.ProgressBar()
    self.progress_bar.set_ellipsize(pango.ELLIPSIZE_MIDDLE)
    
    self.dialog.action_area.pack_end(self.stop_button, expand=False, fill=True)
    self.dialog.action_area.pack_start(self.save_settings_button, expand=False, fill=True)
    self.dialog.action_area.pack_start(self.reset_settings_button, expand=False, fill=True)
    self.dialog.action_area.set_child_secondary(self.save_settings_button, True)
    self.dialog.action_area.set_child_secondary(self.reset_settings_button, True)
    
    self.dialog.vbox.set_spacing(self.DIALOG_VBOX_SPACING)
    self.dialog.vbox.pack_start(self.hpaned_chooser_and_previews)
    self.dialog.vbox.pack_start(self.hbox_file_extension, expand=False, fill=False)
    self.dialog.vbox.pack_start(self.hbox_export_settings, expand=False, fill=False)
    self.dialog.vbox.pack_start(self.expander_advanced_settings, expand=False, fill=False)
    self.dialog.vbox.pack_start(gtk.HSeparator(), expand=False, fill=True)
    self.dialog.vbox.pack_end(self.progress_bar, expand=False, fill=True)
    # Move the action area above the progress bar.
    self.dialog.vbox.reorder_child(self.dialog.action_area, -1)
    
    self.export_layers_button.connect("clicked", self.on_export_click)
    self.cancel_button.connect("clicked", self.cancel)
    self.stop_button.connect("clicked", self.stop)
    self.dialog.connect("delete-event", self.close)
    
    self.save_settings_button.connect("clicked", self.on_save_settings_clicked)
    self.reset_settings_button.connect("clicked", self.on_reset_settings_clicked)
    
    self.file_extension_entry.connect("changed", self.on_file_extension_entry_changed)
    self.expander_advanced_settings.connect("notify::expanded", self.on_expander_advanced_settings_expanded_changed)
    
    self.dialog.connect("notify::is-active", self.on_dialog_is_active_changed)
    self.hpaned_chooser_and_previews.connect("event", self.on_hpaned_left_button_up)
    
    self._connect_setting_changes_to_preview()
    
    self.dialog.set_default_response(gtk.RESPONSE_CANCEL)
    
    self.dialog.vbox.show_all()
    self.progress_bar.hide()
    self.stop_button.hide()
    
    self.export_name_preview.widget.connect("notify::visible", self.on_preview_visible_changed)
    if not self.settings['gui']['export_name_preview_enabled'].value:
      self.export_name_preview.lock_update(True, "preview_enabled")
    self._handle_pane_for_advanced_settings()
    
    self.dialog.set_focus(self.file_extension_entry)
    self.dialog.set_default(self.export_layers_button)
    self.file_extension_entry.set_activates_default(True)
    # Place the cursor at the end of the text entry.
    self.file_extension_entry.set_position(-1)
    
    self.dialog.show()
    self.dialog.action_area.set_border_width(self.ACTION_AREA_BORDER_WIDTH)
  
  def reset_settings(self):
    for setting_group in [self.settings['main'], self.settings['gui']]:
      setting_group.reset()
  
  def save_settings(self):
    status, status_message = pgsettingpersistor.SettingPersistor.save(
      [self.settings['main'], self.settings['gui']], [self.session_source, self.persistent_source])
    if status == pgsettingpersistor.SettingPersistor.WRITE_FAIL:
      display_message(status_message, gtk.MESSAGE_WARNING, parent=self.dialog)
    
    pgsettingpersistor.SettingPersistor.save([self.settings['gui_session']], [self.session_source])
  
  def on_file_extension_entry_changed(self, widget):
    try:
      self.settings['main']['file_extension'].gui.update_setting_value()
    except pgsetting.SettingValueError as e:
      pggui.timeout_add_strict(100, self.export_name_preview.clear)
      
      self.display_message_label(e.message, message_type=gtk.MESSAGE_ERROR,
        setting=self.settings['main']['file_extension'])
      self.export_name_preview.lock_update(True, "invalid_file_extension")
    else:
      self.export_name_preview.lock_update(False, "invalid_file_extension")
      if self._message_setting == self.settings['main']['file_extension']:
        self.display_message_label(None)
      
      pggui.timeout_add_strict(100, self.export_name_preview.update)
  
  def on_expander_advanced_settings_expanded_changed(self, widget, property_spec):
    self._handle_pane_for_advanced_settings()
  
  def _handle_pane_for_advanced_settings(self):
    if self.expander_advanced_settings.get_expanded():
      self.export_name_preview.widget.show()
    else:
      self.export_name_preview.widget.hide()
  
  def on_dialog_is_active_changed(self, widget, property_spec):
    if self.dialog.is_active():
      self.export_name_preview.update()
  
  def _connect_setting_changes_to_preview(self):
    def _on_setting_changed(setting):
      pggui.timeout_add_strict(50, self.export_name_preview.update)
    
    for setting in self.settings['main']:
      if setting.name not in ['file_extension', 'output_directory', 'overwrite_mode']:
        setting.connect_value_changed_event(_on_setting_changed)
  
  def on_hpaned_left_button_up(self, widget, event):
    if event.type == gtk.gdk.BUTTON_RELEASE and event.button == 1:
      current_position = self.hpaned_chooser_and_previews.get_position()
      max_position = self.hpaned_chooser_and_previews.get_property("max-position")
      
      if (current_position == max_position and self.hpaned_previous_position != current_position):
        self.export_name_preview.clear()
        self.settings['gui']['export_name_preview_enabled'].set_value(False)
        self.export_name_preview.lock_update(True, "preview_enabled")
      elif (current_position != max_position and self.hpaned_previous_position == max_position):
        self.export_name_preview.lock_update(False, "preview_enabled")
        self.settings['gui']['export_name_preview_enabled'].set_value(True)
        self.export_name_preview.update()
      
      self.hpaned_previous_position = current_position
  
  def on_preview_visible_changed(self, widget, property_spec):
    preview_visible = self.export_name_preview.widget.get_visible()
    self.export_name_preview.lock_update(not preview_visible, "preview_visible")
    if preview_visible:
      self.export_name_preview.update()
  
  @_set_settings
  def on_save_settings_clicked(self, widget):
    self.save_settings()
    self.display_message_label(_("Settings successfully saved."), message_type=gtk.MESSAGE_INFO)
 
  def on_reset_settings_clicked(self, widget):
    response_id = display_message(_("Do you really want to reset settings?"),
                                  gtk.MESSAGE_WARNING, parent=self.dialog,
                                  buttons=gtk.BUTTONS_YES_NO)
    
    if response_id == gtk.RESPONSE_YES:
      self.reset_settings()
      self.save_settings()
      self.display_message_label(_("Settings reset."), message_type=gtk.MESSAGE_INFO)
  
  @_set_settings
  def on_export_click(self, widget):
    self.setup_gui_before_export()
    pdb.gimp_progress_init("", None)
    
    overwrite_chooser = pggui.GtkDialogOverwriteChooser(
      # Don't insert the Cancel item as a button.
      zip(self.settings['main']['overwrite_mode'].items.values()[:-1],
          self.settings['main']['overwrite_mode'].items_display_names.values()[:-1]),
      default_value=self.settings['main']['overwrite_mode'].items['replace'],
      default_response=self.settings['main']['overwrite_mode'].items['cancel'],
      title=_(constants.PLUGIN_TITLE),
      parent=self.dialog)
    progress_updater = pggui.GtkProgressUpdater(self.progress_bar)
    
    self.layer_exporter = exportlayers.LayerExporter(
      gimpenums.RUN_INTERACTIVE, self.image, self.settings['main'], overwrite_chooser, progress_updater,
      export_context_manager=_handle_gui_in_export, export_context_manager_args=[self.dialog])
    should_quit = True
    try:
      self.layer_exporter.export_layers()
    except exportlayers.ExportLayersCancelError as e:
      should_quit = False
    except exportlayers.ExportLayersError as e:
      display_message(_format_export_error_message(e), message_type=gtk.MESSAGE_WARNING,
                      parent=self.dialog, message_in_text_view=True)
      should_quit = False
    except Exception as e:
      display_exception_message(traceback.format_exc(), parent=self.dialog)
    else:
      self.settings['special']['first_plugin_run'].set_value(False)
      pgsettingpersistor.SettingPersistor.save(
        [self.settings['special']['first_plugin_run']], [self.session_source])
      
      if not self.layer_exporter.exported_layers:
        display_message(_("No layers were exported."), gtk.MESSAGE_INFO, parent=self.dialog)
        should_quit = False
    finally:
      pdb.gimp_progress_end()
    
    self.settings['main']['overwrite_mode'].set_value(overwrite_chooser.overwrite_mode)
    pgsettingpersistor.SettingPersistor.save(
      [self.settings['main'], self.settings['gui'], self.settings['gui_session']], [self.session_source])
    
    if should_quit:
      gtk.main_quit()
    else:
      self.restore_gui_after_export()
      progress_updater.reset()
  
  def setup_gui_before_export(self):
    self.display_message_label(None)
    self._set_gui_enabled(False)
  
  def restore_gui_after_export(self):
    self._set_gui_enabled(True)
  
  def _set_gui_enabled(self, enabled):
    self.progress_bar.set_visible(not enabled)
    self.stop_button.set_visible(not enabled)
    self.cancel_button.set_visible(enabled)
    
    for child in self.dialog.vbox:
      if child not in (self.dialog.action_area, self.progress_bar):
        child.set_sensitive(enabled)
    
    for button in self.dialog.action_area:
      if button != self.stop_button:
        button.set_sensitive(enabled)
    
    if enabled:
      self.dialog.set_focus(self.file_extension_entry)
      self.file_extension_entry.set_position(-1)
    else:
      self.dialog.set_focus(self.stop_button)
  
  def close(self, widget, event):
    gtk.main_quit()
  
  def cancel(self, widget):
    gtk.main_quit()
  
  def stop(self, widget):
    if self.layer_exporter is not None:
      self.layer_exporter.should_stop = True
  
  def display_message_label(self, text, message_type=gtk.MESSAGE_ERROR, setting=None):
    self._message_setting = setting
    
    if text is None or not text:
      self.label_message.set_text("")
    else:
      text = text[0].upper() + text[1:]
      if not text.endswith("."):
        text += "."
      
      # Display literal "&" as intended. Required by the markup.
      text = text.replace("&", "&amp;")
      
      if message_type == gtk.MESSAGE_ERROR:
        color = "red"
      else:
        color = "blue"
      
      self.label_message.set_markup("<span foreground='{0}'><b>{1}</b></span>".format(color, text))


#===============================================================================


class ExportDialog(object):
  
  _HBOX_HORIZONTAL_SPACING = 8
  _DIALOG_WIDTH = 500
  
  def __init__(self, stop_event):
    self.stop_event = stop_event
    self._init_gui()
  
  def _init_gui(self):
    self._dialog = gimpui.Dialog(title=_(constants.PLUGIN_TITLE), role=None)
    self._dialog.set_transient()
    self._dialog.set_border_width(8)
    self._dialog.set_default_size(self._DIALOG_WIDTH, -1)
    
    self._progress_bar = gtk.ProgressBar()
    self._progress_bar.set_ellipsize(pango.ELLIPSIZE_MIDDLE)
    
    self._stop_button = gtk.Button()
    self._stop_button.set_label(_("_Stop"))
    
    self._buttonbox = gtk.HButtonBox()
    self._buttonbox.pack_start(self._stop_button, expand=False, fill=True)
    
    self._hbox_action_area = gtk.HBox(homogeneous=False)
    self._hbox_action_area.set_spacing(self._HBOX_HORIZONTAL_SPACING)
    self._hbox_action_area.pack_start(self._progress_bar, expand=True, fill=True)
    self._hbox_action_area.pack_end(self._buttonbox, expand=False, fill=True)
    
    self._dialog.vbox.pack_end(self._hbox_action_area, expand=False, fill=False)
    
    self._stop_button.connect("clicked", self.stop_event)
    self._dialog.connect("delete-event", self.stop_event)
  
  @property
  def dialog(self):
    return self._dialog
  
  @property
  def progress_bar(self):
    return self._progress_bar
  
  def show(self):
    self._dialog.vbox.show_all()
    self._dialog.action_area.hide()
    self._dialog.show()
  
  def hide(self):
    self._dialog.hide()


#===============================================================================


class _ExportLayersRepeatGui(object):
  
  def __init__(self, image, settings, session_source, persistent_source):
    self.image = image
    self.settings = settings
    self.session_source = session_source
    self.persistent_source = persistent_source
    
    pgsettingpersistor.SettingPersistor.load([self.settings['main']], [self.session_source])
    
    self.layer_exporter = None
    
    self.export_dialog = ExportDialog(self.stop)
    
    pggui.set_gui_excepthook_parent(self.export_dialog.dialog)
    
    gtk.main_iteration()
    self.export_dialog.show()
    self.export_layers()
  
  def export_layers(self):
    overwrite_chooser = overwrite.NoninteractiveOverwriteChooser(self.settings['main']['overwrite_mode'].value)
    progress_updater = pggui.GtkProgressUpdater(self.export_dialog.progress_bar)
    
    pdb.gimp_progress_init("", None)
    
    self.layer_exporter = exportlayers.LayerExporter(
      gimpenums.RUN_WITH_LAST_VALS, self.image, self.settings['main'], overwrite_chooser, progress_updater,
      export_context_manager=_handle_gui_in_export, export_context_manager_args=[self.export_dialog.dialog])
    try:
      self.layer_exporter.export_layers()
    except exportlayers.ExportLayersCancelError:
      pass
    except exportlayers.ExportLayersError as e:
      display_message(_format_export_error_message(e), message_type=gtk.MESSAGE_WARNING,
                      parent=self.export_dialog.dialog, message_in_text_view=True)
    else:
      if not self.layer_exporter.exported_layers:
        display_message(_("No layers were exported."), gtk.MESSAGE_INFO, parent=self.export_dialog.dialog)
    finally:
      pdb.gimp_progress_end()
  
  def stop(self, widget, *args):
    if self.layer_exporter is not None:
      self.layer_exporter.should_stop = True


#===============================================================================


def export_layers_gui(image, settings, session_source, persistent_source):
  _ExportLayersGui(image, settings, session_source, persistent_source)


def export_layers_repeat_gui(image, settings, session_source, persistent_source):
  _ExportLayersRepeatGui(image, settings, session_source, persistent_source)
