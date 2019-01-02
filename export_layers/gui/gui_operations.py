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
This module defines the means to interactively edit a list of operations
executed in the plug-in.
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
from export_layers.pygimplib import pgsetting
from export_layers.pygimplib import pgutils

from .. import operations


class OperationBox(pggui.ItemBox):
  
  _ADD_BUTTON_HBOX_SPACING = 6
  
  _OPERATION_ENABLED_LABEL_MAX_CHAR_WIDTH = 1000
  
  def __init__(
        self,
        operations_,
        builtin_operations=None,
        add_operation_text=None,
        edit_operation_text=None,
        allow_custom_operations=True,
        add_custom_operation_text=None,
        item_spacing=pggui.ItemBox.ITEM_SPACING,
        *args,
        **kwargs):
    super().__init__(item_spacing=item_spacing, *args, **kwargs)
    
    self._operations = operations_
    self._builtin_operations = (
      builtin_operations if builtin_operations is not None else {})
    self._add_operation_text = add_operation_text
    self._edit_operation_text = edit_operation_text
    self._allow_custom_operations = allow_custom_operations
    self._add_custom_operation_text = add_custom_operation_text
    
    self.on_add_item = pgutils.empty_func
    self.on_reorder_item = pgutils.empty_func
    self.on_remove_item = pgutils.empty_func
    
    self._pdb_procedure_browser_dialog = None
    
    self._init_gui()
  
  def _init_gui(self):
    if self._add_operation_text is not None:
      self._button_add = gtk.Button()
      button_hbox = gtk.HBox()
      button_hbox.set_spacing(self._ADD_BUTTON_HBOX_SPACING)
      button_hbox.pack_start(
        gtk.image_new_from_stock(gtk.STOCK_ADD, gtk.ICON_SIZE_MENU),
        expand=False,
        fill=False)
      
      label_add = gtk.Label(
        self._add_operation_text.encode(pgconstants.GTK_CHARACTER_ENCODING))
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
  
  def add_item(self, operation_dict_or_function):
    operation = self.on_add_item(self._operations, operation_dict_or_function)
    self._init_operation_item_gui(operation)
    
    item = _OperationBoxItem(operation, operation["enabled"].gui.element)
    
    super().add_item(item)
    
    item.button_edit.connect("clicked", self._on_item_edit_button_clicked, item)
    item.button_remove.connect(
      "clicked", self._on_item_remove_button_clicked_remove_operation_edit_dialog, item)
    
    return item
  
  def _init_operation_item_gui(self, operation):
    operation.initialize_gui()
    
    # HACK: Prevent displaying horizontal scrollbar by ellipsizing labels. To
    # make ellipsizing work properly, the label width must be set explicitly.
    if isinstance(operation["enabled"].gui, pgsetting.SettingGuiTypes.check_button):
      operation["enabled"].gui.element.set_property("width-request", 1)
      operation["enabled"].gui.element.get_child().set_ellipsize(pango.ELLIPSIZE_END)
      operation["enabled"].gui.element.get_child().set_max_width_chars(
        self._OPERATION_ENABLED_LABEL_MAX_CHAR_WIDTH)
      operation["enabled"].gui.element.get_child().connect(
        "size-allocate",
        self._on_operation_item_gui_label_size_allocate,
        operation["enabled"].gui.element)
  
  def _on_operation_item_gui_label_size_allocate(
        self, item_gui_label, allocation, item_gui):
    pggui.set_tooltip_if_label_does_not_fit(item_gui, item_gui_label)
  
  def reorder_item(self, item, new_position):
    processed_new_position = super().reorder_item(item, new_position)
    self.on_reorder_item(self._operations, item.operation.name, processed_new_position)
  
  def remove_item(self, item):
    if self._get_item_position(item) == len(self._items) - 1:
      self._button_add.grab_focus()
    
    super().remove_item(item)
    
    self.on_remove_item(self._operations, item.operation.name)
  
  def _init_operations_menu_popup(self):
    for operation_dict in self._builtin_operations.values():
      self._add_operation_to_menu_popup(operation_dict)
    
    if self._allow_custom_operations:
      self._operations_menu.append(gtk.SeparatorMenuItem())
      self._add_add_custom_operation_to_menu_popup()
    
    self._operations_menu.show_all()
  
  def _on_button_add_clicked(self, button):
    self._operations_menu.popup(None, None, None, 0, 0)
  
  def _add_operation_to_menu_popup(self, operation_dict):
    menu_item = gtk.MenuItem(
      label=operation_dict["display_name"].encode(
        pgconstants.GTK_CHARACTER_ENCODING),
      use_underline=False)
    menu_item.connect("activate", self._on_operations_menu_item_activate, operation_dict)
    self._operations_menu.append(menu_item)
  
  def _on_operations_menu_item_activate(self, menu_item, operation_dict_or_function):
    self.add_item(operation_dict_or_function)
  
  def _add_add_custom_operation_to_menu_popup(self):
    menu_item = gtk.MenuItem(label=self._add_custom_operation_text, use_underline=False)
    menu_item.connect("activate", self._on_add_custom_operation_menu_item_activate)
    self._operations_menu.append(menu_item)
  
  def _on_add_custom_operation_menu_item_activate(self, menu_item):
    if self._pdb_procedure_browser_dialog:
      self._pdb_procedure_browser_dialog.show()
    else:
      self._pdb_procedure_browser_dialog = self._create_pdb_procedure_browser_dialog()
  
  def _create_pdb_procedure_browser_dialog(self):
    dialog = gimpui.ProcBrowserDialog(
      _("Procedure Browser"),
      role=pygimplib.config.PLUGIN_NAME,
      buttons=(gtk.STOCK_ADD, gtk.RESPONSE_OK, gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
    
    dialog.set_default_response(gtk.RESPONSE_OK)
    dialog.set_alternative_button_order((gtk.RESPONSE_OK, gtk.RESPONSE_CANCEL))
    
    dialog.connect("response", self._on_pdb_procedure_browser_dialog_response)
    
    dialog.show_all()
    
    return dialog
  
  def _on_pdb_procedure_browser_dialog_response(self, dialog, response_id):
    if response_id == gtk.RESPONSE_OK:
      procedure_name = dialog.get_selected()
      if procedure_name:
        pdb_procedure = pdb[procedure_name.encode(pgconstants.GIMP_CHARACTER_ENCODING)]
        
        try:
          pdb_proc_operation_dict = operations.get_operation_dict_for_pdb_procedure(
            pdb_procedure)
        except operations.UnsupportedPdbProcedureError as e:
          pggui.display_error_message(
            title=pygimplib.config.PLUGIN_TITLE,
            app_name="",
            parent=pggui.get_toplevel_window(self),
            message_type=gtk.MESSAGE_WARNING,
            message_markup=(
              _("Could not add procedure '{}' because the parameter type '{}' "
                "is not supported.").format(e.procedure_name, e.unsupported_param_type)),
            message_secondary_markup="",
            report_uri_list=pygimplib.config.BUG_REPORT_URL_LIST,
            report_description=_(
              "You can help fix this issue by sending a report with the text above "
              "to one of the sites below"),
            focus_on_button=True)
          
          dialog.hide()
          return
        
        pdb_proc_operation_dict["enabled"] = False
        
        item = self.add_item(pdb_proc_operation_dict)
        
        operation_edit_dialog = _OperationEditDialog(
          item.operation,
          pdb_procedure,
          title=self._get_operation_edit_dialog_title(item),
          role=pygimplib.config.PLUGIN_NAME)
        
        operation_edit_dialog.connect(
          "response",
          self._on_operation_edit_dialog_for_new_operation_response,
          item)
        
        operation_edit_dialog.show_all()
    
    dialog.hide()
  
  def _on_operation_edit_dialog_for_new_operation_response(
        self, dialog, response_id, item):
    dialog.destroy()
    
    if response_id == gtk.RESPONSE_OK:
      item.operation["enabled"].set_value(True)
    else:
      self.remove_item(item)
  
  def _on_item_edit_button_clicked(self, edit_button, item):
    if item.is_being_edited():
      return
    
    if item.operation.get_value("is_pdb_procedure", False):
      pdb_procedure = pdb[
        item.operation["function"].value.encode(pgconstants.GIMP_CHARACTER_ENCODING)]
    else:
      pdb_procedure = None
    
    operation_values_before_dialog = {
      setting.get_path(item.operation): setting.value
      for setting in item.operation.walk()}
    
    operation_edit_dialog = _OperationEditDialog(
      item.operation,
      pdb_procedure,
      title=self._get_operation_edit_dialog_title(item),
      role=pygimplib.config.PLUGIN_NAME)
    
    item.operation_edit_dialog = operation_edit_dialog
    
    operation_edit_dialog.connect(
      "response",
      self._on_operation_edit_dialog_for_existing_operation_response,
      item,
      operation_values_before_dialog)
    
    operation_edit_dialog.show_all()
  
  def _on_operation_edit_dialog_for_existing_operation_response(
        self, dialog, response_id, item, operation_values_before_dialog):
    dialog.destroy()
    
    if response_id == gtk.RESPONSE_OK:
      item.operation["arguments"].apply_gui_values_to_settings()
    else:
      item.operation.set_values(operation_values_before_dialog)
    
    item.operation_edit_dialog = None
  
  def _on_item_remove_button_clicked_remove_operation_edit_dialog(
        self, button_remove, item):
    if item.is_being_edited():
      item.operation_edit_dialog.response(gtk.RESPONSE_CANCEL)
  
  def _get_operation_edit_dialog_title(self, item):
    if self._edit_operation_text is not None:
      return "{} {}".format(
        self._edit_operation_text, item.operation["display_name"].value)
    else:
      return None


class _OperationBoxItem(pggui.ItemBoxItem):
  
  def __init__(self, operation, item_widget):
    super().__init__(item_widget)
    
    self.operation_edit_dialog = None
    
    self._operation = operation
    
    self._button_edit = gtk.Button()
    self._setup_item_button(self._button_edit, gtk.STOCK_EDIT, position=0)
  
  @property
  def operation(self):
    return self._operation
  
  @property
  def button_edit(self):
    return self._button_edit
  
  def is_being_edited(self):
    return self.operation_edit_dialog is not None


class _OperationEditDialog(gimpui.Dialog):
  
  _DIALOG_BORDER_WIDTH = 8
  _DIALOG_VBOX_SPACING = 8
  
  _TABLE_ROW_SPACING = 4
  _TABLE_COLUMN_SPACING = 8
  
  _ARRAY_PARAMETER_GUI_MAX_WIDTH = 300
  _ARRAY_PARAMETER_GUI_MAX_HEIGHT = 150
  
  _PLACEHOLDER_WIDGET_HORIZONTAL_SPACING_BETWEEN_ELEMENTS = 5
  
  def __init__(self, operation, pdb_procedure, *args, **kwargs):
    super().__init__(*args, **kwargs)
    
    self.set_transient()
    self.set_resizable(False)
    
    self._button_ok = self.add_button(gtk.STOCK_OK, gtk.RESPONSE_OK)
    self._button_cancel = self.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
    self.set_alternative_button_order([gtk.RESPONSE_OK, gtk.RESPONSE_CANCEL])
    
    self._button_reset = gtk.Button()
    self._button_reset.set_label(_("_Reset"))
    self.action_area.pack_start(self._button_reset, expand=False, fill=False)
    self.action_area.set_child_secondary(self._button_reset, True)
    
    self._label_procedure_name = pggui.EditableLabel()
    self._label_procedure_name.label.set_use_markup(True)
    self._label_procedure_name.label.set_ellipsize(pango.ELLIPSIZE_END)
    self._label_procedure_name.label.set_markup(
      "<b>{}</b>".format(gobject.markup_escape_text(operation["display_name"].value)))
    self._label_procedure_name.connect(
      "changed", self._on_label_procedure_name_changed, operation)
    
    if pdb_procedure is not None:
      self._label_procedure_short_description = gtk.Label()
      self._label_procedure_short_description.set_line_wrap(True)
      self._label_procedure_short_description.set_alignment(0.0, 0.5)
      self._label_procedure_short_description.set_label(pdb_procedure.proc_blurb)
      self._label_procedure_short_description.set_tooltip_text(pdb_procedure.proc_help)
    
    self._table_operation_arguments = gtk.Table(homogeneous=False)
    self._table_operation_arguments.set_row_spacings(self._TABLE_ROW_SPACING)
    self._table_operation_arguments.set_col_spacings(self._TABLE_COLUMN_SPACING)
    
    # Put widgets in a custom `VBox` because the action area would otherwise
    # have excessively thick borders for some reason.
    self._vbox = gtk.VBox()
    self._vbox.set_border_width(self._DIALOG_BORDER_WIDTH)
    self._vbox.set_spacing(self._DIALOG_VBOX_SPACING)
    self._vbox.pack_start(self._label_procedure_name, expand=False, fill=False)
    if pdb_procedure is not None:
      self._vbox.pack_start(
        self._label_procedure_short_description, expand=False, fill=False)
    self._vbox.pack_start(self._table_operation_arguments, expand=True, fill=True)
    
    self.vbox.pack_start(self._vbox, expand=False, fill=False)
    
    self._set_arguments(operation, pdb_procedure)
    
    self.set_focus(self._button_ok)
    
    self._button_reset.connect("clicked", self._on_button_reset_clicked, operation)
    self.connect("response", self._on_operation_edit_dialog_response)
  
  def _set_arguments(self, operation, pdb_procedure):
    for i, setting in enumerate(operation["arguments"]):
      if not setting.gui.get_visible():
        continue
      
      label = gtk.Label(setting.display_name)
      label.set_alignment(0.0, 0.5)
      if pdb_procedure is not None:
        label.set_tooltip_text(pdb_procedure.params[i][2])
      
      self._table_operation_arguments.attach(label, 0, 1, i, i + 1)
      
      gui_element_to_attach = setting.gui.element
      
      if not isinstance(setting.gui, pgsetting.SettingGuiTypes.none):
        if isinstance(setting, pgsetting.ArraySetting):
          if setting.element_type.get_allowed_gui_types():
            setting.gui.element.max_width = self._ARRAY_PARAMETER_GUI_MAX_WIDTH
            setting.gui.element.max_height = self._ARRAY_PARAMETER_GUI_MAX_HEIGHT
          else:
            gui_element_to_attach = self._create_placeholder_widget()
      else:
        gui_element_to_attach = self._create_placeholder_widget()
      
      self._table_operation_arguments.attach(gui_element_to_attach, 1, 2, i, i + 1)
  
  def _on_button_reset_clicked(self, button, operation):
    operation["arguments"].reset()
  
  def _on_label_procedure_name_changed(self, editable_label, operation):
    operation["display_name"].set_value(editable_label.label.get_text())
    
    editable_label.label.set_markup(
      "<b>{}</b>".format(gobject.markup_escape_text(editable_label.label.get_text())))
  
  def _on_operation_edit_dialog_response(self, dialog, response_id):
    for child in list(self._table_operation_arguments.get_children()):
      self._table_operation_arguments.remove(child)
  
  def _create_placeholder_widget(self):
    hbox = gtk.HBox()
    hbox.set_spacing(self._PLACEHOLDER_WIDGET_HORIZONTAL_SPACING_BETWEEN_ELEMENTS)
    
    hbox.pack_start(
      gtk.image_new_from_stock(gtk.STOCK_DIALOG_WARNING, gtk.ICON_SIZE_BUTTON),
      expand=False,
      fill=False)
    
    label = gtk.Label()
    label.set_use_markup(True)
    label.set_markup(
      '<span font_size="small">{}</span>'.format(
        gobject.markup_escape_text(_("Cannot modify this parameter"))))
    
    hbox.pack_start(label, expand=False, fill=False)
    
    return hbox
