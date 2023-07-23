# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import unittest

from ... import utils as pgutils

from ...setting import pdbparams as pdbparams_
from ...setting import settings as settings_

from . import stubs_group


class TestCreateParams(unittest.TestCase):
  
  def setUp(self):
    self.file_ext_setting = settings_.FileExtensionSetting(
      'file_extension', default_value='png', display_name='File extension')
    self.unregistrable_setting = settings_.IntSetting(
      'num_exported_items', default_value=0, pdb_type=settings_.SettingPdbTypes.none)
    self.coordinates_setting = settings_.ArraySetting(
      'coordinates',
      default_value=(1.0, 5.0, 10.0),
      element_type='float',
      element_default_value=0.0)
    
    self.settings = stubs_group.create_test_settings_hierarchical()
  
  def test_create_params_single_param(self):
    params = pdbparams_.create_params(self.file_ext_setting)
    param = params[0]
    
    self.assertTrue(len(param), 3)
    self.assertEqual(param[0], settings_.SettingPdbTypes.string)
    self.assertEqual(
      param[1], pgutils.safe_encode_gimp('file-extension'))
    self.assertEqual(
      param[2], pgutils.safe_encode_gimp('File extension'))
  
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
       pgutils.safe_encode_gimp(self.file_ext_setting.pdb_name),
       pgutils.safe_encode_gimp(self.file_ext_setting.description)))
    
    # Array length parameter
    self.assertEqual(params[1][0], settings_.SettingPdbTypes.int32)
    
    self.assertEqual(
      params[2],
      (self.coordinates_setting.pdb_type,
       pgutils.safe_encode_gimp(self.coordinates_setting.pdb_name),
       pgutils.safe_encode_gimp(self.coordinates_setting.description)))
    
    for param, setting in zip(params[3:], self.settings.walk()):
      self.assertEqual(
        param,
        (setting.pdb_type,
         pgutils.safe_encode_gimp(setting.pdb_name),
         pgutils.safe_encode_gimp(setting.description)))
  
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
      element_type='float',
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
    self.assertEqual(param_values[0], self.settings['main/file_extension'].value)
    self.assertEqual(param_values[1], self.settings['advanced/flatten'].value)
    self.assertEqual(param_values[2], self.settings['advanced/overwrite_mode'].value)

  def test_list_param_values_ignore_run_mode(self):
    param_values = pdbparams_.list_param_values([settings_.IntSetting('run_mode'), self.settings])
    self.assertEqual(len(param_values), len(list(self.settings.walk())))
