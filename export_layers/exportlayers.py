#
# This file is part of Export Layers.
#
# Copyright (C) 2013-2015 khalim19 <khalim19@gmail.com>
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
import os

import gimp
import gimpenums

pdb = gimp.pdb

import export_layers.pygimplib as pygimplib

from export_layers.pygimplib import objectfilter
from export_layers.pygimplib import overwrite
from export_layers.pygimplib import pgfileformats
from export_layers.pygimplib import pgitemdata
from export_layers.pygimplib import pgpath
from export_layers.pygimplib import pgpdb
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
    return layer_elem.level == 0
  
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
    return layer_elem.orig_name in selected_layers


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
  This class exports layers as separate images. Additional operations include:
  * layer processing - resizing/cropping, inserting back/foreground, merging
  * layer name processing - validation, file extension manipulation
  
  Attributes:
  
  * `initial_run_mode` - The run mode to use for the first layer exported.
    For subsequent layers, `gimpenums.RUN_WITH_LAST_VALS` is used. If the file
    format in which the layer is exported to can't handle
    `gimpenums.RUN_WITH_LAST_VALS`, `gimpenums.RUN_INTERACTIVE` is used.
  
  * `image` - GIMP image to export layers from.
  
  * `export_settings` - export settings (main settings of the plug-in). This
    class treats them as read-only.
  
  * `overwrite_chooser` - `OverwriteChooser` instance that is invoked if a file
    with the same name already exists. If None is passed during initialization,
    `overwrite.NoninteractiveOverwriteChooser` is used by default.
  
  * `progress_updater` - `ProgressUpdater` instance that indicates the number of
    layers exported. If no progress update is desired, pass None.
  
  * `should_stop` - Can be used to stop the export prematurely. If True,
    the export is stopped after exporting the currently processed layer.
  
  * `layer_data` - `LayerData` instance containing layers to be exported.
    Defaults to None if no export has been performed yet.
  
  * `exported_layers` - List of layers that were successfully exported. Does not
    include skipped layers (when files with the same names already exist).
  
  * `export_context_manager` - Context manager that wraps exporting a single
    layer. This can be used to perform GUI updates before and after export.
    Required parameters: current run mode, current image, layer to export,
    output filename of the layer.
  
  * `export_context_manager_args` - Additional arguments passed to
    `export_context_manager`.
  """
  
  SUPPORTED_TAGS = collections.OrderedDict([
    ('background', _("Background")),
    ('foreground', _("Foreground"))
  ])
  
  SUGGESTED_LAYER_FILENAME_PATTERNS = [
    ("image001", "image[001]", []),
    (_("Layer name"), "[layer name]", []),
    (_("Image name"), "[image name]", ["keep extension"]),
    (_("Layer path"), "[layer path]", ["-"]),
    (_("Tags"), "[tags]", ["specific tags..."]),
    (_("Current date"), "[current date]", ["%Y-%m-%d"]),
  ]
  
  def __init__(self, initial_run_mode, image, export_settings, overwrite_chooser=None, progress_updater=None,
               export_context_manager=None, export_context_manager_args=None):
    self.initial_run_mode = initial_run_mode
    self.image = image
    self.export_settings = export_settings
    
    if overwrite_chooser is None:
      self.overwrite_chooser = overwrite.NoninteractiveOverwriteChooser(
        self.export_settings['overwrite_mode'].value)
    else:
      self.overwrite_chooser = overwrite_chooser
    
    if progress_updater is None:
      self.progress_updater = progress.ProgressUpdater(None)
    else:
      self.progress_updater = progress_updater
    
    if export_context_manager is not None:
      self.export_context_manager = export_context_manager
    else:
      @contextlib.contextmanager
      def _empty_context(*args, **kwargs):
        yield
      self.export_context_manager = _empty_context
    
    if export_context_manager_args is not None:
      self.export_context_manager_args = export_context_manager_args
    else:
      self.export_context_manager_args = []
    
    self.should_stop = False
    
    self._layer_data = None
    self._exported_layers = []
    
    self._operations = {
      'layer_contents': [self._setup, self._cleanup, self._process_layer, self._postprocess_layer],
      'layer_name': [self._preprocess_layer_name, self._preprocess_empty_group_name, self._process_layer_name],
      'export': [self._make_dirs, self._export]
    }
    
    self._operations_functions = {}
    for functions in self._operations.values():
      for function in functions:
        self._operations_functions[function.__name__] = function
  
  @property
  def layer_data(self):
    return self._layer_data
  
  @property
  def exported_layers(self):
    return self._exported_layers
  
  def export_layers(self, operations=None):
    """
    Export layers as separate images from the specified image.
    
    `operations` is a list of tags that constraints the execution of the export.
    Multiple tags can be specified. The following tags are supported:
    
    * 'layer_name' - Perform only operations manipulating layer names and layer
      tree (but not layer contents). This is useful to preview the names of the
      exported layers.
    
    * 'layer_contents' - Perform only operations manipulating the layer itself,
      such as cropping, resizing, etc. This is useful to preview the layer(s).
    
    * 'export' - Perform only operations that export the layer or create
      directories for the layer.
    
    If `operations` is None or empty, perform normal export.
    """
    
    self._init_attributes(operations)
    self._preprocess_layers()
    
    self._setup()
    try:
      self._export_layers()
    finally:
      self._cleanup()
  
  def _init_attributes(self, operations):
    self._enable_disable_operations(operations)
    
    self.should_stop = False
    self._exported_layers = []
    
    self._current_layer_elem = None
    
    self._output_directory = self.export_settings['output_directory'].value
    self._default_file_extension = self.export_settings['file_extension'].value
    self._include_item_path = self.export_settings['layer_groups_as_folders'].value
    
    self._image_copy = None
    self._layer_data = pgitemdata.LayerData(self.image, is_filtered=True)
    self._tagged_layer_elems = collections.defaultdict(list)
    self._tagged_layer_copies = collections.defaultdict(lambda: None)
    
    self.progress_updater.reset()
    
    self._file_extension_properties = self._prefill_file_extension_properties()
    self._default_file_extension = self._default_file_extension.lstrip(".").lower()
    self._current_file_extension = self._default_file_extension
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
    self._has_custom_filename_pattern = (
      self.export_settings['layer_filename_pattern'].value !=
      self.export_settings['layer_filename_pattern'].default_value)
    # key: _ItemDataElement parent original name (None for root); value: list of pattern number generators
    self._pattern_number_filename_generators = {None: self._filename_pattern_generator.get_number_generators()}
  
  def _enable_disable_operations(self, operations_tags):
    for functions in self._operations.values():
      for function in functions:
        setattr(self, function.__name__, self._operations_functions[function.__name__])
    
    if operations_tags:
      for operation_tag, functions in self._operations.items():
        if operation_tag not in operations_tags:
          for function in functions:
            setattr(self, function.__name__, lambda *args, **kwargs: None)
  
  def _get_fields_for_layer_filename_pattern(self):
    def _get_image_name(keep_extension=False):
      image_name = self.image.name if self.image.name is not None else _("Untitled")
      if keep_extension == "keep extension":
        return image_name
      else:
        return pgitemdata.set_file_extension(image_name, "")
    
    def _get_layer_path(separator="-"):
      return separator.join([parent.name for parent in self._current_layer_elem.parents] +
                            [self._current_layer_elem.name])
    
    def _get_current_date(date_format="%Y-%m-%d"):
      return datetime.datetime.now().strftime(date_format)
    
    def _get_tags(*tags):
      tags_to_insert = []
      
      if not tags:
        tags_to_insert = list(self._current_layer_elem.tags)
      else:
        for tag in tags:
          if tag in self._current_layer_elem.tags:
            tags_to_insert.append(tag)
      
      tags_to_insert.sort()
      tags_to_insert = ["[{0}]".format(tag) for tag in tags_to_insert]
      return " ".join(tags_to_insert)
    
    return {
      'layer name': lambda: self._current_layer_elem.name,
      'image name': _get_image_name,
      'layer path': _get_layer_path,
      'current date': _get_current_date,
      'tags': _get_tags
    }
  
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
    for layer_elem in self._layer_data:
      layer_elem.parse_tags()
    
    self._layer_data.filter.add_subfilter(
      'layer_types', objectfilter.ObjectFilter(objectfilter.ObjectFilter.MATCH_ANY))
    
    self._layer_data.filter['layer_types'].add_rule(LayerFilterRules.is_layer)
    
    if self.export_settings['merge_layer_groups'].value:
      self._layer_data.filter.add_rule(LayerFilterRules.is_top_level)
      self._layer_data.filter['layer_types'].add_rule(LayerFilterRules.is_nonempty_group)
    
    if self.export_settings['ignore_invisible'].value:
      self._layer_data.filter.add_rule(LayerFilterRules.is_path_visible)
    
    if self.export_settings['empty_folders'].value:
      self._layer_data.filter['layer_types'].add_rule(LayerFilterRules.is_empty_group)
    
    if self.export_settings['file_extension_mode'].is_item('only_matching_file_extension'):
      self._layer_data.filter.add_rule(LayerFilterRules.has_matching_file_extension,
                                       self._default_file_extension)
    
    if self.export_settings['tagged_layers_mode'].is_item('special'):
      with self._layer_data.filter.add_rule_temp(LayerFilterRules.has_tags, 'background'):
        self._tagged_layer_elems['background'] = list(self._layer_data)
      with self._layer_data.filter.add_rule_temp(LayerFilterRules.has_tags, 'foreground'):
        self._tagged_layer_elems['foreground'] = list(self._layer_data)
      
      self._layer_data.filter.add_rule(LayerFilterRules.has_no_tags, 'background', 'foreground')
    elif self.export_settings['tagged_layers_mode'].is_item('ignore'):
      self._layer_data.filter.add_rule(LayerFilterRules.has_no_tags)
    elif self.export_settings['tagged_layers_mode'].is_item('ignore_other'):
      self._layer_data.filter.add_rule(LayerFilterRules.has_tags)
    
    if self.export_settings['export_only_selected_layers'].value:
      self._layer_data.filter.add_rule(
        LayerFilterRules.is_layer_in_selected_layers, self.export_settings['selected_layers'].value[self.image.ID])
    
    if (self.export_settings['layer_groups_as_folders'].value and
        self.export_settings['export_only_selected_layers'].value):
      self._layer_data.filter['layer_types'].add_rule(LayerFilterRules.is_nonempty_group)
  
  def _export_layers(self):
    with self._layer_data.filter['layer_types'].remove_rule_temp(LayerFilterRules.is_empty_group, False):
      self.progress_updater.num_total_tasks = len(self._layer_data)
    
    for layer_elem in self._layer_data:
      if self.should_stop:
        raise ExportLayersCancelError("export stopped by user")
      
      self._current_layer_elem = layer_elem
      
      if layer_elem.item_type in (layer_elem.ITEM, layer_elem.NONEMPTY_GROUP):
        self._process_and_export_item(layer_elem)
      elif layer_elem.item_type == layer_elem.EMPTY_GROUP:
        self._process_and_export_empty_group(layer_elem)
      else:
        raise ValueError("invalid/unsupported item type '{0}' of _ItemDataElement '{1}'"
                         .format(layer_elem.item_type, layer_elem.name))
  
  def _process_and_export_item(self, layer_elem):
    layer = layer_elem.item
    layer_copy = self._process_layer(self._image_copy, layer)
    self._preprocess_layer_name(layer_elem)
    self._export_layer(layer_elem, self._image_copy, layer_copy)
    self._postprocess_layer(self._image_copy, layer_copy)
    self._postprocess_layer_name(layer_elem)
    
    self.progress_updater.update_tasks()
    
    if self._current_overwrite_mode != overwrite.OverwriteModes.SKIP:
      self._exported_layers.append(layer)
      self._file_extension_properties[self._current_file_extension].processed_count += 1
  
  def _process_and_export_empty_group(self, layer_elem):
    self._preprocess_empty_group_name(layer_elem)
    self._make_dirs(layer_elem.get_filepath(self._output_directory, self._include_item_path))
  
  def _setup(self):
    # Save context just in case. No need for undo groups or undo freeze here.
    pdb.gimp_context_push()
    # Perform subsequent operations on a new image so that the original image
    # and its soon-to-be exported layers are left intact.
    self._image_copy = pgpdb.duplicate(self.image, metadata_only=True)
    
    if pygimplib.config.DEBUG_IMAGE_PROCESSING:
      self._display_id = pdb.gimp_display_new(self._image_copy)
  
  def _cleanup(self):
    if pygimplib.config.DEBUG_IMAGE_PROCESSING:
      pdb.gimp_display_delete(self._display_id)
    
    pdb.gimp_image_delete(self._image_copy)
    
    for tagged_layer_copy in self._tagged_layer_copies.values():
      if tagged_layer_copy is not None:
        pdb.gimp_item_delete(tagged_layer_copy)
    
    pdb.gimp_context_pop()
  
  def _process_layer(self, image, layer):
    background_layer, self._tagged_layer_copies['background'] = self._insert_layer(
      image, self._tagged_layer_elems['background'], self._tagged_layer_copies['background'], insert_index=0)
    
    layer_copy = pdb.gimp_layer_new_from_drawable(layer, image)
    pdb.gimp_image_insert_layer(image, layer_copy, None, 0)
    # This is necessary for file formats which flatten the image (such as JPG).
    pdb.gimp_item_set_visible(layer_copy, True)
    
    if pdb.gimp_item_is_group(layer_copy):
      layer_copy = pgpdb.merge_layer_group(layer_copy)
    
    if self.export_settings['ignore_layer_modes'].value:
      layer_copy.mode = gimpenums.NORMAL_MODE
    
    image.active_layer = layer_copy
    
    foreground_layer, self._tagged_layer_copies['foreground'] = self._insert_layer(
      image, self._tagged_layer_elems['foreground'], self._tagged_layer_copies['foreground'], insert_index=0)
    
    layer_copy = self._crop_and_merge(image, layer_copy, background_layer, foreground_layer)
    
    # Remove the " copy" suffix from the layer name, which is preserved in
    # formats supporting layers (XCF, PSD, ...).
    layer_copy.name = layer.name
    
    return layer_copy
  
  def _postprocess_layer(self, image, layer):
    pdb.gimp_image_remove_layer(image, layer)
  
  def _insert_layer(self, image, layer_elems, inserted_layer_copy, insert_index=0):
    if not layer_elems:
      return None, None
    
    if inserted_layer_copy is None:
      if self.export_settings['use_image_size'].value:
        # Remove layers outside the image canvas since they won't be visible in
        # the exported layer and because we need to avoid `RuntimeError`
        # when `pdb.gimp_image_merge_visible_layers` with `CLIP_TO_IMAGE`
        # argument tries to merge layers that are all outside the image canvas.
        for i in range(len(layer_elems)):
          if not pgpdb.is_layer_inside_image(image, layer_elems[i].item):
            layer_elems.pop(i)
        
        if not layer_elems:
          return None, None
      
      layer_group = pdb.gimp_layer_group_new(image)
      pdb.gimp_image_insert_layer(image, layer_group, None, insert_index)
      
      for i, layer_elem in enumerate(layer_elems):
        layer_copy = pdb.gimp_layer_new_from_drawable(layer_elem.item, image)
        pdb.gimp_image_insert_layer(image, layer_copy, layer_group, i)
        pdb.gimp_item_set_visible(layer_copy, True)
        if self.export_settings['ignore_layer_modes'].value:
          layer_copy.mode = gimpenums.NORMAL_MODE
        if pdb.gimp_item_is_group(layer_copy):
          layer_copy = pgpdb.merge_layer_group(layer_copy)
      
      layer = pgpdb.merge_layer_group(layer_group)
      
      if self.export_settings['use_image_size'].value:
        pdb.gimp_layer_resize_to_image_size(layer)
      
      inserted_layer_copy = pdb.gimp_layer_copy(layer, True)
      return layer, inserted_layer_copy
    else:
      layer_copy = pdb.gimp_layer_copy(inserted_layer_copy, True)
      pdb.gimp_image_insert_layer(image, layer_copy, None, insert_index)
      return layer_copy, inserted_layer_copy
  
  def _crop_and_merge(self, image, layer, background_layer, foreground_layer):
    has_inserted_layers = background_layer is not None or foreground_layer is not None
    
    inserted_layer_to_crop_to = None
    if self.export_settings['crop_mode'].is_item('crop_to_background'):
      inserted_layer_to_crop_to = background_layer
    elif self.export_settings['crop_mode'].is_item('crop_to_foreground'):
      inserted_layer_to_crop_to = foreground_layer
    
    if not self.export_settings['use_image_size'].value:
      pdb.gimp_image_resize_to_layers(image)
      if self.export_settings['crop_mode'].is_item('crop_to_background', 'crop_to_foreground'):
        if inserted_layer_to_crop_to is not None:
          layer = pdb.gimp_image_merge_visible_layers(image, gimpenums.CLIP_TO_IMAGE)
        if self.export_settings['autocrop'].value:
          pdb.plug_in_autocrop(image, layer)
      else:
        if self.export_settings['autocrop'].value:
          pdb.plug_in_autocrop(image, layer)
        if has_inserted_layers:
          layer = pdb.gimp_image_merge_visible_layers(image, gimpenums.CLIP_TO_IMAGE)
    else:
      if (self.export_settings['crop_mode'].is_item('crop_to_background', 'crop_to_foreground') and
          inserted_layer_to_crop_to is not None):
        if self.export_settings['autocrop'].value:
          image.active_layer = inserted_layer_to_crop_to
          pdb.plug_in_autocrop_layer(image, inserted_layer_to_crop_to)
          image.active_layer = layer
      else:
        if self.export_settings['autocrop'].value:
          pdb.plug_in_autocrop_layer(image, layer)
      
      if has_inserted_layers:
        layer = pdb.gimp_image_merge_visible_layers(image, gimpenums.CLIP_TO_IMAGE)
      
      pdb.gimp_layer_resize_to_image_size(layer)
    
    return layer
  
  def _preprocess_layer_name(self, layer_elem):
    self._strip_file_extension(layer_elem)
    self._rename_layer_by_pattern(layer_elem)
    self._layer_data.validate_name(layer_elem)
  
  def _preprocess_empty_group_name(self, layer_elem):
    self._layer_data.validate_name(layer_elem)
    self._layer_data.uniquify_name(layer_elem, self._include_item_path)
  
  def _process_layer_name(self, layer_elem):
    self._set_file_extension(layer_elem)
    self._layer_data.uniquify_name(layer_elem, self._include_item_path,
                                   self._get_uniquifier_position(layer_elem.name))
  
  def _postprocess_layer_name(self, layer_elem):
    if (layer_elem.item_type == layer_elem.NONEMPTY_GROUP and
        self.export_settings['export_only_selected_layers'].value):
      self._layer_data.reset_name(layer_elem)
  
  def _rename_layer_by_pattern(self, layer_elem):
    if self._has_custom_filename_pattern:
      if self.export_settings['layer_groups_as_folders'].value:
        parent = layer_elem.parent.orig_name if layer_elem.parent is not None else None
        if parent not in self._pattern_number_filename_generators:
          self._pattern_number_filename_generators[parent] = self._filename_pattern_generator.reset_numbering()
        else:
          self._filename_pattern_generator.set_number_generators(self._pattern_number_filename_generators[parent])
      
      layer_elem.name = self._filename_pattern_generator.generate()
  
  def _strip_file_extension(self, layer_elem):
    if self.export_settings['strip_mode'].is_item('identical', 'always'):
      file_extension = layer_elem.get_file_extension()
      if file_extension:
        if self.export_settings['strip_mode'].is_item('identical'):
          if file_extension == self._default_file_extension:
            layer_elem.set_file_extension(None)
        else:
          layer_elem.set_file_extension(None)
  
  def _set_file_extension(self, layer_elem):
    if self.export_settings['file_extension_mode'].is_item('use_as_file_extensions'):
      file_extension = layer_elem.get_file_extension()
      if file_extension and self._file_extension_properties[file_extension].is_valid:
        self._current_file_extension = file_extension
      else:
        layer_elem.set_file_extension(self._default_file_extension)
        self._current_file_extension = self._default_file_extension
    elif self.export_settings['file_extension_mode'].is_item('no_special_handling'):
      layer_elem.name += "." + self._default_file_extension
    
  def _get_uniquifier_position(self, str_):
    return len(str_) - len("." + self._current_file_extension)
  
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
      self._file_export_func(run_mode, image, layer, output_filename.encode(),
                             os.path.basename(output_filename).encode())
    except RuntimeError as e:
      # HACK: Since `RuntimeError` could indicate anything, including
      # `pdb.gimp_file_save` failure, this is the only way to intercept that
      # the export was cancelled.
      if "cancelled" in e.message.lower():
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
        if self._current_file_extension != self._default_file_extension:
          self._file_extension_properties[self._current_file_extension].is_valid = False
          self._current_file_extension = self._default_file_extension
          self._current_layer_export_status = ExportStatuses.USE_DEFAULT_FILE_EXTENSION
        else:
          raise ExportLayersError(e.message, layer, self._default_file_extension)
    else:
      self._current_layer_export_status = ExportStatuses.EXPORT_SUCCESSFUL
  
  def _get_run_mode(self):
    if self._file_extension_properties[self._current_file_extension].is_valid:
      if self._file_extension_properties[self._current_file_extension].processed_count == 0:
        return self.initial_run_mode
      else:
        return gimpenums.RUN_WITH_LAST_VALS
    else:
      return self.initial_run_mode
  
  def _update_file_export_func(self):
    if self.export_settings['file_extension_mode'].is_item('use_as_file_extensions'):
      self._file_export_func = pgfileformats.get_save_procedure(self._current_file_extension)
