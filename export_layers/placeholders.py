# -*- coding: utf-8 -*-

"""Placeholder objects replaced with real GIMP objects when calling GIMP PDB
procedures during batch processing.

The following placeholder objects are defined:

* `PLACEHOLDERS['current_image']` - The image currently being processed.

* `PLACEHOLDERS['current_layer']` - The layer currently being processed in the
  current image. This placeholder is used for PDB procedures containing
  `gimp.Layer`, `gimp.Drawable` or `gimp.Item` parameters.

* `PLACEHOLDERS['background_layer']` - The layer positioned immediately after
  the currently processed layer.

* `PLACEHOLDERS['foreground_layer']` - The layer positioned immediately before
  the currently processed layer.
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
  return _get_adjacent_layer(
    batcher,
    lambda position, num_layers: position < num_layers - 1,
    1,
    'insert_background_layers',
    _('There are no background layers.'))


def _get_foreground_layer(batcher):
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
      
      if tags and _has_tag(next_layer, tags):
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


def _has_tag(layer, tags):
  layer_tags = pg.itemtree.get_tags_from_raw_item(layer, pg.config.SOURCE_NAME)
  return any(tag in layer_tags for tag in tags)


_PLACEHOLDERS = collections.OrderedDict([
  ('current_image', _GimpObjectPlaceholder(_('Current Image'), _get_current_image)),
  ('current_layer', _GimpObjectPlaceholder(_('Current Layer'), _get_current_layer)),
  ('background_layer', _GimpObjectPlaceholder(_('Background Layer'), _get_background_layer)),
  ('foreground_layer', _GimpObjectPlaceholder(_('Foreground Layer'), _get_foreground_layer)),
])


def get_replaced_arg(arg, batcher):
  """If `arg` is a placeholder object, returns a real object replacing the
  placeholder. Otherwise, `arg` is returned.
  
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
  """Returns arguments and keyword arguments for a function whose placeholder
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
    """Returns a list of allowed names of placeholders for this setting class.
    """
    return list(cls._ALLOWED_PLACEHOLDERS)
  
  @classmethod
  def get_allowed_placeholders(cls):
    """Returns a list of allowed placeholder objects for this setting class.
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
