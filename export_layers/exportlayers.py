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
This module is the core of the plug-in and provides a class to export layers as
separate images.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *
import future.utils

import collections
import inspect
import os

from gimp import pdb
import gimpenums

from export_layers import pygimplib as pg

from . import builtin_procedures
from . import builtin_constraints
from . import operations
from . import placeholders
from . import renamer


class LayerExporter(object):
  """
  This class exports layers as separate images, with the support for additional
  operations applied on layers (resize, rename, ...).
  
  Attributes:
  
  * `initial_run_mode` - The run mode to use for the first layer exported.
    For subsequent layers, `gimpenums.RUN_WITH_LAST_VALS` is used. If the file
    format in which the layer is exported to cannot handle
    `gimpenums.RUN_WITH_LAST_VALS`, `gimpenums.RUN_INTERACTIVE` is used.
  
  * `image` - GIMP image to export layers from.
  
  * `export_settings` - `SettingGroup` instance containing export settings. This
    class treats them as read-only.
  
  * `overwrite_chooser` - `OverwriteChooser` instance that is invoked if a file
    with the same name already exists. If `None` is passed during
    initialization, `pygimplib.overwrite.NoninteractiveOverwriteChooser` is used
    by default.
  
  * `progress_updater` - `ProgressUpdater` instance that indicates the number of
    layers exported. If no progress update is desired, pass `None`.
  
  * `layer_tree` - `LayerTree` instance containing layers to be exported.
    Defaults to `None` if no export has been performed yet.
  
  * `exported_layers` - List of layers that were successfully exported. Does not
    include skipped layers (when files with the same names already exist).
  
  * `export_context_manager` - Context manager that wraps exporting a single
    layer. This can be used to perform GUI updates before and after export.
    Required parameters: current run mode, current image, layer to export,
    output filename of the layer.
  
  * `export_context_manager_args` - Additional arguments passed to
    `export_context_manager`.
  
  * `current_layer_elem` (read-only) - The `itemtree._ItemTreeElement` instance
    being currently exported.
  
  * `operation_executor` - `pygimplib.operations.OperationExecutor` instance to
    manage operations applied on layers. This property is not `None` only during
    `export()` and can be used to modify the execution of operations while
    processing layers.
  """
  
  def __init__(
        self,
        initial_run_mode,
        image,
        export_settings,
        overwrite_chooser=None,
        progress_updater=None,
        layer_tree=None,
        export_context_manager=None,
        export_context_manager_args=None):
    
    self.initial_run_mode = initial_run_mode
    self.image = image
    self.export_settings = export_settings
    
    self.overwrite_chooser = (
      overwrite_chooser if overwrite_chooser is not None
      else pg.overwrite.NoninteractiveOverwriteChooser(
        self.export_settings["overwrite_mode"].value))
    
    self.progress_updater = (
      progress_updater if progress_updater is not None
      else pg.progress.ProgressUpdater(None))
    
    self._layer_tree = layer_tree
    
    self.export_context_manager = (
      export_context_manager if export_context_manager is not None
      else pg.utils.EmptyContext)
    
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
    
    self._operation_executor = None
    self._initial_operation_executor = pg.operations.OperationExecutor()
  
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
    
    * `"layer_contents"` - Perform only operations manipulating the layer
      itself, such as cropping, resizing, etc. This is useful to preview the
      layer(s).
    
    * `"layer_name"` - Perform only operations manipulating layer names
      and layer tree (but not layer contents). This is useful to preview the
      names of the exported layers.
    
    * `"export"` - Perform only operations that export the layer or create
      directories for the layer.
    
    If `processing_groups` is `None` or empty, perform normal export.
    
    If `layer_tree` is not `None`, use an existing instance of
    `itemtree.LayerTree` instead of creating a new one. If the instance had
    constraints set, they will be reset.
    
    A copy of the image and the layers to be exported are created so that the
    original image and its soon-to-be exported layers are left intact. The
    image copy is automatically destroyed after the export. To keep the image
    copy, pass `True` to `keep_image_copy`. In that case, this method returns
    the image copy. If an exception was raised or if no layer was exported, this
    method returns `None` and the image copy will be destroyed.
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
    Return `True` if the specified `gimp.Layer` was exported in the last export,
    `False` otherwise.
    """
    return layer.ID in self._exported_layers_ids
  
  def stop(self):
    self._should_stop = True
  
  def add_procedure(self, *args, **kwargs):
    """
    Add a procedure to be executed during `export()`. The signature is the same
    as for `pygimplib.operations.OperationExecutor.add()`.
    
    Procedures added by this method are placed before procedures added by
    `operations.add()`.
    
    Unlike `operations.add()`, procedures added by this method do not act as
    settings, i.e. they are merely functions without GUI, are not saved
    persistently and are always enabled.
    """
    return self._initial_operation_executor.add(*args, **kwargs)
  
  def add_constraint(self, func, *args, **kwargs):
    """
    Add a constraint to be applied during `export()`. The first argument is the
    function to act as a filter (returning `True` or `False`). The rest of the
    signature is the same as for `pygimplib.operations.OperationExecutor.add()`.
    
    For more information, see `add_procedure()`.
    """
    return self._initial_operation_executor.add(
      _get_constraint_func(func), *args, **kwargs)
  
  def remove_operation(self, *args, **kwargs):
    """
    Remove an operation originally scheduled to be executed during `export()`.
    The signature is the same as for
    `pygimplib.operations.OperationExecutor.remove()`.
    """
    self._initial_operation_executor.remove(*args, **kwargs)
  
  def reorder_operation(self, *args, **kwargs):
    """
    Reorder an operation to be executed during `export()`. The signature is the
    same as for `pygimplib.operations.OperationExecutor.reorder()`.
    """
    self._initial_operation_executor.reorder(*args, **kwargs)
  
  def _init_attributes(self, processing_groups, layer_tree, keep_image_copy):
    self._operation_executor = pg.operations.OperationExecutor()
    self._add_operations()
    
    self._enable_disable_processing_groups(processing_groups)
    
    if layer_tree is not None:
      self._layer_tree = layer_tree
    else:
      self._layer_tree = pg.itemtree.LayerTree(
        self.image, name=pg.config.SOURCE_PERSISTENT_NAME, is_filtered=True)
    
    self._keep_image_copy = keep_image_copy
    
    self._should_stop = False
    
    self._exported_layers = []
    self._exported_layers_ids = set()
    
    self._current_layer_elem = None
    
    self._output_directory = self.export_settings["output_directory"].value
    
    self._image_copy = None
    self._tagged_layer_elems = collections.defaultdict(list)
    self._tagged_layer_copies = collections.defaultdict(pg.utils.return_none_func)
    self._inserted_tagged_layers = collections.defaultdict(pg.utils.return_none_func)
    
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
    
    self._layer_name_renamer = renamer.LayerNameRenamer(self, pattern)
  
  def _add_operations(self):
    self._operation_executor.add(
      builtin_procedures.set_active_layer, [operations.DEFAULT_PROCEDURES_GROUP])
    
    self._operation_executor.add(
      builtin_procedures.set_active_layer_after_operation,
      [operations.DEFAULT_PROCEDURES_GROUP],
      foreach=True)
    
    self._operation_executor.add(
      self._initial_operation_executor,
      self._initial_operation_executor.list_groups(include_empty_groups=True))
    
    for procedure in operations.walk(self.export_settings["procedures"]):
      add_operation_from_settings(procedure, self._operation_executor)
    
    for constraint in operations.walk(self.export_settings["constraints"]):
      add_operation_from_settings(constraint, self._operation_executor)
  
  def _enable_disable_processing_groups(self, processing_groups):
    for functions in self._processing_groups.values():
      for function in functions:
        setattr(
          self, function.__name__, self._processing_groups_functions[function.__name__])
    
    if processing_groups:
      if "layer_name" in processing_groups:
        processing_groups.append("_postprocess_layer_name")
      
      for processing_group, functions in self._processing_groups.items():
        if processing_group not in processing_groups:
          for function in functions:
            setattr(self, function.__name__, pg.utils.empty_func)
  
  def _preprocess_layers(self):
    if self._layer_tree.filter:
      self._layer_tree.reset_filter()
    
    if self.export_settings.get_value(
         "procedures/added/ignore_folder_structure/enabled", False):
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
      "layer_types", pg.objectfilter.ObjectFilter(pg.objectfilter.ObjectFilter.MATCH_ANY))
    
    self._operation_executor.execute(
      [builtin_constraints.CONSTRAINTS_LAYER_TYPES_GROUP],
      [self],
      additional_args_position=_LAYER_EXPORTER_ARG_POSITION_IN_CONSTRAINTS)
    
    self._init_tagged_layer_elems()
    
    self._operation_executor.execute(
      [operations.DEFAULT_CONSTRAINTS_GROUP],
      [self],
      additional_args_position=_LAYER_EXPORTER_ARG_POSITION_IN_CONSTRAINTS)
  
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
          "invalid/unsupported item type '{}' in {}".format(
            layer_elem.item_type, layer_elem))
  
  def _process_and_export_item(self, layer_elem):
    layer = layer_elem.item
    layer_copy = self._process_layer(layer_elem, self._image_copy, layer)
    self._preprocess_layer_name(layer_elem)
    self._export_layer(layer_elem, self._image_copy, layer_copy)
    self._postprocess_layer(self._image_copy, layer_copy)
    self._postprocess_layer_name(layer_elem)
    
    self.progress_updater.update_tasks()
    
    if self._current_overwrite_mode != pg.overwrite.OverwriteModes.SKIP:
      self._exported_layers.append(layer)
      self._exported_layers_ids.add(layer.ID)
      self._file_extension_properties[self._current_file_extension].processed_count += 1
  
  def _process_empty_group(self, layer_elem):
    self._preprocess_empty_group_name(layer_elem)
    
    empty_group_dirpath = layer_elem.get_filepath(self._output_directory)
    self._make_dirs(empty_group_dirpath, self)
    
    self.progress_updater.update_text(
      _('Creating empty directory "{}"').format(empty_group_dirpath))
    self.progress_updater.update_tasks()
  
  def _setup(self):
    pdb.gimp_context_push()
    
    self._image_copy = pg.pdbutils.create_image_from_metadata(self.image)
    pdb.gimp_image_undo_freeze(self._image_copy)
    
    self._operation_executor.execute(
      ["after_create_image_copy"], [self._image_copy], additional_args_position=0)
    
    if self._use_another_image_copy:
      self._another_image_copy = pg.pdbutils.create_image_from_metadata(self._image_copy)
      pdb.gimp_image_undo_freeze(self._another_image_copy)
    
    if pg.config.DEBUG_IMAGE_PROCESSING:
      self._display_id = pdb.gimp_display_new(self._image_copy)
  
  def _cleanup(self, exception_occurred=False):
    self._copy_non_modifying_parasites(self._image_copy, self.image)
    
    pdb.gimp_image_undo_thaw(self._image_copy)
    
    if pg.config.DEBUG_IMAGE_PROCESSING:
      pdb.gimp_display_delete(self._display_id)
    
    if ((not self._keep_image_copy or self._use_another_image_copy)
        or exception_occurred):
      pg.pdbutils.try_delete_image(self._image_copy)
      if self._use_another_image_copy:
        pdb.gimp_image_undo_thaw(self._another_image_copy)
        if exception_occurred:
          pg.pdbutils.try_delete_image(self._another_image_copy)
    
    for tagged_layer_copy in self._tagged_layer_copies.values():
      if tagged_layer_copy is not None:
        pdb.gimp_item_delete(tagged_layer_copy)
    
    pdb.gimp_context_pop()
  
  def _process_layer(self, layer_elem, image, layer):
    layer_copy = builtin_procedures.copy_and_insert_layer(image, layer, None, 0)
    self._operation_executor.execute(
      ["after_insert_layer"], [image, layer_copy, self], additional_args_position=0)
    
    self._operation_executor.execute(
      [operations.DEFAULT_PROCEDURES_GROUP],
      [image, layer_copy, self],
      additional_args_position=0)
    
    layer_copy = self._merge_and_resize_layer(image, layer_copy)
    
    image.active_layer = layer_copy
    
    layer_copy.name = layer.name
    
    self._operation_executor.execute(
      ["after_process_layer"], [image, layer_copy, self], additional_args_position=0)
    
    return layer_copy
  
  def _postprocess_layer(self, image, layer):
    if not self._keep_image_copy:
      pdb.gimp_image_remove_layer(image, layer)
    else:
      if self._use_another_image_copy:
        another_layer_copy = pdb.gimp_layer_new_from_drawable(
          layer, self._another_image_copy)
        pdb.gimp_image_insert_layer(
          self._another_image_copy,
          another_layer_copy,
          None,
          len(self._another_image_copy.layers))
        another_layer_copy.name = layer.name
        
        pdb.gimp_image_remove_layer(image, layer)
  
  def _merge_and_resize_layer(self, image, layer):
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
    if self.export_settings.get_value(
         "procedures/added/use_file_extensions_in_layer_names/enabled", False):
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
    
    self.progress_updater.update_text(_('Saving "{}"').format(output_filepath))
    
    self._current_overwrite_mode, output_filepath = pg.overwrite.handle_overwrite(
      output_filepath, self.overwrite_chooser,
      self._get_uniquifier_position(output_filepath))
    
    if self._current_overwrite_mode == pg.overwrite.OverwriteModes.CANCEL:
      raise ExportLayersCancelError("cancelled")
    
    if self._current_overwrite_mode != pg.overwrite.OverwriteModes.SKIP:
      self._make_dirs(os.path.dirname(output_filepath), self)
      
      self._export_once_wrapper(
        self._get_export_func(), self._get_run_mode(), image, layer, output_filepath)
      if self._current_layer_export_status == ExportStatuses.FORCE_INTERACTIVE:
        self._export_once_wrapper(
          self._get_export_func(),
          gimpenums.RUN_INTERACTIVE,
          image,
          layer,
          output_filepath)
  
  def _make_dirs(self, dirpath, layer_exporter):
    try:
      pg.path.make_dirs(dirpath)
    except OSError as e:
      try:
        message = e.args[1]
        if e.filename is not None:
          message += ': "{}"'.format(e.filename)
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
    return pg.fileformats.get_save_procedure(self._current_file_extension)
  
  def _export_once(self, export_func, run_mode, image, layer, output_filepath):
    self._current_layer_export_status = ExportStatuses.NOT_EXPORTED_YET
    
    try:
      export_func(
        run_mode,
        image,
        layer,
        output_filepath.encode(pg.GIMP_CHARACTER_ENCODING),
        os.path.basename(output_filepath).encode(pg.GIMP_CHARACTER_ENCODING))
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
  
  @staticmethod
  def _copy_non_modifying_parasites(src_image, dest_image):
    unused_, parasite_names = pdb.gimp_image_get_parasite_list(src_image)
    for parasite_name in parasite_names:
      if dest_image.parasite_find(parasite_name) is None:
        parasite = src_image.parasite_find(parasite_name)
        # Do not attach persistent or undoable parasites to avoid modifying
        # `dest_image`.
        if parasite.flags == 0:
          dest_image.parasite_attach(parasite)


#===============================================================================


_LAYER_EXPORTER_ARG_POSITION_IN_CONSTRAINTS = 1


def add_operation_from_settings(operation, executor):
  if operation.get_value("is_pdb_procedure", False):
    try:
      function = pdb[operation["function"].value.encode(pg.GIMP_CHARACTER_ENCODING)]
    except KeyError:
      raise InvalidPdbProcedureError(
        "invalid PDB procedure '{}'".format(operation["function"].value))
  else:
    function = operation["function"].value
  
  if function is None:
    return
  
  function_args = tuple(arg_setting.value for arg_setting in operation["arguments"])
  function_kwargs = {}
  
  if operation.get_value("is_pdb_procedure", False):
    if _has_run_mode_param(function):
      function_kwargs = {b"run_mode": function_args[0]}
      function_args = function_args[1:]
    
    function = _get_operation_func_for_pdb_procedure(function)
  
  if "constraint" not in operation.tags:
    function = _get_operation_func_with_replaced_placeholders(function)
  
  if "constraint" in operation.tags:
    function = _get_constraint_func(function, subfilter=operation["subfilter"].value)
  
  function = _execute_operation_only_if_enabled(function, operation["enabled"])
  
  executor.add(
    function, operation["operation_groups"].value, function_args, function_kwargs)


def _has_run_mode_param(pdb_procedure):
  return pdb_procedure.params and pdb_procedure.params[0][1] == "run-mode"


def _get_operation_func_for_pdb_procedure(pdb_procedure):
  def _pdb_procedure_as_operation(image, layer, layer_exporter, *args, **kwargs):
    pdb_procedure(*args, **kwargs)
  
  return _pdb_procedure_as_operation


def _get_operation_func_with_replaced_placeholders(function):
  def _operation(image, layer, layer_exporter, *args, **kwargs):
    new_args, new_kwargs = placeholders.get_replaced_args_and_kwargs(
      args, kwargs, image, layer, layer_exporter)
    function(image, layer, layer_exporter, *new_args, **new_kwargs)
  
  return _operation


def _execute_operation_only_if_enabled(operation, setting_enabled):
  def _execute_operation(*operation_args, **operation_kwargs):
    if setting_enabled.value:
      return operation(*operation_args, **operation_kwargs)
    else:
      return False
  
  return _execute_operation


def _get_constraint_func(rule_func, subfilter=None):
  def _add_rule_func(*args):
    layer_exporter, rule_func_args = _get_args_for_constraint_func(rule_func, args)
    
    if subfilter is None:
      object_filter = layer_exporter.layer_tree.filter
    else:
      object_filter = layer_exporter.layer_tree.filter[subfilter]
    
    object_filter.add_rule(rule_func, *rule_func_args)
  
  return _add_rule_func


def _get_args_for_constraint_func(rule_func, args):
  try:
    layer_exporter_arg_position = (
      inspect.getargspec(rule_func).args.index("layer_exporter"))
  except ValueError:
    layer_exporter_arg_position = None
  
  if layer_exporter_arg_position is not None:
    layer_exporter = args[layer_exporter_arg_position - 1]
    rule_func_args = args
  else:
    if len(args) > 1:
      layer_exporter_arg_position = (
        _LAYER_EXPORTER_ARG_POSITION_IN_CONSTRAINTS)
    else:
      layer_exporter_arg_position = (
        _LAYER_EXPORTER_ARG_POSITION_IN_CONSTRAINTS - 1)
    
    layer_exporter = args[layer_exporter_arg_position]
    rule_func_args = (
      args[:layer_exporter_arg_position] + args[layer_exporter_arg_position + 1:])
  
  return layer_exporter, rule_func_args


class _FileExtension(object):
  """
  This class defines additional properties for a file extension.
  
  Attributes:
  
  * `is_valid` - If `True`, file extension is valid and can be used in filenames
    for file export procedures.
  
  * `processed_count` - Number of items with the specific file extension that
    have already been exported.
  """
  
  def __init__(self):
    self.is_valid = True
    self.processed_count = 0


def _get_prefilled_file_extension_properties():
  file_extension_properties = collections.defaultdict(_FileExtension)
  
  for file_format in pg.fileformats.file_formats:
    # This ensures that the file format dialog will be displayed only once per
    # file format if multiple file extensions for the same format are used
    # (e.g. "jpg", "jpeg" or "jpe" for the JPEG format).
    extension_properties = _FileExtension()
    for file_extension in file_format.file_extensions:
      file_extension_properties[file_extension] = extension_properties
  
  return file_extension_properties


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


class InvalidPdbProcedureError(ExportLayersError):
  pass


class ExportStatuses(object):
  EXPORT_STATUSES = (
    NOT_EXPORTED_YET, EXPORT_SUCCESSFUL, FORCE_INTERACTIVE, USE_DEFAULT_FILE_EXTENSION
  ) = (0, 1, 2, 3)
