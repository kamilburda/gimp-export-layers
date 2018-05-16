# -*- coding: utf-8 -*-
#
# Copyright (C) 2014-2018 khalim19
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
This module provides additional functions dealing with GIMP objects (images,
layers, etc.) not defined in the GIMP procedural database (PDB) or the GIMP
Python API.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import os
import contextlib

import gimp
from gimp import pdb
import gimpenums

from . import pgconstants
from . import pginvocation
from . import pgutils

#===============================================================================


@contextlib.contextmanager
def undo_group(image):
  """
  Wrap the enclosing block of code into one GIMP undo group for the specified
  image.
  
  Use this function as a context manager:
    
    with undo_group(image):
      # do stuff
  """
  
  pdb.gimp_image_undo_group_start(image)
  try:
    yield
  finally:
    pdb.gimp_image_undo_group_end(image)


def merge_layer_group(layer_group):
  """
  Merge layers in the specified layer group belonging to the specified image
  into one layer.
  
  This function can handle both top-level and nested layer groups.
  """
  
  if not pdb.gimp_item_is_group(layer_group):
    raise TypeError("'{0}': not a layer group".format(layer_group.name))
  
  image = layer_group.image
  
  with undo_group(image):
    orig_parent_and_pos = ()
    if layer_group.parent is not None:
      # Nested layer group
      orig_parent_and_pos = (
        layer_group.parent, pdb.gimp_image_get_item_position(image, layer_group))
      pdb.gimp_image_reorder_item(image, layer_group, None, 0)
    
    orig_layer_visibility = [layer.visible for layer in image.layers]
    
    for layer in image.layers:
      layer.visible = False
    layer_group.visible = True
    
    merged_layer_group = pdb.gimp_image_merge_visible_layers(
      image, gimpenums.EXPAND_AS_NECESSARY)
    
    for layer, orig_visible in zip(image.layers, orig_layer_visibility):
      layer.visible = orig_visible
  
    if orig_parent_and_pos:
      pdb.gimp_image_reorder_item(
        image, merged_layer_group, orig_parent_and_pos[0], orig_parent_and_pos[1])
  
  return merged_layer_group


def is_layer_inside_image(image, layer):
  """
  Return True if the layer is inside the image canvas (partially or completely).
  Return False if the layer is completely outside the image canvas.
  """
  
  return (
    -image.width < layer.offsets[0] < image.width
    and -image.height < layer.offsets[1] < image.height)


#===============================================================================


def create_image_from_metadata(image_to_copy_metadata_from):
  """
  Create a new image with metadata (dimensions, base type, parasites, etc.)
  copied from `image_to_copy_metadata_from`.
  
  Layers, channels or paths are not copied. For a full image copy, use
  `pdb.gimp_image_duplicate`.
  """
  
  image = image_to_copy_metadata_from
  
  new_image = pdb.gimp_image_new(image.width, image.height, image.base_type)
  
  pdb.gimp_image_set_resolution(new_image, *pdb.gimp_image_get_resolution(image))
  pdb.gimp_image_set_unit(new_image, pdb.gimp_image_get_unit(image))
  
  if image.base_type == gimpenums.INDEXED:
    pdb.gimp_image_set_colormap(new_image, *pdb.gimp_image_get_colormap(image))
  
  # Copy image parasites
  unused_, parasite_names = pdb.gimp_image_get_parasite_list(image)
  for name in parasite_names:
    parasite = image.parasite_find(name)
    # `pdb.gimp_image_parasite_attach` fails for some reason - use
    # `gimp.Image.parasite_attach` instead.
    new_image.parasite_attach(
      gimp.Parasite(parasite.name, parasite.flags, parasite.data))
  
  return new_image


def remove_all_layers(image):
  """
  Remove all layers from the specified image.
  """
  
  for layer in image.layers:
    pdb.gimp_image_remove_layer(image, layer)


def remove_all_channels(image):
  """
  Remove all layers from the specified image.
  """
  
  for channel in image.channels:
    pdb.gimp_image_remove_channel(image, channel)


def remove_all_paths(image):
  """
  Remove all paths (vectors) from the specified image.
  """
  
  for path in image.vectors:
    pdb.gimp_image_remove_vectors(image, path)


def remove_all_items(image):
  """
  Remove all items (layers, channels, paths) from the specified image.
  """
  
  remove_all_layers(image)
  remove_all_channels(image)
  remove_all_paths(image)


#===============================================================================


def load_layer(filepath, image, strip_file_extension=False, layer_to_load_index=0):
  """
  Load an image as a layer given its file path to an existing `image`. Return
  the layer.
  
  The layer is loaded at the end of the image.
  
  Layers names are basenames of the corresponding files. If
  `strip_file_extension` is True, remove the file extension from layer names.
  
  If the file contains multiple layers, specify the index of the desired layer
  to load. Only top-level layers are supported (i.e. not layers inside layer
  groups). If the index is greater than the number of layers in the loaded
  image or is negative, load and return the last layer.
  """
  
  loaded_image = pdb.gimp_file_load(filepath, os.path.basename(filepath))
  
  if layer_to_load_index >= len(image.layers) or layer_to_load_index < 0:
    layer_to_load_index = -1
  
  layer = pdb.gimp_layer_new_from_drawable(
    loaded_image.layers[layer_to_load_index], image)
  layer.name = os.path.basename(filepath)
  if strip_file_extension:
    layer.name = os.path.splitext(layer.name)[0]
  
  pdb.gimp_image_insert_layer(image, layer, None, len(image.layers))
  
  pdb.gimp_image_delete(loaded_image)
  
  return layer


def load_layers(filepaths, image=None, strip_file_extension=False):
  """
  Load multiple layers to one image. Return the image.
  
  The layers are loaded at the end of the image.
  
  If `image` is None, create a new image. If `image` is not None, load the
  layers to the specified image.
  
  Layers names are basenames of the corresponding files. If
  `strip_file_extension` is True, remove the file extension from layer names.
  """
  
  create_new_image = image is None
  if create_new_image:
    image = gimp.Image(1, 1)
  
  for filepath in filepaths:
    load_layer(filepath, image, strip_file_extension)
  
  if create_new_image:
    pdb.gimp_image_resize_to_layers(image)
  
  return image


def copy_and_paste_layer(layer, image, parent=None, position=0):
  """
  Copy the specified layer into the specified image, parent layer group and
  position in the group. Return the copied layer.
  
  If `parent` is None, insert the layer in the main stack (outside of any layer
  group).
  """
  
  layer_copy = pdb.gimp_layer_new_from_drawable(layer, image)
  pdb.gimp_image_insert_layer(image, layer_copy, parent, position)
  
  return layer_copy


#===============================================================================


def compare_layers(
      layers, compare_alpha_channels=True, compare_has_alpha=False,
      apply_layer_attributes=True, apply_layer_masks=True):
  """
  Return True if the contents of all specified layers are identical, False
  otherwise. Layer groups are also supported.
  
  The default values of the optional parameters correspond to how the layers are
  displayed in the image canvas.
  
  If `compare_alpha_channels` is True, perform comparison of alpha channels.
  
  If `compare_has_alpha` is True, compare the presence of alpha channels in all
  layers - if some layers have alpha channels and others don't, do not perform
  full comparison and return False.
  
  If `apply_layer_attributes` is True, take the layer attributes (opacity, mode)
  into consideration when comparing, otherwise ignore them.
  
  If `apply_layer_masks` is True, apply layer masks if they are enabled. If the
  masks are disabled or `apply_layer_masks` is False, layer masks are ignored.
  """
  
  def _copy_layers(image, layers, parent=None, position=0):
    layer_group = pdb.gimp_layer_group_new(image)
    pdb.gimp_image_insert_layer(image, layer_group, parent, position)
    
    for layer in layers:
      copy_and_paste_layer(layer, image, parent=layer_group)
    
    for layer in layer_group.children:
      layer.visible = True
    
    return layer_group
  
  def _process_layers(image, layer_group, apply_layer_attributes, apply_layer_masks):
    for layer in layer_group.children:
      if pdb.gimp_item_is_group(layer):
        layer = merge_layer_group(layer)
      else:
        if layer.opacity != 100.0 or layer.mode != gimpenums.NORMAL_MODE:
          if apply_layer_attributes:
            layer = _apply_layer_attributes(image, layer, layer_group)
          else:
            layer.opacity = 100.0
            layer.mode = gimpenums.NORMAL_MODE
        
        if layer.mask is not None:
          if apply_layer_masks and pdb.gimp_layer_get_apply_mask(layer):
            pdb.gimp_layer_remove_mask(layer, gimpenums.MASK_APPLY)
          else:
            pdb.gimp_layer_remove_mask(layer, gimpenums.MASK_DISCARD)
  
  def _is_identical(layer_group):
    layer_group.children[0].mode = gimpenums.DIFFERENCE_MODE
    
    for layer in layer_group.children[1:]:
      layer.visible = False
    
    for layer in layer_group.children[1:]:
      layer.visible = True
      
      histogram_data = pdb.gimp_histogram(layer_group, gimpenums.HISTOGRAM_VALUE, 1, 255)
      percentile = histogram_data[5]
      identical = percentile == 0.0
      
      if not identical:
        return False
      
      layer.visible = False
    
    return True
  
  def _set_mask_to_layer(layer):
    pdb.gimp_edit_copy(layer.mask)
    floating_sel = pdb.gimp_edit_paste(layer, True)
    pdb.gimp_floating_sel_anchor(floating_sel)
    pdb.gimp_layer_remove_mask(layer, gimpenums.MASK_DISCARD)
  
  def _apply_layer_attributes(image, layer, parent_group):
    temp_group = pdb.gimp_layer_group_new(image)
    pdb.gimp_image_insert_layer(image, temp_group, parent_group, 0)
    pdb.gimp_image_reorder_item(image, layer, temp_group, 0)
    layer = merge_layer_group(temp_group)
    
    return layer
  
  all_layers_have_same_size = (
    all(layers[0].width == layer.width for layer in layers[1:])
    and all(layers[0].height == layer.height for layer in layers[1:]))
  if not all_layers_have_same_size:
    return False
  
  all_layers_are_same_image_type = (
    all(layers[0].type == layer.type for layer in layers[1:]))
  if compare_has_alpha and not all_layers_are_same_image_type:
    return False
  
  image = gimp.Image(1, 1, gimpenums.RGB)
  layer_group = _copy_layers(image, layers)
  pdb.gimp_image_resize_to_layers(image)
  _process_layers(image, layer_group, apply_layer_attributes, apply_layer_masks)
  
  has_alpha = False
  for layer in layer_group.children:
    if pdb.gimp_drawable_has_alpha(layer):
      has_alpha = True
      # Extract alpha channel to the layer mask (to compare alpha channels).
      mask = pdb.gimp_layer_create_mask(layer, gimpenums.ADD_ALPHA_MASK)
      pdb.gimp_layer_add_mask(layer, mask)
      pdb.gimp_layer_set_apply_mask(layer, False)
      # Remove alpha channel
      pdb.gimp_layer_flatten(layer)
  
  identical = _is_identical(layer_group)
  
  if identical and compare_alpha_channels and has_alpha:
    for layer in layer_group.children:
      if layer.mask is not None:
        _set_mask_to_layer(layer)
      else:
        pdb.gimp_drawable_fill(layer, gimpenums.WHITE_FILL)
    
    identical = _is_identical(layer_group)
  
  pdb.gimp_image_delete(image)
  
  return identical


#===============================================================================


@contextlib.contextmanager
def redirect_messages(message_handler=gimpenums.ERROR_CONSOLE):
  """
  Temporarily redirect GIMP messages to the specified message handler.
  
  Use this function as a context manager:
    
    with redirect_messages():
      # do stuff
  """
  
  orig_message_handler = pdb.gimp_message_get_handler()
  pdb.gimp_message_set_handler(message_handler)
  
  try:
    yield
  finally:
    pdb.gimp_message_set_handler(orig_message_handler)


class GimpMessageFile(object):
  
  """
  This class provides a file-like way to write output as GIMP messages.
  
  You can use this class to redirect output or error output to the GIMP console.
  
  Parameters:
  
  * `message_handler` - Handler to which messages are output. Possible values
    are the same as for the `pdb.gimp_message_get_handler()` procedure.
  
  * `message_prefix` - If not None, prepend this string to each message.
  
  * `message_delay_milliseconds` - Delay in milliseconds before displaying the
    output. This is useful to aggregate multiple messages into one in order to
    avoid printing an excessive number of message headers.
  """
  
  def __init__(
        self, message_handler=gimpenums.ERROR_CONSOLE, message_prefix=None,
        message_delay_milliseconds=0):
    self._message_handler = message_handler
    self._message_prefix = str(message_prefix) if message_prefix is not None else ""
    self._message_delay_milliseconds = message_delay_milliseconds
    
    self._buffer_size = 4096
    
    self._orig_message_handler = None
    
    self._message_buffer = self._message_prefix
  
  def write(self, data):
    # Message handler can't be set upon instantiation, because the PDB may not
    # have been initialized yet.
    self._orig_message_handler = pdb.gimp_message_get_handler()
    pdb.gimp_message_set_handler(self._message_handler)
    
    self._write(data)
    
    self.write = self._write
  
  def _write(self, data):
    if len(self._message_buffer) < self._buffer_size:
      self._message_buffer += data
      pginvocation.timeout_add_strict(self._message_delay_milliseconds, self.flush)
    else:
      pginvocation.timeout_remove_strict(self.flush)
      self.flush()
  
  def flush(self):
    gimp.message(self._message_buffer.encode(pgconstants.GIMP_CHARACTER_ENCODING))
    self._message_buffer = self._message_prefix
  
  def close(self):
    if self._orig_message_handler is not None:
      pdb.gimp_message_set_handler(self._orig_message_handler)


#===============================================================================


_dummy_progress_callback = None


def suppress_gimp_progress():
  """
  Prevent the default progress bar in GIMP from updating by installing a dummy
  progress callback. Subsequent calls to this function without a matching call
  to `unsuppress_gimp_progress` have no effect.
  """
  
  global _dummy_progress_callback
  
  if _dummy_progress_callback:
    return
  
  _dummy_progress_callback = gimp.progress_install(
    pgutils.empty_func, pgutils.empty_func, pgutils.empty_func, pgutils.empty_func)


def unsuppress_gimp_progress():
  """
  Undo suppression of the default progress bar in GIMP caused by calling
  `suppress_gimp_progress`. Calling this function before calling
  `suppress_gimp_progress` has no effect.
  """
  
  global _dummy_progress_callback
  
  if not _dummy_progress_callback:
    return
  
  gimp.progress_uninstall(_dummy_progress_callback)
  _dummy_progress_callback = None
