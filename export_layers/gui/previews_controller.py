# -*- coding: utf-8 -*-

"""Class interconnecting preview widgets for item names and images."""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

from export_layers import pygimplib as pg

from export_layers import builtin_constraints
from export_layers import builtin_procedures
from export_layers import exceptions


class PreviewsController(object):
  
  _DELAY_PREVIEWS_SETTING_UPDATE_MILLISECONDS = 50
  _DELAY_PREVIEWS_PANE_DRAG_UPDATE_MILLISECONDS = 500
  
  _ACTION_ERROR_KEY = 'action_error'
  
  def __init__(self, name_preview, image_preview, settings, image):
    self._name_preview = name_preview
    self._image_preview = image_preview
    self._settings = settings
    self._image = image
    
    self._selected_in_preview_constraints = {}
    self._custom_actions = {}
    self._is_initial_selection_set = False
    
    self._last_name_preview_update_successful = True
    
    self._paned_outside_previews_previous_position = (
      self._settings['gui/size/paned_outside_previews_position'].value)
    self._paned_between_previews_previous_position = (
      self._settings['gui/size/paned_between_previews_position'].value)
  
  def connect_setting_changes_to_previews(self):
    self._connect_actions_changed(self._settings['main/procedures'])
    self._connect_actions_changed(self._settings['main/constraints'])
    
    self._connect_setting_after_reset_collapsed_items_in_name_preview()
    self._connect_setting_after_reset_selected_items_in_name_preview()
    self._connect_setting_after_reset_displayed_items_in_image_preview()
    
    self._connect_toggle_name_preview_filtering()
    self._connect_update_rendering_of_image_preview()
    self._connect_image_preview_menu_setting_changes()
    
    self._connect_toplevel_notify_is_active()
  
  def connect_name_preview_events(self):
    self._name_preview.connect(
      'preview-selection-changed', self._on_name_preview_selection_changed)
    self._name_preview.connect(
      'preview-updated', self._on_name_preview_updated)
    self._name_preview.connect(
      'preview-tags-changed', self._on_name_preview_tags_changed)
  
  def on_paned_outside_previews_notify_position(self, paned, property_spec):
    current_position = paned.get_position()
    max_position = paned.get_property('max-position')
    
    if (current_position == max_position
        and self._paned_outside_previews_previous_position != max_position):
      self._disable_preview_on_paned_drag(
        self._name_preview,
        self._settings['gui/name_preview_sensitive'],
        'previews_sensitive')
      self._disable_preview_on_paned_drag(
        self._image_preview,
        self._settings['gui/image_preview_sensitive'],
        'previews_sensitive')
    elif (current_position != max_position
          and self._paned_outside_previews_previous_position == max_position):
      self._enable_preview_on_paned_drag(
        self._name_preview,
        self._settings['gui/name_preview_sensitive'],
        'previews_sensitive')
      self._enable_preview_on_paned_drag(
        self._image_preview,
        self._settings['gui/image_preview_sensitive'],
        'previews_sensitive')
    elif current_position != self._paned_outside_previews_previous_position:
      if self._image_preview.is_larger_than_image():
        pg.invocation.timeout_add_strict(
          self._DELAY_PREVIEWS_PANE_DRAG_UPDATE_MILLISECONDS,
          self._image_preview.update)
      else:
        pg.invocation.timeout_remove_strict(self._image_preview.update)
        self._image_preview.resize()
    
    self._paned_outside_previews_previous_position = current_position
  
  def on_paned_between_previews_notify_position(self, paned, property_spec):
    current_position = paned.get_position()
    max_position = paned.get_property('max-position')
    min_position = paned.get_property('min-position')
    
    if (current_position == max_position
        and self._paned_between_previews_previous_position != max_position):
      self._disable_preview_on_paned_drag(
        self._image_preview,
        self._settings['gui/image_preview_sensitive'],
        'vpaned_preview_sensitive')
    elif (current_position != max_position
          and self._paned_between_previews_previous_position == max_position):
      self._enable_preview_on_paned_drag(
        self._image_preview,
        self._settings['gui/image_preview_sensitive'],
        'vpaned_preview_sensitive')
    elif (current_position == min_position
          and self._paned_between_previews_previous_position != min_position):
      self._disable_preview_on_paned_drag(
        self._name_preview,
        self._settings['gui/name_preview_sensitive'],
        'vpaned_preview_sensitive')
    elif (current_position != min_position
          and self._paned_between_previews_previous_position == min_position):
      self._enable_preview_on_paned_drag(
        self._name_preview,
        self._settings['gui/name_preview_sensitive'],
        'vpaned_preview_sensitive')
    elif current_position != self._paned_between_previews_previous_position:
      if self._image_preview.is_larger_than_image():
        pg.invocation.timeout_add_strict(
          self._DELAY_PREVIEWS_PANE_DRAG_UPDATE_MILLISECONDS,
          self._image_preview.update)
      else:
        pg.invocation.timeout_remove_strict(self._image_preview.update)
        self._image_preview.resize()
    
    self._paned_between_previews_previous_position = current_position
  
  def _connect_actions_changed(self, actions_):
    def _on_after_add_action(actions_, action, *args, **kwargs):
      if action['enabled'].value:
        self._update_previews_on_setting_change(action['enabled'])
      action['enabled'].connect_event(
        'value-changed', self._update_previews_on_setting_change)
    
    def _on_after_reorder_action(actions_, action, *args, **kwargs):
      if action['enabled'].value:
        self._update_previews_on_setting_change(action['enabled'])
    
    def _on_before_remove_action(actions_, action, *args, **kwargs):
      if action['enabled'].value:
        # Changing the enabled state triggers the 'value-changed' event and thus
        # properly keeps the previews in sync after action removal.
        action['enabled'].set_value(False)
    
    actions_.connect_event('after-add-action', _on_after_add_action)
    actions_.connect_event('after-reorder-action', _on_after_reorder_action)
    actions_.connect_event('before-remove-action', _on_before_remove_action)
  
  def _update_previews_on_setting_change(self, setting):
    self._name_preview.lock_update(False, self._ACTION_ERROR_KEY)
    pg.invocation.timeout_add_strict(
      self._DELAY_PREVIEWS_SETTING_UPDATE_MILLISECONDS, self._name_preview.update)
    
    self._image_preview.lock_update(False, self._ACTION_ERROR_KEY)
    pg.invocation.timeout_add_strict(
      self._DELAY_PREVIEWS_SETTING_UPDATE_MILLISECONDS, self._image_preview.update)
  
  def _connect_setting_after_reset_collapsed_items_in_name_preview(self):
    self._settings['gui/name_preview_layers_collapsed_state'].connect_event(
      'after-reset',
      lambda setting: self._name_preview.set_collapsed_items(setting.value[self._image.ID]))
  
  def _connect_setting_after_reset_selected_items_in_name_preview(self):
    self._settings['main/selected_layers'].connect_event(
      'after-reset',
      lambda setting: self._name_preview.set_selected_items(setting.value[self._image.ID]))
  
  def _connect_setting_after_reset_displayed_items_in_image_preview(self):
    def _clear_image_preview(setting):
      self._image_preview.clear()
    
    self._settings['gui/image_preview_displayed_layers'].connect_event(
      'after-reset', _clear_image_preview)
  
  def _connect_toggle_name_preview_filtering(self):
    def _after_add_selected_in_preview(constraints, constraint, orig_constraint_dict):
      if constraint['orig_name'].value == 'selected_in_preview':
        self._selected_in_preview_constraints[constraint.name] = constraint
        
        _on_enabled_changed(constraint['enabled'])
        constraint['enabled'].connect_event('value-changed', _on_enabled_changed)
    
    def _before_remove_selected_in_preview(constraints, constraint):
      if constraint.name in self._selected_in_preview_constraints:
        del self._selected_in_preview_constraints[constraint.name]
    
    def _before_clear_constraints(constraints):
      self._selected_in_preview_constraints = {}
      self._name_preview.is_filtering = False
    
    def _on_enabled_changed(constraint_enabled):
      self._name_preview.is_filtering = (
        any(constraint['enabled'].value
            for constraint in self._selected_in_preview_constraints.values()))
    
    self._settings['main/constraints'].connect_event(
      'after-add-action', _after_add_selected_in_preview)
    
    self._settings['main/constraints'].connect_event(
      'before-remove-action', _before_remove_selected_in_preview)
    
    self._settings['main/constraints'].connect_event(
      'before-clear-actions', _before_clear_constraints)
  
  def _connect_update_rendering_of_image_preview(self):
    def _after_add_action(actions, action, orig_action_dict, builtin_actions):
      if action['orig_name'].value not in builtin_actions:
        self._custom_actions[action.get_path()] = action
        
        _update_rendering_of_image_preview(action['enabled'])
        action['enabled'].connect_event('value-changed', _update_rendering_of_image_preview)
    
    def _before_remove_action(actions, action):
      if action.get_path() in self._custom_actions:
        del self._custom_actions[action.get_path()]
    
    def _before_clear_actions(actions):
      for action in actions:
        if action.get_path() in self._custom_actions:
          del self._custom_actions[action.get_path()]
      
      if not self._custom_actions:
        self._image_preview.prepare_image_for_rendering()
    
    def _update_rendering_of_image_preview(action_enabled):
      if not any(action['enabled'].value for action in self._custom_actions.values()):
        self._image_preview.prepare_image_for_rendering()
      else:
        self._image_preview.prepare_image_for_rendering(
          ['after_process_item_contents'], ['after_process_item_contents'])
    
    self._settings['main/procedures'].connect_event(
      'after-add-action',
      _after_add_action,
      builtin_procedures.BUILTIN_PROCEDURES)
    
    self._settings['main/procedures'].connect_event(
      'before-remove-action', _before_remove_action)
    
    self._settings['main/procedures'].connect_event(
      'before-clear-actions', _before_clear_actions)
    
    self._settings['main/constraints'].connect_event(
      'after-add-action',
      _after_add_action,
      builtin_constraints.BUILTIN_CONSTRAINTS)
    
    self._settings['main/constraints'].connect_event(
      'before-remove-action', _before_remove_action)
    
    self._settings['main/constraints'].connect_event(
      'before-clear-actions', _before_clear_actions)
  
  def _connect_image_preview_menu_setting_changes(self):
    self._settings['gui/image_preview_automatic_update'].connect_event(
      'value-changed',
      lambda setting, update_if_below_setting: update_if_below_setting.set_value(False),
      self._settings['gui/image_preview_automatic_update_if_below_maximum_duration'])
  
  def _connect_toplevel_notify_is_active(self):
    toplevel = (
      pg.gui.get_toplevel_window(self._name_preview)
      or pg.gui.get_toplevel_window(self._image_preview))
    if toplevel is not None:
      toplevel.connect('notify::is-active', self._on_toplevel_notify_is_active)
   
  def _on_name_preview_selection_changed(self, preview):
    self._update_selected_items()
    self._update_image_preview()
  
  def _on_name_preview_updated(self, preview, error):
    if isinstance(error, exceptions.ActionError):
      self._name_preview.lock_update(True, self._ACTION_ERROR_KEY)
      self._image_preview.lock_update(True, self._ACTION_ERROR_KEY)
    
    self._image_preview.update_item()
  
  def _on_name_preview_tags_changed(self, preview):
    self._update_image_preview()
  
  def _on_toplevel_notify_is_active(self, toplevel, property_spec):
    if toplevel.is_active():
      pg.invocation.timeout_remove_strict(self._name_preview.update)
      pg.invocation.timeout_remove_strict(self._image_preview.update)
      
      self._name_preview.update(reset_items=True)
      
      if not self._is_initial_selection_set:
        self._set_initial_selection_and_update_image_preview()
      else:
        self._image_preview.update()
  
  def _enable_preview_on_paned_drag(
        self, preview, preview_sensitive_setting, update_lock_key):
    preview.lock_update(False, update_lock_key)
    preview.add_function_at_update(preview.set_sensitive, True)
    # In case the image preview gets resized, the update would be canceled,
    # hence update always.
    pg.invocation.timeout_add(
      self._DELAY_PREVIEWS_PANE_DRAG_UPDATE_MILLISECONDS, preview.update)
    preview_sensitive_setting.set_value(True)
  
  def _disable_preview_on_paned_drag(
        self, preview, preview_sensitive_setting, update_lock_key):
    preview.lock_update(True, update_lock_key)
    preview.set_sensitive(False)
    preview_sensitive_setting.set_value(False)
  
  def _set_initial_selection_and_update_image_preview(self):
    setting_value = self._settings['gui/image_preview_displayed_layers'].value[self._image.ID]
    
    if not setting_value:
      raw_item_id_to_display = None
    else:
      raw_item_id_to_display = list(setting_value)[0]
    
    if (raw_item_id_to_display is None
        and not self._settings['main/selected_layers'].value[self._image.ID]
        and self._image.active_layer is not None):
      raw_item_id_to_display = self._image.active_layer.ID
      # This triggers an event that updates the image preview as well.
      self._name_preview.set_selected_items([raw_item_id_to_display])
    else:
      self._image_preview.update_item(raw_item_id_to_display)
      self._image_preview.update()
    
    self._is_initial_selection_set = True
  
  def _update_selected_items(self):
    selected_items_dict = self._settings['main/selected_layers'].value
    selected_items_dict[self._image.ID] = self._name_preview.selected_items
    self._settings['main/selected_layers'].set_value(selected_items_dict)
  
  def _update_image_preview(self):
    item_from_cursor = self._name_preview.get_item_from_cursor()
    if item_from_cursor is not None:
      if (self._image_preview.item is None
          or item_from_cursor.raw.ID != self._image_preview.item.raw.ID
          or item_from_cursor.type != self._image_preview.item.type):
        self._image_preview.item = item_from_cursor
        self._image_preview.update()
    else:
      items_from_selected_rows = self._name_preview.get_items_from_selected_rows()
      if items_from_selected_rows:
        self._image_preview.item = items_from_selected_rows[0]
        self._image_preview.update()
      else:
        self._image_preview.clear()
