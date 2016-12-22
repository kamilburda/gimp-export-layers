# -*- coding: utf-8 -*-
#
# This file is part of pygimplib.
#
# Copyright (C) 2014-2016 khalim19 <khalim19@gmail.com>
#
# pygimplib is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pygimplib is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pygimplib.  If not, see <http://www.gnu.org/licenses/>.
#

"""
This module tests the `pgsetting` and `pgsettingpresenter` modules.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import future.standard_library
future.standard_library.install_aliases()

from future.builtins import *

import unittest

from .. import pgutils

#===============================================================================


class TestGetModuleRoot(unittest.TestCase):

  def test_get_module_root(self):
    self.assertEqual(
      pgutils.get_module_root("export_layers.pygimplib.tests.test_pgutils", "export_layers"),
      "export_layers")
    self.assertEqual(
      pgutils.get_module_root("export_layers.pygimplib.tests.test_pgutils", "pygimplib"),
      "export_layers.pygimplib")
    self.assertEqual(
      pgutils.get_module_root("export_layers.pygimplib.tests.test_pgutils", "tests"),
      "export_layers.pygimplib.tests")
    self.assertEqual(
      pgutils.get_module_root("export_layers.pygimplib.tests.test_pgutils", "test_pgutils"),
      "export_layers.pygimplib.tests.test_pgutils")
  
  def test_get_module_root_nonexistent_path_component(self):
    self.assertEqual(
      pgutils.get_module_root("export_layers.pygimplib.tests.test_pgutils", "nonexistent_path_component"),
      "export_layers.pygimplib.tests.test_pgutils")
    
    self.assertEqual(
      pgutils.get_module_root(
        "export_layers.pygimplib.tests.test_pgutils", ".pygimplib"),
      "export_layers.pygimplib.tests.test_pgutils")
    
    self.assertEqual(
      pgutils.get_module_root(
        "export_layers.pygimplib.tests.test_pgutils", "export_layers.pygimplib"),
      "export_layers.pygimplib.tests.test_pgutils")
  
  def test_get_module_root_empty_module_path(self):
    self.assertEqual(pgutils.get_module_root("", "pygimplib"), "")
    self.assertEqual(pgutils.get_module_root(".", "pygimplib"), ".")
  
  def test_get_module_root_empty_path_component(self):
    self.assertEqual(
      pgutils.get_module_root("export_layers.pygimplib.tests.test_pgutils", ""),
      "export_layers.pygimplib.tests.test_pgutils")
    
    self.assertEqual(
      pgutils.get_module_root("export_layers.pygimplib.tests.test_pgutils", "."),
      "export_layers.pygimplib.tests.test_pgutils")

