# -*- coding: utf-8 -*-
#
# This file is part of Export Layers.
#
# Copyright (C) 2013-2018 khalim19 <khalim19@gmail.com>
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
This module defines built-in constraints for the plug-in.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import collections

from export_layers.pygimplib import pgsetting


CONSTRAINTS_LAYER_TYPES_GROUP = "constraints_layer_types"


def is_layer(layer_elem):
  return layer_elem.item_type == layer_elem.ITEM


def is_nonempty_group(layer_elem):
  return layer_elem.item_type == layer_elem.NONEMPTY_GROUP


def is_empty_group(layer_elem):
  return layer_elem.item_type == layer_elem.EMPTY_GROUP


def is_top_level(layer_elem):
  return layer_elem.depth == 0


def is_path_visible(layer_elem):
  return layer_elem.path_visible


def has_matching_file_extension(layer_elem, file_extension):
  return layer_elem.get_file_extension() == file_extension.lower()


def has_matching_default_file_extension(layer_elem, layer_exporter):
  return layer_elem.get_file_extension() == layer_exporter.default_file_extension


def has_tags(layer_elem, tags=None):
  if tags:
    return any(tag for tag in tags if tag in layer_elem.tags)
  else:
    return bool(layer_elem.tags)


def has_no_tags(layer_elem, tags=None):
  return not has_tags(layer_elem, tags)


def is_layer_in_selected_layers(layer_elem, selected_layers):
  return layer_elem.item.ID in selected_layers


_BUILTIN_CONSTRAINTS_LIST = [
  {
    "name": "include_layers",
    "type": "constraint",
    "function": is_layer,
    "display_name": _("Include layers"),
    "subfilter": "layer_types",
    "operation_groups": [CONSTRAINTS_LAYER_TYPES_GROUP],
  },
  {
    "name": "include_layer_groups",
    "type": "constraint",
    "function": is_nonempty_group,
    "display_name": _("Include layer groups"),
    "subfilter": "layer_types",
    "operation_groups": [CONSTRAINTS_LAYER_TYPES_GROUP],
  },
  {
    "name": "include_empty_layer_groups",
    "type": "constraint",
    "function": is_empty_group,
    "display_name": _("Include empty layer groups"),
    "subfilter": "layer_types",
    "operation_groups": [CONSTRAINTS_LAYER_TYPES_GROUP],
  },
  {
    "name": "only_layers_without_tags",
    "type": "constraint",
    "function": has_no_tags,
    "arguments": [
      {
        "type": pgsetting.SettingTypes.array,
        "name": "tags",
        "element_type": pgsetting.SettingTypes.string,
        "default_value": (),
      },
    ],
    "display_name": _("Only layers without tags"),
  },
  {
    "name": "only_layers_with_tags",
    "type": "constraint",
    "function": has_tags,
    "arguments": [
      {
        "type": pgsetting.SettingTypes.array,
        "name": "tags",
        "element_type": pgsetting.SettingTypes.string,
        "default_value": (),
      },
    ],
    "display_name": _("Only layers with tags"),
  },
  {
    "name": "only_layers_matching_file_extension",
    "type": "constraint",
    "function": has_matching_default_file_extension,
    "display_name": _("Only layers matching file extension"),
  },
  {
    "name": "only_toplevel_layers",
    "type": "constraint",
    "function": is_top_level,
    "display_name": _("Only top-level layers"),
  },
  {
    "name": "only_selected_layers",
    "type": "constraint",
    "function": is_layer_in_selected_layers,
    "arguments": [
      {
        "type": pgsetting.SettingTypes.generic,
        "name": "selected_layers",
        "default_value": set(),
        "gui_type": None,
      },
    ],
    "display_name": _("Only layers selected in preview"),
  },
]

BUILTIN_CONSTRAINTS = collections.OrderedDict(
  (operation_dict["name"], operation_dict)
  for operation_dict in _BUILTIN_CONSTRAINTS_LIST)
