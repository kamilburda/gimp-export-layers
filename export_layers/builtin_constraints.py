# -*- coding: utf-8 -*-

"""Built-in plug-in constraints."""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import collections

from gimp import pdb

from export_layers import pygimplib as pg


def is_layer(item):
  return item.type == pg.itemtree.TYPE_ITEM


def is_nonempty_group(item):
  return item.type == pg.itemtree.TYPE_GROUP and pdb.gimp_item_get_children(item.raw)[1]


def has_matching_file_extension(item, file_extension):
  return pg.path.get_file_extension(item.name).lower() == file_extension.lower()


def has_matching_default_file_extension(item, batcher):
  return (
    pg.path.get_file_extension(item.name).lower()
    == batcher.batch_settings['file_extension'].value.lower())


def is_item_in_selected_items(item, selected_layers):
  return item.raw.ID in selected_layers


def is_top_level(item):
  return item.depth == 0


def is_path_visible(item):
  path_visible = True
  if not item.raw.visible:
    path_visible = False
  else:
    for parent in item.parents:
      if not parent.raw.visible:
        path_visible = False
        break
  
  return path_visible


def has_tags(item, tags=None):
  if tags:
    return any(tag for tag in tags if tag in item.tags)
  else:
    return bool(item.tags)


def has_no_tags(item, tags=None):
  return not has_tags(item, tags)


_BUILTIN_CONSTRAINTS_LIST = [
  {
    'name': 'layers',
    'type': 'constraint',
    'function': is_layer,
    'display_name': _('Layers'),
  },
  {
    'name': 'layer_groups',
    'type': 'constraint',
    'function': is_nonempty_group,
    'display_name': _('Layer groups'),
  },
  {
    'name': 'matching_file_extension',
    'type': 'constraint',
    'function': has_matching_default_file_extension,
    'display_name': _('Matching file extension'),
  },
  {
    'name': 'selected_in_preview',
    'type': 'constraint',
    'function': is_item_in_selected_items,
    'arguments': [
      {
        'type': pg.SettingTypes.generic,
        'name': 'selected_layers',
        'default_value': set(),
        'gui_type': None,
      },
    ],
    'display_name': _('Selected in preview'),
  },
  {
    'name': 'top_level',
    'type': 'constraint',
    'function': is_top_level,
    'display_name': _('Top-level'),
  },
  {
    'name': 'visible',
    'type': 'constraint',
    'function': is_path_visible,
    'display_name': _('Visible'),
  },
  {
    'name': 'with_tags',
    'type': 'constraint',
    'function': has_tags,
    'arguments': [
      {
        'type': pg.SettingTypes.array,
        'name': 'tags',
        'element_type': pg.SettingTypes.string,
        'default_value': (),
      },
    ],
    'display_name': _('With tags'),
  },
  {
    'name': 'without_tags',
    'type': 'constraint',
    'function': has_no_tags,
    'arguments': [
      {
        'type': pg.SettingTypes.array,
        'name': 'tags',
        'element_type': pg.SettingTypes.string,
        'default_value': (),
      },
    ],
    'display_name': _('Without tags'),
  },
]

BUILTIN_CONSTRAINTS = collections.OrderedDict(
  (action_dict['name'], action_dict)
  for action_dict in _BUILTIN_CONSTRAINTS_LIST)
