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

import parameterized

from export_layers.pygimplib.tests import stubs_gimp

from .. import placeholders


class TestGetReplacedArgsAndKwargs(unittest.TestCase):
  
  def test_get_replaced_args_and_kwargs(self):
    image = stubs_gimp.ImageStub()
    layer = stubs_gimp.LayerStub()
    layer_exporter = object()
    
    args = ["current_image", "current_layer", "some_other_arg"]
    kwargs = {
      "run_mode": 0, "image": "current_image", "layer": "current_layer"}
    
    new_args, new_kwargs = placeholders.get_replaced_args_and_kwargs(
      args, kwargs, image, layer, layer_exporter)
    
    self.assertListEqual(new_args, [image, layer, "some_other_arg"])
    self.assertDictEqual(new_kwargs, {"run_mode": 0, "image": image, "layer": layer})


class TestPlaceHolderSetting(unittest.TestCase):
  
  @parameterized.parameterized.expand([
    ("placeholder", placeholders.PlaceholderSetting, []),
    ("image_placeholder", placeholders.PlaceholderImageSetting, ["current_image"]),
  ])
  def test_get_allowed_placeholder_names(
        self, test_case_name_suffix, placeholder_setting_type, expected_result):
    self.assertListEqual(
      placeholder_setting_type.get_allowed_placeholder_names(), expected_result)
  
  @parameterized.parameterized.expand([
    ("placeholder", placeholders.PlaceholderSetting, 0),
    ("image_placeholder", placeholders.PlaceholderImageSetting, 1),
  ])
  def test_get_allowed_placeholders(
        self, test_case_name_suffix, placeholder_setting_type, expected_length):
    self.assertEqual(len(placeholder_setting_type.get_allowed_placeholders()), expected_length)
