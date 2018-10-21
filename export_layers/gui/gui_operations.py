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
This module defines the means to graphically edit a list of operations executed
in the plug-in.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import pygtk
pygtk.require("2.0")
import gtk
import gobject
import pango

from gimp import pdb
import gimpui

from export_layers import pygimplib
from export_layers.pygimplib import pgconstants
from export_layers.pygimplib import pggui
from export_layers.pygimplib import pgutils

from .. import operations


class OperationBox(pggui.ItemBox):
  
  _ADD_BUTTON_HBOX_SPACING = 6
  
  def __init__(
        self,
        operations_group=None,
        label_add_text=None,
        item_spacing=pggui.ItemBox.ITEM_SPACING,
        *args,
        **kwargs):
    super().__init__(item_spacing=item_spacing, *args, **kwargs)
    
    self._operations = operations_group
    self._label_add_text = label_add_text
    
    self.on_add_item = pgutils.empty_func
    self.on_reorder_item = pgutils.empty_func
    self.on_remove_item = pgutils.empty_func
    
    self._procedure_browser_dialog = None
    self._operation_edit_dialog = _OperationEditDialog(
      title=None,
      role=pygimplib.config.PLUGIN_NAME)
    
    self._init_gui()
  
  def _init_gui(self):
    if self._label_add_text is not None:
      self._button_add = gtk.Button()
      button_hbox = gtk.HBox()
      button_hbox.set_spacing(self._ADD_BUTTON_HBOX_SPACING)
      button_hbox.pack_start(
        gtk.image_new_from_stock(gtk.STOCK_ADD, gtk.ICON_SIZE_MENU),
        expand=False, fill=False)
      
      label_add = gtk.Label(
        self._label_add_text.encode(pgconstants.GTK_CHARACTER_ENCODING))
      label_add.set_use_underline(True)
      button_hbox.pack_start(label_add, expand=False, fill=False)
      
      self._button_add.add(button_hbox)
    else:
      self._button_add = gtk.Button(stock=gtk.STOCK_ADD)
    
    self._button_add.set_relief(gtk.RELIEF_NONE)
    self._button_add.connect("clicked", self._on_button_add_clicked)
    
    self._vbox.pack_start(self._button_add, expand=False, fill=False)
    
    self._operations_menu = gtk.Menu()
    self._init_operations_menu_popup()
  
  def add_item(self, operation_name):
    operation = self.on_add_item(self._operations, operation_name)
    operation.initialize_gui()
    
    item = _OperationItem(operation, operation["enabled"].gui.element)
    
    self._add_item(item)
    
    return item
  
  def reorder_item(self, item, new_position):
    processed_new_position = self._reorder_item(item, new_position)
    self.on_reorder_item(self._operations, item.operation.name, processed_new_position)
  
  def remove_item(self, item):
    if self._get_item_position(item) == len(self._items) - 1:
      self._button_add.grab_focus()
    
    self._remove_item(item)
    
    self.on_remove_item(self._operations, item.operation.name)
  
  def _init_operations_menu_popup(self):
    for operation in operations.walk(self._operations, subgroup="builtin"):
      self._add_operation_to_menu_popup(operation)
    
    self._operations_menu.append(gtk.SeparatorMenuItem())
    
    self._add_add_custom_procedure_to_menu_popup()
    
    self._operations_menu.show_all()
  
  def _on_button_add_clicked(self, button):
    self._operations_menu.popup(None, None, None, 0, 0)
  
  def _add_operation_to_menu_popup(self, operation):
    menu_item = gtk.MenuItem(
      label=operation["display_name"].value.encode(pgconstants.GTK_CHARACTER_ENCODING),
      use_underline=False)
    menu_item.connect("activate", self._on_operations_menu_item_activate, operation.name)
    self._operations_menu.append(menu_item)
  
  def _on_operations_menu_item_activate(self, menu_item, operation_name):
    self.add_item(operation_name)
  
  def _add_add_custom_procedure_to_menu_popup(self):
    menu_item = gtk.MenuItem(
      label=_("Add custom procedure..."),
      use_underline=False)
    menu_item.connect("activate", self._on_add_custom_procedure_menu_item_activate)
    self._operations_menu.append(menu_item)
  
  def _on_add_custom_procedure_menu_item_activate(self, menu_item):
    if self._procedure_browser_dialog:
      if not self._operation_edit_dialog.get_mapped():
        self._procedure_browser_dialog.show()
      else:
        self._operation_edit_dialog.present()
    else:
      self._procedure_browser_dialog = self._create_procedure_browser_dialog()
  
  def _create_procedure_browser_dialog(self):
    dialog = gimpui.ProcBrowserDialog(
      _("Procedure Browser"),
      role=pygimplib.config.PLUGIN_NAME,
      buttons=(gtk.STOCK_ADD, gtk.RESPONSE_OK, gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
    
    dialog.set_default_response(gtk.RESPONSE_OK)
    dialog.set_alternative_button_order((gtk.RESPONSE_OK, gtk.RESPONSE_CANCEL))
    
    dialog.connect("response", self._on_procedure_browser_dialog_response)
    
    dialog.show_all()
    
    return dialog
  
  def _on_procedure_browser_dialog_response(self, dialog, response_id):
    if response_id == gtk.RESPONSE_OK:
      procedure_name = dialog.get_selected()
      if procedure_name:
        self._operation_edit_dialog.set_contents(self._operations, pdb[procedure_name])
        self._operation_edit_dialog.show_all()
    
    dialog.hide()


class _OperationItem(pggui.ItemBoxItem):
  
  def __init__(self, operation, item_widget):
    super().__init__(item_widget)
    
    self._operation = operation
  
  @property
  def operation(self):
    return self._operation


class _OperationEditDialog(gimpui.Dialog):
  
  _DIALOG_BORDER_WIDTH = 8
  _ACTION_AREA_BORDER_WIDTH = 5
  _DIALOG_HEIGHT = 500
  
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    
    self.set_transient()
    
    self.add_buttons(gtk.STOCK_OK, gtk.RESPONSE_OK, gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
    
    self._label_procedure_name = gtk.Label()
    self._label_procedure_name.set_use_markup(True)
    self._label_procedure_name.set_alignment(0.0, 0.5)
    self._label_procedure_name.set_ellipsize(pango.ELLIPSIZE_END)
    
    self._vbox_operation_parameters = gtk.VBox()
    
    self._scrolled_window = gtk.ScrolledWindow()
    self._scrolled_window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    self._scrolled_window.add_with_viewport(self._vbox_operation_parameters)
    self._scrolled_window.get_child().set_shadow_type(gtk.SHADOW_NONE)
    
    self.vbox.pack_start(self._label_procedure_name, fill=False, expand=False)
    self.vbox.pack_start(self._scrolled_window, fill=True, expand=True)
    
    self.set_border_width(self._DIALOG_BORDER_WIDTH)
    #TODO: Resolve excessive borders at the bottom
    self.action_area.set_border_width(self._ACTION_AREA_BORDER_WIDTH)
    
    self.connect("response", self._on_operation_edit_dialog_response)
  
  def set_contents(self, operations_group, procedure):
    self.set_title(_("Edit operation {}").format(procedure.proc_name))
    self._label_procedure_name.set_markup(
      "<b>" + gobject.markup_escape_text(procedure.proc_name) + "</b>")
    
    operation_parameter_widgets = self._vbox_operation_parameters.get_children()
    for parameter_widget in operation_parameter_widgets:
      self._vbox_operation_parameters.remove(parameter_widget)
    
    operations.add(operations_group, procedure)
  
  def _on_operation_edit_dialog_response(self, dialog, response_id):
    #TODO: If canceling on choosing an operation from the procedure browser
    # dialog, do not add the operation
    
    if response_id == gtk.RESPONSE_OK:
      dialog.hide()
    else:
      dialog.hide()
