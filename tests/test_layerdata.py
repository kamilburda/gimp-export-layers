#-------------------------------------------------------------------------------
#
# This file is part of libgimpplugin.
#
# Copyright (C) 2014 khalim19 <khalim19@gmail.com>
# 
# libgimpplugin is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# libgimpplugin is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with libgimpplugin.  If not, see <http://www.gnu.org/licenses/>.
#
#-------------------------------------------------------------------------------

#===============================================================================

from __future__ import absolute_import
from __future__ import print_function
#from __future__ import unicode_literals
from __future__ import division

#=============================================================================== 

import os
from collections import OrderedDict

import unittest

from ..lib import mock

from .. import layerdata

from . import gimpmocks

#===============================================================================

LIB_NAME = '.'.join(__name__.split('.')[:-2])

#===============================================================================

class LayerFilters(object):
  
  @staticmethod
  def is_layer(layerdata_elem):
    return not layerdata_elem.is_group
  
  @staticmethod
  def is_layer_or_empty_group(layerdata_elem):
    return not layerdata_elem.is_group or layerdata_elem.is_empty
  
  @staticmethod
  def is_path_visible(layerdata_elem):
    return layerdata_elem.path_visible
  
  @staticmethod
  def has_matching_file_format(layerdata_elem, file_format):
    return layerdata_elem.layer_name.endswith('.' + file_format)

#===============================================================================

@mock.patch(LIB_NAME + '.layerdata.pdb', new=gimpmocks.MockPDB())
class TestLayerData(unittest.TestCase):

  @mock.patch(LIB_NAME + '.layerdata.pdb', new=gimpmocks.MockPDB())
  def setUp(self):
    super(TestLayerData, self).setUp()
    
    self.image = gimpmocks.MockImage()
    
    self.all_layers = OrderedDict()
    
    layers = OrderedDict()
    layers['Corners'] = gimpmocks.MockLayerGroup("Corners")
    layers['Frames'] = gimpmocks.MockLayerGroup("Frames")
    layers['[Main Background.png]'] = gimpmocks.MockLayer("[Main Background.png]")
    layers['Overlay - Colorify Create.jpg'] = gimpmocks.MockLayer("Overlay - Colorify Create.jpg", False)
    layers['Overlay - Colorify Create.jpg#'] = gimpmocks.MockLayer("Overlay - Colorify Create.jpg#", False)
    layers['Layer Group'] = gimpmocks.MockLayerGroup("Layer Group", False)
    layers['Layer Group#'] = gimpmocks.MockLayerGroup("Layer Group#", False)
    layers['Layer Group ####4'] = gimpmocks.MockLayerGroup("Layer Group ####4", False)
    layers['Layer Group.png'] = gimpmocks.MockLayerGroup("Layer Group.png", False)
    layers['Overlay - Colorify Convert'] = gimpmocks.MockLayer("Overlay - Colorify Convert", False)
    layers['Overlay - Darken'] = gimpmocks.MockLayer("Overlay - Darken", False)
    self.image.layers = [layer for layer in layers.values()]
    self.all_layers.update(layers)
    
    self.top_level_layers = OrderedDict(layers)
    
    layers = OrderedDict()
    layers['top-left-corner'] = gimpmocks.MockLayer("top-left-corner")
    layers['Layer Group ##1'] = gimpmocks.MockLayerGroup("Layer Group ##1")
    layers['Layer Group #3'] = gimpmocks.MockLayerGroup("Layer Group #3")
    layers['Layer Group ##3'] = gimpmocks.MockLayerGroup("Layer Group ##3")
    layers['top-right-corner'] = gimpmocks.MockLayer("top-right-corner")
    self.all_layers['Corners'].children = [layer for layer in layers.values()]
    self.all_layers.update(layers)
    
    layers = OrderedDict()
    layers['bottom-right-corner'] = gimpmocks.MockLayer("bottom-right-corner")
    layers['bottom-left-corner'] = gimpmocks.MockLayer("bottom-left-corner")
    self.all_layers['Layer Group ##1'].children = [layer for layer in layers.values()]
    self.all_layers.update(layers)
    
    layers = OrderedDict()
    layers['top-frame'] = gimpmocks.MockLayer("top-frame")
    layers['Layer Group #1'] = gimpmocks.MockLayerGroup("Layer Group #1")
    layers['right-frame'] = gimpmocks.MockLayer("right-frame")
    layers['right-frame#'] = gimpmocks.MockLayer("right-frame#")
    layers['[Layer Group #2]'] = gimpmocks.MockLayerGroup("[Layer Group #2]")
    self.all_layers['Frames'].children = [layer for layer in layers.values()]
    self.all_layers.update(layers)
    
    layers = OrderedDict()
    layers['Layer Group 4'] = gimpmocks.MockLayerGroup("Layer Group 4", False)
    layers['Layer Group #4'] = gimpmocks.MockLayerGroup("Layer Group #4")
    layers['Layer Group ##4'] = gimpmocks.MockLayerGroup("Layer Group ##4")
    layers['Layer Group ###4'] = gimpmocks.MockLayerGroup("Layer Group ###4")
    self.all_layers['Layer Group #1'].children = [layer for layer in layers.values()]
    self.all_layers.update(layers)
    
    layers = OrderedDict()
    layers['right-frame# copy'] = gimpmocks.MockLayer("right-frame# copy")
    self.all_layers['Layer Group 4'].children = [layer for layer in layers.values()]
    self.all_layers.update(layers)
    
    layers = OrderedDict()
    layers['bottom-frame copy #1'] = gimpmocks.MockLayer("bottom-frame copy #1")
    layers['Layer Group #7'] = gimpmocks.MockLayerGroup("Layer Group #7")
    self.all_layers['Layer Group #4'].children = [layer for layer in layers.values()]
    self.all_layers.update(layers)
    
    layers = OrderedDict()
    layers['bottom-frame #1'] = gimpmocks.MockLayer("bottom-frame #1", False)
    self.all_layers['Layer Group #7'].children = [layer for layer in layers.values()]
    self.all_layers.update(layers)
    
    layers = OrderedDict()
    layers['bottom-frame copy'] = gimpmocks.MockLayer("bottom-frame copy")
    layers['Layer Group ######4'] = gimpmocks.MockLayerGroup("Layer Group ######4")
    self.all_layers['Layer Group ##4'].children = [layer for layer in layers.values()]
    self.all_layers.update(layers)
    
    layers = OrderedDict()
    layers['bottom-frame'] = gimpmocks.MockLayer("bottom-frame")
    self.all_layers['Layer Group ######4'].children = [layer for layer in layers.values()]
    self.all_layers.update(layers)
    
    self.layer_data = layerdata.LayerData(self.image, is_filtered=False)
    self.layer_count_total = 34
    self.layer_count_only_layers = 17
    self.layer_count_empty_groups = 8
    self.layer_count_matches_jpg = 1
  
  def test_get_len(self):
    self.assertEqual(len(self.layer_data), self.layer_count_total)
    
    self.layer_data.is_filtered = True
    self.layer_data.filter.add_rule(LayerFilters.is_layer)
    self.assertEqual(len(self.layer_data), self.layer_count_only_layers)
  
  def test_empty_layerdata(self):
    self.layer_data.is_filtered = True
    with self.layer_data.filter.add_rule_temp(LayerFilters.has_matching_file_format, 'nolayerhasthisformat'):
      self.assertFalse(bool(self.layer_data))
  
  def test_get_filename(self):
    output_directory = os.path.join("D:", os.sep, "testgimp");
    file_format = 'png'
    # layerdata_elem with parents
    layerdata_elem = self.layer_data['bottom-right-corner']
    
    self.assertEqual(layerdata_elem.get_filename(output_directory, file_format),
                     os.path.join(output_directory, "Corners", "Layer Group ##1",
                                  layerdata_elem.layer_name) +
                       "." + file_format)
    self.assertEqual(layerdata_elem.get_filename(output_directory, file_format, include_layer_path=False),
                     os.path.join(output_directory, layerdata_elem.layer_name) +
                       "." + file_format)
    self.assertEqual(layerdata_elem.get_filename("testgimp", file_format),
                     os.path.join(os.getcwd(), "testgimp", "Corners", "Layer Group ##1",
                                  layerdata_elem.layer_name) +
                       "." + file_format)
    self.assertEqual(layerdata_elem.get_filename(None, file_format),
                     os.path.join(os.getcwd(), "Corners", "Layer Group ##1",
                                  layerdata_elem.layer_name) +
                       "." + file_format)
    self.assertEqual(layerdata_elem.get_filename(output_directory, None),
                     os.path.join(output_directory, "Corners", "Layer Group ##1",
                                  layerdata_elem.layer_name))
    
    # layerdata_elem without parents
    layerdata_with_file_ext = self.layer_data['Overlay - Colorify Create.jpg']
    self.assertEqual(layerdata_with_file_ext.get_filename(output_directory, file_format),
                     os.path.join(output_directory, layerdata_with_file_ext.layer_name) + "." + file_format)
    self.assertEqual(layerdata_with_file_ext.get_filename(output_directory, file_format),
                     layerdata_with_file_ext.get_filename(output_directory, file_format,
                                                          include_layer_path=False))
    self.assertTrue(layerdata_with_file_ext.get_filename(output_directory, "png")
                    .endswith(".jpg.png"))
    self.assertTrue(layerdata_with_file_ext.get_filename(output_directory, "jpg")
                    .endswith(".jpg.jpg"))
    self.assertTrue(layerdata_with_file_ext.get_filename(output_directory, None)
                    .endswith(".jpg"))
    
    layerdata_empty_layer_group = self.layer_data['[Layer Group #2]']
    self.assertEqual(layerdata_empty_layer_group.get_filename(output_directory, file_format),
                     os.path.join(output_directory, 'Frames', layerdata_empty_layer_group.layer_name))
    self.assertEqual(layerdata_empty_layer_group.get_filename(output_directory, file_format,
                                                              include_layer_path=False),
                     os.path.join(output_directory, layerdata_empty_layer_group.layer_name))
    
    layerdata_empty_layer_group_no_parents = self.layer_data['Layer Group']
    self.assertEqual(layerdata_empty_layer_group_no_parents.get_filename(output_directory, file_format),
                     os.path.join(output_directory, layerdata_empty_layer_group_no_parents.layer_name))
    self.assertEqual(layerdata_empty_layer_group_no_parents.get_filename(output_directory, file_format),
                     layerdata_empty_layer_group_no_parents.get_filename(output_directory, file_format,
                                                                         include_layer_path=False))
  
  def test_get_file_extension_properties(self):
    self.layer_data.is_filtered = True
    
    with self.layer_data.filter.add_rule_temp(LayerFilters.is_layer):
      layer_file_extensions = self.layer_data.get_file_extension_properties('jpg')
      
      for file_ext in layer_file_extensions:
        self.assertEqual(layer_file_extensions[file_ext].is_valid, True)
      
      self.assertEqual(layer_file_extensions['jpg'].count, self.layer_count_only_layers - 2)
      self.assertEqual(layer_file_extensions['jpg#'].count, 1)
      self.assertEqual(layer_file_extensions['png]'].count, 1)
  
  def process_layer_data(self, layer_data):
    for layer_data_elem in layer_data:
      # "#" is removed from layer names so that multiple layers have the same name
      # so that the uniquification can kick in.
      layer_data_elem.layer_name = layer_data_elem.layer_name.translate(None, "#")
      layer_data_elem.path_components = [path_component.translate(None, "#")
                                         for path_component in layer_data_elem.path_components]
  
  def compare_uniquified_without_parents(self, layer_data, uniquified_layer_names):
    for key, layer_name in uniquified_layer_names.items():
      self.assertEqual(layer_data[key].layer_name, layer_name,
                       "'" + key + "': '" + str(layer_data[key].layer_name) + "' != '" + str(layer_name) + "'")
  
  def compare_uniquified_with_parents(self, layer_data, uniquified_layer_names):
    for key, layer_path in uniquified_layer_names.items():
      path_components, layer_name = layer_path[:-1], layer_path[-1]
      self.assertEqual(layer_data[key].path_components, path_components,
                       ("parents: '" + key + "': '" + str(layer_data[key].path_components) +
                        "' != '" + str(path_components) + "'"))
      self.assertEqual(layer_data[key].layer_name, layer_name,
                       ("layer name: '" + key + "': '" + str(layer_data[key].layer_name) +
                       "' != '" + str(layer_name) + "'"))
  
  def get_layer_names_without_parents(self, layer_data):
    layer_names = OrderedDict()
    
    orig_is_filtered = layer_data.is_filtered
    layer_data.is_filtered = True
    
    with layer_data.filter.add_rule_temp(LayerFilters.is_layer_or_empty_group):
      for layerdata_elem in layer_data:
        layer_names[layerdata_elem.layer_name] = layerdata_elem.layer_name
    
    layer_data.is_filtered = orig_is_filtered
    
    return layer_names
  
  def get_layer_names_with_parents(self, layer_data):
    layer_names = OrderedDict()
    with layer_data.filter.add_rule_temp(LayerFilters.is_layer_or_empty_group):
      for layerdata_elem in layer_data:
        layer_names[layerdata_elem.layer_name] = layerdata_elem.path_components + [layerdata_elem.layer_name]
    
    return layer_names
  
  def test_uniquify_without_parents(self):
    self.layer_data.is_filtered = True
    layer_names = self.get_layer_names_without_parents(self.layer_data)
    
    self.process_layer_data(self.layer_data)
    self.layer_data.uniquify_layer_names(include_layer_path=False)
    
    layer_names['Overlay - Colorify Create.jpg#'] = "Overlay - Colorify Create.jpg (1)"
    layer_names['Layer Group#']                   = "Layer Group (1)"
    layer_names['Layer Group ####4']              = "Layer Group 4"
    layer_names['Layer Group #3']                 = "Layer Group 3"
    layer_names['Layer Group ##3']                = "Layer Group 3 (1)"
    layer_names['right-frame#']                   = "right-frame (1)"
    layer_names['[Layer Group #2]']               = "[Layer Group 2]"
    layer_names['Layer Group ###4']               = "Layer Group 4 (1)"
    layer_names['right-frame# copy']              = "right-frame copy"
    layer_names['bottom-frame copy #1']           = "bottom-frame copy 1"
    layer_names['bottom-frame #1']                = "bottom-frame 1"
    
    self.compare_uniquified_without_parents(self.layer_data, layer_names)
    
    self.layer_data.is_filtered = False
    self.layer_data.filter.add_rule(LayerFilters.is_path_visible)
    self.layer_data.uniquify_layer_names(include_layer_path=False)
    
    self.compare_uniquified_without_parents(self.layer_data, layer_names)
  
  def test_uniquify_with_parents(self):
    self.layer_data.is_filtered = True
    layer_names = self.get_layer_names_with_parents(self.layer_data)
    
    self.process_layer_data(self.layer_data)
    self.layer_data.uniquify_layer_names(include_layer_path=True)
    
    layer_names['Overlay - Colorify Create.jpg#'] = ["Overlay - Colorify Create.jpg (1)"]
    layer_names['Layer Group#']                   = ["Layer Group (1)"]
    layer_names['Layer Group ####4']              = ["Layer Group 4"]
    layer_names['Layer Group #3']                 = ["Corners", "Layer Group 3"]
    layer_names['Layer Group ##3']                = ["Corners", "Layer Group 3 (1)"]
    layer_names['bottom-right-corner']            = ["Corners",
                                                     "Layer Group 1",
                                                     "bottom-right-corner"]
    layer_names['bottom-left-corner']             = ["Corners",
                                                     "Layer Group 1",
                                                     "bottom-left-corner"]
    layer_names['right-frame#']                   = ["Frames", "right-frame (1)"]
    layer_names['[Layer Group #2]']               = ["Frames", "[Layer Group 2]"]
    layer_names['Layer Group ###4']               = ["Frames",
                                                     "Layer Group 1",
                                                     "Layer Group 4 (3)"]
    layer_names['right-frame# copy']              = ["Frames",
                                                     "Layer Group 1",
                                                     "Layer Group 4",
                                                     "right-frame copy"]
    layer_names['bottom-frame copy #1']           = ["Frames",
                                                     "Layer Group 1",
                                                     "Layer Group 4 (1)",
                                                     "bottom-frame copy 1"]
    layer_names['bottom-frame #1']                = ["Frames",
                                                     "Layer Group 1",
                                                     "Layer Group 4 (1)",
                                                     "Layer Group 7",
                                                     "bottom-frame 1"]
    layer_names['bottom-frame copy']              = ["Frames",
                                                     "Layer Group 1",
                                                     "Layer Group 4 (2)",
                                                     "bottom-frame copy"]
    layer_names['bottom-frame']                   = ["Frames",
                                                     "Layer Group 1",
                                                     "Layer Group 4 (2)",
                                                     "Layer Group 4",
                                                     "bottom-frame"]
    
    self.compare_uniquified_with_parents(self.layer_data, layer_names)
    
    self.layer_data.is_filtered = False
    self.layer_data.filter.add_rule(LayerFilters.is_path_visible)
    self.layer_data.uniquify_layer_names(include_layer_path=True)
    
    self.compare_uniquified_with_parents(self.layer_data, layer_names)
  
  def test_uniquify_filtered_without_parents(self):
    self.layer_data.is_filtered = True
    layer_names = self.get_layer_names_without_parents(self.layer_data)
    
    self.process_layer_data(self.layer_data)
    self.layer_data.filter.add_rule(LayerFilters.is_path_visible)
    self.layer_data.uniquify_layer_names(include_layer_path=False)
    
    layer_names['Overlay - Colorify Create.jpg#'] = "Overlay - Colorify Create.jpg"
    layer_names['Layer Group#']                   = "Layer Group"
    layer_names['Layer Group ####4']              = "Layer Group 4"
    layer_names['Layer Group #3']                 = "Layer Group 3"
    layer_names['Layer Group ##3']                = "Layer Group 3 (1)"
    layer_names['right-frame#']                   = "right-frame (1)"
    layer_names['[Layer Group #2]']               = "[Layer Group 2]"
    layer_names['Layer Group ###4']               = "Layer Group 4"
    layer_names['right-frame# copy']              = "right-frame copy"
    layer_names['bottom-frame copy #1']           = "bottom-frame copy 1"
    layer_names['bottom-frame #1']                = "bottom-frame 1"
    
    self.compare_uniquified_without_parents(self.layer_data, layer_names)
  
  def test_uniquify_filtered_with_parents(self):
    self.layer_data.is_filtered = True
    layer_names = self.get_layer_names_with_parents(self.layer_data)
    
    self.process_layer_data(self.layer_data)
    self.layer_data.filter.add_rule(LayerFilters.is_path_visible)
    self.layer_data.uniquify_layer_names(include_layer_path=True)
    
    layer_names['Overlay - Colorify Create.jpg#'] = ["Overlay - Colorify Create.jpg"]
    layer_names['Layer Group#']                   = ["Layer Group"]
    layer_names['Layer Group ####4']              = ["Layer Group 4"]
    layer_names['Layer Group #3']                 = ["Corners", "Layer Group 3"]
    layer_names['Layer Group ##3']                = ["Corners", "Layer Group 3 (1)"]
    layer_names['bottom-right-corner']            = ["Corners",
                                                     "Layer Group 1",
                                                     "bottom-right-corner"]
    layer_names['bottom-left-corner']             = ["Corners",
                                                     "Layer Group 1",
                                                     "bottom-left-corner"]
    layer_names['right-frame#']                   = ["Frames", "right-frame (1)"]
    layer_names['[Layer Group #2]']               = ["Frames", "[Layer Group 2]"]
    layer_names['Layer Group ###4']               = ["Frames",
                                                     "Layer Group 1",
                                                     "Layer Group 4 (2)"]
    layer_names['right-frame# copy']              = ["Frames",
                                                     "Layer Group 1",
                                                     "Layer Group 4",
                                                     "right-frame copy"]
    layer_names['bottom-frame copy #1']           = ["Frames",
                                                     "Layer Group 1",
                                                     "Layer Group 4",
                                                     "bottom-frame copy 1"]
    layer_names['bottom-frame #1']                = ["Frames",
                                                     "Layer Group 1",
                                                     "Layer Group 4",
                                                     "Layer Group 7",
                                                     "bottom-frame 1"]
    layer_names['bottom-frame copy']              = ["Frames",
                                                     "Layer Group 1",
                                                     "Layer Group 4 (1)",
                                                     "bottom-frame copy"]
    layer_names['bottom-frame']                   = ["Frames",
                                                     "Layer Group 1",
                                                     "Layer Group 4 (1)",
                                                     "Layer Group 4",
                                                     "bottom-frame"]
    
    self.compare_uniquified_with_parents(self.layer_data, layer_names)
  
  def test_uniquify_without_parents_place_before_file_extension(self):
    self.layer_data.is_filtered = True
    layer_names = self.get_layer_names_without_parents(self.layer_data)
    
    self.process_layer_data(self.layer_data)
    self.layer_data.uniquify_layer_names(include_layer_path=False, place_before_file_extension=True)
    
    layer_names['[Main Background.png]']          = "[Main Background.png]"
    layer_names['Overlay - Colorify Create.jpg#'] = "Overlay - Colorify Create (1).jpg"
    layer_names['Layer Group#']                   = "Layer Group (1)"
    layer_names['Layer Group ####4']              = "Layer Group 4"
    layer_names['Layer Group #3']                 = "Layer Group 3"
    layer_names['Layer Group ##3']                = "Layer Group 3 (1)"
    layer_names['right-frame#']                   = "right-frame (1)"
    layer_names['[Layer Group #2]']               = "[Layer Group 2]"
    layer_names['Layer Group ###4']               = "Layer Group 4 (1)"
    layer_names['right-frame# copy']              = "right-frame copy"
    layer_names['bottom-frame copy #1']           = "bottom-frame copy 1"
    layer_names['bottom-frame #1']                = "bottom-frame 1"
    
    self.compare_uniquified_without_parents(self.layer_data, layer_names)
