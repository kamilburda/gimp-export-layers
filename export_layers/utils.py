# -*- coding: utf-8 -*-

"""Utility functions used in other modules."""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

from export_layers import pygimplib as pg


def get_settings_for_batcher(main_settings):
  return {
    'procedures': main_settings['procedures'],
    'constraints': main_settings['constraints'],
    'edit_mode': main_settings['edit_mode'].value,
    'output_directory': main_settings['output_directory'].value,
    'layer_filename_pattern': main_settings['layer_filename_pattern'].value,
    'file_extension': main_settings['file_extension'].value,
    'overwrite_mode': main_settings['overwrite_mode'].value,
  }


def clear_setting_sources(settings, sources=None):
  if sources is None:
    sources = pg.setting.Persistor.get_default_setting_sources()
  
  pg.setting.Persistor.clear(sources)
  
  save_plugin_version(settings, sources)


def save_plugin_version(settings, sources):
  settings['main/plugin_version'].reset()
  settings['main/plugin_version'].save(sources)
