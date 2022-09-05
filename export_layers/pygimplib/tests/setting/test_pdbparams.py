# -*- coding: utf-8 -*-
#
# Copyright (C) 2014-2019 khalim19
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

from ... import constants as pgconstants

from ...setting import pdbparams as pdbparams_
from ...setting import settings as settings_

from . import stubs_group


class TestCreateParams(unittest.TestCase):
  
  def setUp(self):
    self.file_ext_setting = settings_.FileExtensionSetting(
      'file_extension', default_value='png', display_name='File extension')
    self.unregistrable_setting = settings_.IntSetting(
      'num_exported_layers', default_value=0, pdb_type=settings_.SettingPdbTypes.none)
    self.coordinates_setting = settings_.ArraySetting(
      'coordinates',
      default_value=(1.0, 5.0, 10.0),
      element_type=settings_.SettingTypes.float,
      element_default_value=0.0)
    
    self.settings = stubs_group.create_test_settings_hierarchical()
  
  def test_create_params_single_param(self):
    params = pdbparams_.create_params(self.file_ext_setting)
    param = params[0]
    
    self.assertTrue(len(param), 3)
    self.assertEqual(param[0], settings_.SettingPdbTypes.string)
    self.assertEqual(
      param[1], 'file-extension'.encode(pgconstants.GIMP_CHARACTER_ENCODING))
    self.assertEqual(
      param[2], 'File extension'.encode(pgconstants.GIMP_CHARACTER_ENCODING))
  
  def test_create_params_invalid_argument(self):
    with self.assertRaises(TypeError):
      pdbparams_.create_params([self.file_ext_setting])
  
  def test_create_multiple_params(self):
    params = pdbparams_.create_params(
      self.file_ext_setting, self.coordinates_setting, self.settings)
    
    self.assertTrue(len(params), 3 + len(self.settings))
    
    self.assertEqual(
      params[0],
      (self.file_ext_setting.pdb_type,
       self.file_ext_setting.pdb_name.encode(pgconstants.GIMP_CHARACTER_ENCODING),
       self.file_ext_setting.description.encode(pgconstants.GIMP_CHARACTER_ENCODING)))
    
    # Array length parameter
    self.assertEqual(params[1][0], settings_.SettingPdbTypes.int32)
    
    self.assertEqual(
      params[2],
      (self.coordinates_setting.pdb_type,
       self.coordinates_setting.pdb_name.encode(pgconstants.GIMP_CHARACTER_ENCODING),
       self.coordinates_setting.description.encode(pgconstants.GIMP_CHARACTER_ENCODING)))
    
    for param, setting in zip(params[3:], self.settings.walk()):
      self.assertEqual(
        param,
        (setting.pdb_type,
         setting.pdb_name.encode(pgconstants.GIMP_CHARACTER_ENCODING),
         setting.description.encode(pgconstants.GIMP_CHARACTER_ENCODING)))
  
  def test_create_params_with_unregistrable_setting(self):
    params = pdbparams_.create_params(self.unregistrable_setting)
    self.assertEqual(params, [])


class TestIterArgs(unittest.TestCase):
  
  def setUp(self):
    self.settings = stubs_group.create_test_settings_hierarchical()
    self.args = ['png', False, 'replace']
  
  def test_iter_args_number_of_args_equals_number_of_settings(self):
    self.assertListEqual(
      list(pdbparams_.iter_args(self.args, list(self.settings.walk()))),
      self.args)
  
  def test_iter_args_number_of_args_is_less_than_number_of_settings(self):
    self.assertListEqual(
      list(pdbparams_.iter_args(self.args[:-1], list(self.settings.walk()))),
      self.args[:-1])
  
  def test_iter_args_number_of_args_is_more_than_number_of_settings(self):
    self.assertListEqual(
      list(pdbparams_.iter_args(self.args, list(self.settings.walk())[:-1])),
      self.args[:-1])
  
  def test_iter_args_with_array_setting(self):
    coordinates_setting = settings_.ArraySetting(
      'coordinates',
      default_value=(1.0, 5.0, 10.0),
      element_type=settings_.SettingTypes.float,
      element_default_value=0.0)
    
    self.settings.add([coordinates_setting])
    self.args.extend([3, (20.0, 50.0, 40.0)])
    
    self.assertListEqual(
      list(pdbparams_.iter_args(self.args, list(self.settings.walk()))),
      self.args[:-2] + [self.args[-1]])


class TestListParamValues(unittest.TestCase):
  
  def setUp(self):
    self.settings = stubs_group.create_test_settings_hierarchical()
  
  def test_list_param_values(self):
    param_values = pdbparams_.list_param_values([self.settings])
    self.assertEqual(
      param_values[0], self.settings['main/file_extension'].value)
    self.assertEqual(
      param_values[1], self.settings['advanced/only_visible_layers'].value)
    self.assertEqual(
      param_values[2], self.settings['advanced/overwrite_mode'].value)

  def test_list_param_values_ignore_run_mode(self):
    param_values = pdbparams_.list_param_values(
      [settings_.IntSetting('run_mode', 0), self.settings])
    self.assertEqual(len(param_values), len(list(self.settings.walk())))
