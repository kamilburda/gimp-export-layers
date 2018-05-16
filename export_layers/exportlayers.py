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
This module is the core of the plug-in and provides a class to export layers as
separate images.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *
import future.utils

import collections
import contextlib
import datetime
import os
import re

from gimp import pdb
import gimpenums

from export_layers import pygimplib
from export_layers.pygimplib import pgconstants
from export_layers.pygimplib import pgfileformats
from export_layers.pygimplib import pgitemtree
from export_layers.pygimplib import pgobjectfilter
from export_layers.pygimplib import pgoperations
from export_layers.pygimplib import pgoverwrite
from export_layers.pygimplib import pgpath
from export_layers.pygimplib import pgpdb
from export_layers.pygimplib import pgprogress
from export_layers.pygimplib import pgutils

from . import builtin_operations
from . import builtin_constraints

#===============================================================================


@future.utils.python_2_unicode_compatible
class ExportLayersError(Exception):
  
  def __init__(self, message="", layer=None, file_extension=None):
    super().__init__()
    
    self._message = message
    
    try:
      self.layer_name = layer.name
    except AttributeError:
      self.layer_name = None
    
    self.file_extension = file_extension
  
  def __str__(self):
    str_ = self._message
    
    if self.layer_name:
      str_ += "\n" + _("Layer:") + " " + self.layer_name
    if self.file_extension:
      str_ += "\n" + _("File extension:") + " " + self.file_extension
    
    return str_


class ExportLayersCancelError(ExportLayersError):
  pass


class InvalidOutputDirectoryError(ExportLayersError):
  pass


#===============================================================================


def execute_operation_only_if_setting(operation, setting):
  def _execute_operation_only_if_setting(*operation_args, **operation_kwargs):
    if setting.value:
      return operation(*operation_args, **operation_kwargs)
    else:
      return False
  
  return _execute_operation_only_if_setting


#===============================================================================


def _add_constraint(rule_func, subfilter=None):
  def _add_rule_func(*args):
    # HACK: This assumes that `LayerExporter` instance is added as an argument
    # when executing the default group for constraints.
    layer_exporter = args[-1]
    rule_func_args = args[1:]
    
    if subfilter is None:
      object_filter = layer_exporter.layer_tree.filter
    else:
      object_filter = layer_exporter.layer_tree.filter[subfilter]
    
    object_filter.add_rule(rule_func, *rule_func_args)
  
  return _add_rule_func


def _add_constraint_with_layer_exporter(rule_func):
  def _add_rule_func_with_layer_exporter(*args):
    # HACK: This assumes that `LayerExporter` instance is added as an argument
    # when executing the default group for constraints.
    layer_exporter = args[-1]
    layer_exporter.layer_tree.filter.add_rule(rule_func, *args)
  
  return _add_rule_func_with_layer_exporter


#===============================================================================


class LayerNameRenamer(object):
  
  LAYER_NAME_PATTERN_FIELDS = [
    ("image001", "image[001]", []),
    (_("Layer name"),
     "[layer name]",
     ["keep extension",
      "keep only identical extension"]),
    (_("Image name"), "[image name]", ["keep extension"]),
    (_("Layer path"), "[layer path]", ["separator, wrapper"]),
    (_("Tags"),
     "[tags]",
     ["specific tags...",
      "separator, wrapper, specific tags..."]),
    (_("Current date"), "[current date]", ["%Y-%m-%d"]),
  ]
  
  def __init__(self, layer_exporter, pattern):
    self._layer_exporter = layer_exporter
    
    self._filename_pattern_generator = pgpath.StringPatternGenerator(
      pattern=pattern,
      fields=self._get_fields_for_layer_filename_pattern())
    
    # key: _ItemTreeElement parent ID (None for root)
    # value: list of pattern number generators
    self._pattern_number_filename_generators = {
      None: self._filename_pattern_generator.get_number_generators()}
  
  def rename(self, layer_elem):
    parent = layer_elem.parent.item.ID if layer_elem.parent is not None else None
    if parent not in self._pattern_number_filename_generators:
      self._pattern_number_filename_generators[parent] = (
        self._filename_pattern_generator.reset_numbering())
    else:
      self._filename_pattern_generator.set_number_generators(
        self._pattern_number_filename_generators[parent])
    
    layer_elem.name = self._filename_pattern_generator.generate()
  
  def _get_fields_for_layer_filename_pattern(self):
    return {"layer name": self._get_layer_name,
            "image name": self._get_image_name,
            "layer path": self._get_layer_path,
            "current date": self._get_current_date,
            "tags": self._get_tags}
  
  def _get_layer_name(self, file_extension_strip_mode=None):
    layer_elem = self._layer_exporter.current_layer_elem
    
    if file_extension_strip_mode in ["keep extension", "keep only identical extension"]:
      file_extension = layer_elem.get_file_extension_from_orig_name()
      if file_extension:
        if file_extension_strip_mode == "keep only identical extension":
          if file_extension == self._layer_exporter.default_file_extension:
            return layer_elem.name
        else:
          return layer_elem.name
    
    return layer_elem.get_base_name()
  
  def _get_image_name(self, keep_extension=False):
    image_name = (
      self._layer_exporter.image.name if self._layer_exporter.image.name is not None
      else _("Untitled"))
    
    if keep_extension == "keep extension":
      return image_name
    else:
      return pgpath.get_filename_with_new_file_extension(image_name, "")
  
  def _get_layer_path(self, separator="-", wrapper=None):
    if wrapper is None:
      wrapper = "{0}"
    else:
      path_component_token = "$$"
      
      if path_component_token in wrapper:
        wrapper = wrapper.replace(path_component_token, "{0}")
      else:
        wrapper = "{0}"
    
    path_components = (
      [parent.name for parent in self._layer_exporter.current_layer_elem.parents]
      + [self._layer_exporter.current_layer_elem.name])
    
    return separator.join(
      [wrapper.format(path_component) for path_component in path_components])
  
  @staticmethod
  def _get_current_date(date_format="%Y-%m-%d"):
    return datetime.datetime.now().strftime(date_format)
  
  def _get_tags(self, *args):
    tags_to_insert = []
    
    def _insert_tag(tag):
      if tag in self._layer_exporter.BUILTIN_TAGS:
        tag_display_name = self._layer_exporter.BUILTIN_TAGS[tag]
      else:
        tag_display_name = tag
      tags_to_insert.append(tag_display_name)
    
    def _get_tag_from_tag_display_name(tag_display_name):
      builtin_tags_keys = list(self._layer_exporter.BUILTIN_TAGS)
      builtin_tags_values = list(self._layer_exporter.BUILTIN_TAGS.values())
      return builtin_tags_keys[builtin_tags_values.index(tag_display_name)]
    
    def _insert_all_tags():
      for tag in self._layer_exporter.current_layer_elem.tags:
        _insert_tag(tag)
    
    def _insert_specified_tags(tags):
      for tag in tags:
        if tag in self._layer_exporter.BUILTIN_TAGS:
          continue
        if tag in self._layer_exporter.BUILTIN_TAGS.values():
          tag = _get_tag_from_tag_display_name(tag)
        if tag in self._layer_exporter.current_layer_elem.tags:
          _insert_tag(tag)
    
    tag_separator = " "
    tag_wrapper = "[{0}]"
    tag_token = "$$"
    
    if not args:
      _insert_all_tags()
    else:
      if len(args) < 2:
        _insert_specified_tags(args)
      else:
        if tag_token in args[1]:
          tag_separator = args[0]
          tag_wrapper = args[1].replace(tag_token, "{0}")
          
          if len(args) > 2:
            _insert_specified_tags(args[2:])
          else:
            _insert_all_tags()
        else:
          _insert_specified_tags(args)
    
    tags_to_insert.sort(key=lambda tag: tag.lower())
    return tag_separator.join([tag_wrapper.format(tag) for tag in tags_to_insert])


#===============================================================================


class _FileExtension(object):
  """
  This class defines additional properties for a file extension.
  
  Attributes:
  
  * `is_valid` - If True, file extension is valid and can be used in filenames
    for file export procedures.
  
  * `processed_count` - Number of items with the specific file extension that
    have already been exported.
  """
  
  def __init__(self):
    self.is_valid = True
    self.processed_count = 0


def _get_prefilled_file_extension_properties():
  file_extension_properties = collections.defaultdict(_FileExtension)
  
  for file_format in pgfileformats.file_formats:
    # This ensures that the file format dialog will be displayed only once per
    # file format if multiple file extensions for the same format are used
    # (e.g. "jpg", "jpeg" or "jpe" for the JPEG format).
    extension_properties = _FileExtension()
    for file_extension in file_format.file_extensions:
      file_extension_properties[file_extension] = extension_properties
  
  return file_extension_properties


#===============================================================================


class ExportStatuses(object):
  EXPORT_STATUSES = (
    NOT_EXPORTED_YET, EXPORT_SUCCESSFUL, FORCE_INTERACTIVE, USE_DEFAULT_FILE_EXTENSION
  ) = (0, 1, 2, 3)


#===============================================================================

_BUILTIN_OPERATIONS_GROUP = "process_layer"
_BUILTIN_CONSTRAINTS_GROUP = "set_constraints"
_BUILTIN_CONSTRAINTS_LAYER_TYPES_GROUP = "set_constraints_layer_types"

_BUILTIN_OPERATIONS_AND_SETTINGS = {
  "ignore_layer_modes": [builtin_operations.ignore_layer_modes],
  "autocrop": [builtin_operations.autocrop_layer],
  "inherit_transparency_from_layer_groups": [
    builtin_operations.inherit_transparency_from_layer_groups],
  "insert_background_layers": [
    builtin_operations.insert_background_layer, ["background"]],
  "insert_foreground_layers": [
    builtin_operations.insert_foreground_layer, ["foreground"]],
  "autocrop_background": [builtin_operations.autocrop_tagged_layer, ["background"]],
  "autocrop_foreground": [builtin_operations.autocrop_tagged_layer, ["foreground"]]
}

_BUILTIN_CONSTRAINTS_AND_SETTINGS = {
  "only_layers_without_tags": [_add_constraint(builtin_constraints.has_no_tags)],
  "only_layers_with_tags": [_add_constraint(builtin_constraints.has_tags)],
  "only_layers_matching_file_extension": [
    _add_constraint_with_layer_exporter(
      builtin_constraints.has_matching_default_file_extension)],
  "only_toplevel_layers": [_add_constraint(builtin_constraints.is_top_level)]
}

_BUILTIN_INCLUDE_CONSTRAINTS_AND_SETTINGS = {
  "include_layers": [
    _add_constraint(builtin_constraints.is_layer, subfilter="layer_types")],
  "include_layer_groups": [
    _add_constraint(builtin_constraints.is_nonempty_group, subfilter="layer_types")],
  "include_empty_layer_groups": [
    _add_constraint(builtin_constraints.is_empty_group, subfilter="layer_types")]
}

# key: setting name; value: (operation ID, operation group) tuple
_operation_settings_and_items = {}

_operation_executor = pgoperations.OperationExecutor()


def add_operation(base_setting):
  if (base_setting.name in _BUILTIN_OPERATIONS_AND_SETTINGS
      or base_setting.name in _BUILTIN_CONSTRAINTS_AND_SETTINGS
      or base_setting.name in _BUILTIN_INCLUDE_CONSTRAINTS_AND_SETTINGS):
    if base_setting.name in _BUILTIN_OPERATIONS_AND_SETTINGS:
      operation_item = _BUILTIN_OPERATIONS_AND_SETTINGS[base_setting.name]
      operation_group = _BUILTIN_OPERATIONS_GROUP
    elif base_setting.name in _BUILTIN_CONSTRAINTS_AND_SETTINGS:
      operation_item = _BUILTIN_CONSTRAINTS_AND_SETTINGS[base_setting.name]
      operation_group = _BUILTIN_CONSTRAINTS_GROUP
    elif base_setting.name in _BUILTIN_INCLUDE_CONSTRAINTS_AND_SETTINGS:
      operation_item = _BUILTIN_INCLUDE_CONSTRAINTS_AND_SETTINGS[base_setting.name]
      operation_group = _BUILTIN_CONSTRAINTS_LAYER_TYPES_GROUP
    
    operation = operation_item[0]
    operation_args = operation_item[1] if len(operation_item) > 1 else ()
    operation_kwargs = operation_item[2] if len(operation_item) > 2 else {}
    
    operation_id = _operation_executor.add_operation(
      execute_operation_only_if_setting(operation, base_setting),
      [operation_group],
      *operation_args, **operation_kwargs)
    
    _operation_settings_and_items[base_setting.name] = (operation_id, operation_group)


def reorder_operation(setting, new_position):
  if setting.name in _operation_settings_and_items:
    _operation_executor.reorder_operation(
      _operation_settings_and_items[setting.name][0],
      _operation_settings_and_items[setting.name][1], new_position)


def remove_operation(setting):
  if setting.name in _operation_settings_and_items:
    _operation_executor.remove_operation(_operation_settings_and_items[setting.name][0])


def is_valid_operation(base_setting):
  return any(
    base_setting.name in builtin_operations_or_constraints
    for builtin_operations_or_constraints in [
      _BUILTIN_OPERATIONS_AND_SETTINGS,
      _BUILTIN_CONSTRAINTS_AND_SETTINGS,
      _BUILTIN_INCLUDE_CONSTRAINTS_AND_SETTINGS])


_operation_executor.add_foreach_operation(
  builtin_operations.set_active_layer_after_operation, [_BUILTIN_OPERATIONS_GROUP])

#===============================================================================


def _copy_non_modifying_parasites(src_image, dest_image):
  unused_, parasite_names = pdb.gimp_image_get_parasite_list(src_image)
  for parasite_name in parasite_names:
    if dest_image.parasite_find(parasite_name) is None:
      parasite = src_image.parasite_find(parasite_name)
      # Don't attach persistent or undoable parasites to avoid modifying
      # `dest_image`.
      if parasite.flags == 0:
        dest_image.parasite_attach(parasite)


#===============================================================================


class LayerExporter(object):
  
  """
  This class exports layers as separate images, with the support for additional
  operations applied on layers (resize, rename, ...).
  
  Attributes:
  
  * `initial_run_mode` - The run mode to use for the first layer exported.
    For subsequent layers, `gimpenums.RUN_WITH_LAST_VALS` is used. If the file
    format in which the layer is exported to can't handle
    `gimpenums.RUN_WITH_LAST_VALS`, `gimpenums.RUN_INTERACTIVE` is used.
  
  * `image` - GIMP image to export layers from.
  
  * `export_settings` - `SettingGroup` instance containing export settings. This
    class treats them as read-only.
  
  * `overwrite_chooser` - `OverwriteChooser` instance that is invoked if a file
    with the same name already exists. If None is passed during initialization,
    `pgoverwrite.NoninteractiveOverwriteChooser` is used by default.
  
  * `progress_updater` - `ProgressUpdater` instance that indicates the number of
    layers exported. If no progress update is desired, pass None.
  
  * `layer_tree` - `LayerTree` instance containing layers to be exported.
    Defaults to None if no export has been performed yet.
  
  * `exported_layers` - List of layers that were successfully exported. Does not
    include skipped layers (when files with the same names already exist).
  
  * `export_context_manager` - Context manager that wraps exporting a single
    layer. This can be used to perform GUI updates before and after export.
    Required parameters: current run mode, current image, layer to export,
    output filename of the layer.
  
  * `export_context_manager_args` - Additional arguments passed to
    `export_context_manager`.
  
  * `current_layer_elem` (read-only) - The `pgitemtree._ItemTreeElement`
    instance being currently exported.
  
  * `operation_executor` - `pgoperations.OperationExecutor` instance to manage
    operations applied on layers.
  """
  
  BUILTIN_TAGS = {
    "background": _("Background"),
    "foreground": _("Foreground")
  }
  
  def __init__(
        self, initial_run_mode, image, export_settings,
        overwrite_chooser=None, progress_updater=None, layer_tree=None,
        export_context_manager=None, export_context_manager_args=None):
    
    self.initial_run_mode = initial_run_mode
    self.image = image
    self.export_settings = export_settings
    
    self.overwrite_chooser = (
      overwrite_chooser if overwrite_chooser is not None
      else pgoverwrite.NoninteractiveOverwriteChooser(
        self.export_settings["overwrite_mode"].value))
    
    self.progress_updater = (
      progress_updater if progress_updater is not None
      else pgprogress.ProgressUpdater(None))
    
    self._layer_tree = layer_tree
    
    self.export_context_manager = (
      export_context_manager if export_context_manager is not None
      else pgutils.EmptyContext)
    
    self.export_context_manager_args = (
      export_context_manager_args if export_context_manager_args is not None else [])
    
    self._exported_layers = []
    self._exported_layers_ids = set()
    self._current_layer_elem = None
    self._default_file_extension = None
    
    self._should_stop = False
    
    self._processing_groups = {
      "layer_contents": [
        self._setup, self._cleanup, self._process_layer, self._postprocess_layer],
      "layer_name": [
        self._preprocess_layer_name, self._preprocess_empty_group_name,
        self._process_layer_name],
      "_postprocess_layer_name": [self._postprocess_layer_name],
      "export": [self._make_dirs, self._export]
    }
    
    self._processing_groups_functions = {}
    for functions in self._processing_groups.values():
      for function in functions:
        self._processing_groups_functions[function.__name__] = function
    
    self._operation_executor = pgoperations.OperationExecutor()
    self._add_operations_initial()
  
  @property
  def layer_tree(self):
    return self._layer_tree
  
  @property
  def exported_layers(self):
    return self._exported_layers
  
  @property
  def current_layer_elem(self):
    return self._current_layer_elem
  
  @property
  def default_file_extension(self):
    return self._default_file_extension
  
  @property
  def tagged_layer_elems(self):
    return self._tagged_layer_elems
  
  @property
  def inserted_tagged_layers(self):
    return self._inserted_tagged_layers
  
  @property
  def tagged_layer_copies(self):
    return self._tagged_layer_copies
  
  @property
  def operation_executor(self):
    return self._operation_executor
  
  def export(self, processing_groups=None, layer_tree=None, keep_image_copy=False):
    """
    Export layers as separate images from the specified image.
    
    `processing_groups` is a list of strings that constrains the execution of
    the export. Multiple groups can be specified. The following groups are
    supported:
    
    * "layer_contents" - Perform only operations manipulating the layer itself,
      such as cropping, resizing, etc. This is useful to preview the layer(s).
    
    * "layer_name" - Perform only operations manipulating layer names and layer
      tree (but not layer contents). This is useful to preview the names of the
      exported layers.
    
    * "export" - Perform only operations that export the layer or create
      directories for the layer.
    
    If `processing_groups` is None or empty, perform normal export.
    
    If `layer_tree` is not None, use an existing instance of
    `pgitemtree.LayerTree` instead of creating a new one. If the instance had
    constraints set, they will be reset.
    
    A copy of the image and the layers to be exported are created so that the
    original image and its soon-to-be exported layers are left intact. The
    image copy is automatically destroyed after the export. To keep the image
    copy, pass True to `keep_image_copy`. In that case, this method returns the
    image copy. If an exception was raised or if no layer was exported, this
    method returns None and the image copy will be destroyed.
    """
    
    self._init_attributes(processing_groups, layer_tree, keep_image_copy)
    self._preprocess_layers()
    
    exception_occurred = False
    
    self._setup()
    try:
      self._export_layers()
    except Exception:
      exception_occurred = True
      raise
    finally:
      self._cleanup(exception_occurred)
    
    if self._keep_image_copy:
      if self._use_another_image_copy:
        return self._another_image_copy
      else:
        return self._image_copy
    else:
      return None
  
  def has_exported_layer(self, layer):
    """
    Return True if the specified `gimp.Layer` was exported in the last export,
    False otherwise.
    """
    
    return layer.ID in self._exported_layers_ids
  
  @contextlib.contextmanager
  def modify_export_settings(
        self, export_settings_to_modify, settings_events_to_temporarily_disable=None):
    """
    Temporarily modify export settings specified as a dict of
    (setting name: new setting value) pairs. After the execution of the wrapped
    block of code, the settings are restored to their original values.
    
    Any events connected to the settings triggered by the `set_value` method
    will be executed.
    
    `settings_events_to_temporarily_disable` is a dict of
    {setting name: list of event IDs} pairs that temporarily disables events
    specified by their IDs for the specified settings.
    """
    
    if settings_events_to_temporarily_disable is None:
      settings_events_to_temporarily_disable = {}
    
    for setting_name, event_ids in settings_events_to_temporarily_disable.items():
      for event_id in event_ids:
        self.export_settings[setting_name].set_event_enabled(event_id, False)
    
    orig_setting_values = {}
    for setting_name, new_value in export_settings_to_modify.items():
      orig_setting_values[setting_name] = self.export_settings[setting_name].value
      self.export_settings[setting_name].set_value(new_value)
    
    try:
      yield
    finally:
      for setting_name, orig_value in orig_setting_values.items():
        self.export_settings[setting_name].set_value(orig_value)
      
      for setting_name, event_ids in settings_events_to_temporarily_disable.items():
        for event_id in event_ids:
          self.export_settings[setting_name].set_event_enabled(event_id, True)
  
  def stop(self):
    self._should_stop = True
  
  def _add_operations_initial(self):
    self._operation_executor.add_operation(
      builtin_operations.set_active_layer, [_BUILTIN_OPERATIONS_GROUP])
    
    self._operation_executor.add_executor(
      _operation_executor,
      [_BUILTIN_OPERATIONS_GROUP, _BUILTIN_CONSTRAINTS_GROUP,
       _BUILTIN_CONSTRAINTS_LAYER_TYPES_GROUP])
    
    add_operation(self.export_settings["constraints/include/include_layers"])
  
  def _init_attributes(self, processing_groups, layer_tree, keep_image_copy):
    self._enable_disable_processing_groups(processing_groups)
    
    if layer_tree is not None:
      self._layer_tree = layer_tree
    else:
      self._layer_tree = pgitemtree.LayerTree(
        self.image, name=pygimplib.config.SOURCE_PERSISTENT_NAME, is_filtered=True)
    
    self._keep_image_copy = keep_image_copy
    
    self._should_stop = False
    
    self._exported_layers = []
    self._exported_layers_ids = set()
    
    self._current_layer_elem = None
    
    self._output_directory = self.export_settings["output_directory"].value
    
    self._image_copy = None
    self._tagged_layer_elems = collections.defaultdict(list)
    self._tagged_layer_copies = collections.defaultdict(pgutils.return_none_func)
    self._inserted_tagged_layers = collections.defaultdict(pgutils.return_none_func)
    
    self._use_another_image_copy = False
    self._another_image_copy = None
    
    self.progress_updater.reset()
    
    self._file_extension_properties = _get_prefilled_file_extension_properties()
    self._default_file_extension = (
      self.export_settings["file_extension"].value.lstrip(".").lower())
    self._current_file_extension = self._default_file_extension
    self._current_layer_export_status = ExportStatuses.NOT_EXPORTED_YET
    self._current_overwrite_mode = None
    
    if self.export_settings["layer_filename_pattern"].value:
      pattern = self.export_settings["layer_filename_pattern"].value
    else:
      pattern = self.export_settings["layer_filename_pattern"].default_value
    
    self._layer_name_renamer = LayerNameRenamer(self, pattern)
  
  def _enable_disable_processing_groups(self, processing_groups):
    for functions in self._processing_groups.values():
      for function in functions:
        setattr(
          self, function.__name__, self._processing_groups_functions[function.__name__])
    
    if processing_groups:
      if (not self.export_settings["constraints/only_selected_layers"].value
          and "layer_name" in processing_groups):
        processing_groups.append("_postprocess_layer_name")
      
      for processing_group, functions in self._processing_groups.items():
        if processing_group not in processing_groups:
          for function in functions:
            setattr(self, function.__name__, pgutils.empty_func)
  
  def _preprocess_layers(self):
    if self._layer_tree.filter:
      self._layer_tree.reset_filter()
    
    if not self.export_settings["layer_groups_as_folders"].value:
      self._remove_parents_in_layer_elems()
    else:
      self._reset_parents_in_layer_elems()
    
    self._set_layer_constraints()
    
    self.progress_updater.num_total_tasks = len(self._layer_tree)
    
    if self._keep_image_copy:
      with self._layer_tree.filter["layer_types"].remove_rule_temp(
             builtin_constraints.is_empty_group, False):
        num_layers_and_nonempty_groups = len(self._layer_tree)
        if num_layers_and_nonempty_groups > 1:
          self._use_another_image_copy = True
        elif num_layers_and_nonempty_groups < 1:
          self._keep_image_copy = False
  
  def _remove_parents_in_layer_elems(self):
    for layer_elem in self._layer_tree:
      layer_elem.parents = []
      layer_elem.children = None if layer_elem.item_type == layer_elem.ITEM else []
  
  def _reset_parents_in_layer_elems(self):
    for layer_elem in self._layer_tree:
      layer_elem.parents = list(layer_elem.orig_parents)
      layer_elem.children = (
        list(layer_elem.orig_children) if layer_elem.orig_children is not None else None)
  
  def _set_layer_constraints(self):
    self._layer_tree.filter.add_subfilter(
      "layer_types", pgobjectfilter.ObjectFilter(pgobjectfilter.ObjectFilter.MATCH_ANY))
    
    self._operation_executor.execute([_BUILTIN_CONSTRAINTS_LAYER_TYPES_GROUP], self)
    
    self._init_tagged_layer_elems()
    
    if self.export_settings["only_visible_layers"].value:
      self._layer_tree.filter.add_rule(builtin_constraints.is_path_visible)
    
    if self.export_settings["constraints/only_selected_layers"].value:
      self._layer_tree.filter.add_rule(
        builtin_constraints.is_layer_in_selected_layers,
        self.export_settings["selected_layers"].value[self.image.ID])
    
    self._operation_executor.execute([_BUILTIN_CONSTRAINTS_GROUP], self)
  
  def _init_tagged_layer_elems(self):
    with self._layer_tree.filter.add_rule_temp(builtin_constraints.has_tags):
      with self._layer_tree.filter["layer_types"].add_rule_temp(
             builtin_constraints.is_nonempty_group):
        for layer_elem in self._layer_tree:
          for tag in layer_elem.tags:
            self._tagged_layer_elems[tag].append(layer_elem)
  
  def _export_layers(self):
    for layer_elem in self._layer_tree:
      if self._should_stop:
        raise ExportLayersCancelError("export stopped by user")
      
      self._current_layer_elem = layer_elem
      
      if layer_elem.item_type in (layer_elem.ITEM, layer_elem.NONEMPTY_GROUP):
        self._process_and_export_item(layer_elem)
      elif layer_elem.item_type == layer_elem.EMPTY_GROUP:
        self._process_empty_group(layer_elem)
      else:
        raise ValueError(
          "invalid/unsupported item type '{0}' in {1}".format(
            layer_elem.item_type, layer_elem))
  
  def _process_and_export_item(self, layer_elem):
    layer = layer_elem.item
    layer_copy = self._process_layer(layer_elem, self._image_copy, layer)
    self._preprocess_layer_name(layer_elem)
    self._export_layer(layer_elem, self._image_copy, layer_copy)
    self._postprocess_layer(self._image_copy, layer_copy)
    self._postprocess_layer_name(layer_elem)
    
    self.progress_updater.update_tasks()
    
    if self._current_overwrite_mode != pgoverwrite.OverwriteModes.SKIP:
      self._exported_layers.append(layer)
      self._exported_layers_ids.add(layer.ID)
      self._file_extension_properties[self._current_file_extension].processed_count += 1
  
  def _process_empty_group(self, layer_elem):
    self._preprocess_empty_group_name(layer_elem)
    
    empty_group_dirpath = layer_elem.get_filepath(self._output_directory)
    self._make_dirs(empty_group_dirpath, self)
    
    self.progress_updater.update_text(
      _('Creating empty directory "{0}"').format(empty_group_dirpath))
    self.progress_updater.update_tasks()
  
  def _setup(self):
    pdb.gimp_context_push()
    
    self._image_copy = pgpdb.create_image_from_metadata(self.image)
    pdb.gimp_image_undo_freeze(self._image_copy)
    
    self._operation_executor.execute(["after_create_image_copy"], self._image_copy)
    
    if self._use_another_image_copy:
      self._another_image_copy = pgpdb.create_image_from_metadata(self._image_copy)
      pdb.gimp_image_undo_freeze(self._another_image_copy)
    
    if pygimplib.config.DEBUG_IMAGE_PROCESSING:
      self._display_id = pdb.gimp_display_new(self._image_copy)
  
  def _cleanup(self, exception_occurred=False):
    if pygimplib.config.DEBUG_IMAGE_PROCESSING:
      pdb.gimp_display_delete(self._display_id)
    
    _copy_non_modifying_parasites(self._image_copy, self.image)
    
    pdb.gimp_image_undo_thaw(self._image_copy)
    if ((not self._keep_image_copy or self._use_another_image_copy)
        or exception_occurred):
      pdb.gimp_image_delete(self._image_copy)
      if self._use_another_image_copy:
        pdb.gimp_image_undo_thaw(self._another_image_copy)
        if exception_occurred:
          pdb.gimp_image_delete(self._another_image_copy)
    
    for tagged_layer_copy in self._tagged_layer_copies.values():
      if tagged_layer_copy is not None:
        pdb.gimp_item_delete(tagged_layer_copy)
    
    pdb.gimp_context_pop()
  
  def _process_layer(self, layer_elem, image, layer):
    layer_copy = builtin_operations.copy_and_insert_layer(image, layer, None, 0)
    self._operation_executor.execute(["after_insert_layer"], image, layer_copy, self)
    
    self._operation_executor.execute(
      [_BUILTIN_OPERATIONS_GROUP], image, layer_copy, self)
    
    layer_copy = self._merge_and_resize_layer(image, layer_copy)
    
    image.active_layer = layer_copy
    
    layer_copy.name = layer.name
    
    return layer_copy
  
  def _postprocess_layer(self, image, layer):
    if not self._keep_image_copy:
      pdb.gimp_image_remove_layer(image, layer)
    else:
      if self._use_another_image_copy:
        another_layer_copy = pdb.gimp_layer_new_from_drawable(
          layer, self._another_image_copy)
        pdb.gimp_image_insert_layer(
          self._another_image_copy, another_layer_copy, None,
          len(self._another_image_copy.layers))
        another_layer_copy.name = layer.name
        
        pdb.gimp_image_remove_layer(image, layer)
  
  def _merge_and_resize_layer(self, image, layer):
    if not self.export_settings["use_image_size"].value:
      layer_offset_x, layer_offset_y = layer.offsets
      pdb.gimp_image_resize(
        image, layer.width, layer.height, -layer_offset_x, -layer_offset_y)
    
    layer = pdb.gimp_image_merge_visible_layers(image, gimpenums.EXPAND_AS_NECESSARY)
    
    pdb.gimp_layer_resize_to_image_size(layer)
    
    return layer
  
  def _preprocess_layer_name(self, layer_elem):
    self._layer_name_renamer.rename(layer_elem)
    self._set_file_extension(layer_elem)
    self._layer_tree.validate_name(layer_elem)
  
  def _preprocess_empty_group_name(self, layer_elem):
    self._layer_tree.validate_name(layer_elem)
    self._layer_tree.uniquify_name(layer_elem)
  
  def _process_layer_name(self, layer_elem):
    self._layer_tree.uniquify_name(
      layer_elem, uniquifier_position=self._get_uniquifier_position(layer_elem.name))
  
  def _postprocess_layer_name(self, layer_elem):
    if layer_elem.item_type == layer_elem.NONEMPTY_GROUP:
      self._layer_tree.reset_name(layer_elem)
  
  def _set_file_extension(self, layer_elem):
    if self.export_settings["operations/use_file_extensions_in_layer_names"].value:
      orig_file_extension = layer_elem.get_file_extension_from_orig_name()
      if (orig_file_extension
          and self._file_extension_properties[orig_file_extension].is_valid):
        self._current_file_extension = orig_file_extension
      else:
        self._current_file_extension = self._default_file_extension
      layer_elem.set_file_extension(
        self._current_file_extension, keep_extra_trailing_periods=True)
    else:
      layer_elem.name += "." + self._current_file_extension
  
  def _get_uniquifier_position(self, str_):
    return len(str_) - len("." + self._current_file_extension)
  
  def _export_layer(self, layer_elem, image, layer):
    self._process_layer_name(layer_elem)
    self._export(layer_elem, image, layer)
    
    if self._current_layer_export_status == ExportStatuses.USE_DEFAULT_FILE_EXTENSION:
      self._set_file_extension(layer_elem)
      self._process_layer_name(layer_elem)
      self._export(layer_elem, image, layer)
  
  def _export(self, layer_elem, image, layer):
    output_filepath = layer_elem.get_filepath(self._output_directory)
    
    self.progress_updater.update_text(_('Saving "{0}"').format(output_filepath))
    
    self._current_overwrite_mode, output_filepath = pgoverwrite.handle_overwrite(
      output_filepath, self.overwrite_chooser,
      self._get_uniquifier_position(output_filepath))
    
    if self._current_overwrite_mode == pgoverwrite.OverwriteModes.CANCEL:
      raise ExportLayersCancelError("cancelled")
    
    if self._current_overwrite_mode != pgoverwrite.OverwriteModes.SKIP:
      self._make_dirs(os.path.dirname(output_filepath), self)
      
      self._export_once_wrapper(
        self._get_export_func(), self._get_run_mode(), image, layer, output_filepath)
      if self._current_layer_export_status == ExportStatuses.FORCE_INTERACTIVE:
        self._export_once_wrapper(
          self._get_export_func(), gimpenums.RUN_INTERACTIVE, image, layer,
          output_filepath)
  
  def _make_dirs(self, dirpath, layer_exporter):
    try:
      pgpath.make_dirs(dirpath)
    except OSError as e:
      try:
        message = e.args[1]
        if e.filename is not None:
          message += ': "{0}"'.format(e.filename)
      except (IndexError, AttributeError):
        message = str(e)
      
      raise InvalidOutputDirectoryError(
        message, layer_exporter.current_layer_elem, layer_exporter.default_file_extension)
  
  def _export_once_wrapper(self, export_func, run_mode, image, layer, output_filepath):
    with self.export_context_manager(
           run_mode, image, layer, output_filepath, *self.export_context_manager_args):
      self._export_once(export_func, run_mode, image, layer, output_filepath)
  
  def _get_run_mode(self):
    file_extension = self._file_extension_properties[self._current_file_extension]
    if file_extension.is_valid and file_extension.processed_count > 0:
      return gimpenums.RUN_WITH_LAST_VALS
    else:
      return self.initial_run_mode
  
  def _get_export_func(self):
    return pgfileformats.get_save_procedure(self._current_file_extension)
  
  def _export_once(self, export_func, run_mode, image, layer, output_filepath):
    self._current_layer_export_status = ExportStatuses.NOT_EXPORTED_YET
    
    try:
      export_func(
        run_mode, image, layer,
        output_filepath.encode(pgconstants.GIMP_CHARACTER_ENCODING),
        os.path.basename(output_filepath).encode(pgconstants.GIMP_CHARACTER_ENCODING))
    except RuntimeError as e:
      # HACK: Examining the exception message seems to be the only way to determine
      # some specific cases of export failure.
      if self._was_export_canceled_by_user(str(e)):
        raise ExportLayersCancelError(str(e))
      elif self._should_export_again_with_interactive_run_mode(str(e), run_mode):
        self._prepare_export_with_interactive_run_mode()
      elif self._should_export_again_with_default_file_extension():
        self._prepare_export_with_default_file_extension()
      else:
        raise ExportLayersError(str(e), layer, self._default_file_extension)
    else:
      self._current_layer_export_status = ExportStatuses.EXPORT_SUCCESSFUL
  
  def _was_export_canceled_by_user(self, exception_message):
    return any(
      message in exception_message.lower() for message in ["cancelled", "canceled"])
  
  def _should_export_again_with_interactive_run_mode(
        self, exception_message, current_run_mode):
    return (
      "calling error" in exception_message.lower()
      and current_run_mode in (
        gimpenums.RUN_WITH_LAST_VALS, gimpenums.RUN_NONINTERACTIVE))
  
  def _prepare_export_with_interactive_run_mode(self):
    self._current_layer_export_status = ExportStatuses.FORCE_INTERACTIVE
  
  def _should_export_again_with_default_file_extension(self):
    return self._current_file_extension != self._default_file_extension
  
  def _prepare_export_with_default_file_extension(self):
    self._file_extension_properties[self._current_file_extension].is_valid = False
    self._current_file_extension = self._default_file_extension
    self._current_layer_export_status = ExportStatuses.USE_DEFAULT_FILE_EXTENSION
