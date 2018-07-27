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
from export_layers.pygimplib import pgutils

from .. import operations

pygimplib.init()


class TestCreateOperation(unittest.TestCase):
  
  def test_create_operation(self):
    operation_setting = operations.create_operation(
      "autocrop", pgutils.empty_func, True, "Autocrop")
    
    self.assertEqual(operation_setting.name, "autocrop")
    self.assertEqual(operation_setting["function"].value, pgutils.empty_func)
    self.assertEqual(operation_setting["enabled"].value, True)
    self.assertEqual(operation_setting["display_name"].value, "Autocrop")
