#
# This file is part of Export Layers.
#
# Copyright (C) 2013-2016 khalim19 <khalim19@gmail.com>
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
from export_layers.pygimplib import pggui_entries
from export_layers.pygimplib import pgutils
from export_layers.pygimplib import pgsetting
from export_layers.pygimplib import pgsettinggroup
from export_layers.pygimplib import pgsettingpersistor

from export_layers import exportlayers
from export_layers import gui_operations
from export_layers import gui_previews
from export_layers import settings_plugin

#===============================================================================


def display_message(message, message_type, parent=None, buttons=gtk.BUTTONS_OK,
                    message_in_text_view=False, button_response_id_to_focus=None):
  return pggui.display_message(
    message, message_type, title=pygimplib.config.PLUGIN_TITLE, parent=parent, buttons=buttons,
    message_in_text_view=message_in_text_view, button_response_id_to_focus=button_response_id_to_focus)


def display_export_failure_message(exception, parent=None):
  error_message = _(
    "Sorry, but the export was unsuccessful. "
    "You can try exporting again if you fix the issue described below.")
  if not exception.message.endswith("."):
    exception.message += "."
  error_message += "\n" + str(exception)
  
  display_message(error_message, message_type=gtk.MESSAGE_WARNING, parent=parent, message_in_text_view=True)


def display_export_failure_invalid_image_message(details, parent=None):
  dialog = gtk.MessageDialog(
    parent=parent, type=gtk.MESSAGE_WARNING, flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT)
  dialog.set_transient_for(parent)
  dialog.set_title(pygimplib.config.PLUGIN_TITLE)
  
  dialog.set_markup(
    _("Sorry, but the export was unsuccessful. "
      "Do not close the image when exporting, keep it open until the export finishes successfully."))
  
  dialog.format_secondary_markup(
    _("If you believe this is a different error, you can help fix it by sending a report with the text "
      "in the details to one of the sites below."))
  
  expander = pggui.get_exception_details_expander(details)
  dialog.vbox.pack_start(expander, expand=False, fill=False)
  
  if pygimplib.config.BUG_REPORT_URI_LIST:
    vbox_labels_report = pggui.get_report_link_buttons(pygimplib.config.BUG_REPORT_URI_LIST)
    dialog.vbox.pack_start(vbox_labels_report, expand=False, fill=False)
  
  close_button = dialog.add_button(gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE)
  
  dialog.set_focus(close_button)
  
  dialog.show_all()
  dialog.run()
  dialog.destroy()


def display_reset_prompt(parent=None, more_settings_shown=False):
  dialog = gtk.MessageDialog(
    parent=parent, type=gtk.MESSAGE_WARNING, flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
    buttons=gtk.BUTTONS_YES_NO)
  dialog.set_transient_for(parent)
  dialog.set_title(pygimplib.config.PLUGIN_TITLE)
  
  dialog.set_markup(_("Do you really want to reset settings?"))
  
  if more_settings_shown:
    checkbutton_reset_operations = gtk.CheckButton(label=_("Remove operations and filters"), use_underline=False)
    dialog.vbox.pack_start(checkbutton_reset_operations, expand=False, fill=False)
  
  dialog.set_focus(dialog.get_widget_for_response(gtk.RESPONSE_NO))
  
  dialog.show_all()
  response_id = dialog.run()
  dialog.destroy()
  
  return response_id, checkbutton_reset_operations.get_active() if more_settings_shown else False


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
      'type': pgsetting.SettingTypes.generic,
      'name': 'dialog_size',
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
      'default_value': 610
    },
    {
      'type': pgsetting.SettingTypes.float,
      'name': 'previews_vpane_position',
      'default_value': 320
    },
    {
      'type': pgsetting.SettingTypes.float,
      'name': 'settings_vpane_position',
      'default_value': -1
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
    {
      'type': pgsetting.SettingTypes.generic,
      'name': 'displayed_builtin_operations',
      'default_value': [],
      'gui_type': None
    },
    {
      'type': pgsetting.SettingTypes.generic,
      'name': 'displayed_builtin_filters',
      'default_value': [],
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
      'default_value': collections.defaultdict(pgutils.empty_func)
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
      'default_value': collections.defaultdict(pgutils.empty_func)
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
      
      self._settings['gui/displayed_builtin_operations'].set_value(
        self._box_more_operations.displayed_settings_names)
      self._settings['gui/displayed_builtin_filters'].set_value(
        self._box_more_filters.displayed_settings_names)
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
  _MORE_SETTINGS_OPERATIONS_SPACING = 4
  
  _DIALOG_SIZE = (900, 610)
  _DIALOG_BORDER_WIDTH = 8
  _DIALOG_VBOX_SPACING = 5
  _DIALOG_ACTION_AREA_PADDING = 5
  _DIALOG_BUTTONS_HORIZONTAL_SPACING = 6
  
  _FILE_EXTENSION_ENTRY_WIDTH_CHARS = 8
  _FILENAME_PATTERN_ENTRY_MIN_WIDTH_CHARS = 15
  _FILENAME_PATTERN_ENTRY_MAX_WIDTH_CHARS = 50
  
  _DELAY_PREVIEWS_SETTINGS_UPDATE_MILLISECONDS = 50
  _DELAY_PREVIEWS_PANE_DRAG_UPDATE_MILLISECONDS = 500
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
    
    self._export_name_preview = gui_previews.ExportNamePreview(
      self._layer_exporter_for_previews,
      self._initial_layer_tree,
      self._settings['gui_session/export_name_preview_layers_collapsed_state'].value[self._image.ID],
      self._settings['main/selected_layers'].value[self._image.ID],
      on_selection_changed_func=self._on_name_preview_selection_changed,
      on_after_update_func=self._on_name_preview_after_update,
      on_after_edit_tags_func=self._on_name_preview_after_edit_tags)
    
    self._export_image_preview = gui_previews.ExportImagePreview(
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
    self._file_extension_label.set_markup(
      "<b>" + gobject.markup_escape_text(self._settings['main/file_extension'].display_name) + ":</b>")
    self._file_extension_label.set_alignment(0.0, 0.5)
    
    self._file_extension_entry = pggui_entries.FileExtensionEntry()
    self._file_extension_entry.set_width_chars(self._FILE_EXTENSION_ENTRY_WIDTH_CHARS)
    
    self._save_as_label = gtk.Label()
    self._save_as_label.set_markup("<b>" + _("Save as") + ":</b>")
    self._save_as_label.set_alignment(0.0, 0.5)
    
    self._dot_label = gtk.Label(".")
    self._dot_label.set_alignment(0.0, 1.0)
    
    self._filename_pattern_entry = pggui_entries.FilenamePatternEntry(
      exportlayers.LayerExporter.SUGGESTED_LAYER_FILENAME_PATTERNS,
      minimum_width_chars=self._FILENAME_PATTERN_ENTRY_MIN_WIDTH_CHARS,
      maximum_width_chars=self._FILENAME_PATTERN_ENTRY_MAX_WIDTH_CHARS,
      default_item=self._settings['main/layer_filename_pattern'].default_value)
    
    self._label_message = gtk.Label()
    self._label_message.set_alignment(0.0, 0.5)
    self._label_message.set_ellipsize(pango.ELLIPSIZE_MIDDLE)
    
    self._show_more_settings_button = gtk.CheckButton()
    self._show_more_settings_button.set_use_underline(True)
    self._show_more_settings_button.set_label(_("Show _More Settings"))
    
    self._vpaned_settings = gtk.VPaned()
    
    self._settings.initialize_gui({
      'file_extension': [pgsetting.SettingGuiTypes.extended_entry, self._file_extension_entry],
      'dialog_position': [pgsetting.SettingGuiTypes.window_position, self._dialog],
      'dialog_size': [pgsetting.SettingGuiTypes.window_size, self._dialog],
      'show_more_settings': [pgsetting.SettingGuiTypes.checkbox, self._show_more_settings_button],
      'chooser_and_previews_hpane_position': [
        pgsetting.SettingGuiTypes.paned_position, self._hpaned_chooser_and_previews],
      'previews_vpane_position': [
        pgsetting.SettingGuiTypes.paned_position, self._vpaned_previews],
      'settings_vpane_position': [
        pgsetting.SettingGuiTypes.paned_position, self._vpaned_settings],
      'layer_filename_pattern': [pgsetting.SettingGuiTypes.extended_entry, self._filename_pattern_entry]
    })
    
    self._current_directory_setting.set_gui(pgsetting.SettingGuiTypes.folder_chooser, self._folder_chooser)
    
    self._hbox_export_name_labels = gtk.HBox(homogeneous=False)
    self._hbox_export_name_labels.pack_start(self._file_extension_label, expand=False, fill=False)
    self._hbox_export_name_labels.pack_start(self._save_as_label, expand=False, fill=False)
    
    self._hbox_export_name_entries = gtk.HBox(homogeneous=False)
    self._hbox_export_name_entries.set_spacing(self._HBOX_EXPORT_NAME_ENTRIES_SPACING)
    self._hbox_export_name_entries.pack_start(self._filename_pattern_entry, expand=False, fill=False)
    self._hbox_export_name_entries.pack_start(self._dot_label, expand=False, fill=False)
    self._hbox_export_name_entries.pack_start(self._file_extension_entry, expand=False, fill=False)
    
    self._hbox_export_name = gtk.HBox(homogeneous=False)
    self._hbox_export_name.set_spacing(self._HBOX_EXPORT_LABELS_NAME_SPACING)
    self._hbox_export_name.pack_start(self._hbox_export_name_labels, expand=False, fill=False)
    self._hbox_export_name.pack_start(self._hbox_export_name_entries, expand=False, fill=False)
    
    self._hbox_export_name_and_message = gtk.HBox(homogeneous=False)
    self._hbox_export_name_and_message.set_spacing(self._HBOX_HORIZONTAL_SPACING)
    self._hbox_export_name_and_message.pack_start(self._hbox_export_name, expand=False, fill=False)
    self._hbox_export_name_and_message.pack_start(self._label_message, expand=True, fill=True)
    
    self._hbox_settings_checkbuttons = gtk.HBox(homogeneous=False)
    self._hbox_settings_checkbuttons.pack_start(self._settings['main/layer_groups_as_folders'].gui.element)
    self._hbox_settings_checkbuttons.pack_start(self._settings['main/use_image_size'].gui.element)
    self._hbox_settings_checkbuttons.pack_start(self._settings['main/only_visible_layers'].gui.element)
    
    self._vbox_more_settings_builtin = gtk.VBox(homogeneous=False)
    self._vbox_more_settings_builtin.set_spacing(self._MORE_SETTINGS_VERTICAL_SPACING)
    self._vbox_more_settings_builtin.pack_start(
      self._settings['main/process_tagged_layers'].gui.element, expand=False, fill=False)
    self._vbox_more_settings_builtin.pack_start(
      self._settings['main/export_only_selected_layers'].gui.element, expand=False, fill=False)
    
    self._scrolled_window_more_settings_builtin = gtk.ScrolledWindow()
    self._scrolled_window_more_settings_builtin.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    self._scrolled_window_more_settings_builtin.add_with_viewport(self._vbox_more_settings_builtin)
    self._scrolled_window_more_settings_builtin.get_child().set_shadow_type(gtk.SHADOW_NONE)
    
    self._box_more_operations = gui_operations.OperationsBox(
      label_add_text=_("Add _Operations..."), spacing=self._MORE_SETTINGS_OPERATIONS_SPACING,
      settings=list(self._settings['main/more_operations'].iterate_all()),
      displayed_settings_names=self._settings['gui/displayed_builtin_operations'].value)
    
    self._box_more_filters = gui_operations.OperationsBox(
      label_add_text=_("Add _Filters..."), spacing=self._MORE_SETTINGS_OPERATIONS_SPACING,
      settings=list(self._settings['main/more_filters'].iterate_all()),
      displayed_settings_names=self._settings['gui/displayed_builtin_filters'].value)
    
    self._hbox_more_settings = gtk.HBox(homogeneous=True)
    self._hbox_more_settings.set_spacing(self._MORE_SETTINGS_HORIZONTAL_SPACING)
    self._hbox_more_settings.pack_start(self._scrolled_window_more_settings_builtin, expand=True, fill=True)
    self._hbox_more_settings.pack_start(self._box_more_operations.widget, expand=True, fill=True)
    self._hbox_more_settings.pack_start(self._box_more_filters.widget, expand=True, fill=True)
    
    self._vbox_basic_settings = gtk.VBox()
    self._vbox_basic_settings.set_spacing(self._DIALOG_VBOX_SPACING)
    self._vbox_basic_settings.pack_start(self._hpaned_chooser_and_previews)
    self._vbox_basic_settings.pack_start(self._hbox_export_name_and_message, expand=False, fill=False)
    self._vbox_basic_settings.pack_start(self._hbox_settings_checkbuttons, expand=False, fill=False)
    
    self._vpaned_settings.pack1(self._vbox_basic_settings, resize=True, shrink=False)
    self._vpaned_settings.pack2(self._hbox_more_settings, resize=False, shrink=True)
    
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
      self._dialog_buttons.pack_end(button, expand=False, fill=False)
    
    self._dialog_buttons.pack_end(self._stop_button, expand=False, fill=False)
    self._dialog_buttons.pack_start(self._save_settings_button, expand=False, fill=False)
    self._dialog_buttons.pack_start(self._reset_settings_button, expand=False, fill=False)
    self._dialog_buttons.set_child_secondary(self._save_settings_button, True)
    self._dialog_buttons.set_child_secondary(self._reset_settings_button, True)
    
    self._action_area = gtk.HBox(homogeneous=False)
    self._action_area.set_spacing(self._HBOX_HORIZONTAL_SPACING)
    self._action_area.pack_start(self._show_more_settings_button, expand=False, fill=False)
    self._action_area.pack_start(self._dialog_buttons, expand=True, fill=True)
    
    self._dialog.vbox.set_spacing(self._DIALOG_VBOX_SPACING)
    self._dialog.vbox.pack_start(self._vpaned_settings, expand=True, fill=True)
    self._dialog.vbox.pack_start(
      self._action_area, expand=False, fill=False, padding=self._DIALOG_ACTION_AREA_PADDING)
    self._dialog.vbox.pack_end(self._vbox_progress_bars, expand=False, fill=False)
    
    self._export_button.connect("clicked", self._on_export_button_clicked)
    self._cancel_button.connect("clicked", self._on_cancel_button_clicked)
    self._stop_button.connect("clicked", self._stop)
    self._dialog.connect("key-press-event", self._on_dialog_key_press)
    self._dialog.connect("delete-event", self._on_dialog_delete_event)
    
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
    self._hpaned_chooser_and_previews.connect("notify::position", self._on_hpaned_position_changed)
    self._vpaned_previews.connect("notify::position", self._on_vpaned_position_changed)
    
    self._connect_setting_changes_to_previews()
    self._connect_setting_changes_to_operations_boxes()
    
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
      return False
    else:
      return True
  
  def _on_text_entry_changed(self, widget, setting, name_preview_lock_update_key=None):
    try:
      setting.gui.update_setting_value()
    except pgsetting.SettingValueError as e:
      pgutils.timeout_add_strict(
        self._DELAY_NAME_PREVIEW_UPDATE_TEXT_ENTRIES_MILLISECONDS,
        self._export_name_preview.set_sensitive, False)
      self._display_message_label(e.message, message_type=gtk.MESSAGE_ERROR, setting=setting)
      self._export_name_preview.lock_update(True, name_preview_lock_update_key)
    else:
      self._export_name_preview.lock_update(False, name_preview_lock_update_key)
      if self._message_setting == setting:
        self._display_message_label(None)
      
      pgutils.timeout_add_strict(
        self._DELAY_NAME_PREVIEW_UPDATE_TEXT_ENTRIES_MILLISECONDS, self._export_name_preview.update,
        should_enable_sensitive=True)
  
  def _on_show_more_settings_button_toggled(self, widget):
    self._show_hide_more_settings()
  
  def _show_hide_more_settings(self):
    if self._show_more_settings_button.get_active():
      self._hbox_more_settings.show()
      
      self._file_extension_label.hide()
      self._save_as_label.show()
      self._dot_label.show()
      self._filename_pattern_entry.show()
      
      self._frame_previews.show()
      self._export_name_preview.widget.show()
      self._export_image_preview.widget.show()
    else:
      self._hbox_more_settings.hide()
      
      self._frame_previews.hide()
      self._export_name_preview.widget.hide()
      self._export_image_preview.widget.hide()
      
      self._file_extension_label.show()
      self._save_as_label.hide()
      self._dot_label.hide()
      self._filename_pattern_entry.hide()
  
  def _on_dialog_is_active_changed(self, widget, property_spec):
    if not pdb.gimp_image_is_valid(self._image):
      gtk.main_quit()
      return
    
    if self._initial_layer_tree is not None:
      self._initial_layer_tree = None
      return
    
    if self._dialog.is_active() and not self._is_exporting:
      self._export_name_preview.update(reset_items=True)
      self._export_image_preview.update()
  
  def _connect_setting_changes_to_previews(self):
    def _on_setting_changed(setting):
      pgutils.timeout_add_strict(
        self._DELAY_PREVIEWS_SETTINGS_UPDATE_MILLISECONDS, self._export_name_preview.update)
      pgutils.timeout_add_strict(
        self._DELAY_PREVIEWS_SETTINGS_UPDATE_MILLISECONDS, self._export_image_preview.update)
    
    for setting in self._settings['main'].iterate_all():
      if setting.name not in [
          'file_extension', 'output_directory', 'overwrite_mode', 'layer_filename_pattern',
          'export_only_selected_layers', 'selected_layers', 'selected_layers_persistent']:
        setting.connect_event('value-changed', _on_setting_changed)
    
    event_id = self._settings['main/export_only_selected_layers'].connect_event(
      'value-changed', _on_setting_changed)
    self._export_name_preview.temporarily_disable_setting_events_on_update(
      {'export_only_selected_layers': [event_id]})
    self._export_image_preview.temporarily_disable_setting_events_on_update(
      {'export_only_selected_layers': [event_id]})
    
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
  
  def _connect_setting_changes_to_operations_boxes(self):
    self._settings['gui/displayed_builtin_operations'].connect_event(
      'after-reset', lambda setting: self._box_more_operations.clear())
    self._settings['gui/displayed_builtin_filters'].connect_event(
      'after-reset', lambda setting: self._box_more_filters.clear())
  
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
  
  def _on_hpaned_position_changed(self, widget, property_spec):
    current_position = self._hpaned_chooser_and_previews.get_position()
    max_position = self._hpaned_chooser_and_previews.get_property("max-position")
    
    if current_position == max_position and self._hpaned_previous_position != max_position:
      self._disable_preview_on_paned_drag(
        self._export_name_preview, self._settings['gui/export_name_preview_enabled'], "previews_enabled")
      self._disable_preview_on_paned_drag(
        self._export_image_preview, self._settings['gui/export_image_preview_enabled'],
        "previews_enabled")
    elif current_position != max_position and self._hpaned_previous_position == max_position:
      self._enable_preview_on_paned_drag(
        self._export_name_preview, self._settings['gui/export_name_preview_enabled'], "previews_enabled")
      self._enable_preview_on_paned_drag(
        self._export_image_preview, self._settings['gui/export_image_preview_enabled'], "previews_enabled")
    elif current_position != self._hpaned_previous_position:
      if self._export_image_preview.is_larger_than_image():
        pgutils.timeout_add_strict(
          self._DELAY_PREVIEWS_PANE_DRAG_UPDATE_MILLISECONDS, self._export_image_preview.update)
      else:
        pgutils.timeout_remove_strict(self._export_image_preview.update)
        self._export_image_preview.resize()
    
    self._hpaned_previous_position = current_position
  
  def _on_vpaned_position_changed(self, widget, property_spec):
    current_position = self._vpaned_previews.get_position()
    max_position = self._vpaned_previews.get_property("max-position")
    min_position = self._vpaned_previews.get_property("min-position")
    
    if current_position == max_position and self._vpaned_previous_position != max_position:
      self._disable_preview_on_paned_drag(
        self._export_image_preview, self._settings['gui/export_image_preview_enabled'],
        "vpaned_preview_enabled")
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
    elif current_position != self._vpaned_previous_position:
      if self._export_image_preview.is_larger_than_image():
        pgutils.timeout_add_strict(
          self._DELAY_PREVIEWS_PANE_DRAG_UPDATE_MILLISECONDS, self._export_image_preview.update)
      else:
        pgutils.timeout_remove_strict(self._export_image_preview.update)
        self._export_image_preview.resize()
    
    self._vpaned_previous_position = current_position
  
  def _enable_preview_on_paned_drag(self, preview, preview_enabled_setting, update_lock_key):
    preview.lock_update(False, update_lock_key)
    # In case the image preview gets resized, the update would be canceled, hence update always.
    gobject.timeout_add(self._DELAY_PREVIEWS_PANE_DRAG_UPDATE_MILLISECONDS, preview.update, True)
    preview_enabled_setting.set_value(True)
  
  def _disable_preview_on_paned_drag(self, preview, preview_enabled_setting, update_lock_key):
    preview.lock_update(True, update_lock_key)
    preview.set_sensitive(False)
    preview_enabled_setting.set_value(False)
  
  def _on_name_preview_selection_changed(self):
    layer_elem_from_cursor = self._export_name_preview.get_layer_elem_from_cursor()
    if layer_elem_from_cursor is not None:
      if (self._export_image_preview.layer_elem is None
          or layer_elem_from_cursor.item.ID != self._export_image_preview.layer_elem.item.ID):
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
    save_successful = self._save_settings()
    if save_successful:
      self._display_message_label(_("Settings successfully saved."), message_type=gtk.MESSAGE_INFO)
  
  def _on_reset_settings_clicked(self, widget):
    response_id, reset_operations = display_reset_prompt(
      parent=self._dialog, more_settings_shown=self._settings['gui/show_more_settings'].value)
    
    if not reset_operations:
      self._settings.set_ignore_tags({
        'gui/displayed_builtin_operations': ['reset'],
        'gui/displayed_builtin_filters': ['reset'],
      })
    
    if response_id == gtk.RESPONSE_YES:
      self._reset_settings()
      self._save_settings()
      self._display_message_label(_("Settings reset."), message_type=gtk.MESSAGE_INFO)
    
    if not reset_operations:
      self._settings.unset_ignore_tags({
        'gui/displayed_builtin_operations': ['reset'],
        'gui/displayed_builtin_filters': ['reset'],
      })
  
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
  def _on_export_button_clicked(self, widget):
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
      display_export_failure_message(e, parent=self._dialog)
      should_quit = False
    except Exception as e:
      if pdb.gimp_image_is_valid(self._image):
        raise
      else:
        display_export_failure_invalid_image_message(traceback.format_exc(), parent=self._dialog)
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
  
  def _on_dialog_delete_event(self, widget, event):
    gtk.main_quit()
  
  def _on_cancel_button_clicked(self, widget):
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
        pgutils.timeout_add_strict(
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
    self._buttonbox.pack_start(self._stop_button, expand=False, fill=False)
    
    self._hbox_action_area = gtk.HBox(homogeneous=False)
    self._hbox_action_area.set_spacing(self._HBOX_HORIZONTAL_SPACING)
    self._hbox_action_area.pack_start(self._vbox_progress_bars, expand=True, fill=True)
    self._hbox_action_area.pack_end(self._buttonbox, expand=False, fill=False)
    
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
      display_export_failure_message(e, parent=self._dialog)
    except Exception as e:
      if pdb.gimp_image_is_valid(self._image):
        raise
      else:
        display_export_failure_invalid_image_message(traceback.format_exc(), parent=self._dialog)
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
