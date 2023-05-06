# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import io
import unittest

import mock

from ... import utils as pgutils

from ...setting import settings as settings_
from ...setting import sources as sources_

from .. import stubs_gimp
from . import stubs_group


@mock.patch(
  pgutils.get_pygimplib_module_path() + '.setting.sources.gimpshelf.shelf',
  new_callable=stubs_gimp.ShelfStub)
class TestSessionSource(unittest.TestCase):
  
  @mock.patch(
    pgutils.get_pygimplib_module_path() + '.setting.sources.gimpshelf.shelf',
    new=stubs_gimp.ShelfStub())
  def setUp(self):
    self.source_name = 'test_settings'
    self.source = sources_.SessionSource(self.source_name)
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
class TestPersistentSource(unittest.TestCase):
  
  @mock.patch(
    pgutils.get_pygimplib_module_path() + '.setting.sources.gimp.directory',
    new='gimp_directory')
  def setUp(self):
    self.source_name = 'test_settings'
    self.source = sources_.PersistentSource(self.source_name)
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


@mock.patch(pgutils.get_pygimplib_module_path() + '.setting.sources.io.open')
@mock.patch(
  pgutils.get_pygimplib_module_path() + '.setting.sources.os.path.isfile',
  return_value=False)
class TestPickleFileSource(unittest.TestCase):
  
  def setUp(self):
    self.source_name = 'test_settings'
    self.filepath = 'test_filepath.pkl'
    self.source = sources_.PickleFileSource(self.source_name, self.filepath)
    self.settings = stubs_group.create_test_settings()
  
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
    
    source_2 = sources_.PickleFileSource('test_settings_2', self.filepath)
    self.source.write_dict = mock.Mock(wraps=self.source.write_dict)
    source_2.write_dict = mock.Mock(wraps=source_2.write_dict)
    
    self.settings['file_extension'].set_value('jpg')
    self.settings['flatten'].set_value(True)
    
    self.source.write([self.settings['file_extension']])
    mock_os_path_isfile.return_value = True
    
    source_2.write([self.settings['flatten']])
    
    self.source.read([self.settings['file_extension']])
    source_2.read([self.settings['flatten']])
    
    self.assertEqual(self.settings['file_extension'].value, 'jpg')
    self.assertEqual(self.settings['flatten'].value, True)
    
    self.assertEqual(self.source.write_dict.call_count, 1)
    self.assertEqual(source_2.write_dict.call_count, 1)
  
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
    self.source.write_dict = mock.Mock(wraps=self.source.write_dict)
    
    self.source.clear()
    
    self.assertFalse(self.source.has_data())
    self.assertEqual(self.source.write_dict.call_count, 0)
  
  def test_clear_data_in_different_source(self, mock_os_path_isfile, mock_io_open):
    self._set_up_mock_open(mock_io_open)
    
    source_2 = sources_.PickleFileSource('test_settings_2', self.filepath)
    self.source.write_dict = mock.Mock(wraps=self.source.write_dict)
    source_2.write_dict = mock.Mock(wraps=source_2.write_dict)
    
    self.source.write([self.settings['file_extension']])
    mock_os_path_isfile.return_value = True
    
    source_2.write([self.settings['flatten']])
    
    self.source.clear()
    
    self.assertFalse(self.source.has_data())
    self.assertTrue(source_2.has_data())
    
    self.assertEqual(self.source.write_dict.call_count, 2)
    self.assertEqual(source_2.write_dict.call_count, 1)
  
  def _set_up_mock_open(self, mock_io_open):
    mock_io_open.return_value.__enter__.return_value = io.BytesIO()
    mock_io_open.return_value.__exit__.side_effect = (
      lambda *args, **kwargs: mock_io_open.return_value.__enter__.return_value.seek(0))


@mock.patch(
  pgutils.get_pygimplib_module_path() + '.setting.sources.gimpshelf.shelf',
  new_callable=stubs_gimp.ShelfStub)
@mock.patch(
  pgutils.get_pygimplib_module_path() + '.setting.sources.gimp',
  new_callable=stubs_gimp.GimpModuleStub)
class TestSourceReadWriteDict(unittest.TestCase):
  
  @mock.patch(
    pgutils.get_pygimplib_module_path() + '.setting.sources.gimp.directory',
    new='gimp_directory')
  def setUp(self):
    self.source_name = 'test_settings'
    self.source_session = sources_.SessionSource(self.source_name)
    self.source_persistent = sources_.PersistentSource(self.source_name)
    self.settings = stubs_group.create_test_settings()
  
  def test_read_dict(self, mock_persistent_source, mock_session_source):
    for source in [self.source_session, self.source_persistent]:
      self._test_read_dict(source)
  
  def test_read_dict_nonexistent_source(
        self, mock_persistent_source, mock_session_source):
    for source in [self.source_session, self.source_persistent]:
      self._test_read_dict_nonexistent_source(source)
  
  def test_write_dict(self, mock_persistent_source, mock_session_source):
    for source in [self.source_session, self.source_persistent]:
      self._test_write_dict(source)
  
  def _test_read_dict(self, source):
    source.write(self.settings)
    
    data_dict = source.read_dict()
    self.assertDictEqual(
      data_dict,
      {
        'file_extension': self.settings['file_extension'].value,
        'flatten': self.settings['flatten'].value,
        'overwrite_mode': self.settings['overwrite_mode'].value,
      })
  
  def _test_read_dict_nonexistent_source(self, source):
    self.assertIsNone(source.read_dict())
  
  def _test_write_dict(self, source):
    data_dict = {
      'file_extension': self.settings['file_extension'].default_value,
      'flatten': self.settings['flatten'].default_value,
    }
    
    self.settings['file_extension'].set_value('jpg')
    self.settings['flatten'].set_value(True)
    
    source.write_dict(data_dict)
    
    source.read(
      [self.settings['file_extension'], self.settings['flatten']])
    
    self.assertEqual(
      self.settings['file_extension'].value,
      self.settings['file_extension'].default_value)
    self.assertEqual(
      self.settings['flatten'].value,
      self.settings['flatten'].default_value)
