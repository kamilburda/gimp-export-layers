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

import traceback

import gobject
import pygtk
pygtk.require("2.0")
import gtk
import pango

import gimp
import gimpenums
import gimpui

from export_layers.libgimpplugin import settings
from export_layers.libgimpplugin import overwrite
from export_layers.libgimpplugin import gui

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

def display_exception_message(exception_message, parent=None):
  gui.display_exception_message(
    constants.PLUGIN_TITLE,
    exception_message,
    report_uri_list=constants.BUG_REPORT_URI_LIST,
    parent=parent
    )

def display_message_dialog(text, message_type=gtk.MESSAGE_INFO, parent=None):
  message_dialog = gtk.MessageDialog(parent=parent, type=message_type, buttons=gtk.BUTTONS_OK)
  message_dialog.set_transient_for(parent)
  message_dialog.set_markup(text)
  message_dialog.run()
  message_dialog.destroy()

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
  
  BUTTON_HORIZONTAL_PADDING = 6
  BUTTON_VERTICAL_PADDING = 2
  
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
      gui.display_warning_message(constants.PLUGIN_TITLE, self.setting_persistor.status_message)
    self.setting_persistor.read_setting_streams.pop()
    
    self.setting_presenters = settings.SettingPresenterContainer()
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
    
    self.file_format_label = gtk.Label()
    self.file_format_label.set_markup("<b>" + self.main_settings['file_format'].display_name + ":</b>")
    self.file_format_label.set_alignment(0.0, 0.5)
    self.file_format_entry = gtk.Entry()
    self.file_format_entry.set_size_request(100, -1)
    self.label_message = gtk.Label()
    self.label_message.set_alignment(0.0, 0.5)
    
    self.hbox_file_format_entry = gtk.HBox(homogeneous=False)
    self.hbox_file_format_entry.set_spacing(30)
    self.hbox_file_format_entry.pack_start(self.file_format_label, expand=False, fill=True)
    self.hbox_file_format_entry.pack_start(self.file_format_entry, expand=False, fill=True)
    
    self.hbox_file_format = gtk.HBox(homogeneous=False)
    self.hbox_file_format.set_spacing(self.HBOX_HORIZONTAL_SPACING)
    self.hbox_file_format.pack_start(self.hbox_file_format_entry, expand=False, fill=True)
    self.hbox_file_format.pack_start(self.label_message, expand=False, fill=True)
    
    self.export_settings_layer_groups = gtk.CheckButton(self.main_settings['layer_groups_as_directories'].display_name)
    self.export_settings_ignore_invisible = gtk.CheckButton(self.main_settings['ignore_invisible'].display_name)
    self.export_settings_autocrop = gtk.CheckButton(self.main_settings['autocrop'].display_name)
    self.export_settings_use_image_size = gtk.CheckButton(self.main_settings['use_image_size'].display_name)
    self.hbox_export_settings = gtk.HBox(homogeneous=False)
    self.hbox_export_settings.pack_start(self.export_settings_layer_groups)
    self.hbox_export_settings.pack_start(self.export_settings_ignore_invisible)
    self.hbox_export_settings.pack_start(self.export_settings_autocrop)
    self.hbox_export_settings.pack_start(self.export_settings_use_image_size)
    
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
    self.advanced_settings_remove_square_brackets = gtk.CheckButton(
      self.main_settings['remove_square_brackets'].display_name)
    self.advanced_settings_crop_to_background = gtk.CheckButton(
      self.main_settings['crop_to_background'].display_name)
    
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
    self.table_additional_elems.attach(self.advanced_settings_remove_square_brackets, 0, 1, 1, 2)
    self.table_additional_elems.attach(self.advanced_settings_crop_to_background, 0, 1, 1, 2)
    
    self.hbox_tables = gtk.HBox(homogeneous=False)
    self.hbox_tables.set_spacing(self.ADVANCED_SETTINGS_HORIZONTAL_SPACING)
    self.hbox_tables.pack_start(self.table_labels, expand=False, fill=True)
    self.hbox_tables.pack_start(self.table_combo_boxes, expand=False, fill=True)
    self.hbox_tables.pack_start(self.table_additional_elems, expand=False, fill=True)
    
    self.advanced_settings_merge_layer_groups = gtk.CheckButton(self.main_settings['merge_layer_groups'].display_name)
    self.advanced_settings_empty_directories = gtk.CheckButton(self.main_settings['empty_directories'].display_name)
    self.hbox_advanced_layer_group_settings = gtk.HBox(homogeneous=False)
    self.hbox_advanced_layer_group_settings.set_spacing(self.ADVANCED_SETTINGS_HORIZONTAL_SPACING)
    self.hbox_advanced_layer_group_settings.pack_start(self.advanced_settings_merge_layer_groups, expand=False, fill=True)
    self.hbox_advanced_layer_group_settings.pack_start(self.advanced_settings_empty_directories, expand=False, fill=True)
    
    self.vbox_advanced_settings = gtk.VBox(homogeneous=False)
    self.vbox_advanced_settings.set_spacing(self.ADVANCED_SETTINGS_VERTICAL_SPACING)
    self.vbox_advanced_settings.pack_start(self.hbox_tables, expand=False, fill=False)
    self.vbox_advanced_settings.pack_start(self.hbox_advanced_layer_group_settings, expand=False, fill=False)
    
    self.alignment_advanced_settings = gtk.Alignment()
    self.alignment_advanced_settings.set_padding(0, 0, self.ADVANCED_SETTINGS_LEFT_MARGIN, 0)
    self.expander_advanced_settings = gtk.Expander()
    self.expander_advanced_settings.set_use_markup(True)
    self.expander_advanced_settings.set_use_underline(True)
    self.expander_advanced_settings.set_label("<b>_Advanced Settings</b>")
    self.expander_advanced_settings.set_spacing(self.ADVANCED_SETTINGS_VERTICAL_SPACING // 2)
    self.alignment_advanced_settings.add(self.vbox_advanced_settings)
    self.expander_advanced_settings.add(self.alignment_advanced_settings)
    
    
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
    
    
    self.dialog.vbox.set_spacing(self.DIALOG_VBOX_SPACING)
    self.dialog.vbox.pack_start(self.directory_chooser_label, expand=False, fill=False)
    self.dialog.vbox.pack_start(self.directory_chooser, padding=5)
    self.dialog.vbox.pack_start(self.hbox_file_format, expand=False, fill=False)
    self.dialog.vbox.pack_start(self.hbox_export_settings, expand=False, fill=False)
    self.dialog.vbox.pack_start(self.expander_advanced_settings, expand=False, fill=False)
    self.dialog.vbox.pack_start(gtk.HSeparator(), expand=False, fill=True)
    
    self.save_settings_button.connect("clicked", self.on_save_settings)
    self.reset_settings_button.connect("clicked", self.on_reset_settings)
    
    self.export_layers_button.connect("clicked", self.on_export_click)
    self.cancel_button.connect("clicked", self.cancel)
    self.dialog.connect("delete-event", self.close)
    
    self.create_setting_presenters()
    self.create_tooltips()
    
    self.dialog.vbox.show_all()
    
    self.assign_values_from_settings_to_gui_elements()
    self.connect_events_for_settings()
    
    self.dialog.set_focus(self.file_format_entry)
    self.display_message_label(None)
    
    self.dialog.show()
    
    self.dialog.action_area.set_border_width(self.ACTION_AREA_BORDER_WIDTH)
  
  def create_setting_presenters(self):
    self.setting_presenters.add(
      gui.GtkEntryPresenter(
        self.main_settings['file_format'],
        self.file_format_entry))
    
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
        self.main_settings['remove_square_brackets'],
        self.advanced_settings_remove_square_brackets))
    
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
    
  
  def create_tooltips(self):
    for setting_presenter in self.setting_presenters:
      if setting_presenter.setting.description is not None and setting_presenter.setting.description:
        setting_presenter.element.set_tooltip_text(setting_presenter.setting.description)
  
  def connect_events_for_settings(self):
    for setting_presenter in self.setting_presenters:
      if setting_presenter.value_changed_signal is not None:
        if setting_presenter.setting.can_streamline():
          setting_presenter.connect(self.on_element_value_change_streamline)
        else:
          setting_presenter.connect(self.on_element_value_change)
  
  
  def on_element_value_change_streamline(self, widget, *args):
    presenter = self.setting_presenters[widget]
    presenter.setting.value = presenter.value
    changed_settings = presenter.setting.streamline()
    self.setting_presenters.apply_changed_settings(changed_settings)
  
  def on_element_value_change(self, widget, *args):
    presenter = self.setting_presenters[widget]
    presenter.setting.value = presenter.value
  
  
  def assign_values_from_settings_to_gui_elements(self):
    for presenter in self.setting_presenters:
      presenter.value = presenter.setting.value
    
    changed_settings = self.main_settings.streamline(force=True)
    self.setting_presenters.apply_changed_settings(changed_settings)
    
    dialog_position = self.gui_settings['dialog_position'].value
    if dialog_position is not None and len(dialog_position) == 2:
      self.dialog.move(*dialog_position)
    
    self.expander_advanced_settings.set_expanded(self.gui_settings['advanced_settings_expanded'].value)
  
  def assign_values_from_gui_elements_to_settings(self):
    exception_message = ""
    
    for presenter in self.setting_presenters:
      try:
        presenter.setting.value = presenter.value
      except ValueError as e:
        if not exception_message:
          exception_message = e.message
      finally:
        # Settings are continuously streamlined. Clear the changed attributes
        # to prevent streamline() from changing the settings unnecessarily.
        presenter.setting.changed_attributes.clear()
    
    self.gui_settings['dialog_position'].value = self.dialog.get_position()
    self.gui_settings['advanced_settings_expanded'].value = self.expander_advanced_settings.get_expanded()
    
    if exception_message:
      raise ValueError(exception_message)
  
  def reset_settings(self):
    for setting_container in [self.main_settings, self.gui_settings]:
      setting_container.reset()
  
  def save_settings(self):
    self.setting_persistor.write_setting_streams.append(self.config_file_stream)
    
    status = self.setting_persistor.save(self.main_settings, self.gui_settings)
    if status == self.setting_persistor.WRITE_FAIL:
      gui.display_warning_message(constants.PLUGIN_TITLE, self.setting_persistor.status_message,
                                  parent=self.dialog)
    
    self.setting_persistor.write_setting_streams.pop()
  
  def on_save_settings(self, widget):
    try:
      self.assign_values_from_gui_elements_to_settings()
    except ValueError as e:
      self.display_message_label(e.message, message_type=self.ERROR)
      return
    
    self.save_settings()
    self.display_message_label("Settings successfully saved", message_type=self.INFO)
  
  def on_reset_settings(self, widget):
    self.reset_settings()
    self.assign_values_from_settings_to_gui_elements()
    self.save_settings()
    self.display_message_label("Settings reset", message_type=self.INFO)
  
  
  def on_export_click(self, widget):
    try:
      self.assign_values_from_gui_elements_to_settings()
    except ValueError as e:
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
    except exportlayers.ExportLayersError as e:
      self.display_message_label(e.message, message_type=self.ERROR)
      should_quit = False
    except Exception as e:
      display_exception_message(traceback.format_exc(), parent=self.export_dialog.dialog)
    else:
      if self.layer_exporter.exported_layers:
        self.special_settings['first_run'].value = False
        self.setting_persistor.save([self.special_settings['first_run']])
      else:
        display_message_dialog("There are no layers to export.", parent=self.export_dialog.dialog)
        should_quit = False
    finally:
      gobject.source_remove(refresh_event_id)
      progress_updater.reset()
      pdb.gimp_progress_end()
      self.export_dialog.hide()
    
    self.main_settings['overwrite_mode'].value = overwrite_chooser.overwrite_mode
    self.setting_persistor.save(self.main_settings, self.gui_settings)
    
    if should_quit:
      gtk.main_quit()
    else:
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
    
    self._dialog = ExportDialog(self.stop)
    
    gtk.main_iteration()
    self._dialog.show()
    self._export_layers()
  
  def _export_layers(self):
    overwrite_chooser = overwrite.NoninteractiveOverwriteChooser(self.main_settings['overwrite_mode'].value)
    progress_updater = gui.GtkProgressUpdater(self._dialog.progress_bar)
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
      display_exception_message(traceback.format_exc(), parent=self._dialog.dialog)
    else:
      if not self.layer_exporter.exported_layers:
        display_message_dialog("There are no layers to export.", parent=self._dialog.dialog)
    finally:
      gobject.source_remove(refresh_event_id)
      pdb.gimp_progress_end()
      progress_updater.reset()
  
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
  _ExportLayersGui(image, main_settings, special_settings, gimpshelf_stream, config_file_stream)

def export_layers_to_gui(image, main_settings, setting_persistor):
  _ExportLayersToGui(image, main_settings, setting_persistor)
