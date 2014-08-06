#-------------------------------------------------------------------------------
#
# This file is part of pylibgimpplugin.
#
# Copyright (C) 2014 khalim19 <khalim19@gmail.com>
# 
# pylibgimpplugin is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# pylibgimpplugin is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with pylibgimpplugin.  If not, see <http://www.gnu.org/licenses/>.
#
#-------------------------------------------------------------------------------

"""
This module defines:
* GTK overwrite dialog
* GTK progress updater
* GTK exception message
* GTK generic message
* context manager for `sys.excepthook` that displays GTK exception message when
  an unhandled exception is raised
* SettingPresenter subclasses for GTK elements
* SettingPresenterContainer subclass for GTK elements
"""

#===============================================================================

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division

str = unicode

#===============================================================================

import sys
import traceback
from contextlib import contextmanager
import abc
import webbrowser

import pygtk
pygtk.require("2.0")
import gtk

import gimp
import gimpui

from . import settings
from . import overwrite
from . import progress

#===============================================================================

pdb = gimp.pdb

GTK_CHARACTER_ENCODING = "utf-8"

#===============================================================================
# GTK Overwrite Chooser
#===============================================================================

class GtkDialogOverwriteChooser(overwrite.InteractiveOverwriteChooser):
  
  """
  This class is used to display a GTK dialog prompt in an interactive environment
  when a file about to be saved has the same name as an already existing file.
  """
  
  def __init__(self, values_and_display_names, default_value, default_response, title=""):
    
    super(GtkDialogOverwriteChooser, self).__init__(values_and_display_names, default_value, default_response)
    
    self._title = title
    self._values = [value for value, unused_ in self.values_and_display_names]
    
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
    self._apply_to_all_checkbox = gtk.CheckButton(label=_("Apply action to all files"))
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
  
  def _choose(self, filename):
    if filename is not None:
      text_filename = _("A file named \"{0}\" already exists.\nWhat would you like to do?").format(filename)
    else:
      text_filename = _("A file with the same name already exists.\nWhat would you like to do?")
    self._dialog_text.set_markup("<span font_size=\"large\"><b>" + text_filename + "</b></span>")
    self._dialog.show_all()
    self._overwrite_mode = self._dialog.run()
    if self._overwrite_mode not in self._values:
      self._overwrite_mode = self.default_response
    
    self._dialog.hide()
    
    return self._overwrite_mode
  
  def _on_apply_to_all_changed(self, widget):
    self._is_apply_to_all = self._apply_to_all_checkbox.get_active()

#===============================================================================
# GTK Message Dialogs
#===============================================================================

def display_exception_message(exception_message, plugin_title=None,
                              report_uri_list=None, parent=None):
  
  """
  Display an error message for exceptions unhandled by the plug-in.
  
  The message also displays the exception message in the Details box, which
  is collapsed by default.
  
  Optionally, the dialog can contain links to sites where the users can report
  this error, copying the exception message to better track the error down.
  
  Parameters:
  
  * `exception_message` - Exception message (usually traceback) to display in
    the Details box.
  
  * `plugin_title` - Name of the plug-in (string) used as the message title and
    in the message contents.
  
  * `report_uri_list` - List of (name, URL) tuples where the user can report
    the error. If no report list is desired, pass None or an empty sequence.
  
  * `parent` - Parent GUI element.
  """
  
  def connect_linkbuttons(report_linkbuttons):
    
    def open_browser(linkbutton):
      webbrowser.open_new_tab(linkbutton.get_uri())
    
    for linkbutton in report_linkbuttons:
      linkbutton.connect("clicked", open_browser)
  
  
  dialog = gtk.MessageDialog(parent, type=gtk.MESSAGE_ERROR, flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT)
  dialog.set_markup(
    "<span font_size=\"large\"><b>" + _("Oops! Something went wrong.") + "</b></span>"
  )
  dialog.format_secondary_markup(
    _("{0} encountered an unexpected error and has to close. Sorry about that!").format(plugin_title)
  )
  dialog.set_title(plugin_title)
  
  expander = gtk.Expander()
  expander.set_use_markup(True)
  expander.set_label("<b>" + _("Details") + "</b>")
  
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
  exception_text_view.get_buffer().set_text(exception_message)
  
  scrolled_window.add(exception_text_view)
  expander.add(scrolled_window)
  
  vbox_labels_report = gtk.VBox(homogeneous=False)
  
  if report_uri_list is not None and report_uri_list:
    label_report_header = gtk.Label(
      _("To help fix this error, send a report containing the text "
        "in the details above to one of the following sites:")
    )
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
  
    dialog.vbox.pack_end(vbox_labels_report, expand=False, fill=True)
  
  dialog.vbox.pack_start(expander, expand=False, fill=True)
  
  button_ok = dialog.add_button(gtk.STOCK_OK, gtk.RESPONSE_OK)
  
  dialog.set_focus(button_ok)
  
  if report_uri_list is not None and report_uri_list:
    # Apparently, GTK doesn't know how to open URLs on Windows, hence the custom
    # solution. 
    connect_linkbuttons(report_linkbuttons)
  
  dialog.show_all()
  dialog.run()
  dialog.destroy()


def display_message(message, message_type, title=None, parent=None):
  
  """
  Display a generic message.
  
  Parameters:
  
  * `message` - The message to display.
  
  * `message_type` - GTK message type (gtk.INFO, gtk.WARNING, etc.).
  
  * `title` - Message title.
  
  * `parent` - Parent GUI element.
  """
  
  dialog = gtk.MessageDialog(parent=parent, type=message_type,
                             flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                             buttons=gtk.BUTTONS_OK)
  if title is not None:
    dialog.set_title(title)
  dialog.set_transient_for(parent)
  
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
# GUI excepthook
#===============================================================================

@contextmanager
def set_gui_excepthook(plugin_title, report_uri_list=None, parent=None):
  
  """
  Modify `sys.excepthook` to display an error dialog for unhandled exceptions.
  
  Don't display the dialog for exceptions which are not subclasses of
  `Exception` (such as `SystemExit or `KeyboardInterrupt`).
  
  Use this function as a context manager:
    
    with set_gui_excepthook():
      # do stuff
  
  Parameters:
  
  * `plugin_title` - Name of the plug-in (string) used as the dialog title and
    in the dialog contents.
  
  * `report_uri_list` - List of (name, URL) tuples where the user can report
    the error. If no report list is desired, pass None or an empty sequence.
  
  * `parent` - Parent GUI element.
  """
  
  def _gui_excepthook(exc_type, exc_value, exc_traceback):
    
    if issubclass(exc_type, Exception):
      exception_message = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
      display_exception_message(exception_message, plugin_title=plugin_title,
                                report_uri_list=report_uri_list, parent=parent)
      # Make sure to quit the plug-in since unhandled exceptions
      # can mess up the plug-in state.
      if gtk.main_level() > 0:
        gtk.main_quit()
    
    _orig_sys_excepthook(exc_type, exc_value, exc_traceback)
  
  
  _orig_sys_excepthook = sys.excepthook
  sys.excepthook = _gui_excepthook
  
  # Unlike other functions or methods with the `contextmanager` decorator,
  # here the `yield` keyword must not be wrapped in a try-finally block.
  # I don't understand why, though. Somehow, the `finally` block would be
  # executed before `_gui_excepthook` had a chance to kick in.
  yield
  
  sys.excepthook = _orig_sys_excepthook

#===============================================================================
# GTK Progress Updater
#===============================================================================

class GtkProgressUpdater(progress.ProgressUpdater):
  
  def _fill_progress_bar(self):
    self.progress_bar.set_fraction(self._num_finished_tasks / self.num_total_tasks)
    self._force_update()
  
  def _set_text_progress_bar(self, text):
    self.progress_bar.set_text(text)
    self._force_update()
  
  def _force_update(self):
    # This is necessary for the GTK progress bar to be updated properly.
    # See http://faq.pygtk.org/index.py?req=show&file=faq23.020.htp
    while gtk.events_pending():
      gtk.main_iteration()

#===============================================================================
# Custom GTK/gimpui Elements
#===============================================================================

class IntComboBox(gimpui.IntComboBox):
  
  """
  This class is a `gimpui.IntComboBox` subclass that encodes unicode strings
  before initializing `gimpui.IntComboBox`. Apparently, `gimpui.IntComboBox`
  can only handle bytes, not unicode strings.
  """
  
  def __init__(self, labels_and_values):
    """
    Parameters:
    
    * `labels_and_values` - List of (`unicode`, `int`) pairs.
    """
    
    for i in range(0, len(labels_and_values), 2):
      labels_and_values[i] = labels_and_values[i].encode(GTK_CHARACTER_ENCODING)
    
    super(IntComboBox, self).__init__(tuple(labels_and_values))

#===============================================================================
# GTK Setting Presenters
#===============================================================================
  
class GtkSettingPresenter(settings.SettingPresenter):
  
  """
  This class is a SettingPresenter subclass suitable for GTK GUI elements.
  """
  
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
  
  def connect_event(self, event_func, *event_args):
    if self.value_changed_signal is not None:
      return self._element.connect(self.value_changed_signal, event_func, *event_args)
    else:
      raise TypeError("cannot connect signal if value_changed_signal is None")
  
  def set_tooltip(self):
    if self._setting.description is not None and self._setting.description:
      self._element.set_tooltip_text(self._setting.description)
  
#-------------------------------------------------------------------------------

class GtkCheckButtonPresenter(GtkSettingPresenter):
  
  """
  This class is a `SettingPresenter` for `gtk.CheckButton` elements.
  
  Value: Checked state of the checkbox (checked/unchecked).
  """
  
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
  
  """
  This class is a `SettingPresenter` for `gtk.Entry` elements (text fields).
  
  Value: Text in the text field.
  """
  
  @property
  def value(self):
    return self._element.get_text().decode(GTK_CHARACTER_ENCODING)
  
  @value.setter
  def value(self, value_):
    self._element.set_text(value_.encode(GTK_CHARACTER_ENCODING))
    # Place the cursor at the end of the widget.
    self._element.set_position(-1)


class GimpUiIntComboBoxPresenter(GtkSettingPresenter):
  
  """
  This class is a `SettingPresenter` for `gimpui.IntComboBox` elements.
  
  Value: Option selected in the combobox.
  """
  
  def __init__(self, setting, element):
    super(GimpUiIntComboBoxPresenter, self).__init__(setting, element)
    
    self.value_changed_signal = "changed"
  
  @property
  def value(self):
    return self._element.get_active()
  
  @value.setter
  def value(self, value_):
    self._element.set_active(value_)


class GtkExportDialogDirectoryChooserWidgetPresenter(GtkSettingPresenter):
  
  """
  This class is a `SettingPresenter` for `gtk.FileChooserWidget` elements
  used as directory choosers for export dialogs.
  
  Value: Current directory.
  
  The current directory is determined for each image currently opened in GIMP
  separately, according to the following priority list:
  
    1. Last export directory of the current image
    2. Import path for the current image
    3. XCF path for the current image
    4. Last export directory of any image
    5. The default directory (the OS 'Documents' directory)
  
  Attributes:
  
  * `image_ids_and_directories_setting` - a `Setting` object whose value is a
    dict of <`gimp.Image`, directory name> pairs.
  
  * `current_image` - Current `gimp.Image` object.
  """
  
  def __init__(self, setting, element, image_ids_and_directories_setting, current_image):
    super(GtkExportDialogDirectoryChooserWidgetPresenter, self).__init__(setting, element)
    
    self._image_ids_and_directories_setting = image_ids_and_directories_setting
    self.current_image = current_image
    
    self._set_image_ids_and_directories()
  
  @property
  def value(self):
    directory = self._element.get_current_folder()
    if directory is not None:
      directory = directory.decode(GTK_CHARACTER_ENCODING)
    
    self._image_ids_and_directories_setting.value[self.current_image.ID] = directory
    
    return directory
  
  @value.setter
  def value(self, value_):
    """
    `value_` parameter will be ignored if there is a value for directories
    1., 2. or 3. from the priority list (see the class description).
    """
    
    directory = self._image_ids_and_directories_setting.value[self.current_image.ID]
    
    if directory is not None:
      self._element.set_current_folder(directory.encode(GTK_CHARACTER_ENCODING))
    else:
      uri = pdb.gimp_image_get_imported_uri(self.current_image)
      if uri is None:
        uri = pdb.gimp_image_get_xcf_uri(self.current_image)
      
      if uri is not None:
        self._element.set_uri(uri.encode(GTK_CHARACTER_ENCODING))
      else:
        self._element.set_current_folder(value_.encode(GTK_CHARACTER_ENCODING))
  
  def _set_image_ids_and_directories(self):
    setting = self._image_ids_and_directories_setting
    
    current_image_ids = set([image.ID for image in gimp.image_list()])
    setting.value = {
      image_id : setting.value[image_id]
      for image_id in setting.value.keys() if image_id in current_image_ids
    }
    for image_id in current_image_ids:
      if image_id not in setting.value.keys():
        setting.value[image_id] = None
    

class GtkWindowPositionPresenter(GtkSettingPresenter):
  
  """
  This class is a `SettingPresenter` for window or dialog elements
  (`gtk.Window`, `gtk.Dialog`) to get/set its position.
  
  Value: Current position of the window as a tuple with 2 integers.
  """
  
  @property
  def value(self):
    return self._element.get_position()
  
  @value.setter
  def value(self, value_):
    """
    Set new position of the window (i.e. move the window).
    
    Don't move the window if `value_` is None or empty.
    """
    
    if value_ and value_ is not None:
      self._element.move(*value_)


class GtkExpanderPresenter(GtkSettingPresenter):
  
  """
  This class is a `SettingPresenter` for `gtk.Expander` elements.
  
  Value: Expanded state of the expander (expanded/collapsed).
  """
  
  @property
  def value(self):
    return self._element.get_expanded()
  
  @value.setter
  def value(self, value_):
    self._element.set_expanded(value_)

#===============================================================================
# GTK Setting Presenter Container
#===============================================================================

class GtkSettingPresenterContainer(settings.SettingPresenterContainer):
  
  """
  This class is used to group `SettingPresenter` objects in a GTK environment.
  """
  
  def _gui_on_element_value_change(self, widget, presenter, *args):
    self._on_element_value_change(presenter)
  
  def _gui_on_element_value_change_streamline(self, widget, presenter, *args):
    self._on_element_value_change_streamline(presenter)
