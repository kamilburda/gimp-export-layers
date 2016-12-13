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

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

str = unicode

import unittest

from . import stubs_pgsettinggroup
from .. import pgsetting
from .. import pgsettingpdb

#===============================================================================


class TestPdbParamCreator(unittest.TestCase):
  
  def setUp(self):
    self.file_ext_setting = pgsetting.FileExtensionSetting(
      "file_extension", "png", display_name="File extension")
    self.unregistrable_setting = pgsetting.IntSetting(
      "num_exported_layers", 0, pdb_type=pgsetting.SettingPdbTypes.none)
    self.settings = stubs_pgsettinggroup.create_test_settings_hierarchical()
  
  def test_create_one_param_successfully(self):
    params = pgsettingpdb.PdbParamCreator.create_params(self.file_ext_setting)
    # There's only one PDB parameter returned.
    param = params[0]
    
    self.assertTrue(len(param), 3)
    self.assertEqual(param[0], pgsetting.SettingPdbTypes.string)
    self.assertEqual(param[1], "file_extension".encode())
    self.assertEqual(param[2], "File extension".encode())
  
  def test_create_params_invalid_argument(self):
    with self.assertRaises(TypeError):
      pgsettingpdb.PdbParamCreator.create_params([self.file_ext_setting])
  
  def test_create_multiple_params(self):
    params = pgsettingpdb.PdbParamCreator.create_params(self.file_ext_setting, self.settings)
    
    self.assertTrue(len(params), 1 + len(self.settings))
    self.assertEqual(
      params[0],
      (self.file_ext_setting.pdb_type, self.file_ext_setting.name.encode(),
       self.file_ext_setting.description.encode()))
    
    for param, setting in zip(params[1:], self.settings.iterate_all()):
      self.assertEqual(param, (setting.pdb_type, setting.name.encode(), setting.description.encode()))
  
  def test_create_params_with_unregistrable_setting(self):
    params = pgsettingpdb.PdbParamCreator.create_params(self.unregistrable_setting)
    self.assertEqual(params, [])
  
  def test_list_param_values(self):
    param_values = pgsettingpdb.PdbParamCreator.list_param_values([self.settings])
    self.assertEqual(param_values[0], self.settings['main']['file_extension'].value)
    self.assertEqual(param_values[1], self.settings['advanced']['only_visible_layers'].value)
    self.assertEqual(param_values[2], self.settings['advanced']['overwrite_mode'].value)

  def test_list_param_values_ignore_run_mode(self):
    param_values = pgsettingpdb.PdbParamCreator.list_param_values(
      [pgsetting.IntSetting('run_mode', 0), self.settings])
    self.assertEqual(len(param_values), len(list(self.settings.iterate_all())))
