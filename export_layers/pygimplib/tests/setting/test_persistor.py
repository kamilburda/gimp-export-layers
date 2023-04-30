# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import collections
import unittest

import mock

from ... import utils as pgutils

from ...setting import persistor as persistor_
from ...setting import sources as sources_

from .. import stubs_gimp
from . import stubs_group


@mock.patch(
  pgutils.get_pygimplib_module_path() + '.setting.sources.gimpshelf.shelf',
  new_callable=stubs_gimp.ShelfStub)
@mock.patch(
  pgutils.get_pygimplib_module_path() + '.setting.sources.gimp',
  new_callable=stubs_gimp.GimpModuleStub)
class TestPersistor(unittest.TestCase):
  
  @classmethod
  def setUpClass(cls):
    cls.orig_default_setting_sources = persistor_.Persistor.get_default_setting_sources()
  
  @classmethod
  def tearDownClass(cls):
    persistor_.Persistor.set_default_setting_sources(cls.orig_default_setting_sources)
  
  @mock.patch(
    pgutils.get_pygimplib_module_path() + '.setting.sources.gimpshelf.shelf',
    new=stubs_gimp.ShelfStub())
  @mock.patch(
    pgutils.get_pygimplib_module_path() + '.setting.sources.gimp.directory',
    new='gimp_directory')
  def setUp(self):
    self.settings = stubs_group.create_test_settings()
    self.session_source = sources_.SessionSource('')
    self.persistent_source = sources_.PersistentSource('')
    
    self.sources_for_persistor = collections.OrderedDict([
      ('session', self.session_source),
      ('persistent', self.persistent_source)])
    self.session_source_for_persistor = {'session': self.session_source}
    
    persistor_.Persistor.set_default_setting_sources(None)
  
  def test_set_default_setting_sources_none(self, mock_gimp_module, mock_gimp_shelf):
    persistor_.Persistor.set_default_setting_sources(None)
    self.assertEqual(persistor_.Persistor.get_default_setting_sources(), collections.OrderedDict())
  
  def test_set_default_setting_sources_raises_error_on_invalid_input(
        self, mock_gimp_module, mock_gimp_shelf):
    with self.assertRaises(TypeError):
      persistor_.Persistor.set_default_setting_sources(['persistent'])
  
  def test_get_default_setting_sources_returns_copy(self, mock_gimp_module, mock_gimp_shelf):
    persistor_.Persistor.set_default_setting_sources(self.sources_for_persistor)
    
    result = persistor_.Persistor.get_default_setting_sources()
    
    self.assertDictEqual(result, self.sources_for_persistor)
    self.assertNotEqual(id(result), id(self.sources_for_persistor))
  
  def test_load_save(self, mock_gimp_module, mock_gimp_shelf):
    self._test_load_save(self.sources_for_persistor)
  
  def test_load_save_with_default_sources(self, mock_gimp_module, mock_gimp_shelf):
    persistor_.Persistor.set_default_setting_sources(self.sources_for_persistor)
    
    self._test_load_save(None)
  
  def test_load_save_with_default_sources_and_dict(self, mock_gimp_module, mock_gimp_shelf):
    mock_persistent_source = mock.Mock(wraps=self.persistent_source)
    mock_default_session_source = mock.Mock(wraps=self.session_source)
    mock_session_source = mock.Mock(wraps=sources_.SessionSource(''))
    
    session_source_for_persistor = {'session': mock_session_source}
    
    persistor_.Persistor.set_default_setting_sources(self.sources_for_persistor)
    
    self._test_load_save(session_source_for_persistor)
    
    self.assertEqual(mock_session_source.read.call_count, 1)
    self.assertEqual(mock_session_source.write.call_count, 1)
    self.assertEqual(mock_default_session_source.read.call_count, 0)
    self.assertEqual(mock_default_session_source.write.call_count, 0)
    self.assertEqual(mock_persistent_source.read.call_count, 0)
    self.assertEqual(mock_persistent_source.write.call_count, 0)
  
  def test_load_save_with_default_sources_and_list(self, mock_gimp_module, mock_gimp_shelf):
    mock_persistent_source = mock.Mock(wraps=self.persistent_source)
    mock_session_source = mock.Mock(wraps=self.session_source)
    sources_for_persistor = ['session', 'persistent']
    default_sources = collections.OrderedDict([
      ('session', mock_session_source),
      ('persistent', mock_persistent_source)])
    
    persistor_.Persistor.set_default_setting_sources(default_sources)
    
    self._test_load_save(sources_for_persistor)
    
    self.assertEqual(mock_session_source.read.call_count, 1)
    self.assertEqual(mock_session_source.write.call_count, 1)
    # `read` should not be called as all settings have been found in `mock_session_source`.
    self.assertEqual(mock_persistent_source.read.call_count, 0)
    self.assertEqual(mock_persistent_source.write.call_count, 1)
  
  def _test_load_save(self, sources_for_persistor):
    self.settings['file_extension'].set_value('png')
    self.settings['flatten'].set_value(True)
    
    status, unused_ = persistor_.Persistor.save([self.settings], sources_for_persistor)
    
    self.assertEqual(status, persistor_.Persistor.SUCCESS)
    
    self.settings['file_extension'].set_value('jpg')
    self.settings['flatten'].set_value(False)
    
    status, unused_ = persistor_.Persistor.load([self.settings], sources_for_persistor)
    
    self.assertEqual(status, persistor_.Persistor.SUCCESS)
    self.assertEqual(self.settings['file_extension'].value, 'png')
    self.assertEqual(self.settings['flatten'].value, True)
  
  def test_load_combine_settings_from_multiple_sources(self, mock_gimp_module, mock_gimp_shelf):
    self.settings['file_extension'].set_value('png')
    self.settings['flatten'].set_value(True)
    self.session_source.write([self.settings['file_extension']])
    self.settings['file_extension'].set_value('jpg')
    self.persistent_source.write([self.settings['flatten'], self.settings['file_extension']])
    self.settings['file_extension'].set_value('gif')
    self.settings['flatten'].set_value(False)
    
    persistor_.Persistor.load([self.settings], self.sources_for_persistor)
    
    self.assertEqual(self.settings['file_extension'].value, 'png')
    self.assertEqual(self.settings['flatten'].value, True)
    
    for setting in self.settings:
      if setting not in [self.settings['file_extension'], self.settings['flatten']]:
        self.assertEqual(setting.value, setting.default_value)
  
  def test_load_multiple_setting_groups(self, mock_gimp_module, mock_gimp_shelf):
    settings = stubs_group.create_test_settings_hierarchical()
    
    settings['main/file_extension'].set_value('png')
    settings['advanced/flatten'].set_value(True)
    self.session_source.write(settings.walk())
    settings['main/file_extension'].set_value('gif')
    settings['advanced/flatten'].set_value(False)
    
    persistor_.Persistor.load([settings], self.session_source_for_persistor)
    
    self.assertEqual(settings['main/file_extension'].value, 'png')
    self.assertEqual(settings['advanced/flatten'].value, True)
  
  def test_load_empty_settings(self, mock_gimp_module, mock_gimp_shelf):
    status, unused_ = persistor_.Persistor.load([], self.session_source_for_persistor)
    self.assertEqual(status, persistor_.Persistor.SUCCESS)
  
  def test_load_no_default_source(self, mock_gimp_module, mock_gimp_shelf):
    status, unused_ = persistor_.Persistor.load([self.settings], None)
    self.assertEqual(status, persistor_.Persistor.NO_SOURCE)
  
  def test_load_missing_default_source_from_list(self, mock_gimp_module, mock_gimp_shelf):
    persistor_.Persistor.set_default_setting_sources(self.session_source_for_persistor)
    
    status, unused_ = persistor_.Persistor.load([self.settings], ['persistent'])
    
    self.assertEqual(status, persistor_.Persistor.NO_SOURCE)
  
  def test_load_settings_source_not_found(self, mock_gimp_module, mock_gimp_shelf):
    status, unused_ = persistor_.Persistor.load([self.settings], self.sources_for_persistor)
    self.assertEqual(status, persistor_.Persistor.NOT_ALL_SETTINGS_FOUND)
  
  def test_load_settings_not_found(self, mock_gimp_module, mock_gimp_shelf):
    self.session_source.write([self.settings['flatten']])
    self.persistent_source.write([self.settings['file_extension'], self.settings['flatten']])
    
    status, unused_ = persistor_.Persistor.load(
      [self.settings['overwrite_mode']], self.sources_for_persistor)
    self.assertEqual(status, persistor_.Persistor.NOT_ALL_SETTINGS_FOUND)
  
  def test_load_read_fail(self, mock_gimp_module, mock_gimp_shelf):
    self.persistent_source.write(self.settings)
    
    # Simulate formatting error
    parasite = sources_.gimp.parasite_find(self.persistent_source.source_name)
    parasite.data = parasite.data[:-1]
    sources_.gimp.parasite_attach(parasite)
    
    status, unused_ = persistor_.Persistor.load([self.settings], self.sources_for_persistor)
    self.assertEqual(status, persistor_.Persistor.READ_FAIL)
  
  def test_save_empty_settings(self, mock_gimp_module, mock_gimp_shelf):
    status, unused_ = persistor_.Persistor.save([], self.session_source_for_persistor)
    self.assertEqual(status, persistor_.Persistor.SUCCESS)
  
  def test_save_no_default_source(self, mock_gimp_module, mock_gimp_shelf):
    status, unused_ = persistor_.Persistor.save([self.settings], None)
    self.assertEqual(status, persistor_.Persistor.NO_SOURCE)
  
  def test_save_missing_default_source_from_list(self, mock_gimp_module, mock_gimp_shelf):
    persistor_.Persistor.set_default_setting_sources(self.session_source_for_persistor)
    
    status, unused_ = persistor_.Persistor.save([self.settings], ['persistent'])
    
    self.assertEqual(status, persistor_.Persistor.NO_SOURCE)
  
  def test_save_write_fail(self, mock_gimp_module, mock_gimp_shelf):
    with mock.patch(
           pgutils.get_pygimplib_module_path() + '.setting.sources.gimp') as temp_mock_gimp_module:
      temp_mock_gimp_module.parasite_find.side_effect = sources_.SourceWriteError
      status, unused_ = persistor_.Persistor.save([self.settings], self.sources_for_persistor)
    
    self.assertEqual(status, persistor_.Persistor.WRITE_FAIL)
