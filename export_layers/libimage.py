#-------------------------------------------------------------------------------
#
# This file is part of Export Layers.
#
# Copyright (C) 2013, 2014 khalim19 <khalim19@gmail.com>
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
* contains functions dealing with GIMP objects - images, layers, etc.
"""

#=============================================================================== 

from contextlib import contextmanager

import gimp
import gimpenums

#===============================================================================

pdb = gimp.pdb

#===============================================================================

@contextmanager
def undo_group(image):
  pdb.gimp_image_undo_group_start(image)
  try:
    yield
  finally:
    pdb.gimp_image_undo_group_end(image)


def merge_layer_group(image, layer_group):
  """
  Merge the specified layer group into a layer.
  """
  
  if not pdb.gimp_item_is_group(layer_group):
    raise TypeError("layer is not a layer group")
  
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
