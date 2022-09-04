# -*- coding: utf-8 -*-
#
# This file is part of Export Layers.
#
# Copyright (C) 2013-2019 khalim19 <khalim19@gmail.com>
#
# Export Layers is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Export Layers is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Export Layers.  If not, see <https://www.gnu.org/licenses/>.

"""
This module defines built-in procedures for the plug-in.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import collections

from gimp import pdb
import gimpenums

from export_layers import pygimplib as pg


def set_active_layer(image, layer, layer_exporter):
  image.active_layer = layer


def set_active_layer_after_operation(image, layer, layer_exporter):
  operation_executed = yield
  
  if operation_executed or operation_executed is None:
    set_active_layer(image, layer, layer_exporter)


def resize_to_layer_size(image, layer, layer_exporter):
  layer_offset_x, layer_offset_y = layer.offsets
  pdb.gimp_image_resize(
    image, layer.width, layer.height, -layer_offset_x, -layer_offset_y)


def insert_background_layer(image, layer, layer_exporter, tag):
  _insert_tagged_layer(image, layer_exporter, tag, position=len(image.layers))


def insert_foreground_layer(image, layer, layer_exporter, tag):
  _insert_tagged_layer(image, layer_exporter, tag, position=0)


def copy_and_insert_layer(image, layer, parent=None, position=0):
  layer_copy = pdb.gimp_layer_new_from_drawable(layer, image)
  pdb.gimp_image_insert_layer(image, layer_copy, parent, position)
  pdb.gimp_item_set_visible(layer_copy, True)
  
  if pdb.gimp_item_is_group(layer_copy):
    layer_copy = pg.pdbutils.merge_layer_group(layer_copy)
  
  return layer_copy


def inherit_transparency_from_layer_groups(image, layer, layer_exporter):
  new_layer_opacity = layer_exporter.current_layer_elem.item.opacity / 100.0
  for parent_elem in layer_exporter.current_layer_elem.parents:
    new_layer_opacity = new_layer_opacity * (parent_elem.item.opacity / 100.0)
  
  layer.opacity = new_layer_opacity * 100.0


def autocrop_tagged_layer(image, layer, layer_exporter, tag):
  tagged_layer = layer_exporter.inserted_tagged_layers[tag]
  if tagged_layer is not None:
    image.active_layer = tagged_layer
    pdb.plug_in_autocrop_layer(image, tagged_layer)
    return True
  else:
    return False


def _insert_tagged_layer(image, layer_exporter, tag, position=0):
  if not layer_exporter.tagged_layer_elems[tag]:
    return
  
  if layer_exporter.tagged_layer_copies[tag] is None:
    layer_exporter.inserted_tagged_layers[tag] = (
      _insert_merged_tagged_layer(image, layer_exporter, tag, position))
    
    layer_exporter.tagged_layer_copies[tag] = (
      pdb.gimp_layer_copy(layer_exporter.inserted_tagged_layers[tag], True))
  else:
    layer_exporter.inserted_tagged_layers[tag] = (
      pdb.gimp_layer_copy(layer_exporter.tagged_layer_copies[tag], True))
    pdb.gimp_image_insert_layer(
      image, layer_exporter.inserted_tagged_layers[tag], None, position)


def _insert_merged_tagged_layer(image, layer_exporter, tag, position=0):
  first_tagged_layer_position = position
  
  for i, layer_elem in enumerate(layer_exporter.tagged_layer_elems[tag]):
    layer_copy = copy_and_insert_layer(
      image, layer_elem.item, None, first_tagged_layer_position + i)
    layer_copy.visible = True
    layer_exporter.executor.execute(
      ["after_insert_layer"], [image, layer_copy, layer_exporter])
  
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


_BUILTIN_PROCEDURES_LIST = [
  {
    "name": "insert_background_layers",
    "function": insert_background_layer,
    "arguments": [
      {
        "type": pg.SettingTypes.string,
        "name": "tag",
        "default_value": "background",
      },
    ],
    "display_name": _("Insert background layers"),
  },
  {
    "name": "insert_foreground_layers",
    "function": insert_foreground_layer,
    "arguments": [
      {
        "type": pg.SettingTypes.string,
        "name": "tag",
        "default_value": "foreground",
      },
    ],
    "display_name": _("Insert foreground layers"),
  },
  {
    "name": "inherit_transparency_from_layer_groups",
    "function": inherit_transparency_from_layer_groups,
    "display_name": _("Inherit transparency from layer groups"),
  },
  {
    "name": "autocrop_background",
    "function": autocrop_tagged_layer,
    "arguments": [
      {
        "type": pg.SettingTypes.string,
        "name": "tag",
        "default_value": "background",
      },
    ],
    "display_name": _("Autocrop background"),
  },
  {
    "name": "autocrop_foreground",
    "function": autocrop_tagged_layer,
    "arguments": [
      {
        "type": pg.SettingTypes.string,
        "name": "tag",
        "default_value": "foreground",
      },
    ],
    "display_name": _("Autocrop foreground"),
  },
  {
    "name": "ignore_folder_structure",
    "function": None,
    "display_name": _("Ignore folder structure"),
  },
  {
    "name": "use_file_extensions_in_layer_names",
    "function": None,
    "display_name": _("Use file extensions in layer names"),
  },
  {
    "name": "use_layer_size",
    "function": resize_to_layer_size,
    "display_name": _("Use layer size"),
  },
]

BUILTIN_PROCEDURES = collections.OrderedDict(
  (operation_dict["name"], operation_dict) for operation_dict in _BUILTIN_PROCEDURES_LIST)
