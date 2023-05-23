# -*- coding: utf-8 -*-

"""GUI-specific plug-in settings."""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import collections

import gimp

from export_layers import pygimplib as pg


def create_gui_settings():
  gui_settings = pg.setting.Group(
    name='gui',
    setting_attributes={'setting_sources': ['session', 'persistent']})
  
  size_gui_settings = pg.setting.Group(
    name='size',
    setting_attributes={'setting_sources': ['session', 'persistent']})
  
  size_gui_settings.add([
    {
      'type': 'tuple',
      'name': 'dialog_position',
      'default_value': (),
    },
    {
      'type': 'tuple',
      'name': 'dialog_size',
      'default_value': (),
    },
    {
      'type': 'integer',
      'name': 'paned_outside_previews_position',
      'default_value': 610,
    },
    {
      'type': 'float',
      'name': 'paned_between_previews_position',
      'default_value': 360,
    },
    {
      'type': 'float',
      'name': 'settings_vpane_position',
      'default_value': 400,
    },
  ])
  
  gui_settings.add([
    {
      'type': 'boolean',
      'name': 'show_more_settings',
      'default_value': False,
    },
    {
      'type': 'boolean',
      'name': 'name_preview_sensitive',
      'default_value': True,
      'gui_type': None,
    },
    {
      'type': 'boolean',
      'name': 'image_preview_sensitive',
      'default_value': True,
      'gui_type': None,
    },
    {
      'type': 'boolean',
      'name': 'image_preview_automatic_update',
      'default_value': True,
      'gui_type': None,
    },
    {
      'type': 'boolean',
      'name': 'image_preview_automatic_update_if_below_maximum_duration',
      'default_value': True,
      'gui_type': None,
    },
    size_gui_settings,
  ])
  
  session_only_gui_settings = pg.setting.Group(
    name='gui_session',
    setting_attributes={'setting_sources': ['session']})
  
  session_only_gui_settings.add([
    {
      'type': 'image_IDs_and_directories',
      'name': 'image_ids_and_directories',
      'default_value': {},
      'tags': ['ignore_reset'],
    },
    {
      'type': 'generic',
      'name': 'name_preview_layers_collapsed_state',
      # key: image ID
      # value: set of layer IDs collapsed in the name preview
      'default_value': collections.defaultdict(set),
    },
    {
      'type': 'generic',
      'name': 'image_preview_displayed_layers',
      # key: image ID; value: ID of the layer displayed in the preview
      'default_value': collections.defaultdict(pg.utils.return_none_func),
    },
    {
      # Needs to be string type to avoid strict directory validation.
      'type': 'string',
      'name': 'current_directory',
      'default_value': gimp.user_directory(1),  # `Documents` directory
      'gui_type': None,
      'tags': ['ignore_load'],
    },
  ])
  
  persistent_only_gui_settings = pg.setting.Group(
    name='gui_persistent',
    setting_attributes={'setting_sources': ['persistent']})
  
  persistent_only_gui_settings.add([
    {
      'type': 'generic',
      'name': 'name_preview_layers_collapsed_state',
      # key: image file path
      # value: set of layer names collapsed in the name preview
      'default_value': collections.defaultdict(set)
    },
    {
      'type': 'generic',
      'name': 'image_preview_displayed_layers',
      # key: image file path
      # value: name of the layer displayed in the preview
      'default_value': collections.defaultdict(pg.utils.return_none_func)
    },
  ])
  
  return gui_settings, session_only_gui_settings, persistent_only_gui_settings
