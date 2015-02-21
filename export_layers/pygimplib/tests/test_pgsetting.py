#-------------------------------------------------------------------------------
#
# This file is part of pygimplib.
#
# Copyright (C) 2014 khalim19 <khalim19@gmail.com>
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

"""
This module tests the `pgsetting` and `pgsettingpresenter` modules.
"""

#===============================================================================

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division

str = unicode

#===============================================================================

import os

import unittest

import gimpenums

from ..lib import mock
from . import gimpmocks

from .. import pgsetting
from .. import pgsettingpresenter
from .. import pgpath

#===============================================================================

LIB_NAME = '.'.join(__name__.split('.')[:-2])

#===============================================================================


class MockSetting(pgsetting.Setting):
  
  def _init_error_messages(self):
    self._error_messages['value_is_none'] = "value cannot be None"
  
  def _validate(self, value):
    if value is None:
      raise pgsetting.SettingValueError(self._error_messages['value_is_none'])


def on_file_extension_changed(file_extension, ignore_invisible):
  if file_extension.value == "png":
    ignore_invisible.set_value(False)
    ignore_invisible.gui.set_enabled(True)
  else:
    ignore_invisible.set_value(True)
    ignore_invisible.gui.set_enabled(False)


def on_autocrop_changed(autocrop, file_extension):
  if autocrop.value:
    file_extension.set_value("jpg")


class MockGuiWidget(object):
  
  def __init__(self, value):
    self.value = value
    self.enabled = True
    self.visible = True
    
    self._signal = None
    self._event_handler = None
  
  def connect(self, signal, event_handler):
    self._signal = signal
    self._event_handler = event_handler
  
  def set_value(self, value):
    self.value = value
    if self._event_handler is not None:
      self._event_handler()
  

class MockSettingPresenter(pgsettingpresenter.SettingPresenter):

  def get_enabled(self):
    return self._element.enabled
  
  def set_enabled(self, value):
    self._element.enabled = value

  def get_visible(self):
    return self._element.visible
  
  def set_visible(self, value):
    self._element.visible = value
  
  def _get_value(self):
    return self._element.value
  
  def _set_value(self, value):
    self._element.value = value
  
  def _connect_value_changed_event(self):
    self._element.connect(self._VALUE_CHANGED_SIGNAL, self._on_value_changed)


class MockSettingPresenterWithValueChangedSignal(MockSettingPresenter):
  
  _VALUE_CHANGED_SIGNAL = "changed"


#===============================================================================


class TestSetting(unittest.TestCase):
  
  def setUp(self):
    self.setting = pgsetting.Setting('file_extension', "png")
  
  def test_invalid_default_value_raises_error(self):
    with self.assertRaises(pgsetting.SettingDefaultValueError):
      MockSetting('setting', None)
  
  def test_default_value_without_validation(self):
    try:
      MockSetting('setting', None, validate_default_value=False)
    except pgsetting.SettingDefaultValueError:
      self.fail("SettingDefaultValueError should not be raised, default value validation is turned off")
  
  def test_value_invalid_assignment_operation(self):
    with self.assertRaises(AttributeError):
      self.setting.value = "jpg"
  
  def test_connect_value_changed_event_argument_is_not_callable(self):
    with self.assertRaises(TypeError):
      self.setting.connect_value_changed_event(None)
  
  def test_value_changed_event(self):
    ignore_invisible = pgsetting.BoolSetting('ignore_invisible', False)
    self.setting.connect_value_changed_event(on_file_extension_changed, ignore_invisible)
    
    self.setting.set_value("jpg")
    self.assertEqual(ignore_invisible.value, True)
    self.assertEqual(ignore_invisible.gui.get_enabled(), False)
  
  def test_value_changed_event_nested(self):
    ignore_invisible = pgsetting.BoolSetting('ignore_invisible', False)
    self.setting.connect_value_changed_event(on_file_extension_changed, ignore_invisible)
    
    autocrop = pgsetting.BoolSetting('autocrop', False)
    autocrop.connect_value_changed_event(on_autocrop_changed, self.setting)
    
    autocrop.set_value(True)
    
    self.assertEqual(self.setting.value, "jpg")
    self.assertEqual(ignore_invisible.value, True)
    self.assertEqual(ignore_invisible.gui.get_enabled(), False)
  
  def test_remove_value_changed_event(self):
    ignore_invisible = pgsetting.BoolSetting('ignore_invisible', False)
    self.setting.connect_value_changed_event(on_file_extension_changed, ignore_invisible)
    self.setting.remove_value_changed_event()
    
    self.setting.set_value("jpg")
    # `ignore_invisible` should not change
    self.assertEqual(ignore_invisible.value, ignore_invisible.default_value)
    self.assertEqual(ignore_invisible.gui.get_enabled(), True)
  
  def test_remove_value_changed_event_no_previous_event_handler_set(self):
    with self.assertRaises(TypeError):
      self.setting.remove_value_changed_event()
  
  def test_auto_generated_display_name(self):
    self.assertEqual(pgsetting.Setting('this_is_a_setting', "png").display_name, "This is a setting")
  
  def test_custom_error_messages(self):
    setting = MockSetting('setting', "")
    
    setting_with_custom_error_messages = MockSetting(
      'setting', "", error_messages={'value_is_none' : 'this should override the original error message',
                                     'invalid_value' : 'value is invalid'})
    self.assertIn('invalid_value', setting_with_custom_error_messages.error_messages)
    self.assertNotEqual(setting.error_messages['value_is_none'],
                        setting_with_custom_error_messages.error_messages['value_is_none'])
  
  def test_pdb_registration_mode_automatic_is_registrable(self):
    setting = pgsetting.Setting('file_extension', "png", pdb_type=gimpenums.PDB_STRING)
    self.assertEqual(setting.pdb_registration_mode, pgsetting.PdbRegistrationModes.registrable)
  
  def test_pdb_registration_mode_automatic_is_not_registrable(self):
    setting = pgsetting.Setting('file_extension', "png", pdb_type=None)
    self.assertEqual(setting.pdb_registration_mode, pgsetting.PdbRegistrationModes.not_registrable)
  
  def test_invalid_pdb_type_and_registration_mode_raises_error(self):
    with self.assertRaises(ValueError):
      pgsetting.Setting('file_extension', "png", pdb_type=None,
                        pdb_registration_mode=pgsetting.PdbRegistrationModes.registrable)
  
  def test_reset_resets_setting_to_default_value(self):
    self.setting.set_value("jpg")
    self.setting.reset()
    self.assertEqual(self.setting.value, "png")
  
  def test_reset_triggers_value_changed_event(self):
    ignore_invisible = pgsetting.BoolSetting('ignore_invisible', False)
    self.setting.connect_value_changed_event(on_file_extension_changed, ignore_invisible)
    
    self.setting.set_value("jpg")
    self.setting.reset()
    self.assertEqual(ignore_invisible.value, ignore_invisible.default_value)
    self.assertEqual(ignore_invisible.gui.get_enabled(), True)


class TestSettingGui(unittest.TestCase):
  
  def setUp(self):
    self.setting = pgsetting.Setting('file_extension', "png")
    self.widget = MockGuiWidget("")
  
  def test_set_gui_updates_gui_value(self):
    self.setting.set_gui(MockSettingPresenter, self.widget)
    self.assertEqual(self.widget.value, "png")
  
  def test_setting_set_value_updates_gui(self):
    self.setting.set_gui(MockSettingPresenter, self.widget)
    self.setting.set_value("gif")
    self.assertEqual(self.widget.value, "gif")
  
  def test_set_gui_preserves_gui_state(self):
    self.setting.gui.set_enabled(False)
    self.setting.gui.set_visible(False)
    self.setting.set_value("gif")
    
    self.setting.set_gui(MockSettingPresenter, self.widget)
    
    self.assertEqual(self.setting.gui.get_enabled(), False)
    self.assertEqual(self.setting.gui.get_visible(), False)
    self.assertEqual(self.widget.value, "gif")
  
  def test_update_setting_value_manually(self):
    self.setting.set_gui(MockSettingPresenter, self.widget)
    self.widget.set_value("jpg")
    self.assertEqual(self.setting.value, "png")
    
    self.setting.gui.update_setting_value()
    self.assertEqual(self.setting.value, "jpg")
  
  def test_update_setting_value_automatically(self):
    self.setting.set_gui(MockSettingPresenterWithValueChangedSignal, self.widget)
    self.widget.set_value("jpg")
    self.assertEqual(self.setting.value, "jpg")
  
  def test_update_setting_value_triggers_event(self):
    self.setting.set_gui(MockSettingPresenterWithValueChangedSignal, self.widget)
    
    ignore_invisible = pgsetting.BoolSetting('ignore_invisible', False)
    self.setting.connect_value_changed_event(on_file_extension_changed, ignore_invisible)
    
    self.widget.set_value("jpg")
    self.assertEqual(self.setting.value, "jpg")
    self.assertEqual(ignore_invisible.value, True)
    self.assertEqual(ignore_invisible.gui.get_enabled(), False)
  
  def test_reset_updates_gui(self):
    self.setting.set_gui(MockSettingPresenter, self.widget)
    self.setting.set_value("jpg")
    self.setting.reset()
    self.assertEqual(self.widget.value, "png")


#-------------------------------------------------------------------------------


class TestIntSetting(unittest.TestCase):
  
  def setUp(self):
    self.setting = pgsetting.IntSetting('count', 0, min_value=0, max_value=100)
  
  def test_value_is_below_min(self):
    with self.assertRaises(pgsetting.SettingValueError):
      self.setting.set_value(-5)
  
  def test_min_value_does_not_raise_error(self):
    try:
      self.setting.set_value(0)
    except pgsetting.SettingValueError:
      self.fail("SettingValueError should not be raised")
  
  def test_value_is_above_max(self):
    with self.assertRaises(pgsetting.SettingValueError):
      self.setting.set_value(200)
  
  def test_max_value_does_not_raise_error(self):
    try:
      self.setting.set_value(100)
    except pgsetting.SettingValueError:
      self.fail("SettingValueError should not be raised")


class TestFloatSetting(unittest.TestCase):
  
  def setUp(self):
    self.setting = pgsetting.FloatSetting('clip_percent', 0.0, min_value=0.0, max_value=100.0)
  
  def test_value_below_min(self):
    with self.assertRaises(pgsetting.SettingValueError):
      self.setting.set_value(-5.0)
  
  def test_minimum_value_does_not_raise_error(self):
    try:
      self.setting.set_value(0.0)
    except pgsetting.SettingValueError:
      self.fail("SettingValueError should not be raised")
  
  def test_value_above_max(self):
    with self.assertRaises(pgsetting.SettingValueError):
      self.setting.set_value(200.0)
  
  def test_maximum_value_does_not_raise_error(self):
    try:
      self.setting.set_value(100.0)
    except pgsetting.SettingValueError:
      self.fail("SettingValueError should not be raised")


class TestEnumSetting(unittest.TestCase):
  
  def setUp(self):
    self.setting = pgsetting.EnumSetting(
      'overwrite_mode', 'replace',
      [('skip', "Skip"), ('replace', "Replace")],
      display_name="Overwrite mode (non-interactive only)")
  
  def test_explicit_values(self):
    setting = pgsetting.EnumSetting(
      'overwrite_mode', 'replace',
      [('skip', "Skip", 5),
       ('replace', "Replace", 6)])
    self.assertEqual(setting.items['skip'], 5)
    self.assertEqual(setting.items['replace'], 6)
    
    with self.assertRaises(ValueError):
      pgsetting.EnumSetting(
        'overwrite_mode', 'replace',
        [('skip', "Skip", 4),
         ('replace', "Replace")])
    
    with self.assertRaises(ValueError):
      pgsetting.EnumSetting(
        'overwrite_mode', 'replace',
        [('skip', "Skip", 4),
         ('replace', "Replace", 4)])
  
  def test_invalid_default_value(self):
    with self.assertRaises(pgsetting.SettingDefaultValueError):
      pgsetting.EnumSetting(
        'overwrite_mode', 'invalid_default_value',
        [('skip', "Skip"),
         ('replace', "Replace")])
  
  def test_default_value_no_validation(self):
    try:
      pgsetting.EnumSetting(
        'overwrite_mode', None,
        [('skip', "Skip"),
         ('replace', "Replace")],
        validate_default_value=False)
    except pgsetting.SettingDefaultValueError:
      self.fail("SettingDefaultValueError should not be raised, default value validation is turned off")
  
  def test_invalid_items_length_varying(self):
    with self.assertRaises(ValueError):
      pgsetting.EnumSetting(
          'overwrite_mode', None,
          [('skip', "Skip", 1),
           ('replace', "Replace")])
  
  def test_invalid_items_length_too_many_elements(self):
    with self.assertRaises(ValueError):
      pgsetting.EnumSetting(
          'overwrite_mode', None,
          [('skip', "Skip", 1, 1),
           ('replace', "Replace", 1, 1)])
  
  def test_invalid_items_length_too_few_elements(self):
    with self.assertRaises(ValueError):
      pgsetting.EnumSetting(
          'overwrite_mode', None,
          [('skip'),
           ('replace')])
  
  def test_set_invalid_item(self):
    with self.assertRaises(pgsetting.SettingValueError):
      self.setting.set_value(4)
    with self.assertRaises(pgsetting.SettingValueError):
      self.setting.set_value(-1)
  
  def test_get_invalid_item(self):
    with self.assertRaises(KeyError):
      self.setting.items['invalid_item']
  
  def test_short_description(self):
    self.assertEqual(self.setting.short_description,
                     self.setting.display_name + " { Skip (0), Replace (1) }")
  
  def test_get_item_display_names_and_values(self):
    self.assertEqual(self.setting.get_item_display_names_and_values(), ["Skip", 0, "Replace", 1])


class TestImageSetting(unittest.TestCase):
  
  def setUp(self):
    self.setting = pgsetting.ImageSetting('image', None, validate_default_value=False)
  
  @mock.patch(LIB_NAME + '.pgsetting.pdb', new=gimpmocks.MockPDB())
  def test_invalid_image(self):
    pdb = gimpmocks.MockPDB()
    image = pdb.gimp_image_new(2, 2, gimpenums.RGB)
    pdb.gimp_image_delete(image)
    with self.assertRaises(pgsetting.SettingValueError):
      self.setting.set_value(image)


class TestFileExtensionSetting(unittest.TestCase):
  
  def setUp(self):
    self.setting = pgsetting.FileExtensionSetting('file_ext', "png")
  
  def test_invalid_default_value(self):
    with self.assertRaises(pgsetting.SettingDefaultValueError):
      pgsetting.FileExtensionSetting('file_ext', None)
  
  def test_custom_error_message(self):
    self.setting.error_messages[pgpath.FileExtensionValidator.IS_EMPTY] = "My Custom Message"
    try:
      self.setting.set_value("")
    except pgsetting.SettingValueError as e:
      self.assertEqual(e.message, "My Custom Message")


class TestDirectorySetting(unittest.TestCase):
  
  def setUp(self):
    self.setting = pgsetting.DirectorySetting('output_directory', 'C:\\')
  
  def test_update_current_directory_with_current_image_filename(self):
    image = gimpmocks.MockImage()
    filename = "/test/image.png"
    image.filename = filename
    self.setting.update_current_directory(image, None)
    self.assertEqual(self.setting.value, os.path.dirname(filename))
  
  def test_update_current_directory_with_custom_directory(self):
    image = gimpmocks.MockImage()
    
    custom_directory = "/custom/directory"
    image.filename = None
    self.setting.update_current_directory(image, custom_directory)
    self.assertEqual(self.setting.value, custom_directory)
    
    image.filename = "/test/image.png"
    self.setting.update_current_directory(image, custom_directory)
    self.assertEqual(self.setting.value, custom_directory)


#-------------------------------------------------------------------------------


class TestImageIDsAndDirectoriesSetting(unittest.TestCase):
  
  def setUp(self):
    self.setting = pgsetting.ImageIDsAndDirectoriesSetting('image_ids_and_directories', {})
    
    self.image_ids_and_filenames = [(0, None), (1, "C:\\image.png"), (2, "/test/test.jpg"), (4, "/test/another_test.gif")]
    self.image_list = self._create_image_list(self.image_ids_and_filenames)
    self.image_ids_and_directories = self._create_image_ids_and_directories(self.image_list)
    
    self.setting.set_value(self.image_ids_and_directories)
  
  def get_image_list(self):
    # `self.image_list` is wrapped into a method so that `mock.patch.object` can be called on it.
    return self.image_list
  
  def _create_image_list(self, image_ids_and_filenames):
    return [self._create_image(image_id, filename) for image_id, filename in image_ids_and_filenames]
  
  def _create_image(self, image_id, filename):
    image = gimpmocks.MockImage()
    image.ID = image_id
    image.filename = filename
    return image
  
  def _create_image_ids_and_directories(self, image_list):
    image_ids_and_directories = {}
    for image in image_list:
      directory = os.path.dirname(image.filename) if image.filename is not None else None
      image_ids_and_directories[image.ID] = directory
    return image_ids_and_directories
  
  def test_update_image_ids_and_directories_add_new_images(self):
    self.image_list.extend(self._create_image_list([(5, "/test/new_image.png"), (6, None)]))
    
    with mock.patch(LIB_NAME + '.pgsetting.gimp.image_list', new=self.get_image_list):
      self.setting.update_image_ids_and_directories()
    
    self.assertEqual(self.setting.value, self._create_image_ids_and_directories(self.image_list))
  
  def test_update_image_ids_and_directories_remove_closed_images(self):
    self.image_list.pop(1)
    
    with mock.patch(LIB_NAME + '.pgsetting.gimp.image_list', new=self.get_image_list):
      self.setting.update_image_ids_and_directories()
    
    self.assertEqual(self.setting.value, self._create_image_ids_and_directories(self.image_list))
  
  def test_update_directory(self):
    directory = "test_directory"
    self.setting.update_directory(1, directory)
    self.assertEqual(self.setting.value[1], directory)
  
  def test_update_directory_invalid_image_id(self):
    with self.assertRaises(KeyError):
      self.setting.update_directory(-1, "test_directory")
  
  def test_value_setitem_does_not_change_setting_value(self):
    image_id_to_test = 1
    test_directory = "test_directory"
    self.setting.value[image_id_to_test] = test_directory
    self.assertNotEqual(self.setting.value[image_id_to_test], test_directory)
    self.assertEqual(self.setting.value[image_id_to_test], self.image_ids_and_directories[image_id_to_test])
  