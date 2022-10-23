# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import unittest

import mock
import parameterized

from ... import utils as pgutils

from ...setting import group as group_
from ...setting import persistor as persistor_
from ...setting import presenter as presenter_
from ...setting import settings as settings_

from . import stubs_setting
from . import stubs_group


class TestGroupAttributes(unittest.TestCase):
  
  def setUp(self):
    self.settings = group_.Group(name='main')
  
  def test_invalid_group_name(self):
    with self.assertRaises(ValueError):
      group_.Group(name='main/additional')
    
    with self.assertRaises(ValueError):
      group_.Group(name='main.additional')
  
  def test_get_generated_display_name(self):
    self.assertEqual(self.settings.display_name, 'Main')
  
  def test_get_generated_description(self):
    settings = group_.Group(name='main', display_name='_Main')
    self.assertEqual(settings.description, 'Main')
  
  def test_get_custom_display_name_and_description(self):
    settings = group_.Group(
      name='main', display_name='_Main', description='My description')
    self.assertEqual(settings.display_name, '_Main')
    self.assertEqual(settings.description, 'My description')
  
  def test_get_non_existent_setting_name(self):
    with self.assertRaises(KeyError):
      unused_ = self.settings['invalid_name']


class TestGroupAddWithSettingDict(unittest.TestCase):
  
  def setUp(self):
    self.settings = group_.Group('main')
    self.setting_dict = {
      'type': settings_.SettingTypes.boolean,
      'name': 'use_layer_size',
      'default_value': False}
  
  def test_add(self):
    self.settings.add([self.setting_dict])
    
    self.assertIn('use_layer_size', self.settings)
    self.assertIsInstance(self.settings['use_layer_size'], settings_.BoolSetting)
    self.assertEqual(self.settings['use_layer_size'].value, False)
  
  def test_add_with_missing_type_attribute(self):
    del self.setting_dict['type']
    
    with self.assertRaises(TypeError):
      self.settings.add([self.setting_dict])
  
  def test_add_with_missing_single_required_attribute(self):
    del self.setting_dict['name']
    
    with self.assertRaises(TypeError):
      self.settings.add([self.setting_dict])
  
  def test_add_with_missing_multiple_required_attributes(self):
    del self.setting_dict['name']
    del self.setting_dict['default_value']
    
    with self.assertRaises(TypeError):
      self.settings.add([self.setting_dict])
  
  def test_add_with_invalid_setting_attribute(self):
    self.setting_dict['invalid_setting_attribute'] = None
    
    with self.assertRaises(TypeError):
      self.settings.add([self.setting_dict])
  
  def test_add_with_path_separator(self):
    self.setting_dict['name'] = 'use/layer/size'
    
    with self.assertRaises(ValueError):
      self.settings.add([self.setting_dict])
  
  def test_add_with_same_name_in_same_group(self):
    with self.assertRaises(ValueError):
      self.settings.add([self.setting_dict, self.setting_dict])
  
  def test_add_multiple_dicts_with_same_name_in_different_child_groups(self):
    special_settings = group_.Group('special')
    special_settings.add([self.setting_dict])
    
    main_settings = group_.Group('main')
    main_settings.add([self.setting_dict])
    
    self.settings.add([special_settings, main_settings])
    
    self.assertIn('use_layer_size', special_settings)
    self.assertIn('use_layer_size', main_settings)
    self.assertNotEqual(
      special_settings['use_layer_size'], main_settings['use_layer_size'])


class TestGroupAddFromDict(unittest.TestCase):
  
  def test_add_with_group_level_attributes(self):
    settings = group_.Group(name='main', setting_attributes={'pdb_type': None})
    settings.add([
      {
       'type': settings_.SettingTypes.boolean,
       'name': 'only_visible_layers',
       'default_value': False,
      },
      {
       'type': settings_.SettingTypes.boolean,
       'name': 'use_layer_size',
       'default_value': False,
      }
    ])
    
    self.assertEqual(settings['only_visible_layers'].pdb_type, None)
    self.assertEqual(settings['use_layer_size'].pdb_type, None)
  
  def test_add_with_group_level_attributes_overridden_by_setting_attributes(self):
    settings = group_.Group(name='main', setting_attributes={'pdb_type': None})
    settings.add([
      {
       'type': settings_.SettingTypes.boolean,
       'name': 'only_visible_layers',
       'default_value': False,
      },
      {
       'type': settings_.SettingTypes.boolean,
       'name': 'use_layer_size',
       'default_value': False,
       'pdb_type': settings_.SettingPdbTypes.int16
      }
    ])
    
    self.assertEqual(settings['only_visible_layers'].pdb_type, None)
    self.assertEqual(
      settings['use_layer_size'].pdb_type, settings_.SettingPdbTypes.int16)
  
  def test_add_with_group_level_attributes_overridden_by_child_group_attributes(self):
    additional_settings = group_.Group(
      name='additional', setting_attributes={'pdb_type': settings_.SettingPdbTypes.int16})
    
    additional_settings.add([
      {
       'type': settings_.SettingTypes.boolean,
       'name': 'use_layer_size',
       'default_value': False
      }
    ])
    
    settings = group_.Group(
      name='main', setting_attributes={'pdb_type': None, 'display_name': 'Setting name'})
    
    settings.add([
      {
       'type': settings_.SettingTypes.boolean,
       'name': 'only_visible_layers',
       'default_value': False,
      },
      additional_settings
    ])
    
    self.assertEqual(settings['only_visible_layers'].pdb_type, None)
    self.assertEqual(
      settings['additional/use_layer_size'].pdb_type, settings_.SettingPdbTypes.int16)
    self.assertEqual(settings['only_visible_layers'].display_name, 'Setting name')
    self.assertEqual(settings['additional/use_layer_size'].display_name, 'Use layer size')


class TestGroupCreateGroupsFromDict(unittest.TestCase):
  
  def test_create_groups_no_groups(self):
    settings = group_.create_groups({
      'name': 'main',
      'groups': None,
    })
    
    self.assertEqual(len(settings), 0)
  
  def test_create_groups(self):
    settings = group_.create_groups({
      'name': 'main',
      'groups': [
        {
          'name': 'procedures'
        },
        {
          'name': 'constraints',
          'groups': [
            {
              'name': 'include'
            }
          ]
        }
      ]
    })
    
    self.assertEqual(settings.name, 'main')
    self.assertEqual(len(settings), 2)
    self.assertIn('procedures', settings)
    self.assertIn('constraints', settings)
    self.assertIn('constraints/include', settings)
    self.assertIn('include', settings['constraints'])
    self.assertEqual(len(settings['constraints']), 1)
    self.assertNotIn('include', settings)
  
  def test_create_group_invalid_key(self):
    with self.assertRaises(TypeError):
      group_.create_groups({
        'name': 'main',
        'invalid_key': {},
      })


class TestGroup(unittest.TestCase):
  
  def setUp(self):
    self.settings = stubs_group.create_test_settings()
    
    self.first_plugin_run_setting_dict = {
      'type': settings_.SettingTypes.boolean,
      'name': 'first_plugin_run',
      'default_value': False}
    
    self.special_settings = group_.Group('special')
    self.special_settings.add([self.first_plugin_run_setting_dict])
  
  def test_add_same_setting_in_same_group(self):
    with self.assertRaises(ValueError):
      self.special_settings.add([self.special_settings['first_plugin_run']])
  
  def test_add_same_setting_in_different_child_groups(self):
    self.settings.add([self.special_settings['first_plugin_run'], self.special_settings])
    
    self.assertIn('first_plugin_run', self.settings)
    self.assertIn('first_plugin_run', self.special_settings)
    self.assertEqual(
      self.settings['first_plugin_run'], self.special_settings['first_plugin_run'])
  
  def test_add_group(self):
    self.settings.add([self.special_settings])
    
    self.assertIn('special', self.settings)
    self.assertEqual(self.settings['special'], self.special_settings)
  
  def test_add_same_group_in_same_parent_group(self):
    self.settings.add([self.special_settings])
    with self.assertRaises(ValueError):
      self.settings.add([self.special_settings])
  
  def test_add_same_group_as_child_of_itself(self):
    with self.assertRaises(ValueError):
      self.special_settings.add([self.special_settings])
  
  def test_add_different_groups_with_same_name_in_different_child_groups(self):
    main_settings = group_.Group('main')
    main_settings.add([self.special_settings])
    
    different_special_settings = group_.Group('special')
    self.settings.add([main_settings, different_special_settings])
    
    self.assertIn('special', self.settings)
    self.assertIn('special', main_settings)
    self.assertNotEqual(self.settings['special'], main_settings['special'])
  
  def test_add_same_group_in_different_child_groups(self):
    main_settings = group_.Group('main')
    main_settings.add([self.special_settings])
    
    self.settings.add([self.special_settings, main_settings])
    
    self.assertIn('special', self.settings)
    self.assertIn('special', main_settings)
    self.assertEqual(self.settings['special'], main_settings['special'])
  
  @parameterized.parameterized.expand([
    ('setting_exists_returns_setting_value',
     'file_extension',
     'jpg',
     'bmp'),
    
    ('setting_does_not_exist_returns_default_value',
     'invalid_setting',
     'jpg',
     'jpg'),
  ])
  def test_get_value(
        self,
        test_case_name_suffix,
        setting_name_or_path,
        default_value,
        expected_value):
    self.assertEqual(
      self.settings.get_value(setting_name_or_path, default_value), expected_value)
  
  def test_get_attributes(self):
    setting_attributes_and_values = self.settings.get_attributes([
      'file_extension',
      'file_extension.display_name',
    ])
    
    self.assertEqual(len(setting_attributes_and_values), 2)
    self.assertEqual(setting_attributes_and_values['file_extension'], 'bmp')
    self.assertEqual(
      setting_attributes_and_values['file_extension.display_name'], 'File extension')
  
  def test_get_attributes_getter_properties_only(self):
    setting_attributes_and_values = self.settings.get_attributes([
      'file_extension.name'])
    self.assertEqual(
      setting_attributes_and_values['file_extension.name'], 'file_extension')
  
  def test_get_attributes_nonexistent_attribute(self):
    with self.assertRaises(AttributeError):
      self.settings.get_attributes(['file_extension.nonexistent'])
  
  def test_get_attributes_nonexistent_setting(self):
    with self.assertRaises(KeyError):
      self.settings.get_attributes(['nonexistent_setting'])
  
  def test_get_attributes_invalid_number_of_periods(self):
    with self.assertRaises(ValueError):
      self.settings.get_attributes(['file_extension.value.value'])
  
  def test_get_values(self):
    setting_names_and_values = self.settings.get_values()
    
    self.assertEqual(len(setting_names_and_values), 3)
    self.assertEqual(
      setting_names_and_values['file_extension'],
      self.settings['file_extension'].default_value)
    self.assertEqual(
      setting_names_and_values['only_visible_layers'],
      self.settings['only_visible_layers'].default_value)
    self.assertEqual(
      setting_names_and_values['overwrite_mode'],
      self.settings['overwrite_mode'].default_value)
  
  def test_set_values(self):
    self.settings.set_values({
      'file_extension': 'jpg',
      'only_visible_layers': True
    })
    
    self.assertEqual(self.settings['file_extension'].value, 'jpg')
    self.assertEqual(self.settings['only_visible_layers'].value, True)
  
  def test_set_values_nonexistent_setting(self):
    with self.assertRaises(KeyError):
      self.settings.set_values({
        'nonexistent_setting': 'jpg',
      })
  
  def test_remove_settings(self):
    self.settings.remove(['file_extension', 'only_visible_layers'])
    self.assertNotIn('file_extension', self.settings)
    self.assertNotIn('only_visible_layers', self.settings)
    self.assertIn('overwrite_mode', self.settings)
  
  def test_remove_setting_from_group_and_then_group(self):
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
    self.settings['file_extension'].tags.add('ignore_reset')
    self.settings['overwrite_mode'].tags.update(
      ['ignore_reset', 'ignore_apply_gui_value_to_setting'])
    
    self.settings['file_extension'].set_value('gif')
    self.settings['only_visible_layers'].set_value(True)
    self.settings['overwrite_mode'].set_item('skip')
    self.settings['special/first_plugin_run'].set_value(True)
    
    self.settings.reset()
    
    self.assertEqual(self.settings['file_extension'].value, 'gif')
    self.assertEqual(
      self.settings['overwrite_mode'].value,
      self.settings['overwrite_mode'].items['skip'])
    self.assertEqual(
      self.settings['only_visible_layers'].value,
      self.settings['only_visible_layers'].default_value)
    self.assertEqual(
      self.settings['special/first_plugin_run'].value,
      self.settings['special/first_plugin_run'].default_value)
  
  def test_reset_ignore_nested_group(self):
    self.settings.add([self.special_settings])
    self.settings['special'].tags.add('ignore_reset')
    
    self.settings['special/first_plugin_run'].set_value(True)
    
    self.settings.reset()
    
    self.assertNotEqual(
      self.settings['special/first_plugin_run'].value,
      self.settings['special/first_plugin_run'].default_value)


class TestGroupHierarchical(unittest.TestCase):
  
  def setUp(self):
    self.settings = stubs_group.create_test_settings_hierarchical()
  
  def test_get_setting_via_paths(self):
    self.assertEqual(
      self.settings['main/file_extension'], self.settings['main']['file_extension'])
    self.assertEqual(
      self.settings['advanced/only_visible_layers'],
      self.settings['advanced']['only_visible_layers'])
    self.assertEqual(
      self.settings['advanced/overwrite_mode'],
      self.settings['advanced']['overwrite_mode'])
  
  def test_get_setting_via_paths_multiple_levels(self):
    expert_settings = group_.Group('expert')
    expert_settings.add([
        {
         'type': settings_.SettingTypes.integer,
         'name': 'file_extension_strip_mode',
         'default_value': 0
        }
    ])
    
    self.settings['advanced'].add([expert_settings])
    
    self.assertEqual(
      self.settings['advanced/expert/file_extension_strip_mode'],
      self.settings['advanced']['expert']['file_extension_strip_mode'])
    
  def test_get_setting_via_paths_invalid_group(self):
    with self.assertRaises(KeyError):
      unused_ = self.settings['advanced/invalid_group/file_extension_strip_mode']
  
  def test_get_values_returns_paths(self):
    setting_names_and_values = self.settings.get_values()
    
    self.assertEqual(len(setting_names_and_values), 3)
    self.assertEqual(
      setting_names_and_values['main/file_extension'],
      self.settings['main/file_extension'].default_value)
    self.assertEqual(
      setting_names_and_values['advanced/only_visible_layers'],
      self.settings['advanced/only_visible_layers'].default_value)
    self.assertEqual(
      setting_names_and_values['advanced/overwrite_mode'],
      self.settings['advanced/overwrite_mode'].default_value)
  
  def test_contains_via_paths(self):
    self.assertIn('main/file_extension', self.settings)
    self.assertNotIn('main/invalid_setting', self.settings)
  
  def test_walk(self):
    walked_settings = list(self.settings.walk())
    
    self.assertIn(self.settings['main/file_extension'], walked_settings)
    self.assertIn(self.settings['advanced/only_visible_layers'], walked_settings)
    self.assertIn(self.settings['advanced/overwrite_mode'], walked_settings)
  
  def test_walk_ignore_settings_with_tag(self):
    self.settings['main/file_extension'].tags.add('ignore_reset')
    self.settings['advanced/overwrite_mode'].tags.update(
      ['ignore_reset', 'ignore_apply_gui_value_to_setting'])
    
    walked_settings = list(self.settings.walk(
      include_setting_func=lambda setting: 'ignore_reset' not in setting.tags))
    
    self.assertNotIn(self.settings['main/file_extension'], walked_settings)
    self.assertIn(self.settings['advanced/only_visible_layers'], walked_settings)
    self.assertNotIn(self.settings['advanced/overwrite_mode'], walked_settings)
  
  def test_walk_ignore_settings_in_group_with_tag(self):
    self.settings['advanced'].tags.add('ignore_reset')
    
    walked_settings = list(self.settings.walk(
      include_setting_func=lambda setting: 'ignore_reset' not in setting.tags))
    
    self.assertIn(self.settings['main/file_extension'], walked_settings)
    self.assertNotIn(self.settings['advanced/only_visible_layers'], walked_settings)
    self.assertNotIn(self.settings['advanced/overwrite_mode'], walked_settings)
  
  def test_walk_include_groups(self):
    walked_settings = list(self.settings.walk(include_groups=True))
    
    self.assertIn(self.settings['main'], walked_settings)
    self.assertIn(self.settings['main/file_extension'], walked_settings)
    self.assertIn(self.settings['advanced'], walked_settings)
    self.assertIn(self.settings['advanced/only_visible_layers'], walked_settings)
    self.assertIn(self.settings['advanced/overwrite_mode'], walked_settings)
    self.assertNotIn(self.settings, walked_settings)
  
  def test_walk_ignore_settings_in_group_with_tag_include_groups(self):
    self.settings['advanced'].tags.add('ignore_reset')
    
    walked_settings = list(
      self.settings.walk(
        include_setting_func=lambda setting: 'ignore_reset' not in setting.tags,
        include_groups=True))
    
    self.assertIn(self.settings['main'], walked_settings)
    self.assertIn(self.settings['main/file_extension'], walked_settings)
    self.assertNotIn(self.settings['advanced'], walked_settings)
    self.assertNotIn(self.settings['advanced/only_visible_layers'], walked_settings)
    self.assertNotIn(self.settings['advanced/overwrite_mode'], walked_settings)
  
  def test_walk_include_if_parent_skipped(self):
    self.settings['advanced'].tags.add('ignore_reset')
    
    walked_settings = list(
      self.settings.walk(
        include_setting_func=lambda setting: 'ignore_reset' not in setting.tags,
        include_if_parent_skipped=True))
    
    self.assertNotIn(self.settings['main'], walked_settings)
    self.assertIn(self.settings['main/file_extension'], walked_settings)
    self.assertNotIn(self.settings['advanced'], walked_settings)
    self.assertIn(self.settings['advanced/only_visible_layers'], walked_settings)
    self.assertIn(self.settings['advanced/overwrite_mode'], walked_settings)
  
  def test_walk_include_if_parent_skipped_and_include_groups(self):
    self.settings['advanced'].tags.add('ignore_reset')
    
    walked_settings = list(
      self.settings.walk(
        include_setting_func=lambda setting: 'ignore_reset' not in setting.tags,
        include_groups=True,
        include_if_parent_skipped=True))
    
    self.assertIn(self.settings['main'], walked_settings)
    self.assertIn(self.settings['main/file_extension'], walked_settings)
    self.assertNotIn(self.settings['advanced'], walked_settings)
    self.assertIn(self.settings['advanced/only_visible_layers'], walked_settings)
    self.assertIn(self.settings['advanced/overwrite_mode'], walked_settings)
  
  def test_walk_with_callbacks(self):
    walked_settings, walk_callbacks = self._get_test_data_for_walking_group()
    
    for unused_ in self.settings.walk(include_groups=True, walk_callbacks=walk_callbacks):
      pass
    
    self.assertEqual(
      walked_settings,
      ['main', 'file_extension', 'main_end',
       'advanced', 'only_visible_layers', 'overwrite_mode', 'advanced_end'])
  
  def test_walk_with_callbacks_and_ignore_settings(self):
    self.settings['main'].tags.add('ignore_reset')
    self.settings['advanced/overwrite_mode'].tags.update(['ignore_reset'])
    
    walked_settings, walk_callbacks = self._get_test_data_for_walking_group()
    
    for unused_ in self.settings.walk(
          include_setting_func=lambda setting: 'ignore_reset' not in setting.tags,
          include_groups=True,
          walk_callbacks=walk_callbacks):
      pass
    
    self.assertEqual(walked_settings, ['advanced', 'only_visible_layers', 'advanced_end'])
  
  def test_walk_with_callbacks_empty_group(self):
    self.settings['main'].remove(['file_extension'])
    
    walked_settings, walk_callbacks = self._get_test_data_for_walking_group()
    
    for unused_ in self.settings.walk(include_groups=True, walk_callbacks=walk_callbacks):
      pass
    
    self.assertEqual(
      walked_settings,
      ['main', 'main_end',
       'advanced', 'only_visible_layers', 'overwrite_mode', 'advanced_end'])
  
  @staticmethod
  def _get_test_data_for_walking_group():
    walked_settings = []
    
    def _append_setting_name(setting):
      walked_settings.append(setting.name)
    
    def _append_setting_name_and_end_group_walk_indicator(setting):
      walked_settings.append(setting.name + '_end')
    
    walk_callbacks = group_.GroupWalkCallbacks()
    walk_callbacks.on_visit_setting = _append_setting_name
    walk_callbacks.on_visit_group = _append_setting_name
    walk_callbacks.on_end_group_walk = _append_setting_name_and_end_group_walk_indicator
    
    return walked_settings, walk_callbacks


@mock.patch(
  pgutils.get_pygimplib_module_path() + '.setting.persistor.Persistor.save',
  return_value=(persistor_.Persistor.SUCCESS, ''))
@mock.patch(
  pgutils.get_pygimplib_module_path() + '.setting.persistor.Persistor.load',
  return_value=(persistor_.Persistor.SUCCESS, ''))
class TestGroupLoadSave(unittest.TestCase):
  
  def setUp(self):
    self.settings = stubs_group.create_test_settings_load_save()
  
  def test_load_save_setting_sources_not_in_group_and_in_settings(
        self, mock_load, mock_save):
    settings = stubs_group.create_test_settings()
    
    settings.load()
    self.assertEqual(mock_load.call_count, 1)
    self.assertEqual([settings['only_visible_layers']], mock_load.call_args[0][0])
    
    settings.save()
    self.assertEqual(mock_save.call_count, 1)
    self.assertEqual([settings['only_visible_layers']], mock_save.call_args[0][0])
  
  @parameterized.parameterized.expand([
    ('default_sources',
     None,
     3,
     [['main/file_extension'],
      ['advanced/only_visible_layers'],
      ['advanced/use_layer_size']],
     [('session_source', 'persistent_source'),
      ('persistent_source', 'session_source'),
      ('session_source',)]),
    
    ('session_source_only',
     ['session_source'],
     1,
     [['main/file_extension', 'advanced/only_visible_layers', 'advanced/use_layer_size']],
     [('session_source',)]),
    
    ('persistent_source_only',
     ['persistent_source'],
     1,
     [['main/file_extension', 'advanced/only_visible_layers']],
     [('persistent_source',)]),
  ])
  def test_load_save_setting_sources_in_group_and_in_settings(
        self,
        mock_load,
        mock_save,
        test_case_name_suffix,
        setting_sources,
        load_save_call_count,
        setting_names_in_calls,
        expected_setting_sources_in_calls):
    self._test_load_save(
      test_case_name_suffix,
      setting_sources,
      load_save_call_count,
      setting_names_in_calls,
      expected_setting_sources_in_calls,
      'load',
      mock_load)
    
    self._test_load_save(
      test_case_name_suffix,
      setting_sources,
      load_save_call_count,
      setting_names_in_calls,
      expected_setting_sources_in_calls,
      'save',
      mock_save)
  
  def test_load_save_return_statuses(self, mock_load, mock_save):
    load_save_calls_return_values = [
      (persistor_.Persistor.SUCCESS, ''),
      (persistor_.Persistor.SUCCESS, ''),
      (persistor_.Persistor.SUCCESS, '')]
    
    mock_load.side_effect = load_save_calls_return_values
    status, unused_ = self.settings.load()
    self.assertEqual(status, persistor_.Persistor.SUCCESS)
    
    mock_save.side_effect = load_save_calls_return_values
    status, unused_ = self.settings.save()
    self.assertEqual(status, persistor_.Persistor.SUCCESS)
    
    load_save_calls_return_values[1] = (
      persistor_.Persistor.NOT_ALL_SETTINGS_FOUND, '')
    mock_load.side_effect = load_save_calls_return_values
    status, unused_ = self.settings.load()
    self.assertEqual(status, persistor_.Persistor.NOT_ALL_SETTINGS_FOUND)
    
    load_save_calls_return_values[1] = (
      persistor_.Persistor.NOT_ALL_SETTINGS_FOUND, '')
    mock_save.side_effect = load_save_calls_return_values
    status, unused_ = self.settings.save()
    self.assertEqual(status, persistor_.Persistor.NOT_ALL_SETTINGS_FOUND)
    
    load_save_calls_return_values[2] = (
      persistor_.Persistor.READ_FAIL, '')
    mock_load.side_effect = load_save_calls_return_values
    status, unused_ = self.settings.load()
    self.assertEqual(status, persistor_.Persistor.READ_FAIL)
    
    load_save_calls_return_values[2] = persistor_.Persistor.WRITE_FAIL, ''
    mock_save.side_effect = load_save_calls_return_values
    status, unused_ = self.settings.save()
    self.assertEqual(status, persistor_.Persistor.WRITE_FAIL)
  
  def _test_load_save(
        self,
        test_case_name_suffix,
        setting_sources,
        load_save_call_count,
        setting_names_in_calls,
        expected_setting_sources_in_calls,
        load_save_func_name,
        mock_object):
    getattr(self.settings, load_save_func_name)(setting_sources)
    
    self.assertEqual(mock_object.call_count, load_save_call_count)
    
    for i, (setting_names_per_call, setting_sources_per_call) in (
          enumerate(zip(setting_names_in_calls, expected_setting_sources_in_calls))):
      self.assertEqual(
        mock_object.call_args_list[i][0][0],
        [self.settings[name] for name in setting_names_per_call])
      self.assertEqual(
        mock_object.call_args_list[i][0][1],
        setting_sources_per_call)


class TestGroupGui(unittest.TestCase):

  def setUp(self):
    self.settings = group_.Group('main')
    self.settings.add([
      {
        'type': stubs_setting.SettingWithGuiStub,
        'name': 'file_extension',
        'default_value': 'bmp',
      },
      {
        'type': stubs_setting.SettingWithGuiStub,
        'name': 'only_visible_layers',
        'default_value': False,
      },
    ])
  
  def test_initialize_gui(self):
    self.settings.initialize_gui()
    
    self.assertIs(
      type(self.settings['file_extension'].gui),
      stubs_setting.CheckButtonPresenterStub)
    self.assertIs(
      type(self.settings['file_extension'].gui.element),
      stubs_setting.CheckButtonStub)
    self.assertIs(
      type(self.settings['only_visible_layers'].gui),
      stubs_setting.CheckButtonPresenterStub)
    self.assertIs(
      type(self.settings['only_visible_layers'].gui.element),
      stubs_setting.CheckButtonStub)

  def test_initialize_gui_ignores_specified_settings(self):
    self.settings['only_visible_layers'].tags.add('ignore_initialize_gui')
    self.settings.initialize_gui()
    
    self.assertIs(
      type(self.settings['file_extension'].gui),
      stubs_setting.CheckButtonPresenterStub)
    self.assertIs(
      type(self.settings['only_visible_layers'].gui),
      presenter_.NullPresenter)
  
  def test_initialize_gui_with_custom_gui(self):
    file_extension_widget = stubs_setting.GuiWidgetStub('png')
    
    self.settings.initialize_gui(custom_gui={
      'file_extension': [stubs_setting.PresenterStub, file_extension_widget]})
    
    self.assertIs(
      type(self.settings['file_extension'].gui), stubs_setting.PresenterStub)
    self.assertIs(
      type(self.settings['file_extension'].gui.element),
      stubs_setting.GuiWidgetStub)
    # The expected value is 'bmp', not 'png', since the setting value overrides
    # the initial GUI element value.
    self.assertEqual(file_extension_widget.value, 'bmp')
    self.assertIs(
      type(self.settings['only_visible_layers'].gui),
      stubs_setting.CheckButtonPresenterStub)
    self.assertIs(
      type(self.settings['only_visible_layers'].gui.element),
      stubs_setting.CheckButtonStub)
  
  def test_apply_gui_values_to_settings(self):
    file_extension_widget = stubs_setting.GuiWidgetStub(None)
    only_visible_layers_widget = stubs_setting.GuiWidgetStub(None)
    self.settings['file_extension'].set_gui(
      stubs_setting.PresenterStub, file_extension_widget)
    self.settings['only_visible_layers'].set_gui(
      stubs_setting.PresenterStub, only_visible_layers_widget)
    
    file_extension_widget.set_value('gif')
    only_visible_layers_widget.set_value(True)
    
    self.settings.apply_gui_values_to_settings()
    
    self.assertEqual(self.settings['file_extension'].value, 'gif')
    self.assertEqual(self.settings['only_visible_layers'].value, True)
