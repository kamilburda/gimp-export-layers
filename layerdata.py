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
This module defines the following classes:
* `LayerData` - an associative container that stores all layers and layer groups
* `_LayerDataElement` - wrapper for gimp.Layer objects containing custom attributes
  derived from the original gimp.Layer attributes
"""

#===============================================================================

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division

str = unicode

#=============================================================================== 

import os

from collections import OrderedDict
from collections import namedtuple

import gimp

from . import libfiles
from . import objectfilter

#===============================================================================

pdb = gimp.pdb

#===============================================================================

class LayerData(object):
  
  """
  This class stores all layers of an image in an ordered dictionary,
  allowing to access the layers via their names and get various custom layer
  attributes derived from the existing layer attributes.
  
  To iterate over layers:
  
    layer_data = LayerData(image, True)
    for elem in layer_data:
      # do stuff
  
  Attributes:
  
  * `image` - GIMP image to get layer data from.
  
  * `is_filtered` - If True, ignore layers that do not match the filter
    (`ObjectFilter`) in this object when iterating.
  
  * `filter` (read-only) - `ObjectFilter` instance where you can add or remove
    filter rules or subfilters to filter layers.
  """
  
  def __init__(self, image, is_filtered=False, filter_match_type=objectfilter.ObjectFilter.MATCH_ALL):
    
    self.image = image
    
    self.is_filtered = is_filtered
    
    # Filters applied to all layers in self._layerdata
    self._filter = objectfilter.ObjectFilter(filter_match_type)
    
    # Contains all layers (including layer groups) in the layer tree.
    # key: `_LayerDataElement.orig_layer_name` (derived from `gimp.Layer.name`, which is unique)
    # value: `_LayerDataElement` object
    self._layerdata = OrderedDict()
    
    # key `_LayerDataElement` object (parent) or None (root of the layer tree)
    # value: set of `_LayerDataElement` objects
    self._uniquified_layerdata = {}
    
    self._fill_layer_data()
  
  @property
  def filter(self):
    return self._filter
  
  def __getitem__(self, layer_name):
    return self._layerdata[layer_name]
  
  def __contains__(self, layer_name):
    return layer_name in self._layerdata
  
  def __len__(self):
    return len([layerdata_elem for layerdata_elem in self])
  
  def __iter__(self):
    """
    If not filtered, iterate over all layers. If filtered, iterate only over
    layers that match the filter in this object.
    
    Yields:
    
    * `layerdata_elem` - The current `_LayerDataElement` object.
    """
    
    if not self.is_filtered:
      for layerdata_elem in self._layerdata.values():
        yield layerdata_elem
    else:
      for layerdata_elem in self._layerdata.values():
        if self._filter.is_match(layerdata_elem):
          yield layerdata_elem
  
  def _items(self):
    """
    Yield current (`gimp.Layer.name`, `_LayerDataElement` object) tuple.
    """
    
    if not self.is_filtered:
      for name, layerdata_elem in self._layerdata.items():
        yield name, layerdata_elem
    else:
      for name, layerdata_elem in self._layerdata.items():
        if self._filter.is_match(layerdata_elem):
          yield name, layerdata_elem
  
  def uniquify_layer_name(self, layerdata_elem, include_layer_path=True, place_before_file_extension=False):
    """
    Make the `layer_name` attribute in the specified `_LayerDataElement` object
    unique among all other, already uniquified `_LayerDataElement` objects.
    
    To achieve uniquification, a string in the form of " (<number>)" is inserted
    at the end of the layer names.
    
    Parameters:
    
    * `layerdata_elem` - `_LayerDataElement` object whose `layer_name` attribute
      will be uniquified.
    
    * `include_layer_path` - If True, take the layer path into account when
      uniquifying.
      
    * `place_before_file_extension` - If True, uniquify the layer name such that
      the " (<number>)" string that makes the name unique is placed before the
      file extension if the layer name has one. This parameter does not apply to
      the layer path components (parents).
    """
    
    if include_layer_path:
      for elem in layerdata_elem.parents + [layerdata_elem]:
        parent = elem.parent
        
        if parent not in self._uniquified_layerdata:
          self._uniquified_layerdata[parent] = set()
        
        if elem not in self._uniquified_layerdata[parent]:
          layer_names = set([elem_.layer_name for elem_ in self._uniquified_layerdata[parent]])
          if elem.layer_name not in layer_names:
            self._uniquified_layerdata[parent].add(elem)
          else:
            # Don't apply `place_before_file_extension` to any parents.
            if elem == layerdata_elem:
              place_before_file_ext = place_before_file_extension
            else:
              place_before_file_ext = False
            
            elem.layer_name = libfiles.uniquify_string(
              elem.layer_name, layer_names, place_before_file_ext
            )
            self._uniquified_layerdata[parent].add(elem)
    else:
      # Use None as the root of the layer tree.
      parent = None
      
      if parent not in self._uniquified_layerdata:
        self._uniquified_layerdata[parent] = set()
      
      layerdata_elem.layer_name = libfiles.uniquify_string(
        layerdata_elem.layer_name, self._uniquified_layerdata[parent],
        place_before_file_extension
      )
      self._uniquified_layerdata[parent].add(layerdata_elem.layer_name)
  
  def _fill_layer_data(self):
    """
    Fill the _layerdata dictionary, containing
    <gimp.Layer.name, _LayerDataElement> pairs.
    """
    
    _LayerTreeNode = namedtuple('_LayerTreeNode', ['layers', 'parents'])
    layer_tree = [_LayerTreeNode(self.image.layers, [])]
    
    while layer_tree:
      node = layer_tree.pop(0)
      
      index = 0
      for layer in node.layers:
        parents = list(node.parents)
        layerdata_elem = _LayerDataElement(layer, parents)
        
        if pdb.gimp_item_is_group(layer):
          layer_tree.insert(index, _LayerTreeNode(layer.layers, parents + [layerdata_elem]))
          index += 1
        
        self._layerdata[layerdata_elem.orig_layer_name] = layerdata_elem


class _LayerDataElement(object):
  
  """
  This class wraps a `gimp.Layer` object and defines custom layer attributes.
  
  Note that the attributes will not be up to date if changes were made to the
  original `gimp.Layer` objects.
  
  Attributes:
  
  * `layer` (read-only) - `gimp.Layer` object.
  
  * `parents` (read-only) - List of `_LayerDataElement` parents for this layer,
    sorted from the topmost parent to the bottommost (immediate) parent.
  
  * `level` (read-only) - Integer indicating which level in the layer tree is
    the layer positioned at. 0 means the layer is at the top level. The higher
    the level, the deeper the layer is in the layer tree.
  
  * `parent` (read-only) - Immediate `_LayerDataElement` parent of this object.
    If this object has no parent, return None.
  
  * `layer_type` (read-only) - Layer type - one of the following:
      * `LAYER` - normal layer,
      * `NONEMPTY_GROUP` - non-empty layer group, contains children,
      * `EMPTY_GROUP` - empty layer group, contains no children.
  
  * `layer_name` - Layer name as a `unicode` string, initially equal to
    the `orig_layer_name` attribute. Modify this attribute instead of
    `gimp.Layer.name` to avoid modifying the original layer.
  
  * `orig_layer_name` (read-only) - original `gimp.Layer.name` as a `unicode`
    string.
  
  * `path_visible` (read-only) - Visibility of all layer's parents and this
    layer. If all layers are visible, `path_visible` is True. If at least one
    of these layers is invisible, `path_visible` is False.
  
  * `file_extension` (read-only) - File extension of the layer name. If the
    layer has no extension, empty string is returned.
  """
  
  __LAYER_TYPES = LAYER, NONEMPTY_GROUP, EMPTY_GROUP = (0, 1, 2)
  
  def __init__(self, layer, parents=None):
    if layer is None:
      raise TypeError("layer cannot be None")
    
    self._layer = layer
    self._parents = parents if parents is not None else []
    self._level = len(self._parents)
    
    if self._parents:
      self._parent = self._parents[-1]
    else:
      self._parent = None
    
    if pdb.gimp_item_is_group(self._layer):
      if self._layer.children:
        self._layer_type = self.NONEMPTY_GROUP
      else:
        self._layer_type = self.EMPTY_GROUP
    else:
      self._layer_type = self.LAYER
    
    self.layer_name = self._layer.name.decode()
    self._orig_layer_name = self.layer_name
    
    self._path_visible = self._get_layer_visibility()
  
  @property
  def layer(self):
    return self._layer
  
  @property
  def parents(self):
    return self._parents
  
  @property
  def level(self):
    return self._level
  
  @property
  def parent(self):
    return self._parent
  
  @property
  def layer_type(self):
    return self._layer_type
  
  @property
  def orig_layer_name(self):
    return self._orig_layer_name
  
  @property
  def path_visible(self):
    return self._path_visible
  
  def get_file_extension(self):
    """
    Get file extension from the `layer_name` attribute.
    
    If `layer_name` has no file extension, return an empty string.
    """
    
    return libfiles.get_file_extension(self.layer_name)
  
  def set_file_extension(self, file_extension):
    """
    Set file extension in the `layer_name` attribute.
    
    To remove the file extension from `layer_name`, pass an empty string or None.
    """
    
    root = os.path.splitext(self.layer_name)[0]
    
    if file_extension:
      self.layer_name = '.'.join((root, file_extension))
    else:
      self.layer_name = root
  
  def get_filepath(self, directory, include_layer_path=True):
    """
    If `include_layer_path` is True, create file path in the following format:
    <directory>/<layer path components>/<layer name>
    
    If `include_layer_path` is False, create file path in the following format:
    <directory>/<layer name>
    
    If directory is not an absolute path or is None, prepend the current working
    directory.
    
    Layer path components consist of parents' layer names, starting with the
    topmost parent.
    """
    
    if directory is None:
      directory = ""
    
    path = os.path.abspath(directory)
    
    if include_layer_path:
      path_components = self.get_path_components()
      if path_components:
        path = os.path.join(path, os.path.join(*path_components))
    
    path = os.path.join(path, self.layer_name)
    
    return path
  
  def get_path_components(self):
    """
    Return layer names of all parents as path components.
    """
    
    return [parent.layer_name for parent in self.parents]
  
  def validate_name(self):
    """
    Validate the `layer_name` attribute of this object and all of its parents.
    """
    
    self.layer_name = libfiles.FilenameValidator.validate(self.layer_name)
    for parent in self._parents:
      parent.layer_name = libfiles.FilenameValidator.validate(parent.layer_name)
  
  def _get_layer_visibility(self):
    """
    If the layer and all of its parents are visible, return True,
    otherwise return False.
    """
    
    path_visible = True
    if not self._layer.visible:
      path_visible = False
    else:
      for parent in self._parents:
        if not parent.layer.visible:
          path_visible = False
          break
    return path_visible
