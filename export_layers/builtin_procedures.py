# -*- coding: utf-8 -*-

"""Built-in plug-in procedures."""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import collections

import gimp
from gimp import pdb
import gimpenums

from export_layers import pygimplib as pg

from export_layers import export as export_
from export_layers import renamer as renamer_
from export_layers import settings_custom


NAME_ONLY_TAG = 'name'


def set_active_and_current_layer(exporter):
  if pdb.gimp_item_is_valid(exporter.current_raw_item):
    exporter.current_image.active_layer = exporter.current_raw_item
  else:
    if pdb.gimp_item_is_valid(exporter.current_image.active_layer):
      # The active layer may have been set by the procedure.
      exporter.current_raw_item = exporter.current_image.active_layer
    else:
      if len(exporter.current_image.layers) > 0:
        # We cannot make a good guess of what layer is the "right" one, so we
        # resort to taking the first.
        first_layer = exporter.current_image.layers[0]
        exporter.current_raw_item = first_layer
        exporter.current_image.active_layer = first_layer
      else:
        # There is nothing we can do. Let an exception be raised. An empty image
        # could occur e.g. if a custom procedure removed all layers.
        pass


def set_active_and_current_layer_after_action(exporter):
  action_applied = yield
  
  if action_applied or action_applied is None:
    set_active_and_current_layer(exporter)


def remove_folder_hierarchy_from_item(exporter):
  item = exporter.current_item

  item.parents = []
  item.children = []


def inherit_transparency_from_layer_groups(exporter):
  new_layer_opacity = exporter.current_raw_item.opacity / 100.0
  for parent in exporter.current_item.parents:
    new_layer_opacity = new_layer_opacity * (parent.raw.opacity / 100.0)
  
  exporter.current_raw_item.opacity = new_layer_opacity * 100.0


def insert_background_layer(exporter, tag):
  return _insert_tagged_layer(exporter, tag, position=len(exporter.current_image.layers))


def insert_foreground_layer(exporter, tag):
  return _insert_tagged_layer(exporter, tag, position=0)


def _insert_tagged_layer(exporter, tag, position=0):
  tagged_items = [
    item for item in exporter.item_tree.iter(with_folders=False, filtered=False)
    if tag in item.tags]
  merged_tagged_layer = None
  orig_merged_tagged_layer = None
  
  def _cleanup_tagged_layers(exporter):
    if orig_merged_tagged_layer is not None and pdb.gimp_item_is_valid(orig_merged_tagged_layer):
      pdb.gimp_item_delete(orig_merged_tagged_layer)
    
    exporter.invoker.remove(cleanup_tagged_layers_action_id, ['after_process_items_contents'])
  
  # We use`Invoker.add` instead of `exporter.add_procedure` since the latter
  # would add the function only at the start of processing and we already are in
  # the middle of processing here.
  cleanup_tagged_layers_action_id = exporter.invoker.add(
    _cleanup_tagged_layers, ['after_process_items_contents'])
  
  while True:
    image = exporter.current_image
    
    if not tagged_items:
      yield
      continue
    
    if orig_merged_tagged_layer is None:
      merged_tagged_layer = _insert_merged_tagged_layer(
        image, exporter, tagged_items, tag, position)
      
      orig_merged_tagged_layer = pdb.gimp_layer_copy(merged_tagged_layer, True)
      _remove_locks_from_layer(orig_merged_tagged_layer)
    else:
      merged_tagged_layer = pdb.gimp_layer_copy(orig_merged_tagged_layer, True)
      _remove_locks_from_layer(merged_tagged_layer)
      pdb.gimp_image_insert_layer(image, merged_tagged_layer, None, position)
    
    yield


def _insert_merged_tagged_layer(image, exporter, tagged_items, tag, position=0):
  first_tagged_layer_position = position
  
  for i, item in enumerate(tagged_items):
    layer_copy = pg.pdbutils.copy_and_paste_layer(
      item.raw, image, None, first_tagged_layer_position + i, True, True)
    layer_copy.visible = True
    exporter.invoker.invoke(
      ['before_process_item_contents'], [exporter, exporter.current_item, layer_copy])
  
  if len(tagged_items) == 1:
    merged_tagged_layer = image.layers[first_tagged_layer_position]
  else:
    second_to_last_tagged_layer_position = first_tagged_layer_position + len(tagged_items) - 2
    
    for i in range(second_to_last_tagged_layer_position, first_tagged_layer_position - 1, -1):
      merged_tagged_layer = pdb.gimp_image_merge_down(
        image, image.layers[i], gimpenums.EXPAND_AS_NECESSARY)
  
  return merged_tagged_layer


def _remove_locks_from_layer(layer):
  pdb.gimp_item_set_lock_content(layer, False)
  if not isinstance(layer, gimp.GroupLayer):
    pdb.gimp_item_set_lock_position(layer, False)
    pdb.gimp_layer_set_lock_alpha(layer, False)


def rename_layer(exporter, pattern, rename_layers=True, rename_folders=False):
  renamer = renamer_.ItemRenamer(pattern)
  renamed_parents = set()
  
  while True:
    if rename_layers:
      exporter.current_item.name = renamer.rename(exporter)
    
    if rename_folders:
      for parent in exporter.current_item.parents:
        if parent not in renamed_parents:
          parent.name = renamer.rename(exporter, item=parent)
          renamed_parents.add(parent)
    
    yield


def resize_to_layer_size(exporter):
  image = exporter.current_image
  layer = exporter.current_raw_item
  
  layer_offset_x, layer_offset_y = layer.offsets
  pdb.gimp_image_resize(image, layer.width, layer.height, -layer_offset_x, -layer_offset_y)


_BUILTIN_PROCEDURES_LIST = [
  {
    'name': 'export',
    'function': export_.export,
    'display_name': _('Export'),
    'additional_tags': [NAME_ONLY_TAG],
    'arguments': [
      {
        'type': pg.SettingTypes.file_extension,
        'name': 'file_extension',
        'default_value': 'png',
        'display_name': _('File extension'),
        'gui_type': pg.SettingGuiTypes.file_extension_entry,
        'adjust_value': True,
      },
      {
        'type': pg.SettingTypes.enumerated,
        'name': 'export_mode',
        'default_value': 'each_layer',
        'items': [
          ('each_layer', _('For each layer'), export_.ExportModes.EACH_LAYER),
          ('each_top_level_layer_or_group',
           _('For each top-level layer or group'),
           export_.ExportModes.EACH_TOP_LEVEL_LAYER_OR_GROUP),
          ('entire_image_at_once',
           _('For the entire image at once'),
           export_.ExportModes.ENTIRE_IMAGE_AT_ONCE),
        ],
        'display_name': _('Perform export:'),
      },
      {
        'type': settings_custom.FilenamePatternSetting,
        'name': 'single_image_filename_pattern',
        'default_value': '[image name]',
        'display_name': _('Image filename pattern'),
        'gui_type': settings_custom.FilenamePatternEntryPresenter,
      },
      {
        'type': pg.SettingTypes.boolean,
        'name': 'use_file_extension_in_item_name',
        'default_value': False,
        'display_name': _('Use file extension in layer name'),
        'gui_type': pg.SettingGuiTypes.check_button_no_text,
      },
      {
        'type': pg.SettingTypes.boolean,
        'name': 'convert_file_extension_to_lowercase',
        'default_value': False,
        'display_name': _('Convert file extension to lowercase'),
        'gui_type': pg.SettingGuiTypes.check_button_no_text,
      },
      {
        'type': pg.SettingTypes.boolean,
        'name': 'preserve_layer_name_after_export',
        'default_value': False,
        'display_name': _('Preserve layer name after export'),
        'gui_type': pg.SettingGuiTypes.check_button_no_text,
      },
    ],
  },
  {
    'name': 'ignore_folder_structure',
    'function': remove_folder_hierarchy_from_item,
    'display_name': _('Ignore folder structure'),
    'additional_tags': [NAME_ONLY_TAG],
  },
  {
    'name': 'inherit_transparency_from_layer_groups',
    'function': inherit_transparency_from_layer_groups,
    'display_name': _('Inherit transparency from layer groups'),
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
    'name': 'rename',
    'function': rename_layer,
    'display_name': _('Rename'),
    'additional_tags': [NAME_ONLY_TAG],
    'arguments': [
      {
        'type': settings_custom.FilenamePatternSetting,
        'name': 'pattern',
        'default_value': '[layer name]',
        'display_name': _('Layer filename pattern'),
        'gui_type': settings_custom.FilenamePatternEntryPresenter,
      },
      {
        'type': pg.SettingTypes.boolean,
        'name': 'rename_layers',
        'default_value': True,
        'display_name': _('Rename layers'),
        'gui_type': pg.SettingGuiTypes.check_button_no_text,
      },
      {
        'type': pg.SettingTypes.boolean,
        'name': 'rename_folders',
        'default_value': False,
        'display_name': _('Rename folders'),
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
