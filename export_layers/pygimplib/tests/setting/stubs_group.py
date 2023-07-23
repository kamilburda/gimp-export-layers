# -*- coding: utf-8 -*-

"""Stubs primarily to be used in the `test_group_` module."""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

from ...setting import group as group_


def create_test_settings():
  settings = group_.Group('main')
  settings.add([
    {
      'type': 'file_extension',
      'name': 'file_extension',
      'default_value': 'bmp',
      'display_name': 'File extension'
    },
    {
      'type': 'boolean',
      'name': 'flatten',
      'default_value': False,
      'display_name': 'Flatten',
    },
    {
      'type': 'options',
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
      'type': 'file_extension',
      'name': 'file_extension',
      'default_value': 'bmp',
      'display_name': 'File extension'
    },
  ])
  
  advanced_settings = group_.Group('advanced')
  advanced_settings.add([
    {
      'type': 'boolean',
      'name': 'flatten',
      'default_value': False,
      'display_name': 'Flatten',
    },
    {
      'type': 'options',
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


def create_test_settings_with_specific_setting_sources():
  main_settings = group_.Group(
    name='main',
    setting_attributes={'setting_sources': ['persistent']})
  
  main_settings.add([
    {
      'type': 'file_extension',
      'name': 'file_extension',
      'default_value': 'png',
    },
  ])
  
  advanced_settings = group_.Group(
    name='advanced', setting_attributes={'setting_sources': ['session']})
  
  advanced_settings.add([
    {
      'type': 'boolean',
      'name': 'flatten',
      'default_value': False,
      'setting_sources': ['persistent', 'session'],
      'tags': ['ignore_load', 'ignore_save'],
    },
    {
      'type': 'boolean',
      'name': 'use_layer_size',
      'default_value': False,
    },
  ])
  
  settings = group_.Group('settings')
  settings.add([main_settings, advanced_settings])
  
  return settings


def create_test_data_with_specific_setting_sources():
  return [
    {
      'name': 'settings',
      'settings': [
        {
          'name': 'main',
          'setting_attributes': {'setting_sources': ['persistent']},
          'settings': [
            {
              'type': 'file_extension',
              'name': 'file_extension',
              'value': 'png',
              'setting_sources': ['persistent'],
            },
          ],
        },
        {
          'name': 'advanced',
          'setting_attributes': {'setting_sources': ['session']},
          'settings': [
            {
              'type': 'boolean',
              'name': 'flatten',
              'value': False,
              'setting_sources': ['persistent', 'session'],
              'tags': ['ignore_load', 'ignore_save'],
            },
            {
              'type': 'boolean',
              'name': 'use_layer_size',
              'value': False,
              'setting_sources': ['session'],
            },
          ],
        },
      ],
    }
  ]
