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
* miscellaneous helper functions dealing with the GUI

This module also includes functions and classes defined in `_pggui_*` modules.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import os

import pygtk
pygtk.require("2.0")
import gtk
import gobject

import gimpui

from . import pgoverwrite
from . import pgprogress

from ._pggui_cellrenderers import *
from ._pggui_entries import *
from ._pggui_entrypopup import *
from ._pggui_messages import *
from ._pggui_undocontext import *


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
        self,
        values_and_display_names,
        default_value,
        default_response, title="",
        parent=None,
        use_mnemonics=True):
    
    super().__init__(values_and_display_names, default_value, default_response)
    
    self._title = title
    self._parent = parent
    self._use_mnemonics = use_mnemonics
    
    self._init_gui()
  
  def _init_gui(self):
    self._dialog = gimpui.Dialog(
      title="",
      role=None,
      parent=self._parent,
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
          _('A file named "{}" already exists in "{}". ').format(
            filename, os.path.basename(dirpath)))
      else:
        text_choose = _('A file named "{}" already exists.\n').format(filename)
    else:
      text_choose = _("A file with the same name already exists.\n")
    
    text_choose += _("What would you like to do?")
    
    self._dialog_text.set_markup(
      '<span font_size="large"><b>{}</b></span>'.format(
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
      
      # Make sure the label uses as much width as possible in the dialog.
      dialog_text_allocation = dialog_text_event_box.get_allocation()
      dialog_vbox_allocation = self._dialog.vbox.get_allocation()
      self._dialog_text.set_size_request(
        dialog_vbox_allocation.width - dialog_text_allocation.x, -1)


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
