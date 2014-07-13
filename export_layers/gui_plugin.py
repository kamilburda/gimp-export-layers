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
#from __future__ import unicode_literals
from __future__ import division

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

from export_layers.pylibgimpplugin import settings
from export_layers.pylibgimpplugin import overwrite
from export_layers.pylibgimpplugin import gui

from export_layers import exportlayers
from export_layers import constants

#===============================================================================

pdb = gimp.pdb

#===============================================================================

class GuiSettings(settings.SettingContainer):
  
  def _create_settings(self):
    
    self._add(settings.Setting('dialog_position', ()))
    self['dialog_position'].can_be_reset_by_container = False
    
    self._add(settings.IntSetting('advanced_settings_expanded', False))
    self['advanced_settings_expanded'].can_be_reset_by_container = False

#===============================================================================

def display_message(message, message_type, parent=None):
  gui.display_message(
    message,
    message_type,
    title=constants.PLUGIN_TITLE,
    parent=parent
  )


def display_exception_message(exception_message, parent=None):
  gui.display_exception_message(
    exception_message,
    plugin_title=constants.PLUGIN_TITLE,
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
    self._dialog = gimpui.Dialog(title=constants.PLUGIN_TITLE, role=None)
    self._dialog.set_transient()
    self._dialog.set_border_width(8)
    self._dialog.set_default_size(self._DIALOG_WIDTH, -1)
    
    self._progress_bar = gtk.ProgressBar()
    self._progress_bar.set_ellipsize(pango.ELLIPSIZE_MIDDLE)
    
    self._stop_button = gtk.Button()
    self._stop_button.set_label("Stop")
    
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
    
    self.gui_settings = GuiSettings()
    self.setting_persistor = settings.SettingPersistor([self.gimpshelf_stream, self.config_file_stream],
                                                       [self.gimpshelf_stream])
    
    status = self.setting_persistor.load(self.main_settings, self.gui_settings)
    if status == settings.SettingPersistor.READ_FAIL:
      display_message(self.setting_persistor.status_message, gtk.MESSAGE_WARNING)
    self.setting_persistor.read_setting_streams.pop()
    
    self.setting_presenters = gui.GtkSettingPresenterContainer()
    self.layer_exporter = None
    
    self._init_gui()
    self.export_dialog = ExportDialog(self.stop)
    
    gtk.main()
  
  def _init_gui(self):
    self.dialog = gimpui.Dialog(title=constants.PLUGIN_TITLE, role=None)
    self.dialog.set_transient()
    
    self.dialog.set_default_size(*self.DIALOG_SIZE)
    self.dialog.set_border_width(self.DIALOG_BORDER_WIDTH)
    
    self.directory_chooser_label = gtk.Label()
    self.directory_chooser_label.set_markup("<b>Save in folder:</b>")
    self.directory_chooser_label.set_alignment(0.0, 0.5)
    
    self.directory_chooser = gtk.FileChooserWidget(action=gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER)
    
    self.file_extension_label = gtk.Label()
    self.file_extension_label.set_markup("<b>" + self.main_settings['file_extension'].display_name + ":</b>")
    self.file_extension_label.set_alignment(0.0, 0.5)
    self.file_extension_entry = gtk.Entry()
    self.file_extension_entry.set_size_request(100, -1)
    self.label_message = gtk.Label()
    self.label_message.set_alignment(0.0, 0.5)
    
    self.export_settings_layer_groups = gtk.CheckButton(self.main_settings['layer_groups_as_directories'].display_name)
    self.export_settings_ignore_invisible = gtk.CheckButton(self.main_settings['ignore_invisible'].display_name)
    self.export_settings_autocrop = gtk.CheckButton(self.main_settings['autocrop'].display_name)
    self.export_settings_use_image_size = gtk.CheckButton(self.main_settings['use_image_size'].display_name)
    
    self.advanced_settings_file_ext_mode_label = gtk.Label(self.main_settings['file_ext_mode'].display_name + ":")
    self.advanced_settings_file_ext_mode_label.set_alignment(0, 0.5)
    self.advanced_settings_file_ext_mode = gimpui.IntComboBox(
      tuple(self.main_settings['file_ext_mode'].get_option_display_names_and_values()))
    self.advanced_settings_strip_mode = gimpui.IntComboBox(
      tuple(self.main_settings['strip_mode'].get_option_display_names_and_values()))
    
    self.advanced_settings_square_bracketed_mode_label = gtk.Label(
      self.main_settings['square_bracketed_mode'].display_name + ":")
    self.advanced_settings_square_bracketed_mode_label.set_alignment(0, 0.5)
    self.advanced_settings_square_bracketed_mode = gimpui.IntComboBox(
       tuple(self.main_settings['square_bracketed_mode'].get_option_display_names_and_values()))
    self.advanced_settings_crop_to_background = gtk.CheckButton(
      self.main_settings['crop_to_background'].display_name)
    
    self.advanced_settings_merge_layer_groups = gtk.CheckButton(self.main_settings['merge_layer_groups'].display_name)
    self.advanced_settings_empty_directories = gtk.CheckButton(self.main_settings['empty_directories'].display_name)
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
    self.hbox_advanced_settings_checkbuttons.pack_start(self.advanced_settings_empty_directories, expand=False, fill=True)
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
    self.expander_advanced_settings.set_label("<b>_Advanced Settings</b>")
    self.expander_advanced_settings.set_spacing(self.ADVANCED_SETTINGS_VERTICAL_SPACING // 2)
    self.alignment_advanced_settings.add(self.vbox_advanced_settings)
    self.expander_advanced_settings.add(self.alignment_advanced_settings)
    
    self.dialog.vbox.set_spacing(self.DIALOG_VBOX_SPACING)
    self.dialog.vbox.pack_start(self.directory_chooser_label, expand=False, fill=False)
    self.dialog.vbox.pack_start(self.directory_chooser, padding=5)
    self.dialog.vbox.pack_start(self.hbox_file_extension, expand=False, fill=False)
    self.dialog.vbox.pack_start(self.hbox_export_settings, expand=False, fill=False)
    self.dialog.vbox.pack_start(self.expander_advanced_settings, expand=False, fill=False)
    self.dialog.vbox.pack_start(gtk.HSeparator(), expand=False, fill=True)
    
    
    self.export_layers_button = self.dialog.add_button("_Export Layers", gtk.RESPONSE_OK)
    self.export_layers_button.grab_default()
    self.cancel_button = self.dialog.add_button("_Cancel", gtk.RESPONSE_CANCEL)
    self.dialog.set_alternative_button_order([gtk.RESPONSE_OK, gtk.RESPONSE_CANCEL])
    
    self.save_settings_button = gtk.Button()
    self.save_settings_button.set_label("Save Settings")
    self.reset_settings_button = gtk.Button()
    self.reset_settings_button.set_label("Reset Settings")
    self.dialog.action_area.pack_start(self.save_settings_button, expand=False, fill=True)
    self.dialog.action_area.pack_start(self.reset_settings_button, expand=False, fill=True)
    self.dialog.action_area.set_child_secondary(self.save_settings_button, True)
    self.dialog.action_area.set_child_secondary(self.reset_settings_button, True)
    
    
    self.export_layers_button.connect("clicked", self.on_export_click)
    self.cancel_button.connect("clicked", self.cancel)
    self.dialog.connect("delete-event", self.close)
    
    self.save_settings_button.connect("clicked", self.on_save_settings)
    self.reset_settings_button.connect("clicked", self.on_reset_settings)
    
    # Don't show the whole dialog just yet, because some elements may be disabled
    # or made invisible by the setting presenters.
    self.dialog.vbox.show_all()
    
    self.create_setting_presenters()
    self.setting_presenters.set_tooltips()
    self.setting_presenters.assign_setting_values_to_elements()
    self.setting_presenters.connect_value_changed_events()
    
    self.dialog.set_focus(self.file_extension_entry)
    self.dialog.show()
    self.dialog.action_area.set_border_width(self.ACTION_AREA_BORDER_WIDTH)
  
  def create_setting_presenters(self):
    self.setting_presenters.add(
      gui.GtkEntryPresenter(
        self.main_settings['file_extension'],
        self.file_extension_entry))
    
    self.setting_presenters.add(
      gui.GtkDirectoryChooserWidgetPresenter(
        self.main_settings['output_directory'],
        self.directory_chooser,
        image=self.image,
        default_directory=None))
    
    self.setting_presenters.add(
      gui.GtkCheckButtonPresenter(
        self.main_settings['layer_groups_as_directories'],
        self.export_settings_layer_groups))
    
    self.setting_presenters.add(
      gui.GtkCheckButtonPresenter(
        self.main_settings['ignore_invisible'],
        self.export_settings_ignore_invisible))
    
    self.setting_presenters.add(
      gui.GtkCheckButtonPresenter(
        self.main_settings['autocrop'],
        self.export_settings_autocrop))
    
    self.setting_presenters.add(
      gui.GtkCheckButtonPresenter(
        self.main_settings['use_image_size'],
        self.export_settings_use_image_size))
    
    self.setting_presenters.add(
      gui.GimpUiIntComboBoxPresenter(
        self.main_settings['file_ext_mode'],
        self.advanced_settings_file_ext_mode))
    
    self.setting_presenters.add(
      gui.GimpUiIntComboBoxPresenter(
        self.main_settings['strip_mode'],
        self.advanced_settings_strip_mode))
    
    self.setting_presenters.add(
      gui.GimpUiIntComboBoxPresenter(
        self.main_settings['square_bracketed_mode'],
        self.advanced_settings_square_bracketed_mode))
    
    self.setting_presenters.add(
      gui.GtkCheckButtonPresenter(
        self.main_settings['crop_to_background'],
        self.advanced_settings_crop_to_background))
    
    self.setting_presenters.add(
      gui.GtkCheckButtonPresenter(
        self.main_settings['merge_layer_groups'],
        self.advanced_settings_merge_layer_groups))
    
    self.setting_presenters.add(
      gui.GtkCheckButtonPresenter(
        self.main_settings['empty_directories'],
        self.advanced_settings_empty_directories))
    
    self.setting_presenters.add(
      gui.GtkCheckButtonPresenter(
        self.main_settings['ignore_layer_modes'],
        self.advanced_settings_ignore_layer_modes))
    
    self.setting_presenters.add(
      gui.GtkWindowPositionPresenter(
        self.gui_settings['dialog_position'],
        self.dialog))
    
    self.setting_presenters.add(
      gui.GtkExpanderPresenter(
        self.gui_settings['advanced_settings_expanded'],
        self.expander_advanced_settings))
  
  def reset_settings(self):
    for setting_container in [self.main_settings, self.gui_settings]:
      setting_container.reset()
  
  def save_settings(self):
    self.setting_persistor.write_setting_streams.append(self.config_file_stream)
    
    status = self.setting_persistor.save(self.main_settings, self.gui_settings)
    if status == self.setting_persistor.WRITE_FAIL:
      display_message(self.setting_persistor.status_message, gtk.MESSAGE_WARNING,
                      parent=self.dialog)
    self.setting_persistor.write_setting_streams.pop()
  
  def on_save_settings(self, widget):
    try:
      self.setting_presenters.assign_element_values_to_settings()
    except settings.SettingValueError as e:
      self.display_message_label(e.message, message_type=self.ERROR)
      return
    
    self.save_settings()
    self.display_message_label("Settings successfully saved", message_type=self.INFO)
  
  def on_reset_settings(self, widget):
    self.reset_settings()
    self.setting_presenters.assign_setting_values_to_elements()
    self.save_settings()
    self.display_message_label("Settings reset", message_type=self.INFO)
  
  def on_export_click(self, widget):
    try:
      self.setting_presenters.assign_element_values_to_settings()
    except settings.SettingValueError as e:
      self.display_message_label(e.message, message_type=self.ERROR)
      return
    
    self.dialog.hide()
    self.export_dialog.show()
    self.display_message_label(None)
    pdb.gimp_progress_init("", None)
    should_quit = True
    
    overwrite_chooser = gui.GtkDialogOverwriteChooser(
      # Don't insert the Cancel option as a button.
      zip(self.main_settings['overwrite_mode'].options.values()[:-1],
          self.main_settings['overwrite_mode'].options_display_names.values()[:-1]),
      default_value=self.main_settings['overwrite_mode'].options['replace'],
      default_response=self.main_settings['overwrite_mode'].options['cancel'],
      title=constants.PLUGIN_TITLE)
    progress_updater = gui.GtkProgressUpdater(self.export_dialog.progress_bar)
    
    # Make the enabled GUI components more responsive(-ish) by periodically checking
    # whether the GUI has something to do.
    refresh_event_id = gobject.timeout_add(self._GUI_REFRESH_INTERVAL_MILLISECONDS, self.refresh_ui)
    
    self.layer_exporter = exportlayers.LayerExporter(gimpenums.RUN_INTERACTIVE, self.image,
                                                     self.main_settings, overwrite_chooser, progress_updater)
    try:
      self.layer_exporter.export_layers()
    except exportlayers.ExportLayersCancelError as e:
      should_quit = False
    except exportlayers.ExportLayersNoLayersToExport as e:
      display_message(e.message, gtk.MESSAGE_INFO, parent=self.export_dialog.dialog)
      should_quit = False
    except exportlayers.ExportLayersError as e:
      self.display_message_label(e.message, message_type=self.ERROR)
      should_quit = False
    except Exception as e:
      display_exception_message(traceback.format_exc(), parent=self.export_dialog.dialog)
    else:
      self.special_settings['first_run'].value = False
      self.setting_persistor.save([self.special_settings['first_run']])
    finally:
      gobject.source_remove(refresh_event_id)
      pdb.gimp_progress_end()
      self.export_dialog.hide()
    
    self.main_settings['overwrite_mode'].value = overwrite_chooser.overwrite_mode
    self.setting_persistor.save(self.main_settings, self.gui_settings)
    
    if should_quit:
      gtk.main_quit()
    else:
      progress_updater.reset()
      self.dialog.show()
  
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
  
  def __init__(self, image, main_settings, setting_persistor):
    self.image = image
    self.main_settings = main_settings
    self.setting_persistor = setting_persistor
    
    self.setting_persistor.load(self.main_settings)
    
    self.layer_exporter = None
    
    self.export_dialog = ExportDialog(self.stop)
    
    gtk.main_iteration()
    self.export_dialog.show()
    self.export_layers()
  
  def export_layers(self):
    overwrite_chooser = overwrite.NoninteractiveOverwriteChooser(self.main_settings['overwrite_mode'].value)
    progress_updater = gui.GtkProgressUpdater(self.export_dialog.progress_bar)
    pdb.gimp_progress_init("", None)
    refresh_event_id = gobject.timeout_add(self._GUI_REFRESH_INTERVAL_MILLISECONDS, self.refresh_ui)
    try:
      self.layer_exporter = exportlayers.LayerExporter(gimpenums.RUN_WITH_LAST_VALS, self.image,
                                                       self.main_settings, overwrite_chooser, progress_updater)
      self.layer_exporter.export_layers()
    except exportlayers.ExportLayersCancelError:
      pass
    except exportlayers.ExportLayersNoLayersToExport as e:
      display_message(e.message, gtk.MESSAGE_INFO, parent=self.export_dialog.dialog)
    except exportlayers.ExportLayersError:
      pass
    except Exception:
      display_exception_message(traceback.format_exc(), parent=self.export_dialog.dialog)
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
  with gui.set_gui_excepthook(constants.PLUGIN_TITLE, report_uri_list=constants.BUG_REPORT_URI_LIST):
    _ExportLayersGui(image, main_settings, special_settings, gimpshelf_stream, config_file_stream)


def export_layers_to_gui(image, main_settings, setting_persistor):
  with gui.set_gui_excepthook(constants.PLUGIN_TITLE, report_uri_list=constants.BUG_REPORT_URI_LIST):
    _ExportLayersToGui(image, main_settings, setting_persistor)
