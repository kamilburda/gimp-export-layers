# -*- coding: utf-8 -*-

"""Placeholder objects replaced with real GIMP objects when executing GIMP PDB
procedures during export.

The following placeholder objects are defined:

* `PLACEHOLDERS['current_image']` - Represents the image currently being
  processed.

* `PLACEHOLDERS['current_layer']` - Represents the layer currently being
  processed in the current image. This placeholder is currently also used for
  PDB procedures containing `gimp.Drawable` or `gimp.Item` parameters.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import gimpenums

from export_layers import pygimplib as pg

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


def _get_current_image(image, layer, layer_exporter):
  return image


def _get_current_layer(image, layer, layer_exporter):
  return layer


_PLACEHOLDERS = {
  'current_image': _GimpObjectPlaceholder(_('Current Image'), _get_current_image),
  'current_layer': _GimpObjectPlaceholder(_('Current Layer'), _get_current_layer),
}


def get_replaced_arg(arg, image, layer, layer_exporter):
  """
  If `arg` is a placeholder object, return a real object replacing the
  placeholder. Otherwise, return `arg`.
  
  Arguments after `args` are required arguments for operations and are used to
  determine the real object that replaces the placeholder.
  """
  if arg in _PLACEHOLDERS.keys():
    return _PLACEHOLDERS[arg].replace_args(image, layer, layer_exporter)
  else:
    return arg


def get_replaced_args_and_kwargs(func_args, func_kwargs, image, layer, layer_exporter):
  """
  Return arguments and keyword arguments for a function whose placeholder
  objects are replaced with real objects.
  
  Arguments after `func_kwargs` are required arguments for operations and are
  used to determine the real object that replaces the placeholder.
  """
  new_func_args = [
    get_replaced_arg(arg, image, layer, layer_exporter) for arg in func_args]
  
  new_func_kwargs = {
    name: get_replaced_arg(value, image, layer, layer_exporter)
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
  _ALLOWED_PLACEHOLDERS = ['current_layer']


class PlaceholderLayerSetting(PlaceholderSetting):
  
  _DEFAULT_DEFAULT_VALUE = 'current_layer'
  _ALLOWED_PLACEHOLDERS = ['current_layer']


class PlaceholderItemSetting(PlaceholderSetting):
  
  _DEFAULT_DEFAULT_VALUE = 'current_layer'
  _ALLOWED_PLACEHOLDERS = ['current_layer']


PDB_TYPES_TO_PLACEHOLDER_SETTING_TYPES_MAP = {
  gimpenums.PDB_IMAGE: PlaceholderImageSetting,
  gimpenums.PDB_ITEM: PlaceholderItemSetting,
  gimpenums.PDB_DRAWABLE: PlaceholderDrawableSetting,
  gimpenums.PDB_LAYER: PlaceholderLayerSetting,
}
