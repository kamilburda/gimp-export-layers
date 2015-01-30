#-------------------------------------------------------------------------------
#
# This file is part of Export Layers.
#
# Copyright (C) 2013, 2014 khalim19 <khalim19@gmail.com>
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
#-------------------------------------------------------------------------------

"""
This module:
* defines GUI for the plug-in
* defines GUI-specific settings
"""

#===============================================================================

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division

str = unicode

#===============================================================================

import traceback

import gobject
import pygtk
pygtk.require("2.0")
import gtk
import pango

import gimp
import gimpenums
import gimpui

from export_layers.pygimplib import pgsetting
from export_layers.pygimplib import pgsettinggroup
from export_layers.pygimplib import overwrite
from export_layers.pygimplib import pggui

from export_layers import settings_plugin
from export_layers import exportlayers
from export_layers import constants

#===============================================================================

pdb = gimp.pdb

#===============================================================================


def display_message(message, message_type, parent=None):
  pggui.display_message(
    message,
    message_type,
    title=_(constants.PLUGIN_TITLE),
    parent=parent
  )


def display_exception_message(exception_message, parent=None):
  pggui.display_exception_message(
    exception_message,
    plugin_title=_(constants.PLUGIN_TITLE),
    report_uri_list=constants.BUG_REPORT_URI_LIST,
    parent=parent
  )


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
    self._stop_button.set_label(_("Stop"))
    
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


class _ExportLayersGui(object):
  
  HBOX_HORIZONTAL_SPACING = 8
  
  ADVANCED_SETTINGS_HORIZONTAL_SPACING = 12
  ADVANCED_SETTINGS_VERTICAL_SPACING = 6
  ADVANCED_SETTINGS_LEFT_MARGIN = 15
  
  DIALOG_SIZE = (850, 660)
  DIALOG_BORDER_WIDTH = 8
  DIALOG_VBOX_SPACING = 5
  ACTION_AREA_BORDER_WIDTH = 4
  
  MESSAGE_TYPES = INFO, ERROR = (0, 1)
  
  _GUI_REFRESH_INTERVAL_MILLISECONDS = 500
  
  def __init__(self, image, main_settings, special_settings, gimpshelf_stream, config_file_stream):
    self.image = image
    self.main_settings = main_settings
    self.special_settings = special_settings
    self.gimpshelf_stream = gimpshelf_stream
    self.config_file_stream = config_file_stream
    
    self.gui_settings = settings_plugin.create_gui_settings()
    self.session_only_gui_settings = settings_plugin.create_session_only_gui_settings()
    
    status, status_message = pgsettinggroup.SettingPersistor.load([self.main_settings, self.gui_settings],
                                                                  [self.gimpshelf_stream, self.config_file_stream])
    if status == pgsettinggroup.SettingPersistor.READ_FAIL:
      display_message(status_message, gtk.MESSAGE_WARNING)
    
    pgsettinggroup.SettingPersistor.load([self.session_only_gui_settings], [self.gimpshelf_stream])
    self._setup_output_directory_and_image_ids_and_directories()
    
    self.layer_exporter = None
    
    self._init_gui()
    
    gtk.main()
  
  def _setup_output_directory_and_image_ids_and_directories(self):
    """
    Priority:
    
      1. Last export directory of the current image
      2. Import directory of the current image
      3. Last export directory of any image (i.e. the current value of this setting)
      4. The default directory (default value) for this setting
    
    Directory 3. is implicitly set upon loading the setting from a persistent source.
    Directory 4. is implicitly set upon setting instantiation.
    """
    
    self.session_only_gui_settings['image_ids_and_directories'].update_image_ids_and_directories()
    self.main_settings['output_directory'].update_current_directory(
      self.image, self.session_only_gui_settings['image_ids_and_directories'].value[self.image.ID])
    
    #TODO: Once `SettingPresenter` instances are contained in Settings and the event handling is revised, resolve this
#     self.main_settings['output_directory'].connect_value_changed_event(
#       lambda output_directory, image_ids_and_directories, current_image_id:
#          image_ids_and_directories.update_directory(current_image_id, output_directory.value),
#       self.session_only_gui_settings['image_ids_and_directories'], self.image.ID
#     )
  
  def _init_gui(self):
    self.dialog = gimpui.Dialog(title=_(constants.PLUGIN_TITLE), role=constants.PLUGIN_PROGRAM_NAME)
    self.dialog.set_transient()
    
    self.dialog.set_default_size(*self.DIALOG_SIZE)
    self.dialog.set_border_width(self.DIALOG_BORDER_WIDTH)
    
    self.folder_chooser_label = gtk.Label()
    self.folder_chooser_label.set_markup("<b>" + _("Save in folder:") + "</b>")
    self.folder_chooser_label.set_alignment(0.0, 0.5)
    
    self.folder_chooser = gtk.FileChooserWidget(action=gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER)
    
    self.file_extension_label = gtk.Label()
    self.file_extension_label.set_markup("<b>" + self.main_settings['file_extension'].display_name + ":</b>")
    self.file_extension_label.set_alignment(0.0, 0.5)
    self.file_extension_entry = gtk.Entry()
    self.file_extension_entry.set_size_request(100, -1)
    self.label_message = gtk.Label()
    self.label_message.set_alignment(0.0, 0.5)
    
    self.export_settings_layer_groups = gtk.CheckButton(self.main_settings['layer_groups_as_folders'].display_name)
    self.export_settings_ignore_invisible = gtk.CheckButton(self.main_settings['ignore_invisible'].display_name)
    self.export_settings_autocrop = gtk.CheckButton(self.main_settings['autocrop'].display_name)
    self.export_settings_use_image_size = gtk.CheckButton(self.main_settings['use_image_size'].display_name)
    
    self.advanced_settings_file_ext_mode_label = gtk.Label(self.main_settings['file_ext_mode'].display_name + ":")
    self.advanced_settings_file_ext_mode_label.set_alignment(0, 0.5)
    self.advanced_settings_file_ext_mode = pggui.IntComboBox(
      self.main_settings['file_ext_mode'].get_option_display_names_and_values()
    )
    self.advanced_settings_strip_mode = pggui.IntComboBox(
      self.main_settings['strip_mode'].get_option_display_names_and_values()
    )
    
    self.advanced_settings_square_bracketed_mode_label = gtk.Label(
      self.main_settings['square_bracketed_mode'].display_name + ":")
    self.advanced_settings_square_bracketed_mode_label.set_alignment(0, 0.5)
    self.advanced_settings_square_bracketed_mode = pggui.IntComboBox(
      self.main_settings['square_bracketed_mode'].get_option_display_names_and_values()
    )
    self.advanced_settings_crop_to_background = gtk.CheckButton(
      self.main_settings['crop_to_background'].display_name
    )
    
    self.advanced_settings_merge_layer_groups = gtk.CheckButton(self.main_settings['merge_layer_groups'].display_name)
    self.advanced_settings_empty_folders = gtk.CheckButton(self.main_settings['empty_folders'].display_name)
    self.advanced_settings_ignore_layer_modes = gtk.CheckButton(self.main_settings['ignore_layer_modes'].display_name)
    
    
    self.hbox_file_extension_entry = gtk.HBox(homogeneous=False)
    self.hbox_file_extension_entry.set_spacing(30)
    self.hbox_file_extension_entry.pack_start(self.file_extension_label, expand=False, fill=True)
    self.hbox_file_extension_entry.pack_start(self.file_extension_entry, expand=False, fill=True)
    
    self.hbox_file_extension = gtk.HBox(homogeneous=False)
    self.hbox_file_extension.set_spacing(self.HBOX_HORIZONTAL_SPACING)
    self.hbox_file_extension.pack_start(self.hbox_file_extension_entry, expand=False, fill=True)
    self.hbox_file_extension.pack_start(self.label_message, expand=False, fill=True)
    
    self.hbox_export_settings = gtk.HBox(homogeneous=False)
    self.hbox_export_settings.pack_start(self.export_settings_layer_groups)
    self.hbox_export_settings.pack_start(self.export_settings_ignore_invisible)
    self.hbox_export_settings.pack_start(self.export_settings_autocrop)
    self.hbox_export_settings.pack_start(self.export_settings_use_image_size)
    
    self.table_labels = gtk.Table(rows=2, columns=1, homogeneous=False)
    self.table_labels.set_row_spacings(self.ADVANCED_SETTINGS_VERTICAL_SPACING)
    self.table_labels.attach(self.advanced_settings_file_ext_mode_label, 0, 1, 0, 1)
    self.table_labels.attach(self.advanced_settings_square_bracketed_mode_label, 0, 1, 1, 2)
    
    self.table_combo_boxes = gtk.Table(rows=2, columns=1, homogeneous=False)
    self.table_combo_boxes.set_row_spacings(self.ADVANCED_SETTINGS_VERTICAL_SPACING)
    self.table_combo_boxes.attach(self.advanced_settings_file_ext_mode, 0, 1, 0, 1, yoptions=0)
    self.table_combo_boxes.attach(self.advanced_settings_square_bracketed_mode, 0, 1, 1, 2, yoptions=0)
    
    self.table_additional_elems = gtk.Table(rows=2, columns=1, homogeneous=False)
    self.table_additional_elems.set_row_spacings(self.ADVANCED_SETTINGS_VERTICAL_SPACING)
    self.table_additional_elems.attach(self.advanced_settings_strip_mode, 0, 1, 0, 1, yoptions=0)
    self.table_additional_elems.attach(self.advanced_settings_crop_to_background, 0, 1, 1, 2)
    
    self.hbox_tables = gtk.HBox(homogeneous=False)
    self.hbox_tables.set_spacing(self.ADVANCED_SETTINGS_HORIZONTAL_SPACING)
    self.hbox_tables.pack_start(self.table_labels, expand=False, fill=True)
    self.hbox_tables.pack_start(self.table_combo_boxes, expand=False, fill=True)
    self.hbox_tables.pack_start(self.table_additional_elems, expand=False, fill=True)
    
    self.hbox_advanced_settings_checkbuttons = gtk.HBox(homogeneous=False)
    self.hbox_advanced_settings_checkbuttons.set_spacing(self.ADVANCED_SETTINGS_HORIZONTAL_SPACING)
    self.hbox_advanced_settings_checkbuttons.pack_start(self.advanced_settings_merge_layer_groups, expand=False, fill=True)
    self.hbox_advanced_settings_checkbuttons.pack_start(self.advanced_settings_empty_folders, expand=False, fill=True)
    self.hbox_advanced_settings_checkbuttons.pack_start(self.advanced_settings_ignore_layer_modes, expand=False, fill=True)
    
    self.vbox_advanced_settings = gtk.VBox(homogeneous=False)
    self.vbox_advanced_settings.set_spacing(self.ADVANCED_SETTINGS_VERTICAL_SPACING)
    self.vbox_advanced_settings.pack_start(self.hbox_tables, expand=False, fill=False)
    self.vbox_advanced_settings.pack_start(self.hbox_advanced_settings_checkbuttons, expand=False, fill=False)
    
    self.alignment_advanced_settings = gtk.Alignment()
    self.alignment_advanced_settings.set_padding(0, 0, self.ADVANCED_SETTINGS_LEFT_MARGIN, 0)
    self.expander_advanced_settings = gtk.Expander()
    self.expander_advanced_settings.set_use_markup(True)
    self.expander_advanced_settings.set_use_underline(True)
    self.expander_advanced_settings.set_label("<b>" + _("_Advanced Settings") + "</b>")
    self.expander_advanced_settings.set_spacing(self.ADVANCED_SETTINGS_VERTICAL_SPACING // 2)
    self.alignment_advanced_settings.add(self.vbox_advanced_settings)
    self.expander_advanced_settings.add(self.alignment_advanced_settings)
    
    self.export_layers_button = self.dialog.add_button(_("_Export Layers"), gtk.RESPONSE_OK)
    self.export_layers_button.grab_default()
    self.cancel_button = self.dialog.add_button(_("_Cancel"), gtk.RESPONSE_CANCEL)
    self.dialog.set_alternative_button_order([gtk.RESPONSE_OK, gtk.RESPONSE_CANCEL])
    
    self.stop_button = gtk.Button()
    self.stop_button.set_label(_("_Stop"))
    
    self.save_settings_button = gtk.Button()
    self.save_settings_button.set_label(_("Save Settings"))
    self.save_settings_button.set_tooltip_text(
      _("Save settings permanently to a file. "
        "If you start GIMP again, the saved settings will be loaded from the "
        "file when {0} is first opened.").format(constants.PLUGIN_TITLE)
    )
    self.reset_settings_button = gtk.Button()
    self.reset_settings_button.set_label(_("Reset Settings"))
    self.reset_settings_button.set_tooltip_text(_("Reset settings to their default values."))
    
    self.progress_bar = gtk.ProgressBar()
    self.progress_bar.set_ellipsize(pango.ELLIPSIZE_MIDDLE)
    
    self.dialog.action_area.pack_end(self.stop_button, expand=False, fill=True)
    self.dialog.action_area.pack_start(self.save_settings_button, expand=False, fill=True)
    self.dialog.action_area.pack_start(self.reset_settings_button, expand=False, fill=True)
    self.dialog.action_area.set_child_secondary(self.save_settings_button, True)
    self.dialog.action_area.set_child_secondary(self.reset_settings_button, True)
    
    self.dialog.vbox.set_spacing(self.DIALOG_VBOX_SPACING)
    self.dialog.vbox.pack_start(self.folder_chooser_label, expand=False, fill=False)
    self.dialog.vbox.pack_start(self.folder_chooser, padding=5)
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
    
    self.save_settings_button.connect("clicked", self.on_save_settings)
    self.reset_settings_button.connect("clicked", self.on_reset_settings)
    
    self.dialog.set_default_response(gtk.RESPONSE_CANCEL)
    
    self.dialog.vbox.show_all()
    self.progress_bar.hide()
    self.stop_button.hide()
    
    self.set_gui_for_settings()
    self.main_settings.set_gui_tooltips()
    
    self.dialog.set_focus(self.file_extension_entry)
    self.dialog.set_default(self.export_layers_button)
    self.file_extension_entry.set_activates_default(True)
    # Place the cursor at the end of the text entry.
    self.file_extension_entry.set_position(-1)
    
    self.dialog.show()
    self.dialog.action_area.set_border_width(self.ACTION_AREA_BORDER_WIDTH)
  
  def set_gui_for_settings(self):
    self.main_settings['file_extension'].set_gui(
      pggui.GtkEntryPresenter, self.file_extension_entry)
    self.main_settings['output_directory'].set_gui(
      pggui.GtkFolderChooserPresenter, self.folder_chooser)
    self.main_settings['layer_groups_as_folders'].set_gui(
      pggui.GtkCheckButtonPresenter, self.export_settings_layer_groups)
    self.main_settings['ignore_invisible'].set_gui(
      pggui.GtkCheckButtonPresenter, self.export_settings_ignore_invisible)
    self.main_settings['autocrop'].set_gui(
      pggui.GtkCheckButtonPresenter, self.export_settings_autocrop)
    self.main_settings['use_image_size'].set_gui(
      pggui.GtkCheckButtonPresenter, self.export_settings_use_image_size)
    self.main_settings['file_ext_mode'].set_gui(
      pggui.GimpUiIntComboBoxPresenter, self.advanced_settings_file_ext_mode)
    self.main_settings['strip_mode'].set_gui(
      pggui.GimpUiIntComboBoxPresenter, self.advanced_settings_strip_mode)
    self.main_settings['square_bracketed_mode'].set_gui(
      pggui.GimpUiIntComboBoxPresenter, self.advanced_settings_square_bracketed_mode)
    self.main_settings['crop_to_background'].set_gui(
      pggui.GtkCheckButtonPresenter, self.advanced_settings_crop_to_background)
    self.main_settings['merge_layer_groups'].set_gui(
      pggui.GtkCheckButtonPresenter, self.advanced_settings_merge_layer_groups)
    self.main_settings['empty_folders'].set_gui(
      pggui.GtkCheckButtonPresenter, self.advanced_settings_empty_folders)
    self.main_settings['ignore_layer_modes'].set_gui(
      pggui.GtkCheckButtonPresenter, self.advanced_settings_ignore_layer_modes)
    
    self.gui_settings['dialog_position'].set_gui(
      pggui.GtkWindowPositionPresenter, self.dialog)
    self.gui_settings['advanced_settings_expanded'].set_gui(
      pggui.GtkExpanderPresenter, self.expander_advanced_settings)
  
  def reset_settings(self):
    for setting_group in [self.main_settings, self.gui_settings]:
      setting_group.reset()
  
  def save_settings(self):
    status, status_message = pgsettinggroup.SettingPersistor.save([self.main_settings, self.gui_settings],
                                                                  [self.gimpshelf_stream, self.config_file_stream])
    if status == pgsettinggroup.SettingPersistor.WRITE_FAIL:
      display_message(status_message, gtk.MESSAGE_WARNING, parent=self.dialog)
    pgsettinggroup.SettingPersistor.save([self.session_only_gui_settings], [self.gimpshelf_stream])
  
  def on_save_settings(self, widget):
    try:
      self.main_settings.update_setting_values()
      self.gui_settings.update_setting_values()
    except pgsetting.SettingValueError as e:
      self.display_message_label(e.message, message_type=self.ERROR)
      return
    
    self.session_only_gui_settings['image_ids_and_directories'].update_directory(
      self.image.ID, self.main_settings['output_directory'].value)
    
    self.save_settings()
    self.display_message_label(_("Settings successfully saved."), message_type=self.INFO)
  
  def on_reset_settings(self, widget):
    self.reset_settings()
    self.save_settings()
    self.display_message_label(_("Settings reset."), message_type=self.INFO)
  
  def on_export_click(self, widget):
    try:
      self.main_settings.update_setting_values()
      self.gui_settings.update_setting_values()
    except pgsetting.SettingValueError as e:
      self.display_message_label(e.message, message_type=self.ERROR)
      return
    
    self.session_only_gui_settings['image_ids_and_directories'].update_directory(
      self.image.ID, self.main_settings['output_directory'].value)
    
    self.setup_gui_before_export()
    pdb.gimp_progress_init("", None)
    
    overwrite_chooser = pggui.GtkDialogOverwriteChooser(
      # Don't insert the Cancel option as a button.
      zip(self.main_settings['overwrite_mode'].options.values()[:-1],
          self.main_settings['overwrite_mode'].options_display_names.values()[:-1]),
      default_value=self.main_settings['overwrite_mode'].options['replace'],
      default_response=self.main_settings['overwrite_mode'].options['cancel'],
      title=_(constants.PLUGIN_TITLE))
    progress_updater = pggui.GtkProgressUpdater(self.progress_bar)
    
    # Make the enabled GUI components more responsive(-ish) by periodically checking
    # whether the GUI has something to do.
    refresh_event_id = gobject.timeout_add(self._GUI_REFRESH_INTERVAL_MILLISECONDS, self.refresh_ui)
    
    self.layer_exporter = exportlayers.LayerExporter(gimpenums.RUN_INTERACTIVE, self.image,
                                                     self.main_settings, overwrite_chooser, progress_updater)
    should_quit = True
    try:
      self.layer_exporter.export_layers()
    except exportlayers.ExportLayersCancelError as e:
      should_quit = False
    except exportlayers.ExportLayersError as e:
      self.display_message_label(e.message, message_type=self.ERROR)
      should_quit = False
    except Exception as e:
      display_exception_message(traceback.format_exc(), parent=self.dialog)
    else:
      self.special_settings['first_run'].set_value(False)
      pgsettinggroup.SettingPersistor.save([self.special_settings['first_run']], [self.gimpshelf_stream])
      
      if not self.layer_exporter.exported_layers:
        display_message(_("No layers were exported."), gtk.MESSAGE_INFO, parent=self.dialog)
        should_quit = False
    finally:
      gobject.source_remove(refresh_event_id)
      pdb.gimp_progress_end()
    
    self.main_settings['overwrite_mode'].set_value(overwrite_chooser.overwrite_mode)
    pgsettinggroup.SettingPersistor.save([self.main_settings, self.gui_settings, self.session_only_gui_settings],
                                         [self.gimpshelf_stream])
    
    if should_quit:
      gtk.main_quit()
    else:
      progress_updater.reset()
      self.restore_gui_after_export()
  
  def setup_gui_before_export(self):
    self.display_message_label(None)
    self._set_gui_enabled(False)
    self.dialog.set_focus_on_map(False)
  
  def restore_gui_after_export(self):
    self.dialog.set_focus_on_map(True)
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
  
  def close(self, widget, event):
    gtk.main_quit()
  
  def cancel(self, widget):
    gtk.main_quit()
  
  def stop(self, widget):
    if self.layer_exporter is not None:
      self.layer_exporter.should_stop = True
  
  def refresh_ui(self):
    while gtk.events_pending():
      gtk.main_iteration()
    
    if self.layer_exporter is not None:
      return not self.layer_exporter.should_stop
    else:
      return True
  
  def display_message_label(self, text, message_type=ERROR):
    if text is None or not text:
      self.label_message.set_text("")
    else:
      text = text[0].upper() + text[1:]
      if not text.endswith("."):
        text += "."
      
      # Display literal '&' as intended. Required by the markup.
      text = text.replace("&", "&amp;")
      
      if message_type == self.ERROR:
        color = "red"
      else:
        color = "blue"
      
      self.label_message.set_markup('<span foreground="' + color + '"><b>' + text + '</b></span>')


#===============================================================================


class _ExportLayersToGui(object):
  
  _GUI_REFRESH_INTERVAL_MILLISECONDS = 500
  
  def __init__(self, image, main_settings, gimpshelf_stream, config_file_stream):
    self.image = image
    self.main_settings = main_settings
    self.gimpshelf_stream = gimpshelf_stream
    self.config_file_stream = config_file_stream
    
    pgsettinggroup.SettingPersistor.load([self.main_settings], [self.gimpshelf_stream])
    
    self.layer_exporter = None
    
    self.export_dialog = ExportDialog(self.stop)
    
    gtk.main_iteration()
    self.export_dialog.show()
    self.export_layers()
  
  def export_layers(self):
    overwrite_chooser = overwrite.NoninteractiveOverwriteChooser(self.main_settings['overwrite_mode'].value)
    progress_updater = pggui.GtkProgressUpdater(self.export_dialog.progress_bar)
    pdb.gimp_progress_init("", None)
    refresh_event_id = gobject.timeout_add(self._GUI_REFRESH_INTERVAL_MILLISECONDS, self.refresh_ui)
    try:
      self.layer_exporter = exportlayers.LayerExporter(gimpenums.RUN_WITH_LAST_VALS, self.image,
                                                       self.main_settings, overwrite_chooser, progress_updater)
      self.layer_exporter.export_layers()
    except exportlayers.ExportLayersCancelError:
      pass
    except exportlayers.ExportLayersError:
      pass
    except Exception:
      display_exception_message(traceback.format_exc(), parent=self.export_dialog.dialog)
    else:
      if not self.layer_exporter.exported_layers:
        display_message(_("No layers were exported."), gtk.MESSAGE_INFO, parent=self.export_dialog.dialog)
    finally:
      gobject.source_remove(refresh_event_id)
      pdb.gimp_progress_end()
  
  def stop(self, widget, *args):
    if self.layer_exporter is not None:
      self.layer_exporter.should_stop = True
  
  def refresh_ui(self):
    while gtk.events_pending():
      gtk.main_iteration()
    
    if self.layer_exporter is not None:
      return not self.layer_exporter.should_stop
    else:
      return True


#===============================================================================


def export_layers_gui(image, main_settings, special_settings, gimpshelf_stream, config_file_stream):
  with pggui.set_gui_excepthook(_(constants.PLUGIN_TITLE), report_uri_list=constants.BUG_REPORT_URI_LIST):
    _ExportLayersGui(image, main_settings, special_settings, gimpshelf_stream, config_file_stream)


def export_layers_to_gui(image, main_settings, gimpshelf_stream, config_file_stream):
  with pggui.set_gui_excepthook(_(constants.PLUGIN_TITLE), report_uri_list=constants.BUG_REPORT_URI_LIST):
    _ExportLayersToGui(image, main_settings, gimpshelf_stream, config_file_stream)
