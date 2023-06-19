# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import io
import unittest

import mock

from ... import utils as pgutils

from ...setting import group as group_
from ...setting import settings as settings_
from ...setting import sources as sources_

from .. import stubs_gimp
from . import stubs_group


def _test_settings_for_read_write():
  settings = group_.create_groups({
    'name': 'all_settings',
    'groups': [
      {
        'name': 'main',
        'setting_attributes': {'gui_type': None},
      },
      {
        'name': 'special',
        'setting_attributes': {'gui_type': None},
      },
    ],
  })
  
  settings['main'].add([
    {
      'type': 'str',
      'name': 'file_extension',
      'default_value': 'png',
    },
  ])
  
  procedures = group_.create_groups({
    'name': 'procedures',
    'groups': [
      {
        'name': 'use_layer_size',
        'setting_attributes': {'gui_type': None},
      },
      {
        'name': 'insert_background_layers',
        'setting_attributes': {'gui_type': None},
      },
    ]
  })
  
  procedures['use_layer_size'].add([
    {
      'type': 'bool',
      'name': 'enabled',
      'default_value': True,
    },
    group_.Group(name='arguments', setting_attributes={'gui_type': None}),
  ])
  
  procedures['insert_background_layers'].add([
    {
      'type': 'bool',
      'name': 'enabled',
      'default_value': True,
    },
    group_.Group(name='arguments', setting_attributes={'gui_type': None}),
  ])
  
  procedures['insert_background_layers/arguments'].add([
    {
      'type': 'str',
      'name': 'tag',
      'default_value': 'background',
    }
  ])
  
  settings['main'].add([procedures])
  
  constraints = group_.Group(name='constraints', setting_attributes={'gui_type': None})
  
  settings['main'].add([constraints])
  
  settings['special'].add([
    {
      'type': 'bool',
      'name': 'first_plugin_run',
      'default_value': False,
    },
  ])
  
  settings.add([
    {
      'type': 'str',
      'name': 'standalone_setting',
      'default_value': 'something',
      'gui_type': None,
    }
  ])
  
  return settings


def _test_data_for_read_write():
  return [
    {
      'name': 'all_settings',
      'settings': [
        {
          'name': 'main',
          'settings': [
            {
              'type': 'string',
              'name': 'file_extension',
              'value': 'png',
              'default_value': 'png',
              'gui_type': None,
            },
            {
              'name': 'procedures',
              'settings': [
                {
                  'name': 'use_layer_size',
                  'settings': [
                    {
                      'type': 'bool',
                      'name': 'enabled',
                      'value': True,
                      'default_value': True,
                      'gui_type': None,
                    },
                    {
                      'name': 'arguments',
                      'settings': [],
                    },
                  ],
                },
                {
                  'name': 'insert_background_layers',
                  'settings': [
                    {
                      'type': 'bool',
                      'name': 'enabled',
                      'value': True,
                      'default_value': True,
                      'gui_type': None,
                    },
                    {
                      'name': 'arguments',
                      'settings': [
                        {
                          'type': 'string',
                          'name': 'tag',
                          'value': 'background',
                          'default_value': 'background',
                          'gui_type': None,
                        },
                      ],
                    },
                  ],
                },
              ],
            },
            {
              'name': 'constraints',
              'settings': [],
            },
          ],
        },
        {
          'name': 'special',
          'settings': [
            {
              'type': 'bool',
              'name': 'first_plugin_run',
              'value': False,
              'default_value': False,
              'gui_type': None,
            },
          ],
        },
        {
          'type': 'string',
          'name': 'standalone_setting',
          'value': 'something',
          'default_value': 'something',
          'gui_type': None,
        },
      ],
    },
  ]


class _StubSource(sources_.Source):
  
  def __init__(self, source_name, source_type):
    super().__init__(source_name, source_type)
    
    self.data = []
  
  def clear(self):
    pass
  
  def has_data(self):
    return False
  
  def read_data_from_source(self):
    return self.data
  
  def write_data_to_source(self, data):
    pass


class TestSourceRead(unittest.TestCase):

  def setUp(self):
    self.source_name = 'test_settings'
    self.source = _StubSource(self.source_name, 'persistent')
    
    self.settings = _test_settings_for_read_write()
    
    self.maxDiff = None

  def test_read(self):
    self.source.data = _test_data_for_read_write()
    
    self.source.data[0]['settings'][0]['settings'][0]['value'] = 'jpg'
    self.source.data[0]['settings'][0]['settings'][1]['settings'][0][
      'settings'][0]['value'] = False
    self.source.data[0]['settings'][2]['value'] = 'something_else'
    
    expected_setting_values = {
      setting.get_path(): setting.value for setting in self.settings.walk()}
    expected_setting_values['all_settings/main/file_extension'] = 'jpg'
    expected_setting_values['all_settings/main/procedures/use_layer_size/enabled'] = False
    expected_setting_values['all_settings/standalone_setting'] = 'something_else'
    
    self.source.read([self.settings])
    
    for setting in self.settings.walk():
      self.assertEqual(setting.value, expected_setting_values[setting.get_path()])
  
  def test_read_specific_settings(self):
    self.source.data = _test_data_for_read_write()
    
    self.source.data[0]['settings'][0]['settings'][0]['value'] = 'jpg'
    self.source.data[0]['settings'][0]['settings'][1]['settings'][1][
      'settings'][0]['value'] = False
    self.source.data[0]['settings'][0]['settings'][1]['settings'][1][
      'settings'][1]['settings'][0]['value'] = 'foreground'
    self.source.data[0]['settings'][2]['value'] = 'something_else'
    
    expected_setting_values = {
      setting.get_path(): setting.value for setting in self.settings.walk()}
    expected_setting_values[
      'all_settings/main/procedures/insert_background_layers/enabled'] = False
    expected_setting_values[
      'all_settings/main/procedures/insert_background_layers/arguments/tag'] = 'foreground'
    expected_setting_values['all_settings/standalone_setting'] = 'something_else'
    
    self.source.read([self.settings['main/procedures'], self.settings['standalone_setting']])
    
    for setting in self.settings.walk():
      self.assertEqual(setting.value, expected_setting_values[setting.get_path()])
  
  def test_read_ignores_non_value_attributes_for_existing_settings(self):
    self.source.data = _test_data_for_read_write()
    
    self.source.data[0]['settings'][0]['settings'][0]['value'] = 'jpg'
    self.source.data[0]['settings'][0]['settings'][0]['default_value'] = 'gif'
    self.source.data[0]['settings'][0]['settings'][0]['description'] = 'some description'
    
    self.source.read([self.settings['main/file_extension']])
    
    self.assertEqual(self.settings['main/file_extension'].value, 'jpg')
    self.assertEqual(self.settings['main/file_extension'].default_value, 'png')
    self.assertEqual(self.settings['main/file_extension'].description, 'File extension')
  
  def test_read_not_all_settings_found(self):
    self.source.data = _test_data_for_read_write()
    
    # 'main/procedures/use_layer_size/arguments'
    del self.source.data[0]['settings'][0]['settings'][1]['settings'][0]['settings'][1]
    # 'main/procedures/use_layer_size/enabled'
    del self.source.data[0]['settings'][0]['settings'][1]['settings'][0]['settings'][0]
    # 'main/procedures/insert_background_layers'
    del self.source.data[0]['settings'][0]['settings'][1]['settings'][1]
    # 'main/constraints'
    del self.source.data[0]['settings'][0]['settings'][2]
    # 'main/file_extension'
    del self.source.data[0]['settings'][0]['settings'][0]
    # 'special'
    del self.source.data[0]['settings'][1]
    
    self.source.read(
      [self.settings['main/file_extension'],
       self.settings['main/procedures/insert_background_layers'],
       self.settings['main/procedures/use_layer_size']])
    
    self.assertListEqual(
      self.source.settings_not_found,
      [self.settings['main/file_extension'],
       self.settings['main/procedures/insert_background_layers'],
       # Missing settings and empty groups must be expanded.
       self.settings['main/procedures/use_layer_size/enabled'],
       self.settings['main/procedures/use_layer_size/arguments']])
    
    # Test if `settings_not_found` is reset on each call to `read()`
    self.source.read([self.settings['main/constraints']])
    
    self.assertListEqual(self.source.settings_not_found, [self.settings['main/constraints']])
  
  def test_read_creates_new_child_groups_and_settings_if_missing(self):
    self.source.data = _test_data_for_read_write()
    
    # Add 'main/procedures/use_layer_size/arguments/tag'
    tag_argument = {
      'type': 'string',
      'name': 'tag',
      'value': 'foreground',
      'default_value': 'background',
    }
    self.source.data[0]['settings'][0]['settings'][1]['settings'][0][
      'settings'][1]['settings'].append(tag_argument)
    
    # Add 'main/constraints/visible'
    visible_constraint = {
      'name': 'visible',
      'setting_attributes': {'gui_type': None},
      'settings': [
        {
          'type': 'bool',
          'name': 'enabled',
          'value': False,
          'default_value': True,
        },
        {
          'name': 'arguments',
          'setting_attributes': {'gui_type': None},
          'settings': [
            {
              'type': 'string',
              'name': 'tag',
              'value': 'foreground',
              'default_value': 'background',
            },
          ],
        },
      ],
    }
    self.source.data[0]['settings'][0]['settings'][2]['settings'].append(visible_constraint)
    
    expected_num_settings_and_groups = len(list(self.settings.walk(include_groups=True))) + 5
    
    self.source.read([self.settings])
    
    self.assertEqual(
      len(list(self.settings.walk(include_groups=True))), expected_num_settings_and_groups)
    self.assertDictEqual(
      self.settings['main/procedures/use_layer_size/arguments/tag'].to_dict(),
      {
        'type': 'string',
        'name': 'tag',
        'value': 'foreground',
        'default_value': 'background',
        'gui_type': None,
      })
    self.assertDictEqual(
      self.settings['main/constraints/visible/enabled'].to_dict(),
      {
        'type': 'bool',
        'name': 'enabled',
        'value': False,
        'default_value': True,
        'gui_type': None,
      })
    self.assertDictEqual(
      self.settings['main/constraints/visible/arguments/tag'].to_dict(),
      {
        'type': 'string',
        'name': 'tag',
        'value': 'foreground',
        'default_value': 'background',
        'gui_type': None,
      })
  
  def test_read_invalid_setting_value_set_to_default_value(self):
    setting_dict = {
      'name': 'some_number',
      'default_value': 2,
      'min_value': 0,
    }
    
    setting = settings_.IntSetting(**setting_dict)
    setting.set_value(5)
    
    setting_dict['type'] = 'int'
    setting_dict['value'] = -1
        
    self.source.data = [setting_dict]
    
    self.source.read([setting])
    
    self.assertEqual(
      setting.value,
      setting.default_value)
  
  def test_read_raises_error_if_list_expected_but_not_found(self):
    self.source.data = [
      {
        'name': 'all_settings',
        'settings': {'name': 'file_extension_not_inside_list', 'type': 'string', 'value': 'png'}
      }
    ]
    
    with self.assertRaises(sources_.SourceInvalidFormatError):
      self.source.read([self.settings])
  
  def test_read_raises_error_if_dict_expected_but_not_found(self):
    self.source.data = [
      {
        'name': 'all_settings',
        'settings': [[{'name': 'file_extension_not_inside_list', 'type': 'string', 'value': 'png'}]]
      }
    ]
    
    with self.assertRaises(sources_.SourceInvalidFormatError):
      self.source.read([self.settings])
  
  def test_read_raises_error_if_dict_is_missing_name(self):
    self.source.data = [
      {
        'name': 'all_settings',
        'settings': [{'type': 'string', 'value': 'png'}]
      }
    ]
    
    with self.assertRaises(sources_.SourceInvalidFormatError):
      self.source.read([self.settings])
  
  def test_read_raises_error_if_dict_is_missing_value(self):
    self.source.data = [
      {
        'name': 'all_settings',
        'settings': [{'name': 'file_extension', 'type': 'string'}]
      }
    ]
    
    with self.assertRaises(sources_.SourceInvalidFormatError):
      self.source.read([self.settings])
  
  def test_read_raises_error_if_dict_is_missing_settings(self):
    self.source.data = [
      {
        'name': 'all_settings',
      }
    ]
    
    with self.assertRaises(sources_.SourceInvalidFormatError):
      self.source.read([self.settings])
  
  def test_read_raises_error_if_dict_has_both_value_and_settings(self):
    self.source.data = [
      {
        'name': 'all_settings',
        'settings': [{'name': 'file_extension', 'type': 'string', 'value': 'png'}],
        'value': 'png',
      }
    ]
    
    with self.assertRaises(sources_.SourceInvalidFormatError):
      self.source.read([self.settings])
  
  def test_read_raises_error_if_dict_has_value_but_object_is_group(self):
    self.source.data = [
      {
        'name': 'all_settings',
        'settings': [
          {
            'type': 'string',
            'name': 'main',
            'value': 'png',
          },
        ],
      }
    ]
    
    with self.assertRaises(sources_.SourceInvalidFormatError):
      self.source.read([self.settings])
  
  def test_read_raises_error_if_dict_has_settings_but_object_is_setting(self):
    self.source.data = [
      {
        'name': 'all_settings',
        'settings': [
          {
            'name': 'main',
            'settings': [
              {
                'name': 'file_extension',
                'settings': [
                  {
                    'type': 'string',
                    'name': 'some_setting',
                    'value': 'png',
                  }
                ],
              },
            ]
          },
        ],
      }
    ]
    
    with self.assertRaises(sources_.SourceInvalidFormatError):
      self.source.read([self.settings])


class TestSourceWrite(unittest.TestCase):
  
  def setUp(self):
    self.source_name = 'test_settings'
    self.source = _StubSource(self.source_name, 'persistent')
    
    self.settings = _test_settings_for_read_write()
    
    self.maxDiff = None
  
  def test_write_empty_data(self):
    expected_data = _test_data_for_read_write()
    
    self.source.write([self.settings])
    
    self.assertListEqual(self.source.data, expected_data)
  
  def test_write_modifies_existing_data(self):
    expected_data = _test_data_for_read_write()
    
    self.settings['main/file_extension'].set_value('jpg')
    self.settings['main/procedures/use_layer_size/enabled'].set_value(False)
    self.settings['standalone_setting'].set_value('something_else')
    
    expected_data[0]['settings'][0]['settings'][0]['value'] = 'jpg'
    expected_data[0]['settings'][0]['settings'][1]['settings'][0]['settings'][0]['value'] = False
    expected_data[0]['settings'][2]['value'] = 'something_else'
    
    self.source.data = _test_data_for_read_write()
    self.source.write([self.settings])
    
    self.assertListEqual(self.source.data, expected_data)
  
  def test_write_modifies_only_selected_settings(self):
    expected_data = _test_data_for_read_write()
    
    self.settings['main/file_extension'].set_value('jpg')
    self.settings['main/procedures/use_layer_size/enabled'].set_value(False)
    self.settings['main/procedures/insert_background_layers/enabled'].set_value(False)
    self.settings['standalone_setting'].set_value('something_else')
    
    expected_data[0]['settings'][0]['settings'][1]['settings'][0]['settings'][0]['value'] = False
    expected_data[0]['settings'][0]['settings'][1]['settings'][1]['settings'][0]['value'] = False
    expected_data[0]['settings'][2]['value'] = 'something_else'
    
    self.source.data = _test_data_for_read_write()
    self.source.write([self.settings['main/procedures'], self.settings['standalone_setting']])
    
    self.assertListEqual(self.source.data, expected_data)
  
  def test_write_adds_groups_which_are_not_present_in_source(self):
    expected_data = _test_data_for_read_write()
    
    # Keep only 'main/procedures/use_layer_size/enabled' and 'standalone_setting'
    del expected_data[0]['settings'][0]['settings'][1]['settings'][0]['settings'][1]
    del expected_data[0]['settings'][0]['settings'][1]['settings'][1]
    del expected_data[0]['settings'][0]['settings'][2]
    del expected_data[0]['settings'][0]['settings'][0]
    del expected_data[0]['settings'][1]
    
    self.source.write(
      [self.settings['main/procedures/use_layer_size/enabled'],
       self.settings['standalone_setting']])
    
    self.assertListEqual(self.source.data, expected_data)
  
  def test_write_adds_settings_to_existing_groups(self):
    expected_data = _test_data_for_read_write()
    
    new_setting = {
      'type': 'string',
      'name': 'origin',
    }
    
    expected_new_setting_dict = {
      'type': 'string',
      'name': 'origin',
      'value': 'builtin',
      'gui_type': None,
    }
    
    self.settings['main/procedures/use_layer_size/arguments'].add([new_setting])
    self.settings['main/procedures/use_layer_size/arguments/origin'].set_value('builtin')
    
    expected_data[0]['settings'][0]['settings'][1]['settings'][0]['settings'][1][
      'settings'].append(expected_new_setting_dict)
    
    self.source.write([self.settings])
    
    self.assertListEqual(self.source.data, expected_data)
  
  def test_write_multiple_settings_separately(self):
    expected_data = _test_data_for_read_write()
    
    expected_data[0]['settings'][0]['settings'][0]['value'] = 'jpg'
    expected_data[0]['settings'][2]['value'] = 'something_else'
    
    self.settings['main/file_extension'].set_value('jpg')
    
    self.source.write([self.settings])
    
    self.settings['standalone_setting'].set_value('something_else')
    
    self.source.write([self.settings['standalone_setting']])
    
    self.assertListEqual(self.source.data, expected_data)
  
  def test_write_raises_error_if_list_expected_but_not_found(self):
    self.source.data = {'source_name': []}
    
    with self.assertRaises(sources_.SourceInvalidFormatError):
      self.source.write([self.settings])
  
  def test_write_raises_error_if_dict_expected_but_not_found(self):
    self.source.data = [[{'source_name': []}]]
    
    with self.assertRaises(sources_.SourceInvalidFormatError):
      self.source.write([self.settings])


@mock.patch(
  pgutils.get_pygimplib_module_path() + '.setting.sources.gimpshelf.shelf',
  new_callable=stubs_gimp.ShelfStub)
class TestGimpShelfSource(unittest.TestCase):
  
  @mock.patch(
    pgutils.get_pygimplib_module_path() + '.setting.sources.gimpshelf.shelf',
    new=stubs_gimp.ShelfStub())
  def setUp(self):
    self.source_name = 'test_settings'
    self.source = sources_.GimpShelfSource(self.source_name)
    self.settings = stubs_group.create_test_settings()
  
  def test_write_read(self, mock_session_source):
    self.settings['file_extension'].set_value('png')
    self.settings['flatten'].set_value(True)
    
    self.source.write([self.settings])
    
    self.settings['file_extension'].reset()
    self.settings['flatten'].reset()
    
    self.source.read([self.settings])
    
    self.assertEqual(self.settings['file_extension'].value, 'png')
    self.assertEqual(self.settings['flatten'].value, True)
  
  def test_clear(self, mock_session_source):
    self.source.write([self.settings])
    self.source.clear()
    
    with self.assertRaises(sources_.SourceNotFoundError):
      self.source.read([self.settings])
  
  def test_has_data_with_no_data(self, mock_session_source):
    self.assertFalse(self.source.has_data())
  
  def test_has_data_with_data(self, mock_session_source):
    self.source.write([self.settings['file_extension']])
    self.assertTrue(self.source.has_data())


@mock.patch(
  pgutils.get_pygimplib_module_path() + '.setting.sources.gimp',
  new_callable=stubs_gimp.GimpModuleStub)
class TestGimpParasiteSource(unittest.TestCase):
  
  @mock.patch(
    pgutils.get_pygimplib_module_path() + '.setting.sources.gimp.directory',
    new='gimp_directory')
  def setUp(self):
    self.source_name = 'test_settings'
    self.source = sources_.GimpParasiteSource(self.source_name)
    self.settings = stubs_group.create_test_settings()
  
  def test_write_read(self, mock_persistent_source):
    self.settings['file_extension'].set_value('jpg')
    self.settings['flatten'].set_value(True)
    
    self.source.write([self.settings])
    
    self.settings['file_extension'].reset()
    self.settings['flatten'].reset()
    
    self.source.read([self.settings])
    
    self.assertEqual(self.settings['file_extension'].value, 'jpg')
    self.assertEqual(self.settings['flatten'].value, True)
  
  def test_read_source_not_found(self, mock_persistent_source):
    with self.assertRaises(sources_.SourceNotFoundError):
      self.source.read([self.settings])
  
  def test_read_settings_invalid_format(self, mock_persistent_source):
    self.source.write([self.settings])
    
    # Simulate formatting error
    parasite = sources_.gimp.parasite_find(self.source_name)
    parasite.data = parasite.data[:-1]
    sources_.gimp.parasite_attach(parasite)
    
    with self.assertRaises(sources_.SourceInvalidFormatError):
      self.source.read([self.settings])
  
  def test_clear(self, mock_persistent_source):
    self.source.write([self.settings])
    self.source.clear()
    
    with self.assertRaises(sources_.SourceNotFoundError):
      self.source.read([self.settings])
  
  def test_has_data_with_no_data(self, mock_persistent_source):
    self.assertFalse(self.source.has_data())
  
  def test_has_data_with_data(self, mock_persistent_source):
    self.source.write([self.settings['file_extension']])
    self.assertTrue(self.source.has_data())


class _FileSourceTests(object):
  
  def __init__(self, source_name, filepath, source_class):
    self._source_name = source_name
    self._filepath = filepath
    self._source_class = source_class
  
  def test_write_read(self, mock_os_path_isfile, mock_io_open):
    self._set_up_mock_open(mock_io_open)
    
    self.settings['file_extension'].set_value('jpg')
    self.settings['flatten'].set_value(True)
    
    self.source.write([self.settings])
    
    mock_os_path_isfile.return_value = True
    self.source.read([self.settings])
    
    self.assertEqual(self.settings['file_extension'].value, 'jpg')
    self.assertEqual(self.settings['flatten'].value, True)
  
  def test_write_multiple_settings_separately(self, mock_os_path_isfile, mock_io_open):
    self._set_up_mock_open(mock_io_open)
    
    self.settings['file_extension'].set_value('jpg')
    
    self.source.write([self.settings['file_extension']])
    
    self.settings['flatten'].set_value(True)
    
    mock_os_path_isfile.return_value = True
    self.source.write([self.settings['flatten']])
    
    self.source.read([self.settings['file_extension']])
    self.source.read([self.settings['flatten']])
    
    self.assertEqual(self.settings['file_extension'].value, 'jpg')
    self.assertEqual(self.settings['flatten'].value, True)
    
    self.settings['file_extension'].set_value('gif')
    
    self.source.write([self.settings['file_extension']])
    self.source.read([self.settings['file_extension']])
    
    self.assertEqual(self.settings['file_extension'].value, 'gif')
    self.assertEqual(self.settings['flatten'].value, True)
  
  def test_write_retains_other_source_names(self, mock_os_path_isfile, mock_io_open):
    self._set_up_mock_open(mock_io_open)
    
    source_2 = self._source_class('test_settings_2', self.filepath)
    self.source.write_data_to_source = mock.Mock(wraps=self.source.write_data_to_source)
    source_2.write_data_to_source = mock.Mock(wraps=source_2.write_data_to_source)
    
    self.settings['file_extension'].set_value('jpg')
    self.settings['flatten'].set_value(True)
    
    self.source.write([self.settings['file_extension']])
    mock_os_path_isfile.return_value = True
    
    source_2.write([self.settings['flatten']])
    
    self.source.read([self.settings['file_extension']])
    source_2.read([self.settings['flatten']])
    
    self.assertEqual(self.settings['file_extension'].value, 'jpg')
    self.assertEqual(self.settings['flatten'].value, True)
    
    self.assertEqual(self.source.write_data_to_source.call_count, 1)
    self.assertEqual(source_2.write_data_to_source.call_count, 1)
  
  def test_has_data_no_data(self, mock_os_path_isfile, mock_io_open):
    self._set_up_mock_open(mock_io_open)
    
    self.assertFalse(self.source.has_data())
  
  def test_has_data_contains_data(self, mock_os_path_isfile, mock_io_open):
    self._set_up_mock_open(mock_io_open)
    
    self.settings['file_extension'].set_value('jpg')
    
    self.source.write([self.settings['file_extension']])
    
    mock_os_path_isfile.return_value = True
    
    self.assertTrue(self.source.has_data())
  
  def test_has_data_error_on_read(self, mock_os_path_isfile, mock_io_open):
    self._set_up_mock_open(mock_io_open)
    
    self.source.write([self.settings['file_extension']])
    
    mock_os_path_isfile.return_value = True
    mock_io_open.return_value.__exit__.side_effect = sources_.SourceInvalidFormatError
    
    self.assertEqual(self.source.has_data(), 'invalid_format')
  
  def test_clear_no_data(self, mock_os_path_isfile, mock_io_open):
    self._set_up_mock_open(mock_io_open)
    self.source.write_data_to_source = mock.Mock(wraps=self.source.write_data_to_source)
    
    self.source.clear()
    
    self.assertFalse(self.source.has_data())
    self.assertEqual(self.source.write_data_to_source.call_count, 0)
  
  def test_clear_data_in_different_source(self, mock_os_path_isfile, mock_io_open):
    def _truncate_and_write(data):
      string_io.truncate(0)
      _orig_string_io_write(data)
    
    string_io = self._set_up_mock_open(mock_io_open)
    
    source_2 = self._source_class('test_settings_2', self.filepath)
    self.source.write_data_to_source = mock.Mock(wraps=self.source.write_data_to_source)
    source_2.write_data_to_source = mock.Mock(wraps=source_2.write_data_to_source)
    
    self.source.write([self.settings['file_extension']])
    mock_os_path_isfile.return_value = True
    
    source_2.write([self.settings['flatten']])
    
    _orig_string_io_write = string_io.write
    string_io.write = _truncate_and_write
    
    self.source.clear()
    
    self.assertFalse(self.source.has_data())
    self.assertTrue(source_2.has_data())
    
    self.assertEqual(self.source.write_data_to_source.call_count, 1)
    self.assertEqual(source_2.write_data_to_source.call_count, 1)
  
  def _set_up_mock_open(self, mock_io_open):
    string_io = io.StringIO()
    
    mock_io_open.return_value.__enter__.return_value = string_io
    mock_io_open.return_value.__exit__.side_effect = (
      lambda *args, **kwargs: mock_io_open.return_value.__enter__.return_value.seek(0))
    
    return string_io


@mock.patch(pgutils.get_pygimplib_module_path() + '.setting.sources.io.open')
@mock.patch(
  pgutils.get_pygimplib_module_path() + '.setting.sources.os.path.isfile',
  return_value=False)
class TestPickleFileSource(unittest.TestCase, _FileSourceTests):
  
  def __init__(self, *args, **kwargs):
    _FileSourceTests.__init__(
      self, 'test_settings', 'test_filepath.pkl', sources_.PickleFileSource)
    
    unittest.TestCase.__init__(self, *args, **kwargs)
  
  def setUp(self):
    self.source_name = self._source_name
    self.filepath = self._filepath
    self.source = self._source_class(self.source_name, self.filepath)
    self.settings = stubs_group.create_test_settings()


@mock.patch(pgutils.get_pygimplib_module_path() + '.setting.sources.io.open')
@mock.patch(
  pgutils.get_pygimplib_module_path() + '.setting.sources.os.path.isfile',
  return_value=False)
class TestJsonFileSource(unittest.TestCase, _FileSourceTests):
  
  def __init__(self, *args, **kwargs):
    _FileSourceTests.__init__(
      self, 'test_settings', 'test_filepath.json', sources_.JsonFileSource)
    
    unittest.TestCase.__init__(self, *args, **kwargs)
  
  def setUp(self):
    self.source_name = self._source_name
    self.filepath = self._filepath
    self.source = self._source_class(self.source_name, self.filepath)
    self.settings = stubs_group.create_test_settings()
