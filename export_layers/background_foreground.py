# -*- coding: utf-8 -*-

"""Background and foreground layer insertion and manipulation."""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import gimp
from gimp import pdb
import gimpenums

from export_layers import exceptions

from export_layers import pygimplib as pg


def insert_background_layer(batcher, tag):
  return _insert_tagged_layer(batcher, tag, 'after')


def insert_foreground_layer(batcher, tag):
  return _insert_tagged_layer(batcher, tag, 'before')


def _insert_tagged_layer(batcher, tag, insert_mode):
  tagged_items = [
    item for item in batcher.item_tree.iter(with_folders=True, filtered=False)
    if tag in item.tags]
  merged_tagged_layer = None
  orig_merged_tagged_layer = None
  
  def _cleanup_tagged_layers(batcher):
    if orig_merged_tagged_layer is not None and pdb.gimp_item_is_valid(orig_merged_tagged_layer):
      pdb.gimp_item_delete(orig_merged_tagged_layer)
    
    batcher.invoker.remove(cleanup_tagged_layers_action_id, ['cleanup_contents'])
  
  # We use`Invoker.add` instead of `batcher.add_procedure` since the latter
  # would add the function only at the start of processing and we already are in
  # the middle of processing here.
  cleanup_tagged_layers_action_id = batcher.invoker.add(
    _cleanup_tagged_layers, ['cleanup_contents'])
  
  while True:
    image = batcher.current_image
    current_parent = batcher.current_raw_item.parent
    
    position = pdb.gimp_image_get_item_position(image, batcher.current_raw_item)
    if insert_mode == 'after':
      position += 1
    
    if not tagged_items:
      yield
      continue
    
    if orig_merged_tagged_layer is None:
      merged_tagged_layer = _insert_merged_tagged_layer(
        batcher, image, tagged_items, tag, current_parent, position)
      
      orig_merged_tagged_layer = pdb.gimp_layer_copy(merged_tagged_layer, True)
      _remove_locks_from_layer(orig_merged_tagged_layer)
    else:
      merged_tagged_layer = pdb.gimp_layer_copy(orig_merged_tagged_layer, True)
      _remove_locks_from_layer(merged_tagged_layer)
      pdb.gimp_image_insert_layer(image, merged_tagged_layer, current_parent, position)
    
    yield


def _insert_merged_tagged_layer(batcher, image, tagged_items, tag, parent, position):
  first_tagged_layer_position = position
  
  for i, item in enumerate(tagged_items):
    layer_copy = pg.pdbutils.copy_and_paste_layer(
      item.raw, image, parent, first_tagged_layer_position + i, True, True, True)
    layer_copy.visible = True
    
    batcher.invoker.invoke(
      ['before_process_item_contents'], [batcher, batcher.current_item, layer_copy])

  if parent is None:
    children = image.layers
  else:
    children = parent.children
  
  if len(tagged_items) == 1:
    merged_tagged_layer = children[first_tagged_layer_position]
  else:
    second_to_last_tagged_layer_position = first_tagged_layer_position + len(tagged_items) - 2
    
    for i in range(second_to_last_tagged_layer_position, first_tagged_layer_position - 1, -1):
      merged_tagged_layer = pdb.gimp_image_merge_down(
        image, children[i], gimpenums.EXPAND_AS_NECESSARY)
  
  return merged_tagged_layer


def _remove_locks_from_layer(layer):
  pdb.gimp_item_set_lock_content(layer, False)
  if not isinstance(layer, gimp.GroupLayer):
    if gimp.version >= (2, 10):
      pdb.gimp_item_set_lock_position(layer, False)
    pdb.gimp_layer_set_lock_alpha(layer, False)


def merge_background(batcher, merge_type=gimpenums.EXPAND_AS_NECESSARY):
  _merge_tagged_layer(
    batcher,
    merge_type,
    get_background_layer,
    'current_item')


def merge_foreground(batcher, merge_type=gimpenums.EXPAND_AS_NECESSARY):
  _merge_tagged_layer(
    batcher,
    merge_type,
    get_foreground_layer,
    'tagged_layer')


def _merge_tagged_layer(batcher, merge_type, get_tagged_layer_func, layer_to_merge_down_str):
  tagged_layer = get_tagged_layer_func(batcher)
  
  if tagged_layer is not None:
    name = batcher.current_raw_item.name
    visible = pdb.gimp_item_get_visible(batcher.current_raw_item)
    orig_tags = _get_tags(batcher.current_raw_item)
    
    if layer_to_merge_down_str == 'current_item':
      layer_to_merge_down = batcher.current_raw_item
    elif layer_to_merge_down_str == 'tagged_layer':
      layer_to_merge_down = tagged_layer
    else:
      raise ValueError('invalid value for "layer_to_merge_down_str"')
    
    pdb.gimp_item_set_visible(batcher.current_raw_item, True)
    
    merged_layer = pdb.gimp_image_merge_down(
      batcher.current_image, layer_to_merge_down, merge_type)
    merged_layer.name = name
    
    batcher.current_raw_item = merged_layer
    
    pdb.gimp_item_set_visible(batcher.current_raw_item, visible)
    _set_tags(batcher.current_raw_item, orig_tags)
    # We do not expect layer groups as folders to be merged since the plug-in
    # manipulates regular layers only (a layer group is merged into a single
    # layer during processing). Therefore, folder tags are ignored.
    _set_tags(batcher.current_raw_item, set(), pg.itemtree.TYPE_FOLDER)


def get_background_layer(batcher):
  return _get_adjacent_layer(
    batcher,
    lambda position, num_layers: position < num_layers - 1,
    1,
    'insert_background_layers',
    _('There are no background layers.'))


def get_foreground_layer(batcher):
  return _get_adjacent_layer(
    batcher,
    lambda position, num_layers: position > 0,
    -1,
    'insert_foreground_layers',
    _('There are no foreground layers.'))


def _get_adjacent_layer(
      batcher, position_cond_func, adjacent_position_increment,
      insert_tagged_layers_procedure_name, skip_message):
  raw_item = batcher.current_raw_item
  if raw_item.parent is None:
    children = batcher.current_image.layers
  else:
    children = raw_item.parent.children
  
  adjacent_layer = None
  
  num_layers = len(children)
  
  if num_layers > 1:
    position = pdb.gimp_image_get_item_position(batcher.current_image, batcher.current_raw_item)
    if position_cond_func(position, num_layers):
      next_layer = children[position + adjacent_position_increment]
      tags = [
        procedure['arguments/tag'].value
        for procedure in _get_previous_enabled_procedures(
          batcher, batcher.current_procedure, insert_tagged_layers_procedure_name)]
      
      if _has_tag(next_layer, tags, None) or _has_tag(next_layer, tags, pg.itemtree.TYPE_FOLDER):
        adjacent_layer = next_layer
  
  if adjacent_layer is not None:
    # This is necessary for some procedures relying on the active layer, e.g.
    # `plug-in-autocrop-layer`.
    batcher.current_image.active_layer = adjacent_layer
    return adjacent_layer
  else:
    raise exceptions.SkipAction(skip_message)


def _get_previous_enabled_procedures(batcher, current_action, action_orig_name_to_match):
  # HACK: This avoids a circular import. To resolve this, one possible way is to
  # refactor `actions` to turn actions into classes.
  from export_layers import actions
  
  previous_enabled_procedures = []
  
  for procedure in actions.walk(batcher.procedures):
    if procedure == current_action:
      return previous_enabled_procedures
    
    if procedure['enabled'].value and procedure['orig_name'].value == action_orig_name_to_match:
      previous_enabled_procedures.append(procedure)
  
  return previous_enabled_procedures


def _has_tag(layer, tags, item_type=None):
  return any(tag in _get_tags(layer, item_type) for tag in tags)


def _get_tags(layer, item_type=None):
  return pg.itemtree.get_tags_from_raw_item(layer, pg.config.SOURCE_NAME, item_type)


def _set_tags(layer, tags, item_type=None):
  return pg.itemtree.set_tags_for_raw_item(layer, tags, pg.config.SOURCE_NAME, item_type)
