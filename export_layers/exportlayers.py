#
# This file is part of Export Layers.
#
# Copyright (C) 2013-2016 khalim19 <khalim19@gmail.com>
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
# along with Export Layers.  If not, see <http://www.gnu.org/licenses/>.
#

"""
This module:
* is the core of the plug-in
* defines a class that exports layers as individual images
* defines filter rules for layers
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

str = unicode

import collections
import contextlib
import datetime
import functools
import os

import gimp
import gimpenums

pdb = gimp.pdb

import export_layers.pygimplib as pygimplib

from export_layers.pygimplib import objectfilter
from export_layers.pygimplib import operations
from export_layers.pygimplib import overwrite
from export_layers.pygimplib import pgfileformats
from export_layers.pygimplib import pgitemtree
from export_layers.pygimplib import pgpath
from export_layers.pygimplib import pgpdb
from export_layers.pygimplib import pgutils
from export_layers.pygimplib import progress

#===============================================================================


class ExportLayersError(Exception):
  
  def __init__(self, message="", layer=None, file_extension=None):
    super(ExportLayersError, self).__init__()
    
    self.message = message
    
    try:
      self.layer_name = layer.name
    except AttributeError:
      self.layer_name = None
    
    self.file_extension = file_extension
  
  def __str__(self):
    str_ = self.message
    
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

# Operations


def execute_operation_only_if_setting(operation, setting):
  def _execute_operation_only_if_setting(*operation_args, **operation_kwargs):
    if setting.value:
      return operation(*operation_args, **operation_kwargs)
    else:
      return False
  
  return _execute_operation_only_if_setting


def ignore_layer_modes(image, layer, layer_exporter):
  layer.mode = gimpenums.NORMAL_MODE


def inherit_transparency_from_layer_groups(image, layer, layer_exporter):
  layer.opacity = 100.0 * functools.reduce(
    lambda layer1_opacity, layer2_opacity: layer1_opacity * layer2_opacity,
    [parent.item.opacity / 100.0 for parent in layer_exporter.current_layer_elem.parents]
    + [layer_exporter.current_layer_elem.item.opacity / 100.0])


def autocrop_layer(image, layer, layer_exporter):
  pdb.plug_in_autocrop_layer(image, layer)


def autocrop_to_tagged_layer(tag, image, layer, layer_exporter):
  tagged_layer = layer_exporter.inserted_tagged_layers[tag]
  if tagged_layer is not None:
    image.active_layer = tagged_layer
    pdb.plug_in_autocrop_layer(image, tagged_layer)
    return True
  else:
    return False


def set_active_layer(image, layer, layer_exporter):
  image.active_layer = layer


def set_active_layer_after_operation(image, layer, layer_exporter):
  operation_executed = yield
  
  if operation_executed or operation_executed is None:
    set_active_layer(image, layer, layer_exporter)


def copy_and_insert_layer(image, layer, parent=None, position=0):
  layer_copy = pdb.gimp_layer_new_from_drawable(layer, image)
  pdb.gimp_image_insert_layer(image, layer_copy, parent, position)
  pdb.gimp_item_set_visible(layer_copy, True)
  
  if pdb.gimp_item_is_group(layer_copy):
    layer_copy = pgpdb.merge_layer_group(layer_copy)
  
  return layer_copy

  
def _insert_tagged_layer(image, tag, layer_exporter, positon=0):
  if not layer_exporter.tagged_layer_elems[tag]:
    return
  
  if layer_exporter.tagged_layer_copies[tag] is None:
    layer_group = pdb.gimp_layer_group_new(image)
    pdb.gimp_image_insert_layer(image, layer_group, None, positon)
    
    for i, layer_elem in enumerate(layer_exporter.tagged_layer_elems[tag]):
      layer_copy = copy_and_insert_layer(image, layer_elem.item, layer_group, i)
      layer_exporter.operations_executor.execute(["after_insert_layer"], image, layer_copy, layer_exporter)
    
    layer_exporter.inserted_tagged_layers[tag] = pgpdb.merge_layer_group(layer_group)
    layer_exporter.tagged_layer_copies[tag] = (
      pdb.gimp_layer_copy(layer_exporter.inserted_tagged_layers[tag], True))
  else:
    layer_exporter.inserted_tagged_layers[tag] = (
      pdb.gimp_layer_copy(layer_exporter.tagged_layer_copies[tag], True))
    pdb.gimp_image_insert_layer(image, layer_exporter.inserted_tagged_layers[tag], None, positon)


def insert_background_layer(tag, image, layer, layer_exporter):
  _insert_tagged_layer(image, tag, layer_exporter, positon=len(image.layers))


def insert_foreground_layer(tag, image, layer, layer_exporter):
  _insert_tagged_layer(image, tag, layer_exporter, positon=0)


#===============================================================================


_BUILTIN_OPERATIONS_DEFAULT_GROUP = "process_layer"

_operations_executor = operations.OperationsExecutor()

_operations_executor.add_foreach_operation(set_active_layer_after_operation, [_BUILTIN_OPERATIONS_DEFAULT_GROUP])

_builtin_operations_and_settings = {
  'ignore_layer_modes': [ignore_layer_modes],
  'autocrop': [autocrop_layer],
  'inherit_transparency_from_layer_groups': [inherit_transparency_from_layer_groups],
  'insert_background_layers': [insert_background_layer, ["background"]],
  'insert_foreground_layers': [insert_foreground_layer, ["foreground"]],
  'autocrop_to_background': [autocrop_to_tagged_layer, ["background"]],
  'autocrop_to_foreground': [autocrop_to_tagged_layer, ["foreground"]]
}

_operation_settings_and_ids = {}


def add_operation(base_setting, operation_group=_BUILTIN_OPERATIONS_DEFAULT_GROUP):
  if base_setting.name in _builtin_operations_and_settings:
    operation_item = _builtin_operations_and_settings[base_setting.name]
    operation = operation_item[0]
    operation_args = operation_item[1] if len(operation_item) > 1 else ()
    operation_kwargs = operation_item[2] if len(operation_item) > 2 else {}
    
    _operation_settings_and_ids[base_setting.name] = _operations_executor.add_operation(
      execute_operation_only_if_setting(operation, base_setting),
      [operation_group],
      *operation_args, **operation_kwargs)


def reorder_operation(setting, new_position, operation_group=_BUILTIN_OPERATIONS_DEFAULT_GROUP):
  if setting.name in _operation_settings_and_ids:
    _operations_executor.reorder_operation(_operation_settings_and_ids[setting.name], operation_group, new_position)


def remove_operation(setting, operation_group=_BUILTIN_OPERATIONS_DEFAULT_GROUP):
  if setting.name in _operation_settings_and_ids:
    _operations_executor.remove_operation(_operation_settings_and_ids[setting.name])


#===============================================================================


class LayerFilterRules(object):
  
  @staticmethod
  def is_layer(layer_elem):
    return layer_elem.item_type == layer_elem.ITEM
  
  @staticmethod
  def is_nonempty_group(layer_elem):
    return layer_elem.item_type == layer_elem.NONEMPTY_GROUP
  
  @staticmethod
  def is_empty_group(layer_elem):
    return layer_elem.item_type == layer_elem.EMPTY_GROUP
  
  @staticmethod
  def is_top_level(layer_elem):
    return layer_elem.depth == 0
  
  @staticmethod
  def is_path_visible(layer_elem):
    return layer_elem.path_visible
  
  @staticmethod
  def has_matching_file_extension(layer_elem, file_extension):
    return layer_elem.get_file_extension() == file_extension.lower()
  
  @staticmethod
  def has_tags(layer_elem, *tags):
    if tags:
      return any(tag for tag in tags if tag in layer_elem.tags)
    else:
      return bool(layer_elem.tags)
  
  @staticmethod
  def has_no_tags(layer_elem, *tags):
    return not LayerFilterRules.has_tags(layer_elem, *tags)
  
  @staticmethod
  def is_layer_in_selected_layers(layer_elem, selected_layers):
    return layer_elem.item.ID in selected_layers


#===============================================================================


class _FileExtensionProperties(object):
  """
  This class contains additional properties for a file extension.
  
  Attributes:
  
  * `is_valid` - If True, file extension is valid and can be used in filenames
    for file export procedures.
  
  * `processed_count` - Number of items with the specific file extension that
    have already been exported.
  """
  
  def __init__(self):
    self.is_valid = True
    self.processed_count = 0


class ExportStatuses(object):
  EXPORT_STATUSES = (
    NOT_EXPORTED_YET, EXPORT_SUCCESSFUL, FORCE_INTERACTIVE, USE_DEFAULT_FILE_EXTENSION
  ) = (0, 1, 2, 3)


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
    `overwrite.NoninteractiveOverwriteChooser` is used by default.
  
  * `progress_updater` - `ProgressUpdater` instance that indicates the number of
    layers exported. If no progress update is desired, pass None.
  
  * `should_stop` - Can be used to stop the export prematurely. If True,
    the export is stopped after exporting the currently processed layer.
  
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
  
  * `operations_executor` - `operations.OperationsExecutor` instance to manage
    operations applied on layers.
  """
  
  BUILTIN_TAGS = {
    'background': _("Background"),
    'foreground': _("Foreground")
  }
  
  SUGGESTED_LAYER_FILENAME_PATTERNS = [
    ("image001", "image[001]", []),
    (_("Layer name"), "[layer name]", ["keep extension/keep only identical extension"]),
    (_("Image name"), "[image name]", ["keep extension"]),
    (_("Layer path"), "[layer path]", ["-"]),
    (_("Tags"), "[tags]", ["specific tags..."]),
    (_("Current date"), "[current date]", ["%Y-%m-%d"]),
  ]
  
  def __init__(self, initial_run_mode, image, export_settings, overwrite_chooser=None, progress_updater=None,
               layer_tree=None, export_context_manager=None, export_context_manager_args=None):
    self.initial_run_mode = initial_run_mode
    self.image = image
    self.export_settings = export_settings
    self.overwrite_chooser = (
      overwrite_chooser if overwrite_chooser is not None
      else overwrite.NoninteractiveOverwriteChooser(self.export_settings['overwrite_mode'].value))
    self.progress_updater = progress_updater if progress_updater is not None else progress.ProgressUpdater(None)
    self._layer_tree = layer_tree
    self.export_context_manager = (
      export_context_manager if export_context_manager is not None else pgutils.EmptyContext)
    self.export_context_manager_args = (
      export_context_manager_args if export_context_manager_args is not None else [])
    
    self.should_stop = False
    
    self._exported_layers = []
    self._current_layer_elem = None
    
    self._processing_groups = {
      'layer_contents': [self._setup, self._cleanup, self._process_layer, self._postprocess_layer],
      'layer_name': [self._preprocess_layer_name, self._preprocess_empty_group_name, self._process_layer_name],
      '_postprocess_layer_name': [self._postprocess_layer_name],
      'export': [self._make_dirs, self._export]
    }
    
    self._processing_groups_functions = {}
    for functions in self._processing_groups.values():
      for function in functions:
        self._processing_groups_functions[function.__name__] = function
    
    self._operations_executor = operations.OperationsExecutor()
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
  def tagged_layer_elems(self):
    return self._tagged_layer_elems
  
  @property
  def inserted_tagged_layers(self):
    return self._inserted_tagged_layers
  
  @property
  def tagged_layer_copies(self):
    return self._tagged_layer_copies
  
  @property
  def operations_executor(self):
    return self._operations_executor
  
  def export(self, processing_groups=None, layer_tree=None, keep_exported_layers=False):
    """
    Export layers as separate images from the specified image.
    
    `processing_groups` is a list of strings that constraints the execution of
    the export. Multiple groups be specified. The following groups are
    supported:
    
    * 'layer_contents' - Perform only operations manipulating the layer itself,
      such as cropping, resizing, etc. This is useful to preview the layer(s).
    
    * 'layer_name' - Perform only operations manipulating layer names and layer
      tree (but not layer contents). This is useful to preview the names of the
      exported layers.
    
    * 'export' - Perform only operations that export the layer or create
      directories for the layer.
    
    If `processing_groups` is None or empty, perform normal export.
    
    If `layer_tree` is not None, use an existing instance of
    `pgitemtree.LayerTree` instead of creating a new one. If the instance had
    filters set, they will be reset.
    
    A copy of the image and the layers to be exported are created so that the
    original image and its soon-to-be exported layers are left intact. The
    copies are automatically destroyed after their export. To keep the copies,
    pass True to `keep_exported_layers`. In that case, this method returns the
    image copy containing the exported layers. It is up to you to destroy the
    image copy. The method returns None if an exception was raised or if no
    layer was exported; in that case, the image copy is automatically destroyed.
    """
    
    self._init_attributes(processing_groups, layer_tree, keep_exported_layers)
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
    
    if self._keep_exported_layers:
      if self._use_another_image_copy:
        return self._another_image_copy
      else:
        return self._image_copy
    else:
      return None
  
  @contextlib.contextmanager
  def modify_export_settings(self, export_settings_to_modify, settings_events_to_temporarily_disable=None):
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
  
  def _add_operations_initial(self):
    self._operations_executor.add_operation(set_active_layer, ["process_layer"])
    self._operations_executor.add_executor(_operations_executor, ["process_layer"])
  
  def _init_attributes(self, processing_groups, layer_tree, keep_exported_layers):
    self._enable_disable_processing_groups(processing_groups)
    
    if layer_tree is not None:
      self._layer_tree = layer_tree
    else:
      self._layer_tree = pgitemtree.LayerTree(
        self.image, name=pygimplib.config.SOURCE_PERSISTENT_NAME, is_filtered=True)
    
    self._keep_exported_layers = keep_exported_layers
    
    self.should_stop = False
    
    self._exported_layers = []
    
    self._current_layer_elem = None
    self._current_file_extension = None
    
    self._output_directory = self.export_settings['output_directory'].value
    self._include_item_path = self.export_settings['layer_groups_as_folders'].value
    
    self._image_copy = None
    self._tagged_layer_elems = collections.defaultdict(list)
    self._tagged_layer_copies = collections.defaultdict(lambda: None)
    self._inserted_tagged_layers = collections.defaultdict(lambda: None)
    
    self._use_another_image_copy = False
    self._another_image_copy = None
    
    self.progress_updater.reset()
    
    self._file_extension_properties = self._prefill_file_extension_properties()
    self._default_file_extension = self.export_settings['file_extension'].value.lstrip(".").lower()
    self._file_extension_to_assign = self._default_file_extension
    self._file_export_func = pgfileformats.get_save_procedure(self._default_file_extension)
    self._current_layer_export_status = ExportStatuses.NOT_EXPORTED_YET
    self._current_overwrite_mode = None
    
    if self.export_settings['layer_filename_pattern'].value:
      pattern = self.export_settings['layer_filename_pattern'].value
    else:
      pattern = self.export_settings['layer_filename_pattern'].default_value
    
    self._filename_pattern_generator = pgpath.StringPatternGenerator(
      pattern=pattern,
      fields=self._get_fields_for_layer_filename_pattern())
    # key: _ItemTreeElement parent ID (None for root); value: list of pattern number generators
    self._pattern_number_filename_generators = {None: self._filename_pattern_generator.get_number_generators()}
  
  def _enable_disable_processing_groups(self, processing_groups):
    for functions in self._processing_groups.values():
      for function in functions:
        setattr(self, function.__name__, self._processing_groups_functions[function.__name__])
    
    if processing_groups:
      if (not self.export_settings['more_filters/only_selected_layers'].value
          and 'layer_name' in processing_groups):
        processing_groups.append('_postprocess_layer_name')
      
      for processing_group, functions in self._processing_groups.items():
        if processing_group not in processing_groups:
          for function in functions:
            setattr(self, function.__name__, lambda *args, **kwargs: None)
  
  def _get_fields_for_layer_filename_pattern(self):
    
    def _get_layer_name(file_extension_strip_mode=None):
      layer_elem = self._current_layer_elem
      
      if file_extension_strip_mode in ["keep extension", "keep only identical extension"]:
        file_extension = self._current_file_extension
        if file_extension:
          if file_extension_strip_mode == "keep only identical extension":
            if file_extension == self._default_file_extension:
              return layer_elem.name
          else:
            return layer_elem.name
      
      return layer_elem.get_base_name()
    
    def _get_image_name(keep_extension=False):
      image_name = self.image.name if self.image.name is not None else _("Untitled")
      if keep_extension == "keep extension":
        return image_name
      else:
        return pgitemtree.set_file_extension(image_name, "")
    
    def _get_layer_path(separator="-"):
      return separator.join(
        [parent.name for parent in self._current_layer_elem.parents] + [self._current_layer_elem.name])
    
    def _get_current_date(date_format="%Y-%m-%d"):
      return datetime.datetime.now().strftime(date_format)
    
    def _get_tags(*tags):
      tags_to_insert = []
      
      def _insert_tag(tag):
        if tag in self.BUILTIN_TAGS:
          tag_display_name = self.BUILTIN_TAGS[tag]
        else:
          tag_display_name = tag
        tags_to_insert.append(tag_display_name)
      
      def _get_tag_from_tag_display_name(tag_display_name):
        return list(self.BUILTIN_TAGS.keys())[list(self.BUILTIN_TAGS.values()).index(tag_display_name)]
      
      if not tags:
        for tag in self._current_layer_elem.tags:
          _insert_tag(tag)
      else:
        for tag in tags:
          if tag in self.BUILTIN_TAGS.keys():
            continue
          if tag in self.BUILTIN_TAGS.values():
            tag = _get_tag_from_tag_display_name(tag)
          if tag in self._current_layer_elem.tags:
            _insert_tag(tag)
      
      tags_to_insert.sort(key=lambda tag: tag.lower())
      return " ".join(["[{0}]".format(tag) for tag in tags_to_insert])
    
    return {'layer name': _get_layer_name,
            'image name': _get_image_name,
            'layer path': _get_layer_path,
            'current date': _get_current_date,
            'tags': _get_tags}
  
  def _prefill_file_extension_properties(self):
    file_extension_properties = collections.defaultdict(_FileExtensionProperties)
    
    for file_format in pgfileformats.file_formats:
      # This ensures that the file format dialog will be displayed only once per
      # file format if multiple file extensions for the same format are used
      # (e.g. "jpg", "jpeg" or "jpe" for the JPEG format).
      extension_properties = _FileExtensionProperties()
      for file_extension in file_format.file_extensions:
        file_extension_properties[file_extension] = extension_properties
    
    return file_extension_properties
  
  def _preprocess_layers(self):
    if self._layer_tree.filter:
      self._layer_tree.reset_filter()
    
    self._set_layer_filters()
    
    with self._layer_tree.filter['layer_types'].remove_rule_temp(LayerFilterRules.is_empty_group, False):
      self.progress_updater.num_total_tasks = len(self._layer_tree)
    
    if self._keep_exported_layers:
      if self.progress_updater.num_total_tasks > 1:
        self._use_another_image_copy = True
      elif self.progress_updater.num_total_tasks < 1:
        self._keep_exported_layers = False
  
  def _set_layer_filters(self):
    self._layer_tree.filter.add_subfilter(
      'layer_types', objectfilter.ObjectFilter(objectfilter.ObjectFilter.MATCH_ANY))
    
    self._layer_tree.filter['layer_types'].add_rule(LayerFilterRules.is_layer)
    
    with (self._layer_tree.filter['layer_types'].add_rule_temp(LayerFilterRules.is_nonempty_group)
          if self.export_settings['layer_groups_as_folders'].value else pgutils.empty_context):
      with self._layer_tree.filter.add_rule_temp(LayerFilterRules.has_tags):
        for layer_elem in self._layer_tree:
          for tag in layer_elem.tags:
            self._tagged_layer_elems[tag].append(layer_elem)
    
    if self.export_settings['more_operations/merge_layer_groups'].value:
      self._layer_tree.filter.add_rule(LayerFilterRules.is_top_level)
      self._layer_tree.filter['layer_types'].add_rule(LayerFilterRules.is_nonempty_group)
    
    if self.export_settings['only_visible_layers'].value:
      self._layer_tree.filter.add_rule(LayerFilterRules.is_path_visible)
    
    if self.export_settings['more_operations/create_folders_for_empty_groups'].value:
      self._layer_tree.filter['layer_types'].add_rule(LayerFilterRules.is_empty_group)
    
    if self.export_settings['more_filters/only_layers_matching_file_extension'].value:
      self._layer_tree.filter.add_rule(LayerFilterRules.has_matching_file_extension, self._default_file_extension)
    
    if self.export_settings['more_filters/only_non_tagged_layers'].value:
      self._layer_tree.filter.add_rule(LayerFilterRules.has_no_tags)
    
    if self.export_settings['more_filters/only_tagged_layers'].value:
      self._layer_tree.filter.add_rule(LayerFilterRules.has_tags)
    
    if self.export_settings['more_filters/only_selected_layers'].value:
      self._layer_tree.filter.add_rule(
        LayerFilterRules.is_layer_in_selected_layers, self.export_settings['selected_layers'].value[self.image.ID])
      if self.export_settings['layer_groups_as_folders'].value:
        self._layer_tree.filter['layer_types'].add_rule(LayerFilterRules.is_nonempty_group)
  
  def _export_layers(self):
    for layer_elem in self._layer_tree:
      if self.should_stop:
        raise ExportLayersCancelError("export stopped by user")
      
      self._current_layer_elem = layer_elem
      self._current_file_extension = layer_elem.get_file_extension()
      
      if layer_elem.item_type in (layer_elem.ITEM, layer_elem.NONEMPTY_GROUP):
        self._process_and_export_item(layer_elem)
      elif layer_elem.item_type == layer_elem.EMPTY_GROUP:
        self._process_and_export_empty_group(layer_elem)
      else:
        raise ValueError(
          "invalid/unsupported item type '{0}' of _ItemTreeElement '{1}'".format(
            layer_elem.item_type, layer_elem.name))
  
  def _process_and_export_item(self, layer_elem):
    layer = layer_elem.item
    layer_copy = self._process_layer(layer_elem, self._image_copy, layer)
    self._preprocess_layer_name(layer_elem)
    self._export_layer(layer_elem, self._image_copy, layer_copy)
    self._postprocess_layer(self._image_copy, layer_copy)
    self._postprocess_layer_name(layer_elem)
    self.progress_updater.update_tasks()
    
    if self._current_overwrite_mode != overwrite.OverwriteModes.SKIP:
      self._exported_layers.append(layer)
      self._file_extension_properties[self._file_extension_to_assign].processed_count += 1
  
  def _process_and_export_empty_group(self, layer_elem):
    self._preprocess_empty_group_name(layer_elem)
    self._make_dirs(layer_elem.get_filepath(self._output_directory, self._include_item_path))
  
  def _setup(self):
    # Save context in case hook functions modify the context without reverting to its original state.
    pdb.gimp_context_push()
    
    self._image_copy = pgpdb.duplicate(self.image, metadata_only=True)
    pdb.gimp_image_undo_freeze(self._image_copy)
    
    self._operations_executor.execute(["after_create_image_copy"], self._image_copy)
    
    if self._use_another_image_copy:
      self._another_image_copy = pgpdb.duplicate(self._image_copy, metadata_only=True)
      pdb.gimp_image_undo_freeze(self._another_image_copy)
    
    if pygimplib.config.DEBUG_IMAGE_PROCESSING:
      self._display_id = pdb.gimp_display_new(self._image_copy)
  
  def _cleanup(self, exception_occurred=False):
    if pygimplib.config.DEBUG_IMAGE_PROCESSING:
      pdb.gimp_display_delete(self._display_id)
    
    self._copy_non_modifying_parasites(self._image_copy, self.image)
    
    pdb.gimp_image_undo_thaw(self._image_copy)
    if (not self._keep_exported_layers or self._use_another_image_copy) or exception_occurred:
      pdb.gimp_image_delete(self._image_copy)
      if self._use_another_image_copy:
        pdb.gimp_image_undo_thaw(self._another_image_copy)
        if exception_occurred:
          pdb.gimp_image_delete(self._another_image_copy)
    
    for tagged_layer_copy in self._tagged_layer_copies.values():
      if tagged_layer_copy is not None:
        pdb.gimp_item_delete(tagged_layer_copy)
    
    pdb.gimp_context_pop()
  
  def _copy_non_modifying_parasites(self, src_image, dest_image):
    for parasite_name in src_image.parasite_list():
      if dest_image.parasite_find(parasite_name) is None:
        parasite = src_image.parasite_find(parasite_name)
        # Don't attach persistent or undoable parasites to avoid modifying `dest_image`.
        if parasite.flags == 0:
          dest_image.parasite_attach(parasite)
  
  def _process_layer(self, layer_elem, image, layer):
    layer_copy = copy_and_insert_layer(image, layer, None, 0)
    self._operations_executor.execute(["after_insert_layer"], image, layer_copy, self)
    
    self._operations_executor.execute(["process_layer"], image, layer_copy, self)
    
    layer_copy = self._merge_and_resize_layer(image, layer_copy)
    
    image.active_layer = layer_copy
    
    layer_copy.name = layer.name
    
    return layer_copy
  
  def _postprocess_layer(self, image, layer):
    if not self._keep_exported_layers:
      pdb.gimp_image_remove_layer(image, layer)
    else:
      if self._use_another_image_copy:
        another_layer_copy = pdb.gimp_layer_new_from_drawable(layer, self._another_image_copy)
        pdb.gimp_image_insert_layer(
          self._another_image_copy, another_layer_copy, None, len(self._another_image_copy.layers))
        another_layer_copy.name = layer.name
        
        pdb.gimp_image_remove_layer(image, layer)
  
  def _merge_and_resize_layer(self, image, layer):
    if not self.export_settings['use_image_size'].value:
      layer_offset_x, layer_offset_y = layer.offsets
      pdb.gimp_image_resize(image, layer.width, layer.height, -layer_offset_x, -layer_offset_y)
    
    layer = pdb.gimp_image_merge_visible_layers(image, gimpenums.EXPAND_AS_NECESSARY)
    
    pdb.gimp_layer_resize_to_image_size(layer)
    
    return layer
  
  def _preprocess_layer_name(self, layer_elem):
    self._rename_layer_by_pattern(layer_elem)
    self._set_file_extension(layer_elem)
    self._layer_tree.validate_name(layer_elem)
  
  def _preprocess_empty_group_name(self, layer_elem):
    self._layer_tree.validate_name(layer_elem)
    self._layer_tree.uniquify_name(layer_elem, self._include_item_path)
  
  def _process_layer_name(self, layer_elem):
    self._layer_tree.uniquify_name(
      layer_elem, self._include_item_path, self._get_uniquifier_position(layer_elem.name))
  
  def _postprocess_layer_name(self, layer_elem):
    if self.export_settings['more_filters/only_selected_layers'].value:
      if layer_elem.item_type == layer_elem.NONEMPTY_GROUP:
        self._layer_tree.reset_name(layer_elem)
  
  def _rename_layer_by_pattern(self, layer_elem):
    if self.export_settings['layer_groups_as_folders'].value:
      parent = layer_elem.parent.item.ID if layer_elem.parent is not None else None
      if parent not in self._pattern_number_filename_generators:
        self._pattern_number_filename_generators[parent] = self._filename_pattern_generator.reset_numbering()
      else:
        self._filename_pattern_generator.set_number_generators(self._pattern_number_filename_generators[parent])
    
    layer_elem.name = self._filename_pattern_generator.generate()
  
  def _set_file_extension(self, layer_elem):
    if self.export_settings['more_operations/use_file_extensions_in_layer_names'].value:
      if self._current_file_extension and self._file_extension_properties[self._current_file_extension].is_valid:
        self._file_extension_to_assign = self._current_file_extension
      else:
        self._file_extension_to_assign = self._default_file_extension
      layer_elem.set_file_extension(self._file_extension_to_assign, keep_extra_periods=True)
    else:
      layer_elem.name += "." + self._file_extension_to_assign
  
  def _get_uniquifier_position(self, str_):
    return len(str_) - len("." + self._file_extension_to_assign)
  
  def _make_dirs(self, path):
    try:
      pgpath.make_dirs(path)
    except OSError as e:
      try:
        message = e.args[1]
        if e.filename is not None:
          message += ": \"{0}\"".format(e.filename)
      except (IndexError, AttributeError):
        message = str(e)
      
      raise InvalidOutputDirectoryError(message, self._current_layer_elem, self._default_file_extension)
  
  def _export_layer(self, layer_elem, image, layer):
    self._process_layer_name(layer_elem)
    self._export(layer_elem, image, layer)
    
    if self._current_layer_export_status == ExportStatuses.USE_DEFAULT_FILE_EXTENSION:
      self._set_file_extension(layer_elem)
      self._process_layer_name(layer_elem)
      self._export(layer_elem, image, layer)
  
  def _export(self, layer_elem, image, layer):
    output_filename = layer_elem.get_filepath(self._output_directory, self._include_item_path)
    
    self.progress_updater.update_text(_("Saving '{0}'").format(output_filename))
    
    self._current_overwrite_mode, output_filename = overwrite.handle_overwrite(
      output_filename, self.overwrite_chooser, self._get_uniquifier_position(output_filename))
    
    if self._current_overwrite_mode == overwrite.OverwriteModes.CANCEL:
      raise ExportLayersCancelError("cancelled")
    
    if self._current_overwrite_mode != overwrite.OverwriteModes.SKIP:
      run_mode = self._get_run_mode()
      self._make_dirs(os.path.dirname(output_filename))
      
      self._update_file_export_func()
      
      self._export_once_wrapper(run_mode, image, layer, output_filename)
      if self._current_layer_export_status == ExportStatuses.FORCE_INTERACTIVE:
        self._export_once_wrapper(gimpenums.RUN_INTERACTIVE, image, layer, output_filename)
  
  def _export_once_wrapper(self, run_mode, image, layer, output_filename):
    with self.export_context_manager(run_mode, image, layer, output_filename, *self.export_context_manager_args):
      self._export_once(run_mode, image, layer, output_filename)
  
  def _export_once(self, run_mode, image, layer, output_filename):
    self._current_layer_export_status = ExportStatuses.NOT_EXPORTED_YET
    
    try:
      self._file_export_func(
        run_mode, image, layer, output_filename.encode(), os.path.basename(output_filename).encode())
    except RuntimeError as e:
      # HACK: Since `RuntimeError` could indicate anything, including
      # `pdb.gimp_file_save` failure, this is the only way to intercept that
      # the export was canceled.
      if any(message in e.message.lower() for message in ["cancelled", "canceled"]):
        raise ExportLayersCancelError(e.message)
      # HACK: Try again, this time forcing the interactive mode if the
      # non-interactive mode failed (certain file formats do not allow the
      # non-interactive mode).
      elif "calling error" in e.message.lower():
        if run_mode in (gimpenums.RUN_WITH_LAST_VALS, gimpenums.RUN_NONINTERACTIVE):
          self._current_layer_export_status = ExportStatuses.FORCE_INTERACTIVE
        else:
          raise ExportLayersError(e.message, layer, self._default_file_extension)
      else:
        if self._file_extension_to_assign != self._default_file_extension:
          self._file_extension_properties[self._file_extension_to_assign].is_valid = False
          self._file_extension_to_assign = self._default_file_extension
          self._current_layer_export_status = ExportStatuses.USE_DEFAULT_FILE_EXTENSION
        else:
          raise ExportLayersError(e.message, layer, self._default_file_extension)
    else:
      self._current_layer_export_status = ExportStatuses.EXPORT_SUCCESSFUL
  
  def _get_run_mode(self):
    if self._file_extension_properties[self._file_extension_to_assign].is_valid:
      if self._file_extension_properties[self._file_extension_to_assign].processed_count == 0:
        return self.initial_run_mode
      else:
        return gimpenums.RUN_WITH_LAST_VALS
    else:
      return self.initial_run_mode
  
  def _update_file_export_func(self):
    if self.export_settings['more_operations/use_file_extensions_in_layer_names'].value:
      self._file_export_func = pgfileformats.get_save_procedure(self._file_extension_to_assign)
