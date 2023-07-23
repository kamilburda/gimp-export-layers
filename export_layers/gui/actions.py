# -*- coding: utf-8 -*-

"""Widgets to interactively edit actions (procedures/constraints)."""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import pygtk
pygtk.require('2.0')
import gtk
import gobject
import pango

from gimp import pdb
import gimpui

from export_layers import pygimplib as pg

from export_layers import actions as actions_
from export_layers.gui import messages as messages_


class ActionBox(pg.gui.ItemBox):
  """
  This class defines a scrollable box that allows the user to add, edit and
  remove actions interactively. Each action has an associated widget
  (item) displayed in the box.
  
  The box connects events to the passed actions that keeps the actions and
  the box in sync. For example, when adding an action via `actions.add()`,
  the item for the action is automatically added to the box. Conversely, when
  calling `add_item()` from this class, both the action and the item are
  added to the actions and the GUI, respectively.
  
  Signals:
  
  * `'action-box-item-added'` - An item was added via `add_item()`.
    
    Arguments:
    
    * `item` - The added item.
    
  * `'action-box-item-reordered'` - An item was reordered via
    `reorder_item()`.
    
    Arguments:
    
    * `item` - The reordered item.
    * `new_position` - The new position of the reordered item (starting from 0).
    
  * `'action-box-item-removed'` - An item was removed via `remove_item()`.
    
    Arguments:
    
    * `item` - The removed item.
  """
  
  __gsignals__ = {
    b'action-box-item-added': (
      gobject.SIGNAL_RUN_FIRST, None, (gobject.TYPE_PYOBJECT,)),
    b'action-box-item-reordered': (
      gobject.SIGNAL_RUN_FIRST, None, (gobject.TYPE_PYOBJECT, gobject.TYPE_INT)),
    b'action-box-item-removed': (
      gobject.SIGNAL_RUN_FIRST, None, (gobject.TYPE_PYOBJECT,)),
  }
  
  _ADD_BUTTON_HBOX_SPACING = 6
  
  _ACTION_ENABLED_LABEL_MAX_CHAR_WIDTH = 1000
  
  def __init__(
        self,
        actions,
        builtin_actions=None,
        add_action_text=None,
        edit_action_text=None,
        allow_custom_actions=True,
        add_custom_action_text=None,
        item_spacing=pg.gui.ItemBox.ITEM_SPACING,
        *args,
        **kwargs):
    super().__init__(item_spacing=item_spacing, *args, **kwargs)
    
    self._actions = actions
    self._builtin_actions = (
      builtin_actions if builtin_actions is not None else {})
    self._add_action_text = add_action_text
    self._edit_action_text = edit_action_text
    self._allow_custom_actions = allow_custom_actions
    self._add_custom_action_text = add_custom_action_text
    
    self._pdb_procedure_browser_dialog = None
    
    self._init_gui()
    
    self._after_add_action_event_id = self._actions.connect_event(
      'after-add-action',
      lambda actions, action, orig_action_dict: self._add_item_from_action(action))
    
    self._after_reorder_action_event_id = self._actions.connect_event(
      'after-reorder-action',
      lambda actions, action, current_position, new_position: (
        self._reorder_action(action, new_position)))
    
    self._before_remove_action_event_id = self._actions.connect_event(
      'before-remove-action',
      lambda actions, action: self._remove_action(action))
    
    self._before_clear_actions_event_id = self._actions.connect_event(
      'before-clear-actions', lambda actions: self._clear())
  
  def add_item(self, action_dict_or_function):
    self._actions.set_event_enabled(self._after_add_action_event_id, False)
    action = actions_.add(self._actions, action_dict_or_function)
    self._actions.set_event_enabled(self._after_add_action_event_id, True)
    
    item = self._add_item_from_action(action)
    
    self.emit('action-box-item-added', item)
    
    return item
  
  def reorder_item(self, item, new_position):
    processed_new_position = self._reorder_item(item, new_position)
    
    self._actions.set_event_enabled(self._after_reorder_action_event_id, False)
    actions_.reorder(self._actions, item.action.name, processed_new_position)
    self._actions.set_event_enabled(self._after_reorder_action_event_id, True)
    
    self.emit('action-box-item-reordered', item, new_position)
  
  def remove_item(self, item):
    self._remove_item(item)
    
    self._actions.set_event_enabled(self._before_remove_action_event_id, False)
    actions_.remove(self._actions, item.action.name)
    self._actions.set_event_enabled(self._before_remove_action_event_id, True)
    
    self.emit('action-box-item-removed', item)
  
  def _init_gui(self):
    if self._add_action_text is not None:
      self._button_add = gtk.Button()
      button_hbox = gtk.HBox()
      button_hbox.set_spacing(self._ADD_BUTTON_HBOX_SPACING)
      button_hbox.pack_start(
        gtk.image_new_from_stock(gtk.STOCK_ADD, gtk.ICON_SIZE_MENU), expand=False, fill=False)
      
      label_add = gtk.Label(pg.utils.safe_encode_gtk(self._add_action_text))
      label_add.set_use_underline(True)
      button_hbox.pack_start(label_add, expand=False, fill=False)
      
      self._button_add.add(button_hbox)
    else:
      self._button_add = gtk.Button(stock=gtk.STOCK_ADD)
    
    self._button_add.set_relief(gtk.RELIEF_NONE)
    self._button_add.connect('clicked', self._on_button_add_clicked)
    
    self._vbox.pack_start(self._button_add, expand=False, fill=False)
    
    self._actions_menu = gtk.Menu()
    self._init_actions_menu_popup()
  
  def _add_item_from_action(self, action):
    self._init_action_item_gui(action)
    
    item = _ActionBoxItem(action, action['enabled'].gui.element)
    
    super().add_item(item)
    
    item.button_edit.connect('clicked', self._on_item_button_edit_clicked, item)
    item.button_remove.connect(
      'clicked', self._on_item_button_remove_clicked_remove_action_edit_dialog, item)
    
    return item
  
  def _init_action_item_gui(self, action):
    action.initialize_gui()
    
    # HACK: Prevent displaying horizontal scrollbar by ellipsizing labels. To
    # make ellipsizing work properly, the label width must be set explicitly.
    if isinstance(action['enabled'].gui, pg.setting.SettingGuiTypes.check_button):
      action['enabled'].gui.element.set_property('width-request', 1)
      action['enabled'].gui.element.get_child().set_ellipsize(pango.ELLIPSIZE_END)
      action['enabled'].gui.element.get_child().set_max_width_chars(
        self._ACTION_ENABLED_LABEL_MAX_CHAR_WIDTH)
      action['enabled'].gui.element.get_child().connect(
        'size-allocate',
        self._on_action_item_gui_label_size_allocate,
        action['enabled'].gui.element)
  
  def _on_action_item_gui_label_size_allocate(self, item_gui_label, allocation, item_gui):
    if pg.gui.label_fits_text(item_gui_label):
      item_gui.set_tooltip_text(None)
    else:
      item_gui.set_tooltip_text(item_gui_label.get_text())
  
  def _reorder_action(self, action, new_position):
    item = next((item_ for item_ in self._items if item_.action.name == action.name), None)
    if item is not None:
      self._reorder_item(item, new_position)
    else:
      raise ValueError('action "{}" does not match any item in "{}"'.format(action.name, self))
  
  def _reorder_item(self, item, new_position):
    return super().reorder_item(item, new_position)
  
  def _remove_action(self, action):
    item = next((item_ for item_ in self._items if item_.action.name == action.name), None)
    
    if item is not None:
      self._remove_item(item)
    else:
      raise ValueError('action "{}" does not match any item in "{}"'.format(
        action.get_path(), self))
  
  def _remove_item(self, item):
    if self._get_item_position(item) == len(self._items) - 1:
      self._button_add.grab_focus()
    
    super().remove_item(item)
  
  def _clear(self):
    for unused_ in range(len(self._items)):
      self._remove_item(self._items[0])
  
  def _init_actions_menu_popup(self):
    for action_dict in self._builtin_actions.values():
      self._add_action_to_menu_popup(action_dict)
    
    if self._allow_custom_actions:
      self._actions_menu.append(gtk.SeparatorMenuItem())
      self._add_add_custom_action_to_menu_popup()
    
    self._actions_menu.show_all()
  
  def _on_button_add_clicked(self, button):
    self._actions_menu.popup(None, None, None, 0, 0)
  
  def _add_action_to_menu_popup(self, action_dict):
    menu_item = gtk.MenuItem(
      label=pg.utils.safe_encode_gtk(action_dict['display_name']),
      use_underline=False)
    menu_item.connect('activate', self._on_actions_menu_item_activate, action_dict)
    self._actions_menu.append(menu_item)
  
  def _on_actions_menu_item_activate(self, menu_item, action_dict):
    item = self.add_item(action_dict)
    
    if action_dict.get('display_options_on_create', False):
      self._display_action_edit_dialog(item)
  
  def _add_add_custom_action_to_menu_popup(self):
    menu_item = gtk.MenuItem(label=self._add_custom_action_text, use_underline=False)
    menu_item.connect('activate', self._on_add_custom_action_menu_item_activate)
    self._actions_menu.append(menu_item)
  
  def _on_add_custom_action_menu_item_activate(self, menu_item):
    if self._pdb_procedure_browser_dialog:
      self._pdb_procedure_browser_dialog.show()
    else:
      self._pdb_procedure_browser_dialog = self._create_pdb_procedure_browser_dialog()
  
  def _create_pdb_procedure_browser_dialog(self):
    dialog = gimpui.ProcBrowserDialog(
      _('Procedure Browser'),
      role=pg.config.PLUGIN_NAME,
      buttons=(gtk.STOCK_ADD, gtk.RESPONSE_OK, gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
    
    dialog.set_default_response(gtk.RESPONSE_OK)
    dialog.set_alternative_button_order((gtk.RESPONSE_OK, gtk.RESPONSE_CANCEL))
    
    dialog.connect('response', self._on_pdb_procedure_browser_dialog_response)
    
    dialog.show_all()
    
    return dialog
  
  def _on_pdb_procedure_browser_dialog_response(self, dialog, response_id):
    if response_id == gtk.RESPONSE_OK:
      procedure_name = dialog.get_selected()
      if procedure_name:
        pdb_procedure = pdb[pg.utils.safe_encode_gimp(procedure_name)]
        
        try:
          pdb_proc_action_dict = actions_.get_action_dict_for_pdb_procedure(pdb_procedure)
        except actions_.UnsupportedPdbProcedureError as e:
          messages_.display_failure_message(
            main_message=_(
              'An error occurred while adding procedure "{}".'.format(e.procedure_name)),
            failure_message='',
            details=(
              _('Could not add procedure "{}" because the parameter type "{}"'
                ' is not supported.').format(e.procedure_name, e.unsupported_param_type)),
            parent=pg.gui.get_toplevel_window(self),
            report_description=_(
              'You can help fix this issue by sending a report with the text above'
              ' to one of the sites below'),
            display_details_initially=True)
          
          dialog.hide()
          return
        
        pdb_proc_action_dict['enabled'] = False
        
        item = self.add_item(pdb_proc_action_dict)
        
        self._display_action_edit_dialog(item, pdb_procedure)
    
    dialog.hide()
  
  def _display_action_edit_dialog(
        self, item, pdb_procedure=None, action_values_before_dialog=None):
    action_edit_dialog = _ActionEditDialog(
      item.action,
      pdb_procedure,
      title=self._get_action_edit_dialog_title(item),
      role=pg.config.PLUGIN_NAME)
    
    item.action_edit_dialog = action_edit_dialog
    
    if action_values_before_dialog is None:
      action_edit_dialog.connect(
        'response',
        self._on_action_edit_dialog_for_new_action_response,
        item)
    else:
      action_edit_dialog.connect(
        'response',
        self._on_action_edit_dialog_for_existing_action_response,
        item,
        action_values_before_dialog)
    
    action_edit_dialog.show_all()
  
  def _on_item_button_edit_clicked(self, edit_button, item):
    if item.is_being_edited():
      item.action_edit_dialog.present()
      return
    
    if item.action['origin'].is_item('gimp_pdb'):
      pdb_procedure = pdb[pg.utils.safe_encode_gimp(item.action['function'].value)]
    else:
      pdb_procedure = None
    
    action_values_before_dialog = {
      setting.get_path(item.action): setting.value
      for setting in item.action.walk()}
    
    self._display_action_edit_dialog(item, pdb_procedure, action_values_before_dialog)
  
  def _on_action_edit_dialog_for_new_action_response(
        self, dialog, response_id, item):
    dialog.destroy()
    
    if response_id == gtk.RESPONSE_OK:
      item.action['arguments'].apply_gui_values_to_settings()
      item.action['enabled'].set_value(True)
    else:
      self.remove_item(item)
    
    item.action_edit_dialog = None
  
  def _on_action_edit_dialog_for_existing_action_response(
        self, dialog, response_id, item, action_values_before_dialog):
    dialog.destroy()
    
    if response_id == gtk.RESPONSE_OK:
      item.action['arguments'].apply_gui_values_to_settings()
    else:
      item.action.set_values(action_values_before_dialog)
    
    item.action_edit_dialog = None
  
  def _on_item_button_remove_clicked_remove_action_edit_dialog(
        self, button_remove, item):
    if item.is_being_edited():
      item.action_edit_dialog.response(gtk.RESPONSE_CANCEL)
  
  def _get_action_edit_dialog_title(self, item):
    if self._edit_action_text is not None:
      return '{}: {}'.format(
        self._edit_action_text, item.action['display_name'].value)
    else:
      return None


class _ActionBoxItem(pg.gui.ItemBoxItem):
  
  def __init__(self, action, item_widget):
    super().__init__(item_widget)
    
    self.action_edit_dialog = None
    
    self._action = action
    
    self._button_edit = gtk.Button()
    self._setup_item_button(self._button_edit, gtk.STOCK_EDIT, position=0)
    
    self._button_warning = gtk.Button()
    self._setup_item_indicator_button(self._button_warning, gtk.STOCK_DIALOG_WARNING, position=0)
    self._button_warning.hide()
    
    self._display_warning_message_event_id = None
  
  @property
  def action(self):
    return self._action
  
  @property
  def button_edit(self):
    return self._button_edit
  
  def is_being_edited(self):
    return self.action_edit_dialog is not None
  
  def close_edit_dialog(self):
    if self.action_edit_dialog is not None:
      self.action_edit_dialog.response(gtk.RESPONSE_CANCEL)
  
  def set_tooltip(self, text):
    self.widget.set_tooltip_text(text)
  
  def has_warning(self):
    return self._button_warning.get_visible()
  
  def set_warning(self, show, main_message=None, failure_message=None, details=None, parent=None):
    if show:
      self.set_tooltip(failure_message)
      if details is not None:
        if self._display_warning_message_event_id is not None:
          self._button_warning.disconnect(self._display_warning_message_event_id)
        
        self._display_warning_message_event_id = self._button_warning.connect(
          'clicked',
          self._on_button_warning_clicked, main_message, failure_message, details, parent)
      
      self._button_warning.show()
    else:
      self._button_warning.hide()
      
      self.set_tooltip(None)
      if self._display_warning_message_event_id is not None:
        self._button_warning.disconnect(self._display_warning_message_event_id)
        self._display_warning_message_event_id = None
  
  def _on_button_warning_clicked(self, button, main_message, short_message, full_message, parent):
    messages_.display_failure_message(main_message, short_message, full_message, parent=parent)


class _ActionEditDialog(gimpui.Dialog):
  
  _DIALOG_BORDER_WIDTH = 8
  _DIALOG_VBOX_SPACING = 8
  
  _TABLE_ROW_SPACING = 4
  _TABLE_COLUMN_SPACING = 8
  
  _ARRAY_PARAMETER_GUI_WIDTH = 300
  _ARRAY_PARAMETER_GUI_MAX_HEIGHT = 150
  
  _PLACEHOLDER_WIDGET_HORIZONTAL_SPACING_BETWEEN_ELEMENTS = 5
  
  _MORE_OPTIONS_SPACING = 4
  _MORE_OPTIONS_BORDER_WIDTH = 4
  
  def __init__(self, action, pdb_procedure, *args, **kwargs):
    super().__init__(*args, **kwargs)
    
    self.set_transient()
    self.set_resizable(False)
    
    self._button_ok = self.add_button(gtk.STOCK_OK, gtk.RESPONSE_OK)
    self._button_cancel = self.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
    self.set_alternative_button_order([gtk.RESPONSE_OK, gtk.RESPONSE_CANCEL])
    
    self._button_reset = gtk.Button()
    self._button_reset.set_label(_('_Reset'))
    self.action_area.pack_start(self._button_reset, expand=False, fill=False)
    self.action_area.set_child_secondary(self._button_reset, True)
    
    self._label_procedure_name = pg.gui.EditableLabel()
    self._label_procedure_name.label.set_use_markup(True)
    self._label_procedure_name.label.set_ellipsize(pango.ELLIPSIZE_END)
    self._label_procedure_name.label.set_markup(
      '<b>{}</b>'.format(gobject.markup_escape_text(action['display_name'].value)))
    self._label_procedure_name.connect(
      'changed', self._on_label_procedure_name_changed, action)
    
    self._label_procedure_description = None
    
    if action['description'].value:
      self._label_procedure_description = self._create_label_description(
        action['description'].value)
    elif pdb_procedure is not None:
      self._label_procedure_description = self._create_label_description(
        pdb_procedure.proc_blurb, pdb_procedure.proc_help)
    
    self._table_action_arguments = gtk.Table(homogeneous=False)
    self._table_action_arguments.set_row_spacings(self._TABLE_ROW_SPACING)
    self._table_action_arguments.set_col_spacings(self._TABLE_COLUMN_SPACING)
    
    self._vbox_more_options = gtk.VBox()
    self._vbox_more_options.set_spacing(self._MORE_OPTIONS_SPACING)
    self._vbox_more_options.set_border_width(self._MORE_OPTIONS_BORDER_WIDTH)
    self._vbox_more_options.pack_start(
      action['enabled_for_previews'].gui.element, expand=False, fill=False)
    if 'also_apply_to_parent_folders' in action:
      self._vbox_more_options.pack_start(
        action['also_apply_to_parent_folders'].gui.element, expand=False, fill=False)
    
    action['more_options_expanded'].gui.element.add(self._vbox_more_options)
    
    # Put widgets in a custom `VBox` because the action area would otherwise
    # have excessively thick borders for some reason.
    self._vbox = gtk.VBox()
    self._vbox.set_border_width(self._DIALOG_BORDER_WIDTH)
    self._vbox.set_spacing(self._DIALOG_VBOX_SPACING)
    self._vbox.pack_start(self._label_procedure_name, expand=False, fill=False)
    if self._label_procedure_description is not None:
      self._vbox.pack_start(self._label_procedure_description, expand=False, fill=False)
    self._vbox.pack_start(self._table_action_arguments, expand=True, fill=True)
    self._vbox.pack_start(action['more_options_expanded'].gui.element, expand=False, fill=False)
    
    self.vbox.pack_start(self._vbox, expand=False, fill=False)
    
    self._set_arguments(action, pdb_procedure)
    
    self.set_focus(self._button_ok)
    
    self._button_reset.connect('clicked', self._on_button_reset_clicked, action)
    self.connect('response', self._on_action_edit_dialog_response, action)
  
  def _create_label_description(self, summary, full_description=None):
    label_description = gtk.Label()
    label_description.set_line_wrap(True)
    label_description.set_alignment(0.0, 0.5)
    label_description.set_label(summary)
    if full_description:
      label_description.set_tooltip_text(full_description)
    
    return label_description
  
  def _set_arguments(self, action, pdb_procedure):
    for i, setting in enumerate(action['arguments']):
      if not setting.gui.get_visible():
        continue
      
      label = gtk.Label(setting.display_name)
      label.set_alignment(0.0, 0.5)
      if pdb_procedure is not None:
        label.set_tooltip_text(pdb_procedure.params[i][2])
      
      self._table_action_arguments.attach(label, 0, 1, i, i + 1)
      
      gui_element_to_attach = setting.gui.element
      
      if not isinstance(setting.gui, pg.setting.SettingGuiTypes.null):
        if isinstance(setting, pg.setting.ArraySetting):
          if setting.element_type.get_allowed_gui_types():
            setting.gui.element.set_property('width-request', self._ARRAY_PARAMETER_GUI_WIDTH)
            setting.gui.element.max_height = self._ARRAY_PARAMETER_GUI_MAX_HEIGHT
          else:
            gui_element_to_attach = self._create_placeholder_widget()
      else:
        gui_element_to_attach = self._create_placeholder_widget()
      
      self._table_action_arguments.attach(gui_element_to_attach, 1, 2, i, i + 1)
  
  def _on_button_reset_clicked(self, button, action):
    action['arguments'].reset()
  
  def _on_label_procedure_name_changed(self, editable_label, action):
    action['display_name'].set_value(editable_label.label.get_text())
    
    editable_label.label.set_markup(
      '<b>{}</b>'.format(gobject.markup_escape_text(editable_label.label.get_text())))
  
  def _on_action_edit_dialog_response(self, dialog, response_id, action):
    for child in list(self._table_action_arguments.get_children()):
      self._table_action_arguments.remove(child)
    
    for child in list(self._vbox_more_options.get_children()):
      self._vbox_more_options.remove(child)
    
    action['more_options_expanded'].gui.element.remove(self._vbox_more_options)
    self._vbox.remove(action['more_options_expanded'].gui.element)
  
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
        gobject.markup_escape_text(_('Cannot modify this parameter'))))
    
    hbox.pack_start(label, expand=False, fill=False)
    
    return hbox
