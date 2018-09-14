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
    
    self._menu_items_and_operation_names = {}
    
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
    
    self._operations_menu.show_all()
  
  def _add_operation_to_menu_popup(self, operation):
    menu_item = gtk.MenuItem(
      label=operation["display_name"].value.encode(pgconstants.GTK_CHARACTER_ENCODING),
      use_underline=False)
    menu_item.connect("activate", self._on_operations_menu_item_activate)
    self._operations_menu.append(menu_item)
    self._menu_items_and_operation_names[menu_item] = operation.name
  
  def _on_operations_menu_item_activate(self, menu_item):
    self.add_item(self._menu_items_and_operation_names[menu_item])
  
  def _on_button_add_clicked(self, button):
    self._operations_menu.popup(None, None, None, 0, 0)


class _OperationItem(pggui.ItemBoxItem):
  
  def __init__(self, operation, item_widget):
    super().__init__(item_widget)
    
    self._operation = operation
  
  @property
  def operation(self):
    return self._operation
