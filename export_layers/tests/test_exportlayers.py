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

from gimp import pdb
import gimpenums

from export_layers import pygimplib
from export_layers.pygimplib import pgoperations
from export_layers.pygimplib import pgutils

from .. import config
config.init()

from .. import builtin_operations
from .. import exportlayers
from .. import operations
from .. import settings_plugin

pygimplib.init()


class TestExportLayersInitialOperations(unittest.TestCase):
  
  @classmethod
  def setUpClass(cls):
    cls.image = pdb.gimp_image_new(1, 1, gimpenums.RGB)
  
  @classmethod
  def tearDownClass(cls):
    pdb.gimp_image_delete(cls.image)
  
  def test_export_added_operations_are_executed_first(self):
    settings = settings_plugin.create_settings()
    
    settings["special/image"].set_value(self.image)
    settings["main/file_extension"].set_value("xcf")
    
    layer_exporter = exportlayers.LayerExporter(
      settings["special/run_mode"].value,
      settings["special/image"].value,
      settings["main"])
    
    operations.add(settings["main/operations"], "ignore_layer_modes")
    
    layer_exporter.add_operation(
      pgutils.empty_func, [builtin_operations.BUILTIN_OPERATIONS_GROUP])
    
    layer_exporter.export(processing_groups=[])
    
    added_operation_items = layer_exporter.operation_executor.list_operations(
      group=builtin_operations.BUILTIN_OPERATIONS_GROUP)
    
    self.assertEqual(len(added_operation_items), 3)
    
    initial_executor = added_operation_items[1]
    self.assertIsInstance(initial_executor, pgoperations.OperationExecutor)
    
    operations_in_initial_executor = initial_executor.list_operations(
      group=builtin_operations.BUILTIN_OPERATIONS_GROUP)
    self.assertEqual(len(operations_in_initial_executor), 1)
    self.assertEqual(operations_in_initial_executor[0], (pgutils.empty_func, (), {}))
