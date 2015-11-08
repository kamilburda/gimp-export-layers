#-------------------------------------------------------------------------------
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
#-------------------------------------------------------------------------------

"""
This module defines the GUI for the plug-in.
"""

#===============================================================================

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division

str = unicode

#===============================================================================

import functools
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
from export_layers.pygimplib import pgsettingpersistor
from export_layers.pygimplib import overwrite
from export_layers.pygimplib import pggui

from export_layers import settings_plugin
from export_layers import exportlayers
from export_layers import constants

#===============================================================================

pdb = gimp.pdb

#===============================================================================


def display_message(message, message_type, parent=None, buttons=gtk.BUTTONS_OK):
  return pggui.display_message(
    message,
    message_type,
    title=_(constants.PLUGIN_TITLE),
    parent=parent,
    buttons=buttons
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


def _apply_gui_values_to_settings(func):
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
    except pgsetting.SettingValueError as e:
      self.display_message_label(e.message, message_type=self.ERROR)
      return
    
    func(self, *args, **kwargs)
  
  return func_wrapper


def _setup_image_ids_and_directories_and_output_directory(settings, current_image):
  """
  Set up the initial output directory for the current image according to the
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
  settings['main']['output_directory'].update_current_directory(
      current_image, settings['gui_session']['image_ids_and_directories'].value[current_image.ID])
  
  def on_output_directory_changed(output_directory, image_ids_and_directories, current_image_id):
    image_ids_and_directories.update_directory(current_image_id, output_directory.value)
  
  settings['main']['output_directory'].connect_value_changed_event(
    on_output_directory_changed, [settings['gui_session']['image_ids_and_directories'], current_image.ID])


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
  
  def __init__(self, image, settings, session_source, persistent_source):
    self.image = image
    self.settings = settings
    self.session_source = session_source
    self.persistent_source = persistent_source
    
    settings_plugin.add_gui_settings(settings)
    
    status, status_message = pgsettingpersistor.SettingPersistor.load(
      [self.settings['main'], self.settings['gui']], [self.session_source, self.persistent_source])
    if status == pgsettingpersistor.SettingPersistor.READ_FAIL:
      display_message(status_message, gtk.MESSAGE_WARNING)
    
    pgsettingpersistor.SettingPersistor.load([self.settings['gui_session']], [self.session_source])
    
    _setup_image_ids_and_directories_and_output_directory(self.settings, self.image)
    
    self.layer_exporter = None
    
    self._init_gui()
    
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
    
    self.advanced_settings_file_ext_mode_label = gtk.Label(
      self.settings['main']['file_ext_mode'].display_name + ":")
    self.advanced_settings_file_ext_mode_label.set_alignment(0, 0.5)
    
    self.advanced_settings_square_bracketed_mode_label = gtk.Label(
      self.settings['main']['square_bracketed_mode'].display_name + ":")
    self.advanced_settings_square_bracketed_mode_label.set_alignment(0, 0.5)
    
    self.settings.initialize_gui({
      'file_extension': [
         pgsetting.SettingGuiTypes.file_extension_entry, self.file_extension_entry],
      'output_directory': [
         pgsetting.SettingGuiTypes.folder_chooser, self.folder_chooser],
      'dialog_position': [
         pgsetting.SettingGuiTypes.window_position, self.dialog],
      'advanced_settings_expanded': [
         pgsetting.SettingGuiTypes.expander, self.expander_advanced_settings],
    })
    
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
    self.table_labels.attach(self.advanced_settings_file_ext_mode_label, 0, 1, 0, 1)
    self.table_labels.attach(self.advanced_settings_square_bracketed_mode_label, 0, 1, 1, 2)
    
    self.table_combo_boxes = gtk.Table(rows=2, columns=1, homogeneous=False)
    self.table_combo_boxes.set_row_spacings(self.ADVANCED_SETTINGS_VERTICAL_SPACING)
    self.table_combo_boxes.attach(self.settings['main']['file_ext_mode'].gui.element, 0, 1, 0, 1, yoptions=0)
    self.table_combo_boxes.attach(
      self.settings['main']['square_bracketed_mode'].gui.element, 0, 1, 1, 2, yoptions=0)
    
    self.table_additional_elems = gtk.Table(rows=2, columns=1, homogeneous=False)
    self.table_additional_elems.set_row_spacings(self.ADVANCED_SETTINGS_VERTICAL_SPACING)
    self.table_additional_elems.attach(self.settings['main']['strip_mode'].gui.element, 0, 1, 0, 1, yoptions=0)
    self.table_additional_elems.attach(self.settings['main']['crop_to_background'].gui.element, 0, 1, 1, 2)
    
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
    
    self.export_layers_button = self.dialog.add_button(_("_Export Layers"), gtk.RESPONSE_OK)
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
    
    self.save_settings_button.connect("clicked", self.on_save_settings_clicked)
    self.reset_settings_button.connect("clicked", self.on_reset_settings_clicked)
    
    self.dialog.set_default_response(gtk.RESPONSE_CANCEL)
    
    self.dialog.vbox.show_all()
    self.progress_bar.hide()
    self.stop_button.hide()
    
    self.dialog.set_focus(self.file_extension_entry)
    self.dialog.set_default(self.export_layers_button)
    self.file_extension_entry.set_activates_default(True)
    # Place the cursor at the end of the text entry.
    self.file_extension_entry.set_position(-1)
    
    self.dialog.show()
    self.dialog.action_area.set_border_width(self.ACTION_AREA_BORDER_WIDTH)
    
    # This may fix the hidden file format dialog bug on Windows.
    self.dialog.grab_remove()
  
  def reset_settings(self):
    for setting_group in [self.settings['main'], self.settings['gui']]:
      setting_group.reset()
  
  def save_settings(self):
    status, status_message = pgsettingpersistor.SettingPersistor.save(
      [self.settings['main'], self.settings['gui']], [self.session_source, self.persistent_source])
    if status == pgsettingpersistor.SettingPersistor.WRITE_FAIL:
      display_message(status_message, gtk.MESSAGE_WARNING, parent=self.dialog)
    
    pgsettingpersistor.SettingPersistor.save([self.settings['gui_session']], [self.session_source])
  
  @_apply_gui_values_to_settings
  def on_save_settings_clicked(self, widget):
    self.save_settings()
    self.display_message_label(_("Settings successfully saved."), message_type=self.INFO)
  
  def on_reset_settings_clicked(self, widget):
    resopnse_id = display_message(_("Do you really want to reset settings?"),
                                  gtk.MESSAGE_WARNING, parent=self.dialog,
                                  buttons=gtk.BUTTONS_YES_NO)
    
    if resopnse_id == gtk.RESPONSE_YES:
      self.reset_settings()
      self.save_settings()
      self.display_message_label(_("Settings reset."), message_type=self.INFO)
  
  @_apply_gui_values_to_settings
  def on_export_click(self, widget):
    self.setup_gui_before_export()
    pdb.gimp_progress_init("", None)
    
    overwrite_chooser = pggui.GtkDialogOverwriteChooser(
      # Don't insert the Cancel item as a button.
      zip(self.settings['main']['overwrite_mode'].items.values()[:-1],
          self.settings['main']['overwrite_mode'].items_display_names.values()[:-1]),
      default_value=self.settings['main']['overwrite_mode'].items['replace'],
      default_response=self.settings['main']['overwrite_mode'].items['cancel'],
      title=_(constants.PLUGIN_TITLE))
    progress_updater = pggui.GtkProgressUpdater(self.progress_bar)
    
    # Make the enabled GUI components more responsive(-ish) by periodically checking
    # whether the GUI has something to do.
    refresh_event_id = gobject.timeout_add(self._GUI_REFRESH_INTERVAL_MILLISECONDS, self.refresh_ui)
    
    self.layer_exporter = exportlayers.LayerExporter(
      gimpenums.RUN_INTERACTIVE, self.image, self.settings['main'], overwrite_chooser, progress_updater)
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
      self.settings['special']['first_plugin_run'].set_value(False)
      pgsettingpersistor.SettingPersistor.save(
        [self.settings['special']['first_plugin_run']], [self.session_source])
      
      if not self.layer_exporter.exported_layers:
        display_message(_("No layers were exported."), gtk.MESSAGE_INFO, parent=self.dialog)
        should_quit = False
    finally:
      gobject.source_remove(refresh_event_id)
      pdb.gimp_progress_end()
    
    self.settings['main']['overwrite_mode'].set_value(overwrite_chooser.overwrite_mode)
    pgsettingpersistor.SettingPersistor.save(
      [self.settings['main'], self.settings['gui'], self.settings['gui_session']], [self.session_source])
    
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
      
      # Display literal "&" as intended. Required by the markup.
      text = text.replace("&", "&amp;")
      
      if message_type == self.ERROR:
        color = "red"
      else:
        color = "blue"
      
      self.label_message.set_markup("<span foreground='{0}'><b>{1}</b></span>".format(color, text))


#===============================================================================


class _ExportLayersToGui(object):
  
  _GUI_REFRESH_INTERVAL_MILLISECONDS = 500
  
  def __init__(self, image, settings, session_source, persistent_source):
    self.image = image
    self.settings = settings
    self.session_source = session_source
    self.persistent_source = persistent_source
    
    pgsettingpersistor.SettingPersistor.load([self.settings['main']], [self.session_source])
    
    self.layer_exporter = None
    
    self.export_dialog = ExportDialog(self.stop)
    
    gtk.main_iteration()
    self.export_dialog.show()
    self.export_layers()
  
  def export_layers(self):
    overwrite_chooser = overwrite.NoninteractiveOverwriteChooser(self.settings['main']['overwrite_mode'].value)
    progress_updater = pggui.GtkProgressUpdater(self.export_dialog.progress_bar)
    pdb.gimp_progress_init("", None)
    refresh_event_id = gobject.timeout_add(self._GUI_REFRESH_INTERVAL_MILLISECONDS, self.refresh_ui)
    try:
      self.layer_exporter = exportlayers.LayerExporter(
        gimpenums.RUN_WITH_LAST_VALS, self.image, self.settings['main'], overwrite_chooser, progress_updater)
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


def export_layers_gui(image, settings, session_source, persistent_source):
  _ExportLayersGui(image, settings, session_source, persistent_source)


def export_layers_repeat_gui(image, settings, session_source, persistent_source):
  _ExportLayersToGui(image, settings, session_source, persistent_source)

