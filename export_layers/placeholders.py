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
This module defines placeholder GIMP objects that are replaced with real objects
during export. Specifically, the following placeholder objects are created:

* `PLACEHOLDERS["current_image"]` - represents the image currently being
  processed

* `PLACEHOLDERS["current_layer"]` - represents the layer currently being
  processed in the current image
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import gimpenums

from export_layers.pygimplib import pgsetting
from export_layers.pygimplib import pgsettingutils

from .gui import gui_placeholders


class _GimpObjectPlaceholder(object):
  
  def __init__(self, name, replacement_func):
    self._name = name
    self._replacement_func = replacement_func
  
  @property
  def name(self):
    return self._name
  
  def replace_args(self, *args):
    return self._replacement_func(*args)


def _get_current_image(image, layer, layer_exporter):
  return image


def _get_current_layer(image, layer, layer_exporter):
  return layer


PLACEHOLDERS = {
  "current_image": _GimpObjectPlaceholder(_("Current Image"), _get_current_image),
  "current_layer": _GimpObjectPlaceholder(_("Current Layer"), _get_current_layer),
}


def get_replaced_arg(arg, image, layer, layer_exporter):
  """
  If `arg` is a placeholder object, return a real object replacing the
  placeholder. Otherwise, return `arg`.
  
  Arguments after `args` are mandatory arguments for operations and are used to
  determine the real object that replaces the placeholder.
  """
  if arg in PLACEHOLDERS.values():
    return arg.replace_args(image, layer, layer_exporter)
  else:
    return arg


def get_replaced_args_and_kwargs(func_args, func_kwargs, image, layer, layer_exporter):
  """
  Return arguments and keyword arguments for a function whose placeholder
  objects are replaced with real objects.
  
  Arguments after `func_kwargs` are mandatory arguments for operations and are
  used to determine the real object that replaces the placeholder.
  """
  new_func_args = [
    get_replaced_arg(arg, image, layer, layer_exporter) for arg in func_args]
  
  new_func_kwargs = {
    name: get_replaced_arg(value, image, layer, layer_exporter)
    for name, value in func_kwargs.items()}
  
  return new_func_args, new_func_kwargs


#===============================================================================


class PlaceholderSetting(pgsetting.Setting):
   
  _ALLOWED_GUI_TYPES = [gui_placeholders.GimpObjectPlaceholdersComboBoxPresenter]
  _ALLOWED_PLACEHOLDERS = []
  
  @classmethod
  def get_allowed_placeholders(cls):
    """
    Return a list of allowed placeholder objects for this setting class.
    """
    return cls._ALLOWED_PLACEHOLDERS
  
  def _init_error_messages(self):
    self.error_messages["invalid_value"] = _("Invalid placeholder.")
  
  def _validate(self, value):
    if value not in self._ALLOWED_PLACEHOLDERS:
      raise pgsetting.SettingValueError(
        pgsettingutils.value_to_str_prefix(value) + self.error_messages["invalid_value"])


class PlaceholderImageSetting(PlaceholderSetting):
  
  _DEFAULT_DEFAULT_VALUE = PLACEHOLDERS["current_image"]
  _ALLOWED_PLACEHOLDERS = [PLACEHOLDERS["current_image"]]


class PlaceholderDrawableSetting(PlaceholderSetting):
  
  _DEFAULT_DEFAULT_VALUE = PLACEHOLDERS["current_layer"]
  _ALLOWED_PLACEHOLDERS = [PLACEHOLDERS["current_layer"]]


class PlaceholderLayerSetting(PlaceholderSetting):
  
  _DEFAULT_DEFAULT_VALUE = PLACEHOLDERS["current_layer"]
  _ALLOWED_PLACEHOLDERS = [PLACEHOLDERS["current_layer"]]


PDB_TYPES_TO_PLACEHOLDER_SETTING_TYPES_MAP = {
  gimpenums.PDB_IMAGE: PlaceholderImageSetting,
  gimpenums.PDB_DRAWABLE: PlaceholderDrawableSetting,
  gimpenums.PDB_LAYER: PlaceholderLayerSetting,
}
