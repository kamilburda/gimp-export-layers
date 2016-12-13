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

from ..lib import mock

from . import stubs_pgsetting
from . import stubs_pgsettinggroup
from .. import pgsetting
from .. import pgsettinggroup
from .. import pgsettingpersistor
from .. import pgconstants

#===============================================================================


class TestSettingGroupAddSettings(unittest.TestCase):
  
  def setUp(self):
    self.settings = pgsettinggroup.SettingGroup('main')
  
  def test_add_with_group_level_attributes(self):
    settings = pgsettinggroup.SettingGroup(name='main', setting_attributes={'pdb_type': None})
    settings.add([
      {
       'type': pgsetting.SettingTypes.boolean,
       'name': 'only_visible_layers',
       'default_value': False,
      },
      {
       'type': pgsetting.SettingTypes.boolean,
       'name': 'autocrop',
       'default_value': False,
      }
    ])
    
    self.assertEqual(settings['only_visible_layers'].pdb_type, None)
    self.assertEqual(settings['autocrop'].pdb_type, None)
  
  def test_add_with_group_level_attributes_overridden_by_setting_attributes(self):
    settings = pgsettinggroup.SettingGroup(name='main', setting_attributes={'pdb_type': None})
    settings.add([
      {
       'type': pgsetting.SettingTypes.boolean,
       'name': 'only_visible_layers',
       'default_value': False,
      },
      {
       'type': pgsetting.SettingTypes.boolean,
       'name': 'autocrop',
       'default_value': False,
       'pdb_type': pgsetting.SettingPdbTypes.int16
      }
    ])
    
    self.assertEqual(settings['only_visible_layers'].pdb_type, None)
    self.assertEqual(settings['autocrop'].pdb_type, pgsetting.SettingPdbTypes.int16)
  
  def test_add_with_group_level_attributes_overridden_by_subgroup_attributes(self):
    additional_settings = pgsettinggroup.SettingGroup(
      name='additional', setting_attributes={'pdb_type': pgsetting.SettingPdbTypes.int16})
    
    additional_settings.add([
        {
         'type': pgsetting.SettingTypes.boolean,
         'name': 'autocrop',
         'default_value': False
        }
    ])
    
    settings = pgsettinggroup.SettingGroup(
      name='main', setting_attributes={'pdb_type': None, 'display_name': "Setting name"})
    
    settings.add([
      {
       'type': pgsetting.SettingTypes.boolean,
       'name': 'only_visible_layers',
       'default_value': False,
      },
      additional_settings
    ])
    
    self.assertEqual(settings['only_visible_layers'].pdb_type, None)
    self.assertEqual(settings['additional/autocrop'].pdb_type, pgsetting.SettingPdbTypes.int16)
    self.assertEqual(settings['only_visible_layers'].display_name, "Setting name")
    self.assertEqual(settings['additional/autocrop'].display_name, "Autocrop")

  def test_add_raise_error_for_missing_type_attribute(self):
    with self.assertRaises(TypeError):
      self.settings.add([
        {
         'name': 'autocrop',
         'default_value': False,
        }
      ])
  
  def test_add_raise_error_for_missing_single_mandatory_attribute(self):
    with self.assertRaises(TypeError):
      self.settings.add([
        {
         'type': pgsetting.SettingTypes.boolean,
         'default_value': False,
        }
      ])
  
  def test_add_raise_error_for_missing_multiple_mandatory_attributes(self):
    with self.assertRaises(TypeError):
      self.settings.add([
        {
         'type': pgsetting.SettingTypes.enumerated,
        }
      ])
  
  def test_add_raise_error_for_non_existent_attribute(self):
    with self.assertRaises(TypeError):
      self.settings.add([
        {
         'type': pgsetting.SettingTypes.boolean,
         'name': 'autocrop',
         'default_value': False,
         'non_existent_attribute': None
        }
      ])
  
  def test_add_raise_error_if_name_already_exists(self):
    with self.assertRaises(KeyError):
      self.settings.add([
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
  
  def test_add_raise_error_if_setting_has_path_separator(self):
    with self.assertRaises(ValueError):
      self.settings.add([
        {
         'type': pgsetting.SettingTypes.boolean,
         'name': 'file/extension',
         'default_value': ""
        }
      ])
  

#===============================================================================


class TestSettingGroup(unittest.TestCase):
  
  def setUp(self):
    self.settings = stubs_pgsettinggroup.create_test_settings()
    
    self.first_plugin_run_setting_dict = {
      'type': pgsetting.SettingTypes.boolean,
      'name': 'first_plugin_run',
      'default_value': False}
    
    self.special_settings = pgsettinggroup.SettingGroup('special')
    self.special_settings.add([self.first_plugin_run_setting_dict])
  
  def test_get_setting_raise_error_if_invalid_name(self):
    with self.assertRaises(KeyError):
      self.settings['invalid_name']
  
  def test_add_setting(self):
    self.settings.add([
      {
       'type': pgsetting.SettingTypes.boolean,
       'name': 'autocrop',
       'default_value': False
      }
    ])
    
    self.assertIn('autocrop', self.settings)
    self.assertIsInstance(self.settings['autocrop'], pgsetting.BoolSetting)
  
  def test_add_existing_setting_group(self):
    self.settings.add([self.special_settings])
    
    self.assertIn('special', self.settings)
    self.assertEqual(self.settings['special'], self.special_settings)
  
  def test_add_settings_with_same_name_in_different_subgroups(self):
    main_settings = pgsettinggroup.SettingGroup('main')
    main_settings.add([self.first_plugin_run_setting_dict])
    
    self.settings.add([self.special_settings, main_settings])
    
    self.assertIn('first_plugin_run', self.special_settings)
    self.assertIn('first_plugin_run', main_settings)
    self.assertNotEqual(self.special_settings['first_plugin_run'], main_settings['first_plugin_run'])
  
  def test_add_setting_raise_error_if_name_already_exists(self):
    with self.assertRaises(KeyError):
      self.settings.add([
        {
         'type': pgsetting.SettingTypes.boolean,
         'name': 'file_extension',
         'default_value': ""
        }
      ])
  
  def test_add_setting_group_raise_error_if_name_already_exists(self):
    self.settings.add([self.special_settings])
    with self.assertRaises(KeyError):
      self.settings.add([self.special_settings])
  
  def test_remove_settings(self):
    self.settings.remove(['file_extension', 'only_visible_layers'])
    self.assertNotIn('file_extension', self.settings)
    self.assertNotIn('only_visible_layers', self.settings)
    self.assertIn('overwrite_mode', self.settings)
  
  def test_remove_setting_from_setting_group_and_then_setting_group(self):
    self.settings.add([self.special_settings])
    
    self.settings['special'].remove(['first_plugin_run'])
    self.assertNotIn('first_plugin_run', self.settings['special'])
    
    self.settings.remove(['special'])
    self.assertNotIn('special', self.settings)
  
  def test_remove_settings_raise_error_if_invalid_name(self):
    with self.assertRaises(KeyError):
      self.settings.remove(['file_extension', 'invalid_setting'])
  
  def test_remove_setting_raise_error_if_already_removed(self):
    self.settings.remove(['file_extension'])
    with self.assertRaises(KeyError):
      self.settings.remove(['file_extension'])
  
  def test_reset_settings_and_nested_groups_and_ignore_specified_settings(self):
    self.settings.add([self.special_settings])
    self.settings.set_ignore_tags({
      'file_extension': ['reset'],
      'overwrite_mode': ['reset', 'apply_gui_values_to_settings'],
    })
    
    self.settings['file_extension'].set_value("gif")
    self.settings['only_visible_layers'].set_value(True)
    self.settings['overwrite_mode'].set_item('skip')
    self.settings['special']['first_plugin_run'].set_value(True)
    
    self.settings.reset()
    
    self.assertEqual(self.settings['file_extension'].value, "gif")
    self.assertEqual(self.settings['overwrite_mode'].value, self.settings['overwrite_mode'].items['skip'])
    self.assertEqual(
      self.settings['only_visible_layers'].value, self.settings['only_visible_layers'].default_value)
    self.assertEqual(
      self.settings['special']['first_plugin_run'].value,
      self.settings['special']['first_plugin_run'].default_value)
  
  def test_reset_ignore_nested_group(self):
    self.settings.add([self.special_settings])
    self.settings.set_ignore_tags({'special': ['reset']})
    
    self.settings['special']['first_plugin_run'].set_value(True)
    
    self.settings.reset()
    
    self.assertNotEqual(
      self.settings['special']['first_plugin_run'].value,
      self.settings['special']['first_plugin_run'].default_value)
  

#===============================================================================


class TestSettingGroupHierarchical(unittest.TestCase):
  
  def setUp(self):
    self.settings = stubs_pgsettinggroup.create_test_settings_hierarchical()
  
  def test_get_settings_via_paths(self):
    self.assertEqual(self.settings['main/file_extension'], self.settings['main']['file_extension'])
    self.assertEqual(
      self.settings['advanced/only_visible_layers'], self.settings['advanced']['only_visible_layers'])
    self.assertEqual(
      self.settings['advanced/overwrite_mode'], self.settings['advanced']['overwrite_mode'])
    
    expert_settings = pgsettinggroup.SettingGroup('expert')
    expert_settings.add([
        {
         'type': pgsetting.SettingTypes.integer,
         'name': 'file_extension_strip_mode',
         'default_value': 0
        }
    ])
    
    self.settings['advanced'].add([expert_settings])
    
    self.assertEqual(
      self.settings['advanced/expert/file_extension_strip_mode'],
      self.settings['advanced']['expert']['file_extension_strip_mode'])
    
    with self.assertRaises(KeyError):
      self.settings['advanced/invalid_group/file_extension_strip_mode']
  
  def test_contains_via_paths(self):
    self.assertIn('main/file_extension', self.settings)
    self.assertNotIn('main/invalid_setting', self.settings)
  
  def test_iterate_all_no_ignore_tags(self):
    iterated_settings = list(self.settings.iterate_all())
    
    self.assertIn(self.settings['main']['file_extension'], iterated_settings)
    self.assertIn(self.settings['advanced']['only_visible_layers'], iterated_settings)
    self.assertIn(self.settings['advanced']['overwrite_mode'], iterated_settings)
  
  def test_iterate_all_with_ignore_tag_for_settings(self):
    self.settings['main'].set_ignore_tags({
      'file_extension': ['reset']
    })
    self.settings['advanced'].set_ignore_tags({
      'overwrite_mode': ['reset', 'apply_gui_values_to_settings']
    })
    
    iterated_settings = list(self.settings.iterate_all(['reset']))
    
    self.assertNotIn(self.settings['main']['file_extension'], iterated_settings)
    self.assertIn(self.settings['advanced']['only_visible_layers'], iterated_settings)
    self.assertNotIn(self.settings['advanced']['overwrite_mode'], iterated_settings)
  
  def test_iterate_all_with_ignore_tag_for_groups(self):
    self.settings.set_ignore_tags({
      'advanced': ['apply_gui_values_to_settings']
    })
    
    iterated_settings = list(self.settings.iterate_all(['apply_gui_values_to_settings']))
    
    self.assertIn(self.settings['main']['file_extension'], iterated_settings)
    self.assertNotIn(self.settings['advanced']['only_visible_layers'], iterated_settings)
    self.assertNotIn(self.settings['advanced']['overwrite_mode'], iterated_settings)
  
  def test_iterate_all_with_ignore_tag_multiple_times(self):
    self.settings['advanced'].set_ignore_tags({
      'only_visible_layers': ['apply_gui_values_to_settings']
    })
    self.settings['advanced'].set_ignore_tags({
      'overwrite_mode': ['apply_gui_values_to_settings']
    })
    
    iterated_settings = list(self.settings.iterate_all(['apply_gui_values_to_settings']))
    
    self.assertIn(self.settings['main']['file_extension'], iterated_settings)
    self.assertNotIn(self.settings['advanced']['only_visible_layers'], iterated_settings)
    self.assertNotIn(self.settings['advanced']['overwrite_mode'], iterated_settings)
  
  def test_iterate_all_with_ignore_tag_for_settings_with_paths(self):
    self.settings.set_ignore_tags({
      'main/file_extension': ['reset'],
      'advanced/overwrite_mode': ['reset', 'apply_gui_values_to_settings']
    })
    
    iterated_settings = list(self.settings.iterate_all(['reset']))
    
    self.assertNotIn(self.settings['main']['file_extension'], iterated_settings)
    self.assertIn(self.settings['advanced']['only_visible_layers'], iterated_settings)
    self.assertNotIn(self.settings['advanced']['overwrite_mode'], iterated_settings)
  
  def test_iterate_all_set_unset_ignore_tags(self):
    self.settings.set_ignore_tags({
      'main/file_extension': ['reset'],
      'advanced/overwrite_mode': ['reset', 'apply_gui_values_to_settings']
    })
    
    self.settings.unset_ignore_tags({
      'main/file_extension': ['reset']
    })
    
    settings_except_reset = list(self.settings.iterate_all(['reset']))
    self.assertIn(self.settings['main']['file_extension'], settings_except_reset)
    self.assertNotIn(self.settings['advanced']['overwrite_mode'], settings_except_reset)
    
    self.settings.unset_ignore_tags({
      'advanced/overwrite_mode': ['apply_gui_values_to_settings']
    })
    
    settings_except_apply_gui = list(self.settings.iterate_all(['apply_gui_values_to_settings']))
    self.assertIn(self.settings['main']['file_extension'], settings_except_apply_gui)
    self.assertIn(self.settings['advanced']['overwrite_mode'], settings_except_apply_gui)
    
    self.settings.set_ignore_tags({
      'main/file_extension': ['reset']
    })
    
    self.assertNotIn(self.settings['main']['file_extension'], list(self.settings.iterate_all(['reset'])))
  
  def test_iterate_all_unset_ignore_tags_invalid_tags(self):
    with self.assertRaises(ValueError):
      self.settings.unset_ignore_tags({
        'main/file_extension': ['reset']
      })
    
    self.settings.set_ignore_tags({
      'main/file_extension': ['reset']
    })
    
    with self.assertRaises(ValueError):
      self.settings.unset_ignore_tags({
        'main/file_extension': ['apply_gui_values_to_settings']
      })


#===============================================================================


@mock.patch(
  pgconstants.PYGIMPLIB_MODULE_PATH + '.pgsettingpersistor.SettingPersistor.save',
  return_value=(pgsettingpersistor.SettingPersistor.SUCCESS, ""))
@mock.patch(
  pgconstants.PYGIMPLIB_MODULE_PATH + '.pgsettingpersistor.SettingPersistor.load',
  return_value=(pgsettingpersistor.SettingPersistor.SUCCESS, ""))
class TestSettingGroupLoadSave(unittest.TestCase):
  
  def setUp(self):
    self.settings = stubs_pgsettinggroup.create_test_settings_load_save()
  
  def test_load_save_setting_sources_not_in_group_and_in_settings(self, mock_load, mock_save):
    settings = stubs_pgsettinggroup.create_test_settings()
    
    settings.load()
    self.assertEqual(mock_load.call_count, 1)
    self.assertEqual([settings['only_visible_layers']], mock_load.call_args[0][0])
    
    settings.save()
    self.assertEqual(mock_save.call_count, 1)
    self.assertEqual([settings['only_visible_layers']], mock_save.call_args[0][0])
  
  def test_load_save_setting_sources_in_group_and_in_settings(self, mock_load, mock_save):
    self.settings.load()
    self.assertEqual(mock_load.call_count, 3)
    self.assertEqual([self.settings['main/file_extension']], mock_load.call_args_list[0][0][0])
    self.assertEqual([self.settings['advanced/only_visible_layers']], mock_load.call_args_list[1][0][0])
    self.assertEqual([self.settings['advanced/autocrop']], mock_load.call_args_list[2][0][0])
    
    self.settings.save()
    self.assertEqual(mock_save.call_count, 3)
    self.assertEqual([self.settings['main/file_extension']], mock_save.call_args_list[0][0][0])
    self.assertEqual([self.settings['advanced/only_visible_layers']], mock_save.call_args_list[1][0][0])
    self.assertEqual([self.settings['advanced/autocrop']], mock_save.call_args_list[2][0][0])
  
  def test_load_save_return_statuses(self, mock_load, mock_save):
    load_save_calls_return_values = [
      (pgsettingpersistor.SettingPersistor.SUCCESS, ""), (pgsettingpersistor.SettingPersistor.SUCCESS, ""),
      (pgsettingpersistor.SettingPersistor.SUCCESS, "")]
    
    mock_load.side_effect = load_save_calls_return_values
    status, _unused = self.settings.load()
    self.assertEqual(status, pgsettingpersistor.SettingPersistor.SUCCESS)
    
    mock_save.side_effect = load_save_calls_return_values
    status, _unused = self.settings.save()
    self.assertEqual(status, pgsettingpersistor.SettingPersistor.SUCCESS)
    
    load_save_calls_return_values[1] = (pgsettingpersistor.SettingPersistor.NOT_ALL_SETTINGS_FOUND, "")
    mock_load.side_effect = load_save_calls_return_values
    status, _unused = self.settings.load()
    self.assertEqual(status, pgsettingpersistor.SettingPersistor.NOT_ALL_SETTINGS_FOUND)
    
    load_save_calls_return_values[1] = (pgsettingpersistor.SettingPersistor.NOT_ALL_SETTINGS_FOUND, "")
    mock_save.side_effect = load_save_calls_return_values
    status, _unused = self.settings.save()
    self.assertEqual(status, pgsettingpersistor.SettingPersistor.NOT_ALL_SETTINGS_FOUND)
    
    load_save_calls_return_values[2] = (pgsettingpersistor.SettingPersistor.READ_FAIL, "")
    mock_load.side_effect = load_save_calls_return_values
    status, _unused = self.settings.load()
    self.assertEqual(status, pgsettingpersistor.SettingPersistor.READ_FAIL)
    
    load_save_calls_return_values[2] = (pgsettingpersistor.SettingPersistor.WRITE_FAIL, "")
    mock_save.side_effect = load_save_calls_return_values
    status, _unused = self.settings.save()
    self.assertEqual(status, pgsettingpersistor.SettingPersistor.WRITE_FAIL)


#===============================================================================


class TestSettingGroupGui(unittest.TestCase):

  def setUp(self):
    self.settings = pgsettinggroup.SettingGroup('main')
    self.settings.add([
      {
        'type': stubs_pgsetting.SettingWithGuiStub,
        'name': 'file_extension',
        'default_value': 'bmp',
      },
      {
        'type': stubs_pgsetting.SettingWithGuiStub,
        'name': 'only_visible_layers',
        'default_value': False,
      },
    ])

  def test_initialize_gui_without_custom_gui(self):
    self.settings.initialize_gui()
    
    self.assertIs(type(self.settings['file_extension'].gui), stubs_pgsetting.CheckButtonPresenterStub)
    self.assertIs(type(self.settings['file_extension'].gui.element), stubs_pgsetting.CheckButtonStub)
    self.assertIs(type(self.settings['only_visible_layers'].gui), stubs_pgsetting.CheckButtonPresenterStub)
    self.assertIs(type(self.settings['only_visible_layers'].gui.element), stubs_pgsetting.CheckButtonStub)
  
  def test_initialize_gui_with_custom_gui(self):
    file_extension_widget = stubs_pgsetting.GuiWidgetStub("png")
    
    self.settings.initialize_gui(custom_gui={
      'file_extension': [stubs_pgsetting.SettingPresenterStub, file_extension_widget],
    })
    
    self.assertIs(type(self.settings['file_extension'].gui), stubs_pgsetting.SettingPresenterStub)
    self.assertIs(type(self.settings['file_extension'].gui.element), stubs_pgsetting.GuiWidgetStub)
    # It's "bmp", not "png", since the setting value overrides the initial GUI element value.
    self.assertEqual(file_extension_widget.value, "bmp")
    self.assertIs(type(self.settings['only_visible_layers'].gui), stubs_pgsetting.CheckButtonPresenterStub)
    self.assertIs(type(self.settings['only_visible_layers'].gui.element), stubs_pgsetting.CheckButtonStub)
  
  def test_apply_gui_values_to_settings_ignores_specified_settings(self):
    file_extension_widget = stubs_pgsetting.GuiWidgetStub(None)
    only_visible_layers_widget = stubs_pgsetting.GuiWidgetStub(None)
    self.settings['file_extension'].set_gui(stubs_pgsetting.SettingPresenterStub, file_extension_widget)
    self.settings['only_visible_layers'].set_gui(stubs_pgsetting.SettingPresenterStub, only_visible_layers_widget)
    
    file_extension_widget.set_value("gif")
    only_visible_layers_widget.set_value(True)
    
    self.settings.apply_gui_values_to_settings()
    
    self.assertEqual(self.settings['file_extension'].value, "gif")
    self.assertEqual(self.settings['only_visible_layers'].value, True)
