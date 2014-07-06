#-------------------------------------------------------------------------------
#
# This file is part of libgimpplugin.
#
# Copyright (C) 2014 khalim19 <khalim19@gmail.com>
# 
# libgimpplugin is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# libgimpplugin is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with libgimpplugin.  If not, see <http://www.gnu.org/licenses/>.
#
#-------------------------------------------------------------------------------

#=============================================================================== 

import errno
from StringIO import StringIO
import unittest
import json

import gimpenums

from ..lib import mock

from .. import settings

from . import gimpmocks

#===============================================================================

LIB_NAME = '.'.join(__name__.split('.')[:-2])

#===============================================================================

class MockStringIO(StringIO):
  def read(self):
    return self.getvalue()


class MockGuiWidget(object):
  def __init__(self, value):
    self.value = value
    self.enabled = True
    self.visible = True


class MockSettingPresenter(settings.SettingPresenter):
  
  @property
  def value(self):
    return self._element.value
  @value.setter
  def value(self, val):
    self._element.value = val

  @property
  def enabled(self):
    return self._element.enabled
  @enabled.setter
  def enabled(self, val):
    self._element.enabled = val

  @property
  def visible(self):
    return self._element.visible
  @visible.setter
  def visible(self, val):
    self._element.visible = val

  def connect_event(self, *args):
    pass
  
  def set_tooltip(self):
    pass


class MockSettingPresenterContainer(settings.SettingPresenterContainer):
  
  def connect_value_changed_events(self):
    pass


class SettingContainerTest(settings.SettingContainer):
  
  def _create_settings(self):
    
    self._add(settings.NonEmptyStringSetting('file_format', ""))
    self._add(settings.BoolSetting('ignore_invisible', False))
    self._add(
      settings.EnumSetting(
       'overwrite_mode', 'rename_new',
       [('replace', "Replace"),
        ('skip', "Skip"),
        ('rename_new', "Rename new file"),
        ('rename_existing', "Rename existing file")])
      )
    
    self['file_format'].set_streamline_func(streamline_file_format, self['ignore_invisible'])
    self['overwrite_mode'].set_streamline_func(streamline_overwrite_mode, self['ignore_invisible'], self['file_format'])


def streamline_file_format(file_format, ignore_invisible):
  if ignore_invisible.value:
    file_format.value = "png"
    file_format.ui_enabled = False
  else:
    file_format.value = "jpg"
    file_format.ui_enabled = True


def streamline_overwrite_mode(overwrite_mode, ignore_invisible, file_format):
  if ignore_invisible.value:
    overwrite_mode.value = overwrite_mode.options['skip']
    file_format.error_messages['custom'] = "custom error message"
  else:
    overwrite_mode.value = overwrite_mode.options['replace']
    file_format.error_messages['custom'] = "different custom error message"

#===============================================================================

class TestSetting(unittest.TestCase):
  
  def setUp(self):
    self.setting = settings.Setting('file_format', "")
  
  def test_changed_attributes(self):
    for attr, val in [('value', "png"), ('ui_enabled', False), ('ui_visible', True)]:
      setattr(self.setting, attr, val)
    
    for attr in ['value', 'ui_enabled', 'ui_visible']:
      self.assertTrue(attr in self.setting.changed_attributes,
                      msg=("'" + attr + "' not in " + str(self.setting.changed_attributes)))
  
  def test_can_be_registered_to_pdb(self):
    self.setting.gimp_pdb_type = gimpenums.PDB_INT32
    self.assertEqual(self.setting.can_be_registered_to_pdb, True)
    
    self.setting.gimp_pdb_type = None
    self.assertEqual(self.setting.can_be_registered_to_pdb, False)
    
    with self.assertRaises(ValueError):
      self.setting.gimp_pdb_type = None
      self.setting.can_be_registered_to_pdb = True
  
  def test_reset(self):
    setting = settings.Setting('file_format', "")
    setting.value = "png"
    setting.reset()
    self.assertEqual(setting.value, "")
  
  def test_set_remove_streamline_func(self):
    with self.assertRaises(TypeError):
      self.setting.remove_streamline_func()
    
    with self.assertRaises(TypeError):
      self.setting.set_streamline_func(None)
    
    with self.assertRaises(TypeError):
      self.setting.set_streamline_func("this is not a function")
  
  def test_invalid_streamline(self):
    with self.assertRaises(TypeError):
      self.setting.streamline()
  
  def test_can_streamline(self):
    self.setting.set_streamline_func(streamline_file_format)
    self.assertTrue(self.setting.can_streamline)
    self.setting.remove_streamline_func()
    self.assertFalse(self.setting.can_streamline)
  
  def test_streamline(self):
    ignore_invisible = settings.BoolSetting('ignore_invisible', False)
    self.setting.value = "gif"
    self.setting.set_streamline_func(streamline_file_format, ignore_invisible)
    
    changed_settings = self.setting.streamline()
    self.assertTrue(self.setting in changed_settings)
    self.assertTrue('ui_enabled' in changed_settings[self.setting])
    self.assertTrue('value' in changed_settings[self.setting])
    self.assertEqual(self.setting.ui_enabled, True)
    self.assertEqual(self.setting.value, "jpg")
  
  def test_streamline_force(self):
    ignore_invisible = settings.BoolSetting('ignore_invisible', False)
    self.setting.set_streamline_func(streamline_file_format, ignore_invisible)
    
    changed_settings = self.setting.streamline()
    self.assertEqual({}, changed_settings)
    
    changed_settings = self.setting.streamline(force=True)
    self.assertTrue(self.setting in changed_settings)


class TestIntSetting(unittest.TestCase):
  
  def setUp(self):
    self.setting = settings.IntSetting('count', 0)
    self.setting.min_value = 0
    self.setting.max_value = 100
  
  def test_below_min(self):
    with self.assertRaises(ValueError):
      self.setting.value = -5
  
  def test_above_max(self):
    with self.assertRaises(ValueError):
      self.setting.value = 200


class TestFloatSetting(unittest.TestCase):
  
  def setUp(self):
    self.setting = settings.FloatSetting('clip_percent', 0.0)
    self.setting.min_value = 0.0
    self.setting.max_value = 100.0
  
  def test_below_min(self):
    with self.assertRaises(ValueError):
      self.setting.value = -5.0
    
    try:
      self.setting.value = 0.0
    except ValueError:
      self.fail("ValueError should not be raised")
  
  def test_above_max(self):
    with self.assertRaises(ValueError):
      self.setting.value = 200.0
    
    try:
      self.setting.value = 100.0
    except ValueError:
      self.fail("ValueError should not be raised")


class TestEnumSetting(unittest.TestCase):
  
  def setUp(self):
    self.setting_display_name = "Overwrite mode (non-interactive only)"
    
    self.setting = settings.EnumSetting(
      'overwrite_mode', 'replace',
      [('skip', "Skip"),
       ('replace', "Replace")])
    self.setting.display_name = self.setting_display_name
  
  def test_explicit_values(self):
    
    setting = settings.EnumSetting(
      'overwrite_mode', 'replace',
      [('skip', "Skip", 5),
       ('replace', "Replace", 6)])
    self.assertEqual(setting.options['skip'], 5)
    self.assertEqual(setting.options['replace'], 6)
    
    with self.assertRaises(ValueError):
      settings.EnumSetting(
        'overwrite_mode', 'replace',
        [('skip', "Skip", 4),
         ('replace', "Replace")])
    
    with self.assertRaises(ValueError):
      settings.EnumSetting(
        'overwrite_mode', 'replace',
        [('skip', "Skip", 4),
         ('replace', "Replace", 4)])
  
  def test_invalid_default_value(self):
    with self.assertRaises(ValueError):
      settings.EnumSetting(
        'overwrite_mode', 'invalid_default_value',
        [('skip', "Skip"),
         ('replace', "Replace")])
  
  def test_set_invalid_option(self):
    with self.assertRaises(ValueError):
      self.setting.value = 4
    with self.assertRaises(ValueError):
      self.setting.value = -1
  
  def test_get_invalid_option(self):
    with self.assertRaises(KeyError):
      self.setting.options['invalid_option']
  
  def test_display_name(self):
    self.assertEqual(self.setting.display_name, self.setting_display_name)
  
  def test_short_description(self):
    self.assertEqual(self.setting.short_description,
                     self.setting_display_name + " { Skip (0), Replace (1) }")
  
  def test_get_option_display_names_and_values(self):
    option_display_names_and_values = self.setting.get_option_display_names_and_values()
    self.assertEqual(option_display_names_and_values,
                     ["Skip", 0, "Replace", 1])


class TestImageSetting(unittest.TestCase):
  
  def setUp(self):
    self.setting = settings.ImageSetting('image', None)
  
  @mock.patch(LIB_NAME + '.settings.pdb', new=gimpmocks.MockPDB())
  def test_invalid_image(self):
    pdb = gimpmocks.MockPDB()
    image = pdb.gimp_image_new(2, 2, gimpenums.RGB)
    pdb.gimp_image_delete(image)
    with self.assertRaises(ValueError):
      self.setting.value = image


class TestNonEmptyStringSetting(unittest.TestCase):
  
  def setUp(self):
    self.setting = settings.NonEmptyStringSetting('file_format', "")
  
  def test_invalid_string(self):
    with self.assertRaises(ValueError):
      self.setting.value = ""
    with self.assertRaises(ValueError):
      self.setting.value = None

#===============================================================================

class TestSettingContainer(unittest.TestCase):
  
  def setUp(self):
    self.settings = SettingContainerTest()
      
  def test_get_setting_invalid_key(self):
    with self.assertRaises(KeyError):
      self.settings['invalid_key']
  
  def test_streamline(self):
    self.settings.streamline(force=True)
    self.assertEqual(self.settings['file_format'].value, "jpg")
    self.assertEqual(self.settings['file_format'].ui_enabled, True)
    self.assertEqual(self.settings['overwrite_mode'].value, self.settings['overwrite_mode'].options['replace'])
  
  def test_reset(self):
    self.settings['overwrite_mode'].value = self.settings['overwrite_mode'].options['rename_new']
    self.settings['file_format'].value = "jpg"
    self.settings['file_format'].can_be_reset_by_container = False
    self.settings.reset()
    self.assertEqual(self.settings['overwrite_mode'].value, self.settings['overwrite_mode'].default_value)
    self.assertNotEqual(self.settings['file_format'].value, self.settings['file_format'].default_value)
    self.assertEqual(self.settings['file_format'].value, "jpg")

#===============================================================================

class TestSettingPresenterContainer(unittest.TestCase):
  
  def setUp(self):
    self.settings = SettingContainerTest()
    self.element = MockGuiWidget("")
    self.setting_presenter = MockSettingPresenter(self.settings['file_format'], self.element)
    
    self.presenter_container = MockSettingPresenterContainer()
    self.presenter_container.add(self.setting_presenter)
    self.presenter_container.add(MockSettingPresenter(self.settings['overwrite_mode'], self.element))
    self.presenter_container.add(MockSettingPresenter(self.settings['ignore_invisible'], self.element))
  
  def test_get_item(self):
    self.assertEqual(self.presenter_container[self.settings['file_format']], self.setting_presenter)

#===============================================================================

class TestShelfSettingStream(unittest.TestCase):
  
  @mock.patch(LIB_NAME + '.settings.shelf', new=gimpmocks.MockGimpShelf())
  def setUp(self):
    self.prefix = 'prefix'
    self.stream = settings.GimpShelfSettingStream(self.prefix)
    self.settings = SettingContainerTest()
  
  @mock.patch(LIB_NAME + '.settings.shelf', new=gimpmocks.MockGimpShelf())
  def test_write(self):
    self.settings['file_format'].value = "png"
    self.settings['ignore_invisible'].value = True
    self.stream.write(self.settings)
    
    self.assertEqual(settings.shelf[self.prefix + 'file_format'], "png")
    self.assertEqual(settings.shelf[self.prefix + 'ignore_invisible'], True)
  
  @mock.patch(LIB_NAME + '.settings.shelf', new=gimpmocks.MockGimpShelf())
  def test_read(self):
    settings.shelf[self.prefix + 'file_format'] = "png"
    settings.shelf[self.prefix + 'ignore_invisible'] = True
    self.stream.read([self.settings['file_format'], self.settings['ignore_invisible']])
    self.assertEqual(self.settings['file_format'].value, "png")
    self.assertEqual(self.settings['ignore_invisible'].value, True)
  
  @mock.patch(LIB_NAME + '.settings.shelf', new=gimpmocks.MockGimpShelf())
  def test_read_settings_not_found(self):
    with self.assertRaises(settings.SettingsNotFoundInStreamError):
      self.stream.read(self.settings)
  
  @mock.patch(LIB_NAME + '.settings.shelf', new=gimpmocks.MockGimpShelf())
  def test_read_invalid_setting_value(self):
    setting_with_invalid_value = settings.NonEmptyStringSetting('file_format', "")
    self.stream.write([setting_with_invalid_value])
    self.stream.read([setting_with_invalid_value])
    self.assertEqual(setting_with_invalid_value.value, setting_with_invalid_value.default_value)


@mock.patch('__builtin__.open')
class TestJSONFileSettingStream(unittest.TestCase):
  
  def setUp(self):
    self.stream = settings.JSONFileSettingStream("/test/file")
    self.settings = SettingContainerTest()
    self.setting_with_invalid_value = settings.NonEmptyStringSetting('file_format', "")
  
  def test_write(self, mock_file):
    self.settings['file_format'].value = "jpg"
    self.settings['ignore_invisible'].value = True
    
    mock_file.return_value.__enter__.return_value = MockStringIO()
    file_ = mock_file.return_value.__enter__.return_value
    
    self.stream.write(self.settings)
    settings = json.loads(file_.read())
    self.assertEqual(self.settings['file_format'].value, "jpg")
    self.assertEqual(self.settings['ignore_invisible'].value, True)
  
  def test_read(self, mock_file):
    self.settings['file_format'].value = "jpg"
    self.settings['ignore_invisible'].value = True
    
    mock_file.return_value.__enter__.return_value = MockStringIO()
    
    self.stream.write(self.settings)
    self.stream.read(self.settings)
    self.assertEqual(self.settings['file_format'].value, "jpg")
    self.assertEqual(self.settings['ignore_invisible'].value, True)
  
  def test_write_ioerror_oserror(self, mock_file):
    mock_file.side_effect = IOError("Whatever other I/O error it could be")
    with self.assertRaises(settings.SettingStreamWriteError):
      self.stream.write(self.settings)
    
    mock_file.side_effect = OSError("Permission denied or whatever other OS error it could be")
    with self.assertRaises(settings.SettingStreamWriteError):
      self.stream.write(self.settings)
  
  def test_read_ioerror_oserror(self, mock_file):
    mock_file.side_effect = IOError("File not found or whatever other I/O error it could be")
    with self.assertRaises(settings.SettingStreamReadError):
      self.stream.read(self.settings)
    
    mock_file.side_effect = OSError("Permission denied or whatever other OS error it could be")
    with self.assertRaises(settings.SettingStreamReadError):
      self.stream.read(self.settings)

  def test_read_invalid_file_format(self, mock_file):
    mock_file.side_effect = ValueError("Invalid file format; must be JSON")
    with self.assertRaises(settings.SettingStreamInvalidFormatError):
      self.stream.read(self.settings)

  def test_read_invalid_setting_value(self, mock_file):
    mock_file.return_value.__enter__.return_value = MockStringIO()
    
    self.stream.write([self.setting_with_invalid_value])
    self.stream.read([self.setting_with_invalid_value])
    self.assertEqual(self.setting_with_invalid_value.value, self.setting_with_invalid_value.default_value)
  
  def test_read_settings_not_found(self, mock_file):
    mock_file.return_value.__enter__.return_value = MockStringIO()
    
    self.stream.write([self.setting_with_invalid_value])
    with self.assertRaises(settings.SettingsNotFoundInStreamError):
      self.stream.read(self.settings)

#===============================================================================

@mock.patch('__builtin__.open')
class TestSettingPersistor(unittest.TestCase):
  
  @mock.patch(LIB_NAME + '.settings.shelf', new=gimpmocks.MockGimpShelf())
  def setUp(self):
    self.settings = SettingContainerTest()
    self.first_stream = settings.GimpShelfSettingStream('')
    self.second_stream = settings.JSONFileSettingStream('filename')
    self.setting_persistor = settings.SettingPersistor([self.first_stream, self.second_stream],
                                                       [self.first_stream, self.second_stream])
  
  @mock.patch(LIB_NAME + '.settings.shelf', new=gimpmocks.MockGimpShelf())
  def test_load_save(self, mock_file):
    mock_file.return_value.__enter__.return_value = MockStringIO()
    
    self.settings['file_format'].value = "png"
    self.settings['ignore_invisible'].value = True
    
    status = self.setting_persistor.save(self.settings)
    self.assertEqual(status, settings.SettingPersistor.SUCCESS)
    
    self.settings['file_format'].value = "jpg"
    self.settings['ignore_invisible'].value = False
    
    status = self.setting_persistor.load(self.settings)
    self.assertEqual(status, settings.SettingPersistor.SUCCESS)
    self.assertEqual(self.settings['file_format'].value, "png")
    self.assertEqual(self.settings['ignore_invisible'].value, True)
  
  @mock.patch(LIB_NAME + '.settings.shelf', new=gimpmocks.MockGimpShelf())
  def test_load_combine_settings_from_multiple_streams(self, mock_file):
    mock_file.return_value.__enter__.return_value = MockStringIO()
    
    self.settings['file_format'].value = "png"
    self.settings['ignore_invisible'].value = True
    self.first_stream.write([self.settings['file_format']])
    self.settings['file_format'].value = "jpg"
    self.second_stream.write([self.settings['ignore_invisible'], self.settings['file_format']])
    self.settings['file_format'].value = "gif"
    self.settings['ignore_invisible'].value = False
    
    self.setting_persistor.load(self.settings)
    
    self.assertEqual(self.settings['file_format'].value, "png")
    self.assertEqual(self.settings['ignore_invisible'].value, True)
    
    for setting in self.settings:
      if setting not in [self.settings['file_format'], self.settings['ignore_invisible']]:
        self.assertEqual(setting.value, setting.default_value)
  
  @mock.patch(LIB_NAME + '.settings.shelf', new=gimpmocks.MockGimpShelf())
  def test_load_settings_file_not_found(self, mock_file):
    mock_file.return_value.__enter__.return_value = MockStringIO()
    mock_file.side_effect = IOError("File not found")
    mock_file.side_effect.errno = errno.ENOENT
    
    status = self.setting_persistor.load(self.settings)
    self.assertEqual(status, settings.SettingPersistor.NOT_ALL_SETTINGS_FOUND)
    
  @mock.patch(LIB_NAME + '.settings.shelf', new=gimpmocks.MockGimpShelf())
  def test_load_settings_not_found(self, mock_file):
    mock_file.return_value.__enter__.return_value = MockStringIO()
    self.first_stream.write([self.settings['ignore_invisible']])
    self.second_stream.write([self.settings['file_format'], self.settings['ignore_invisible']])
    
    status = self.setting_persistor.load([self.settings['overwrite_mode']])
    self.assertEqual(status, settings.SettingPersistor.NOT_ALL_SETTINGS_FOUND)
  
  @mock.patch(LIB_NAME + '.settings.shelf', new=gimpmocks.MockGimpShelf())
  def test_load_read_fail(self, mock_file):
    mock_file.return_value.__enter__.return_value = MockStringIO()
    
    status = self.setting_persistor.load(self.settings)
    self.assertEqual(status, settings.SettingPersistor.READ_FAIL)
    
    mock_file.side_effect = IOError()
    status = self.setting_persistor.load(self.settings)
    self.assertEqual(status, settings.SettingPersistor.READ_FAIL)
    
    mock_file.side_effect = OSError()
    status = self.setting_persistor.load(self.settings)
    self.assertEqual(status, settings.SettingPersistor.READ_FAIL)
  
  @mock.patch(LIB_NAME + '.settings.shelf', new=gimpmocks.MockGimpShelf())
  def test_save_write_fail(self, mock_file):
    mock_file.return_value.__enter__.return_value = MockStringIO()
    
    mock_file.side_effect = IOError()
    status = self.setting_persistor.save(self.settings)
    self.assertEqual(status, settings.SettingPersistor.WRITE_FAIL)
    
    mock_file.side_effect = OSError()
    status = self.setting_persistor.save(self.settings)
    self.assertEqual(status, settings.SettingPersistor.WRITE_FAIL)
    
