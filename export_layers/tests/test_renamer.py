# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import unittest

import mock
import parameterized

from export_layers import pygimplib as pg

from export_layers.pygimplib.tests import stubs_gimp
from export_layers.pygimplib.tests import utils_itemtree

from export_layers import renamer


class TestNumberField(unittest.TestCase):
  
  @parameterized.parameterized.expand([
    ('two_padding_zeroes',
     1, 3, ['001', '002', '003']),
    ('one_padding_zero',
     1, 2, ['01', '02', '03']),
    ('start_from_number_greater_than_one',
     5, 3, ['005', '006', '007']),
    ('incrementing_number_to_two_digits_removes_one_padded_zero',
     9, 3, ['009', '010', '011']),
    ('incrementing_number_to_digits_without_padding_removes_last_padded_zero',
     99, 3, ['099', '100', '101']),
    ('incrementing_number_to_more_digits_than_padding',
     999, 3, ['999', '1000', '1001']),
  ])
  def test_generate_number(
        self, test_case_name_suffix, initial_number, padding, expected_outputs):
    number_generator = renamer.NumberField.generate_number(initial_number, padding)
    outputs = [next(number_generator) for unused_ in range(len(expected_outputs))]
    
    self.assertListEqual(outputs, expected_outputs)


@mock.patch(
  pg.PYGIMPLIB_MODULE_PATH + '.itemtree.pdb',
  new=stubs_gimp.PdbStub())
@mock.patch(
  pg.PYGIMPLIB_MODULE_PATH + '.itemtree.gimp.GroupLayer',
  new=stubs_gimp.LayerGroupStub)
class TestRenameWithNumberField(unittest.TestCase):
  
  @mock.patch(
    pg.PYGIMPLIB_MODULE_PATH + '.itemtree.pdb',
    new=stubs_gimp.PdbStub())
  @mock.patch(
    pg.PYGIMPLIB_MODULE_PATH + '.itemtree.gimp.GroupLayer',
    new=stubs_gimp.LayerGroupStub)
  def setUp(self):
    layers_string = """
      foreground
      Corners {
        corner
        top-left-corner {
          bottom-left-corner
          bottom-right-corner
          top-left-corner
        }
        top-right-corner
      }
      Frames {
        top-frame
      }
      background
      Overlay {
      }
      Overlay2
    """
    
    self.image = utils_itemtree.parse_layers(layers_string)
  
  @parameterized.parameterized.expand([
    ('start_from_one',
     'image[001]',
     """
     image001
     Corners {
       image001
       top-left-corner {
         image001
         image002
         image003
       }
       image002
     }
     Frames {
       image001
     }
     image002
     Overlay {
     }
     image003
      """),
    
    ('start_with_offset',
     'image[003]',
     """
     image003
     Corners {
       image003
       top-left-corner {
         image003
         image004
         image005
       }
       image004
     }
     Frames {
       image003
     }
     image004
     Overlay {
     }
     image005
      """),
    
    ('multiple_number_fields_increment_independently',
     'image[001]_[005]',
     """
     image001_005
     Corners {
       image001_005
       top-left-corner {
         image001_005
         image002_006
         image003_007
       }
       image002_006
     }
     Frames {
       image001_005
     }
     image002_006
     Overlay {
     }
     image003_007
     """),
  ])
  def test_rename(self, test_case_name_suffix, pattern, expected_layer_names_str):
    layer_tree = pg.itemtree.LayerTree(self.image)
    
    layer_exporter_mock = mock.Mock()
    
    layer_name_renamer = renamer.LayerNameRenamer(
      layer_exporter_mock, pattern, fields_raw=[renamer.FIELDS['^[0-9]+$']])
    
    for layer_elem in layer_tree:
      layer_exporter_mock.current_layer_elem = layer_elem
      
      if layer_elem.item_type == layer_elem.ITEM:
        layer_elem.name = layer_name_renamer.rename(layer_elem)
    
    expected_layer_tree = (
      pg.itemtree.LayerTree(utils_itemtree.parse_layers(expected_layer_names_str)))
    
    self.assertListEqual(
      [renamed_layer_elem.name for renamed_layer_elem in layer_tree],
      [expected_layer_elem.name for expected_layer_elem in expected_layer_tree])
