# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import unittest

from ...setting import group as group_
from ...setting import settings as settings_
from ...setting import utils as utils_

from . import stubs_setting


class TestGetProcessedSettingAttribute(unittest.TestCase):
  
  def test_get_processed_display_name(self):
    self.assertEqual(
      utils_.get_processed_display_name(
        None, 'my_setting_name'), 'My setting name')
    self.assertEqual(
      utils_.get_processed_display_name(
        'My display name', 'my_setting_name'), 'My display name')
  
  def test_get_processed_description(self):
    self.assertEqual(
      utils_.get_processed_description(
        None, 'My _Setting Name'), 'My Setting Name')
    self.assertEqual(
      utils_.get_processed_description(
        'My description', 'My _Setting Name'), 'My description')


def _create_test_settings_for_path():
  setting = stubs_setting.StubSetting('file_extension')
  main_settings = group_.Group('main')
  advanced_settings = group_.Group('advanced')
  
  advanced_settings.add([setting])
  main_settings.add([advanced_settings])
  
  return setting, advanced_settings, main_settings


class TestSettingParentMixin(unittest.TestCase):
  
  def setUp(self):
    self.setting, self.advanced_settings, self.main_settings = (
      _create_test_settings_for_path())
  
  def test_get_parent_empty(self):
    setting = stubs_setting.StubSetting('file_extension')
    
    self.assertEqual(setting.parent, None)
  
  def test_get_parent(self):
    self.assertEqual(self.setting.parent, self.advanced_settings)
    self.assertEqual(self.advanced_settings.parent, self.main_settings)
    self.assertEqual(self.main_settings.parent, None)
  
  def test_get_parents(self):
    self.assertEqual(self.setting.parents, [self.main_settings, self.advanced_settings])
    self.assertEqual(self.advanced_settings.parents, [self.main_settings])
    self.assertEqual(self.main_settings.parents, [])


class TestSettingEventsMixin(unittest.TestCase):
  
  def setUp(self):
    self.file_extension = stubs_setting.StubSetting('file_extension', default_value='png')
    self.flatten = settings_.BoolSetting('flatten', default_value=False)
  
  def test_connect_event_argument_is_not_callable(self):
    with self.assertRaises(TypeError):
      self.file_extension.connect_event('test-event', None)
  
  def test_events_are_unique_for_one_instance_and_across_instances(self):
    event_ids = set()
    
    event_ids.add(self.file_extension.connect_event('test-event', lambda *args: None))
    event_ids.add(self.file_extension.connect_event('test-event', lambda *args: None))
    event_ids.add(self.flatten.connect_event('test-event', lambda *args: None))
    
    self.assertEqual(len(event_ids), 3)
  
  def test_invoke_event(self):
    self.flatten.set_value(True)
    self.file_extension.connect_event(
      'test-event', stubs_setting.on_file_extension_changed, self.flatten)
    
    self.file_extension.invoke_event('test-event')
    
    self.assertEqual(self.file_extension.value, 'png')
    self.assertFalse(self.flatten.value)
  
  def test_invoke_event_with_arguments(self):
    self.flatten.set_value(True)
    self.file_extension.connect_event('test-event', stubs_setting.on_file_extension_changed)
    
    self.file_extension.invoke_event('test-event', self.flatten)
    
    self.assertEqual(self.file_extension.value, 'png')
    self.assertFalse(self.flatten.value)
  
  def test_connect_event_with_keyword_arguments(self):
    use_layer_size = settings_.BoolSetting('use_layer_size', default_value=False)
    use_layer_size.connect_event(
      'test-event',
      stubs_setting.on_use_layer_size_changed,
      self.file_extension,
      file_extension_value='tiff')
    
    use_layer_size.set_value(True)
    use_layer_size.invoke_event('test-event')
    
    self.assertEqual(self.file_extension.value, 'tiff')
  
  def test_invoke_event_with_keyword_arguments(self):
    use_layer_size = settings_.BoolSetting('use_layer_size', default_value=False)
    use_layer_size.connect_event(
      'test-event',
      stubs_setting.on_use_layer_size_changed,
      file_extension_value='tiff')
    
    use_layer_size.set_value(True)
    use_layer_size.invoke_event('test-event', file_extension=self.file_extension)
    
    self.assertEqual(self.file_extension.value, 'tiff')
  
  def test_invoke_event_places_invoke_event_arguments_first(self):
    use_layer_size = settings_.BoolSetting('use_layer_size', default_value=False)
    use_layer_size.connect_event(
      'test-event',
      stubs_setting.on_use_layer_size_changed,
      'tiff')
    
    use_layer_size.set_value(True)
    use_layer_size.invoke_event('test-event', self.file_extension)
    
    self.assertEqual(self.file_extension.value, 'tiff')
  
  def test_connect_event_multiple_events_on_single_setting(self):
    self.file_extension.connect_event(
      'test-event', stubs_setting.on_file_extension_changed, self.flatten)
    
    use_layer_size = settings_.BoolSetting('use_layer_size', default_value=False)
    self.file_extension.connect_event(
      'test-event',
      stubs_setting.on_file_extension_changed_with_use_layer_size,
      use_layer_size)
    
    self.file_extension.set_value('jpg')
    self.file_extension.invoke_event('test-event')
    
    self.assertEqual(self.file_extension.value, 'jpg')
    self.assertTrue(self.flatten.value)
    self.assertFalse(use_layer_size.gui.get_visible())
  
  def test_remove_event(self):
    event_id = self.file_extension.connect_event(
      'test-event', stubs_setting.on_file_extension_changed, self.flatten)
    
    self.file_extension.remove_event(event_id)
    self.file_extension.set_value('jpg')
    self.file_extension.invoke_event('test-event')
    
    self.assertEqual(self.flatten.value, self.flatten.default_value)
    self.assertTrue(self.flatten.gui.get_sensitive())
  
  def test_remove_event_with_id_non_last_event(self):
    event_id = self.file_extension.connect_event(
      'test-event', stubs_setting.on_file_extension_changed, self.flatten)
    
    use_layer_size = settings_.BoolSetting('use_layer_size', default_value=False)
    self.file_extension.connect_event(
      'test-event',
      stubs_setting.on_file_extension_changed_with_use_layer_size,
      use_layer_size)
    
    self.file_extension.remove_event(event_id)
    self.file_extension.set_value('jpg')
    self.file_extension.invoke_event('test-event')
    
    self.assertFalse(self.flatten.value)
    self.assertFalse(use_layer_size.gui.get_visible())
  
  def test_remove_event_invalid_id_raises_error(self):
    with self.assertRaises(ValueError):
      self.file_extension.remove_event(-1)
  
  def test_has_event(self):
    event_id = self.file_extension.connect_event(
      'test-event', stubs_setting.on_file_extension_changed, self.flatten)
    
    self.assertTrue(self.file_extension.has_event(event_id))
    
    self.file_extension.remove_event(event_id)
    self.assertFalse(self.file_extension.has_event(event_id))
  
  def test_has_event_returns_false_on_no_events(self):
    self.assertFalse(self.file_extension.has_event(-1))
  
  def test_set_event_enabled(self):
    event_id = self.file_extension.connect_event(
      'test-event', stubs_setting.on_file_extension_changed, self.flatten)
    
    self.file_extension.set_event_enabled(event_id, False)
    self.file_extension.set_value('jpg')
    self.file_extension.invoke_event('test-event')
    self.assertFalse(self.flatten.value)
    
    self.file_extension.set_event_enabled(event_id, True)
    self.file_extension.set_value('jpg')
    self.file_extension.invoke_event('test-event')
    self.assertTrue(self.flatten.value)
  
  def test_set_event_enabled_invalid_event_raises_error(self):
    with self.assertRaises(ValueError):
      self.file_extension.set_event_enabled(-1, False)


class TestSettingPath(unittest.TestCase):
  
  def setUp(self):
    self.setting, self.advanced_settings, self.main_settings = (
      _create_test_settings_for_path())
  
  def test_get_path_no_parent(self):
    setting = stubs_setting.StubSetting('file_extension')
    self.assertEqual(utils_.get_setting_path(setting), 'file_extension')
  
  def test_get_path(self):
    self.assertEqual(
      utils_.get_setting_path(self.setting), 'main/advanced/file_extension')
    self.assertEqual(
      utils_.get_setting_path(self.advanced_settings), 'main/advanced')
    self.assertEqual(
      utils_.get_setting_path(self.main_settings), 'main')
  
  def test_get_path_with_relative_path_from_group(self):
    self._test_get_path_with_relative_path(
      self.setting, self.main_settings, 'advanced/file_extension')
    self._test_get_path_with_relative_path(
      self.setting, self.advanced_settings, 'file_extension')
    self._test_get_path_with_relative_path(
      self.setting, self.setting, '')
    self._test_get_path_with_relative_path(
      self.advanced_settings, self.main_settings, 'advanced')
    self._test_get_path_with_relative_path(
      self.advanced_settings, self.advanced_settings, '')
    self._test_get_path_with_relative_path(
      self.main_settings, self.main_settings, '')
  
  def test_get_path_with_relative_path_from_non_matching_group(self):
    special_settings = group_.Group('special')
    
    self._test_get_path_with_relative_path(
      self.setting, special_settings, 'main/advanced/file_extension')
    self._test_get_path_with_relative_path(
      self.advanced_settings, special_settings, 'main/advanced')
    self._test_get_path_with_relative_path(
      self.main_settings, special_settings, 'main')
  
  def test_get_path_without_root_group(self):
    self.assertEqual(
      utils_.get_setting_path(self.setting, 'root'), 'advanced/file_extension')
    self.assertEqual(
      utils_.get_setting_path(self.advanced_settings, 'root'), 'advanced')
    self.assertEqual(
      utils_.get_setting_path(self.main_settings, 'root'), 'main')
  
  def _test_get_path_with_relative_path(
        self, setting, relative_path_group, expected_path):
    self.assertEqual(
      utils_.get_setting_path(
        setting, relative_path_group=relative_path_group),
      expected_path)
