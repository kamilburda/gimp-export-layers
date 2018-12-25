# -*- coding: utf-8 -*-
#
# This file is part of Export Layers.
#
# Copyright (C) 2013-2018 khalim19 <khalim19@gmail.com>
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

from export_layers import pygimplib

from export_layers.pygimplib.tests import stubs_gimp

from .. import placeholders

pygimplib.init()


class TestGetReplacedArgsAndKwargs(unittest.TestCase):
  
  def test_get_replaced_args_and_kwargs(self):
    image = stubs_gimp.ImageStub()
    layer = stubs_gimp.LayerStub()
    layer_exporter = object()
    
    args = [
      placeholders.PLACEHOLDERS["current_image"],
      placeholders.PLACEHOLDERS["current_layer"],
      "some_other_arg"]
    kwargs = {
      "run_mode": 0,
      "image": placeholders.PLACEHOLDERS["current_image"],
      "layer": placeholders.PLACEHOLDERS["current_layer"],
    }
    
    new_args, new_kwargs = placeholders.get_replaced_args_and_kwargs(
      args, kwargs, image, layer, layer_exporter)
    
    self.assertListEqual(new_args, [image, layer, "some_other_arg"])
    self.assertDictEqual(new_kwargs, {"run_mode": 0, "image": image, "layer": layer})
