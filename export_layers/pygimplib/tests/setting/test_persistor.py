# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

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
  
  def test_load_save(self, mock_persistent_source, mock_session_source):
    self.settings['file_extension'].set_value('png')
    self.settings['only_visible_layers'].set_value(True)
    
    status, unused_ = persistor_.Persistor.save(
      [self.settings], [self.session_source, self.persistent_source])
    self.assertEqual(status, persistor_.Persistor.SUCCESS)
    
    self.settings['file_extension'].set_value('jpg')
    self.settings['only_visible_layers'].set_value(False)
    
    status, unused_ = persistor_.Persistor.load(
      [self.settings], [self.session_source, self.persistent_source])
    self.assertEqual(status, persistor_.Persistor.SUCCESS)
    self.assertEqual(self.settings['file_extension'].value, 'png')
    self.assertEqual(self.settings['only_visible_layers'].value, True)
  
  def test_load_combine_settings_from_multiple_sources(
        self, mock_persistent_source, mock_session_source):
    self.settings['file_extension'].set_value('png')
    self.settings['only_visible_layers'].set_value(True)
    self.session_source.write([self.settings['file_extension']])
    self.settings['file_extension'].set_value('jpg')
    self.persistent_source.write(
      [self.settings['only_visible_layers'], self.settings['file_extension']])
    self.settings['file_extension'].set_value('gif')
    self.settings['only_visible_layers'].set_value(False)
    
    persistor_.Persistor.load(
      [self.settings], [self.session_source, self.persistent_source])
    
    self.assertEqual(self.settings['file_extension'].value, 'png')
    self.assertEqual(self.settings['only_visible_layers'].value, True)
    
    for setting in self.settings:
      if setting not in [
           self.settings['file_extension'], self.settings['only_visible_layers']]:
        self.assertEqual(setting.value, setting.default_value)
  
  def test_load_groups(self, mock_persistent_source, mock_session_source):
    settings = stubs_group.create_test_settings_hierarchical()
    
    settings['main/file_extension'].set_value('png')
    settings['advanced/only_visible_layers'].set_value(True)
    self.session_source.write(settings.walk())
    settings['main/file_extension'].set_value('gif')
    settings['advanced/only_visible_layers'].set_value(False)
    
    persistor_.Persistor.load([settings], [self.session_source])
    
    self.assertEqual(settings['main/file_extension'].value, 'png')
    self.assertEqual(settings['advanced/only_visible_layers'].value, True)
  
  def test_load_settings_source_not_found(
        self, mock_persistent_source, mock_session_source):
    status, unused_ = persistor_.Persistor.load(
      [self.settings], [self.session_source, self.persistent_source])
    self.assertEqual(status, persistor_.Persistor.NOT_ALL_SETTINGS_FOUND)
  
  def test_load_settings_not_found(self, mock_persistent_source, mock_session_source):
    self.session_source.write([self.settings['only_visible_layers']])
    self.persistent_source.write(
      [self.settings['file_extension'], self.settings['only_visible_layers']])
    
    status, unused_ = persistor_.Persistor.load(
      [self.settings['overwrite_mode']], [self.session_source, self.persistent_source])
    self.assertEqual(status, persistor_.Persistor.NOT_ALL_SETTINGS_FOUND)
  
  def test_load_read_fail(self, mock_persistent_source, mock_session_source):
    self.persistent_source.write(self.settings)
    
    # Simulate formatting error
    parasite = sources_.gimp.parasite_find(self.persistent_source.source_name)
    parasite.data = parasite.data[:-1]
    sources_.gimp.parasite_attach(parasite)
    
    status, unused_ = persistor_.Persistor.load(
      [self.settings], [self.session_source, self.persistent_source])
    self.assertEqual(status, persistor_.Persistor.READ_FAIL)
  
  def test_load_write_fail(self, mock_persistent_source, mock_session_source):
    with mock.patch(
           pgutils.get_pygimplib_module_path()
           + '.setting.sources.gimp') as temp_mock_persistent_source:
      temp_mock_persistent_source.parasite_find.side_effect = sources_.SourceWriteError
      status, unused_ = persistor_.Persistor.save(
        [self.settings], [self.session_source, self.persistent_source])
    
    self.assertEqual(status, persistor_.Persistor.WRITE_FAIL)
