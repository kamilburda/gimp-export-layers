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
This module defines the GUI for the plug-in.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import contextlib
import functools
import os
import traceback

try:
  import webbrowser
except ImportError:
  _webbrowser_module_found = False
else:
  _webbrowser_module_found = True

import pygtk
pygtk.require("2.0")
import gtk
import gobject
import pango

import gimp
from gimp import pdb
import gimpenums
import gimpui

from export_layers import pygimplib
from export_layers.pygimplib import pgconstants
from export_layers.pygimplib import pggui
from export_layers.pygimplib import pggui_entries
from export_layers.pygimplib import pginvocation
from export_layers.pygimplib import pgoverwrite
from export_layers.pygimplib import pgpdb
from export_layers.pygimplib import pgsetting
from export_layers.pygimplib import pgsettingpersistor

from .. import exportlayers
from .. import settings_plugin
from . import gui_operations
from . import gui_preview_image
from . import gui_preview_name
from . import gui_previews_controller
from . import gui_progress
from . import settings_gui

#===============================================================================


def display_message(
      message, message_type, parent=None, buttons=gtk.BUTTONS_OK,
      message_in_text_view=False, button_response_id_to_focus=None):
  return pggui.display_message(
    message, message_type, title=pygimplib.config.PLUGIN_TITLE, parent=parent,
    buttons=buttons, message_in_text_view=message_in_text_view,
    button_response_id_to_focus=button_response_id_to_focus)


def display_export_failure_message(exception, parent=None):
  error_message = _(
    "Sorry, but the export was unsuccessful. "
    "You can try exporting again if you fix the issue described below.")
  error_message += "\n" + str(exception)
  
  display_message(
    error_message, message_type=gtk.MESSAGE_WARNING, parent=parent,
    message_in_text_view=True)


def display_export_failure_invalid_image_message(details, parent=None):
  pggui.display_error_message(
    title=pygimplib.config.PLUGIN_TITLE,
    app_name=pygimplib.config.PLUGIN_TITLE,
    parent=parent,
    message_type=gtk.MESSAGE_WARNING,
    message_markup=_(
      "Sorry, but the export was unsuccessful. "
      "Do not close the image when exporting, "
      "keep it open until the export finishes successfully."),
    message_secondary_markup=_(
      "If you believe this is a different error, "
      "you can help fix it by sending a report with the text "
      "in the details to one of the sites below."),
    details=details,
    display_details_initially=False,
    report_uri_list=pygimplib.config.BUG_REPORT_URL_LIST,
    report_description="",
    focus_on_button=True)


def display_reset_prompt(parent=None, more_settings_shown=False):
  dialog = gtk.MessageDialog(
    parent=parent, type=gtk.MESSAGE_WARNING,
    flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
    buttons=gtk.BUTTONS_YES_NO)
  dialog.set_transient_for(parent)
  dialog.set_title(pygimplib.config.PLUGIN_TITLE)
  
  dialog.set_markup(_("Are you sure you want to reset settings?"))
  
  if more_settings_shown:
    checkbutton_reset_operations = gtk.CheckButton(
      label=_("Remove operations and constraints"), use_underline=False)
    dialog.vbox.pack_start(checkbutton_reset_operations, expand=False, fill=False)
  
  dialog.set_focus(dialog.get_widget_for_response(gtk.RESPONSE_NO))
  
  dialog.show_all()
  response_id = dialog.run()
  dialog.destroy()
  
  reset_operations = (
    checkbutton_reset_operations.get_active() if more_settings_shown else False)
  
  return response_id, reset_operations


#===============================================================================


@contextlib.contextmanager
def handle_gui_in_export(run_mode, image, layer, output_filepath, window):
  should_manipulate_window = run_mode == gimpenums.RUN_INTERACTIVE
  
  if should_manipulate_window:
    window_position = window.get_position()
    window.hide()
  while gtk.events_pending():
    gtk.main_iteration()
  
  try:
    yield
  finally:
    if should_manipulate_window:
      window.move(*window_position)
      window.show()
    while gtk.events_pending():
      gtk.main_iteration()


def stop_export(layer_exporter):
  if layer_exporter is not None:
    layer_exporter.stop()
    return True
  else:
    return False


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
      self._settings["main"].apply_gui_values_to_settings()
      self._settings["gui"].apply_gui_values_to_settings()
      
      self._settings["gui_session/current_directory"].gui.update_setting_value()
      
      self._settings["main/output_directory"].set_value(
        self._settings["gui_session/current_directory"].value)
      
      self._settings["gui_session/export_name_preview_layers_collapsed_state"].value[
        self._image.ID] = self._export_name_preview.collapsed_items
      self._settings["main/selected_layers"].value[
        self._image.ID] = self._export_name_preview.selected_items
      self._settings["gui_session/export_image_preview_displayed_layers"].value[
        self._image.ID] = (
          self._export_image_preview.layer_elem.item.ID
          if self._export_image_preview.layer_elem is not None else None)
      
      self._settings["gui/displayed_builtin_operations"].set_value(
        self._box_operations.displayed_settings_names)
      self._settings["gui/displayed_builtin_constraints"].set_value(
        self._box_constraints.displayed_settings_names)
    except pgsetting.SettingValueError as e:
      self._display_message_label(str(e), gtk.MESSAGE_ERROR, e.setting)
      return
    
    func(self, *args, **kwargs)
  
  return func_wrapper


#===============================================================================


def _update_directory(setting, current_image, current_image_dirpath):
  """
  Set the directory path to the setting according to the priority list below:
  
  1. `current_image_dirpath` if not None
  2. `current_image` - import path of the current image if not None
  
  If update was performed, return True, otherwise return False.
  """
  
  if current_image_dirpath is not None:
    if isinstance(current_image_dirpath, bytes):
      current_image_dirpath = current_image_dirpath.decode(
        pgconstants.GIMP_CHARACTER_ENCODING)
    
    setting.set_value(current_image_dirpath)
    return True
  
  if current_image.filename is not None:
    setting.set_value(
      os.path.dirname(
        current_image.filename.decode(pgconstants.GIMP_CHARACTER_ENCODING)))
    return True
  
  return False


def _setup_image_ids_and_directories_and_initial_directory(
      settings, current_directory_setting, current_image):
  """
  Set up the initial directory path for the current image according to the
  following priority list:
  
    1. Last export directory path of the current image
    2. Import directory path of the current image
    3. Last export directory path of any image (i.e. the current value of
       "main/output_directory")
    4. The default directory path (default value) for "main/output_directory"
  
  Notes:
  
    Directory 3. is set upon loading "main/output_directory" from a persistent
    source.
    Directory 4. is set upon the instantiation of "main/output_directory".
  """
  
  settings["gui_session/image_ids_and_directories"].update_image_ids_and_dirpaths()
  
  update_performed = _update_directory(
    current_directory_setting, current_image,
    settings["gui_session/image_ids_and_directories"].value[current_image.ID])
  
  if not update_performed:
    current_directory_setting.set_value(settings["main/output_directory"].value)


def _setup_output_directory_changed(settings, current_image):
  def on_output_directory_changed(
        output_directory, image_ids_and_directories, current_image_id):
    image_ids_and_directories.update_dirpath(current_image_id, output_directory.value)
  
  settings["main/output_directory"].connect_event("value-changed",
    on_output_directory_changed, settings["gui_session/image_ids_and_directories"],
    current_image.ID)


def _add_gui_settings(settings):
  gui_settings, session_only_gui_settings, persistent_only_gui_settings = (
    settings_gui.create_gui_settings())
  settings.add(
    [gui_settings, session_only_gui_settings, persistent_only_gui_settings])


#===============================================================================


class ExportLayersGui(object):
  
  _HBOX_EXPORT_LABELS_NAME_SPACING = 15
  _HBOX_EXPORT_NAME_ENTRIES_SPACING = 3
  _HBOX_EXPORT_NAME_AND_MESSAGE_HORIZONTAL_SPACING = 8
  _HBOX_EXPORT_NAME_AND_MESSAGE_BORDER_WIDTH = 2
  
  _MORE_SETTINGS_HORIZONTAL_SPACING = 12
  _MORE_SETTINGS_BORDER_WIDTH = 2
  _MORE_SETTINGS_VERTICAL_SPACING = 6
  _MORE_SETTINGS_OPERATIONS_SPACING = 4
  
  _DIALOG_SIZE = (900, 610)
  _DIALOG_BORDER_WIDTH = 8
  _DIALOG_VBOX_SPACING = 5
  _DIALOG_ACTION_AREA_BORDER_WIDTH = 5
  _DIALOG_BUTTONS_HORIZONTAL_SPACING = 6
  
  _FILE_EXTENSION_ENTRY_MIN_WIDTH_CHARS = 4
  _FILE_EXTENSION_ENTRY_MAX_WIDTH_CHARS = 15
  _FILENAME_PATTERN_ENTRY_MIN_WIDTH_CHARS = 12
  _FILENAME_PATTERN_ENTRY_MAX_WIDTH_CHARS = 50
  
  _DELAY_NAME_PREVIEW_UPDATE_TEXT_ENTRIES_MILLISECONDS = 100
  _DELAY_CLEAR_LABEL_MESSAGE_MILLISECONDS = 10000
  
  def __init__(self, initial_layer_tree, settings, run_gui_func=None):
    self._initial_layer_tree = initial_layer_tree
    self._settings = settings
    
    self._image = self._initial_layer_tree.image
    self._layer_exporter = None
    self._is_exporting = False
    
    self._layer_exporter_for_previews = exportlayers.LayerExporter(
      gimpenums.RUN_NONINTERACTIVE, self._image, self._settings["main"],
      overwrite_chooser=pgoverwrite.NoninteractiveOverwriteChooser(
        self._settings["main/overwrite_mode"].items["replace"]),
      layer_tree=self._initial_layer_tree)
    
    self._init_settings()
    
    if gimp.version[:2] == (2, 8):
      pgpdb.suppress_gimp_progress()
    
    self._init_gui()
    
    pggui.set_gui_excepthook_parent(self._dialog)
    
    if not run_gui_func:
      gtk.main()
    else:
      run_gui_func(self, self._dialog, self._settings)
  
  def _init_settings(self):
    _add_gui_settings(self._settings)
    
    settings_plugin.setup_image_ids_and_filepaths_settings(
      self._settings["gui_session/export_name_preview_layers_collapsed_state"],
      self._settings["gui_persistent/export_name_preview_layers_collapsed_state_persistent"],
      settings_plugin.convert_set_of_layer_ids_to_names,
      [self._layer_exporter_for_previews.layer_tree],
      settings_plugin.convert_set_of_layer_names_to_ids,
      [self._layer_exporter_for_previews.layer_tree])
    
    settings_plugin.setup_image_ids_and_filepaths_settings(
      self._settings["gui_session/export_image_preview_displayed_layers"],
      self._settings["gui_persistent/export_image_preview_displayed_layers_persistent"],
      settings_plugin.convert_layer_id_to_name,
      [self._layer_exporter_for_previews.layer_tree],
      settings_plugin.convert_layer_name_to_id,
      [self._layer_exporter_for_previews.layer_tree])
    
    status, status_message = self._settings.load()
    if status == pgsettingpersistor.SettingPersistor.READ_FAIL:
      display_message(status_message, gtk.MESSAGE_WARNING)
    
    # Needs to be string to avoid strict directory validation
    self._settings["gui_session"].add([pgsetting.StringSetting(
      "current_directory", self._settings["main/output_directory"].default_value)])
    self._message_setting = None
    
    _setup_image_ids_and_directories_and_initial_directory(
      self._settings, self._settings["gui_session/current_directory"], self._image)
    _setup_output_directory_changed(self._settings, self._image)
  
  def _init_gui(self):
    self._dialog = gimpui.Dialog(
      title=pygimplib.config.PLUGIN_TITLE, role=pygimplib.config.PLUGIN_NAME)
    self._dialog.set_transient()
    self._dialog.set_default_size(*self._DIALOG_SIZE)
    self._dialog.set_border_width(self._DIALOG_BORDER_WIDTH)
    
    self._folder_chooser_label = gtk.Label()
    self._folder_chooser_label.set_markup("<b>" + _("Save in folder:") + "</b>")
    self._folder_chooser_label.set_alignment(0.0, 0.5)
    
    self._folder_chooser = gtk.FileChooserWidget(
      action=gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER)
    
    self._init_gui_previews()
    
    self._vbox_folder_chooser = gtk.VBox(homogeneous=False)
    self._vbox_folder_chooser.set_spacing(self._DIALOG_VBOX_SPACING * 2)
    self._vbox_folder_chooser.pack_start(
      self._folder_chooser_label, expand=False, fill=False)
    self._vbox_folder_chooser.pack_start(self._folder_chooser)
    
    self._vpaned_previews = gtk.VPaned()
    self._vpaned_previews.pack1(
      self._export_name_preview.widget, resize=True, shrink=True)
    self._vpaned_previews.pack2(
      self._export_image_preview.widget, resize=True, shrink=True)
    
    self._frame_previews = gtk.Frame()
    self._frame_previews.set_shadow_type(gtk.SHADOW_ETCHED_OUT)
    self._frame_previews.add(self._vpaned_previews)
    
    self._hpaned_chooser_and_previews = gtk.HPaned()
    self._hpaned_chooser_and_previews.pack1(
      self._vbox_folder_chooser, resize=True, shrink=False)
    self._hpaned_chooser_and_previews.pack2(
      self._frame_previews, resize=True, shrink=True)
    
    self._file_extension_label = gtk.Label()
    self._file_extension_label.set_markup(
      "<b>{0}:</b>".format(
        gobject.markup_escape_text(self._settings["main/file_extension"].display_name)))
    self._file_extension_label.set_alignment(0.0, 0.5)
    
    self._file_extension_entry = pggui_entries.FileExtensionEntry(
      minimum_width_chars=self._FILE_EXTENSION_ENTRY_MIN_WIDTH_CHARS,
      maximum_width_chars=self._FILE_EXTENSION_ENTRY_MAX_WIDTH_CHARS)
    
    self._save_as_label = gtk.Label()
    self._save_as_label.set_markup("<b>{0}:</b>".format(_("Save as")))
    self._save_as_label.set_alignment(0.0, 0.5)
    
    self._dot_label = gtk.Label(".")
    self._dot_label.set_alignment(0.0, 1.0)
    
    self._filename_pattern_entry = pggui_entries.FilenamePatternEntry(
      exportlayers.LayerNameRenamer.LAYER_NAME_PATTERN_FIELDS,
      minimum_width_chars=self._FILENAME_PATTERN_ENTRY_MIN_WIDTH_CHARS,
      maximum_width_chars=self._FILENAME_PATTERN_ENTRY_MAX_WIDTH_CHARS,
      default_item=self._settings["main/layer_filename_pattern"].default_value)
    
    self._label_message = gtk.Label()
    self._label_message.set_alignment(0.0, 0.5)
    self._label_message.set_ellipsize(pango.ELLIPSIZE_MIDDLE)
    
    self._menu_item_show_more_settings = gtk.CheckMenuItem(_("Show More Settings"))
    
    self._vpaned_settings = gtk.VPaned()
    
    self._settings.initialize_gui({
      "file_extension": [
        pgsetting.SettingGuiTypes.extended_entry, self._file_extension_entry],
      "dialog_position": [
        pgsetting.SettingGuiTypes.window_position, self._dialog],
      "dialog_size": [
        pgsetting.SettingGuiTypes.window_size, self._dialog],
      "show_more_settings": [
        pgsetting.SettingGuiTypes.check_menu_item, self._menu_item_show_more_settings],
      "paned_outside_previews_position": [
        pgsetting.SettingGuiTypes.paned_position, self._hpaned_chooser_and_previews],
      "paned_between_previews_position": [
        pgsetting.SettingGuiTypes.paned_position, self._vpaned_previews],
      "settings_vpane_position": [
        pgsetting.SettingGuiTypes.paned_position, self._vpaned_settings],
      "layer_filename_pattern": [
        pgsetting.SettingGuiTypes.extended_entry, self._filename_pattern_entry]
    })
    
    self._settings["gui_session/current_directory"].set_gui(
      pgsetting.SettingGuiTypes.folder_chooser, self._folder_chooser)
    
    self._hbox_export_name_labels = gtk.HBox(homogeneous=False)
    self._hbox_export_name_labels.pack_start(
      self._file_extension_label, expand=False, fill=False)
    self._hbox_export_name_labels.pack_start(
      self._save_as_label, expand=False, fill=False)
    
    self._hbox_export_name_entries = gtk.HBox(homogeneous=False)
    self._hbox_export_name_entries.set_spacing(self._HBOX_EXPORT_NAME_ENTRIES_SPACING)
    self._hbox_export_name_entries.pack_start(
      self._filename_pattern_entry, expand=False, fill=False)
    self._hbox_export_name_entries.pack_start(
      self._dot_label, expand=False, fill=False)
    self._hbox_export_name_entries.pack_start(
      self._file_extension_entry, expand=False, fill=False)
    
    self._hbox_export_name = gtk.HBox(homogeneous=False)
    self._hbox_export_name.set_spacing(self._HBOX_EXPORT_LABELS_NAME_SPACING)
    self._hbox_export_name.pack_start(
      self._hbox_export_name_labels, expand=False, fill=False)
    self._hbox_export_name.pack_start(
      self._hbox_export_name_entries, expand=False, fill=False)
    
    self._hbox_export_name_and_message = gtk.HBox(homogeneous=False)
    self._hbox_export_name_and_message.set_spacing(
      self._HBOX_EXPORT_NAME_AND_MESSAGE_HORIZONTAL_SPACING)
    self._hbox_export_name_and_message.set_border_width(
      self._HBOX_EXPORT_NAME_AND_MESSAGE_BORDER_WIDTH)
    self._hbox_export_name_and_message.pack_start(
      self._hbox_export_name, expand=False, fill=False)
    self._hbox_export_name_and_message.pack_start(
      self._label_message, expand=True, fill=True)
    
    self._hbox_basic_settings = gtk.HBox(homogeneous=False)
    self._hbox_basic_settings.pack_start(
      self._settings["main/layer_groups_as_folders"].gui.element)
    self._hbox_basic_settings.pack_start(
      self._settings["main/use_image_size"].gui.element)
    self._hbox_basic_settings.pack_start(
      self._settings["main/only_visible_layers"].gui.element)
    
    self._vbox_basic_settings = gtk.VBox(homogeneous=False)
    self._vbox_basic_settings.set_spacing(self._MORE_SETTINGS_VERTICAL_SPACING)
    
    self._scrolled_window_basic_settings = gtk.ScrolledWindow()
    self._scrolled_window_basic_settings.set_policy(
      gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    self._scrolled_window_basic_settings.add_with_viewport(self._vbox_basic_settings)
    self._scrolled_window_basic_settings.get_child().set_shadow_type(gtk.SHADOW_NONE)
    
    self._init_gui_operation_boxes()
    
    self._hbox_more_settings = gtk.HBox(homogeneous=True)
    self._hbox_more_settings.set_spacing(self._MORE_SETTINGS_HORIZONTAL_SPACING)
    self._hbox_more_settings.set_border_width(self._MORE_SETTINGS_BORDER_WIDTH)
    self._hbox_more_settings.pack_start(
      self._scrolled_window_basic_settings, expand=True, fill=True)
    self._hbox_more_settings.pack_start(
      self._box_operations.widget, expand=True, fill=True)
    self._hbox_more_settings.pack_start(
      self._box_constraints.widget, expand=True, fill=True)
    
    self._vbox_settings = gtk.VBox()
    self._vbox_settings.set_spacing(self._DIALOG_VBOX_SPACING)
    self._vbox_settings.pack_start(self._hpaned_chooser_and_previews)
    self._vbox_settings.pack_start(
      self._hbox_export_name_and_message, expand=False, fill=False)
    self._vbox_settings.pack_start(
      self._hbox_basic_settings, expand=False, fill=False)
    
    self._vpaned_settings.pack1(self._vbox_settings, resize=True, shrink=False)
    self._vpaned_settings.pack2(self._hbox_more_settings, resize=False, shrink=True)
    
    self._button_export = self._dialog.add_button(_("_Export"), gtk.RESPONSE_OK)
    self._button_cancel = self._dialog.add_button(_("_Cancel"), gtk.RESPONSE_CANCEL)
    self._dialog.set_alternative_button_order([gtk.RESPONSE_OK, gtk.RESPONSE_CANCEL])
    
    self._button_stop = gtk.Button()
    self._button_stop.set_label(_("_Stop"))
    
    self._label_button_settings = gtk.Label(_("_Settings"))
    self._label_button_settings.set_use_underline(True)
    
    self._hbox_button_settings = gtk.HBox()
    self._hbox_button_settings.pack_start(
      self._label_button_settings, expand=True, fill=True)
    self._hbox_button_settings.pack_start(
      gtk.Arrow(gtk.ARROW_DOWN, gtk.SHADOW_IN), expand=False, fill=False)
    
    self._button_settings = gtk.Button()
    self._button_settings.add(self._hbox_button_settings)
    
    self._menu_item_save_settings = gtk.MenuItem(_("Save Settings"))
    self._menu_item_reset_settings = gtk.MenuItem(_("Reset settings"))
    
    self._menu_settings = gtk.Menu()
    self._menu_settings.append(self._menu_item_show_more_settings)
    self._menu_settings.append(self._menu_item_save_settings)
    self._menu_settings.append(self._menu_item_reset_settings)
    self._menu_settings.show_all()
    
    self._dialog.action_area.pack_end(self._button_stop, expand=False, fill=False)
    self._dialog.action_area.pack_start(self._button_settings, expand=False, fill=False)
    self._dialog.action_area.set_child_secondary(self._button_settings, True)
    
    self._progress_bar = gtk.ProgressBar()
    self._progress_bar.set_ellipsize(pango.ELLIPSIZE_MIDDLE)
    
    self._dialog.vbox.set_spacing(self._DIALOG_VBOX_SPACING)
    self._dialog.vbox.pack_start(self._vpaned_settings, expand=True, fill=True)
    self._dialog.vbox.pack_end(self._progress_bar, expand=False, fill=False)
    
    # Move the action area above the progress bar.
    self._dialog.vbox.reorder_child(self._dialog.action_area, -1)
    
    self._button_export.connect("clicked", self._on_button_export_clicked)
    self._button_cancel.connect("clicked", self._on_button_cancel_clicked)
    self._button_stop.connect("clicked", self._on_button_stop_clicked)
    self._dialog.connect("key-press-event", self._on_dialog_key_press)
    self._dialog.connect("delete-event", self._on_dialog_delete_event)
    
    if _webbrowser_module_found:
      self._button_help = gtk.Button()
      self._button_help.set_label(_("_Help"))
      self._dialog.action_area.pack_start(self._button_help, expand=False, fill=False)
      self._dialog.action_area.set_child_secondary(self._button_help, True)
      self._button_help.connect("clicked", self._on_button_help_clicked)
    
    self._button_settings.connect("clicked", self._on_button_settings_clicked)
    self._menu_item_show_more_settings.connect(
      "toggled", self._on_menu_item_show_more_settings_toggled)
    self._menu_item_save_settings.connect(
      "activate", self._on_save_settings_activate)
    self._menu_item_reset_settings.connect(
      "activate", self._on_reset_settings_activate)
    
    self._file_extension_entry.connect(
      "changed", self._on_text_entry_changed,
      self._settings["main/file_extension"], "invalid_file_extension")
    self._filename_pattern_entry.connect(
      "changed", self._on_text_entry_changed,
      self._settings["main/layer_filename_pattern"], "invalid_layer_filename_pattern")
    
    self._dialog.connect("notify::is-active", self._on_dialog_is_active_changed)
    
    self._dialog.connect(
      "notify::is-active",
      self._export_previews_controller.on_dialog_is_active_changed,
      lambda: self._is_exporting)
    self._hpaned_chooser_and_previews.connect(
      "notify::position",
      self._export_previews_controller.on_paned_outside_previews_position_changed)
    self._vpaned_previews.connect(
      "notify::position",
      self._export_previews_controller.on_paned_between_previews_position_changed)
    
    self._export_previews_controller.connect_setting_changes_to_previews()
    self._connect_setting_changes_to_operation_boxes()
    
    self._dialog.set_default_response(gtk.RESPONSE_CANCEL)
    
    self._dialog.vbox.show_all()
    self._progress_bar.hide()
    self._button_stop.hide()
    
    self._dialog.action_area.set_border_width(self._DIALOG_ACTION_AREA_BORDER_WIDTH)
    
    self._export_previews_controller.connect_visible_changed_to_previews()
    
    self._show_hide_more_settings()
    
    self._export_previews_controller.init_previews()
    
    self._dialog.set_focus(self._file_extension_entry)
    self._button_export.set_flags(gtk.CAN_DEFAULT)
    self._button_export.grab_default()
    self._filename_pattern_entry.set_activates_default(True)
    self._file_extension_entry.set_activates_default(True)
    # Place the cursor at the end of the text entry.
    self._file_extension_entry.set_position(-1)
    
    self._dialog.show()
  
  def _init_gui_previews(self):
    self._export_name_preview = gui_preview_name.ExportNamePreview(
      self._layer_exporter_for_previews,
      self._initial_layer_tree,
      self._settings["gui_session/export_name_preview_layers_collapsed_state"].value[
        self._image.ID],
      self._settings["main/selected_layers"].value[self._image.ID],
      self._settings["gui/displayed_tags"])
    
    self._export_image_preview = gui_preview_image.ExportImagePreview(
      self._layer_exporter_for_previews,
      self._settings["gui_session/export_image_preview_displayed_layers"].value[
        self._image.ID])
    
    self._export_previews_controller = gui_previews_controller.ExportPreviewsController(
      self._export_name_preview, self._export_image_preview, self._settings, self._image)
    
    self._export_name_preview.on_selection_changed = (
      self._export_previews_controller.on_name_preview_selection_changed)
    self._export_name_preview.on_after_update = (
      self._export_previews_controller.on_name_preview_after_update)
    self._export_name_preview.on_after_edit_tags = (
      self._export_previews_controller.on_name_preview_after_edit_tags)
  
  def _init_gui_operation_boxes(self):
    self._box_operations = self._create_operation_box(
      self._settings["main/operations"],
      self._settings["gui/displayed_builtin_operations"],
      _("Add _Operation..."))
    
    self._box_constraints = self._create_operation_box(
      self._settings["main/constraints"],
      self._settings["gui/displayed_builtin_constraints"],
      _("Add _Constraint..."))
  
  def _create_operation_box(
        self, setting_group_with_operations, setting_displayed_operations,
        label_add_operation):
    operation_box = gui_operations.OperationBox(
      label_add_text=label_add_operation,
      spacing=self._MORE_SETTINGS_OPERATIONS_SPACING,
      settings=setting_group_with_operations)
    
    operation_box.on_add_operation = exportlayers.add_operation
    operation_box.on_reorder_operation = exportlayers.reorder_operation
    operation_box.on_remove_operation = exportlayers.remove_operation
    
    for setting_name in setting_displayed_operations.value:
      if setting_name in setting_group_with_operations:
        operation_box.add_operation_item(setting_group_with_operations[setting_name])
    
    return operation_box
  
  def _save_settings(self):
    status, status_message = self._settings.save()
    if status == pgsettingpersistor.SettingPersistor.WRITE_FAIL:
      display_message(status_message, gtk.MESSAGE_WARNING, parent=self._dialog)
      return False
    else:
      return True
  
  def _reset_settings(self):
    self._settings.reset()
  
  @staticmethod
  def _clear_setting_sources():
    pgsettingpersistor.SettingPersistor.clear(
      [pygimplib.config.SOURCE_SESSION, pygimplib.config.SOURCE_PERSISTENT])
  
  def _on_text_entry_changed(self, widget, setting, name_preview_lock_update_key=None):
    try:
      setting.gui.update_setting_value()
    except pgsetting.SettingValueError as e:
      pginvocation.timeout_add_strict(
        self._DELAY_NAME_PREVIEW_UPDATE_TEXT_ENTRIES_MILLISECONDS,
        self._export_name_preview.set_sensitive, False)
      self._display_message_label(str(e), gtk.MESSAGE_ERROR, setting)
      self._export_name_preview.lock_update(True, name_preview_lock_update_key)
    else:
      self._export_name_preview.lock_update(False, name_preview_lock_update_key)
      if self._message_setting == setting:
        self._display_message_label(None)
      
      self._export_name_preview.add_function_at_update(
        self._export_name_preview.set_sensitive, True)
      
      pginvocation.timeout_add_strict(
        self._DELAY_NAME_PREVIEW_UPDATE_TEXT_ENTRIES_MILLISECONDS,
        self._export_name_preview.update)
  
  def _on_menu_item_show_more_settings_toggled(self, widget):
    self._show_hide_more_settings()
  
  def _show_hide_more_settings(self):
    if self._menu_item_show_more_settings.get_active():
      basic_settings_gui_elements = self._hbox_basic_settings.get_children()
      for gui_element in basic_settings_gui_elements:
        self._hbox_basic_settings.remove(gui_element)
        self._vbox_basic_settings.pack_start(gui_element, expand=False, fill=False)
      
      self._hbox_basic_settings.hide()
      self._hbox_more_settings.show()
      
      self._file_extension_label.hide()
      self._save_as_label.show()
      self._dot_label.show()
      self._filename_pattern_entry.show()
      
      self._frame_previews.show()
      self._export_name_preview.widget.show()
      self._export_image_preview.widget.show()
    else:
      basic_settings_gui_elements = self._vbox_basic_settings.get_children()
      for gui_element in basic_settings_gui_elements:
        self._vbox_basic_settings.remove(gui_element)
        self._hbox_basic_settings.pack_start(gui_element)
      
      self._hbox_basic_settings.show()
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
  
  def _connect_setting_changes_to_operation_boxes(self):
    self._settings["gui/displayed_builtin_operations"].connect_event(
      "after-reset", lambda setting: self._box_operations.clear())
    self._settings["gui/displayed_builtin_constraints"].connect_event(
      "after-reset", lambda setting: self._box_constraints.clear())
  
  def _on_dialog_key_press(self, widget, event):
    if gtk.gdk.keyval_name(event.keyval) == "Escape":
      export_stopped = stop_export(self._layer_exporter)
      return export_stopped
  
  def _on_button_settings_clicked(self, button):
    dialog_position = self._dialog.get_window().get_origin()
    button_allocation = button.get_allocation()
    self._menu_settings.popup(
      None, None,
      lambda menu: (
        button_allocation.x + dialog_position[0],
        button_allocation.y + button_allocation.height + dialog_position[1],
        True),
      0, 0)
  
  @_set_settings
  def _on_save_settings_activate(self, widget):
    save_successful = self._save_settings()
    if save_successful:
      self._display_message_label(_("Settings successfully saved."), gtk.MESSAGE_INFO)
  
  def _on_reset_settings_activate(self, widget):
    response_id, reset_operations = display_reset_prompt(
      parent=self._dialog,
      more_settings_shown=self._settings["gui/show_more_settings"].value)
    
    if not reset_operations:
      self._settings["gui/displayed_builtin_operations"].tags.add("ignore_reset")
      self._settings["gui/displayed_builtin_constraints"].tags.add("ignore_reset")
    
    if response_id == gtk.RESPONSE_YES:
      self._reset_settings()
      self._save_settings()
      
      if reset_operations:
        self._clear_setting_sources()
      
      self._display_message_label(_("Settings reset."), gtk.MESSAGE_INFO)
    
    if not reset_operations:
      self._settings["gui/displayed_builtin_operations"].tags.remove("ignore_reset")
      self._settings["gui/displayed_builtin_constraints"].tags.remove("ignore_reset")
  
  @_set_settings
  def _on_button_export_clicked(self, widget):
    self._setup_gui_before_export()
    overwrite_chooser, progress_updater = self._setup_layer_exporter()
    
    item_progress_indicator = gui_progress.ItemProgressIndicator(
      self._progress_bar, progress_updater)
    item_progress_indicator.install_progress_for_status(
      self._progress_set_value_and_show_dialog)
    
    should_quit = True
    self._is_exporting = True
    
    try:
      self._layer_exporter.export()
    except exportlayers.ExportLayersCancelError as e:
      should_quit = False
    except exportlayers.ExportLayersError as e:
      display_export_failure_message(e, parent=self._dialog)
      should_quit = False
    except Exception as e:
      if pdb.gimp_image_is_valid(self._image):
        raise
      else:
        display_export_failure_invalid_image_message(
          traceback.format_exc(), parent=self._dialog)
    else:
      self._settings["special/first_plugin_run"].set_value(False)
      self._settings["special/first_plugin_run"].save()
      
      if not self._layer_exporter.exported_layers:
        display_message(
          _("No layers were exported."), gtk.MESSAGE_INFO, parent=self._dialog)
        should_quit = False
    finally:
      item_progress_indicator.uninstall_progress_for_status()
      self._layer_exporter = None
      self._is_exporting = False
    
    if (overwrite_chooser.overwrite_mode
        in self._settings["main/overwrite_mode"].items.values()):
      self._settings["main/overwrite_mode"].set_value(overwrite_chooser.overwrite_mode)
    
    pgsettingpersistor.SettingPersistor.save(
      [self._settings["main"], self._settings["gui"], self._settings["gui_session"]],
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
  
  def _setup_layer_exporter(self):
    overwrite_chooser = pggui.GtkDialogOverwriteChooser(
      self._get_overwrite_dialog_items(),
      default_value=self._settings["main/overwrite_mode"].items["replace"],
      default_response=pgoverwrite.OverwriteModes.CANCEL,
      title=pygimplib.config.PLUGIN_TITLE,
      parent=self._dialog)
    
    progress_updater = pggui.GtkProgressUpdater(self._progress_bar)
    
    self._layer_exporter = exportlayers.LayerExporter(
      gimpenums.RUN_INTERACTIVE, self._image, self._settings["main"],
      overwrite_chooser, progress_updater,
      export_context_manager=handle_gui_in_export,
      export_context_manager_args=[self._dialog])
    
    return overwrite_chooser, progress_updater
  
  def _get_overwrite_dialog_items(self):
    return list(zip(
      self._settings["main/overwrite_mode"].items.values(),
      self._settings["main/overwrite_mode"].items_display_names.values()))
  
  def _set_gui_enabled(self, enabled):
    self._progress_bar.set_visible(not enabled)
    self._button_stop.set_visible(not enabled)
    self._button_cancel.set_visible(enabled)
    
    for child in self._dialog.vbox:
      if child not in (self._dialog.action_area, self._progress_bar):
        child.set_sensitive(enabled)
    
    self._button_settings.set_sensitive(enabled)
    
    for button in self._dialog.action_area:
      if button != self._button_stop:
        button.set_sensitive(enabled)
    
    if enabled:
      self._dialog.set_focus(self._file_extension_entry)
      self._file_extension_entry.set_position(-1)
    else:
      self._dialog.set_focus(self._button_stop)
  
  def _progress_set_value_and_show_dialog(self, fraction):
    self._progress_bar.set_fraction(fraction)
    
    # Without this workaround, the main dialog would not appear until the export
    # of the second layer.
    if not self._dialog.get_mapped():
      self._dialog.show()
    
    while gtk.events_pending():
      gtk.main_iteration()
  
  def _on_dialog_delete_event(self, widget, event):
    gtk.main_quit()
  
  def _on_button_cancel_clicked(self, widget):
    gtk.main_quit()
  
  def _on_button_stop_clicked(self, widget):
    stop_export(self._layer_exporter)
  
  def _on_button_help_clicked(self, widget):
    if os.path.isfile(pygimplib.config.LOCAL_DOCS_PATH):
      docs_url = pygimplib.config.LOCAL_DOCS_PATH
    else:
      docs_url = pygimplib.config.DOCS_URL
    
    webbrowser.open_new_tab(docs_url)
  
  def _display_message_label(self, text, message_type=gtk.MESSAGE_ERROR, setting=None):
    self._message_setting = setting
    
    if not text:
      self._label_message.set_text("")
    else:
      text = text[0].upper() + text[1:]
      if not text.endswith("."):
        text += "."
      
      if message_type == gtk.MESSAGE_ERROR:
        self._label_message.set_markup('<span foreground="red"><b>{0}</b></span>'.format(
          gobject.markup_escape_text(text)))
        
        if not (os.name == "nt" and gimp.version >= (2, 10)):
          pginvocation.timeout_remove_strict(self._display_message_label)
      else:
        self._label_message.set_markup('<span><b>{0}</b></span>'.format(
          gobject.markup_escape_text(text)))
        
        if not (os.name == "nt" and gimp.version >= (2, 10)):
          pginvocation.timeout_add_strict(
            self._DELAY_CLEAR_LABEL_MESSAGE_MILLISECONDS, self._display_message_label, None)


#===============================================================================


class ExportLayersRepeatGui(object):
  
  _HBOX_HORIZONTAL_SPACING = 8
  _DIALOG_WIDTH = 500
  
  def __init__(self, layer_tree, settings):
    self._layer_tree = layer_tree
    self._settings = settings
    
    self._image = self._layer_tree.image
    self._layer_exporter = None
    
    _add_gui_settings(self._settings)
    
    pgsettingpersistor.SettingPersistor.load(
      [self._settings], [pygimplib.config.SOURCE_SESSION])
    
    self._add_operations()
    
    self._init_gui()
    
    pggui.set_gui_excepthook_parent(self._dialog)
    
    gtk.main_iteration()
    self.show()
    self.export_layers()
  
  def _init_gui(self):
    if gimp.version >= (2, 10):
      gimpui.gimp_ui_init()
    
    self._dialog = gimpui.Dialog(title=pygimplib.config.PLUGIN_TITLE, role=None)
    self._dialog.set_transient()
    self._dialog.set_border_width(8)
    self._dialog.set_default_size(self._DIALOG_WIDTH, -1)
    
    self._button_stop = gtk.Button()
    self._button_stop.set_label(_("_Stop"))
    
    self._buttonbox = gtk.HButtonBox()
    self._buttonbox.pack_start(self._button_stop, expand=False, fill=False)
    
    self._progress_bar = gtk.ProgressBar()
    self._progress_bar.set_ellipsize(pango.ELLIPSIZE_MIDDLE)
    
    self._hbox_action_area = gtk.HBox(homogeneous=False)
    self._hbox_action_area.set_spacing(self._HBOX_HORIZONTAL_SPACING)
    self._hbox_action_area.pack_start(self._progress_bar, expand=True, fill=True)
    self._hbox_action_area.pack_end(self._buttonbox, expand=False, fill=False)
    
    self._dialog.vbox.pack_end(self._hbox_action_area, expand=False, fill=False)
    
    self._button_stop.connect("clicked", self._on_button_stop_clicked)
    self._dialog.connect("delete-event", self._on_dialog_delete_event)
  
  def _add_operations(self):
    self._add_operation_settings(
      self._settings["main/operations"],
      self._settings["gui/displayed_builtin_operations"])
    
    self._add_operation_settings(
      self._settings["main/constraints"],
      self._settings["gui/displayed_builtin_constraints"])
  
  @staticmethod
  def _add_operation_settings(
        setting_group_with_operations, setting_displayed_operations):
    for setting_name in setting_displayed_operations.value:
      if setting_name in setting_group_with_operations:
        exportlayers.add_operation(setting_group_with_operations[setting_name])
  
  def export_layers(self):
    progress_updater = pggui.GtkProgressUpdater(self._progress_bar)
    item_progress_indicator = gui_progress.ItemProgressIndicator(
      self._progress_bar, progress_updater)
    item_progress_indicator.install_progress_for_status()
    
    self._layer_exporter = exportlayers.LayerExporter(
      gimpenums.RUN_WITH_LAST_VALS, self._image, self._settings["main"],
      pgoverwrite.NoninteractiveOverwriteChooser(
        self._settings["main/overwrite_mode"].value),
      progress_updater,
      export_context_manager=handle_gui_in_export,
      export_context_manager_args=[self._dialog])
    try:
      self._layer_exporter.export(layer_tree=self._layer_tree)
    except exportlayers.ExportLayersCancelError:
      pass
    except exportlayers.ExportLayersError as e:
      display_export_failure_message(e, parent=self._dialog)
    except Exception as e:
      if pdb.gimp_image_is_valid(self._image):
        raise
      else:
        display_export_failure_invalid_image_message(
          traceback.format_exc(), parent=self._dialog)
    else:
      if not self._layer_exporter.exported_layers:
        display_message(
          _("No layers were exported."), gtk.MESSAGE_INFO, parent=self._dialog)
    finally:
      item_progress_indicator.uninstall_progress_for_status()
  
  def show(self):
    self._dialog.vbox.show_all()
    self._dialog.action_area.hide()
    self._dialog.show()
  
  def hide(self):
    self._dialog.hide()
  
  def _on_button_stop_clicked(self, widget):
    stop_export(self._layer_exporter)
  
  def _on_dialog_delete_event(self, widget, event):
    stop_export(self._layer_exporter)
