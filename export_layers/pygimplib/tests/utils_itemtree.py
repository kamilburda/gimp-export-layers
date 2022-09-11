# -*- coding: utf-8 -*-

"""Utility functions for the `test_itemtree` module."""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

from . import stubs_gimp


def parse_layers(layer_tree_string):
  """
  From a given string containing layer names separated by lines and
  curly braces (each on a separate line), return an image containing parsed
  layers.
  
  Leading or trailing spaces in each line in the string are truncated.
  """
  image = stubs_gimp.ImageStub()
  
  layer_tree_string = layer_tree_string.strip()
  lines = layer_tree_string.splitlines(False)
  
  num_lines = len(lines)
  parents = [image]
  current_parent = image
  
  for i in range(num_lines):
    current_symbol = lines[i].strip()
    
    layer = None
    
    if current_symbol.endswith(' {'):
      layer = stubs_gimp.LayerGroupStub(current_symbol.rstrip(' {'))
      current_parent.layers.append(layer)
      current_parent = layer
      parents.append(current_parent)
    elif current_symbol == '}':
      parents.pop()
      current_parent = parents[-1]
    else:
      layer = stubs_gimp.LayerStub(current_symbol)
      current_parent.layers.append(layer)
    
    if layer is not None:
      layer.parent = current_parent
  
  return image
