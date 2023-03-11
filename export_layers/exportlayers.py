# -*- coding: utf-8 -*-

"""Plug-in core - exporting layers as separate images."""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *
import future.utils

import collections
import inspect
import os

from gimp import pdb
import gimpenums

from export_layers import pygimplib as pg

from export_layers import builtin_procedures
from export_layers import builtin_constraints
from export_layers import actions
from export_layers import placeholders
from export_layers import renamer
from export_layers import uniquifier


_EXPORTER_ARG_POSITION_IN_PROCEDURES = 0
_EXPORTER_ARG_POSITION_IN_CONSTRAINTS = 0


class LayerExporter(object):
  """
  This class exports layers as separate images, with the support for additional
  actions applied on layers (resize, rename, ...).
  
  Attributes:
  
  * `initial_run_mode` - The run mode to use for the first layer exported.
    For subsequent layers, `gimpenums.RUN_WITH_LAST_VALS` is used. If the file
    format in which the layer is exported to cannot handle
    `gimpenums.RUN_WITH_LAST_VALS`, `gimpenums.RUN_INTERACTIVE` is used.
  
  * `image` - GIMP image to export layers from.
  
  * `export_settings` - `setting.Group` instance containing export settings.
    This class treats them as read-only.
  
  * `overwrite_chooser` - `OverwriteChooser` instance that is invoked if a file
    with the same name already exists. If `None` is passed during
    initialization, `pygimplib.overwrite.NoninteractiveOverwriteChooser` is used
    by default.
  
  * `progress_updater` - `ProgressUpdater` instance that indicates the number of
    layers exported. If no progress update is desired, pass `None`.
  
  * `item_tree` - `ItemTree` instance containing layers to be exported.
    Defaults to `None` if no export has been performed yet.
  
  * `exported_raw_items` - List of layers that were successfully exported. Does
    not include skipped layers (when files with the same names already exist).
  
  * `export_context_manager` - Context manager that wraps exporting a single
    layer. This can be used to perform GUI updates before and after export.
    Required parameters: current run mode, current image, layer to export,
    output filename of the layer.
  
  * `export_context_manager_args` - Additional arguments passed to
    `export_context_manager`.
  
  * `current_item` (read-only) - An `itemtree._Item` instance being
    currently exported.
  
  * `invoker` - `pygimplib.invoker.Invoker` instance to
    manage procedures and constraints applied on layers. This property is not
    `None` only during `export()`.
  """
  
  def __init__(
        self,
        initial_run_mode,
        image,
        export_settings,
        overwrite_chooser=None,
        progress_updater=None,
        item_tree=None,
        export_context_manager=None,
        export_context_manager_args=None):
    
    self.initial_run_mode = initial_run_mode
    self.image = image
    self.export_settings = export_settings
    
    self.overwrite_chooser = (
      overwrite_chooser if overwrite_chooser is not None
      else pg.overwrite.NoninteractiveOverwriteChooser(
        self.export_settings['overwrite_mode'].value))
    
    self.progress_updater = (
      progress_updater if progress_updater is not None
      else pg.progress.ProgressUpdater(None))
    
    self._item_tree = item_tree
    self._layer_types_filter = None
    
    self._is_preview = False
    
    self.export_context_manager = (
      export_context_manager if export_context_manager is not None
      else pg.utils.EmptyContext)
    
    self.export_context_manager_args = (
      export_context_manager_args if export_context_manager_args is not None else [])
    
    self._default_file_extension = None
    self._file_extension_properties = None
    
    self.current_file_extension = None
    
    self._current_item = None
    self._current_raw_item = None
    self._current_image = None
    
    self._exported_raw_items = []
    self._exported_raw_items_ids = set()
    
    self._should_stop = False
    
    self._processing_groups = {
      'item_contents': [
        self._setup, self._cleanup, self._process_item_with_actions, self._postprocess_item],
      'item_name': [
        self._preprocess_item_name, self._process_parent_folder_names, self._process_item_name],
      'export': [self._make_dirs, self._export],
      'item_name_for_preview': [self._process_item_name_for_preview],
    }
    self._default_processing_groups = [
      'item_contents',
      'item_name',
      'export',
    ]
    
    self._processing_groups_functions = {}
    for functions in self._processing_groups.values():
      for function in functions:
        self._processing_groups_functions[function.__name__] = function
    
    self._invoker = None
    self._initial_invoker = pg.invoker.Invoker()
    self._NAME_ONLY_ACTION_GROUP = 'name'
  
  @property
  def item_tree(self):
    return self._item_tree
  
  @property
  def is_preview(self):
    return self._is_preview
  
  @property
  def exported_raw_items(self):
    return self._exported_raw_items
  
  @property
  def current_item(self):
    return self._current_item
  
  @property
  def current_raw_item(self):
    return self._current_raw_item
  
  @property
  def current_image(self):
    return self._current_image
  
  @property
  def tagged_items(self):
    return self._tagged_items
  
  @property
  def inserted_tagged_layers(self):
    return self._inserted_tagged_layers
  
  @property
  def tagged_layer_copies(self):
    return self._tagged_layer_copies
  
  @property
  def default_file_extension(self):
    return self._default_file_extension
  
  @property
  def file_extension_properties(self):
    return self._file_extension_properties
  
  @property
  def invoker(self):
    return self._invoker
  
  def export(
        self, processing_groups=None, item_tree=None, keep_image_copy=False, is_preview=False):
    """
    Export layers as separate images from the specified image.
    
    `processing_groups` is a list of strings that control which parts of the
    export are effective and which are ignored. Multiple groups can be
    specified. The following groups are supported:
    
    * `'item_contents'` - Perform only actions manipulating the layer
      itself, such as cropping, resizing, etc. This is useful to preview the
      layer(s).
    
    * `'item_name'` - Perform only actions manipulating layer names
      and layer tree (but not layer contents). This is useful to preview the
      names of the exported layers.
    
    * `'export'` - Perform only actions that export the layer or create
      directories for the layer.
    
    If `processing_groups` is `None` or empty, perform normal export.
    
    If `item_tree` is not `None`, use an existing instance of
    `itemtree.ItemTree` instead of creating a new one. If the instance had
    constraints set, they will be reset.
    
    A copy of the image and the layers to be exported are created so that the
    original image and its soon-to-be exported layers are left intact. The
    image copy is automatically destroyed after the export. To keep the image
    copy, pass `True` to `keep_image_copy`. In that case, this method returns
    the image copy. If an exception was raised or if no layer was exported, this
    method returns `None` and the image copy will be destroyed.
    
    If `is_preview` is `True`, only procedures and constraints that are marked
    as enabled for previews will be applied for previews. This has no effect
    during real export.
    """
    self._init_attributes(processing_groups, item_tree, keep_image_copy, is_preview)
    self._preprocess_items()
    
    exception_occurred = False
    
    self._setup()
    try:
      self._process_items()
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
  
  def has_exported_item(self, raw_item):
    """Returns `True` if the GIMP item was exported in the last export, `False`
    otherwise.
    """
    return raw_item.ID in self._exported_raw_items_ids
  
  def stop(self):
    self._should_stop = True
  
  def add_procedure(self, *args, **kwargs):
    """
    Add a procedure to be applied during `export()`. The signature is the same
    as for `pygimplib.invoker.Invoker.add()`.
    
    Procedures added by this method are placed before procedures added by
    `actions.add()`.
    
    Unlike `actions.add()`, procedures added by this method do not act as
    settings, i.e. they are merely functions without GUI, are not saved
    persistently and are always enabled.
    """
    return self._initial_invoker.add(*args, **kwargs)
  
  def add_constraint(self, func, *args, **kwargs):
    """
    Add a constraint to be applied during `export()`. The first argument is the
    function to act as a filter (returning `True` or `False`). The rest of the
    signature is the same as for `pygimplib.invoker.Invoker.add()`.
    
    For more information, see `add_procedure()`.
    """
    return self._initial_invoker.add(
      self._get_constraint_func(func), *args, **kwargs)
  
  def remove_action(self, *args, **kwargs):
    """
    Remove an action originally scheduled to be applied during `export()`.
    The signature is the same as for `pygimplib.invoker.Invoker.remove()`.
    """
    self._initial_invoker.remove(*args, **kwargs)
  
  def reorder_action(self, *args, **kwargs):
    """
    Reorder an action to be applied during `export()`.
    The signature is the same as for `pygimplib.invoker.Invoker.reorder()`.
    """
    self._initial_invoker.reorder(*args, **kwargs)
  
  def _add_action_from_settings(self, action, tags=None, action_groups=None):
    """Adds an action and wraps/processes the action's function according to the
    action's settings.
    
    For PDB procedures, the function name is converted to a proper function
    object. For constraints, the function is wrapped to act as a proper filter
    rule for `item_tree.filter`. Any placeholder objects (e.g. "current image")
    as function arguments are replaced with real objects during processing of
    each item.
    
    If `tags` is not `None`, the action will not be added if it does not contain
    any of the specified tags.
    
    If `action_groups` is not `None`, the action will be added to the specified
    action groups instead of the groups defined in `action['action_groups']`.
    """
    if action.get_value('is_pdb_procedure', False):
      try:
        function = pdb[pg.utils.safe_encode_gimp(action['function'].value)]
      except KeyError:
        raise InvalidPdbProcedureError(
          'invalid PDB procedure "{}"'.format(action['function'].value))
    else:
      function = action['function'].value
    
    if function is None:
      return
    
    if tags is not None and not any(tag in action.tags for tag in tags):
      return
    
    orig_function = function
    function_args = tuple(arg_setting.value for arg_setting in action['arguments'])
    function_kwargs = {}
    
    if action.get_value('is_pdb_procedure', False):
      if self._has_run_mode_param(function):
        function_kwargs = {b'run_mode': function_args[0]}
        function_args = function_args[1:]
      
      function = self._get_action_func_for_pdb_procedure(function)
    
    function = self._get_action_func_with_replaced_placeholders(function)
    
    if 'constraint' in action.tags:
      function = self._get_constraint_func(
        function, orig_function, action['orig_name'].value, action['subfilter'].value)
    
    function = self._apply_action_only_if_enabled(function, action)
    
    if action_groups is None:
      action_groups = action['action_groups'].value
    
    self.invoker.add(function, action_groups, function_args, function_kwargs)
  
  def _has_run_mode_param(self, pdb_procedure):
    return pdb_procedure.params and pdb_procedure.params[0][1] == 'run-mode'
  
  def _get_action_func_for_pdb_procedure(self, pdb_procedure):
    def _pdb_procedure_as_action(exporter, *args, **kwargs):
      return pdb_procedure(*args, **kwargs)
    
    return _pdb_procedure_as_action
  
  def _get_action_func_with_replaced_placeholders(self, function):
    def _action(*args, **kwargs):
      new_args, new_kwargs = placeholders.get_replaced_args_and_kwargs(args, kwargs, self)
      return function(*new_args, **new_kwargs)
    
    return _action
  
  def _apply_action_only_if_enabled(self, function, action):
    if self.is_preview:
      def _apply_action_in_preview(*action_args, **action_kwargs):
        if action['enabled'].value and action['enabled_for_previews'].value:
          return function(*action_args, **action_kwargs)
        else:
          return False
      
      return _apply_action_in_preview
    else:
      def _apply_action(*action_args, **action_kwargs):
        if action['enabled'].value:
          return function(*action_args, **action_kwargs)
        else:
          return False
      
      return _apply_action
  
  def _get_constraint_func(self, func, orig_func=None, name='', subfilter=None):
    def _add_func(*args, **kwargs):
      func_args = self._get_args_for_constraint_func(
        orig_func if orig_func is not None else func, args)
      
      if subfilter is None:
        object_filter = self.item_tree.filter
      else:
        subfilter_ids = self.item_tree.filter.find(name=subfilter)
        if subfilter_ids:
          object_filter = self.item_tree.filter[subfilter_ids[0]]
        else:
          object_filter = self.item_tree.filter.add(pg.objectfilter.ObjectFilter(name=subfilter))
      
      object_filter.add(func, func_args, kwargs, name=name)
    
    return _add_func
  
  def _get_args_for_constraint_func(self, func, args):
    try:
      exporter_arg_position = inspect.getargspec(func).args.index('exporter')
    except ValueError:
      exporter_arg_position = None
    
    if exporter_arg_position is not None:
      func_args = args
    else:
      if len(args) > 1:
        exporter_arg_position = _EXPORTER_ARG_POSITION_IN_CONSTRAINTS
      else:
        exporter_arg_position = 0
      
      func_args = args[:exporter_arg_position] + args[exporter_arg_position + 1:]
    
    return func_args
  
  def _init_attributes(self, processing_groups, item_tree, keep_image_copy, is_preview):
    self._invoker = pg.invoker.Invoker()
    self._add_actions()
    self._add_name_only_actions()
    
    self._enable_disable_processing_groups(processing_groups)
    
    if item_tree is not None:
      self._item_tree = item_tree
      self._reset_item_attributes()
    else:
      self._item_tree = pg.itemtree.LayerTree(self.image, name=pg.config.SOURCE_NAME)
    
    self._keep_image_copy = keep_image_copy
    self._is_preview = is_preview
    
    self._should_stop = False
    
    self._exported_raw_items = []
    self._exported_raw_items_ids = set()
    
    self._output_directory = self.export_settings['output_directory'].value
    
    self._image_copy = None
    self._tagged_items = collections.defaultdict(list)
    self._tagged_layer_copies = collections.defaultdict(pg.utils.return_none_func)
    self._inserted_tagged_layers = collections.defaultdict(pg.utils.return_none_func)
    
    self._use_another_image_copy = False
    self._another_image_copy = None
    
    self.progress_updater.reset()
    
    self._default_file_extension = self.export_settings['file_extension'].value
    self._file_extension_properties = _FileExtensionProperties()
    
    self.current_file_extension = self._default_file_extension
    
    self._current_item = None
    self._current_raw_item = None
    self._current_image = None
    
    self._current_export_status = ExportStatuses.NOT_EXPORTED_YET
    self._current_overwrite_mode = None
    
    self._renamer = renamer.LayerNameRenamer(self.export_settings['layer_filename_pattern'].value)
    self._uniquifier = uniquifier.ItemUniquifier()
    self._processed_parent_names = set()
  
  def _add_actions(self):
    self._invoker.add(
      builtin_procedures.set_active_layer, [actions.DEFAULT_PROCEDURES_GROUP])
    
    self._invoker.add(
      builtin_procedures.set_active_layer_after_action,
      [actions.DEFAULT_PROCEDURES_GROUP],
      foreach=True)
    
    self._invoker.add(
      self._initial_invoker,
      self._initial_invoker.list_groups(include_empty_groups=True))
    
    for procedure in actions.walk(self.export_settings['procedures']):
      self._add_action_from_settings(procedure)
    
    for constraint in actions.walk(self.export_settings['constraints']):
      self._add_action_from_settings(constraint)
  
  def _add_name_only_actions(self):
    for procedure in actions.walk(self.export_settings['procedures']):
      self._add_action_from_settings(
        procedure, [builtin_procedures.NAME_ONLY_TAG], [self._NAME_ONLY_ACTION_GROUP])
    
    for constraint in actions.walk(self.export_settings['constraints']):
      self._add_action_from_settings(
        constraint, [builtin_procedures.NAME_ONLY_TAG], [self._NAME_ONLY_ACTION_GROUP])
  
  def _enable_disable_processing_groups(self, processing_groups):
    for functions in self._processing_groups.values():
      for function in functions:
        setattr(self, function.__name__, self._processing_groups_functions[function.__name__])
    
    if processing_groups is None:
      processing_groups = self._default_processing_groups
    
    for processing_group, functions in self._processing_groups.items():
      if processing_group not in processing_groups:
        for function in functions:
          setattr(self, function.__name__, pg.utils.empty_func)
  
  def _reset_item_attributes(self):
    for item in self._item_tree.iter_all():
      item.name = item.orig_name
      item.parents = list(item.orig_parents)
      item.children = list(item.orig_children)
  
  def _preprocess_items(self):
    if self._item_tree.filter:
      self._item_tree.reset_filter()
    
    self._set_constraints()
    
    self.progress_updater.num_total_tasks = len(self._item_tree)
    
    if self._keep_image_copy:
      with self._layer_types_filter.remove_temp(
            func_or_filter=builtin_constraints.is_nonempty_group):
        num_items = len(self._item_tree)
        if num_items > 1:
          self._use_another_image_copy = True
        elif num_items < 1:
          self._keep_image_copy = False
  
  def _set_constraints(self):
    self._layer_types_filter = pg.objectfilter.ObjectFilter(
      pg.objectfilter.ObjectFilter.MATCH_ANY, name='layer_types')
    
    self._item_tree.filter.add(self._layer_types_filter)
    
    self._invoker.invoke(
      [builtin_constraints.CONSTRAINTS_LAYER_TYPES_GROUP],
      [self],
      additional_args_position=_EXPORTER_ARG_POSITION_IN_CONSTRAINTS)
    
    self._init_tagged_items()
    
    self._invoker.invoke(
      [actions.DEFAULT_CONSTRAINTS_GROUP],
      [self],
      additional_args_position=_EXPORTER_ARG_POSITION_IN_CONSTRAINTS)
  
  def _init_tagged_items(self):
    with self._item_tree.filter.add_temp(builtin_constraints.has_tags):
      with self._layer_types_filter.add_temp(builtin_constraints.is_nonempty_group):
        for item in self._item_tree:
          for tag in item.tags:
            self._tagged_items[tag].append(item)
  
  def _process_items(self):
    for item in self._item_tree:
      if self._should_stop:
        raise ExportCancelError('export stopped by user')
      
      self._current_item = item
      
      self._process_item(item)
  
  def _process_item(self, item):
    raw_item = item.raw
    
    self._current_raw_item = raw_item
    
    self._preprocess_item_name(item)
    self._process_item_name_for_preview()
    raw_item_copy = self._process_item_with_actions(item, self._image_copy, raw_item)
    self._export_item(item, self._image_copy, raw_item_copy)
    self._postprocess_item(self._image_copy, raw_item_copy)
    
    self.progress_updater.update_tasks()
    
    if self._current_overwrite_mode != pg.overwrite.OverwriteModes.SKIP:
      self._exported_raw_items.append(raw_item)
      self._exported_raw_items_ids.add(raw_item.ID)
      self._file_extension_properties[pg.path.get_file_extension(item.name)].processed_count += 1
  
  def _setup(self):
    pdb.gimp_context_push()
    
    self._image_copy = pg.pdbutils.create_image_from_metadata(self.image)
    pdb.gimp_image_undo_freeze(self._image_copy)
    
    self._current_image = self._image_copy
    
    self._invoker.invoke(
      ['after_create_image_copy'],
      [self],
      additional_args_position=_EXPORTER_ARG_POSITION_IN_PROCEDURES)
    
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
    
    for tagged_layer_copy in self._tagged_layer_copies.values():
      if tagged_layer_copy is not None:
        pdb.gimp_item_delete(tagged_layer_copy)
    
    if ((not self._keep_image_copy or self._use_another_image_copy)
        or exception_occurred):
      pg.pdbutils.try_delete_image(self._image_copy)
      if self._use_another_image_copy:
        pdb.gimp_image_undo_thaw(self._another_image_copy)
        if exception_occurred:
          pg.pdbutils.try_delete_image(self._another_image_copy)
    
    pdb.gimp_context_pop()
    
    self._current_item = None
    self._current_raw_item = None
    self._current_image = None
  
  def _process_item_with_actions(self, item, image, raw_item):
    raw_item_copy = builtin_procedures.copy_and_insert_layer(image, raw_item, None, 0)
    
    self._current_raw_item = raw_item_copy
    
    self._invoker.invoke(
      ['after_insert_item'],
      [self, raw_item_copy],
      additional_args_position=_EXPORTER_ARG_POSITION_IN_PROCEDURES)
    
    self._invoker.invoke(
      [actions.DEFAULT_PROCEDURES_GROUP],
      [self],
      additional_args_position=_EXPORTER_ARG_POSITION_IN_PROCEDURES)
    
    raw_item_copy = self._merge_and_resize_layer(image, raw_item_copy)
    image.active_layer = raw_item_copy
    raw_item_copy.name = raw_item.name
    
    self._current_raw_item = raw_item_copy
    
    self._invoker.invoke(
      ['after_process_item'],
      [self],
      additional_args_position=_EXPORTER_ARG_POSITION_IN_PROCEDURES)
    
    return raw_item_copy
  
  def _postprocess_item(self, image, raw_item):
    if not self._keep_image_copy:
      pdb.gimp_image_remove_layer(image, raw_item)
    else:
      if self._use_another_image_copy:
        another_raw_item_copy = pg.pdbutils.copy_and_paste_layer(
          raw_item, self._another_image_copy, None, len(self._another_image_copy.layers),
          remove_lock_attributes=True)
        
        another_raw_item_copy.name = raw_item.name
        
        pdb.gimp_image_remove_layer(image, raw_item)
  
  def _merge_and_resize_layer(self, image, raw_item):
    raw_item = pdb.gimp_image_merge_visible_layers(image, gimpenums.EXPAND_AS_NECESSARY)
    pdb.gimp_layer_resize_to_image_size(raw_item)
    return raw_item
  
  def _preprocess_item_name(self, item):
    item.name = self._renamer.rename(self)
    self.current_file_extension = self._default_file_extension
  
  def _process_item_name_for_preview(self):
    self._invoker.invoke(
      [self._NAME_ONLY_ACTION_GROUP],
      [self],
      additional_args_position=_EXPORTER_ARG_POSITION_IN_PROCEDURES)
  
  def _process_item_name(self, item, force_default_file_extension):
    if not force_default_file_extension:
      if self.current_file_extension == self._default_file_extension:
        item.name += '.' + self._default_file_extension
      else:
        item.name = pg.path.get_filename_with_new_file_extension(
          item.name, self.current_file_extension, keep_extra_trailing_periods=True)
    else:
      item.name = pg.path.get_filename_with_new_file_extension(
        item.name, self._default_file_extension, keep_extra_trailing_periods=True)
    
    self._validate_name(item)
    self._uniquifier.uniquify(
      item,
      position=self._get_unique_substring_position(
        item.name, pg.path.get_file_extension(item.name)))
  
  @staticmethod
  def _validate_name(item):
    item.name = pg.path.FilenameValidator.validate(item.name)
  
  def _get_unique_substring_position(self, str_, file_extension):
    return len(str_) - len('.' + file_extension)
  
  def _export_item(self, item, image, raw_item):
    self._process_parent_folder_names(item)
    self._process_item_name(item, False)
    self._export(item, image, raw_item)
    
    if self._current_export_status == ExportStatuses.USE_DEFAULT_FILE_EXTENSION:
      self._process_item_name(item, True)
      self._export(item, image, raw_item)
  
  def _process_parent_folder_names(self, item):
    for parent in item.parents:
      if parent not in self._processed_parent_names:
        self._validate_name(parent)
        self._uniquifier.uniquify(parent)
        
        self._processed_parent_names.add(parent)
  
  def _export(self, item, image, raw_item):
    output_filepath = self._get_item_filepath(item, self._output_directory)
    file_extension = pg.path.get_file_extension(item.name)
    
    self.progress_updater.update_text(_('Saving "{}"').format(output_filepath))
    
    self._current_overwrite_mode, output_filepath = pg.overwrite.handle_overwrite(
      output_filepath, self.overwrite_chooser,
      self._get_unique_substring_position(output_filepath, file_extension))
    
    if self._current_overwrite_mode == pg.overwrite.OverwriteModes.CANCEL:
      raise ExportCancelError('cancelled')
    
    if self._current_overwrite_mode != pg.overwrite.OverwriteModes.SKIP:
      self._make_dirs(os.path.dirname(output_filepath), self)
      
      self._export_once_wrapper(
        self._get_export_func(file_extension),
        self._get_run_mode(file_extension),
        image, raw_item, output_filepath, file_extension)
      if self._current_export_status == ExportStatuses.FORCE_INTERACTIVE:
        self._export_once_wrapper(
          self._get_export_func(file_extension),
          gimpenums.RUN_INTERACTIVE,
          image, raw_item, output_filepath, file_extension)
  
  @staticmethod
  def _get_item_filepath(item, dirpath):
    """Returns a file path based on the specified directory path and the name of
    the item and its parents.
    
    The file path created has the following format:
      
      <directory path>/<item path components>/<item name>
    
    If the directory path is not an absolute path or is `None`, the
    current working directory is prepended.
    
    Item path components consist of parents' item names, starting with the
    topmost parent.
    """
    if dirpath is None:
      dirpath = ''
    
    path = os.path.abspath(dirpath)
    
    path_components = [parent.name for parent in item.parents]
    if path_components:
      path = os.path.join(path, os.path.join(*path_components))
    
    return os.path.join(path, item.name)
  
  def _make_dirs(self, dirpath, exporter):
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
        message, exporter.current_item.name, exporter.default_file_extension)
  
  def _export_once_wrapper(
        self, export_func, run_mode, image, raw_item, output_filepath, file_extension):
    with self.export_context_manager(
           run_mode, image, raw_item, output_filepath, *self.export_context_manager_args):
      self._export_once(export_func, run_mode, image, raw_item, output_filepath, file_extension)
  
  def _get_run_mode(self, file_extension):
    file_extension_property = self._file_extension_properties[file_extension]
    if file_extension_property.is_valid and file_extension_property.processed_count > 0:
      return gimpenums.RUN_WITH_LAST_VALS
    else:
      return self.initial_run_mode
  
  def _get_export_func(self, file_extension):
    return pg.fileformats.get_save_procedure(file_extension)
  
  def _export_once(self, export_func, run_mode, image, raw_item, output_filepath, file_extension):
    self._current_export_status = ExportStatuses.NOT_EXPORTED_YET
    
    try:
      export_func(
        run_mode,
        image,
        raw_item,
        pg.utils.safe_encode_gimp(output_filepath),
        pg.utils.safe_encode_gimp(os.path.basename(output_filepath)))
    except RuntimeError as e:
      # HACK: Examining the exception message seems to be the only way to determine
      # some specific cases of export failure.
      if self._was_export_canceled_by_user(str(e)):
        raise ExportCancelError(str(e))
      elif self._should_export_again_with_interactive_run_mode(str(e), run_mode):
        self._prepare_export_with_interactive_run_mode()
      elif self._should_export_again_with_default_file_extension(file_extension):
        self._prepare_export_with_default_file_extension(file_extension)
      else:
        raise ExportError(str(e), raw_item.name, self._default_file_extension)
    else:
      self._current_export_status = ExportStatuses.EXPORT_SUCCESSFUL
  
  def _was_export_canceled_by_user(self, exception_message):
    return any(
      message in exception_message.lower() for message in ['cancelled', 'canceled'])
  
  def _should_export_again_with_interactive_run_mode(
        self, exception_message, current_run_mode):
    return (
      'calling error' in exception_message.lower()
      and current_run_mode in (
        gimpenums.RUN_WITH_LAST_VALS, gimpenums.RUN_NONINTERACTIVE))
  
  def _prepare_export_with_interactive_run_mode(self):
    self._current_export_status = ExportStatuses.FORCE_INTERACTIVE
  
  def _should_export_again_with_default_file_extension(self, file_extension):
    return file_extension != self._default_file_extension
  
  def _prepare_export_with_default_file_extension(self, file_extension):
    self._file_extension_properties[file_extension].is_valid = False
    self._current_export_status = ExportStatuses.USE_DEFAULT_FILE_EXTENSION
  
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


class _FileExtensionProperties(object):
  """Mapping of file extensions from `pygimplib.fileformats.file_formats` to
  `_FileExtension` instances.
  
  File extension as a key is always converted to lowercase.
  """
  def __init__(self):
    self._properties = collections.defaultdict(_FileExtension)
    
    for file_format in pg.fileformats.file_formats:
      # This ensures that the file format dialog will be displayed only once per
      # file format if multiple file extensions for the same format are used
      # (e.g. 'jpg', 'jpeg' or 'jpe' for the JPEG format).
      extension_properties = _FileExtension()
      for file_extension in file_format.file_extensions:
        self._properties[file_extension.lower()] = extension_properties
  
  def __getitem__(self, key):
    return self._properties[key.lower()]


@future.utils.python_2_unicode_compatible
class ExportError(Exception):
  
  def __init__(self, message='', item_name=None, file_extension=None):
    super().__init__()
    
    self._message = message
    self.item_name = item_name
    self.file_extension = file_extension
  
  def __str__(self):
    str_ = self._message
    
    if self.item_name:
      str_ += '\n' + _('Layer:') + ' ' + self.item_name
    if self.file_extension:
      str_ += '\n' + _('File extension:') + ' ' + self.file_extension
    
    return str_


class ExportCancelError(ExportError):
  pass


class InvalidOutputDirectoryError(ExportError):
  pass


class InvalidPdbProcedureError(ExportError):
  pass


class ExportStatuses(object):
  EXPORT_STATUSES = (
    NOT_EXPORTED_YET, EXPORT_SUCCESSFUL, FORCE_INTERACTIVE, USE_DEFAULT_FILE_EXTENSION
  ) = (0, 1, 2, 3)
