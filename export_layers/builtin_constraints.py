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

#===============================================================================


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


def has_tags(layer_elem, *tags):
  if tags:
    return any(tag for tag in tags if tag in layer_elem.tags)
  else:
    return bool(layer_elem.tags)


def has_no_tags(layer_elem, *tags):
  return not has_tags(layer_elem, *tags)


def is_layer_in_selected_layers(layer_elem, selected_layers):
  return layer_elem.item.ID in selected_layers
