# -*- coding: utf-8 -*-
#
# Copyright (C) 2014-2018 khalim19
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
This module defines:
* GTK overwrite dialog
* GTK progress updater
* GTK exception dialog
* GTK generic message dialog
* wrapper for `sys.excepthook` that displays the GTK exception dialog when an
  unhandled exception is raised
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import functools
import os
import sys
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

import gimpui

from . import pgoverwrite
from . import pgprogress

#===============================================================================


class GtkDialogOverwriteChooser(pgoverwrite.InteractiveOverwriteChooser):
  
  """
  This class is used to display a GTK dialog prompt in an interactive
  environment when a file about to be saved has the same name as an already
  existing file.
  """
  
  _DIALOG_BORDER_WIDTH = 8
  _DIALOG_HBOX_CONTENTS_SPACING = 10
  _DIALOG_VBOX_SPACING = 5
  _DIALOG_ACTION_AREA_SPACING = 8
  
  def __init__(
        self, values_and_display_names, default_value, default_response, title="",
        parent=None, use_mnemonics=True):
    
    super().__init__(values_and_display_names, default_value, default_response)
    
    self._title = title
    self._parent = parent
    self._use_mnemonics = use_mnemonics
    
    self._init_gui()
  
  def _init_gui(self):
    self._dialog = gimpui.Dialog(
      title="", role=None, parent=self._parent,
      flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT)
    self._dialog.set_transient_for(self._parent)
    self._dialog.set_title(self._title)
    self._dialog.set_border_width(self._DIALOG_BORDER_WIDTH)
    self._dialog.set_resizable(False)
    
    self._dialog_icon = gtk.Image()
    self._dialog_icon.set_from_stock(gtk.STOCK_DIALOG_QUESTION, gtk.ICON_SIZE_DIALOG)
    
    self._dialog_text = gtk.Label("")
    self._dialog_text.set_line_wrap(True)
    self._dialog_text.set_use_markup(True)
    
    self._dialog_text_event_box = gtk.EventBox()
    self._dialog_text_event_box.add(self._dialog_text)
    
    self._hbox_dialog_contents = gtk.HBox(homogeneous=False)
    self._hbox_dialog_contents.set_spacing(self._DIALOG_HBOX_CONTENTS_SPACING)
    self._hbox_dialog_contents.pack_start(self._dialog_icon, expand=False, fill=False)
    self._hbox_dialog_contents.pack_start(
      self._dialog_text_event_box, expand=False, fill=False)
    
    if self._use_mnemonics:
      label_apply_to_all = _("_Apply action to all files")
    else:
      label_apply_to_all = _("Apply action to all files")
    self._checkbutton_apply_to_all = gtk.CheckButton(label=label_apply_to_all)
    self._checkbutton_apply_to_all.set_use_underline(self._use_mnemonics)
    
    self._dialog.vbox.set_spacing(self._DIALOG_VBOX_SPACING)
    self._dialog.vbox.pack_start(self._hbox_dialog_contents, expand=False, fill=False)
    self._dialog.vbox.pack_start(self._checkbutton_apply_to_all, expand=False, fill=False)
    
    self._buttons = {}
    for value, display_name in self.values_and_display_names:
      self._buttons[value] = self._dialog.add_button(display_name, value)
    
    self._dialog.action_area.set_spacing(self._DIALOG_ACTION_AREA_SPACING)
    
    self._checkbutton_apply_to_all.connect("toggled", self._on_apply_to_all_changed)
    
    self._is_dialog_text_allocated_size = False
    self._dialog_text_event_box.connect(
      "size-allocate", self._on_dialog_text_event_box_size_allocate)
    
    self._dialog.set_focus(self._buttons[self.default_value])
  
  def _choose(self, filepath):
    if filepath is not None:
      dirpath, filename = os.path.split(filepath)
      if dirpath:
        text_choose = (
          _('A file named "{0}" already exists in "{1}". ').format(
            filename, os.path.basename(dirpath)))
      else:
        text_choose = _('A file named "{0}" already exists.\n').format(filename)
    else:
      text_choose = _("A file with the same name already exists.\n")
    
    text_choose += _("What would you like to do?")
    
    self._dialog_text.set_markup(
      '<span font_size="large"><b>{0}</b></span>'.format(
        gobject.markup_escape_text(text_choose)))
    
    self._dialog.show_all()
    
    self._overwrite_mode = self._dialog.run()
    
    if self._overwrite_mode not in self._values:
      self._overwrite_mode = self.default_response
    
    self._dialog.hide()
    
    return self._overwrite_mode
  
  def _on_apply_to_all_changed(self, widget):
    self._is_apply_to_all = self._checkbutton_apply_to_all.get_active()
  
  def _on_dialog_text_event_box_size_allocate(self, dialog_text_event_box, allocation):
    if not self._is_dialog_text_allocated_size:
      self._is_dialog_text_allocated_size = True
      
      # Make sure the label uses as much width as it can in the dialog.
      dialog_text_allocation = dialog_text_event_box.get_allocation()
      dialog_vbox_allocation = self._dialog.vbox.get_allocation()
      self._dialog_text.set_size_request(
        dialog_vbox_allocation.width - dialog_text_allocation.x, -1)


#===============================================================================


class GtkProgressUpdater(pgprogress.ProgressUpdater):
  
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


def display_error_message(
      title=None, app_name=None, parent=None, message_type=gtk.MESSAGE_ERROR,
      flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
      message_markup=None, message_secondary_markup=None,
      details=None, display_details_initially=True,
      report_uri_list=None, report_description=None,
      button_stock_id=gtk.STOCK_CLOSE, button_response_id=gtk.RESPONSE_CLOSE,
      focus_on_button=False):
  """
  Display a message to alert the user about an error or an exception that
  occurred in the application.
  
  Parameters:
  
  * `title` - Message title.
  
  * `app_name` - Name of the application to use in the default contents of
    `message_secondary_markup`.
  
  * `parent` - Parent widget.
  
  * `message_type` - GTK message type (gtk.MESSAGE_ERROR, etc.).
  
  * `flags` - GTK dialog flags.
  
  * `message_markup` - Primary message text to display as markup.
  
  * `message_secondary_markup` - Secondary message text to display as markup.
  
  * `details` - Text to display in a box with details. If None, do not display
    any box.
  
  * `display_details_initially` - If True, display the details by default,
    otherwise hide them in an expander.
  
  * `report_uri_list` - List of (name, URL) pairs where the user can report
    the error. If no report list is desired, pass None or an empty sequence.
  
  * `report_description` - Text accompanying `report_uri_list`. If None, use
    default text. To suppress displaying the report description, pass an empty
    string.
  
  * `button_stock_id` - Stock ID of the button to close the dialog with.
  
  * `button_response_id` - Response ID of the button to close the dialog with.
  
  * `focus_on_button` - If True, focus on the button to close the dialog with.
    If False, focus on the box with details if `details` is not None, otherwise
    let the message dialog determine the focus widget.
  """
  
  if message_markup is None:
    message_markup = (
      '<span font_size="large"><b>{0}</b></span>'.format(
        _("Oops. Something went wrong.")))
  
  if message_secondary_markup is None:
    message_secondary_markup = _(
      "{0} encountered an unexpected error and has to close. Sorry about that!").format(
        gobject.markup_escape_text(app_name))
  
  if report_description is None:
    report_description = _(
      "You can help fix this error by sending a report with the text "
      "in the details above to one of the following sites")
  
  dialog = gtk.MessageDialog(parent, type=message_type, flags=flags)
  dialog.set_transient_for(parent)
  if title is not None:
    dialog.set_title(title)
  
  dialog.set_markup(message_markup)
  dialog.format_secondary_markup(message_secondary_markup)
  
  if details is not None:
    expander = _get_details_expander(details)
    if display_details_initially:
      expander.set_expanded(True)
  else:
    expander = None
  
  if report_uri_list:
    vbox_labels_report = _get_report_link_buttons(
      report_uri_list, report_description=report_description)
    dialog.vbox.pack_end(vbox_labels_report, expand=False, fill=False)
  
  if expander is not None:
    dialog.vbox.pack_start(expander, expand=False, fill=False)
  
  dialog.add_button(button_stock_id, button_response_id)
  
  if focus_on_button:
    button = dialog.get_widget_for_response(button_response_id)
    if button is not None:
      dialog.set_focus(button)
  else:
    if (expander is not None
        and expander.get_child() is not None
        and display_details_initially):
      dialog.set_focus(expander.get_child())
  
  dialog.show_all()
  response_id = dialog.run()
  dialog.destroy()
  
  return response_id


def _get_details_expander(details_text):
  expander = gtk.Expander()
  expander.set_use_markup(True)
  expander.set_label("<b>" + _("Details") + "</b>")
  
  scrolled_window = gtk.ScrolledWindow()
  scrolled_window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
  scrolled_window.set_size_request(400, 200)
  scrolled_window.set_shadow_type(gtk.SHADOW_IN)
  
  exception_text_view = gtk.TextView()
  exception_text_view.set_editable(False)
  exception_text_view.set_wrap_mode(gtk.WRAP_WORD)
  exception_text_view.set_cursor_visible(False)
  exception_text_view.set_pixels_above_lines(1)
  exception_text_view.set_pixels_below_lines(1)
  exception_text_view.set_pixels_inside_wrap(0)
  exception_text_view.set_left_margin(5)
  exception_text_view.set_right_margin(5)
  exception_text_view.get_buffer().set_text(details_text)
  
  scrolled_window.add(exception_text_view)
  expander.add(scrolled_window)
  
  return expander


def _get_report_link_buttons(report_uri_list, report_description=None):
  if not report_uri_list:
    return None
  
  vbox_link_buttons = gtk.VBox(homogeneous=False)
  
  if report_description:
    label_report_text = report_description
    if not _webbrowser_module_found:
      label_report_text += " " + _("(right-click to copy link)")
    label_report_text += ":"
    
    label_report = gtk.Label(label_report_text)
    label_report.set_alignment(0, 0.5)
    label_report.set_padding(3, 3)
    label_report.set_line_wrap(True)
    label_report.set_line_wrap_mode(pango.WRAP_WORD)
    vbox_link_buttons.pack_start(label_report, expand=False, fill=False)
  
  report_linkbuttons = []
  for name, uri in report_uri_list:
    linkbutton = gtk.LinkButton(uri, label=name)
    linkbutton.set_alignment(0, 0.5)
    report_linkbuttons.append(linkbutton)
  
  for linkbutton in report_linkbuttons:
    vbox_link_buttons.pack_start(linkbutton, expand=False, fill=False)
  
  if _webbrowser_module_found:
    # Apparently, GTK doesn't know how to open URLs on Windows, hence the custom
    # solution.
    for linkbutton in report_linkbuttons:
      linkbutton.connect(
        "clicked", lambda linkbutton: webbrowser.open_new_tab(linkbutton.get_uri()))
  
  return vbox_link_buttons


def display_message(
      message, message_type, title=None, parent=None, buttons=gtk.BUTTONS_OK,
      message_in_text_view=False, button_response_id_to_focus=None):
  """
  Display a generic message.
  
  Parameters:
  
  * `message` - The message to display.
  
  * `message_type` - GTK message type (gtk.MESSAGE_INFO, etc.).
  
  * `title` - Message title.
  
  * `parent` - Parent GUI element.
  
  * `buttons` - Buttons to display in the dialog.
  
  * `message_in_text_view` - If True, display text the after the first newline
    character in a text view.
  
  * `button_response_id_to_focus` - Response ID of the button to set as the
    focus. If None, the dialog determines which widget gets the focus.
  """
  
  dialog = gtk.MessageDialog(
    parent=parent, type=message_type,
    flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=buttons)
  dialog.set_transient_for(parent)
  if title is not None:
    dialog.set_title(title)
  
  messages = message.split("\n", 1)
  if len(messages) > 1:
    dialog.set_markup(gobject.markup_escape_text(messages[0]))
    
    if message_in_text_view:
      text_view = gtk.TextView()
      text_view.set_editable(False)
      text_view.set_wrap_mode(gtk.WRAP_WORD)
      text_view.set_cursor_visible(False)
      text_view.set_pixels_above_lines(1)
      text_view.set_pixels_below_lines(1)
      text_view.set_pixels_inside_wrap(0)
      text_view.get_buffer().set_text(messages[1])
      
      scrolled_window = gtk.ScrolledWindow()
      scrolled_window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
      scrolled_window.set_size_request(-1, 100)
      scrolled_window.set_shadow_type(gtk.SHADOW_IN)
      
      scrolled_window.add(text_view)
      
      vbox = dialog.get_message_area()
      vbox.pack_end(scrolled_window, expand=True, fill=True)
    else:
      dialog.format_secondary_markup(gobject.markup_escape_text(messages[1]))
  else:
    dialog.set_markup(gobject.markup_escape_text(message))
  
  if button_response_id_to_focus is not None:
    button = dialog.get_widget_for_response(button_response_id_to_focus)
    if button is not None:
      dialog.set_focus(button)
  
  dialog.show_all()
  response_id = dialog.run()
  dialog.destroy()
  
  return response_id


#===============================================================================

_gui_excepthook_parent = None


def set_gui_excepthook(title, app_name, report_uri_list=None, parent=None):
  """
  Modify `sys.excepthook` to display an error dialog for unhandled exceptions.
  
  Don't display the dialog for exceptions which are not subclasses of
  `Exception` (such as `SystemExit or `KeyboardInterrupt`).
  
  Parameters:
  
  * `title` - Dialog title.
  
  * `report_uri_list` - List of (name, URL) tuples where the user can report
    the error. If no report list is desired, pass None or an empty sequence.
  
  * `parent` - Parent GUI element.
  """
  
  global _gui_excepthook_parent
  
  _gui_excepthook_parent = parent
  
  def gui_excepthook(func):
    
    @functools.wraps(func)
    def func_wrapper(self, *args, **kwargs):
      
      def _gui_excepthook(exc_type, exc_value, exc_traceback):
        orig_sys_excepthook(exc_type, exc_value, exc_traceback)
        
        if issubclass(exc_type, Exception):
          exception_message = "".join(
            traceback.format_exception(exc_type, exc_value, exc_traceback))
          
          display_error_message(
            title=title, app_name=app_name, parent=_gui_excepthook_parent,
            details=exception_message, report_uri_list=report_uri_list)
          
          # Make sure to quit the application since unhandled exceptions can
          # mess up the application state.
          if gtk.main_level() > 0:
            gtk.main_quit()
      
      orig_sys_excepthook = sys.excepthook
      sys.excepthook = _gui_excepthook
      
      func(self, *args, **kwargs)
      
      sys.excepthook = orig_sys_excepthook
  
    return func_wrapper
  
  return gui_excepthook


def set_gui_excepthook_parent(parent):
  """
  Set the parent GUI element to attach the exception dialog to when using
  `set_gui_excepthook`. This function allows to modify the parent dynamically
  even after decorating a function with `set_gui_excepthook`.
  """
  
  global _gui_excepthook_parent
  
  _gui_excepthook_parent = parent


#===============================================================================


def get_toplevel_window(widget):
  """
  Return the toplevel window (`gtk.Window`) for the specified widget
  (`gtk.Widget`). If the widget has no toplevel window, return None.
  """
  
  toplevel_widget = widget.get_toplevel()
  if toplevel_widget.flags() & gtk.TOPLEVEL:
    return toplevel_widget
  else:
    return None
