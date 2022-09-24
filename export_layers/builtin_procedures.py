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


NAME_ONLY_TAG = 'name'


def set_active_layer(image, layer, layer_exporter):
  image.active_layer = layer


def set_active_layer_after_action(image, layer, layer_exporter):
  action_applied = yield
  
  if action_applied or action_applied is None:
    set_active_layer(image, layer, layer_exporter)


def copy_and_insert_layer(
      image, layer, parent=None, position=0,
      remove_lock_attributes=True):
  layer_copy = pg.pdbutils.copy_and_paste_layer(
    layer, image, parent, position, remove_lock_attributes)
  
  pdb.gimp_item_set_visible(layer_copy, True)
  
  if pdb.gimp_item_is_group(layer_copy):
    layer_copy = pg.pdbutils.merge_layer_group(layer_copy)
  
  return layer_copy


def autocrop_tagged_layer(image, layer, layer_exporter, tag):
  tagged_layer = layer_exporter.inserted_tagged_layers[tag]
  if tagged_layer is not None:
    image.active_layer = tagged_layer
    pdb.plug_in_autocrop_layer(image, tagged_layer)
    return True
  else:
    return False


def remove_folder_hierarchy_from_layer(image, layer, layer_exporter):
  layer_elem = layer_exporter.current_layer_elem

  layer_elem.parents = []
  layer_elem.children = None if layer_elem.item_type == layer_elem.ITEM else []


def insert_background_layer(image, layer, layer_exporter, tag):
  _insert_tagged_layer(image, layer_exporter, tag, position=len(image.layers))


def insert_foreground_layer(image, layer, layer_exporter, tag):
  _insert_tagged_layer(image, layer_exporter, tag, position=0)


def inherit_transparency_from_layer_groups(image, layer, layer_exporter):
  new_layer_opacity = layer_exporter.current_layer_elem.item.opacity / 100.0
  for parent_elem in layer_exporter.current_layer_elem.parents:
    new_layer_opacity = new_layer_opacity * (parent_elem.item.opacity / 100.0)
  
  layer.opacity = new_layer_opacity * 100.0


def rename_layer(image, layer, layer_exporter, pattern):
  renamer = renamer_.LayerNameRenamer(layer_exporter, pattern)
  
  while True:
    renamer.rename(layer_exporter.current_layer_elem)
    unused_ = yield


def resize_to_layer_size(image, layer, layer_exporter):
  layer_offset_x, layer_offset_y = layer.offsets
  pdb.gimp_image_resize(
    image, layer.width, layer.height, -layer_offset_x, -layer_offset_y)


def _insert_tagged_layer(image, layer_exporter, tag, position=0):
  if not layer_exporter.tagged_layer_elems[tag]:
    return
  
  if layer_exporter.tagged_layer_copies[tag] is None:
    layer_exporter.inserted_tagged_layers[tag] = (
      _insert_merged_tagged_layer(image, layer_exporter, tag, position))
    
    layer_exporter.tagged_layer_copies[tag] = pdb.gimp_layer_copy(
      layer_exporter.inserted_tagged_layers[tag], True)
    _remove_locks_from_layer(layer_exporter.tagged_layer_copies[tag])
  else:
    layer_exporter.inserted_tagged_layers[tag] = pdb.gimp_layer_copy(
      layer_exporter.tagged_layer_copies[tag], True)
    _remove_locks_from_layer(layer_exporter.inserted_tagged_layers[tag])
    pdb.gimp_image_insert_layer(
      image, layer_exporter.inserted_tagged_layers[tag], None, position)


def _insert_merged_tagged_layer(image, layer_exporter, tag, position=0):
  first_tagged_layer_position = position
  
  for i, layer_elem in enumerate(layer_exporter.tagged_layer_elems[tag]):
    layer_copy = copy_and_insert_layer(
      image, layer_elem.item, None, first_tagged_layer_position + i)
    layer_copy.visible = True
    layer_exporter.invoker.invoke(
      ['after_insert_layer'], [image, layer_copy, layer_exporter])
  
  if len(layer_exporter.tagged_layer_elems[tag]) == 1:
    merged_layer_for_tag = image.layers[first_tagged_layer_position]
  else:
    second_to_last_tagged_layer_position = (
      first_tagged_layer_position + len(layer_exporter.tagged_layer_elems[tag]) - 2)
    
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


class FilenamePatternEntryPresenter(pg.setting.presenters_gtk.ExtendedEntryPresenter):
  """`pygimplib.setting.Presenter` subclass for
  `pygimplib.gui.FilenamePatternEntry` elements.
  
  Value: Text in the entry.
  """
  
  def _create_gui_element(self, setting):
    return pg.gui.FilenamePatternEntry(renamer_.get_field_descriptions(renamer_.FIELDS))


class FilenamePatternEntrySetting(pg.setting.StringSetting):
  
  _ALLOWED_GUI_TYPES = [FilenamePatternEntryPresenter]


_BUILTIN_PROCEDURES_LIST = [
  {
    'name': 'autocrop_background',
    'function': autocrop_tagged_layer,
    'arguments': [
      {
        'type': pg.SettingTypes.string,
        'name': 'tag',
        'default_value': 'background',
      },
    ],
    'display_name': _('Autocrop background'),
  },
  {
    'name': 'autocrop_foreground',
    'function': autocrop_tagged_layer,
    'arguments': [
      {
        'type': pg.SettingTypes.string,
        'name': 'tag',
        'default_value': 'foreground',
      },
    ],
    'display_name': _('Autocrop foreground'),
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
    'arguments': [
      {
        'type': pg.SettingTypes.string,
        'name': 'tag',
        'default_value': 'background',
      },
    ],
    'display_name': _('Insert background layers'),
  },
  {
    'name': 'insert_foreground_layers',
    'function': insert_foreground_layer,
    'arguments': [
      {
        'type': pg.SettingTypes.string,
        'name': 'tag',
        'default_value': 'foreground',
      },
    ],
    'display_name': _('Insert foreground layers'),
  },
  {
    'name': 'inherit_transparency_from_layer_groups',
    'function': inherit_transparency_from_layer_groups,
    'display_name': _('Inherit transparency from layer groups'),
  },
  {
    'name': 'rename_layer',
    'function': rename_layer,
    'arguments': [
      {
        'type': FilenamePatternEntrySetting,
        'name': 'pattern',
        'default_value': '[layer name]',
        'display_name': _('Layer filename pattern'),
        'gui_type': FilenamePatternEntryPresenter,
      },
    ],
    'display_name': _('Rename layer'),
    'additional_tags': [NAME_ONLY_TAG],
  },
  {
    'name': 'use_file_extensions_in_layer_names',
    'function': None,
    'display_name': _('Use file extensions in layer names'),
    'additional_tags': [NAME_ONLY_TAG],
  },
  {
    'name': 'use_layer_size',
    'function': resize_to_layer_size,
    'display_name': _('Use layer size'),
  },
]

BUILTIN_PROCEDURES = collections.OrderedDict(
  (action_dict['name'], action_dict) for action_dict in _BUILTIN_PROCEDURES_LIST)
