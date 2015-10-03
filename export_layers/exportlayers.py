#-------------------------------------------------------------------------------
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
#-------------------------------------------------------------------------------

"""
This module:
* is the core of the plug-in
* defines a class that exports layers as individual images
* defines filter rules for layers
"""

#===============================================================================

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division

str = unicode

#===============================================================================

import os
from collections import defaultdict

import gimp
import gimpenums

from export_layers import constants

from export_layers.pygimplib import pgfileformats
from export_layers.pygimplib import pgpath
from export_layers.pygimplib import pgpdb
from export_layers.pygimplib import pgitemdata
from export_layers.pygimplib import objectfilter
from export_layers.pygimplib import progress

#===============================================================================

pdb = gimp.pdb

#===============================================================================


class ExportLayersError(Exception):
  pass


class ExportLayersCancelError(ExportLayersError):
  pass


#===============================================================================


class OverwriteHandler(object):
  
  """
  This class handles conflicting files using the specified `OverwriteChooser`
  class with the following choices available:
  
    * Replace
    * Skip
    * Rename new file
    * Rename existing file
    * Cancel
  """
  
  __OVERWRITE_MODES = REPLACE, SKIP, RENAME_NEW, RENAME_EXISTING, CANCEL = (0, 1, 2, 3, 4)
  
  @classmethod
  def handle(cls, filename, overwrite_chooser, uniquifier_position=None):
    should_skip = False
    
    if os.path.exists(filename):
      overwrite_chooser.choose(filename=os.path.basename(filename))
      if overwrite_chooser.overwrite_mode == cls.SKIP:
        should_skip = True
      elif overwrite_chooser.overwrite_mode == cls.REPLACE:
        # Nothing needs to be done here.
        pass
      elif overwrite_chooser.overwrite_mode in (cls.RENAME_NEW, cls.RENAME_EXISTING):
        uniq_filename = pgpath.uniquify_filename(filename, uniquifier_position)
        if overwrite_chooser.overwrite_mode == cls.RENAME_NEW:
          filename = uniq_filename
        else:
          os.rename(filename, uniq_filename)
      elif overwrite_chooser.overwrite_mode == cls.CANCEL:
        raise ExportLayersCancelError("cancelled")
    
    return should_skip, filename


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
  def is_enclosed_in_square_brackets(layer_elem):
    return layer_elem.name.startswith("[") and layer_elem.name.endswith("]")
  
  @staticmethod
  def is_not_enclosed_in_square_brackets(layer_elem):
    return not LayerFilterRules.is_enclosed_in_square_brackets(layer_elem)
  
  @staticmethod
  def has_tag(layer_elem, tag):
    return tag in layer_elem.tags


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


class LayerExporter(object):
  
  """
  This class:
  * exports layers as separate images
  * validates layer names
  
  Attributes:
  
  * `initial_run_mode` - The run mode to use for the first layer exported.
    For subsequent layers, `gimpenums.RUN_WITH_LAST_VALS` is used. If the file
    format in which the layer is exported to can't handle
    `gimpenums.RUN_WITH_LAST_VALS`, `gimpenums.RUN_INTERACTIVE` is used.
  
  * `image` - GIMP image to export layers from.
  
  * `export_settings` - export settings (main settings of the plug-in). This
    class treats them as read-only.
  
  * `overwrite_chooser` - `OverwriteChooser` instance that is invoked if a file
    with the same name already exists.
  
  * `progress_updater` - `ProgressUpdater` instance that indicates the number of
    layers exported. If no progress update is desired, pass None.
  
  * `should_stop` - Can be used to stop the export prematurely. If True,
    the export is stopped after exporting the currently processed layer.
  
  * `exported_layers` - List of layers that were successfully exported. Includes
    layers which were skipped (when files with the same names already exist).
  """
  
  __EXPORT_STATUSES = (
    _NOT_EXPORTED_YET, _EXPORT_SUCCESSFUL, _FORCE_INTERACTIVE,
    _USE_DEFAULT_FILE_EXTENSION
  ) = (0, 1, 2, 3)
  
  def __init__(self, initial_run_mode, image, export_settings, overwrite_chooser, progress_updater):
    self.initial_run_mode = initial_run_mode
    self.image = image
    self.export_settings = export_settings
    self.overwrite_chooser = overwrite_chooser
    self.progress_updater = progress_updater
    
    self.should_stop = False
    self._exported_layers = []
  
  @property
  def exported_layers(self):
    return self._exported_layers
  
  def export_layers(self):
    """
    Export layers as separate images from the specified image.
    """
    
    self._init_attributes()
    self._set_layer_filters()
    
    self._setup()
    try:
      self._export_layers()
    finally:
      self._cleanup()
  
  def _init_attributes(self):
    self.should_stop = False
    
    self._exported_layers = []
    
    self._output_directory = self.export_settings['output_directory'].value
    self._default_file_extension = self.export_settings['file_extension'].value
    self._include_item_path = self.export_settings['layer_groups_as_folders'].value
    
    self._image_copy = None
    self._layer_data = pgitemdata.LayerData(self.image, is_filtered=True)
    self._background_layer_elems = []
    # Layer containing all background layers merged into one. This layer is not
    # inserted into the image, but rather its copies (for each layer to be exported).
    self._background_layer = None
    
    if self.progress_updater is None:
      self.progress_updater = progress.ProgressUpdater(None)
    self.progress_updater.reset()
    
    self._file_extension_properties = self._prefill_file_extension_properties()
    self._default_file_extension = self._default_file_extension.lstrip(".").lower()
    self._current_file_extension = self._default_file_extension
    self._file_export_func = self._get_file_export_func(self._default_file_extension)
    self._current_layer_export_status = self._NOT_EXPORTED_YET
    self._is_current_layer_skipped = False
  
  def _prefill_file_extension_properties(self):
    file_extension_properties = defaultdict(_FileExtensionProperties)
    
    for file_format in pgfileformats.file_formats:
      # This ensures that the file format dialog will be displayed only once per
      # file format if multiple file extensions for the same format are used
      # (e.g. "jpg", "jpeg" or "jpe" for the JPEG format).
      extension_properties = _FileExtensionProperties()
      for file_extension in file_format.file_extensions:
        file_extension_properties[file_extension] = extension_properties
    
    return file_extension_properties
  
  def _set_layer_filters(self):
    """
    Set layer filters according to the main settings.
    
    Create a list of background layers (which are not exported, but are used
    during the layer processing).
    """
    
    self._layer_data.filter.add_subfilter(
      'layer_types', objectfilter.ObjectFilter(objectfilter.ObjectFilter.MATCH_ANY)
    )
    
    self._layer_data.filter['layer_types'].add_rule(LayerFilterRules.is_layer)
    
    if self.export_settings['merge_layer_groups'].value:
      self._layer_data.filter.add_rule(LayerFilterRules.is_top_level)
      self._layer_data.filter['layer_types'].add_rule(LayerFilterRules.is_nonempty_group)
    
    if self.export_settings['ignore_invisible'].value:
      self._layer_data.filter.add_rule(LayerFilterRules.is_path_visible)
    
    if self.export_settings['empty_folders'].value:
      self._layer_data.filter['layer_types'].add_rule(LayerFilterRules.is_empty_group)
    
    if (self.export_settings['square_bracketed_mode'].value ==
        self.export_settings['square_bracketed_mode'].items['normal']):
      for layer_elem in self._layer_data:
        self._remove_square_brackets(layer_elem)
    elif (self.export_settings['square_bracketed_mode'].value ==
          self.export_settings['square_bracketed_mode'].items['background']):
      with self._layer_data.filter.add_rule_temp(LayerFilterRules.is_enclosed_in_square_brackets):
        self._background_layer_elems = list(self._layer_data)
      self._layer_data.filter.add_rule(LayerFilterRules.is_not_enclosed_in_square_brackets)
    elif (self.export_settings['square_bracketed_mode'].value ==
          self.export_settings['square_bracketed_mode'].items['ignore']):
      self._layer_data.filter.add_rule(LayerFilterRules.is_not_enclosed_in_square_brackets)
    elif (self.export_settings['square_bracketed_mode'].value ==
          self.export_settings['square_bracketed_mode'].items['ignore_other']):
      filter_tag = "allow_square_bracketed_only"
      
      with self._layer_data.filter.add_rule_temp(LayerFilterRules.is_enclosed_in_square_brackets):
        for layer_elem in self._layer_data:
          layer_elem.tags.add(filter_tag)
          self._remove_square_brackets(layer_elem)
      
      self._layer_data.filter.add_rule(LayerFilterRules.has_tag, filter_tag)
    
    if (self.export_settings['file_ext_mode'].value ==
        self.export_settings['file_ext_mode'].items['only_matching_file_extension']):
      self._layer_data.filter.add_rule(LayerFilterRules.has_matching_file_extension,
                                       self._default_file_extension)
  
  def _export_layers(self):
    with self._layer_data.filter['layer_types'].remove_rule_temp(
      LayerFilterRules.is_empty_group, raise_if_not_found=False
    ):
      self.progress_updater.num_total_tasks = len(self._layer_data)
    
    pgpath.make_dirs(self._output_directory)
    
    for layer_elem in self._layer_data:
      if self.should_stop:
        raise ExportLayersCancelError("export stopped by user")
      
      if layer_elem.item_type in (layer_elem.ITEM, layer_elem.NONEMPTY_GROUP):
        layer = layer_elem.item
        layer_copy = self._process_layer(layer)
        # Remove the " copy" suffix from the layer name, which is preserved in
        # formats supporting layers (XCF, PSD, ...).
        layer_copy.name = layer.name
        
        layer_elem.validate_name()
        self._strip_file_extension(layer_elem)
        
        self._set_file_extension_and_update_file_export_func(layer_elem)
        self._layer_data.uniquify_name(layer_elem, self._include_item_path,
                                       self._get_uniquifier_position(layer_elem.name))
        self._export_layer(layer_elem, self._image_copy, layer_copy)
        
        if self._current_layer_export_status == self._USE_DEFAULT_FILE_EXTENSION:
          self._set_file_extension_and_update_file_export_func(layer_elem)
          self._layer_data.uniquify_name(layer_elem, self._include_item_path,
                                         self._get_uniquifier_position(layer_elem.name))
          self._export_layer(layer_elem, self._image_copy, layer_copy)
        
        self.progress_updater.update_tasks(1)
        if not self._is_current_layer_skipped:
          # Append the original layer, not the copy, since the copy is going to
          # be destroyed.
          self._exported_layers.append(layer)
          self._file_extension_properties[self._current_file_extension].processed_count += 1
        pdb.gimp_image_remove_layer(self._image_copy, layer_copy)
      elif layer_elem.item_type == layer_elem.EMPTY_GROUP:
        layer_elem.validate_name()
        self._layer_data.uniquify_name(layer_elem, self._include_item_path)
        empty_directory = layer_elem.get_filepath(self._output_directory, self._include_item_path)
        pgpath.make_dirs(empty_directory)
      else:
        raise ValueError("invalid/unsupported item type '{0}' of _ItemDataElement '{1}'"
                         .format(layer_elem.item_type, layer_elem.name))
  
  def _setup(self):
    # Save context just in case. No need for undo groups or undo freeze here.
    pdb.gimp_context_push()
    # Perform subsequent operations on a new image so that the original image
    # and its soon-to-be exported layers are left intact.
    self._image_copy = pgpdb.duplicate(self.image, metadata_only=True)
    
    if constants.DEBUG_IMAGE_PROCESSING:
      self._display_id = pdb.gimp_display_new(self._image_copy)
  
  def _cleanup(self):
    if constants.DEBUG_IMAGE_PROCESSING:
      pdb.gimp_display_delete(self._display_id)
    
    pdb.gimp_image_delete(self._image_copy)
    if self._background_layer is not None:
      pdb.gimp_item_delete(self._background_layer)
    pdb.gimp_context_pop()
  
  def _remove_square_brackets(self, layer_elem):
    if layer_elem.name.startswith("[") and layer_elem.name.endswith("]"):
      layer_elem.name = layer_elem.name[1:-1]
  
  def _process_layer(self, layer):
    background_layer = self._insert_background()
    
    layer_copy = pdb.gimp_layer_new_from_drawable(layer, self._image_copy)
    pdb.gimp_image_insert_layer(self._image_copy, layer_copy, None, 0)
    # This is necessary for file formats which flatten the image (such as JPG).
    pdb.gimp_item_set_visible(layer_copy, True)
    if pdb.gimp_item_is_group(layer_copy):
      layer_copy = pgpdb.merge_layer_group(layer_copy)
    
    if self.export_settings['ignore_layer_modes'].value:
      layer_copy.mode = gimpenums.NORMAL_MODE
    
    self._image_copy.active_layer = layer_copy
    
    layer_copy = self._crop_and_merge(layer_copy, background_layer)
    
    return layer_copy
  
  def _insert_background(self):
    if not self._background_layer_elems:
      return None

    if self._background_layer is None:
      if self.export_settings['use_image_size'].value:
        # Remove background layers outside the image canvas, since they wouldn't
        # be visible anyway and because we need to avoid `RuntimeError`
        # when `pdb.gimp_image_merge_visible_layers` with the `CLIP_TO_IMAGE`
        # option tries to merge layers that are all outside the image canvas.
        self._background_layer_elems = [
          bg_elem for bg_elem in self._background_layer_elems
          if pgpdb.is_layer_inside_image(self._image_copy, bg_elem.item)
        ]
        if not self._background_layer_elems:
          return None
      
      for i, bg_elem in enumerate(self._background_layer_elems):
        bg_layer_copy = pdb.gimp_layer_new_from_drawable(bg_elem.item, self._image_copy)
        pdb.gimp_image_insert_layer(self._image_copy, bg_layer_copy, None, i)
        pdb.gimp_item_set_visible(bg_layer_copy, True)
        if self.export_settings['ignore_layer_modes'].value:
          bg_layer_copy.mode = gimpenums.NORMAL_MODE
        if pdb.gimp_item_is_group(bg_layer_copy):
          bg_layer_copy = pgpdb.merge_layer_group(bg_layer_copy)
      
      if self.export_settings['use_image_size'].value:
        merge_type = gimpenums.CLIP_TO_IMAGE
      else:
        merge_type = gimpenums.EXPAND_AS_NECESSARY
      
      background_layer = pdb.gimp_image_merge_visible_layers(self._image_copy, merge_type)
      self._background_layer = pdb.gimp_layer_copy(background_layer, True)
      return background_layer
    else:
      # Optimization: copy the already created background layer.
      background_layer_copy = pdb.gimp_layer_copy(self._background_layer, True)
      pdb.gimp_image_insert_layer(self._image_copy, background_layer_copy, None, 0)
      return background_layer_copy
  
  def _crop_and_merge(self, layer, background_layer):
    if not self.export_settings['use_image_size'].value:
      pdb.gimp_image_resize_to_layers(self._image_copy)
      if self.export_settings['crop_to_background'].value:
        if background_layer is not None:
          layer = pdb.gimp_image_merge_visible_layers(self._image_copy, gimpenums.CLIP_TO_IMAGE)
        if self.export_settings['autocrop'].value:
          pdb.plug_in_autocrop(self._image_copy, layer)
      else:
        if self.export_settings['autocrop'].value:
          pdb.plug_in_autocrop(self._image_copy, layer)
        if background_layer is not None:
          layer = pdb.gimp_image_merge_visible_layers(self._image_copy, gimpenums.CLIP_TO_IMAGE)
    else:
      if self.export_settings['crop_to_background'].value and background_layer is not None:
        if self.export_settings['autocrop'].value:
          self._image_copy.active_layer = background_layer
          pdb.plug_in_autocrop_layer(self._image_copy, background_layer)
          self._image_copy.active_layer = layer
      else:
        if self.export_settings['autocrop'].value:
          pdb.plug_in_autocrop_layer(self._image_copy, layer)
      
      if background_layer is not None:
        layer = pdb.gimp_image_merge_visible_layers(self._image_copy, gimpenums.CLIP_TO_IMAGE)
      
      pdb.gimp_layer_resize_to_image_size(layer)
    
    return layer
  
  def _strip_file_extension(self, layer_elem):
    if self.export_settings['strip_mode'].value in (
         self.export_settings['strip_mode'].items['identical'],
         self.export_settings['strip_mode'].items['always']):
      file_extension = layer_elem.get_file_extension()
      if file_extension:
        if self.export_settings['strip_mode'].value == self.export_settings['strip_mode'].items['identical']:
          if file_extension == self._default_file_extension:
            layer_elem.set_file_extension(None)
        else:
          layer_elem.set_file_extension(None)
  
  def _set_file_extension_and_update_file_export_func(self, layer_elem):
    if (self.export_settings['file_ext_mode'].value ==
        self.export_settings['file_ext_mode'].items['use_as_file_extensions']):
      
      file_extension = layer_elem.get_file_extension()
      if file_extension and self._file_extension_properties[file_extension].is_valid:
        self._current_file_extension = file_extension
      else:
        layer_elem.set_file_extension(self._default_file_extension)
        self._current_file_extension = self._default_file_extension
      
      self._file_export_func = self._get_file_export_func(self._current_file_extension)
      
    elif (self.export_settings['file_ext_mode'].value ==
          self.export_settings['file_ext_mode'].items['no_special_handling']):
      
      layer_elem.name += "." + self._default_file_extension
  
  def _get_uniquifier_position(self, str_):
    return len(str_) - len("." + self._current_file_extension)
  
  def _get_file_export_func(self, file_extension):
    if file_extension in pgfileformats.file_formats_dict:
      return pgfileformats.file_formats_dict[file_extension].save_procedure_func
    else:
      return pgfileformats.get_default_save_procedure()
  
  def _get_run_mode(self):
    if self._file_extension_properties[self._current_file_extension].is_valid:
      if self._file_extension_properties[self._current_file_extension].processed_count == 0:
        return self.initial_run_mode
      else:
        return gimpenums.RUN_WITH_LAST_VALS
    else:
      return self.initial_run_mode
  
  def _export_layer(self, layer_elem, image, layer):
    output_filename = layer_elem.get_filepath(self._output_directory, self._include_item_path)
    self._is_current_layer_skipped, output_filename = OverwriteHandler.handle(
      output_filename, self.overwrite_chooser, self._get_uniquifier_position(output_filename))
    self.progress_updater.update_text(_("Saving '{0}'").format(output_filename))
    
    if not self._is_current_layer_skipped:
      self._export(image, layer, output_filename)
  
  def _export(self, image, layer, output_filename):
    run_mode = self._get_run_mode()
    pgpath.make_dirs(os.path.dirname(output_filename))
    
    self._export_once(run_mode, image, layer, output_filename)
    
    if self._current_layer_export_status == self._FORCE_INTERACTIVE:
      self._export_once(gimpenums.RUN_INTERACTIVE, image, layer, output_filename)
  
  def _export_once(self, run_mode, image, layer, output_filename):
    self._current_layer_export_status = self._NOT_EXPORTED_YET
    
    try:
      self._file_export_func(run_mode, image, layer, output_filename.encode(),
                             os.path.basename(output_filename).encode())
    except RuntimeError as e:
      # HACK: Since `RuntimeError` could indicate anything, including
      # `pdb.gimp_file_save` failure, this is the only way to intercept the
      # "cancel" operation.
      if "cancelled" in e.message.lower():
        raise ExportLayersCancelError(e.message)
      else:
        if self._current_file_extension != self._default_file_extension:
          self._file_extension_properties[self._current_file_extension].is_valid = False
          self._current_file_extension = self._default_file_extension
          self._current_layer_export_status = self._USE_DEFAULT_FILE_EXTENSION
        else:
          # Try again, this time forcing the interactive mode if the
          # non-interactive mode failed (certain file formats do not allow the
          # non-interactive mode).
          if run_mode in (gimpenums.RUN_WITH_LAST_VALS, gimpenums.RUN_NONINTERACTIVE):
            self._current_layer_export_status = self._FORCE_INTERACTIVE
          else:
            error_message = '"' + self._current_file_extension + '": ' + e.message
            if not e.message.endswith("."):
              error_message += "."
            raise ExportLayersError(error_message)
    else:
      self._current_layer_export_status = self._EXPORT_SUCCESSFUL
