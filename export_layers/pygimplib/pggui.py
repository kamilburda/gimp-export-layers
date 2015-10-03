#-------------------------------------------------------------------------------
#
# This file is part of pygimplib.
#
# Copyright (C) 2014, 2015 khalim19 <khalim19@gmail.com>
#
# pygimplib is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pygimplib is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pygimplib.  If not, see <http://www.gnu.org/licenses/>.
#
#-------------------------------------------------------------------------------

"""
This module defines:
* GTK overwrite dialog
* GTK progress updater
* GTK exception dialog
* GTK generic message dialog
* wrapper for `sys.excepthook` that displays the GTK exception dialog when an
  unhandled exception is raised
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
import functools

try:
  import webbrowser
except ImportError:
  _webbrowser_module_found = False
else:
  _webbrowser_module_found = True

import pygtk

pygtk.require("2.0")

import gtk

import gimp
import gimpui

from . import overwrite
from . import progress

from .pggui_fileextension import FileExtensionEntry

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
  
  def __init__(self, values_and_display_names, default_value, default_response, title="",
               use_mnemonics=True):
    
    super(GtkDialogOverwriteChooser, self).__init__(values_and_display_names, default_value, default_response)
    
    self._title = title
    self._use_mnemonics = use_mnemonics
    
    self._init_gui()
  
  def _init_gui(self):
    self._dialog = gimpui.Dialog(title="", role=None)
    self._dialog.set_transient()
    self._dialog.set_border_width(8)
    self._dialog.set_resizable(False)
    self._dialog.set_title(self._title)
    
    self._dialog_icon = gtk.Image()
    self._dialog_icon.set_from_stock(gtk.STOCK_DIALOG_QUESTION, gtk.ICON_SIZE_DIALOG)
    self._dialog_text = gtk.Label("")
    
    self._hbox_dialog_contents = gtk.HBox(homogeneous=False)
    self._hbox_dialog_contents.set_spacing(10)
    self._hbox_dialog_contents.pack_start(self._dialog_icon, expand=False, fill=False)
    self._hbox_dialog_contents.pack_start(self._dialog_text, expand=False, fill=False)
    
    if self._use_mnemonics:
      apply_to_all_checkbox_label = _("_Apply action to all files")
    else:
      apply_to_all_checkbox_label = _("Apply action to all files")
    self._apply_to_all_checkbox = gtk.CheckButton(label=apply_to_all_checkbox_label)
    self._apply_to_all_checkbox.set_use_underline(self._use_mnemonics)
    
    self._hbox_apply_to_all = gtk.HBox(homogeneous=False)
    self._hbox_apply_to_all.set_spacing(5)
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
  
  dialog = gtk.MessageDialog(parent, type=gtk.MESSAGE_ERROR,
                             flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT)
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
    label_report_header_text = _("You can help fix this error by sending a report with the text "
                                 "in the details above to one of the following sites")
    if not _webbrowser_module_found:
      label_report_header_text += " " + _("(right-click to copy link)")
    label_report_header_text += ":"
    
    label_report_header = gtk.Label(label_report_header_text)
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
  
  if report_uri_list is not None and report_uri_list and _webbrowser_module_found:
    # Apparently, GTK doesn't know how to open URLs on Windows, hence the custom
    # solution.
    connect_linkbuttons(report_linkbuttons)
  
  dialog.show_all()
  dialog.run()
  dialog.destroy()


def display_message(message, message_type, title=None, parent=None, buttons=gtk.BUTTONS_OK):
  
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
                             buttons=buttons)
  if title is not None:
    dialog.set_title(title)
  dialog.set_transient_for(parent)
  
  messages = message.split("\n", 1)
  if len(messages) > 1:
    dialog.set_markup(messages[0])
    dialog.format_secondary_markup(messages[1])
  else:
    dialog.set_markup(message)
  
  dialog.show_all()
  response_id = dialog.run()
  dialog.destroy()
  
  return response_id


#===============================================================================
# GUI excepthook
#===============================================================================


def set_gui_excepthook(plugin_title, report_uri_list=None, parent=None):
  """
  Modify `sys.excepthook` to display an error dialog for unhandled exceptions.
  
  Don't display the dialog for exceptions which are not subclasses of
  `Exception` (such as `SystemExit or `KeyboardInterrupt`).
  
  Parameters:
  
  * `plugin_title` - Name of the plug-in (string) used as the dialog title and
    in the dialog contents.
  
  * `report_uri_list` - List of (name, URL) tuples where the user can report
    the error. If no report list is desired, pass None or an empty sequence.
  
  * `parent` - Parent GUI element.
  """
  
  def real_decorator(func):
    
    @functools.wraps(func)
    def func_wrapper(self, *args, **kwargs):
      
      def gui_excepthook(exc_type, exc_value, exc_traceback):
        orig_sys_excepthook(exc_type, exc_value, exc_traceback)
        
        if issubclass(exc_type, Exception):
          exception_message = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
          display_exception_message(exception_message, plugin_title=plugin_title,
                                    report_uri_list=report_uri_list, parent=parent)
          # Make sure to quit the application since unhandled exceptions can
          # mess up the application state.
          if gtk.main_level() > 0:
            gtk.main_quit()
      
      orig_sys_excepthook = sys.excepthook
      sys.excepthook = gui_excepthook
      
      func(self, *args, **kwargs)
      
      sys.excepthook = orig_sys_excepthook
  
    return func_wrapper
  
  return real_decorator


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
  This class is a `gimpui.IntComboBox` subclass that encodes `unicode` strings
  before initializing `gimpui.IntComboBox`. Apparently, `gimpui.IntComboBox`
  can only handle bytes, not `unicode` strings.
  """
  
  def __init__(self, labels_and_values):
    """
    Parameters:
    
    * `labels_and_values` - List of (`unicode`, `int`) pairs.
    """
    
    for i in range(0, len(labels_and_values), 2):
      labels_and_values[i] = labels_and_values[i].encode(GTK_CHARACTER_ENCODING)
    
    super(IntComboBox, self).__init__(tuple(labels_and_values))
