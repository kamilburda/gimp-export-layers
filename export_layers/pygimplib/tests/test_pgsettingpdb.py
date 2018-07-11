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

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import unittest

from . import stubs_pgsettinggroup
from .. import pgconstants
from .. import pgsetting
from .. import pgsettingpdb


class TestPdbParamCreator(unittest.TestCase):
  
  def setUp(self):
    self.file_ext_setting = pgsetting.FileExtensionSetting(
      "file_extension", "png", display_name="File extension")
    self.unregistrable_setting = pgsetting.IntSetting(
      "num_exported_layers", 0, pdb_type=pgsetting.SettingPdbTypes.none)
    self.settings = stubs_pgsettinggroup.create_test_settings_hierarchical()
  
  def test_create_one_param_successfully(self):
    params = pgsettingpdb.PdbParamCreator.create_params(self.file_ext_setting)
    # There is only one PDB parameter returned.
    param = params[0]
    
    self.assertTrue(len(param), 3)
    self.assertEqual(param[0], pgsetting.SettingPdbTypes.string)
    self.assertEqual(
      param[1], "file_extension".encode(pgconstants.GIMP_CHARACTER_ENCODING))
    self.assertEqual(
      param[2], "File extension".encode(pgconstants.GIMP_CHARACTER_ENCODING))
  
  def test_create_params_invalid_argument(self):
    with self.assertRaises(TypeError):
      pgsettingpdb.PdbParamCreator.create_params([self.file_ext_setting])
  
  def test_create_multiple_params(self):
    params = pgsettingpdb.PdbParamCreator.create_params(
      self.file_ext_setting, self.settings)
    
    self.assertTrue(len(params), 1 + len(self.settings))
    self.assertEqual(
      params[0],
      (self.file_ext_setting.pdb_type,
       self.file_ext_setting.name.encode(pgconstants.GIMP_CHARACTER_ENCODING),
       self.file_ext_setting.description.encode(pgconstants.GIMP_CHARACTER_ENCODING)))
    
    for param, setting in zip(params[1:], self.settings.walk()):
      self.assertEqual(
        param,
        (setting.pdb_type,
         setting.name.encode(pgconstants.GIMP_CHARACTER_ENCODING),
         setting.description.encode(pgconstants.GIMP_CHARACTER_ENCODING)))
  
  def test_create_params_with_unregistrable_setting(self):
    params = pgsettingpdb.PdbParamCreator.create_params(self.unregistrable_setting)
    self.assertEqual(params, [])
  
  def test_list_param_values(self):
    param_values = pgsettingpdb.PdbParamCreator.list_param_values([self.settings])
    self.assertEqual(
      param_values[0], self.settings["main/file_extension"].value)
    self.assertEqual(
      param_values[1], self.settings["advanced/only_visible_layers"].value)
    self.assertEqual(
      param_values[2], self.settings["advanced/overwrite_mode"].value)

  def test_list_param_values_ignore_run_mode(self):
    param_values = pgsettingpdb.PdbParamCreator.list_param_values(
      [pgsetting.IntSetting("run_mode", 0), self.settings])
    self.assertEqual(len(param_values), len(list(self.settings.walk())))
