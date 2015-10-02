#-------------------------------------------------------------------------------
#
# This file is part of pygimplib.
#
# Copyright (C) 2014, 2015 khalim19 <khalim19@gmail.com>
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

from .test_pgsetting import MockGuiWidget, MockCheckbox
from .test_pgsetting import MockSettingPresenter, MockCheckboxPresenter
from .test_pgsetting import MockSettingWithGui

#===============================================================================

LIB_NAME = ".".join(__name__.split(".")[:-2])

#===============================================================================


class MockStringIO(StringIO):
  def read(self):
    return self.getvalue()


#===============================================================================


def create_test_settings():
  settings = pgsettinggroup.SettingGroup('main', [
    {
      'type': pgsetting.SettingTypes.file_extension,
      'name': 'file_extension',
      'default_value': 'bmp',
      'display_name': "File extension"
    },
    {
      'type': pgsetting.SettingTypes.boolean,
      'name': 'ignore_invisible',
      'default_value': False,
      'display_name': "Ignore invisible",
    },
    {
      'type': pgsetting.SettingTypes.enumerated,
      'name': 'overwrite_mode',
      'default_value': 'rename_new',
      'items': [('replace', "Replace"),
                ('skip', "Skip"),
                ('rename_new', "Rename new file"),
                ('rename_existing', "Rename existing file")],
     'error_messages': { 'invalid_value': "Invalid value. Something went wrong on our end... we are so sorry!" }
    },
  ])
  
  settings.set_ignore_tags({
    'file_extension': ['reset'],
    'overwrite_mode': ['reset', 'apply_gui_values_to_settings'],
  })
  
  return settings


def create_test_settings_hierarchical():
  main_settings = pgsettinggroup.SettingGroup('main', [
    {
      'type': pgsetting.SettingTypes.file_extension,
      'name': 'file_extension',
      'default_value': 'bmp',
      'display_name': "File extension"
    },
  ])
  
  advanced_settings = pgsettinggroup.SettingGroup('advanced', [
    {
      'type': pgsetting.SettingTypes.boolean,
      'name': 'ignore_invisible',
      'default_value': False,
      'display_name': "Ignore invisible",
    },
    {
      'type': pgsetting.SettingTypes.enumerated,
      'name': 'overwrite_mode',
      'default_value': 'rename_new',
      'items': [('replace', "Replace"),
                ('skip', "Skip"),
                ('rename_new', "Rename new file"),
                ('rename_existing', "Rename existing file")],
    },
  ])
  
  settings = pgsettinggroup.SettingGroup('settings', [main_settings, advanced_settings])
  
  return settings


#===============================================================================


class TestSettingGroupCreation(unittest.TestCase):
  
  def test_pass_existing_setting_group(self):
    special_settings = pgsettinggroup.SettingGroup('special', [
      {
       'type': pgsetting.SettingTypes.boolean,
       'name': 'first_plugin_run',
       'default_value': False
      }
    ])
    
    settings = pgsettinggroup.SettingGroup('main', [
      {
       'type': pgsetting.SettingTypes.boolean,
       'name': 'ignore_invisible',
       'default_value': False,
      },
      special_settings,
      {
        'type': pgsetting.SettingTypes.boolean,
        'name': 'autocrop',
        'default_value': False
      },
    ])
    
    self.assertIn('special', settings)
    self.assertEqual(settings['special'], special_settings)
  
  def test_raise_type_error_for_missing_type_attribute(self):
    with self.assertRaises(TypeError):
      pgsettinggroup.SettingGroup('main', [
        {
         'name': 'autocrop',
         'default_value': False,
        }
      ])
  
  def test_raise_type_error_for_missing_single_mandatory_attribute(self):
    with self.assertRaises(TypeError):
      pgsettinggroup.SettingGroup('main', [
        {
         'type': pgsetting.SettingTypes.boolean,
         'default_value': False,
        }
      ])
  
  def test_raise_type_error_for_missing_multiple_mandatory_attributes(self):
    with self.assertRaises(TypeError):
      pgsettinggroup.SettingGroup('main', [
        {
         'type': pgsetting.SettingTypes.enumerated,
        }
      ])
  
  def test_raise_type_error_for_non_existent_attribute(self):
    with self.assertRaises(TypeError):
      pgsettinggroup.SettingGroup('main', [
        {
         'type': pgsetting.SettingTypes.boolean,
         'name': 'autocrop',
         'default_value': False,
         'non_existent_attribute': None
        }
      ])
  
  def test_raise_key_error_if_name_already_exists(self):
    with self.assertRaises(KeyError):
      pgsettinggroup.SettingGroup('main', [
        {
         'type': pgsetting.SettingTypes.boolean,
         'name': 'autocrop',
         'default_value': False,
        },
        {
         'type': pgsetting.SettingTypes.boolean,
         'name': 'autocrop',
         'default_value': False,
        }
      ])


class TestSettingGroup(unittest.TestCase):
  
  def setUp(self):
    self.settings = create_test_settings()
    self.special_settings = pgsettinggroup.SettingGroup('special', [
      {
       'type': pgsetting.SettingTypes.boolean,
       'name': 'first_plugin_run',
       'default_value': False
      }
    ])
      
  def test_get_setting_raise_key_error_if_invalid_name(self):
    with self.assertRaises(KeyError):
      self.settings['invalid_name']
  
  def test_add_settings(self):
    self.settings.add([
      {
       'type': pgsetting.SettingTypes.boolean,
       'name': 'autocrop',
       'default_value': False
      },
      self.special_settings,             
    ])
    
    self.assertIn('special', self.settings)
    self.assertEqual(self.settings['special'], self.special_settings)
    self.assertIn('autocrop', self.settings)
    self.assertIsInstance(self.settings['autocrop'], pgsetting.BoolSetting)
  
  def test_add_setting_raise_key_error_if_name_already_exists(self):
    with self.assertRaises(KeyError):
      self.settings.add([
        {
         'type': pgsetting.SettingTypes.boolean,
         'name': 'file_extension',
         'default_value': ""
        }
      ])
    
  def test_add_nested_setting_group_raise_key_error_if_name_already_exists(self):
    self.settings.add([self.special_settings])
    with self.assertRaises(KeyError):
      self.settings.add([self.special_settings])
  
  def test_remove_settings(self):
    self.settings.remove(['file_extension', 'ignore_invisible'])
    self.assertNotIn('file_extension', self.settings)
    self.assertNotIn('ignore_invisible', self.settings)
    self.assertIn('overwrite_mode', self.settings)
  
  def test_remove_settings_nested_group(self):
    self.settings.add([self.special_settings])
    
    self.settings['special'].remove(['first_plugin_run'])
    self.assertNotIn('first_plugin_run', self.settings['special'])
    
    self.settings.remove(['special'])
    self.assertNotIn('special', self.settings)
  
  def test_remove_settings_raise_key_error_if_invalid_name(self):
    with self.assertRaises(KeyError):
      self.settings.remove(['file_extension', 'invalid_setting'])
  
  def test_remove_settings_raise_key_error_if_already_removed(self):
    self.settings.remove(['file_extension'])
    with self.assertRaises(KeyError):
      self.settings.remove(['file_extension'])
  
  def test_reset_settings_resets_nested_groups_and_ignores_specified_settings(self):
    self.settings.add([self.special_settings])
    
    self.settings['file_extension'].set_value("gif")
    self.settings['ignore_invisible'].set_value(True)
    self.settings['overwrite_mode'].set_value(self.settings['overwrite_mode'].items['skip'])
    self.settings['special']['first_plugin_run'].set_value(True)
    
    self.settings.reset()
    
    # `reset()` ignores 'file_extension' and 'overwrite_mode' 
    self.assertEqual(self.settings['file_extension'].value, "gif")
    self.assertEqual(self.settings['overwrite_mode'].value, self.settings['overwrite_mode'].items['skip'])
    self.assertEqual(self.settings['ignore_invisible'].value, self.settings['ignore_invisible'].default_value)
    self.assertEqual(self.settings['special']['first_plugin_run'].value,
                     self.settings['special']['first_plugin_run'].default_value)
  
  def test_reset_ignores_nested_group(self):
    self.settings.add([self.special_settings])
    self.settings.set_ignore_tags({ 'special': ['reset'] })
    
    self.settings['special']['first_plugin_run'].set_value(True)
    self.settings.reset()
    self.assertNotEqual(self.settings['special']['first_plugin_run'].value,
                        self.settings['special']['first_plugin_run'].default_value)


class TestSettingGroupIterateAll(unittest.TestCase):
  
  def setUp(self):
    self.settings = create_test_settings_hierarchical()
  
  def test_iterate_all_no_ignore_tags(self):
    self.settings = create_test_settings_hierarchical()
    iterated_settings = list(self.settings.iterate_all())
    
    self.assertIn(self.settings['main']['file_extension'], iterated_settings)
    self.assertIn(self.settings['advanced']['ignore_invisible'], iterated_settings)
    self.assertIn(self.settings['advanced']['overwrite_mode'], iterated_settings)
  
  def test_iterate_all_with_ignore_tag_for_settings(self):
    self.settings = create_test_settings_hierarchical()
    
    self.settings['main'].set_ignore_tags({
      'file_extension': ['reset']
    })
    self.settings['advanced'].set_ignore_tags({
      'overwrite_mode': ['reset', 'apply_gui_values_to_settings']
    })
    
    iterated_settings = list(self.settings.iterate_all(['reset']))
    
    self.assertNotIn(self.settings['main']['file_extension'], iterated_settings)
    self.assertIn(self.settings['advanced']['ignore_invisible'], iterated_settings)
    self.assertNotIn(self.settings['advanced']['overwrite_mode'], iterated_settings)
  
  def test_iterate_all_with_ignore_tag_for_groups(self):
    self.settings = create_test_settings_hierarchical()
    
    self.settings.set_ignore_tags({
      'advanced': ['apply_gui_values_to_settings']
    })
    
    iterated_settings = list(self.settings.iterate_all(['apply_gui_values_to_settings']))
    
    self.assertIn(self.settings['main']['file_extension'], iterated_settings)
    self.assertNotIn(self.settings['advanced']['ignore_invisible'], iterated_settings)
    self.assertNotIn(self.settings['advanced']['overwrite_mode'], iterated_settings)


class TestSettingGroupGui(unittest.TestCase):

  def setUp(self):
    self.settings = pgsettinggroup.SettingGroup('main', [
      {
        'type': MockSettingWithGui,
        'name': 'file_extension',
        'default_value': 'bmp',
      },
      {
        'type': MockSettingWithGui,
        'name': 'ignore_invisible',
        'default_value': False,
      },
    ])

  def test_initialize_gui_without_custom_gui(self):
    self.settings.initialize_gui()
    
    self.assertIs(type(self.settings['file_extension'].gui), MockCheckboxPresenter)
    self.assertIs(type(self.settings['file_extension'].gui.element), MockCheckbox)
    self.assertIs(type(self.settings['ignore_invisible'].gui), MockCheckboxPresenter)
    self.assertIs(type(self.settings['ignore_invisible'].gui.element), MockCheckbox)
  
  def test_initialize_gui_with_custom_gui(self):
    file_extension_widget = MockGuiWidget("png")
    
    self.settings.initialize_gui(custom_gui={
      'file_extension': [MockSettingPresenter, file_extension_widget],
    })
    
    self.assertIs(type(self.settings['file_extension'].gui), MockSettingPresenter)
    self.assertIs(type(self.settings['file_extension'].gui.element), MockGuiWidget)
    # It's "bmp", not "png", since the setting value overrides the initial GUI element value.
    self.assertEqual(file_extension_widget.value, "bmp")
    self.assertIs(type(self.settings['ignore_invisible'].gui), MockCheckboxPresenter)
    self.assertIs(type(self.settings['ignore_invisible'].gui.element), MockCheckbox)
  
  def test_apply_gui_values_to_settings_ignores_specified_settings(self):
    file_extension_widget = MockGuiWidget(None)
    ignore_invisible_widget = MockGuiWidget(None)
    self.settings['file_extension'].create_gui(MockSettingPresenter, file_extension_widget)
    self.settings['ignore_invisible'].create_gui(MockSettingPresenter, ignore_invisible_widget)
    
    file_extension_widget.set_value("gif")
    ignore_invisible_widget.set_value(True)
    
    self.settings.apply_gui_values_to_settings()
    
    self.assertEqual(self.settings['file_extension'].value, "gif")
    self.assertEqual(self.settings['ignore_invisible'].value, True)
    

#===============================================================================


class TestPdbParamCreator(unittest.TestCase):
  
  def setUp(self):
    self.file_ext_setting = pgsetting.FileExtensionSetting(
      "file_extension", "png", display_name="File extension")
    self.unregistrable_setting = pgsetting.IntSetting(
      "num_exported_layers", 0, pdb_type=pgsetting.SettingPdbTypes.none)
    self.settings = create_test_settings_hierarchical()
  
  def test_create_one_param_successfully(self):
    params = pgsettinggroup.PdbParamCreator.create_params(self.file_ext_setting)
    # There's only one PDB parameter returned.
    param = params[0]
    
    self.assertTrue(len(param), 3)
    self.assertEqual(param[0], pgsetting.SettingPdbTypes.string)
    self.assertEqual(param[1], "file_extension".encode())
    self.assertEqual(param[2], "File extension".encode())
  
  def test_create_params_invalid_argument(self):
    with self.assertRaises(TypeError):
      pgsettinggroup.PdbParamCreator.create_params([self.file_ext_setting])
  
  def test_create_multiple_params(self):
    params = pgsettinggroup.PdbParamCreator.create_params(self.file_ext_setting, self.settings)
    
    self.assertTrue(len(params), 1 + len(self.settings))
    
    self.assertEqual(params[0], (self.file_ext_setting.pdb_type, self.file_ext_setting.name.encode(),
                                 self.file_ext_setting.description.encode()))
    for param, setting in zip(params[1:], self.settings.iterate_all()):
      self.assertEqual(param, (setting.pdb_type, setting.name.encode(),
                               setting.description.encode()))
  
  def test_create_params_with_unregistrable_setting(self):
    params = pgsettinggroup.PdbParamCreator.create_params(self.unregistrable_setting)
    self.assertEqual(params, [])
  
  def test_list_param_values(self):
    param_values = pgsettinggroup.PdbParamCreator.list_param_values([self.settings])
    self.assertEqual(param_values[0], self.settings['main']['file_extension'].value)
    self.assertEqual(param_values[1], self.settings['advanced']['ignore_invisible'].value)
    self.assertEqual(param_values[2], self.settings['advanced']['overwrite_mode'].value)

  def test_list_param_values_ignore_run_mode(self):
    param_values = pgsettinggroup.PdbParamCreator.list_param_values(
      [pgsetting.IntSetting('run_mode', 0), self.settings])
    self.assertEqual(len(param_values), len(list(self.settings.iterate_all())))
    
  