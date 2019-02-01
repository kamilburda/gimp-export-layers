# -*- coding: utf-8 -*-
#
# This file is part of Export Layers.
#
# Copyright (C) 2013-2019 khalim19 <khalim19@gmail.com>
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
# along with Export Layers.  If not, see <https://www.gnu.org/licenses/>.

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import unittest

import mock
import parameterized

from export_layers import pygimplib

from export_layers.pygimplib import pgitemtree
from export_layers.pygimplib import pgconstants
from export_layers.pygimplib.tests import stubs_gimp
from export_layers.pygimplib.tests import utils_pgitemtree

from .. import renamer

pygimplib.init()


class TestNumberField(unittest.TestCase):
  
  @parameterized.parameterized.expand([
    ("two_padding_zeroes",
     3, 1, ["001", "002", "003"]),
    ("one_padding_zero",
     2, 1, ["01", "02", "03"]),
    ("start_from_number_greater_than_one",
     3, 5, ["005", "006", "007"]),
    ("incrementing_number_to_two_digits_removes_one_padded_zero",
     3, 9, ["009", "010", "011"]),
    ("incrementing_number_to_digits_without_padding_removes_last_padded_zero",
     3, 99, ["099", "100", "101"]),
    ("incrementing_number_to_more_digits_than_padding",
     3, 999, ["999", "1000", "1001"]),
  ])
  def test_generate_number(
        self, test_case_name_suffix, padding, initial_number, expected_outputs):
    number_generator = renamer.NumberField.generate_number(padding, initial_number)
    outputs = [next(number_generator) for unused_ in range(len(expected_outputs))]
    
    self.assertListEqual(outputs, expected_outputs)


@mock.patch(
  pgconstants.PYGIMPLIB_MODULE_PATH + ".pgitemtree.pdb",
  new=stubs_gimp.PdbStub())
@mock.patch(
  pgconstants.PYGIMPLIB_MODULE_PATH + ".pgitemtree.gimp.GroupLayer",
  new=stubs_gimp.LayerGroupStub)
class TestRenameWithNumberField(unittest.TestCase):
  
  @mock.patch(
    pgconstants.PYGIMPLIB_MODULE_PATH + ".pgitemtree.pdb",
    new=stubs_gimp.PdbStub())
  @mock.patch(
    pgconstants.PYGIMPLIB_MODULE_PATH + ".pgitemtree.gimp.GroupLayer",
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
    
    self.image = utils_pgitemtree.parse_layers(layers_string)
  
  @parameterized.parameterized.expand([
    ("start_from_one",
     "image[001]",
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
    
    ("start_with_offset",
     "image[003]",
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
    
    ("multiple_number_fields_increment_independently",
     "image[001]_[005]",
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
    layer_tree = pgitemtree.LayerTree(self.image)
    
    layer_name_renamer = (
      renamer.LayerNameRenamer(None, pattern, fields=[renamer.NumberField()]))
    
    for layer_elem in layer_tree:
      if layer_elem.item_type == layer_elem.ITEM:
        layer_name_renamer.rename(layer_elem)
    
    expected_layer_tree = (
      pgitemtree.LayerTree(utils_pgitemtree.parse_layers(expected_layer_names_str)))
    
    self.assertListEqual(
      [renamed_layer_elem.name for renamed_layer_elem in layer_tree],
      [expected_layer_elem.name for expected_layer_elem in expected_layer_tree])
