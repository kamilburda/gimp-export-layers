# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import collections

import pygtk
pygtk.require('2.0')
import gtk

import unittest

import mock
import parameterized

from export_layers import pygimplib as pg

from export_layers.pygimplib.tests import stubs_gimp

from export_layers import update


@mock.patch(
  pg.utils.get_pygimplib_module_path() + '.setting.sources.gimpshelf.shelf',
  new_callable=stubs_gimp.ShelfStub)
@mock.patch(
  pg.utils.get_pygimplib_module_path() + '.setting.sources.gimp',
  new_callable=stubs_gimp.GimpModuleStub)
@mock.patch(
  'export_layers.update.gimpshelf.shelf',
  new_callable=stubs_gimp.ShelfStub)
@mock.patch(
  'export_layers.update.gimp',
  new_callable=stubs_gimp.GimpModuleStub)
@mock.patch('export_layers.update.handle_update')
@mock.patch('export_layers.gui.messages.display_message')
class TestUpdate(unittest.TestCase):
  
  def setUp(self):
    self.settings = pg.setting.create_groups({
      'name': 'all_settings',
      'groups': [
        {
          'name': 'main',
          'setting_attributes': {'setting_sources': ['persistent']},
        }
      ]
    })
    
    self.current_version = '3.3'
    self.new_version = '3.4'
    self.old_incompatible_version = '0.1'
    
    self.settings['main'].add([
      {
        'type': 'string',
        'name': 'plugin_version',
        'default_value': self.new_version,
        'pdb_type': None,
        'gui_type': None,
      },
      {
        'type': 'string',
        'name': 'test_setting',
        'default_value': 'test',
        'pdb_type': None,
        'gui_type': None,
      },
    ])
  
  def test_fresh_start_stores_new_version(self, *mocks):
    self.assertFalse(pg.setting.Persistor.get_default_setting_sources()['persistent'].has_data())
    
    status, unused_ = update.update(self.settings)
    
    self.assertEqual(status, update.FRESH_START)
    self.assertEqual(self.settings['main/plugin_version'].value, self.new_version)
    
    load_result = self.settings['main/plugin_version'].load()
    
    self.assertEqual(self.settings['main/plugin_version'].value, self.new_version)
    self.assertEqual(load_result.status, pg.setting.Persistor.SUCCESS)
  
  def test_minimum_version_or_later_is_overwritten_by_new_version(self, *mocks):
    self.settings['main/plugin_version'].set_value(self.current_version)
    self.settings['main/plugin_version'].save()
    
    status, unused_ = update.update(self.settings)
    
    self.assertEqual(status, update.UPDATE)
    self.assertEqual(self.settings['main/plugin_version'].value, self.new_version)
  
  def test_persistent_source_has_data_but_not_version_clears_setting_sources(
        self, mock_display_message, *other_mocks):
    mock_display_message.return_value = gtk.RESPONSE_YES
    
    self.settings['main/test_setting'].save()
    
    status, unused_ = update.update(self.settings)
    
    self.assertEqual(status, update.CLEAR_SETTINGS)
    self.assertEqual(self.settings['main/plugin_version'].value, self.new_version)
  
  def test_less_than_minimum_version_clears_setting_sources(
        self, mock_display_message, *other_mocks):
    mock_display_message.return_value = gtk.RESPONSE_YES
    
    self.settings['main/plugin_version'].set_value(self.old_incompatible_version)
    self.settings['main'].save()
    
    status, unused_ = update.update(self.settings)
    
    load_result = self.settings['main/test_setting'].load()
    
    self.assertEqual(status, update.CLEAR_SETTINGS)
    self.assertEqual(self.settings['main/plugin_version'].value, self.new_version)
    self.assertEqual(load_result.status, pg.setting.Persistor.PARTIAL_SUCCESS)
    self.assertTrue(bool(load_result.settings_not_loaded))
  
  def test_ask_to_clear_positive_response(self, mock_display_message, *other_mocks):
    mock_display_message.return_value = gtk.RESPONSE_YES
    
    self.settings['main/plugin_version'].set_value(self.old_incompatible_version)
    self.settings['main'].save()
    
    status, unused_ = update.update(self.settings, 'ask_to_clear')
    
    load_result = self.settings['main/test_setting'].load()
    
    self.assertEqual(status, update.CLEAR_SETTINGS)
    self.assertEqual(self.settings['main/plugin_version'].value, self.new_version)
    self.assertEqual(load_result.status, pg.setting.Persistor.PARTIAL_SUCCESS)
    self.assertTrue(bool(load_result.settings_not_loaded))
  
  def test_ask_to_clear_negative_response(self, mock_display_message, *other_mocks):
    mock_display_message.return_value = gtk.RESPONSE_NO
    
    self.settings['main/plugin_version'].set_value(self.old_incompatible_version)
    self.settings['main'].save()
    
    status, unused_ = update.update(self.settings, 'ask_to_clear')
    
    load_result = self.settings['main/test_setting'].load()
    
    self.assertEqual(status, update.ABORT)
    self.assertEqual(self.settings['main/plugin_version'].value, self.old_incompatible_version)
    self.assertEqual(load_result.status, pg.setting.Persistor.SUCCESS)


class TestHandleUpdate(unittest.TestCase):
  
  def setUp(self):
    self.update_handlers = collections.OrderedDict([
      ('3.3.1', lambda *args, **kwargs: self._invoked_handlers.append('3.3.1')),
      ('3.4', lambda *args, **kwargs: self._invoked_handlers.append('3.4')),
      ('3.5', lambda *args, **kwargs: self._invoked_handlers.append('3.5')),
    ])
    
    self._invoked_handlers = []
    
    self.settings = pg.setting.Group('settings')
  
  @parameterized.parameterized.expand([
    ['previous_version_earlier_than_all_handlers_invoke_one_handler',
     '3.3', '3.3.1', ['3.3.1']],
    ['previous_version_earlier_than_all_handlers_invoke_multiple_handlers',
     '3.3', '3.4', ['3.3.1', '3.4']],
    ['equal_previous_and_current_version_invoke_no_handler',
     '3.5', '3.5', []],
    ['equal_previous_and_current_version_and_globally_not_latest_invoke_no_handler',
     '3.3.1', '3.3.1', []],
    ['previous_version_equal_to_first_handler_invoke_one_handler',
     '3.3.1', '3.4', ['3.4']],
    ['previous_version_equal_to_latest_handler_invoke_no_handler',
     '3.5', '3.6', []],
    ['previous_greater_than_handlers_invoke_no_handler',
     '3.6', '3.6', []],
  ])
  def test_handle_update(
        self,
        test_case_name_suffix,
        previous_version_str,
        current_version_str,
        invoked_handlers):
    update.handle_update(
      self.settings,
      {},
      self.update_handlers,
      pg.version.Version.parse(previous_version_str),
      pg.version.Version.parse(current_version_str),
      False,
      False)
    
    self.assertEqual(self._invoked_handlers, invoked_handlers)


class TestReplaceFieldArgumentsInPattern(unittest.TestCase):
  
  @parameterized.parameterized.expand([
    ['single_argument_per_field',
     [['layer name', r'keep extension', r'%e'], ['tags', r'\$\$', r'%t']],
     '[layer name, keep extension]_[layer name]_[tags, _, ($$)]',
     '[layer name, %e]_[layer name]_[tags, _, (%t)]'],
    
    ['multiple_arguments_per_field',
     [['layer name', r'keep extension', r'%e'],
      ['layer name', r'lowercase', r'%l'],
      ['tags', r'\$\$', r'%t']],
     '[layer name, lowercase, keep extension]_[layer name]_[tags, _, ($$)]',
     '[layer name, %l, %e]_[layer name]_[tags, _, (%t)]'],
    
    ['unspecified_fields_remain_unmodified',
     [['layer name', r'keep extension', r'%e'], ['tags', r'\$\$', r'%t']],
     '[layer name, keep extension]_[001]_[tags, _, ($$)]',
     '[layer name, %e]_[001]_[tags, _, (%t)]'],
  ])
  def test_replace_field_arguments_in_pattern(
        self, test_case_name_suffix, fields_and_replacements, pattern, expected_output):
    self.assertEqual(
      update.replace_field_arguments_in_pattern(pattern, fields_and_replacements),
      expected_output)
  
  @parameterized.parameterized.expand([
    ['multiple_arguments_per_field',
     [
       ['layer path', [r'(.*)', r'(.*)'], [r'\1', r'\1', '%e']],
       ['layer path', [r'(.*)'], [r'\1', '%c', '%e']],
       ['layer path', [], ['-', '%c', '%e']],
     ],
     '[layer path]_[layer path, _, (%c)]_[tags, _, (%t)]',
     '[layer path, -, %c, %e]_[layer path, _, (%c), %e]_[tags, _, (%t)]'],
  ])
  def test_replace_field_arguments_in_pattern_with_lists(
        self, test_case_name_suffix, fields_and_replacements, pattern, expected_output):
    self.assertEqual(
      update.replace_field_arguments_in_pattern(pattern, fields_and_replacements, as_lists=True),
      expected_output)
