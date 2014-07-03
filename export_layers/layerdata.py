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
* defines an associative container that stores all layers and layer groups
* defines custom attributes for layers derived from the original attributes
"""

#=============================================================================== 

import os

from collections import OrderedDict
from collections import namedtuple

import gimp

import libgimpplugin
import objectfilter

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
  
  * image: GIMP image to get layers from.
  
  * is_filtered: If True, ignore layers that do not match the filter
    (ObjectFilter) in this object when iterating.
  
  * filter (read-only): ObjectFilter instance where you can add or remove filter
    rules.
  """
  
  def __init__(self, image, is_filtered=False):
    
    self.image = image
    
    self.is_filtered = is_filtered
    
    # Filters applied to all layers in self._layerdata
    self._filter = objectfilter.ObjectFilter()
    
    # Contains all layers (including groups) in the layer tree.
    # key: gimp.Layer.name (gimp.Layer names are unique)
    # value: _LayerDataElement object
    self._layerdata = OrderedDict()
    
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
    if not self.is_filtered:
      for layerdata_elem in self._layerdata.values():
        yield layerdata_elem
    else:
      for layerdata_elem in self._layerdata.values():
        if self._filter.is_match(layerdata_elem):
          yield layerdata_elem
  
  def get_file_format_properties(self, default_file_format):
    
    class LayerFileExtensionProperties(object):
      def __init__(self):
        self.count = 0
        self.processed_count = 0
        self.is_valid = True
    
    layer_file_ext_properties = {}
    
    for layerdata_elem in self:
      file_format = layerdata_elem.file_extension
      if not file_format:
        file_format = default_file_format
      
      if file_format not in layer_file_ext_properties:
        layer_file_ext_properties[file_format] = LayerFileExtensionProperties()
      layer_file_ext_properties[file_format].count += 1
    
    if default_file_format not in layer_file_ext_properties:
      layer_file_ext_properties[default_file_format] = LayerFileExtensionProperties()
    
    return layer_file_ext_properties
  
  def uniquify_layer_names(self, include_layer_path=True, place_before_file_extension=False):
    """
    Make the names of layers and layer groups unique so that
    all filenames or directory names on the same directory level are unique.
    
    This is necessary in case the layer names in the _LayerDataElement objects
    had their characters invalid in filenames removed, which may result in
    multiple layers or layer groups having the same name.
    
    To achieve uniquification, a string in the form of " (<number>)" is inserted
    at the end of the names.
    
    Parameters:
    
    * include_layer_path: If True, take layer path into account when uniquifying.
      
    * place_before_file_extension: Uniquify such that the " (<number>)" string
      that makes the names unique is placed before the file extension
      if the layer name has one.
    """
    
    def _uniquify(layerdata):
      layer_paths = set()
      for layerdata_elem in layerdata:
        layerdata_elem.layer_name = libgimpplugin.uniquify_string(
          layerdata_elem.layer_name, layer_paths, place_before_file_extension=place_before_file_extension)
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
    Fill the _layerdata dictionary,
    containing <gimp.Layer.name, _LayerDataElement> pairs.
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
  This class wraps a gimp.Layer object and defines custom layer attributes.
  
  Note that the attributes will not be up to date if changes were made to the
  original gimp.Layer objects.
  
  Attributes:
  
  * layer: gimp.Layer object
  
  * parents: List of _LayerDataElement parents for this layer, sorted from the
    bottommost (immediate) parent to the topmost parent.
  
  * level: Integer indicating at which level in the layer tree is the layer positioned.
    0 means the layer is at the top level.
  
  * layer_name: Layer name. Modify this attribute instead of gimp.Layer.name
    to avoid modifying the original layer.
  
  * is_group: If True, layer is a layer group. If False, layer is gimp.Layer.
  
  * is_empty: If True, layer is an empty layer group.
  
  * path_components: List of all parents' names for this layer, sorted from the
    topmost to the bottommost parent. This attribute can be used in determining
    the filename of the layer if layer groups are treated as directories.
  
  * path_visible: Visibility of all layer's parents and this layer. If all layers
    are visible, path_visible is True. If at least one of these layers is invisible,
    path_visible is False.
  
  * file_extension (read-only): File extension of the layer name. If the layer has
    no extension, empty string is returned.
  """
  
  def __init__(self, layer, parents=None):
    if layer is None:
      raise TypeError("layer cannot be None")
    
    self.layer = layer
    self.parents = parents if parents is not None else []
    
    self.level = len(self.parents)
    
    self.layer_name = self.layer.name
    self.is_group = pdb.gimp_item_is_group(self.layer)
    self.is_empty = self.is_group and not self.layer.children
    
    self.path_components = self.update_path_components()
    self.path_visible = self._get_layer_visibility()
  
  @property
  def file_extension(self):
    return libgimpplugin.get_file_extension(self.layer_name)
  
  def get_filename(self, output_directory, file_format, include_layer_path=True):
    """
    If include_layer_path is True, get layer filename in the following format:
    <output directory>/<layer path>/<layer name>.<file format>
    
    If include_layer_path is False, get layer filename in the following format:
    <output directory>/<layer name>.<file format>
    """
    
    if output_directory is None:
      output_directory = ""
    
    path = os.path.abspath(output_directory)
    if include_layer_path and self.path_components:
      path = os.path.join(path, os.path.join(*self.path_components))
    path = os.path.join(path, self.layer_name)
    
    if file_format is not None and file_format and not self.is_empty:
      path += '.' + file_format
    
    return path
  
  def update_path_components(self):
    return [parent.layer_name for parent in reversed(self.parents)]
  
  def validate_name(self, string_validator):
    self.layer_name = string_validator.validate(self.layer_name)
    self.path_components = [string_validator.validate(path_component)
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
