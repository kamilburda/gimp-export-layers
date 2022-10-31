# -*- coding: utf-8 -*-

"""Built-in plug-in procedures."""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import collections

import gimp
from gimp import pdb
import gimpenums

from export_layers import pygimplib as pg

from export_layers import renamer as renamer_
from export_layers import settings_custom


NAME_ONLY_TAG = 'name'


def set_active_layer(image, layer, exporter):
  image.active_layer = layer


def set_active_layer_after_action(image, layer, exporter):
  action_applied = yield
  
  if action_applied or action_applied is None:
    set_active_layer(image, layer, exporter)


def copy_and_insert_layer(image, layer, parent=None, position=0, remove_lock_attributes=True):
  layer_copy = pg.pdbutils.copy_and_paste_layer(
    layer, image, parent, position, remove_lock_attributes)
  
  pdb.gimp_item_set_visible(layer_copy, True)
  
  if pdb.gimp_item_is_group(layer_copy):
    layer_copy = pg.pdbutils.merge_layer_group(layer_copy)
  
  return layer_copy


def autocrop_tagged_layer(image, layer, exporter, tag):
  tagged_layer = exporter.inserted_tagged_layers[tag]
  if tagged_layer is not None:
    image.active_layer = tagged_layer
    pdb.plug_in_autocrop_layer(image, tagged_layer)
    return True
  else:
    return False


def remove_folder_hierarchy_from_layer(image, layer, exporter):
  layer_elem = exporter.current_layer_elem

  layer_elem.parents = []
  layer_elem.children = None if layer_elem.item_type == layer_elem.ITEM else []


def insert_background_layer(image, layer, exporter, tag):
  _insert_tagged_layer(image, exporter, tag, position=len(image.layers))


def insert_foreground_layer(image, layer, exporter, tag):
  _insert_tagged_layer(image, exporter, tag, position=0)


def inherit_transparency_from_layer_groups(image, layer, exporter):
  new_layer_opacity = exporter.current_layer_elem.item.opacity / 100.0
  for parent_elem in exporter.current_layer_elem.parents:
    new_layer_opacity = new_layer_opacity * (parent_elem.item.opacity / 100.0)
  
  layer.opacity = new_layer_opacity * 100.0


def rename_layer(image, layer, exporter, pattern):
  renamer = renamer_.LayerNameRenamer(exporter, pattern)
  
  while True:
    exporter.current_layer_elem.name = renamer.rename(exporter.current_layer_elem)
    unused_ = yield


def resize_to_layer_size(image, layer, exporter):
  layer_offset_x, layer_offset_y = layer.offsets
  pdb.gimp_image_resize(image, layer.width, layer.height, -layer_offset_x, -layer_offset_y)


def use_file_extension_in_layer_name(
      image, layer, exporter, convert_file_extension_to_lowercase=False):
  layer_elem = exporter.current_layer_elem
  
  orig_file_extension = layer_elem.get_file_extension_from_orig_name()
  if (orig_file_extension
      and orig_file_extension.lower() != layer_elem.get_file_extension().lower()
      and exporter.file_extension_properties[orig_file_extension].is_valid):
    if convert_file_extension_to_lowercase:
      orig_file_extension = orig_file_extension.lower()
    
    exporter.current_file_extension = orig_file_extension


def _insert_tagged_layer(image, exporter, tag, position=0):
  if not exporter.tagged_layer_elems[tag]:
    return
  
  if exporter.tagged_layer_copies[tag] is None:
    exporter.inserted_tagged_layers[tag] = _insert_merged_tagged_layer(
      image, exporter, tag, position)
    
    exporter.tagged_layer_copies[tag] = pdb.gimp_layer_copy(
      exporter.inserted_tagged_layers[tag], True)
    _remove_locks_from_layer(exporter.tagged_layer_copies[tag])
  else:
    exporter.inserted_tagged_layers[tag] = pdb.gimp_layer_copy(
      exporter.tagged_layer_copies[tag], True)
    _remove_locks_from_layer(exporter.inserted_tagged_layers[tag])
    pdb.gimp_image_insert_layer(image, exporter.inserted_tagged_layers[tag], None, position)


def _insert_merged_tagged_layer(image, exporter, tag, position=0):
  first_tagged_layer_position = position
  
  for i, layer_elem in enumerate(exporter.tagged_layer_elems[tag]):
    layer_copy = copy_and_insert_layer(
      image, layer_elem.item, None, first_tagged_layer_position + i)
    layer_copy.visible = True
    exporter.invoker.invoke(['after_insert_layer'], [image, layer_copy, exporter])
  
  if len(exporter.tagged_layer_elems[tag]) == 1:
    merged_layer_for_tag = image.layers[first_tagged_layer_position]
  else:
    second_to_last_tagged_layer_position = (
      first_tagged_layer_position + len(exporter.tagged_layer_elems[tag]) - 2)
    
    for i in range(
          second_to_last_tagged_layer_position,
          first_tagged_layer_position - 1,
          -1):
      merged_layer_for_tag = pdb.gimp_image_merge_down(
        image, image.layers[i], gimpenums.EXPAND_AS_NECESSARY)
  
  return merged_layer_for_tag


def _remove_locks_from_layer(layer):
  pdb.gimp_item_set_lock_content(layer, False)
  if not isinstance(layer, gimp.GroupLayer):
    pdb.gimp_item_set_lock_position(layer, False)
    pdb.gimp_layer_set_lock_alpha(layer, False)


_BUILTIN_PROCEDURES_LIST = [
  {
    'name': 'autocrop_background',
    'function': autocrop_tagged_layer,
    'display_name': _('Autocrop background'),
    'arguments': [
      {
        'type': pg.SettingTypes.string,
        'name': 'tag',
        'default_value': 'background',
      },
    ],
  },
  {
    'name': 'autocrop_foreground',
    'function': autocrop_tagged_layer,
    'display_name': _('Autocrop foreground'),
    'arguments': [
      {
        'type': pg.SettingTypes.string,
        'name': 'tag',
        'default_value': 'foreground',
      },
    ],
  },
  {
    'name': 'ignore_folder_structure',
    'function': remove_folder_hierarchy_from_layer,
    'display_name': _('Ignore folder structure'),
    'additional_tags': [NAME_ONLY_TAG],
  },
  {
    'name': 'insert_background_layers',
    'function': insert_background_layer,
    'display_name': _('Insert background layers'),
    'arguments': [
      {
        'type': pg.SettingTypes.string,
        'name': 'tag',
        'default_value': 'background',
      },
    ],
  },
  {
    'name': 'insert_foreground_layers',
    'function': insert_foreground_layer,
    'display_name': _('Insert foreground layers'),
    'arguments': [
      {
        'type': pg.SettingTypes.string,
        'name': 'tag',
        'default_value': 'foreground',
      },
    ],
  },
  {
    'name': 'inherit_transparency_from_layer_groups',
    'function': inherit_transparency_from_layer_groups,
    'display_name': _('Inherit transparency from layer groups'),
  },
  {
    'name': 'rename_layer',
    'function': rename_layer,
    'display_name': _('Rename layer'),
    'additional_tags': [NAME_ONLY_TAG],
    'arguments': [
      {
        'type': settings_custom.FilenamePatternSetting,
        'name': 'pattern',
        'default_value': '[layer name]',
        'display_name': _('Layer filename pattern'),
        'gui_type': settings_custom.FilenamePatternEntryPresenter,
      },
    ],
  },
  {
    'name': 'use_file_extension_in_layer_name',
    'function': use_file_extension_in_layer_name,
    'display_name': _('Use file extension in layer name'),
    'additional_tags': [NAME_ONLY_TAG],
    'arguments': [
      {
        'type': pg.SettingTypes.boolean,
        'name': 'convert_file_extension_to_lowercase',
        'default_value': False,
        'display_name': _('Convert file extension to lowercase'),
        'gui_type': pg.SettingGuiTypes.check_button_no_text,
      },
    ],
  },
  {
    'name': 'use_layer_size',
    'function': resize_to_layer_size,
    'display_name': _('Use layer size'),
  },
]

BUILTIN_PROCEDURES = collections.OrderedDict(
  (action_dict['name'], action_dict) for action_dict in _BUILTIN_PROCEDURES_LIST)
