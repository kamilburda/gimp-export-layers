#-------------------------------------------------------------------------------
#
# This file is part of pygimplib.
#
# Copyright (C) 2014, 2015 khalim19 <khalim19@gmail.com>
#
# pygimplib is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pygimplib is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pygimplib.  If not, see <http://www.gnu.org/licenses/>.
#
#-------------------------------------------------------------------------------

"""
This module defines functions dealing with GIMP objects (images, layers, etc.)
not defined in the GIMP procedural database (PDB) or the GIMP Python API.
"""

#===============================================================================

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division

str = unicode

#===============================================================================

import os

from contextlib import contextmanager

import gimp
import gimpenums

#===============================================================================

pdb = gimp.pdb

#===============================================================================


@contextmanager
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
    raise TypeError("\"{0}\": not a layer group".format(layer_group.name))
  
  image = layer_group.image
  
  with undo_group(image):
    orig_parent_and_pos = ()
    if layer_group.parent is not None:
      # Nested layer group
      orig_parent_and_pos = (layer_group.parent, pdb.gimp_image_get_item_position(image, layer_group))
      pdb.gimp_image_reorder_item(image, layer_group, None, 0)
    
    orig_layer_visibility = [layer.visible for layer in image.layers]
    
    for layer in image.layers:
      layer.visible = False
    layer_group.visible = True
    
    merged_layer_group = pdb.gimp_image_merge_visible_layers(image, gimpenums.EXPAND_AS_NECESSARY)
    
    for layer, orig_visible in zip(image.layers, orig_layer_visibility):
      layer.visible = orig_visible
  
    if orig_parent_and_pos:
      pdb.gimp_image_reorder_item(image, merged_layer_group, orig_parent_and_pos[0], orig_parent_and_pos[1])
  
  return merged_layer_group


def is_layer_inside_image(image, layer):
  """
  Return True if the layer is inside the image canvas (partially or completely).
  Return False if the layer is completely outside the image canvas.
  """
  
  return ((-image.width < layer.offsets[0] < image.width) and
          (-image.height < layer.offsets[1] < image.height))


#-------------------------------------------------------------------------------


def duplicate(image, metadata_only=False):
  """
  Duplicate the specified image.
  
  If `metadata_only` is True, copy image metadata only, do not copy layers,
  channels or paths.
  """
  
  if not metadata_only:
    new_image = pdb.gimp_image_duplicate(image)
  else:
    new_image = pdb.gimp_image_new(image.width, image.height, image.base_type)
    
    pdb.gimp_image_set_resolution(new_image, *pdb.gimp_image_get_resolution(image))
    
    if image.base_type == gimpenums.INDEXED:
      pdb.gimp_image_set_colormap(new_image, *pdb.gimp_image_get_colormap(image))
    
    # Copy image parasites
    unused_, parasite_names = pdb.gimp_image_get_parasite_list(image)
    for name in parasite_names:
      parasite = image.parasite_find(name)
      # `pdb.gimp_image_parasite_attach` fails for some reason - use
      # `gimp.Image.parasite_attach` instead.
      new_image.parasite_attach(gimp.Parasite(parasite.name, parasite.flags, parasite.data))
  
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


#-------------------------------------------------------------------------------


def load_layers(layer_filenames, image=None, strip_file_extension=False):
  """
  Load multiple layers to one image. Return the image.
  
  If `image` is None, create a new image. If `image` is not None, load the
  layers to the specified image.
  
  If `strip_file_extension` is True, remove the file extension from the names of
  the loaded layers (GIMP automatically names the layers by their basenames).
  """
  
  create_new_image = image is None
  if create_new_image:
    image = gimp.Image(1, 1)
  
  for filename in layer_filenames:
    layer = pdb.gimp_file_load_layer(image, filename)
    pdb.gimp_image_insert_layer(image, layer, None, len(image.layers))
    if strip_file_extension:
      layer.name = os.path.splitext(layer.name)[0]
  
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


#-------------------------------------------------------------------------------


def compare_layers(layers, compare_alpha_channels=True, compare_has_alpha=False,
                   apply_layer_attributes=True, apply_layer_masks=True):
  """
  Return True if all layers are identical (i.e. have the same contents), False
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
  
  if (not all(layers[0].width == layer.width for layer in layers[1:])
      or not all(layers[0].height == layer.height for layer in layers[1:])):
    return False
  
  if compare_has_alpha and not all(layers[0].type == layer.type for layer in layers[1:]):
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
    
    identical = identical and _is_identical(layer_group)
  
  pdb.gimp_image_delete(image)
  
  return identical

