# -*- coding: utf-8 -*-

"""Placeholder objects replaced with real GIMP objects when calling GIMP PDB
procedures during batch processing.

The following placeholder objects are defined:

* `PLACEHOLDERS['current_image']` - Represents the image currently being
  processed.

* `PLACEHOLDERS['current_layer']` - Represents the layer currently being
  processed in the current image. This placeholder is currently also used for
  PDB procedures containing `gimp.Drawable` or `gimp.Item` parameters.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import collections

from gimp import pdb
import gimpenums

from export_layers import pygimplib as pg

from export_layers import exceptions
from export_layers.gui import placeholders as gui_placeholders


class _GimpObjectPlaceholder(object):
  
  def __init__(self, display_name, replacement_func):
    self._display_name = display_name
    self._replacement_func = replacement_func
  
  @property
  def display_name(self):
    return self._display_name
  
  def replace_args(self, *args):
    return self._replacement_func(*args)


def _get_current_image(batcher):
  return batcher.current_image


def _get_current_layer(batcher):
  return batcher.current_raw_item


def _get_background_layer(batcher):
  num_layers = len(batcher.current_image.layers)
  
  if num_layers > 1:
    position = pdb.gimp_image_get_item_position(
      batcher.current_image, batcher.current_raw_item)
    if position == 0 or position < num_layers - 1:
      background_layer = batcher.current_image.layers[position + 1]
      # This is necessary for some procedures relying on the active layer, e.g.
      # `plug-in-autocrop-layer`.
      batcher.current_image.active_layer = background_layer
      return background_layer
  
  raise exceptions.InvalidPlaceholderError('there are no background layers')


def _get_foreground_layer(batcher):
  if len(batcher.current_image.layers) > 1:
    position = pdb.gimp_image_get_item_position(
      batcher.current_image, batcher.current_raw_item)
    if position > 0:
      foreground_layer = batcher.current_image.layers[position - 1]
      # This is necessary for some procedures relying on the active layer, e.g.
      # `plug-in-autocrop-layer`.
      batcher.current_image.active_layer = foreground_layer
      return foreground_layer
  
  raise exceptions.InvalidPlaceholderError('there are no foreground layers')


_PLACEHOLDERS = collections.OrderedDict([
  ('current_image', _GimpObjectPlaceholder(_('Current Image'), _get_current_image)),
  ('current_layer', _GimpObjectPlaceholder(_('Current Layer'), _get_current_layer)),
  ('background_layer', _GimpObjectPlaceholder(_('Background'), _get_background_layer)),
  ('foreground_layer', _GimpObjectPlaceholder(_('Foreground'), _get_foreground_layer)),
])


def get_replaced_arg(arg, batcher):
  """
  If `arg` is a placeholder object, return a real object replacing the
  placeholder. Otherwise, return `arg`.
  
  Arguments after `args` are required arguments for actions and are used to
  determine the real object that replaces the placeholder.
  """
  try:
    placeholder = _PLACEHOLDERS[arg]
  except (KeyError, TypeError):
    return arg
  else:
    return placeholder.replace_args(batcher)


def get_replaced_args_and_kwargs(func_args, func_kwargs, batcher):
  """
  Return arguments and keyword arguments for a function whose placeholder
  objects are replaced with real objects.
  
  Arguments after `func_kwargs` are required arguments for actions and are
  used to determine the real object that replaces the placeholder.
  """
  new_func_args = tuple(get_replaced_arg(arg, batcher) for arg in func_args)
  
  new_func_kwargs = {
    name: get_replaced_arg(value, batcher)
    for name, value in func_kwargs.items()}
  
  return new_func_args, new_func_kwargs


#===============================================================================


class PlaceholderSetting(pg.setting.Setting):
   
  _ALLOWED_GUI_TYPES = [gui_placeholders.GimpObjectPlaceholdersComboBoxPresenter]
  _ALLOWED_PLACEHOLDERS = []
  
  @classmethod
  def get_allowed_placeholder_names(cls):
    """
    Return a list of allowed names of placeholders for this setting class.
    """
    return list(cls._ALLOWED_PLACEHOLDERS)
  
  @classmethod
  def get_allowed_placeholders(cls):
    """
    Return a list of allowed placeholder objects for this setting class.
    """
    return [
      placeholder for placeholder_name, placeholder in _PLACEHOLDERS.items()
      if placeholder_name in cls._ALLOWED_PLACEHOLDERS]
  
  def _init_error_messages(self):
    self.error_messages['invalid_value'] = _('Invalid placeholder.')
  
  def _validate(self, value):
    if value not in self._ALLOWED_PLACEHOLDERS:
      raise pg.setting.SettingValueError(
        pg.setting.value_to_str_prefix(value) + self.error_messages['invalid_value'])


class PlaceholderImageSetting(PlaceholderSetting):
  
  _DEFAULT_DEFAULT_VALUE = 'current_image'
  _ALLOWED_PLACEHOLDERS = ['current_image']


class PlaceholderDrawableSetting(PlaceholderSetting):
  
  _DEFAULT_DEFAULT_VALUE = 'current_layer'
  _ALLOWED_PLACEHOLDERS = ['current_layer', 'background_layer', 'foreground_layer']


class PlaceholderLayerSetting(PlaceholderSetting):
  
  _DEFAULT_DEFAULT_VALUE = 'current_layer'
  _ALLOWED_PLACEHOLDERS = ['current_layer', 'background_layer', 'foreground_layer']


class PlaceholderItemSetting(PlaceholderSetting):
  
  _DEFAULT_DEFAULT_VALUE = 'current_layer'
  _ALLOWED_PLACEHOLDERS = ['current_layer', 'background_layer', 'foreground_layer']


PDB_TYPES_TO_PLACEHOLDER_SETTING_TYPES_MAP = {
  gimpenums.PDB_IMAGE: PlaceholderImageSetting,
  gimpenums.PDB_ITEM: PlaceholderItemSetting,
  gimpenums.PDB_DRAWABLE: PlaceholderDrawableSetting,
  gimpenums.PDB_LAYER: PlaceholderLayerSetting,
}
