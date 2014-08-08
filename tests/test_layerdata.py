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

#===============================================================================

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division

str = unicode

#=============================================================================== 

import os
from collections import OrderedDict

import unittest

from ..lib import mock
from . import gimpmocks

from .. import layerdata

#===============================================================================

LIB_NAME = '.'.join(__name__.split('.')[:-2])

#===============================================================================

class LayerFilterRules(object):
  
  @staticmethod
  def is_layer(layerdata_elem):
    return layerdata_elem.layer_type == layerdata_elem.LAYER
  
  @staticmethod
  def is_layer_or_empty_group(layerdata_elem):
    return layerdata_elem.layer_type in (layerdata_elem.LAYER, layerdata_elem.EMPTY_GROUP)
  
  @staticmethod
  def is_path_visible(layerdata_elem):
    return layerdata_elem.path_visible
  
  @staticmethod
  def has_matching_file_extension(layerdata_elem, file_extension):
    return layerdata_elem.layer_name.endswith('.' + file_extension)

#===============================================================================

def _parse_layers(docstring):
  """
  From a given docstring containing layer names separated by lines and
  curly braces (each on a separate line), return an image containing parsed
  layers.
  
  Leading or trailing spaces in each line in the docstring are truncated.
  """
  
  image = gimpmocks.MockImage()
  
  docstring = docstring.strip()
  lines = docstring.splitlines(False)
  
  num_lines = len(lines)
  parents = [image]
  current_parent = image
  
  for i in range(num_lines):
    current_symbol = lines[i].strip()
    
    layer = None
    
    if current_symbol.endswith(" {"):
      layer = gimpmocks.MockLayerGroup(current_symbol.rstrip(" {"))
      current_parent.layers.append(layer)
      current_parent = layer
      parents.append(current_parent)
    elif current_symbol == "}":
      parents.pop()
      current_parent = parents[-1]
    else:
      layer = gimpmocks.MockLayer(current_symbol)
      current_parent.layers.append(layer)
    
    if layer is not None:
      layer.parent = current_parent
  
  return image

#===============================================================================

@mock.patch(LIB_NAME + '.layerdata.pdb', new=gimpmocks.MockPDB())
class TestLayerData(unittest.TestCase):

  @mock.patch(LIB_NAME + '.layerdata.pdb', new=gimpmocks.MockPDB())
  def setUp(self):
    layers_string = """
      Corners {
        top-left-corner
        top-right-corner
        top-left-corner: {
        }
        top-left-corner:: {
          bottom-right-corner
          bottom-right-corner:
          bottom-left-corner
        }
      }
      Corners: {
        top-left-corner:::
      }
      Frames {
        top-frame
      }
      main-background.jpg
      main-background.jpg:
      Overlay {
      }
      Corners::
      top-left-corner::::
      main-background.jpg:: {
        alt-frames
        alt-corners
      }
    """
    
    image = _parse_layers(layers_string)
    self.layer_data = layerdata.LayerData(image)
  
  def test_get_len(self):
    layer_count_total = 20
    layer_count_only_layers = 13
    
    self.assertEqual(len(self.layer_data), layer_count_total)
    
    self.layer_data.is_filtered = True
    self.layer_data.filter.add_rule(LayerFilterRules.is_layer)
    self.assertEqual(len(self.layer_data), layer_count_only_layers)
  
  def test_get_filepath(self):
    output_directory = os.path.join("D:", os.sep, "testgimp");
    
    # layerdata_elem with parents
    layerdata_elem = self.layer_data['bottom-right-corner']
    
    self.assertEqual(
      layerdata_elem.get_filepath(output_directory),
      os.path.join(output_directory, "Corners", "top-left-corner::", layerdata_elem.layer_name)
    )
    self.assertEqual(
      layerdata_elem.get_filepath(output_directory, include_layer_path=False),
      os.path.join(output_directory, layerdata_elem.layer_name)
    )
    self.assertEqual(
      layerdata_elem.get_filepath("testgimp"),
      os.path.join(os.getcwd(), "testgimp", "Corners", "top-left-corner::", layerdata_elem.layer_name)
    )
    self.assertEqual(
      layerdata_elem.get_filepath(None),
      os.path.join(os.getcwd(), "Corners", "top-left-corner::", layerdata_elem.layer_name)
    )
    
    layerdata_empty_layer_group = self.layer_data['top-left-corner:']
    
    self.assertEqual(
      layerdata_empty_layer_group.get_filepath(output_directory),
      os.path.join(output_directory, 'Corners', layerdata_empty_layer_group.layer_name)
    )
    self.assertEqual(
      layerdata_empty_layer_group.get_filepath(output_directory, include_layer_path=False),
      os.path.join(output_directory, layerdata_empty_layer_group.layer_name)
    )
    
    layerdata_empty_layer_group_no_parents = self.layer_data['Overlay']
    
    self.assertEqual(
      layerdata_empty_layer_group_no_parents.get_filepath(output_directory),
      os.path.join(output_directory, layerdata_empty_layer_group_no_parents.layer_name)
    )
    self.assertEqual(
      layerdata_empty_layer_group_no_parents.get_filepath(output_directory),
      layerdata_empty_layer_group_no_parents.get_filepath(output_directory, include_layer_path=False)
    )
  
  def test_set_file_extension(self):
    layerdata_elem = self.layer_data['main-background.jpg']
    
    layerdata_elem.set_file_extension(None)
    self.assertEqual(layerdata_elem.layer_name, "main-background")
    layerdata_elem.set_file_extension("png")
    self.assertEqual(layerdata_elem.layer_name, "main-background.png")
  
  #-----------------------------------------------------------------------------
    
  def _compare_uniquified_without_parents(self, layer_data, uniquified_layer_names):
    for key, layer_name in uniquified_layer_names.items():
      self.assertEqual(
        layer_data[key].layer_name, layer_name,
        "'" + key + "': '" + str(layer_data[key].layer_name) + "' != '" + str(layer_name) + "'"
      )
  
  def _compare_uniquified_with_parents(self, layer_data, uniquified_layer_names):
    for key, layer_path in uniquified_layer_names.items():
      path_components, layer_name = layer_path[:-1], layer_path[-1]
      self.assertEqual(
        layer_data[key].get_path_components(), path_components,
        ("parents: '" + key + "': '" + str(layer_data[key].get_path_components()) +
         "' != '" + str(path_components) + "'")
      )
      self.assertEqual(
        layer_data[key].layer_name, layer_name,
        ("layer name: '" + key + "': '" + str(layer_data[key].layer_name) +
         "' != '" + str(layer_name) + "'")
      )
  
  def test_uniquifies_without_layer_groups(self):
    uniquified_layer_names = OrderedDict([
      ("top-left-corner",      "top-left-corner (1)"),
      ("top-right-corner",     "top-right-corner"),
      ("top-left-corner:",     "top-left-corner (2)"),
      ("bottom-right-corner",  "bottom-right-corner"),
      ("bottom-right-corner:", "bottom-right-corner (1)"),
      ("bottom-left-corner",   "bottom-left-corner"),
      ("top-left-corner:::",   "top-left-corner (3)"),
      ("top-frame",            "top-frame"),
      ("main-background.jpg",  "main-background.jpg"),
      ("main-background.jpg:", "main-background.jpg (1)"),
      ("Corners",              "Corners"),
      ("top-left-corner::::",  "top-left-corner")
    ])
    
    # This is to make the uniquification work properly for these tests. It's not
    # inside the `uniquify_layer_names` method because the code that uses this
    # method may need to uniquify non-empty layer groups in some scenarios
    # (such as when merging non-empty layer groups into layers, which would not
    # match the filter).
    self.layer_data.is_filtered = True
    self.layer_data.filter.add_rule(LayerFilterRules.is_layer_or_empty_group)
    
    for layerdata_elem in self.layer_data:
      layerdata_elem.validate_name()
      self.layer_data.uniquify_layer_name(layerdata_elem, include_layer_path=False,
                                          place_before_file_extension=False)
    self._compare_uniquified_without_parents(self.layer_data, uniquified_layer_names)
  
  def test_uniquifies_with_layer_groups(self):
    uniquified_layer_names = OrderedDict([
      ("Corners",                ["Corners (1)"]),
      ("top-left-corner",        ["Corners (1)", "top-left-corner"]),
      ("top-right-corner",       ["Corners (1)", "top-right-corner"]),
      ("top-left-corner:",       ["Corners (1)", "top-left-corner (1)"]),
      ("top-left-corner::",      ["Corners (1)", "top-left-corner (2)"]),
      ("bottom-right-corner",    ["Corners (1)", "top-left-corner (2)", "bottom-right-corner"]),
      ("bottom-right-corner:",   ["Corners (1)", "top-left-corner (2)", "bottom-right-corner (1)"]),
      ("bottom-left-corner",     ["Corners (1)", "top-left-corner (2)", "bottom-left-corner"]),
      ("Corners:",               ["Corners (2)"]),
      ("top-left-corner:::",     ["Corners (2)", "top-left-corner"]),
      ("Frames",                 ["Frames"]),
      ("top-frame",              ["Frames", "top-frame"]),
      ("main-background.jpg",    ["main-background.jpg"]),
      ("main-background.jpg:",   ["main-background.jpg (1)"]),
      ("Corners::",              ["Corners"]),
      ("top-left-corner::::",    ["top-left-corner"]),
      ("main-background.jpg::",  ["main-background.jpg (2)"]),
      ("alt-frames",             ["main-background.jpg (2)", "alt-frames"]),
      ("alt-corners",            ["main-background.jpg (2)", "alt-corners"]),
    ])
    
    self.layer_data.is_filtered = True
    self.layer_data.filter.add_rule(LayerFilterRules.is_layer_or_empty_group)
    
    for layerdata_elem in self.layer_data:
      layerdata_elem.validate_name()
      self.layer_data.uniquify_layer_name(layerdata_elem, include_layer_path=True,
                                          place_before_file_extension=False)
    self._compare_uniquified_with_parents(self.layer_data, uniquified_layer_names)
  
  def test_uniquifies_with_regards_to_file_extension(self):
    uniquified_layer_names = OrderedDict([
      ("main-background.jpg",    ["main-background.jpg"]),
      ("main-background.jpg:",   ["main-background (1).jpg"]),
      ("main-background.jpg::",  ["main-background.jpg (1)"])
    ])
    
    self.layer_data.is_filtered = True
    self.layer_data.filter.add_rule(LayerFilterRules.is_layer_or_empty_group)
    
    for layerdata_elem in self.layer_data:
      layerdata_elem.validate_name()
      self.layer_data.uniquify_layer_name(layerdata_elem, include_layer_path=True,
                                          place_before_file_extension=True)
    self._compare_uniquified_with_parents(self.layer_data, uniquified_layer_names)
  
