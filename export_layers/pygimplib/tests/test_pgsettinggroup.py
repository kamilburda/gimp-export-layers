#-------------------------------------------------------------------------------
#
# This file is part of pygimplib.
#
# Copyright (C) 2014 khalim19 <khalim19@gmail.com>
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
#-------------------------------------------------------------------------------

#===============================================================================

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division

str = unicode

#===============================================================================

from StringIO import StringIO

import unittest

import gimpenums

from .. import pgsetting
from .. import pgsettinggroup

#===============================================================================

LIB_NAME = '.'.join(__name__.split('.')[:-2])

#===============================================================================


class MockStringIO(StringIO):
  def read(self):
    return self.getvalue()


#===============================================================================


def create_test_settings():
  file_extension_display_name = "File extension"
  
  settings = pgsettinggroup.SettingGroup([
    {
      'type': pgsetting.SettingTypes.file_extension,
      'name': 'file_extension',
      'default_value': 'bmp',
      'resettable_by_group': False,
      'display_name': file_extension_display_name
    },
    {
      'type': pgsetting.SettingTypes.boolean,
      'name': 'ignore_invisible',
      'default_value': False,
      'display_name': "Ignore invisible",
      'description': (
        "If enabled, \"{0}\" is set to \"png\" for some reason. If disabled, \"{0}\" is set to \"jpg\"."
      ).format(file_extension_display_name)
    },
    {
      'type': pgsetting.SettingTypes.enumerated,
      'name': 'overwrite_mode',
      'default_value': 'rename_new',
      'resettable_by_group': False,
      'options': [('replace', "Replace"),
                  ('skip', "Skip"),
                  ('rename_new', "Rename new file"),
                  ('rename_existing', "Rename existing file")],
    },
  ])
  
  return settings


#===============================================================================


class TestSettingGroupCreation(unittest.TestCase):
  
  def test_raise_type_error_for_missing_type_attribute(self):
    with self.assertRaises(TypeError):
      pgsettinggroup.SettingGroup([
        {
         'name': 'file_extension',
         'default_value': 'bmp',
        }
      ])
  
  def test_raise_type_error_for_missing_single_mandatory_attribute(self):
    with self.assertRaises(TypeError):
      pgsettinggroup.SettingGroup([
        {
         'type': pgsetting.SettingTypes.file_extension,
         'default_value': 'bmp',
        }
      ])
  
  def test_raise_type_error_for_missing_multiple_mandatory_attributes(self):
    with self.assertRaises(TypeError):
      pgsettinggroup.SettingGroup([
        {
         'type': pgsetting.SettingTypes.enumerated,
        }
      ])
  
  def test_raise_type_error_for_non_existent_attribute(self):
    with self.assertRaises(TypeError):
      pgsettinggroup.SettingGroup([
        {
         'type': pgsetting.SettingTypes.file_extension,
         'name': 'file_extension',
         'default_value': 'bmp',
         'non_existent_attribute': None
        }
      ])


class TestSettingGroup(unittest.TestCase):
  
  def setUp(self):
    self.settings = create_test_settings()
      
  def test_get_setting_invalid_name(self):
    with self.assertRaises(KeyError):
      self.settings['invalid_name']


#===============================================================================


class TestPdbParamCreator(unittest.TestCase):
  
  def setUp(self):
    self.file_ext_setting = pgsetting.FileExtensionSetting("file_extension", "png",
                                                           display_name="File extension")
    self.unregistrable_setting = pgsetting.IntSetting("num_exported_layers", 0,
                                                      pdb_registration_mode=pgsetting.PdbRegistrationModes.not_registrable)
    self.settings = create_test_settings()
  
  def test_create_one_param_successfully(self):
    params = pgsettinggroup.PdbParamCreator.create_params(self.file_ext_setting)
    # There's only one PDB parameter returned.
    param = params[0]
    
    self.assertTrue(len(param), 3)
    self.assertEqual(param[0], gimpenums.PDB_STRING)
    self.assertEqual(param[1], "file_extension".encode())
    self.assertEqual(param[2], "File extension".encode())
  
  def test_create_params_invalid_argument(self):
    with self.assertRaises(TypeError):
      pgsettinggroup.PdbParamCreator.create_params([self.file_ext_setting])
  
  def test_create_multiple_params(self):
    params = pgsettinggroup.PdbParamCreator.create_params(self.file_ext_setting, self.settings)
    
    self.assertTrue(len(params), 1 + len(self.settings))
    
    self.assertEqual(params[0], (self.file_ext_setting.pdb_type, self.file_ext_setting.name.encode(),
                                 self.file_ext_setting.short_description.encode()))
    for param, setting in zip(params[1:], self.settings):
      self.assertEqual(param, (setting.pdb_type, setting.name.encode(),
                               setting.short_description.encode()))
  
  def test_create_params_with_unregistrable_setting(self):
    params = pgsettinggroup.PdbParamCreator.create_params(self.unregistrable_setting)
    self.assertEqual(params, [])
