#-------------------------------------------------------------------------------
#
# This file is part of libgimpplugin.
#
# Copyright (C) 2014 khalim19 <khalim19@gmail.com>
# 
# libgimpplugin is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# libgimpplugin is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with libgimpplugin.  If not, see <http://www.gnu.org/licenses/>.
#
#-------------------------------------------------------------------------------

"""
This module:
* defines GTK overwrite dialog
* defines GTK progress updater
* defines wrappers for GTK elements (used for SettingPresenter objects)
"""

#=============================================================================== 

import abc
import webbrowser

import pygtk
pygtk.require("2.0")
import gtk

import gimpui

import settings
import overwrite
import progress

#===============================================================================

class GtkDialogOverwriteChooser(overwrite.InteractiveOverwriteChooser):
  
  """
  This class is used to display a GTK dialog prompt in an interactive environment
  when a file about to be saved has the same name as an already existing file.
  """
  
  def __init__(self, values_and_display_names, default_value, default_response, title=""):
    
    super(GtkDialogOverwriteChooser, self).__init__(values_and_display_names, default_value, default_response)
    
    self._title = title
    self._values = [value for value, _ in self.values_and_display_names]
    
    self._init_gui()
  
  def _init_gui(self):
    self._dialog = gimpui.Dialog(title="", role=None)
    self._dialog.set_transient()
    self._dialog.set_border_width(8)
    self._dialog.set_resizable(False)
    self._dialog.set_title(self._title)
    
    self._hbox_dialog_contents = gtk.HBox(homogeneous=False)
    self._hbox_dialog_contents.set_spacing(10)
    self._dialog_icon = gtk.Image()
    self._dialog_icon.set_from_stock(gtk.STOCK_DIALOG_QUESTION, gtk.ICON_SIZE_DIALOG)
    self._dialog_text = gtk.Label("")
    self._hbox_dialog_contents.pack_start(self._dialog_icon, expand=False, fill=False)
    self._hbox_dialog_contents.pack_start(self._dialog_text, expand=False, fill=False)
    
    self._hbox_apply_to_all = gtk.HBox(homogeneous=False)
    self._hbox_apply_to_all.set_spacing(5)
    self._apply_to_all_checkbox = gtk.CheckButton(label="Apply action to all files")
    self._hbox_apply_to_all.pack_start(self._apply_to_all_checkbox, expand=False, fill=False)
    
    self._dialog.vbox.set_spacing(3)
    self._dialog.vbox.pack_start(self._hbox_dialog_contents, expand=False, fill=False)
    self._dialog.vbox.pack_start(self._hbox_apply_to_all, expand=False, fill=False)
    
    self._buttons = {}
    for value, display_name in self.values_and_display_names:
      self._buttons[value] = self._dialog.add_button(display_name, value)
    
    self._dialog.action_area.set_spacing(8)
    
    self._apply_to_all_checkbox.connect("toggled", self._on_apply_to_all_changed)
    
    self._dialog.set_focus(self._buttons[self.default_value])
  
  def _choose(self):
    if self.filename is not None:
      text_filename = "named \"" + self.filename + "\""
    else:
      text_filename = "with the same name"
    self._dialog_text.set_markup("<span font_size=\"large\"><b>A file " + text_filename +
                                 " already exists.\nWhat would you like to do?</b></span>")
    self._dialog.show_all()
    self._overwrite_mode = self._dialog.run()
    if self._overwrite_mode not in self._values:
      self._overwrite_mode = self.default_response
    
    self._dialog.hide()
    
    return self._overwrite_mode
  
  def _on_apply_to_all_changed(self, widget):
    self._is_apply_to_all = self._apply_to_all_checkbox.get_active()

#===============================================================================

def display_exception_message(plugin_title, exc_message, report_uri_list, parent=None):
  
  def connect_linkbuttons():
    def open_browser(linkbutton):
      webbrowser.open_new_tab(linkbutton.get_uri())
    
    for linkbutton in report_linkbuttons:
      linkbutton.connect("clicked", open_browser)
  
  dialog = gtk.MessageDialog(parent, type=gtk.MESSAGE_ERROR, flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT)
  dialog.set_markup("<span font_size=\"large\"><b>Oops! Something went wrong.</b></span>")
  dialog.format_secondary_markup((plugin_title + " encountered an unexpected error and has to close. "
                                  "Sorry about that!"))
  
  expander = gtk.Expander()
  expander.set_use_markup(True)
  expander.set_label("<b>Details</b>")
  
  scrolled_window = gtk.ScrolledWindow()
  scrolled_window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
  scrolled_window.set_size_request(400, 200)
  scrolled_window.set_shadow_type(gtk.SHADOW_IN)
  
  exception_text_view = gtk.TextView()
  exception_text_view.set_editable(False)
  exception_text_view.set_cursor_visible(False)
  exception_text_view.set_pixels_above_lines(1)
  exception_text_view.set_pixels_below_lines(1)
  exception_text_view.set_pixels_inside_wrap(0)
  exception_text_view.set_left_margin(5)
  exception_text_view.set_right_margin(5)
  exception_text_view.get_buffer().set_text(exc_message)
  
  scrolled_window.add(exception_text_view)
  expander.add(scrolled_window)
  
  vbox_labels_report = gtk.VBox(homogeneous=False)
  
  label_report_header = gtk.Label(("To help fix this error, send a report containing the text "
                                   "in the details above to one of the following sites:"))
  label_report_header.set_alignment(0, 0.5)
  label_report_header.set_padding(3, 3)
  label_report_header.set_line_wrap(True)
  label_report_header.set_line_wrap_mode(gtk.WRAP_WORD)
  
  report_linkbuttons = []
  for name, uri in report_uri_list:
    linkbutton = gtk.LinkButton(uri, label=name)
    linkbutton.set_alignment(0, 0.5)
    report_linkbuttons.append(linkbutton)
  
  vbox_labels_report.pack_start(label_report_header, expand=False, fill=True)
  for linkbutton in report_linkbuttons:
    vbox_labels_report.pack_start(linkbutton, expand=False, fill=True)
  
  dialog.vbox.pack_start(expander, expand=False, fill=True)
  dialog.vbox.pack_start(vbox_labels_report, expand=False, fill=True)
  
  button_ok = dialog.add_button(gtk.STOCK_OK, gtk.RESPONSE_OK)
  
  dialog.set_focus(button_ok)
  
  # Apparently, GTK doesn't know how to open URLs on Windows, hence the custom solution. 
  connect_linkbuttons()
  
  dialog.show_all()
  dialog.run()
  dialog.destroy()

def display_warning_message(title, message, parent=None):
  dialog = gtk.MessageDialog(parent=parent, type=gtk.MESSAGE_WARNING,
                             flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                             buttons=gtk.BUTTONS_OK)
  dialog.set_title(title)
  
  messages = message.split('\n', 1)
  
  if len(messages) > 1:
    dialog.set_markup(messages[0])
    dialog.format_secondary_markup(messages[1])
  else:
    dialog.set_markup(message)
  
  dialog.show_all()
  dialog.run()
  dialog.destroy()

#===============================================================================

class GtkProgressUpdater(progress.ProgressUpdater):
  def _fill_progress_bar(self):
    self.progress_bar.set_fraction(float(self._num_finished_tasks) / float(self.num_total_tasks))
  
  def _set_text_progress_bar(self, text):
    self.progress_bar.set_text(text)
  
  def update(self, num_tasks=0, text=None):
    super(GtkProgressUpdater, self).update(num_tasks, text)
    # This is necessary for the GTK progress bar to be updated properly.
    # See http://faq.pygtk.org/index.py?req=show&file=faq23.020.htp
    while gtk.events_pending():
      gtk.main_iteration()

#===============================================================================
  
class GtkSettingPresenter(settings.SettingPresenter):
  
  __metaclass__ = abc.ABCMeta
  
  @property
  def enabled(self):
    return self._element.get_sensitive()
  @enabled.setter
  def enabled(self, value):
    self._element.set_sensitive(value)
  
  @property
  def visible(self):
    return self._element.get_visible()
  @visible.setter
  def visible(self, value):
    self._element.set_visible(value)
  
  def connect_event(self, *args):
    if self.value_changed_signal is not None:
      return self._element.connect(self.value_changed_signal, *args)
    else:
      raise TypeError("cannot connect signal if value_changed_signal is None")

#-------------------------------------------------------------------------------

class GtkCheckButtonPresenter(GtkSettingPresenter):
  
  def __init__(self, setting, element):
    super(GtkCheckButtonPresenter, self).__init__(setting, element)
    
    self.value_changed_signal = "clicked"
    
  @property
  def value(self):
    return self._element.get_active()
  @value.setter
  def value(self, value_):
    self._element.set_active(value_)

class GtkEntryPresenter(GtkSettingPresenter):
  
  @property
  def value(self):
    return self._element.get_text()
  @value.setter
  def value(self, value_):
    self._element.set_text(value_)
    # Place the cursor at the end of the widget.
    self._element.set_position(-1)

class GimpUiIntComboBoxPresenter(GtkSettingPresenter):
  
  def __init__(self, setting, element):
    super(GimpUiIntComboBoxPresenter, self).__init__(setting, element)
    
    self.value_changed_signal = "changed"
  
  @property
  def value(self):
    return self._element.get_active()
  @value.setter
  def value(self, value_):
    self._element.set_active(value_)

class GtkDirectoryChooserWidgetPresenter(GtkSettingPresenter):
  
  def __init__(self, setting, element, image, default_directory):
    super(GtkDirectoryChooserWidgetPresenter, self).__init__(setting, element)
    
    self.image = image
    self.default_directory = default_directory
  
  @property
  def value(self):
    return self._element.get_current_folder()
  @value.setter
  def value(self, value_):
    if value_ is not None:
      self._element.set_current_folder(value_)
    else:
      if self.image.uri is not None:
        self._element.set_uri(self.image.uri)
      else:
        self._element.set_current_folder(self.default_directory)

