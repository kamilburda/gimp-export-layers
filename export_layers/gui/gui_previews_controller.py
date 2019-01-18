# -*- coding: utf-8 -*-
#
# This file is part of Export Layers.
#
# Copyright (C) 2013-2019 khalim19 <khalim19@gmail.com>
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
This module provides a class to interconnect the widgets displaying previews of
layer names and images to be exported.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

from export_layers.pygimplib import pggui
from export_layers.pygimplib import pginvocation

from export_layers import builtin_constraints
from export_layers import builtin_procedures


class ExportPreviewsController(object):
  
  _DELAY_PREVIEWS_SETTING_UPDATE_MILLISECONDS = 50
  _DELAY_PREVIEWS_PANE_DRAG_UPDATE_MILLISECONDS = 500
  
  def __init__(self, name_preview, image_preview, settings, image):
    self._name_preview = name_preview
    self._image_preview = image_preview
    self._settings = settings
    self._image = image
    
    self._only_selected_layers_constraints = {}
    self._custom_operations = {}
    self._is_initial_selection_set = False
    
    self._paned_outside_previews_previous_position = (
      self._settings["gui/paned_outside_previews_position"].value)
    self._paned_between_previews_previous_position = (
      self._settings["gui/paned_between_previews_position"].value)
  
  def connect_setting_changes_to_previews(self):
    self._connect_operations_changed(self._settings["main/procedures"])
    self._connect_operations_changed(self._settings["main/constraints"])
    
    self._connect_setting_after_reset_collapsed_layers_in_name_preview()
    self._connect_setting_after_reset_selected_layers_in_name_preview()
    self._connect_setting_after_reset_displayed_layers_in_image_preview()
    
    self._connect_toggle_name_preview_filtering()
    self._connect_set_image_preview_scaling()
    self._connect_image_preview_menu_setting_changes()
    
    self._connect_toplevel_notify_is_active()
  
  def connect_name_preview_events(self):
    self._name_preview.connect(
      "preview-selection-changed", self._on_name_preview_selection_changed)
    self._name_preview.connect(
      "preview-updated", self._on_name_preview_updated)
    self._name_preview.connect(
      "preview-tags-changed", self._on_name_preview_tags_changed)
  
  def on_paned_outside_previews_notify_position(self, paned, property_spec):
    current_position = paned.get_position()
    max_position = paned.get_property("max-position")
    
    if (current_position == max_position
        and self._paned_outside_previews_previous_position != max_position):
      self._disable_preview_on_paned_drag(
        self._name_preview,
        self._settings["gui/name_preview_sensitive"],
        "previews_sensitive")
      self._disable_preview_on_paned_drag(
        self._image_preview,
        self._settings["gui/image_preview_sensitive"],
        "previews_sensitive")
    elif (current_position != max_position
          and self._paned_outside_previews_previous_position == max_position):
      self._enable_preview_on_paned_drag(
        self._name_preview,
        self._settings["gui/name_preview_sensitive"],
        "previews_sensitive")
      self._enable_preview_on_paned_drag(
        self._image_preview,
        self._settings["gui/image_preview_sensitive"],
        "previews_sensitive")
    elif current_position != self._paned_outside_previews_previous_position:
      if self._image_preview.is_larger_than_image():
        pginvocation.timeout_add_strict(
          self._DELAY_PREVIEWS_PANE_DRAG_UPDATE_MILLISECONDS,
          self._image_preview.update)
      else:
        pginvocation.timeout_remove_strict(self._image_preview.update)
        self._image_preview.resize()
    
    self._paned_outside_previews_previous_position = current_position
  
  def on_paned_between_previews_notify_position(self, paned, property_spec):
    current_position = paned.get_position()
    max_position = paned.get_property("max-position")
    min_position = paned.get_property("min-position")
    
    if (current_position == max_position
        and self._paned_between_previews_previous_position != max_position):
      self._disable_preview_on_paned_drag(
        self._image_preview,
        self._settings["gui/image_preview_sensitive"],
        "vpaned_preview_sensitive")
    elif (current_position != max_position
          and self._paned_between_previews_previous_position == max_position):
      self._enable_preview_on_paned_drag(
        self._image_preview,
        self._settings["gui/image_preview_sensitive"],
        "vpaned_preview_sensitive")
    elif (current_position == min_position
          and self._paned_between_previews_previous_position != min_position):
      self._disable_preview_on_paned_drag(
        self._name_preview,
        self._settings["gui/name_preview_sensitive"],
        "vpaned_preview_sensitive")
    elif (current_position != min_position
          and self._paned_between_previews_previous_position == min_position):
      self._enable_preview_on_paned_drag(
        self._name_preview,
        self._settings["gui/name_preview_sensitive"],
        "vpaned_preview_sensitive")
    elif current_position != self._paned_between_previews_previous_position:
      if self._image_preview.is_larger_than_image():
        pginvocation.timeout_add_strict(
          self._DELAY_PREVIEWS_PANE_DRAG_UPDATE_MILLISECONDS,
          self._image_preview.update)
      else:
        pginvocation.timeout_remove_strict(self._image_preview.update)
        self._image_preview.resize()
    
    self._paned_between_previews_previous_position = current_position
  
  def _connect_operations_changed(self, operations_):
    def _on_after_add_operation(operations_, operation, *args, **kwargs):
      if operation["enabled"].value:
        self._update_previews_on_setting_change(operation["enabled"])
      operation["enabled"].connect_event(
        "value-changed", self._update_previews_on_setting_change)
    
    def _on_after_reorder_operation(operations_, operation, *args, **kwargs):
      if operation["enabled"].value:
        self._update_previews_on_setting_change(operation["enabled"])
    
    def _on_before_remove_operation(operations_, operation, *args, **kwargs):
      if operation["enabled"].value:
        # Changing the enabled state triggers the "value-changed" event and thus
        # properly keeps the previews in sync after operation removal.
        operation["enabled"].set_value(False)
    
    operations_.connect_event("after-add-operation", _on_after_add_operation)
    operations_.connect_event("after-reorder-operation", _on_after_reorder_operation)
    operations_.connect_event("before-remove-operation", _on_before_remove_operation)
  
  def _update_previews_on_setting_change(self, setting):
    pginvocation.timeout_add_strict(
      self._DELAY_PREVIEWS_SETTING_UPDATE_MILLISECONDS, self._name_preview.update)
    pginvocation.timeout_add_strict(
      self._DELAY_PREVIEWS_SETTING_UPDATE_MILLISECONDS, self._image_preview.update)
  
  def _connect_setting_after_reset_collapsed_layers_in_name_preview(self):
    self._settings[
      "gui_session/name_preview_layers_collapsed_state"].connect_event(
        "after-reset",
        lambda setting: self._name_preview.set_collapsed_items(
          setting.value[self._image.ID]))
  
  def _connect_setting_after_reset_selected_layers_in_name_preview(self):
    self._settings["main/selected_layers"].connect_event(
      "after-reset",
      lambda setting: self._name_preview.set_selected_items(
        setting.value[self._image.ID]))
  
  def _connect_setting_after_reset_displayed_layers_in_image_preview(self):
    def _clear_image_preview(setting):
      self._image_preview.clear()
    
    self._settings["gui_session/image_preview_displayed_layers"].connect_event(
      "after-reset", _clear_image_preview)
  
  def _connect_toggle_name_preview_filtering(self):
    def _after_add_only_selected_layers(constraints, constraint, orig_constraint_dict):
      if constraint["orig_name"].value == "only_selected_layers":
        self._only_selected_layers_constraints[constraint.name] = constraint
        
        _on_enabled_changed(constraint["enabled"])
        constraint["enabled"].connect_event("value-changed", _on_enabled_changed)
    
    def _before_remove_only_selected_layers(constraints, constraint):
      if constraint.name in self._only_selected_layers_constraints:
        del self._only_selected_layers_constraints[constraint.name]
    
    def _before_clear_constraints(constraints):
      self._only_selected_layers_constraints = {}
      self._name_preview.is_filtering = False
    
    def _on_enabled_changed(constraint_enabled):
      self._name_preview.is_filtering = (
        any(constraint["enabled"].value
            for constraint in self._only_selected_layers_constraints.values()))
    
    self._settings["main/constraints"].connect_event(
      "after-add-operation", _after_add_only_selected_layers)
    
    self._settings["main/constraints"].connect_event(
      "before-remove-operation", _before_remove_only_selected_layers)
    
    self._settings["main/constraints"].connect_event(
      "before-clear-operations", _before_clear_constraints)
  
  def _connect_set_image_preview_scaling(self):
    def _after_add_operation(
          operations, operation, orig_operation_dict, builtin_operations):
      if operation["orig_name"].value not in builtin_operations:
        self._custom_operations[operation.name] = operation
        
        _set_image_preview_scaling(operation["enabled"])
        operation["enabled"].connect_event("value-changed", _set_image_preview_scaling)
    
    def _before_remove_operation(operations, operation):
      if operation.name in self._custom_operations:
        del self._custom_operations[operation.name]
    
    def _before_clear_operations(operations):
      self._custom_operations = {}
      self._image_preview.set_scaling()
    
    def _set_image_preview_scaling(operation_enabled):
      if not any(operation["enabled"].value
                 for operation in self._custom_operations.values()):
        self._image_preview.set_scaling()
      else:
        self._image_preview.set_scaling(
          ["after_process_layer"], ["after_process_layer"])
    
    self._settings["main/procedures"].connect_event(
      "after-add-operation",
      _after_add_operation,
      builtin_procedures.BUILTIN_PROCEDURES)
    
    self._settings["main/procedures"].connect_event(
      "before-remove-operation", _before_remove_operation)
    
    self._settings["main/procedures"].connect_event(
      "before-clear-operations", _before_clear_operations)
    
    self._settings["main/constraints"].connect_event(
      "after-add-operation",
      _after_add_operation,
      builtin_constraints.BUILTIN_CONSTRAINTS)
    
    self._settings["main/constraints"].connect_event(
      "before-remove-operation", _before_remove_operation)
    
    self._settings["main/constraints"].connect_event(
      "before-clear-operations", _before_clear_operations)
  
  def _connect_image_preview_menu_setting_changes(self):
    def _on_preview_toggled_automatic_update(preview, automatic):
      self._settings["gui/image_preview_automatic_update"].set_value(automatic)
    
    self._settings["gui/image_preview_automatic_update"].connect_event(
      "value-changed",
      lambda setting, update_if_below_setting: update_if_below_setting.set_value(False),
      self._settings[
        "gui/image_preview_automatic_update_if_below_maximum_duration"])
    
    self._image_preview.connect(
      "preview-toggled-automatic-update", _on_preview_toggled_automatic_update)
  
  def _connect_toplevel_notify_is_active(self):
    toplevel = (
      pggui.get_toplevel_window(self._name_preview)
      or pggui.get_toplevel_window(self._image_preview))
    if toplevel is not None:
      toplevel.connect("notify::is-active", self._on_toplevel_notify_is_active)
   
  def _on_name_preview_selection_changed(self, preview):
    self._update_selected_layers()
    self._update_image_preview()
  
  def _on_name_preview_updated(self, preview):
    self._image_preview.update_layer_elem()
  
  def _on_name_preview_tags_changed(self, preview):
    self._update_image_preview()
  
  def _on_toplevel_notify_is_active(self, toplevel, property_spec):
    if toplevel.is_active():
      pginvocation.timeout_remove_strict(self._name_preview.update)
      pginvocation.timeout_remove_strict(self._image_preview.update)
      
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
    pginvocation.timeout_add(
      self._DELAY_PREVIEWS_PANE_DRAG_UPDATE_MILLISECONDS, preview.update)
    preview_sensitive_setting.set_value(True)
  
  def _disable_preview_on_paned_drag(
        self, preview, preview_sensitive_setting, update_lock_key):
    preview.lock_update(True, update_lock_key)
    preview.set_sensitive(False)
    preview_sensitive_setting.set_value(False)
  
  def _set_initial_selection_and_update_image_preview(self):
    layer_id_to_display = self._settings[
      "gui_session/image_preview_displayed_layers"].value[self._image.ID]
    
    if (layer_id_to_display is None
        and not self._settings["main/selected_layers"].value[self._image.ID]
        and self._image.active_layer is not None):
      layer_id_to_display = self._image.active_layer.ID
      # This triggers an event that updates the image preview as well.
      self._name_preview.set_selected_items([layer_id_to_display])
    else:
      self._image_preview.update_layer_elem(layer_id_to_display)
      self._image_preview.update()
    
    self._is_initial_selection_set = True
  
  def _update_selected_layers(self):
    selected_layers_dict = self._settings["main/selected_layers"].value
    selected_layers_dict[self._image.ID] = self._name_preview.selected_items
    self._settings["main/selected_layers"].set_value(selected_layers_dict)
  
  def _update_image_preview(self):
    layer_elem_from_cursor = self._name_preview.get_layer_elem_from_cursor()
    if layer_elem_from_cursor is not None:
      if (self._image_preview.layer_elem is None
          or (layer_elem_from_cursor.item.ID != self._image_preview.layer_elem.item.ID)):
        self._image_preview.layer_elem = layer_elem_from_cursor
        self._image_preview.update()
    else:
      layer_elems_from_selected_rows = (
        self._name_preview.get_layer_elems_from_selected_rows())
      if layer_elems_from_selected_rows:
        self._image_preview.layer_elem = layer_elems_from_selected_rows[0]
        self._image_preview.update()
      else:
        self._image_preview.clear()
