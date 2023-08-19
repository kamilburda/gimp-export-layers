# -*- coding: utf-8 -*-

"""Tests for the `setting.setting` and `setting.presenter` modules."""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import unittest

import gimpcolor
import gimpenums

import mock
import parameterized

from ... import utils as pgutils
from ... import path as pgpath

from ...setting import presenter as presenter_
from ...setting import presenters_gtk
from ...setting import settings as settings_

from .. import stubs_gimp
from . import stubs_setting


class TestSetting(unittest.TestCase):
  
  def setUp(self):
    self.setting = stubs_setting.StubSetting('file_extension', default_value='png')
  
  def test_str(self):
    self.assertEqual(str(self.setting), '<StubSetting "file_extension">')
  
  def test_invalid_setting_name(self):
    with self.assertRaises(ValueError):
      stubs_setting.StubSetting('file/extension', default_value='png')
    
    with self.assertRaises(ValueError):
      stubs_setting.StubSetting('file.extension', default_value='png')
  
  def test_default_default_value(self):
    self.assertEqual(stubs_setting.StubSetting('setting').default_value, 0)
  
  def test_callable_default_default_value(self):
    self.assertEqual(
      stubs_setting.StubWithCallableDefaultDefaultValueSetting('setting').default_value,
      '_setting')
  
  def test_explicit_default_value(self):
    self.assertEqual(
      stubs_setting.StubSetting('file_extension', default_value='png').default_value, 'png')
  
  def test_invalid_default_value(self):
    with self.assertRaises(settings_.SettingDefaultValueError):
      stubs_setting.StubSetting('setting', default_value=None)
  
  def test_empty_value_as_default_value(self):
    try:
      stubs_setting.StubSetting('setting', default_value='')
    except settings_.SettingDefaultValueError:
      self.fail(
        'SettingDefaultValueError should not be raised - default value is an empty value')
  
  def test_assign_empty_value_not_allowed(self):
    with self.assertRaises(settings_.SettingValueError):
      self.setting.set_value('')
  
  def test_assign_empty_value_allowed(self):
    setting = stubs_setting.StubSetting('setting', default_value='', allow_empty_values=True)
    setting.set_value('')
    
    self.assertEqual(setting.value, '')
  
  def test_value_direct_assignment_not_allowed(self):
    with self.assertRaises(AttributeError):
      self.setting.value = 'jpg'
  
  def test_get_generated_display_name(self):
    self.assertEqual(self.setting.display_name, 'File extension')
  
  def test_get_generated_description(self):
    setting = stubs_setting.StubSetting(
      'setting', default_value='default value', display_name='_Setting')
    
    self.assertEqual(setting.display_name, '_Setting')
    self.assertEqual(setting.description, 'Setting')
  
  def test_get_custom_display_name_and_description(self):
    setting = stubs_setting.StubSetting(
      'setting',
      default_value='default value', display_name='_Setting', description='My description')
    
    self.assertEqual(setting.display_name, '_Setting')
    self.assertEqual(setting.description, 'My description')
  
  def test_custom_error_messages(self):
    setting = stubs_setting.StubSetting('setting', default_value='')
    
    setting_with_custom_error_messages = stubs_setting.StubSetting(
      'setting',
      default_value='',
      error_messages={
        'invalid_value': 'this should override the original error message',
        'custom_message': 'custom message'})
    
    self.assertIn('custom_message', setting_with_custom_error_messages.error_messages)
    self.assertNotEqual(
      setting.error_messages['invalid_value'],
      setting_with_custom_error_messages.error_messages['invalid_value'])
  
  def test_pdb_type_automatic_is_registrable(self):
    setting = stubs_setting.StubRegistrableToPdbSetting(
      'file_extension', default_value='png', pdb_type=settings_.SettingPdbTypes.string)
    
    self.assertTrue(setting.can_be_registered_to_pdb())
  
  def test_pdb_type_automatic_is_not_registrable(self):
    self.assertFalse(self.setting.can_be_registered_to_pdb())
  
  def test_invalid_pdb_type(self):
    with self.assertRaises(ValueError):
      stubs_setting.StubSetting(
        'file_extension', default_value='png', pdb_type=settings_.SettingPdbTypes.string)
  
  def test_get_pdb_param_for_registrable_setting(self):
    setting = stubs_setting.StubRegistrableToPdbSetting('file_extension', default_value='png')
    self.assertEqual(
      setting.get_pdb_param(),
      [(settings_.SettingPdbTypes.string, b'file-extension', b'File extension')])
  
  def test_get_pdb_param_for_nonregistrable_setting(self):
    self.assertEqual(self.setting.get_pdb_param(), None)
  
  def test_reset(self):
    self.setting.set_value('jpg')
    self.setting.reset()
    self.assertEqual(self.setting.value, 'png')
  
  def test_reset_with_container_as_default_value(self):
    setting = stubs_setting.StubSetting('image_ids_and_directories', default_value={})
    setting.value[1] = 'image_directory'
    
    setting.reset()
    self.assertEqual(setting.value, {})
    
    setting.value[2] = 'another_image_directory'
    
    setting.reset()
    self.assertEqual(setting.value, {})
  
  def test_to_dict(self):
    self.assertDictEqual(
      self.setting.to_dict(),
      {
        'name': 'file_extension',
        'value': 'png',
        'type': 'stub',
        'default_value': 'png',
      })
  
  def test_to_dict_when_default_value_object_is_passed_to_init(self):
    setting = stubs_setting.StubSetting(
      'file_extension', default_value=settings_.Setting.DEFAULT_VALUE)
    
    self.assertDictEqual(
      setting.to_dict(),
      {
        'name': 'file_extension',
        'value': 0,
        'type': 'stub',
        'default_value': 0,
      })
  
  def test_to_dict_with_gui_type_as_object(self):
    setting = stubs_setting.StubWithGuiSetting(
      'file_extension',
      default_value='png',
      gui_type=stubs_setting.StubPresenter)
    
    self.assertDictEqual(
      setting.to_dict(),
      {
        'name': 'file_extension',
        'value': 'png',
        'type': 'stub_with_gui',
        'default_value': 'png',
        'gui_type': 'stub',
      })
  
  def test_to_dict_with_tags(self):
    tags = set(['ignore_reset', 'ignore_load'])
    expected_tags = list(tags)
    
    setting = stubs_setting.StubSetting(
      'file_extension', default_value='png', tags=tags)
    
    self.assertDictEqual(
      setting.to_dict(),
      {
        'name': 'file_extension',
        'value': 'png',
        'type': 'stub',
        'default_value': 'png',
        'tags': expected_tags,
      })


class TestSettingEvents(unittest.TestCase):
  
  def setUp(self):
    self.setting = stubs_setting.StubSetting('file_extension', default_value='png')
    self.flatten = settings_.BoolSetting('flatten', default_value=False)
  
  def test_connect_value_changed_event(self):
    self.setting.connect_event(
      'value-changed', stubs_setting.on_file_extension_changed, self.flatten)
    
    self.setting.set_value('jpg')
    self.assertEqual(self.flatten.value, True)
    self.assertFalse(self.flatten.gui.get_sensitive())
  
  def test_connect_value_changed_event_nested(self):
    self.setting.connect_event(
      'value-changed', stubs_setting.on_file_extension_changed, self.flatten)
    
    use_layer_size = settings_.BoolSetting('use_layer_size', default_value=False)
    use_layer_size.connect_event(
      'value-changed', stubs_setting.on_use_layer_size_changed, self.setting)
    
    use_layer_size.set_value(True)
    
    self.assertEqual(self.setting.value, 'jpg')
    self.assertEqual(self.flatten.value, True)
    self.assertFalse(self.flatten.gui.get_sensitive())
  
  def test_reset_triggers_value_changed_event(self):
    self.setting.connect_event(
      'value-changed', stubs_setting.on_file_extension_changed, self.flatten)
    
    self.setting.set_value('jpg')
    self.setting.reset()
    self.assertEqual(self.flatten.value, self.flatten.default_value)
    self.assertTrue(self.flatten.gui.get_sensitive())


class TestSettingGui(unittest.TestCase):
  
  def setUp(self):
    self.setting = stubs_setting.StubWithGuiSetting('file_extension', default_value='png')
    self.widget = stubs_setting.GuiWidgetStub('')
  
  def test_set_gui_updates_gui_value(self):
    self.setting.set_gui(stubs_setting.StubPresenter, self.widget)
    self.assertEqual(self.widget.value, 'png')
  
  def test_setting_set_value_updates_gui(self):
    self.setting.set_gui(stubs_setting.StubPresenter, self.widget)
    self.setting.set_value('gif')
    self.assertEqual(self.widget.value, 'gif')
  
  def test_set_gui_preserves_gui_state(self):
    self.setting.gui.set_sensitive(False)
    self.setting.gui.set_visible(False)
    self.setting.set_value('gif')
    
    self.setting.set_gui(stubs_setting.StubPresenter, self.widget)
    
    self.assertFalse(self.setting.gui.get_sensitive())
    self.assertFalse(self.setting.gui.get_visible())
    self.assertEqual(self.widget.value, 'gif')
  
  def test_setting_gui_type(self):
    setting = stubs_setting.StubWithGuiSetting(
      'flatten', default_value=False, gui_type=stubs_setting.CheckButtonStubPresenter)
    setting.set_gui()
    self.assertIs(type(setting.gui), stubs_setting.CheckButtonStubPresenter)
    self.assertIs(type(setting.gui.element), stubs_setting.CheckButtonStub)
  
  def test_setting_different_gui_type(self):
    setting = stubs_setting.StubWithGuiSetting(
      'flatten', default_value=False, gui_type=stubs_setting.StubPresenter)
    setting.set_gui()
    self.assertIs(type(setting.gui), stubs_setting.StubPresenter)
    self.assertIs(type(setting.gui.element), stubs_setting.GuiWidgetStub)
  
  def test_setting_invalid_gui_type_raise_error(self):
    with self.assertRaises(ValueError):
      stubs_setting.StubWithGuiSetting(
        'flatten',
        default_value=False,
        gui_type=stubs_setting.YesNoToggleButtonStubPresenter)
  
  def test_setting_null_gui_type(self):
    setting = stubs_setting.StubWithGuiSetting('flatten', default_value=False, gui_type='null')
    setting.set_gui()
    self.assertIs(type(setting.gui), presenter_.NullPresenter)
  
  def test_set_gui_gui_type_is_specified_gui_element_is_none_raise_error(self):
    setting = stubs_setting.StubWithGuiSetting('flatten', default_value=False)
    with self.assertRaises(ValueError):
      setting.set_gui(gui_type=stubs_setting.CheckButtonStubPresenter)
  
  def test_set_gui_gui_type_is_none_gui_element_is_specified_raise_error(self):
    setting = stubs_setting.StubWithGuiSetting('flatten', default_value=False)
    with self.assertRaises(ValueError):
      setting.set_gui(gui_element=stubs_setting.GuiWidgetStub)
  
  def test_set_gui_manual_gui_type(self):
    setting = stubs_setting.StubWithGuiSetting('flatten', default_value=False)
    setting.set_gui(
      gui_type=stubs_setting.YesNoToggleButtonStubPresenter,
      gui_element=stubs_setting.GuiWidgetStub(None))
    self.assertIs(type(setting.gui), stubs_setting.YesNoToggleButtonStubPresenter)
    self.assertIs(type(setting.gui.element), stubs_setting.GuiWidgetStub)
  
  def test_set_gui_gui_element_is_none_presenter_has_no_wrapper_raise_error(self):
    setting = stubs_setting.StubWithGuiSetting(
      'flatten',
      default_value=False,
      gui_type=stubs_setting.StubWithoutGuiElementCreationPresenter)
    with self.assertRaises(ValueError):
      setting.set_gui()
  
  def test_update_setting_value_manually(self):
    self.setting.set_gui(stubs_setting.StubPresenter, self.widget)
    self.widget.set_value('jpg')
    self.assertEqual(self.setting.value, 'png')
    
    self.setting.gui.update_setting_value()
    self.assertEqual(self.setting.value, 'jpg')
  
  def test_update_setting_value_automatically(self):
    self.setting.set_gui(
      stubs_setting.StubWithValueChangedSignalPresenter, self.widget)
    self.widget.set_value('jpg')
    self.assertEqual(self.setting.value, 'jpg')
  
  def test_update_setting_value_triggers_value_changed_event(self):
    self.setting.set_gui(
      stubs_setting.StubWithValueChangedSignalPresenter, self.widget)
    
    flatten = settings_.BoolSetting('flatten', default_value=False)
    self.setting.connect_event('value-changed', stubs_setting.on_file_extension_changed, flatten)
    
    self.widget.set_value('jpg')
    self.assertEqual(self.setting.value, 'jpg')
    self.assertEqual(flatten.value, True)
    self.assertFalse(flatten.gui.get_sensitive())
  
  def test_reset_updates_gui(self):
    self.setting.set_gui(stubs_setting.StubPresenter, self.widget)
    self.setting.set_value('jpg')
    self.setting.reset()
    self.assertEqual(self.widget.value, 'png')
  
  def test_update_setting_value_manually_for_automatically_updated_settings_when_reset_to_disallowed_empty_value(self):
    setting = stubs_setting.StubWithGuiSetting('file_extension', default_value='')
    setting.set_gui(
      stubs_setting.StubWithValueChangedSignalPresenter, self.widget)
    setting.set_value('jpg')
    setting.reset()
    
    with self.assertRaises(settings_.SettingValueError):
      # Raise error because setting is reset to an empty value, while empty
      # values are disallowed (`allow_empty_values` is False).
      setting.gui.update_setting_value()
  
  def test_null_presenter_has_automatic_gui(self):
    setting = stubs_setting.StubWithGuiSetting('file_extension', default_value='')
    self.assertTrue(setting.gui.gui_update_enabled)
  
  def test_manual_gui_update_enabled_is_false(self):
    setting = stubs_setting.StubWithGuiSetting('file_extension', default_value='')
    setting.set_gui(stubs_setting.StubPresenter, self.widget)
    self.assertFalse(setting.gui.gui_update_enabled)
  
  def test_automatic_gui_update_enabled_is_true(self):
    setting = stubs_setting.StubWithGuiSetting('file_extension', default_value='')
    setting.set_gui(
      stubs_setting.StubWithValueChangedSignalPresenter, self.widget)
    self.assertTrue(setting.gui.gui_update_enabled)
    
    self.widget.set_value('png')
    self.assertEqual(setting.value, 'png')
  
  def test_automatic_gui_update_enabled_is_false(self):
    setting = stubs_setting.StubWithGuiSetting(
      'file_extension', default_value='', auto_update_gui_to_setting=False)
    setting.set_gui(
      stubs_setting.StubWithValueChangedSignalPresenter, self.widget)
    self.assertFalse(setting.gui.gui_update_enabled)
    
    self.widget.set_value('png')
    self.assertEqual(setting.value, '')
  
  def test_set_gui_disable_automatic_setting_value_update(self):
    setting = stubs_setting.StubWithGuiSetting('file_extension', default_value='')
    setting.set_gui(
      stubs_setting.StubWithValueChangedSignalPresenter,
      self.widget, auto_update_gui_to_setting=False)
    self.assertFalse(setting.gui.gui_update_enabled)
    
    self.widget.set_value('png')
    self.assertEqual(setting.value, '')
  
  def test_automatic_gui_update_after_being_disabled(self):
    setting = stubs_setting.StubWithGuiSetting(
      'file_extension', default_value='', auto_update_gui_to_setting=False)
    setting.set_gui(
      stubs_setting.StubWithValueChangedSignalPresenter, self.widget)
    setting.gui.auto_update_gui_to_setting(True)
    
    self.widget.set_value('png')
    self.assertEqual(setting.value, 'png')
  
  def test_automatic_gui_update_for_manual_gui_raises_value_error(self):
    setting = stubs_setting.StubWithGuiSetting('file_extension', default_value='')
    setting.set_gui(stubs_setting.StubPresenter, self.widget)
    
    self.assertFalse(setting.gui.gui_update_enabled)
    
    with self.assertRaises(ValueError):
      setting.gui.auto_update_gui_to_setting(True)


#===============================================================================


class TestGenericSetting(unittest.TestCase):
  
  def test_value_functions_with_one_parameter(self):
    setting = settings_.GenericSetting(
      'selected_layers',
      value_set=lambda value: tuple(value),
      value_save=lambda value: list(value))

    setting.set_value([4, 6, 2])
    
    self.assertEqual(setting.value, (4, 6, 2))
    self.assertDictEqual(
      setting.to_dict(), {'name': setting.name, 'value': [4, 6, 2], 'type': 'generic'})
  
  def test_value_functions_as_none(self):
    setting = settings_.GenericSetting('selected_layers')
    
    setting.set_value([4, 6, 2])
    
    self.assertEqual(setting.value, [4, 6, 2])
    self.assertDictEqual(
      setting.to_dict(), {'name': setting.name, 'value': repr([4, 6, 2]), 'type': 'generic'})
  
  def test_value_functions_with_two_parameters(self):
    setting = settings_.GenericSetting(
      'selected_layers',
      value_set=lambda value, setting: tuple(setting.name + '_' + str(item) for item in value),
      value_save=lambda value, setting: list(value))
    
    setting.set_value([4, 6, 2])
    
    self.assertEqual(
      setting.value, ('selected_layers_4', 'selected_layers_6', 'selected_layers_2'))
    self.assertDictEqual(
      setting.to_dict(),
      {
        'name': setting.name,
        'value': ['selected_layers_4', 'selected_layers_6', 'selected_layers_2'],
        'type': 'generic',
      })
  
  def test_value_set_with_invalid_number_of_parameters_raises_error(self):
    with self.assertRaises(TypeError):
      settings_.GenericSetting(
        'selected_layers',
        value_set=lambda value, setting, redundant: tuple(value),
        value_save=lambda value, setting: list(value))
  
  def test_value_set_not_being_callable_raises_error(self):
    with self.assertRaises(TypeError):
      settings_.GenericSetting(
        'selected_layers',
        value_set='not_a_callable',
        value_save=lambda value, setting: list(value))
  
  def test_value_save_with_invalid_number_of_parameters_raises_error(self):
    with self.assertRaises(TypeError):
      settings_.GenericSetting(
        'selected_layers',
        value_set=lambda value, setting: tuple(value),
        value_save=lambda value, setting, redundant: list(value))
  
  def test_value_save_not_being_callable_raises_error(self):
    with self.assertRaises(TypeError):
      settings_.GenericSetting(
        'selected_layers',
        value_set=lambda value, setting: tuple(value),
        value_save='not_a_callable')


class TestBoolSetting(unittest.TestCase):
  
  def test_description_from_display_name(self):
    setting = settings_.BoolSetting('flatten', default_value=False, display_name='_Flatten')
    self.assertEqual(setting.description, 'Flatten?')


class TestIntSetting(unittest.TestCase):
  
  def setUp(self):
    self.setting = settings_.IntSetting(
      'count', default_value=0, min_value=0, max_value=100)
  
  def test_value_is_below_min(self):
    with self.assertRaises(settings_.SettingValueError):
      self.setting.set_value(-5)
  
  def test_min_value_does_not_raise_error(self):
    try:
      self.setting.set_value(0)
    except settings_.SettingValueError:
      self.fail('SettingValueError should not be raised')
  
  def test_value_is_above_max(self):
    with self.assertRaises(settings_.SettingValueError):
      self.setting.set_value(200)
  
  def test_max_value_does_not_raise_error(self):
    try:
      self.setting.set_value(100)
    except settings_.SettingValueError:
      self.fail('SettingValueError should not be raised')


class TestFloatSetting(unittest.TestCase):
  
  def setUp(self):
    self.setting = settings_.FloatSetting(
      'clip_percent', default_value=0.0, min_value=0.0, max_value=100.0)
  
  def test_value_below_min(self):
    with self.assertRaises(settings_.SettingValueError):
      self.setting.set_value(-5.0)
  
  def test_minimum_value_does_not_raise_error(self):
    try:
      self.setting.set_value(0.0)
    except settings_.SettingValueError:
      self.fail('SettingValueError should not be raised')
  
  def test_value_above_max(self):
    with self.assertRaises(settings_.SettingValueError):
      self.setting.set_value(200.0)
  
  def test_maximum_value_does_not_raise_error(self):
    try:
      self.setting.set_value(100.0)
    except settings_.SettingValueError:
      self.fail('SettingValueError should not be raised')


class TestCreateEnumSetting(unittest.TestCase):
  
  def test_default_default_value_is_first_item(self):
    setting = settings_.EnumSetting(
      'overwrite_mode', [('skip', 'Skip'), ('replace', 'Replace')])
    self.assertEqual(setting.default_value, setting.items['skip'])
  
  def test_no_items_raises_error(self):
    with self.assertRaises(ValueError):
      settings_.EnumSetting('overwrite_mode', [])
  
  def test_explicit_item_values(self):
    setting = settings_.EnumSetting(
      'overwrite_mode',
      [('skip', 'Skip', 5), ('replace', 'Replace', 6)],
      default_value='replace')
    self.assertEqual(setting.items['skip'], 5)
    self.assertEqual(setting.items['replace'], 6)
  
  def test_inconsistent_number_of_elements_raises_error(self):
    with self.assertRaises(ValueError):
      settings_.EnumSetting(
        'overwrite_mode', [('skip', 'Skip', 4), ('replace', 'Replace')], default_value='replace')
    
  def test_same_explicit_item_value_multiple_times_raises_error(self):
    with self.assertRaises(ValueError):
      settings_.EnumSetting(
        'overwrite_mode', [('skip', 'Skip', 4), ('replace', 'Replace', 4)])
  
  def test_invalid_default_value_raises_error(self):
    with self.assertRaises(settings_.SettingDefaultValueError):
      settings_.EnumSetting(
        'overwrite_mode',
        [('skip', 'Skip'), ('replace', 'Replace')],
        default_value='invalid_default_value')
  
  def test_too_many_elements_in_items_raises_error(self):
    with self.assertRaises(ValueError):
      settings_.EnumSetting(
        'overwrite_mode', [('skip', 'Skip', 1, 1), ('replace', 'Replace', 1, 1)])
  
  def test_too_few_elements_in_items_raises_error(self):
    with self.assertRaises(ValueError):
      settings_.EnumSetting('overwrite_mode', [('skip'), ('replace')])
  
  def test_no_empty_value(self):
    setting = settings_.EnumSetting(
      'overwrite_mode', [('skip', 'Skip'), ('replace', 'Replace')])
    self.assertEqual(setting.empty_value, None)
  
  def test_valid_empty_value(self):
    setting = settings_.EnumSetting(
      'overwrite_mode',
      [('choose', 'Choose your mode'), ('skip', 'Skip'), ('replace', 'Replace')],
      default_value='replace',
      empty_value='choose')
    self.assertEqual(setting.empty_value, setting.items['choose'])
  
  def test_empty_value_is_equal_to_default_default_value(self):
    setting = settings_.EnumSetting(
      'overwrite_mode',
      [('choose', 'Choose your mode'), ('skip', 'Skip'), ('replace', 'Replace')],
      empty_value='choose')
    
    self.assertEqual(setting.default_value, setting.items['choose'])
    self.assertEqual(setting.empty_value, setting.items['choose'])
  
  def test_invalid_empty_value_raises_error(self):
    with self.assertRaises(ValueError):
      settings_.EnumSetting(
        'overwrite_mode',
        [('skip', 'Skip'), ('replace', 'Replace')],
        empty_value='invalid_value')
  

class TestEnumSetting(unittest.TestCase):
  
  def setUp(self):
    self.setting = settings_.EnumSetting(
      'overwrite_mode',
      [('skip', 'Skip'), ('replace', 'Replace')],
      default_value='replace',
      display_name='Overwrite mode')
  
  def test_set_invalid_item(self):
    with self.assertRaises(settings_.SettingValueError):
      self.setting.set_value(4)
    with self.assertRaises(settings_.SettingValueError):
      self.setting.set_value(-1)
  
  def test_get_invalid_item(self):
    with self.assertRaises(KeyError):
      unused_ = self.setting.items['invalid_item']
  
  def test_description(self):
    self.assertEqual(self.setting.description, 'Overwrite mode { Skip (0), Replace (1) }')
  
  def test_description_with_mnemonics_from_item_display_names(self):
    setting = settings_.EnumSetting(
      'overwrite_mode',
      [('skip', '_Skip'), ('replace', '_Replace')],
      display_name='_Overwrite mode',
      default_value='replace')
    self.assertEqual(setting.description, 'Overwrite mode { Skip (0), Replace (1) }')
  
  def test_get_item_display_names_and_values(self):
    self.assertEqual(
      self.setting.get_item_display_names_and_values(), ['Skip', 0, 'Replace', 1])
  
  def test_is_value_empty(self):
    setting = settings_.EnumSetting(
      'overwrite_mode',
      [('choose', '-Choose Your Mode-'), ('skip', 'Skip'), ('replace', 'Replace')],
      default_value='replace',
      empty_value='choose',
      allow_empty_values=True)
    
    self.assertFalse(setting.is_value_empty())
    setting.set_value(setting.items['choose'])
    self.assertTrue(setting.is_value_empty())
  
  def test_set_empty_value_not_allowed(self):
    setting = settings_.EnumSetting(
      'overwrite_mode',
      [('choose', '-Choose Your Mode-'), ('skip', 'Skip'), ('replace', 'Replace')],
      default_value='replace',
      empty_value='choose')
    
    with self.assertRaises(settings_.SettingValueError):
      setting.set_value(setting.items['choose'])
  
  def test_to_dict(self):
    self.assertDictEqual(
      self.setting.to_dict(),
      {
        'name': 'overwrite_mode',
        'value': 1,
        'type': 'enum',
        'default_value': 'replace',
        'items': [['skip', 'Skip'], ['replace', 'Replace']],
        'display_name': 'Overwrite mode',
      })


class TestStringSetting(unittest.TestCase):
  
  def test_to_dict_bytes_is_converted_to_str(self):
    setting = settings_.StringSetting('file_extension', default_value=b'png')
    
    self.assertEqual(
      setting.to_dict(),
      {
        'name': 'file_extension',
        'value': 'png',
        'type': 'string',
        'default_value': 'png',
      })


@mock.patch(
  pgutils.get_pygimplib_module_path() + '.setting.settings.pdb', new=stubs_gimp.PdbStub())
@mock.patch(
  pgutils.get_pygimplib_module_path() + '.pdbutils.gimp', new=stubs_gimp.GimpModuleStub())
class TestImageSetting(unittest.TestCase):
  
  @mock.patch(
    pgutils.get_pygimplib_module_path() + '.setting.settings.pdb', new=stubs_gimp.PdbStub())
  def setUp(self):
    self.pdb = stubs_gimp.PdbStub()
    
    self.image = self.pdb.gimp_image_new(2, 2, gimpenums.RGB)
    
    self.setting = settings_.ImageSetting('image', default_value=self.image)
  
  def test_set_value_with_object(self):
    image = self.pdb.gimp_image_new(2, 2, gimpenums.RGB)
    
    self.setting.set_value(image)
    
    self.assertEqual(self.setting.value, image)
  
  def test_set_value_with_file_path(self):
    self.pdb.gimp_image_set_filename(self.image, 'file_path')
    
    with mock.patch(
          pgutils.get_pygimplib_module_path() + '.pdbutils.gimp') as temp_mock_gimp_module:
      temp_mock_gimp_module.image_list.return_value = [self.image]
    
      self.setting.set_value('file_path')
    
    self.assertEqual(self.setting.value, self.image)
  
  def test_set_value_with_non_matching_file_path(self):
    with mock.patch(
          pgutils.get_pygimplib_module_path() + '.pdbutils.gimp') as temp_mock_gimp_module:
      temp_mock_gimp_module.image_list.return_value = []
      
      self.setting.set_value('file_path')
      
      self.assertEqual(self.setting.value, None)
  
  def test_set_value_with_id(self):
    self.image.ID = 2
    
    with mock.patch(
          pgutils.get_pygimplib_module_path() + '.pdbutils.gimp') as temp_mock_gimp_module:
      temp_mock_gimp_module._id2image.return_value = self.image
      
      self.setting.set_value(2)
    
    self.assertEqual(self.setting.value, self.image)
  
  def test_set_value_with_invalid_id(self):
    self.image.ID = 2
    
    with mock.patch(
          pgutils.get_pygimplib_module_path() + '.pdbutils.gimp') as temp_mock_gimp_module:
      temp_mock_gimp_module._id2image.return_value = None
      
      self.setting.set_value(3)
      
      self.assertEqual(self.setting.value, None)
  
  def test_set_value_with_none(self):
    self.setting.set_value(None)
    
    self.assertEqual(self.setting.value, None)
  
  def test_set_value_invalid_image_raises_error(self):
    self.pdb.gimp_image_delete(self.image)
    with self.assertRaises(settings_.SettingValueError):
      self.setting.set_value(self.image)
  
  def test_default_value_with_raw_type(self):
    self.pdb.gimp_image_set_filename(self.image, 'file_path')
    
    with mock.patch(
          pgutils.get_pygimplib_module_path() + '.pdbutils.gimp') as temp_mock_gimp_module:
      temp_mock_gimp_module.image_list.return_value = [self.image]
      
      setting = settings_.ImageSetting('image', default_value='file_path')
    
    self.assertEqual(setting.default_value, self.image)
  
  def test_empty_value_as_default_value(self):
    try:
      settings_.ImageSetting('image', default_value=None)
    except settings_.SettingDefaultValueError:
      self.fail(
        'SettingDefaultValueError should not be raised - default value is an empty value')
  
  def test_to_dict(self):
    self.pdb.gimp_image_set_filename(self.image, 'file_path')
    
    self.assertDictEqual(
      self.setting.to_dict(),
      {
        'name': 'image',
        'value': 'file_path',
        'type': 'image',
        'default_value': 'file_path',
      })
  
  def test_to_dict_if_image_is_none(self):
    setting = settings_.ImageSetting('image', default_value=None)
    
    self.assertDictEqual(
      setting.to_dict(),
      {
        'name': 'image',
        'value': None,
        'type': 'image',
        'default_value': None,
      })
  
  def test_to_dict_with_missing_filename(self):
    self.pdb.gimp_image_set_filename(self.image, None)
    
    self.assertDictEqual(
      self.setting.to_dict(),
      {
        'name': 'image',
        'value': None,
        'type': 'image',
        'default_value': None,
      })
  
  def test_to_dict_with_session_source_type(self):
    self.image.ID = 2
    
    self.assertDictEqual(
      self.setting.to_dict(source_type='session'),
      {
        'name': 'image',
        'value': 2,
        'type': 'image',
        'default_value': 2,
      })


@mock.patch(
  pgutils.get_pygimplib_module_path() + '.setting.settings.pdb', new=stubs_gimp.PdbStub())
@mock.patch(
  pgutils.get_pygimplib_module_path() + '.setting.settings.gimp', new=stubs_gimp.GimpModuleStub())
@mock.patch(
  pgutils.get_pygimplib_module_path() + '.pdbutils.gimp', new=stubs_gimp.GimpModuleStub())
class TestGimpItemSetting(unittest.TestCase):
  
  class StubItemSetting(settings_.GimpItemSetting):
    pass
  
  def setUp(self):
    pdb = stubs_gimp.PdbStub()
    
    self.image = pdb.gimp_image_new(2, 2, gimpenums.RGB)
    
    self.parent_of_parent = stubs_gimp.LayerGroupStub(name='group1')
    
    self.parent = stubs_gimp.LayerGroupStub(name='group2')
    self.parent.parent = self.parent_of_parent
    
    self.layer = stubs_gimp.LayerStub(name='layer')
    self.layer.parent = self.parent
    self.layer.image = self.image
    self.layer.image.filename = 'image_filepath'
    
    self.image.layers = [self.parent_of_parent]
    self.parent_of_parent.children = [self.parent]
    self.parent.children = [self.layer]
    
    self.setting = self.StubItemSetting('item', default_value=self.layer)
  
  def test_set_value_with_object(self):
    layer = stubs_gimp.LayerStub(name='layer2')
    
    self.setting.set_value(layer)
    self.assertEqual(self.setting.value, layer)
  
  def test_set_value_with_list(self):
    with mock.patch(
          pgutils.get_pygimplib_module_path() + '.pdbutils.gimp') as temp_mock_gimp_module:
      temp_mock_gimp_module.image_list.return_value = [self.image]
      
      self.setting.set_value(['image_filepath', 'Layer', 'group1/group2/layer'])
    
    self.assertEqual(self.setting.value, self.layer)
  
  def test_set_value_with_list_and_top_level_layer(self):
    self.layer.parent = None
    self.image.layers = [self.layer]
    
    with mock.patch(
          pgutils.get_pygimplib_module_path() + '.pdbutils.gimp') as temp_mock_gimp_module:
      temp_mock_gimp_module.image_list.return_value = [self.image]
      
      self.setting.set_value(['image_filepath', 'Layer', 'layer'])
    
    self.assertEqual(self.setting.value, self.layer)
  
  def test_set_value_with_list_invalid_length_raises_error(self):
    with self.assertRaises(ValueError):
      self.setting.set_value(['image_filepath'])
  
  def test_set_value_with_list_no_matching_image_returns_none(self):
    with mock.patch(
          pgutils.get_pygimplib_module_path() + '.pdbutils.gimp') as temp_mock_gimp_module:
      temp_mock_gimp_module.image_list.return_value = []
      
      self.setting.set_value(['image_filepath', 'Layer', 'group1/group2/layer'])
    
    self.assertEqual(self.setting.value, None)
  
  def test_set_value_with_list_no_matching_layer_returns_none(self):
    with mock.patch(
          pgutils.get_pygimplib_module_path() + '.pdbutils.gimp') as temp_mock_gimp_module:
      temp_mock_gimp_module.image_list.return_value = [self.image]
      
      self.setting.set_value(['image_filepath', 'Layer', 'group1/group2/some_other_layer'])
    
    self.assertEqual(self.setting.value, None)
  
  def test_set_value_with_list_no_matching_parent_returns_none(self):
    with mock.patch(
          pgutils.get_pygimplib_module_path() + '.pdbutils.gimp') as temp_mock_gimp_module:
      temp_mock_gimp_module.image_list.return_value = [self.image]
      
      self.setting.set_value(['image_filepath', 'Layer', 'group1/some_other_group2/layer'])
    
    self.assertEqual(self.setting.value, None)
  
  def test_set_value_with_list_with_id(self):
    with mock.patch(
          pgutils.get_pygimplib_module_path()
          + '.tests.stubs_gimp.ItemStub.from_id') as from_id_function:
      from_id_function.return_value = self.layer
      
      self.setting.set_value(2)
    
    self.assertEqual(self.setting.value, self.layer)
  
  def test_set_value_with_list_with_invalid_id(self):
    with mock.patch(
          pgutils.get_pygimplib_module_path()
          + '.tests.stubs_gimp.ItemStub.from_id') as from_id_function:
      from_id_function.return_value = None
    
      self.setting.set_value(2)
    
    self.assertEqual(self.setting.value, None)
  
  def test_to_dict(self):
    self.assertDictEqual(
      self.setting.to_dict(),
      {
        'name': 'item',
        'value': ['image_filepath', 'LayerStub', 'group1/group2/layer'],
        'type': 'stub_item',
        'default_value': ['image_filepath', 'LayerStub', 'group1/group2/layer'],
      })
  
  def test_to_dict_value_is_none(self):
    self.assertDictEqual(
      self.StubItemSetting('item', default_value=None).to_dict(),
      {
        'name': 'item',
        'value': None,
        'type': 'stub_item',
        'default_value': None,
      })
  
  def test_to_dict_value_is_none_and_source_type_is_session(self):
    self.assertDictEqual(
      self.StubItemSetting('item', default_value=None).to_dict(source_type='session'),
      {
        'name': 'item',
        'value': None,
        'type': 'stub_item',
        'default_value': None,
      })
  
  def test_to_dict_without_image_filename(self):
    self.image.filename = None
    
    self.assertDictEqual(
      self.setting.to_dict(),
      {
        'name': 'item',
        'value': None,
        'type': 'stub_item',
        'default_value': None,
      })
  
  def test_to_dict_without_parents(self):
    self.layer.parent = None
    
    self.assertDictEqual(
      self.setting.to_dict(),
      {
        'name': 'item',
        'value': ['image_filepath', 'LayerStub', 'layer'],
        'type': 'stub_item',
        'default_value': ['image_filepath', 'LayerStub', 'layer'],
      })
  
  def test_to_dict_via_item_id(self):
    self.layer.ID = 2
    
    self.assertDictEqual(
      self.setting.to_dict(source_type='session'),
      {
        'name': 'item',
        'value': 2,
        'type': 'stub_item',
        'default_value': 2,
      })


class TestColorSetting(unittest.TestCase):
  
  def test_create_with_default_default_value(self):
    self.assertEqual(settings_.ColorSetting('color').default_value, gimpcolor.RGB(0, 0, 0))
  
  def test_set_value_with_object(self):
    color = gimpcolor.RGB(5, 5, 5)
    
    setting = settings_.ColorSetting('color')
    setting.set_value(color)
    
    self.assertEqual(setting.value, color)
  
  def test_set_value_with_list(self):
    setting = settings_.ColorSetting('color')
    setting.set_value([5, 2, 8])
    
    self.assertEqual(setting.value, gimpcolor.RGB(5, 2, 8))
  
  def test_set_value_with_list_with_four_values(self):
    setting = settings_.ColorSetting('color')
    setting.set_value([5, 2, 8, 4])
    
    self.assertEqual(setting.value, gimpcolor.RGB(5, 2, 8, 4))
  
  def test_to_dict(self):
    setting = settings_.ColorSetting('color')
    setting.set_value(gimpcolor.RGB(5, 2, 8))
    
    self.assertDictEqual(
      setting.to_dict(), {'name': 'color', 'value': [5, 2, 8, 255], 'type': 'color'})
  
  def test_to_dict_with_four_values(self):
    setting = settings_.ColorSetting('color')
    setting.set_value(gimpcolor.RGB(5, 2, 8, 4))
    
    self.assertDictEqual(
      setting.to_dict(), {'name': 'color', 'value': [5, 2, 8, 4], 'type': 'color'})


@mock.patch(
  pgutils.get_pygimplib_module_path() + '.setting.settings.pdb', new=stubs_gimp.PdbStub())
class TestDisplaySetting(unittest.TestCase):
  
  def test_to_dict(self):
    setting = settings_.DisplaySetting('display')
    display = stubs_gimp.DisplayStub(id_=1)
    
    with mock.patch(
          pgutils.get_pygimplib_module_path() + '.setting.settings.pdb') as temp_mock_pdb:
      temp_mock_pdb.gimp_display_is_valid.return_value = True
      
      setting.set_value(display)
    
    self.assertDictEqual(
      setting.to_dict(), {'name': 'display', 'value': None, 'type': 'display'})


@mock.patch(
  pgutils.get_pygimplib_module_path() + '.setting.settings.gimp', new=stubs_gimp.GimpModuleStub())
class TestParasiteSetting(unittest.TestCase):
  
  def test_create_with_default_default_value(self):
    setting = settings_.ParasiteSetting('parasite')
    
    self.assertEqual(setting.value.name, 'parasite')
    self.assertEqual(setting.value.flags, 0)
    self.assertEqual(setting.value.data, '')
  
  def test_set_value_by_object(self):
    setting = settings_.ParasiteSetting('parasite')
    
    parasite = stubs_gimp.ParasiteStub('parasite_stub', 1, 'data')
    
    setting.set_value(parasite)
    
    self.assertEqual(setting.value, parasite)
  
  def test_set_value_by_list(self):
    setting = settings_.ParasiteSetting('parasite')
    
    setting.set_value(['parasite_stub', 1, 'data'])
    
    self.assertEqual(setting.value.name, 'parasite_stub')
    self.assertEqual(setting.value.flags, 1)
    self.assertEqual(setting.value.data, 'data')
  
  def test_to_dict(self):
    setting = settings_.ParasiteSetting('parasite')
    
    parasite = stubs_gimp.ParasiteStub('parasite_stub', 1, 'data')
    
    setting.set_value(parasite)
    
    self.assertDictEqual(
      setting.to_dict(),
      {'name': 'parasite', 'value': ['parasite_stub', 1, 'data'], 'type': 'parasite'})


class TestFileExtensionSetting(unittest.TestCase):
  
  def setUp(self):
    self.setting = settings_.FileExtensionSetting('file_ext', default_value='png')
  
  def test_with_adjust_value(self):
    setting = settings_.FileExtensionSetting('file_ext', adjust_value=True, default_value='png')
    
    setting.set_value('.jpg')
    
    self.assertEqual(setting.value, 'jpg')
  
  def test_invalid_default_value(self):
    with self.assertRaises(settings_.SettingDefaultValueError):
      settings_.FileExtensionSetting('file_ext', default_value=None)
  
  def test_custom_error_message(self):
    self.setting.error_messages[pgpath.FileValidatorErrorStatuses.IS_EMPTY] = (
      'my custom message')
    try:
      self.setting.set_value('')
    except settings_.SettingValueError as e:
      self.assertEqual(str(e), 'my custom message')


class TestDirpathSetting(unittest.TestCase):
  
  def setUp(self):
    self.setting = settings_.DirpathSetting('output_directory', default_value='/some_dir')
  
  def test_default_value_as_bytes_convert_to_unicode(self):
    setting = settings_.DirpathSetting(
      'output_directory', default_value=b'/some_dir/p\xc5\x88g')
    self.assertIsInstance(setting.value, str)
  
  def test_set_value_as_bytes_convert_to_unicode(self):
    self.setting.set_value(b'/some_dir/p\xc5\x88g')
    self.assertIsInstance(self.setting.value, str)


class TestBrushSetting(unittest.TestCase):
  
  def setUp(self):
    self.setting = settings_.BrushSetting('brush', default_value=('', -1, -1, -1))
  
  def test_init_with_brush_name_only(self):
    setting = settings_.BrushSetting('brush', default_value='Clipboard')
    
    self.assertEqual(setting.value, ('Clipboard',))
    self.assertEqual(setting.default_value, ('Clipboard',))
  
  @parameterized.parameterized.expand([
    ('one_element', ('Clipboard',), ('Clipboard',)),
    ('two_elements', ('Clipboard', 50.0), ('Clipboard', 50.0)),
    ('four_elements', ('Clipboard', 50.0, 10.0, -1), ('Clipboard', 50.0, 10.0, -1)),
  ])
  def test_set_value_with_tuple_valid_length(
        self, test_case_name_suffix, value, expected_value):
    self.setting.set_value(value)
    self.assertEqual(self.setting.value, expected_value)
  
  def test_set_value_with_tuple_invalid_length(self):
    with self.assertRaises(settings_.SettingValueError):
      self.setting.set_value(('', -1, -1, -1, -1))
  
  def test_set_value_converts_brush_name_to_tuple(self):
    self.setting.set_value('Clipboard')
    self.assertEqual(self.setting.value, ('Clipboard',))
  
  def test_set_value_converts_list_to_tuple(self):
    self.setting.set_value(['Clipboard', 50.0, 10.0, -1])
    self.assertEqual(self.setting.value, ('Clipboard', 50.0, 10.0, -1))
  
  def test_to_dict(self):
    self.setting.set_value(('Clipboard', 50.0, 10.0, -1))
    
    self.assertDictEqual(
      self.setting.to_dict(),
      {
        'name': 'brush',
        'value': ['Clipboard', 50.0, 10.0, -1],
        'type': 'brush',
        'default_value': ['', -1, -1, -1],
      })


#===============================================================================


class TestCreateArraySetting(unittest.TestCase):
  
  def test_create(self):
    setting = settings_.ArraySetting(
      'coordinates',
      default_value=(1.0, 5.0, 10.0),
      element_type='float',
      element_default_value=0.0)
    
    self.assertEqual(setting.name, 'coordinates')
    self.assertEqual(setting.default_value, (1.0, 5.0, 10.0))
    self.assertEqual(setting.value, (1.0, 5.0, 10.0))
    self.assertEqual(setting.element_type, settings_.FloatSetting)
    self.assertEqual(setting.element_default_value, 0.0)
  
  def test_create_with_empty_tuple(self):
    setting = settings_.ArraySetting(
      'coordinates',
      default_value=(),
      element_type='float',
      element_default_value=0.0)
    
    self.assertEqual(setting.default_value, ())
    self.assertEqual(setting.value, ())
  
  def test_create_with_element_default_value(self):
    setting = settings_.ArraySetting('coordinates', element_type='float')
    setting.add_element()
    
    self.assertEqual(setting[0].value, 0.0)
  
  def test_create_passing_non_tuple_as_default_value_converts_initial_value_to_tuple(self):
    setting = settings_.ArraySetting(
      'coordinates',
      default_value=[1.0, 5.0, 10.0],
      element_type='float',
      element_default_value=0.0)
    
    self.assertEqual(setting.default_value, (1.0, 5.0, 10.0))
    self.assertEqual(setting.value, (1.0, 5.0, 10.0))
  
  def test_create_with_additional_read_only_element_arguments(self):
    setting = settings_.ArraySetting(
      'coordinates',
      default_value=(1.0, 5.0, 10.0),
      element_type='float',
      element_default_value=0.0,
      element_min_value=-100.0,
      element_max_value=100.0)
    
    self.assertEqual(setting.element_min_value, -100.0)
    self.assertEqual(setting.element_max_value, 100.0)
    
    for setting_attribute in setting.__dict__:
      if setting_attribute.startswith('element_'):
        with self.assertRaises(AttributeError):
          setattr(setting, setting_attribute, None)
  
  def test_create_with_additional_arguments_overriding_internal_element_arguments(self):
    setting = settings_.ArraySetting(
      'coordinates',
      default_value=(1.0, 5.0, 10.0),
      element_type='float',
      element_default_value=0.0,
      element_min_value=-100.0,
      element_max_value=100.0,
      element_display_name='Coordinate')
    
    self.assertEqual(setting.element_display_name, 'Coordinate')
  
  def test_create_passing_invalid_default_value_raises_error(self):
    with self.assertRaises(settings_.SettingValueError):
      settings_.ArraySetting(
        'coordinates',
        default_value=(-200.0, 200.0),
        element_type='float',
        element_default_value=0.0,
        element_min_value=-100.0,
        element_max_value=100.0)
  
  @parameterized.parameterized.expand([
    ('default_value_is_empty', ()),
    ('default_value_is_not_empty', (1.0, 5.0, 10.0)),
  ])
  def test_create_invalid_element_default_value_raises_error(
        self, test_case_name_suffix, default_value):
    with self.assertRaises(settings_.SettingDefaultValueError):
      settings_.ArraySetting(
        'coordinates',
        default_value=default_value,
        element_type='float',
        element_default_value=-200.0,
        element_min_value=-100.0,
        element_max_value=100.0)
  
  @parameterized.parameterized.expand([
    ('element_pdb_type_is_registrable',
     settings_.SettingPdbTypes.automatic,
     'float',
     settings_.SettingPdbTypes.array_float),
    
    ('registration_is_disabled_explicitly',
     None,
     'float',
     settings_.SettingPdbTypes.none),
  ])
  def test_create_with_pdb_type(
        self, test_case_name_suffix,
        pdb_type, element_type, expected_pdb_type,
        value_set_func=None, value_save_func=None):
    setting = settings_.ArraySetting(
      'coordinates',
      default_value=(1.0, 5.0, 10.0),
      pdb_type=pdb_type,
      element_type=element_type,
      element_default_value=0.0)
    
    self.assertEqual(setting.pdb_type, expected_pdb_type)
  
  def test_create_with_pdb_type_element_pdb_type_is_not_registrable(self):
    setting = settings_.ArraySetting(
      'coordinates',
      default_value=(1.0, 5.0, 10.0),
      element_type='generic',
      element_default_value=0.0,
      element_value_set=lambda value: value,
      element_value_save=lambda value: value)
    
    self.assertEqual(setting.pdb_type, settings_.SettingPdbTypes.none)
  
  def test_create_with_explicit_valid_element_pdb_type(self):
    setting = settings_.ArraySetting(
      'coordinates',
      default_value=(1, 5, 10),
      element_type='integer',
      element_default_value=0,
      element_pdb_type=settings_.SettingPdbTypes.int16)
    
    self.assertEqual(setting.pdb_type, settings_.SettingPdbTypes.array_int16)
  
  def test_create_with_invalid_element_pdb_type(self):
    with self.assertRaises(ValueError):
      settings_.ArraySetting(
        'coordinates',
        default_value=(1.0, 5.0, 10.0),
        element_type='float',
        element_default_value=0.0,
        element_pdb_type=settings_.SettingPdbTypes.int16)
  
  def test_create_multidimensional_array(self):
    values = ((1.0, 5.0, 10.0), (2.0, 15.0, 25.0), (-5.0, 10.0, 40.0))
    
    setting = settings_.ArraySetting(
      'path_coordinates',
      default_value=values,
      element_type='array',
      element_default_value=(0.0, 0.0, 0.0),
      element_element_type='float',
      element_element_default_value=1.0)
    
    self.assertTupleEqual(setting.default_value, values)
    self.assertEqual(setting.element_type, settings_.ArraySetting)
    self.assertEqual(setting.element_default_value, (0.0, 0.0, 0.0))
    self.assertFalse(setting.can_be_registered_to_pdb())
    
    for i in range(len(setting)):
      self.assertEqual(setting[i].element_type, settings_.FloatSetting)
      self.assertEqual(setting[i].default_value, (0.0, 0.0, 0.0))
      self.assertEqual(setting[i].value, values[i])
      self.assertFalse(setting[i].can_be_registered_to_pdb())
      
      for j in range(len(setting[i])):
        self.assertEqual(setting[i][j].default_value, 1.0)
        self.assertEqual(setting[i][j].value, values[i][j])
  
  def test_create_multidimensional_array_with_default_default_values(self):
    setting = settings_.ArraySetting(
      'path_coordinates',
      element_type='array',
      element_element_type='float')
    
    setting.add_element()
    self.assertEqual(setting.value, ((),))
    setting[0].add_element()
    self.assertEqual(setting.value, ((0.0,),))


class TestArraySetting(unittest.TestCase):
  
  def setUp(self):
    self.setting = settings_.ArraySetting(
      'coordinates',
      default_value=(1.0, 5.0, 10.0),
      element_type='float',
      element_default_value=0.0,
      element_min_value=-100.0,
      element_max_value=100.0)
  
  def test_get_elements(self):
    self.assertListEqual(
      self.setting.get_elements(), [self.setting[0], self.setting[1], self.setting[2]])
    
  def test_get_elements_returns_a_copy(self):
    elements = self.setting.get_elements()
    del elements[0]
    self.assertNotEqual(self.setting.get_elements(), elements)
  
  def test_has_element_default_value_even_if_not_specified(self):
    setting = settings_.ArraySetting(
      'coordinates',
      element_type='float')
    
    self.assertTrue(hasattr(setting, 'element_default_value'))
    self.assertEqual(setting.element_default_value, 0.0)
  
  @parameterized.parameterized.expand([
    ('with_tuple', (20.0, 50.0, 40.0), (20.0, 50.0, 40.0)),
    ('with_list', [20.0, 50.0, 40.0], (20.0, 50.0, 40.0)),
  ])
  def test_set_value(self, test_case_name_suffix, input_value, expected_value):
    self.setting.set_value(input_value)
    
    self.assertEqual(self.setting.value, expected_value)
    for i, expected_element_value in enumerate(expected_value):
      self.assertEqual(self.setting[i].value, expected_element_value)
  
  def test_set_value_with_list_of_type_having_custom_set_value(self):
    setting = settings_.ArraySetting(
      'coordinates',
      default_value=(),
      element_type='brush',
      element_default_value=())
    
    setting.set_value(['Clipboard', 'Clipboard2'])
    
    self.assertEqual(setting.value, (('Clipboard',), ('Clipboard2',)))
  
  def test_set_value_validates_if_value_is_iterable(self):
    with self.assertRaises(settings_.SettingValueError):
      self.setting.set_value(45)
  
  @parameterized.parameterized.expand([
    ('first_is_invalid', (200.0, 50.0, 40.0)),
    ('middle_is_invalid', (20.0, 200.0, 40.0)),
    ('last_is_invalid', (20.0, 50.0, 200.0)),
    ('two_are_invalid', (20.0, 200.0, 200.0)),
    ('all_are_invalid', (200.0, 200.0, 200.0)),
  ])
  def test_set_value_validates_each_element_value_individually(
        self, test_case_name_suffix, input_value):
    with self.assertRaises(settings_.SettingValueError):
      self.setting.set_value(input_value)
  
  def test_reset_retains_default_value(self):
    self.setting.set_value((20.0, 50.0, 40.0))
    self.setting.reset()
    self.assertEqual(self.setting.value, (1.0, 5.0, 10.0))
    self.assertEqual(self.setting.default_value, (1.0, 5.0, 10.0))
  
  def test_to_dict(self):
    self.assertDictEqual(
      self.setting.to_dict(),
      {
        'name': 'coordinates',
        'value': [1.0, 5.0, 10.0],
        'type': 'array',
        'default_value': [1.0, 5.0, 10.0],
        'element_type': 'float',
        'element_default_value': 0.0,
        'element_max_value': 100.0,
        'element_min_value': -100.0,
      })
  
  def test_to_dict_with_type_having_custom_to_dict(self):
    setting = settings_.ArraySetting(
      'coordinates',
      default_value=(),
      element_type='brush',
      element_default_value=())
    
    setting.set_value(['Clipboard', 'Clipboard2'])
    
    self.assertDictEqual(
      setting.to_dict(),
      {
        'name': 'coordinates',
        'value': [['Clipboard'], ['Clipboard2']],
        'type': 'array',
        'default_value': [],
        'element_type': 'brush',
        'element_default_value': [],
      })
  
  def test_to_dict_with_element_type_as_class(self):
    setting = settings_.ArraySetting(
      'coordinates',
      default_value=(1.0, 5.0, 10.0),
      element_type=settings_.FloatSetting,
      element_default_value=0.0,
      element_min_value=-100.0,
      element_max_value=100.0)
    
    self.assertDictEqual(
      setting.to_dict(),
      {
        'name': 'coordinates',
        'value': [1.0, 5.0, 10.0],
        'type': 'array',
        'default_value': [1.0, 5.0, 10.0],
        'element_type': 'float',
        'element_default_value': 0.0,
        'element_max_value': 100.0,
        'element_min_value': -100.0,
      })
  
  @parameterized.parameterized.expand([
    ('first', 0, 1.0),
    ('middle', 1, 5.0),
    ('last', 2, 10.0),
    ('last_with_negative_index', -1, 10.0),
    ('second_to_last_with_negative_index', -2, 5.0),
  ])
  def test_getitem(self, test_case_name_suffix, index, expected_value):
    self.assertEqual(self.setting[index].value, expected_value)
  
  @parameterized.parameterized.expand([
    ('first_to_middle', None, 2, [1.0, 5.0]),
    ('middle_to_last', 1, None, [5.0, 10.0]),
    ('middle_to_last_explicit', 1, 3, [5.0, 10.0]),
    ('all', None, None, [1.0, 5.0, 10.0]),
    ('negative_last_to_middle', -1, -3, [10.0, 5.0], -1),
  ])
  def test_getitem_slice(
        self, test_case_name_suffix, index_begin, index_end, expected_value, step=None):
    self.assertEqual(
      [element.value for element in self.setting[index_begin:index_end:step]],
      expected_value)
  
  @parameterized.parameterized.expand([
    ('one_more_than_length', 3),
    ('more_than_length', 5),
  ])
  def test_getitem_out_of_bounds_raises_error(self, test_case_name_suffix, index):
    with self.assertRaises(IndexError):
      self.setting[index]
  
  @parameterized.parameterized.expand([
    ('first_element', [0]),
    ('middle_element', [1]),
    ('last_element', [2]),
    ('two_elements', [1, 1]),
    ('all_elements', [0, 0, 0]),
  ])
  def test_delitem(self, test_case_name_suffix, indexes_to_delete):
    orig_len = len(self.setting)
    
    for index in indexes_to_delete:
      del self.setting[index]
    
    self.assertEqual(len(self.setting), orig_len - len(indexes_to_delete))
  
  @parameterized.parameterized.expand([
    ('one_more_than_length', 3),
    ('more_than_length', 5),
  ])
  def test_delitem_out_of_bounds_raises_error(self, test_case_name_suffix, index):
    with self.assertRaises(IndexError):
      self.setting[index]
  
  @parameterized.parameterized.expand([
    ('append_default_value',
     None, settings_.ArraySetting.ELEMENT_DEFAULT_VALUE, -1, 0.0),
    
    ('insert_at_beginning_default_value',
     0, settings_.ArraySetting.ELEMENT_DEFAULT_VALUE, 0, 0.0),
    
    ('insert_in_middle_default_value',
     1, settings_.ArraySetting.ELEMENT_DEFAULT_VALUE, 1, 0.0),
    
    ('append_value',
     None, 40.0, -1, 40.0),
    
    ('insert_in_middle_value',
     1, 40.0, 1, 40.0),
  ])
  def test_add_element(
        self, test_case_name_suffix, index, value, insertion_index, expected_value):
    element = self.setting.add_element(index, value=value)
    self.assertEqual(len(self.setting), 4)
    self.assertIs(self.setting[insertion_index], element)
    self.assertEqual(self.setting[insertion_index].value, expected_value)
  
  def test_add_element_none_as_value(self):
    setting = settings_.ArraySetting(
      'coordinates',
      default_value=(),
      element_type='generic',
      element_default_value=0,
      element_value_set=lambda value: value,
      element_value_save=lambda value: value)
    
    setting.add_element(value=None)
    self.assertEqual(setting[-1].value, None)
  
  @parameterized.parameterized.expand([
    ('middle_to_first', 1, 0, [5.0, 1.0, 10.0]),
    ('middle_to_last', 1, 2, [1.0, 10.0, 5.0]),
    ('middle_to_last_above_bounds', 1, 3, [1.0, 10.0, 5.0]),
    ('first_to_middle', 0, 1, [5.0, 1.0, 10.0]),
    ('last_to_middle', 2, 1, [1.0, 10.0, 5.0]),
    ('middle_to_last_negative_position', 1, -1, [1.0, 10.0, 5.0]),
    ('middle_to_middle_negative_position', 1, -2, [1.0, 5.0, 10.0]),
  ])
  def test_reorder_element(
        self, test_case_name_suffix, index, new_index, expected_values):
    self.setting.reorder_element(index, new_index)
    self.assertEqual(
      [element.value for element in self.setting[:]],
      expected_values)
  
  def test_set_element_value(self):
    self.setting[1].set_value(50.0)
    self.assertEqual(self.setting[1].value, 50.0)
    self.assertEqual(self.setting.value, (1.0, 50.0, 10.0))
  
  def test_set_element_value_validates_value(self):
    with self.assertRaises(settings_.SettingValueError):
      self.setting[1].set_value(200.0)
  
  def test_reset_element_sets_element_default_value(self):
    self.setting[1].reset()
    self.assertEqual(self.setting[1].value, 0.0)
    self.assertEqual(self.setting.value, (1.0, 0.0, 10.0))
  
  def test_connect_event_for_individual_elements_affects_those_elements_only(self):
    def _on_array_changed(array_setting):
      array_setting[2].set_value(70.0)
    
    def _on_element_changed(element, array_setting):
      array_setting[0].set_value(20.0)
    
    self.setting.connect_event('value-changed', _on_array_changed)
    
    self.setting[1].connect_event('value-changed', _on_element_changed, self.setting)
    self.setting[1].set_value(50.0)
    
    self.assertEqual(self.setting[0].value, 20.0)
    self.assertEqual(self.setting[1].value, 50.0)
    self.assertEqual(self.setting[2].value, 10.0)
    self.assertEqual(self.setting.value, (20.0, 50.0, 10.0))
    
    self.setting.set_value((60.0, 80.0, 30.0))
    self.assertEqual(self.setting.value, (60.0, 80.0, 70.0))
  
  @parameterized.parameterized.expand([
    ('default_index',
     None, settings_.ArraySetting.ELEMENT_DEFAULT_VALUE, None, 0.0),
    
    ('explicit_index',
     1, settings_.ArraySetting.ELEMENT_DEFAULT_VALUE, 1, 0.0),
  ])
  def test_before_add_element_event(
        self, test_case_name_suffix, index, value, expected_index, expected_value):
    event_args = []
    
    def _on_before_add_element(array_setting, index, value):
      event_args.append((index, value))
    
    self.setting.connect_event('before-add-element', _on_before_add_element)
    
    self.setting.add_element(index, value)
    self.assertEqual(event_args[0][0], expected_index)
    self.assertEqual(event_args[0][1], expected_value)
  
  @parameterized.parameterized.expand([
    ('default_index',
     None, settings_.ArraySetting.ELEMENT_DEFAULT_VALUE, -1, 0.0),
    
    ('explicit_zero_index',
     0, settings_.ArraySetting.ELEMENT_DEFAULT_VALUE, 0, 0.0),
    
    ('explicit_positive_index',
     1, settings_.ArraySetting.ELEMENT_DEFAULT_VALUE, 1, 0.0),
    
    ('explicit_negative_index',
     -1, settings_.ArraySetting.ELEMENT_DEFAULT_VALUE, -2, 0.0),
  ])
  def test_after_add_element_event(
        self, test_case_name_suffix, index, value, expected_index, expected_value):
    event_args = []
    
    def _on_after_add_element(array_setting, insertion_index, value):
      event_args.append((insertion_index, value))
    
    self.setting.connect_event('after-add-element', _on_after_add_element)
    
    self.setting.add_element(index, value)
    self.assertEqual(event_args[0][0], expected_index)
    self.assertEqual(event_args[0][1], expected_value)
  
  @parameterized.parameterized.expand([
    ('default_length_name_and_description',
     None,
     None,
     b'coordinates-length',
     b'Number of elements in "coordinates"'),
    
    ('custom_length_name_and_description',
     'num-axes-coordinates',
     'The number of axes for coordinates',
     b'num-axes-coordinates',
     b'The number of axes for coordinates'),
  ])
  def test_get_pdb_param_for_registrable_setting(
        self,
        test_case_name_suffix,
        length_name,
        length_description,
        expected_length_name,
        expected_length_description):
    self.assertEqual(
      self.setting.get_pdb_param(length_name, length_description),
      [(settings_.SettingPdbTypes.int, expected_length_name, expected_length_description),
       (settings_.SettingPdbTypes.array_float, b'coordinates', b'Coordinates')])
  
  def test_get_pdb_param_for_nonregistrable_setting(self):
    setting = settings_.ArraySetting(
      'coordinates',
      default_value=(1.0, 5.0, 10.0),
      element_type='generic',
      element_default_value=0.0,
      element_value_set=lambda value: value,
      element_value_save=lambda value: value)
    
    self.assertEqual(setting.get_pdb_param(), None)


class TestArraySettingCreateWithSize(unittest.TestCase):
  
  @parameterized.parameterized.expand([
    ('default_sizes', None, None, 0, None),
    ('min_size_zero', 0, None, 0, None),
    ('min_size_positive', 1, None, 1, None),
    ('min_size_positive_max_size_positive', 1, 5, 1, 5),
    ('max_size_equal_to_default_value_length', 1, 3, 1, 3),
    ('min_and_max_size_equal_to_default_value_length', 3, 3, 3, 3),
  ])
  def test_create_with_size(
        self,
        test_case_name_suffix,
        min_size,
        max_size,
        expected_min_size,
        expected_max_size):
    setting = settings_.ArraySetting(
      'coordinates',
      default_value=(1.0, 5.0, 10.0),
      element_type='float',
      element_default_value=0.0,
      min_size=min_size,
      max_size=max_size)
    
    self.assertEqual(setting.min_size, expected_min_size)
    self.assertEqual(setting.max_size, expected_max_size)
  
  @parameterized.parameterized.expand([
    ('min_size_negative', -1, None),
    ('max_size_less_than_min_size', 5, 4),
    ('max_size_less_than_default_value_length', 0, 2),
    ('min_size_greater_than_default_value_length', 4, None),
  ])
  def test_create_raises_error_on_invalid_size(
        self, test_case_name_suffix, min_size, max_size):
    with self.assertRaises(settings_.SettingDefaultValueError):
      settings_.ArraySetting(
        'coordinates',
        default_value=(1.0, 5.0, 10.0),
        element_type='float',
        element_default_value=0.0,
        min_size=min_size,
        max_size=max_size)


class TestArraySettingSize(unittest.TestCase):
  
  def setUp(self):
    self.setting = settings_.ArraySetting(
      'coordinates',
      default_value=(1.0, 5.0, 10.0),
      element_type='float',
      element_default_value=0.0,
      element_min_value=-100.0,
      element_max_value=100.0,
      min_size=2,
      max_size=4)
  
  def test_set_value_with_respect_to_size(self):
    try:
      self.setting.set_value((5.0, 10.0))
    except settings_.SettingValueError:
      self.fail(
        'setting the value while satisfying size restrictions should not raise error')
  
  @parameterized.parameterized.expand([
    ('value_length_less_than_min_size', (1.0,)),
    ('value_length_greater_than_max_size', (1.0, 5.0, 10.0, 30.0, 70.0)),
  ])
  def test_set_value_invalid_size_raises_error(self, test_case_name_suffix, value):
    with self.assertRaises(settings_.SettingValueError):
      self.setting.set_value(value)
  
  def test_add_element_with_respect_to_size(self):
    try:
      self.setting.add_element()
    except settings_.SettingValueError:
      self.fail(
        'adding an element while satisfying size restrictions should not raise error')
  
  def test_add_element_more_than_max_size_raises_error(self):
    self.setting.add_element()
    with self.assertRaises(settings_.SettingValueError):
      self.setting.add_element()
  
  def test_delete_element_with_respect_to_size(self):
    try:
      del self.setting[-1]
    except settings_.SettingValueError:
      self.fail(
        'deleting an element while satisfying size restrictions should not raise error')
  
  def test_delete_element_less_then_min_size_raises_error(self):
    del self.setting[-1]
    with self.assertRaises(settings_.SettingValueError):
      del self.setting[-1]


class TestContainerSettings(unittest.TestCase):
  
  def test_set_value_nullable_allows_none(self):
    setting = settings_.ListSetting('setting', nullable=True)
    
    setting.set_value(None)
    self.assertIsNone(setting.value)
  
  def test_set_value_for_list_setting(self):
    expected_value = [1, 4, 'five']
    
    setting = settings_.ListSetting('setting')
    
    setting.set_value(expected_value)
    self.assertEqual(setting.value, expected_value)
    
    setting.set_value(tuple(expected_value))
    self.assertListEqual(setting.value, expected_value)
  
  def test_set_value_for_tuple_setting(self):
    expected_value = (1, 4, 'five')
    
    setting = settings_.TupleSetting('setting')
    
    setting.set_value(expected_value)
    self.assertEqual(setting.value, expected_value)
    
    setting.set_value(list(expected_value))
    self.assertTupleEqual(setting.value, expected_value)
  
  def test_to_dict_for_tuple_setting(self):
    expected_value = (1, 4, 'five')
    
    setting = settings_.TupleSetting('setting')
    
    setting.set_value(expected_value)
    
    self.assertDictEqual(
      setting.to_dict(), {'name': 'setting', 'value': [1, 4, 'five'], 'type': 'tuple'})
  
  def test_set_value_for_set_setting(self):
    expected_value = set([1, 4, 'five'])
    
    setting = settings_.SetSetting('setting')
    
    setting.set_value(expected_value)
    self.assertEqual(setting.value, expected_value)
    
    setting.set_value(list(expected_value))
    self.assertSetEqual(setting.value, expected_value)
  
  def test_to_dict_for_set_setting(self):
    expected_value = set([1, 4, 'five'])
    
    setting = settings_.SetSetting('setting')

    setting.set_value(expected_value)
    
    self.assertDictEqual(
      setting.to_dict(), {'name': 'setting', 'value': list(expected_value), 'type': 'set'})


class TestSettingTypeFunctions(unittest.TestCase):
  
  def test_process_setting_type_with_name(self):
    self.assertEqual(settings_.process_setting_type('int'), settings_.IntSetting)
  
  def test_process_setting_type_with_type(self):
    self.assertEqual(settings_.process_setting_type(settings_.IntSetting), settings_.IntSetting)
  
  def test_process_setting_type_with_invalid_name(self):
    with self.assertRaises(TypeError):
      self.assertEqual(settings_.process_setting_type('invalid_type'))
  
  def test_process_setting_type_with_invalid_type(self):
    with self.assertRaises(TypeError):
      self.assertEqual(settings_.process_setting_type(object()))


class TestSettingGuiTypeFunctions(unittest.TestCase):
  
  def test_process_setting_gui_type_with_name(self):
    self.assertEqual(
      settings_.process_setting_gui_type('check_button'), presenters_gtk.CheckButtonPresenter)
  
  def test_process_setting_gui_type_with_type(self):
    self.assertEqual(
      settings_.process_setting_gui_type(presenters_gtk.CheckButtonPresenter),
      presenters_gtk.CheckButtonPresenter)
  
  def test_process_setting_gui_type_with_invalid_name(self):
    with self.assertRaises(TypeError):
      self.assertEqual(settings_.process_setting_gui_type('invalid_type'))
  
  def test_process_setting_gui_type_with_invalid_type(self):
    with self.assertRaises(TypeError):
      self.assertEqual(settings_.process_setting_gui_type(object()))
