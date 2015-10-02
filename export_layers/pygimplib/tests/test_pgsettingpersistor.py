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

from ..lib import mock
from . import gimpmocks

from .. import pgsetting
from .. import pgsettingpersistor

from .test_pgsettinggroup import create_test_settings
from .test_pgsettinggroup import create_test_settings_hierarchical

#===============================================================================

LIB_NAME = ".".join(__name__.split(".")[:-2])

#===============================================================================


class MockStringIO(StringIO):
  def read(self):
    return self.getvalue()


#===============================================================================


class TestSessionPersistentSettingSource(unittest.TestCase):
  
  @mock.patch(LIB_NAME + ".pgsettingpersistor.gimpshelf.shelf", new=gimpmocks.MockGimpShelf())
  def setUp(self):
    self.source_name = 'test_settings_'
    self.source = pgsettingpersistor.SessionPersistentSettingSource(self.source_name)
    self.settings = create_test_settings()
  
  @mock.patch(LIB_NAME + ".pgsettingpersistor.gimpshelf.shelf", new=gimpmocks.MockGimpShelf())
  def test_write(self):
    self.settings['file_extension'].set_value("png")
    self.settings['ignore_invisible'].set_value(True)
    self.source.write(self.settings)
    
    self.assertEqual(pgsettingpersistor.gimpshelf.shelf[self.source_name + 'file_extension'], "png")
    self.assertEqual(pgsettingpersistor.gimpshelf.shelf[self.source_name + 'ignore_invisible'], True)
  
  @mock.patch(LIB_NAME + ".pgsettingpersistor.gimpshelf.shelf", new=gimpmocks.MockGimpShelf())
  def test_read(self):
    pgsettingpersistor.gimpshelf.shelf[self.source_name + 'file_extension'] = "png"
    pgsettingpersistor.gimpshelf.shelf[self.source_name + 'ignore_invisible'] = True
    self.source.read([self.settings['file_extension'], self.settings['ignore_invisible']])
    self.assertEqual(self.settings['file_extension'].value, "png")
    self.assertEqual(self.settings['ignore_invisible'].value, True)
  
  @mock.patch(LIB_NAME + ".pgsettingpersistor.gimpshelf.shelf", new=gimpmocks.MockGimpShelf())
  def test_read_settings_not_found(self):
    with self.assertRaises(pgsettingpersistor.SettingsNotFoundInSourceError):
      self.source.read(self.settings)
  
  @mock.patch(LIB_NAME + ".pgsettingpersistor.gimpshelf.shelf", new=gimpmocks.MockGimpShelf())
  def test_read_invalid_setting_value_set_to_default_value(self):
    setting_with_invalid_value = pgsetting.IntSetting('int', -1)
    self.source.write([setting_with_invalid_value])
    
    setting = pgsetting.IntSetting('int', 2, min_value=0)
    self.source.read([setting])
    
    self.assertEqual(setting.value, setting.default_value)


class TestPersistentSettingSource(unittest.TestCase):
  
  @mock.patch(LIB_NAME + ".pgsettingpersistor.gimp", new=gimpmocks.MockGimpParasite())
  def setUp(self):
    self.source_name = 'test_settings_'
    self.source = pgsettingpersistor.PersistentSettingSource(self.source_name)
    self.settings = create_test_settings()
  
  @mock.patch(LIB_NAME + ".pgsettingpersistor.gimp", new=gimpmocks.MockGimpParasite())
  def test_write_read(self):
    self.settings['file_extension'].set_value("jpg")
    self.settings['ignore_invisible'].set_value(True)
    self.source.write(self.settings)
    self.source.read(self.settings)
    self.assertEqual(self.settings['file_extension'].value, "jpg")
    self.assertEqual(self.settings['ignore_invisible'].value, True)
  
  @mock.patch(LIB_NAME + ".pgsettingpersistor.gimp", new=gimpmocks.MockGimpParasite())
  def test_read_source_not_found(self):
    with self.assertRaises(pgsettingpersistor.SettingSourceNotFoundError):
      self.source.read(self.settings)
  
  @mock.patch(LIB_NAME + ".pgsettingpersistor.gimp", new=gimpmocks.MockGimpParasite())
  def test_read_settings_not_found(self):
    self.source.write([self.settings['file_extension']])
    with self.assertRaises(pgsettingpersistor.SettingsNotFoundInSourceError):
      self.source.read(self.settings)
  
  @mock.patch(LIB_NAME + ".pgsettingpersistor.gimp", new=gimpmocks.MockGimpParasite())
  def test_read_settings_invalid_format(self):
    self.source.write(self.settings)
    
    # Simulate formatting error
    parasite = pgsettingpersistor.gimp.parasite_find(self.source_name)
    parasite.data = parasite.data[:-1]
    pgsettingpersistor.gimp.parasite_attach(parasite)
    
    with self.assertRaises(pgsettingpersistor.SettingSourceInvalidFormatError):
      self.source.read(self.settings)
  
  @mock.patch(LIB_NAME + ".pgsettingpersistor.gimp", new=gimpmocks.MockGimpParasite())
  def test_read_invalid_setting_value_set_to_default_value(self):
    setting_with_invalid_value = pgsetting.IntSetting('int', -1)
    self.source.write([setting_with_invalid_value])
    
    setting = pgsetting.IntSetting('int', 2, min_value=0)
    self.source.read([setting])
    
    self.assertEqual(setting.value, setting.default_value)


#===============================================================================


class TestSettingPersistor(unittest.TestCase):
  
  @mock.patch(LIB_NAME + ".pgsettingpersistor.gimpshelf.shelf", new=gimpmocks.MockGimpShelf())
  @mock.patch(LIB_NAME + ".pgsettingpersistor.gimp", new=gimpmocks.MockGimpParasite())
  def setUp(self):
    self.settings = create_test_settings()
    self.session_source = pgsettingpersistor.SessionPersistentSettingSource('')
    self.persistent_source = pgsettingpersistor.PersistentSettingSource('')
  
  @mock.patch(LIB_NAME + ".pgsettingpersistor.gimpshelf.shelf", new=gimpmocks.MockGimpShelf())
  @mock.patch(LIB_NAME + ".pgsettingpersistor.gimp", new=gimpmocks.MockGimpParasite())
  def test_load_save(self):
    self.settings['file_extension'].set_value("png")
    self.settings['ignore_invisible'].set_value(True)
    
    status, unused_ = pgsettingpersistor.SettingPersistor.save(
      [self.settings], [self.session_source, self.persistent_source])
    self.assertEqual(status, pgsettingpersistor.SettingPersistor.SUCCESS)
    
    self.settings['file_extension'].set_value("jpg")
    self.settings['ignore_invisible'].set_value(False)
    
    status, unused_ = pgsettingpersistor.SettingPersistor.load(
      [self.settings], [self.session_source, self.persistent_source])
    self.assertEqual(status, pgsettingpersistor.SettingPersistor.SUCCESS)
    self.assertEqual(self.settings['file_extension'].value, "png")
    self.assertEqual(self.settings['ignore_invisible'].value, True)
  
  @mock.patch(LIB_NAME + ".pgsettingpersistor.gimpshelf.shelf", new=gimpmocks.MockGimpShelf())
  @mock.patch(LIB_NAME + ".pgsettingpersistor.gimp", new=gimpmocks.MockGimpParasite())
  def test_load_combine_settings_from_multiple_sources(self):
    self.settings['file_extension'].set_value("png")
    self.settings['ignore_invisible'].set_value(True)
    self.session_source.write([self.settings['file_extension']])
    self.settings['file_extension'].set_value("jpg")
    self.persistent_source.write([self.settings['ignore_invisible'], self.settings['file_extension']])
    self.settings['file_extension'].set_value("gif")
    self.settings['ignore_invisible'].set_value(False)
    
    pgsettingpersistor.SettingPersistor.load([self.settings], [self.session_source, self.persistent_source])
    
    self.assertEqual(self.settings['file_extension'].value, "png")
    self.assertEqual(self.settings['ignore_invisible'].value, True)
    
    for setting in self.settings:
      if setting not in [self.settings['file_extension'], self.settings['ignore_invisible']]:
        self.assertEqual(setting.value, setting.default_value)
  
  @mock.patch(LIB_NAME + ".pgsettingpersistor.gimpshelf.shelf", new=gimpmocks.MockGimpShelf())
  @mock.patch(LIB_NAME + ".pgsettingpersistor.gimp", new=gimpmocks.MockGimpParasite())
  def test_load_setting_groups(self):
    settings = create_test_settings_hierarchical()
    
    settings['main']['file_extension'].set_value("png")
    settings['advanced']['ignore_invisible'].set_value(True)
    self.session_source.write(list(settings.iterate_all()))
    settings['main']['file_extension'].set_value("gif")
    settings['advanced']['ignore_invisible'].set_value(False)
    
    pgsettingpersistor.SettingPersistor.load([settings], [self.session_source])
    
    self.assertEqual(settings['main']['file_extension'].value, "png")
    self.assertEqual(settings['advanced']['ignore_invisible'].value, True)
  
  @mock.patch(LIB_NAME + ".pgsettingpersistor.gimpshelf.shelf", new=gimpmocks.MockGimpShelf())
  @mock.patch(LIB_NAME + ".pgsettingpersistor.gimp", new=gimpmocks.MockGimpParasite())
  def test_load_settings_source_not_found(self):
    status, unused_ = pgsettingpersistor.SettingPersistor.load(
      [self.settings], [self.session_source, self.persistent_source])
    self.assertEqual(status, pgsettingpersistor.SettingPersistor.NOT_ALL_SETTINGS_FOUND)
  
  @mock.patch(LIB_NAME + ".pgsettingpersistor.gimpshelf.shelf", new=gimpmocks.MockGimpShelf())
  @mock.patch(LIB_NAME + ".pgsettingpersistor.gimp", new=gimpmocks.MockGimpParasite())
  def test_load_settings_not_found(self):
    self.session_source.write([self.settings['ignore_invisible']])
    self.persistent_source.write([self.settings['file_extension'], self.settings['ignore_invisible']])
    
    status, unused_ = pgsettingpersistor.SettingPersistor.load(
      [self.settings['overwrite_mode']], [self.session_source, self.persistent_source])
    self.assertEqual(status, pgsettingpersistor.SettingPersistor.NOT_ALL_SETTINGS_FOUND)
  
  @mock.patch(LIB_NAME + ".pgsettingpersistor.gimpshelf.shelf", new=gimpmocks.MockGimpShelf())
  @mock.patch(LIB_NAME + ".pgsettingpersistor.gimp", new=gimpmocks.MockGimpParasite())
  def test_load_read_fail(self):
    self.persistent_source.write(self.settings)
    
    # Simulate formatting error
    parasite = pgsettingpersistor.gimp.parasite_find(self.persistent_source.source_name)
    parasite.data = parasite.data[:-1]
    pgsettingpersistor.gimp.parasite_attach(parasite)
    
    status, unused_ = pgsettingpersistor.SettingPersistor.load(
      [self.settings], [self.session_source, self.persistent_source])
    self.assertEqual(status, pgsettingpersistor.SettingPersistor.READ_FAIL)

