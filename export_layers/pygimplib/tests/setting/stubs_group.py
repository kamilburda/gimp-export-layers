# -*- coding: utf-8 -*-

"""Stubs primarily to be used in the `test_group_` module."""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

from ...setting import group as group_
from ...setting import settings as settings_


def create_test_settings():
  settings = group_.Group('main')
  settings.add([
    {
      'type': settings_.SettingTypes.file_extension,
      'name': 'file_extension',
      'default_value': 'bmp',
      'display_name': 'File extension'
    },
    {
      'type': settings_.SettingTypes.boolean,
      'name': 'only_visible_layers',
      'default_value': False,
      'display_name': 'Only visible layers',
      'setting_sources': [object()]
    },
    {
      'type': settings_.SettingTypes.enumerated,
      'name': 'overwrite_mode',
      'default_value': 'rename_new',
      'items': [('replace', 'Replace'),
                ('skip', 'Skip'),
                ('rename_new', 'Rename new file'),
                ('rename_existing', 'Rename existing file')],
      'error_messages': {
        'invalid_value': (
          'Invalid value. Something went wrong on our end... we are so sorry!')}
    },
  ])
  
  return settings


def create_test_settings_hierarchical():
  main_settings = group_.Group('main')
  main_settings.add([
    {
      'type': settings_.SettingTypes.file_extension,
      'name': 'file_extension',
      'default_value': 'bmp',
      'display_name': 'File extension'
    },
  ])
  
  advanced_settings = group_.Group('advanced')
  advanced_settings.add([
    {
      'type': settings_.SettingTypes.boolean,
      'name': 'only_visible_layers',
      'default_value': False,
      'display_name': 'Only visible layers',
    },
    {
      'type': settings_.SettingTypes.enumerated,
      'name': 'overwrite_mode',
      'default_value': 'rename_new',
      'items': [('replace', 'Replace'),
                ('skip', 'Skip'),
                ('rename_new', 'Rename new file'),
                ('rename_existing', 'Rename existing file')],
    },
  ])
  
  settings = group_.Group('settings')
  settings.add([main_settings, advanced_settings])
  
  return settings


def create_test_settings_load_save():
  dummy_session_source, dummy_persistent_source = 'session_source', 'persistent_source'
  
  main_settings = group_.Group(
    name='main',
    setting_attributes={
      'setting_sources': [dummy_session_source, dummy_persistent_source]})
  
  main_settings.add([
    {
      'type': settings_.SettingTypes.file_extension,
      'name': 'file_extension',
      'default_value': 'bmp',
    },
  ])
  
  advanced_settings = group_.Group(
    name='advanced', setting_attributes={'setting_sources': [dummy_session_source]})
  
  advanced_settings.add([
    {
      'type': settings_.SettingTypes.boolean,
      'name': 'only_visible_layers',
      'default_value': False,
      'setting_sources': [dummy_persistent_source, dummy_session_source]
    },
    {
      'type': settings_.SettingTypes.boolean,
      'name': 'use_layer_size',
      'default_value': False
    },
  ])
  
  settings = group_.Group('settings')
  settings.add([main_settings, advanced_settings])
  
  return settings
