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
#from __future__ import unicode_literals
from __future__ import division

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
  
  def __init__(self, image, is_filtered=False):
    
    self.image = image
    
    self.is_filtered = is_filtered
    
    # Filters applied to all layers in self._layerdata
    self._filter = objectfilter.ObjectFilter()
    
    # Contains all layers (including layer groups) in the layer tree.
    # key: `gimp.Layer.name` (`gimp.Layer` names are unique)
    # value: `_LayerDataElement` object
    self._layerdata = OrderedDict()
    
    self._cached_layerdata = None
    
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
      if self._cached_layerdata is None:
        layerdata = self._layerdata
      else:
        layerdata = self._cached_layerdata
      
      for layerdata_elem in layerdata.values():
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
  
  def cache_layers(self):
    """
    Cache layers that match the filter in this class. If you remove filters
    after calling this method and then iterate, this class will iterate over
    the cached layers only.
    
    To clear the layer cache, simply call `clear_cache()`.
    
    Calling `cache_layers()` again renews the layer cache.
    """
    
    self._cached_layerdata = OrderedDict(self._items())
  
  def clear_cache(self):
    """
    Clear the layer cache after `cache_layers()` was called.
    
    Nothing happens if the cache is empty (since there is nothing to clear).
    """
    
    if self._cached_layerdata is not None:
      self._cached_layerdata = None
  
  def get_file_extension_properties(self, default_file_extension):
    
    """
    Get data about file extensions in layer names for each file extension.
    
    For layers with no file extension, fill the data for `default_file_extension`.
    
    Parameters:
    
    * `default_file_extension` - Default file format to use for layers with no
      file extension.
    
    Returns:
    
      Dict of <file extension, `LayerFileExtensionProperties` object> pairs.
      `LayerFileExtensionProperties` objects contain the following attributes:
      
      * `count` - Number of layers having the file extension
      
      * `processed_count` - Number of layers processed so far. Initially set to 0.
        Can be used by other functions when processing layers.
      
      * `is_valid` - If True, file extension is considered valid.
        If False, it is considered invalid. Initially set to True.
        Can also be used by other functions when processing layers.
    """
    
    class LayerFileExtensionProperties(object):
      def __init__(self):
        self.count = 0
        self.processed_count = 0
        self.is_valid = True
    
    layer_file_ext_properties = {}
    
    for layerdata_elem in self:
      file_format = layerdata_elem.file_extension
      if not file_format:
        file_format = default_file_extension
      
      if file_format not in layer_file_ext_properties:
        layer_file_ext_properties[file_format] = LayerFileExtensionProperties()
      layer_file_ext_properties[file_format].count += 1
    
    if default_file_extension not in layer_file_ext_properties:
      layer_file_ext_properties[default_file_extension] = LayerFileExtensionProperties()
    
    return layer_file_ext_properties
  
  def uniquify_layer_names(self, include_layer_path=True, place_before_file_extension=False):
    """
    Make the names of layers and layer groups unique to make sure that
    all filenames or directory names on the same directory level will be unique.
    
    This is necessary in case the layer names in the `_LayerDataElement` objects
    had their characters invalid in filenames removed, which may result in
    multiple layers or layer groups having the same name.
    
    To achieve uniquification, a string in the form of " (<number>)" is inserted
    at the end of the layer names.
    
    Parameters:
    
    * `include_layer_path` - If True, take the layer path into account when
      uniquifying.
      
    * `place_before_file_extension` - If True, uniquify such that the
      " (<number>)" string that makes the names unique is placed before the file
      extension if the layer name has one.
    """
    
    def _uniquify(layerdata):
      layer_paths = set()
      for layerdata_elem in layerdata:
        layerdata_elem.layer_name = libfiles.uniquify_string(
          layerdata_elem.layer_name, layer_paths, place_before_file_extension=place_before_file_extension
        )
        layerdata_elem.path_components = layerdata_elem.update_path_components()
        layer_paths.add(layerdata_elem.layer_name)
    
    if include_layer_path:
      _LayerTreeNode = namedtuple('_LayerTreeNode', ['layers', 'parents'])
      layer_tree = [_LayerTreeNode(self.image.layers, [])]
      
      while layer_tree:
        node = layer_tree.pop(0)
        
        index = 0
        layerdata = []
        for layer in node.layers:
          parents = list(node.parents)
          layerdata_elem = _LayerDataElement(layer, parents)
          
          if pdb.gimp_item_is_group(layer):
            layer_tree.insert(index, _LayerTreeNode(layer.layers, [layerdata_elem] + parents))
            index += 1
          
          if not self.is_filtered or self._filter.is_match(layerdata_elem):
            layerdata.append(self._layerdata[layer.name])
        
        _uniquify(layerdata)
    else:
      def is_layer_or_empty_group(layerdata_elem):
        return not layerdata_elem.is_group or layerdata_elem.is_empty
      
      # Non-empty layer groups must be filtered out since they are
      # not exported, and would interfere with the uniquification of
      # layers and empty layer groups.
      
      orig_filter = self._filter
      orig_is_filtered = self.is_filtered
      if not orig_is_filtered:
        self._filter = objectfilter.ObjectFilter()
        self.is_filtered = True
      
      self._filter.add_rule(is_layer_or_empty_group)
      _uniquify(self)
      self._filter.remove_rule(is_layer_or_empty_group)
      
      if not orig_is_filtered:
        self._filter = orig_filter
        self.is_filtered = False
  
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
          layer_tree.insert(index, _LayerTreeNode(layer.layers, [layerdata_elem] + parents))
          index += 1
          
        self._layerdata[layer.name] = layerdata_elem


class _LayerDataElement(object):
  
  """
  This class wraps a `gimp.Layer` object and defines custom layer attributes.
  
  Note that the attributes will not be up to date if changes were made to the
  original `gimp.Layer` objects.
  
  Attributes:
  
  * `layer` - `gimp.Layer` object
  
  * `parents` - List of `_LayerDataElement` parents for this layer, sorted from the
    bottommost (immediate) parent to the topmost parent.
  
  * `level` - Integer indicating at which level in the layer tree is the layer
    positioned. 0 means the layer is at the top level.
  
  * `layer_name` - Layer name. Modify this attribute instead of `gimp.Layer.name`
    to avoid modifying the original layer. While `gimp.Layer.name` are bytes
    encoded in UTF-8, `layer_name` is of type `unicode`.
  
  * `is_group` - If True, layer is a layer group (`gimp.GroupLayer`). If False,
    layer is `gimp.Layer`.
  
  * `is_empty` - If True, layer is an empty layer group.
  
  * `path_components` - List of all parents' names for this layer, sorted from the
    topmost to the bottommost parent. This attribute can be used in creating
    the filename of the layer if layer groups are treated as directories.
  
  * `path_visible` - Visibility of all layer's parents and this layer. If all layers
    are visible, `path_visible` is True. If at least one of these layers is invisible,
    `path_visible` is False.
  
  * `file_extension` (read-only) - File extension of the layer name. If the layer has
    no extension, empty string is returned.
  """
  
  def __init__(self, layer, parents=None):
    if layer is None:
      raise TypeError("layer cannot be None")
    
    self.layer = layer
    self.parents = parents if parents is not None else []
    
    self.level = len(self.parents)
    
    self.layer_name = self.layer.name
#    self.layer_name = self.layer.name.decode()
    self.is_group = pdb.gimp_item_is_group(self.layer)
    self.is_empty = self.is_group and not self.layer.children
    
    self.path_components = self.update_path_components()
    self.path_visible = self._get_layer_visibility()
  
  @property
  def file_extension(self):
    return libfiles.get_file_extension(self.layer_name)
  
  def get_filename(self, output_directory, file_extension, include_layer_path=True):
    """
    Create layer filename.
    
    If `include_layer_path` is True, get layer filename in the following format:
    <output directory>/<layer path>/<layer name>.<file extension>
    
    If `include_layer_path` is False, get layer filename in the following format:
    <output directory>/<layer name>.<file extension>
    
    Parameters:
    
    * `output_directory` - Output directory.
    
    * `file_extension` - File extension for the filename.
    
    * `include_layer_path` - If True, insert the `path_components` attribute
      into the file path after the output directory.
    """
    
    if output_directory is None:
      output_directory = ""
    
    path = os.path.abspath(output_directory)
    if include_layer_path and self.path_components:
      path = os.path.join(path, os.path.join(*self.path_components))
    path = os.path.join(path, self.layer_name)
    
    if file_extension is not None and file_extension and not self.is_empty:
      path += '.' + file_extension
    
    return path
  
  def update_path_components(self):
    """
    Re-create and return the `path_components` attribute.
    
    This method should be called if `layer_name` for non-empty layer groups
    was changed.
    """
    return [parent.layer_name for parent in reversed(self.parents)]
  
  def validate_name(self):
    """
    Validate `layer_name` and `path_components` attributes.
    """
    self.layer_name = libfiles.FilenameValidator.validate(self.layer_name)
    self.path_components = [libfiles.FilenameValidator.validate(path_component)
                            for path_component in self.path_components]

  def _get_layer_visibility(self):
    """
    If the layer and all of its parents are visible, return True,
    otherwise return False.
    """
    path_visible = True
    if self.layer is not None and not self.layer.visible:
      path_visible = False
    else:
      for parent in self.parents:
        if not parent.layer.visible:
          path_visible = False
          break
    return path_visible
