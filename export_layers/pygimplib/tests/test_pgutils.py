# -*- coding: utf-8 -*-
#
# Copyright (C) 2014-2018 khalim19
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
This module tests the `pgsetting` and `pgsettingpresenter` modules.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import inspect
import unittest

from .. import pgutils

#===============================================================================


class TestGetModuleRoot(unittest.TestCase):

  def test_get_module_root(self):
    self.assertEqual(
      pgutils.get_module_root(
        "export_layers.pygimplib.tests.test_pgutils", "export_layers"),
      "export_layers")
    self.assertEqual(
      pgutils.get_module_root("export_layers.pygimplib.tests.test_pgutils", "pygimplib"),
      "export_layers.pygimplib")
    self.assertEqual(
      pgutils.get_module_root("export_layers.pygimplib.tests.test_pgutils", "tests"),
      "export_layers.pygimplib.tests")
    self.assertEqual(
      pgutils.get_module_root(
        "export_layers.pygimplib.tests.test_pgutils", "test_pgutils"),
      "export_layers.pygimplib.tests.test_pgutils")
  
  def test_get_module_root_nonexistent_name_component(self):
    self.assertEqual(
      pgutils.get_module_root(
        "export_layers.pygimplib.tests.test_pgutils", "nonexistent_name_component"),
      "export_layers.pygimplib.tests.test_pgutils")
    
    self.assertEqual(
      pgutils.get_module_root(
        "export_layers.pygimplib.tests.test_pgutils", ".pygimplib"),
      "export_layers.pygimplib.tests.test_pgutils")
    
    self.assertEqual(
      pgutils.get_module_root(
        "export_layers.pygimplib.tests.test_pgutils", "export_layers.pygimplib"),
      "export_layers.pygimplib.tests.test_pgutils")
  
  def test_get_module_root_empty_module_name(self):
    self.assertEqual(pgutils.get_module_root("", "pygimplib"), "")
    self.assertEqual(pgutils.get_module_root(".", "pygimplib"), ".")
  
  def test_get_module_root_empty_name_component(self):
    self.assertEqual(
      pgutils.get_module_root("export_layers.pygimplib.tests.test_pgutils", ""),
      "export_layers.pygimplib.tests.test_pgutils")
    
    self.assertEqual(
      pgutils.get_module_root("export_layers.pygimplib.tests.test_pgutils", "."),
      "export_layers.pygimplib.tests.test_pgutils")


class TestGetCurrentModuleFilepath(unittest.TestCase):
  
  def test_get_current_module_filepath(self):
    self.assertEqual(
      pgutils.get_current_module_filepath(),
      inspect.getfile(inspect.currentframe()))
