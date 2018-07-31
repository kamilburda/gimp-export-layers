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

import parameterized

from export_layers import pygimplib
from export_layers.pygimplib import pgutils
from export_layers.pygimplib import pgsettinggroup

from .. import operations

pygimplib.init()


class TestCreateOperation(unittest.TestCase):
  
  def test_create_operation(self):
    operation = operations.create_operation(
      "autocrop", pgutils.empty_func, True, "Autocrop")
    
    self.assertEqual(operation.name, "autocrop")
    self.assertEqual(operation["function"].value, pgutils.empty_func)
    self.assertEqual(operation["enabled"].value, True)
    self.assertEqual(operation["display_name"].value, "Autocrop")
    self.assertSetEqual(operation.tags, set(["operation"]))
  
  def test_create_constraint(self):
    constraint = operations.create_constraint(
      "only_visible_layers", pgutils.empty_func, True, "Only Visible Layers")
    
    self.assertEqual(constraint.name, "only_visible_layers")
    self.assertEqual(constraint["function"].value, pgutils.empty_func)
    self.assertEqual(constraint["enabled"].value, True)
    self.assertEqual(constraint["display_name"].value, "Only Visible Layers")
    self.assertEqual(constraint["subfilter"].value, None)
    self.assertSetEqual(constraint.tags, set(["operation", "constraint"]))


class TestWalkOperations(unittest.TestCase):
  
  def setUp(self):
    self.operation_group = pgsettinggroup.SettingGroup("test_operations")
    self.operation_group.add([
      operations.create_operation(
        name="autocrop",
        function=pgutils.empty_func,
        enabled=True,
        display_name=_("Autocrop"),
      ),
      operations.create_operation(
        name="autocrop_background",
        function=pgutils.empty_func,
        enabled=False,
        display_name=_("Autocrop background layers"),
      ),
      operations.create_operation(
        name="autocrop_foreground",
        function=pgutils.empty_func,
        enabled=False,
        display_name=_("Autocrop foreground layers"),
      ),
    ])
  
  @parameterized.parameterized.expand([
    ("operations",
     "operation",
     ["autocrop",
      "autocrop_background",
      "autocrop_foreground"]),
    
    ("constraints",
     "constraint", []),
    
    ("enabled",
     "enabled",
     ["autocrop/enabled",
      "autocrop_background/enabled",
      "autocrop_foreground/enabled"]),
    
    ("nonexistent_setting",
     "nonexistent_setting", []),
  ])
  def test_walk_operations(
        self, test_case_name_suffix, setting_name, expected_setting_paths):
    self.assertListEqual(
      list(operations.walk_operations(self.operation_group, setting_name=setting_name)),
      [self.operation_group[path] for path in expected_setting_paths])
