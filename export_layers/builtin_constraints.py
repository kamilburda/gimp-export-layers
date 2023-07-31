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
  return pg.path.get_file_extension(item.name).lower() == batcher.file_extension.lower()


def is_item_in_selected_items(item, selected_items):
  return item.raw.ID in selected_items


def is_top_level(item):
  return item.depth == 0


def is_visible(item):
  return item.raw.visible


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
    # FOR TRANSLATORS: Think of "Only layers matching file extension" when translating this
    'display_name': _('Matching file extension'),
  },
  {
    'name': 'selected_in_preview',
    'type': 'constraint',
    'function': is_item_in_selected_items,
    # FOR TRANSLATORS: Think of "Only layers selected in preview" when translating this
    'display_name': _('Selected in preview'),
    'arguments': [
      {
        'type': 'set',
        'name': 'selected_layers',
        'display_name': _('Selected layers'),
        'gui_type': None,
      },
    ],
  },
  {
    'name': 'top_level',
    'type': 'constraint',
    'function': is_top_level,
    # FOR TRANSLATORS: Think of "Only top-level layers" when translating this
    'display_name': _('Top-level'),
  },
  {
    'name': 'visible',
    'type': 'constraint',
    'function': is_visible,
    # FOR TRANSLATORS: Think of "Only visible layers" when translating this
    'display_name': _('Visible'),
  },
  {
    'name': 'with_tags',
    'type': 'constraint',
    'function': has_tags,
    # FOR TRANSLATORS: Think of "Only layers with tags" when translating this
    'display_name': _('With tags'),
    'arguments': [
      {
        'type': 'array',
        'name': 'tags',
        'display_name': _('Tags'),
        'element_type': 'string',
        'default_value': (),
      },
    ],
  },
  {
    'name': 'without_tags',
    'type': 'constraint',
    'function': has_no_tags,
    # FOR TRANSLATORS: Think of "Only layers without tags" when translating this
    'display_name': _('Without tags'),
    'arguments': [
      {
        'type': 'array',
        'name': 'tags',
        'display_name': _('Tags'),
        'element_type': 'string',
        'default_value': (),
      },
    ],
  },
]

# Create a separate dictionary for functions since objects cannot be saved
# to a persistent source. Saving them as strings would not be reliable as
# function names and paths may change when refactoring or adding/modifying features.
# The 'function' setting is set to an empty value as the function can be inferred
# via the action's 'orig_name' setting.
BUILTIN_CONSTRAINTS = collections.OrderedDict()
BUILTIN_CONSTRAINTS_FUNCTIONS = collections.OrderedDict()

for action_dict in _BUILTIN_CONSTRAINTS_LIST:
  function = action_dict['function']
  action_dict['function'] = ''
  
  BUILTIN_CONSTRAINTS[action_dict['name']] = action_dict
  BUILTIN_CONSTRAINTS_FUNCTIONS[action_dict['name']] = function
