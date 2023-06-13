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
  
  constraints = group_.Group(name='constraints')
  
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


class TestUpdateDataForSource(unittest.TestCase):
  
  def setUp(self):
    self.source_name = 'test_settings'
    self.source = sources_.PickleFileSource(self.source_name, filepath='filepath')
    
    self.settings = _test_settings_for_read_write()
    
    self.maxDiff = None
  
  def test_update_data_for_source_empty_data(self):
    expected_data = _test_data_for_read_write()
    
    data = []
    self.source._update_data_for_source([self.settings], data)
    
    self.assertListEqual(data, expected_data)
  
  def test_update_data_for_source_modifies_existing_data(self):
    expected_data = _test_data_for_read_write()
    
    self.settings['main/file_extension'].set_value('jpg')
    self.settings['main/procedures/use_layer_size/enabled'].set_value(False)
    self.settings['standalone_setting'].set_value('something_else')
    
    expected_data[0]['settings'][0]['settings'][0]['value'] = 'jpg'
    expected_data[0]['settings'][0]['settings'][1]['settings'][0]['settings'][0]['value'] = False
    expected_data[0]['settings'][2]['value'] = 'something_else'
    
    data = _test_data_for_read_write()
    self.source._update_data_for_source([self.settings], data)
    
    self.assertListEqual(data, expected_data)
  
  def test_update_data_for_source_modifies_only_selected_settings(self):
    expected_data = _test_data_for_read_write()
    
    self.settings['main/file_extension'].set_value('jpg')
    self.settings['main/procedures/use_layer_size/enabled'].set_value(False)
    self.settings['main/procedures/insert_background_layers/enabled'].set_value(False)
    self.settings['standalone_setting'].set_value('something_else')
    
    expected_data[0]['settings'][0]['settings'][1]['settings'][0]['settings'][0]['value'] = False
    expected_data[0]['settings'][0]['settings'][1]['settings'][1]['settings'][0]['value'] = False
    expected_data[0]['settings'][2]['value'] = 'something_else'
    
    data = _test_data_for_read_write()
    self.source._update_data_for_source(
      [self.settings['main/procedures'], self.settings['standalone_setting']],
      data)
    
    self.assertListEqual(data, expected_data)
  
  def test_update_data_for_source_adds_groups_which_are_not_present_in_source(self):
    expected_data = _test_data_for_read_write()
    
    # Keep only 'main/procedures/use_layer_size/enabled' and 'standalone_setting'
    del expected_data[0]['settings'][0]['settings'][1]['settings'][0]['settings'][1]
    del expected_data[0]['settings'][0]['settings'][1]['settings'][1]
    del expected_data[0]['settings'][0]['settings'][2]
    del expected_data[0]['settings'][0]['settings'][0]
    del expected_data[0]['settings'][1]
    
    data = []
    self.source._update_data_for_source(
      [self.settings['main/procedures/use_layer_size/enabled'],
       self.settings['standalone_setting']],
      data)
    
    self.assertListEqual(data, expected_data)
  
  def test_update_data_for_source_adds_settings_to_existing_groups(self):
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
    
    data = []
    self.source._update_data_for_source(self.settings, data)
    
    self.assertListEqual(data, expected_data)
  
  def test_update_data_for_source_raises_error_if_list_expected_but_not_found(self):
    settings = _test_settings_for_read_write()
    
    data_with_wrong_structure = {'source_name': []}
    
    with self.assertRaises(sources_.SourceInvalidFormatError):
      self.source._update_data_for_source([settings], data_with_wrong_structure)
  
  def test_update_data_for_source_raises_error_if_dict_expected_but_not_found(self):
    settings = _test_settings_for_read_write()
    
    data_with_wrong_structure = [[{'source_name': []}]]
    
    with self.assertRaises(sources_.SourceInvalidFormatError):
      self.source._update_data_for_source([settings], data_with_wrong_structure)


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
  
  def test_write(self, mock_session_source):
    self.settings['file_extension'].set_value('png')
    self.settings['flatten'].set_value(True)
    
    self.source.write(self.settings)
    
    self.assertEqual(
      sources_.gimpshelf.shelf[self.source_name][
        self.settings['file_extension'].get_path('root')],
      'png')
    self.assertEqual(
      sources_.gimpshelf.shelf[self.source_name][
        self.settings['flatten'].get_path('root')],
      True)
  
  def test_write_multiple_settings_separately(self, mock_session_source):
    self.settings['file_extension'].set_value('jpg')
    self.source.write([self.settings['file_extension']])
    self.settings['flatten'].set_value(True)
    
    self.source.write([self.settings['flatten']])
    self.source.read([self.settings['file_extension']])
    self.source.read([self.settings['flatten']])
    
    self.assertEqual(self.settings['file_extension'].value, 'jpg')
    self.assertEqual(self.settings['flatten'].value, True)
  
  def test_read(self, mock_session_source):
    data = {}
    data[self.settings['file_extension'].get_path('root')] = 'png'
    data[self.settings['flatten'].get_path('root')] = True
    sources_.gimpshelf.shelf[self.source_name] = data
    
    self.source.read(
      [self.settings['file_extension'], self.settings['flatten']])
    
    self.assertEqual(self.settings['file_extension'].value, 'png')
    self.assertEqual(self.settings['flatten'].value, True)
  
  def test_read_settings_not_found(self, mock_session_source):
    self.source.write([self.settings['file_extension']])
    with self.assertRaises(sources_.SettingsNotFoundInSourceError):
      self.source.read(self.settings)
  
  def test_read_settings_invalid_format(self, mock_session_source):
    with mock.patch(
           pgutils.get_pygimplib_module_path()
           + '.setting.sources.gimpshelf.shelf') as temp_mock_session_source:
      temp_mock_session_source.__getitem__.side_effect = Exception
      
      with self.assertRaises(sources_.SourceInvalidFormatError):
        self.source.read(self.settings)
  
  def test_read_invalid_setting_value_set_to_default_value(self, mock_session_source):
    setting_with_invalid_value = settings_.IntSetting('int', default_value=-1)
    self.source.write([setting_with_invalid_value])
    
    setting = settings_.IntSetting('int', default_value=2, min_value=0)
    self.source.read([setting])
    
    self.assertEqual(setting.value, setting.default_value)
  
  def test_clear(self, mock_session_source):
    self.source.write(self.settings)
    self.source.clear()
    
    with self.assertRaises(sources_.SourceNotFoundError):
      self.source.read(self.settings)
  
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
    
    self.source.write(self.settings)
    self.source.read(self.settings)
    
    self.assertEqual(self.settings['file_extension'].value, 'jpg')
    self.assertEqual(self.settings['flatten'].value, True)
  
  def test_write_multiple_settings_separately(self, mock_persistent_source):
    self.settings['file_extension'].set_value('jpg')
    self.source.write([self.settings['file_extension']])
    self.settings['flatten'].set_value(True)
    
    self.source.write([self.settings['flatten']])
    self.source.read([self.settings['file_extension']])
    self.source.read([self.settings['flatten']])
    
    self.assertEqual(self.settings['file_extension'].value, 'jpg')
    self.assertEqual(self.settings['flatten'].value, True)
  
  def test_write_read_same_setting_name_in_different_groups(self, mock_persistent_source):
    settings = stubs_group.create_test_settings_hierarchical()
    file_extension_advanced_setting = settings_.FileExtensionSetting(
      'file_extension', default_value='png')
    settings['advanced'].add([file_extension_advanced_setting])
    
    self.source.write(settings.walk())
    self.source.read(settings.walk())
    
    self.assertEqual(settings['main/file_extension'].value, 'bmp')
    self.assertEqual(settings['advanced/file_extension'].value, 'png')
  
  def test_read_source_not_found(self, mock_persistent_source):
    with self.assertRaises(sources_.SourceNotFoundError):
      self.source.read(self.settings)
  
  def test_read_settings_not_found(self, mock_persistent_source):
    self.source.write([self.settings['file_extension']])
    with self.assertRaises(sources_.SettingsNotFoundInSourceError):
      self.source.read(self.settings)
  
  def test_read_settings_invalid_format(self, mock_persistent_source):
    self.source.write(self.settings)
    
    # Simulate formatting error
    parasite = sources_.gimp.parasite_find(self.source_name)
    parasite.data = parasite.data[:-1]
    sources_.gimp.parasite_attach(parasite)
    
    with self.assertRaises(sources_.SourceInvalidFormatError):
      self.source.read(self.settings)
  
  def test_read_invalid_setting_value_set_to_default_value(self, mock_persistent_source):
    setting_with_invalid_value = settings_.IntSetting('int', default_value=-1)
    self.source.write([setting_with_invalid_value])
    
    setting = settings_.IntSetting('int', default_value=2, min_value=0)
    self.source.read([setting])
    
    self.assertEqual(setting.value, setting.default_value)
  
  def test_clear(self, mock_persistent_source):
    self.source.write(self.settings)
    self.source.clear()
    
    with self.assertRaises(sources_.SourceNotFoundError):
      self.source.read(self.settings)
  
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
    
    self.source.write(self.settings)
    
    mock_os_path_isfile.return_value = True
    self.source.read(self.settings)
    
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
