#-------------------------------------------------------------------------------
#
# This file is part of pylibgimpplugin.
#
# Copyright (C) 2014 khalim19 <khalim19@gmail.com>
#
# pylibgimpplugin is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pylibgimpplugin is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pylibgimpplugin.  If not, see <http://www.gnu.org/licenses/>.
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

from contextlib import contextmanager

import gimp
import gimpenums

#===============================================================================

pdb = gimp.pdb

#===============================================================================
# Functions
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


def merge_layer_group(image, layer_group):
  """
  Merge layers in the specified layer group belonging to the specified image
  into one layer.
  
  This function can handle both top-level and nested layer groups.
  """
  
  if not pdb.gimp_item_is_group(layer_group):
    raise TypeError("not a layer group")
  
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


def duplicate(image, remove_items=False):
  """
  Duplicate the specified image.
  
  If `remove_items` is true, remove all items (layers, channels, paths)
  from the duplicated image.
  """
  
  image_new = pdb.gimp_image_duplicate(image)
  if remove_items:
    remove_all_items(image_new)
  
  return image_new
