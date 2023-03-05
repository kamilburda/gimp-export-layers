# -*- coding: utf-8 -*-

"""Built-in plug-in constraints."""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import collections

from gimp import pdb

from export_layers import pygimplib as pg


CONSTRAINTS_LAYER_TYPES_GROUP = 'constraints_layer_types'


def is_layer(item):
  return item.type == pg.itemtree.TYPE_ITEM


def is_nonempty_group(item):
  return item.type == pg.itemtree.TYPE_GROUP and pdb.gimp_item_get_children(item.raw)[1]


def is_path_visible(item):
  return item.path_visible


def is_top_level(item):
  return item.depth == 0


def has_tags(item, tags=None):
  if tags:
    return any(tag for tag in tags if tag in item.tags)
  else:
    return bool(item.tags)


def has_no_tags(item, tags=None):
  return not has_tags(item, tags)


def has_matching_file_extension(item, file_extension):
  return pg.path.get_file_extension(item.name).lower() == file_extension.lower()


def has_matching_default_file_extension(item, exporter):
  return pg.path.get_file_extension(item.name).lower() == exporter.default_file_extension.lower()


def is_item_in_selected_items(item, selected_layers):
  return item.raw.ID in selected_layers


_BUILTIN_CONSTRAINTS_LIST = [
  {
    'name': 'include_layers',
    'type': 'constraint',
    'function': is_layer,
    'display_name': _('Include layers'),
    'subfilter': 'layer_types',
    'action_groups': [CONSTRAINTS_LAYER_TYPES_GROUP],
  },
  {
    'name': 'include_layer_groups',
    'type': 'constraint',
    'function': is_nonempty_group,
    'display_name': _('Include layer groups'),
    'subfilter': 'layer_types',
    'action_groups': [CONSTRAINTS_LAYER_TYPES_GROUP],
  },
  {
    'name': 'only_visible_layers',
    'type': 'constraint',
    'function': is_path_visible,
    'enabled': False,
    'display_name': _('Only visible layers'),
  },
  {
    'name': 'only_toplevel_layers',
    'type': 'constraint',
    'function': is_top_level,
    'display_name': _('Only top-level layers'),
  },
  {
    'name': 'only_layers_with_tags',
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
    'display_name': _('Only layers with tags'),
  },
  {
    'name': 'only_layers_without_tags',
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
    'display_name': _('Only layers without tags'),
  },
  {
    'name': 'only_layers_matching_file_extension',
    'type': 'constraint',
    'function': has_matching_default_file_extension,
    'display_name': _('Only layers matching file extension'),
  },
  {
    'name': 'only_selected_layers',
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
    'display_name': _('Only layers selected in preview'),
  },
]

BUILTIN_CONSTRAINTS = collections.OrderedDict(
  (action_dict['name'], action_dict)
  for action_dict in _BUILTIN_CONSTRAINTS_LIST)
