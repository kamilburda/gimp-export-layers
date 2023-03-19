# -*- coding: utf-8 -*-

"""Plug-in core - exporting layers as separate images."""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import collections
import inspect

from gimp import pdb

from export_layers import pygimplib as pg

from export_layers import builtin_procedures
from export_layers import builtin_constraints
from export_layers import actions
from export_layers import export as export_
from export_layers import exceptions
from export_layers import placeholders


_EXPORTER_ARG_POSITION_IN_PROCEDURES = 0
_EXPORTER_ARG_POSITION_IN_CONSTRAINTS = 0

_NAME_ONLY_ACTION_GROUP = 'name'


class LayerExporter(object):
  """Class exporting layers as separate images, with the support for additional
  actions applied on layers (resize, rename, ...).
  
  Attributes:
  
  * `initial_run_mode` - The run mode to use for the first layer exported.
    For subsequent layers, `gimpenums.RUN_WITH_LAST_VALS` is used. If the file
    format in which the layer is exported to cannot handle
    `gimpenums.RUN_WITH_LAST_VALS`, `gimpenums.RUN_INTERACTIVE` is used.
  
  * `image` - Input `gimp.Image` to export layers from.
  
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
  
  * `refresh` - Used by procedures to control whether to remove layer copies
    once processed (`True`) or to retain them after processing (`False`).
    Setting this to `False` allows e.g. the export procedure to export multiple
    layers at once instead of each layer individually.
  
  * `current_item` (read-only) - An `itemtree._Item` instance currently being
    processed.
  
  * `current_raw_item` - Raw item (`gimp.Layer`) currently being processed.
  
  * `current_image` (read-only) - The current `gimp.Image` containing layer(s)
    being processed. This is usually a copy of `image` to avoid modifying
    original layers.
  
  * `process_contents` (read-only) - See `export()`.
  
  * `process_export` (read-only) - See `export()`.
  
  * `process_names` (read-only) - See `export()`.
  
  * `tagged_items` - Dictionary of (tag name, `itemtree._Item`) pairs containing
    tagged items.
  
  * `inserted_tagged_items` - Dictionary of (tag name, `itemtree._Item`) pairs
    containing tagged items currently inserted in `current_image`.
  
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
    
    self.export_context_manager = (
      export_context_manager if export_context_manager is not None else pg.utils.EmptyContext)
    
    self.export_context_manager_args = (
      export_context_manager_args if export_context_manager_args is not None else [])
    
    self.refresh = True
    
    self._is_preview = False
    
    self._current_item = None
    self._current_raw_item = None
    self._current_image = None
    
    self._process_contents = True
    self._process_export = True
    self._process_names = True
    
    self._exported_raw_items = []
    
    self._should_stop = False
    
    self._invoker = None
    self._initial_invoker = pg.invoker.Invoker()
  
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
  
  @current_raw_item.setter
  def current_raw_item(self, value):
    self._current_raw_item = value
  
  @property
  def current_image(self):
    return self._current_image
  
  @property
  def process_contents(self):
    return self._process_contents
  
  @property
  def process_export(self):
    return self._process_export
  
  @property
  def process_names(self):
    return self._process_names
  
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
  def invoker(self):
    return self._invoker
  
  def export(
        self, item_tree=None, keep_image_copy=False, is_preview=False,
        process_contents=True, process_names=True, process_export=True):
    """Batch-processes and exports layers as separate images.
    
    If `item_tree` is not `None`, use an existing instance of
    `itemtree.ItemTree` instead of creating a new one. If the instance had
    filters (constraints) set, they will be reset.
    
    A copy of the image and the layers to be exported are created so that the
    original image and its soon-to-be exported layers are left intact. The
    image copy is automatically destroyed after the export. To keep the image
    copy, pass `True` to `keep_image_copy`. In that case, this method returns
    the image copy. If an exception was raised or if no layer was exported, this
    method returns `None` and the image copy will be destroyed.
    
    If `is_preview` is `True`, only procedures and constraints that are marked
    as "enabled for previews" will be applied for previews. This has no effect
    during real export.
    
    If `process_contents` is `True`, invoke procedures on layers. Setting this
    to `False` is useful if you require only layer names to be processed.
    
    If `process_names` is `True`, process layer names before export to
    be suitable to save to disk (in particular to remove characters invalid for
    a file system). If `is_preview` is `True` and `process_names` is `True`,
    also invoke built-in procedures modifying item names only (e.g. renaming
    layers).
    
    If `process_export` is `True`, perform export of layers. Setting this
    to `False` is useful to preview the processed contents of a layer without
    saving it to a file.
    """
    self._init_attributes(
      item_tree, keep_image_copy, is_preview,
      process_contents, process_names, process_export)
    self._preprocess_items()
    
    exception_occurred = False
    
    if process_contents:
      self._setup()
    try:
      self._process_items()
    except Exception:
      exception_occurred = True
      raise
    finally:
      if process_contents:
        self._cleanup(exception_occurred)
    
    if process_contents and self._keep_image_copy:
      if self._use_another_image_copy:
        return self._another_image_copy
      else:
        return self._image_copy
    else:
      return None
  
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
    
    This class recognizes several action groups that are invoked at certain
    places when `export()` is called:
    * `'after_create_image_copy'` - invoked after creating an internal copy of
      the original image. The image copy is used for processing each layer in a
      non-destructive manner. Only one argument is accepted - instance of this
      class.
    * `'after_insert_item'` - invoked after a layer was inserted in the image
      copy and immediately before procedures are invoked on the layer. Only one
      argument is accepted - instance of this class.
    * `'after_process_item'` - invoked after all procedures have been applied to
      the layer. Only one argument is accepted - instance of this
      class.
    """
    return self._initial_invoker.add(*args, **kwargs)
  
  def add_constraint(self, func, *args, **kwargs):
    """
    Add a constraint to be applied during `export()`. The first argument is the
    function to act as a filter (returning `True` or `False`). The rest of the
    signature is the same as for `pygimplib.invoker.Invoker.add()`.
    
    For more information, see `add_procedure()`.
    """
    return self._initial_invoker.add(self._get_constraint_func(func), *args, **kwargs)
  
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
        raise exceptions.InvalidPdbProcedureError(
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
    if self._is_preview:
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
  
  def _init_attributes(
        self, item_tree, keep_image_copy, is_preview,
        process_contents, process_names, process_export):
    self._process_contents = process_contents
    self._process_names = process_names
    self._process_export = process_export
    
    self._invoker = pg.invoker.Invoker()
    self._add_actions()
    self._add_name_only_actions()
    
    if item_tree is not None:
      self._item_tree = item_tree
    else:
      self._item_tree = pg.itemtree.LayerTree(self.image, name=pg.config.SOURCE_NAME)
    
    self._keep_image_copy = keep_image_copy
    self._is_preview = is_preview
    
    self._should_stop = False
    
    self._exported_raw_items = []
    
    self._image_copy = None
    
    self._tagged_items = collections.defaultdict(list)
    self._tagged_layer_copies = collections.defaultdict(pg.utils.return_none_func)
    self._inserted_tagged_layers = collections.defaultdict(pg.utils.return_none_func)
    
    self._use_another_image_copy = False
    self._another_image_copy = None
    
    self.progress_updater.reset()
    
    self.refresh = True
    
    self._current_item = None
    self._current_raw_item = None
    self._current_image = None
  
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
    
    self._add_default_rename_procedure([actions.DEFAULT_PROCEDURES_GROUP])
    
    for procedure in actions.walk(self.export_settings['procedures']):
      self._add_action_from_settings(procedure)
    
    self._add_default_export_procedure([actions.DEFAULT_PROCEDURES_GROUP])
    
    for constraint in actions.walk(self.export_settings['constraints']):
      self._add_action_from_settings(constraint)
  
  def _add_name_only_actions(self):
    self._add_default_rename_procedure([_NAME_ONLY_ACTION_GROUP])
    
    for procedure in actions.walk(self.export_settings['procedures']):
      self._add_action_from_settings(
        procedure, [builtin_procedures.NAME_ONLY_TAG], [_NAME_ONLY_ACTION_GROUP])
    
    self._add_default_export_procedure([_NAME_ONLY_ACTION_GROUP])
    
    for constraint in actions.walk(self.export_settings['constraints']):
      self._add_action_from_settings(
        constraint, [builtin_procedures.NAME_ONLY_TAG], [_NAME_ONLY_ACTION_GROUP])
  
  def _add_default_rename_procedure(self, action_groups):
    if not any(
          procedure['orig_name'].value == 'rename_layer' and procedure['enabled'].value
          for procedure in actions.walk(self.export_settings['procedures'])):
      self._invoker.add(
        builtin_procedures.rename_layer,
        groups=action_groups,
        args=[self.export_settings['layer_filename_pattern'].value])
  
  def _add_default_export_procedure(self, action_groups):
    if not any(
          procedure['orig_name'].value == 'export' and procedure['enabled'].value
          for procedure in actions.walk(self.export_settings['procedures'])):
      self._invoker.add(
        export_.export,
        groups=action_groups,
        args=[self.export_settings['file_extension'].value, export_.ExportModes.EACH_LAYER])
  
  def _preprocess_items(self):
    if self._item_tree.filter:
      self._item_tree.reset_filter()
    
    self._set_constraints()
    
    num_items = len(self._item_tree)
    
    if self._keep_image_copy:
      if num_items > 1:
        self._use_another_image_copy = True
      elif num_items < 1:
        self._keep_image_copy = False
    
    self.progress_updater.num_total_tasks = num_items
  
  def _set_constraints(self):
    self._init_tagged_items()
    
    self._invoker.invoke(
      [actions.DEFAULT_CONSTRAINTS_GROUP],
      [self],
      additional_args_position=_EXPORTER_ARG_POSITION_IN_CONSTRAINTS)
  
  def _init_tagged_items(self):
    with self._item_tree.filter.add_temp(builtin_constraints.has_tags):
      for item in self._item_tree:
        for tag in item.tags:
          self._tagged_items[tag].append(item)
  
  def _process_items(self):
    for item in self._item_tree:
      if self._should_stop:
        raise exceptions.BatcherCancelError('stopped by user')
      
      self._process_item(item)
  
  def _process_item(self, item):
    self._current_item = item
    self.current_raw_item = item.raw
    
    if self._is_preview and self._process_names:
      self._process_item_with_name_only_actions()
    
    if self._process_contents:
      self._process_item_with_actions(item, self.current_raw_item)
      
      if self.refresh:
        self._postprocess_item(self.current_raw_item)
    
    self.progress_updater.update_tasks()
  
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
      self._another_image_copy = pg.pdbutils.create_image_from_metadata(self.current_image)
      pdb.gimp_image_undo_freeze(self._another_image_copy)
    
    if pg.config.DEBUG_IMAGE_PROCESSING:
      self._display_id = pdb.gimp_display_new(self.current_image)
  
  def _cleanup(self, exception_occurred=False):
    self._copy_non_modifying_parasites(self.current_image, self.image)
    
    pdb.gimp_image_undo_thaw(self.current_image)
    
    if pg.config.DEBUG_IMAGE_PROCESSING:
      pdb.gimp_display_delete(self._display_id)
    
    for tagged_layer_copy in self._tagged_layer_copies.values():
      if tagged_layer_copy is not None:
        pdb.gimp_item_delete(tagged_layer_copy)
    
    if ((not self._keep_image_copy or self._use_another_image_copy)
        or exception_occurred):
      pg.pdbutils.try_delete_image(self.current_image)
      if self._use_another_image_copy:
        pdb.gimp_image_undo_thaw(self._another_image_copy)
        if exception_occurred:
          pg.pdbutils.try_delete_image(self._another_image_copy)
    
    pdb.gimp_context_pop()
    
    self._current_item = None
    self._current_raw_item = None
    self._current_image = None
  
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
  
  def _process_item_with_name_only_actions(self):
    self._invoker.invoke(
      [_NAME_ONLY_ACTION_GROUP],
      [self],
      additional_args_position=_EXPORTER_ARG_POSITION_IN_PROCEDURES)
  
  def _process_item_with_actions(self, item, raw_item):
    raw_item_copy = builtin_procedures.copy_and_insert_layer(
      self.current_image, raw_item, None, len(self.current_image.layers))
    
    self.current_raw_item = raw_item_copy
    self.current_raw_item.name = raw_item.name
    
    self._invoker.invoke(
      ['after_insert_item'],
      [self],
      additional_args_position=_EXPORTER_ARG_POSITION_IN_PROCEDURES)
    
    self._invoker.invoke(
      [actions.DEFAULT_PROCEDURES_GROUP],
      [self],
      additional_args_position=_EXPORTER_ARG_POSITION_IN_PROCEDURES)
    
    self._invoker.invoke(
      ['after_process_item'],
      [self],
      additional_args_position=_EXPORTER_ARG_POSITION_IN_PROCEDURES)
  
  def _postprocess_item(self, raw_item):
    if not self._keep_image_copy:
      for layer in self.current_image.layers:
        pdb.gimp_image_remove_layer(self.current_image, layer)
    else:
      if self._use_another_image_copy:
        another_raw_item_copy = pg.pdbutils.copy_and_paste_layer(
          raw_item, self._another_image_copy, None, len(self._another_image_copy.layers),
          remove_lock_attributes=True)
        
        another_raw_item_copy.name = raw_item.name
        
        for layer in self.current_image.layers:
          pdb.gimp_image_remove_layer(self.current_image, layer)
