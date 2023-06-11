# -*- coding: utf-8 -*-

"""Plug-in settings."""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import collections
import os

import gimp
import gimpenums

from export_layers import pygimplib as pg

from export_layers import actions
from export_layers import builtin_constraints
from export_layers import builtin_procedures
from export_layers import export as export_
# Despite being unused, `settings_custom` must be imported so that the custom
# setting and GUI classes defined there are properly registered (via metaclasses
# in `pg.setting.meta`).
from export_layers import settings_custom  # @UnusedImport
from export_layers.gui import settings_gui


def create_settings():
  settings = pg.setting.create_groups({
    'name': 'all_settings',
    'groups': [
      {
        # These settings require special handling in the code, hence their separation
        # from the other settings.
        'name': 'special',
        'tags': ['ignore_reset', 'ignore_load', 'ignore_save'],
        'setting_attributes': {'gui_type': None},
      },
      {
        'name': 'main',
        'setting_attributes': {'setting_sources': ['session', 'persistent']},
      }
    ]
  })
  
  settings['special'].add([
    {
      'type': 'options',
      'name': 'run_mode',
      'default_value': 'non_interactive',
      'items': [
        ('interactive', 'RUN-INTERACTIVE', gimpenums.RUN_INTERACTIVE),
        ('non_interactive', 'RUN-NONINTERACTIVE', gimpenums.RUN_NONINTERACTIVE),
        ('run_with_last_vals', 'RUN-WITH-LAST-VALS', gimpenums.RUN_WITH_LAST_VALS)],
      'display_name': _('The run mode'),
    },
    {
      'type': 'image',
      'name': 'image',
      'default_value': None,
      'display_name': _('Image'),
    },
    {
      'type': 'boolean',
      'name': 'first_plugin_run',
      'default_value': True,
      'pdb_type': None,
      'setting_sources': ['session'],
    },
  ])
  
  settings['main'].add([
    {
      'type': 'file_extension',
      'name': 'file_extension',
      'default_value': 'png',
      'display_name': _('File extension'),
      'adjust_value': True,
    },
    {
      'type': 'string',
      'name': 'output_directory',
      'default_value': gimp.user_directory(1),  # `Documents` directory
      'display_name': _('Output directory'),
      'gui_type': None,
      'tags': ['ignore_reset'],
    },
    {
      'type': 'filename_pattern',
      'name': 'layer_filename_pattern',
      'default_value': '[layer name]',
      'display_name': _('Layer filename pattern'),
      'description': _('Layer filename pattern (empty string = layer name)'),
      'gui_type': None,
    },
    {
      'type': 'generic',
      'name': 'selected_layers',
      # key: image ID; value: set of selected layer IDs
      'default_value': collections.defaultdict(set),
      'display_name': _('Selected layers'),
      'pdb_type': None,
      'setting_sources': ['session'],
      'value_set': lambda value: collections.defaultdict(
        set, {key: set(val) for key, val in value.items()}),
      'value_save': lambda value: {key: list(val) for key, val in value.items()},
    },
    {
      'type': 'generic',
      'name': 'selected_layers_persistent',
      # key: image file path; value: set of selected layer names
      'default_value': collections.defaultdict(set),
      'display_name': _('Selected layers'),
      'pdb_type': None,
      'setting_sources': ['persistent'],
      'value_set': lambda value: collections.defaultdict(
        set, {key: set(val) for key, val in value.items()}),
      'value_save': lambda value: {key: list(val) for key, val in value.items()},
    },
    {
      'type': 'options',
      'name': 'overwrite_mode',
      'default_value': 'rename_new',
      'items': [
        ('replace', _('_Replace'), pg.overwrite.OverwriteModes.REPLACE),
        ('skip', _('_Skip'), pg.overwrite.OverwriteModes.SKIP),
        ('rename_new', _('Rename _new file'), pg.overwrite.OverwriteModes.RENAME_NEW),
        ('rename_existing', _('Rename _existing file'),
         pg.overwrite.OverwriteModes.RENAME_EXISTING)],
      'display_name': _('Overwrite mode (non-interactive run mode only)'),
    },
    {
      'type': 'dict',
      'name': 'available_tags',
      'default_value': actions.BUILTIN_TAGS,
      'pdb_type': None,
      'gui_type': None,
    },
    {
      'type': 'boolean',
      'name': 'edit_mode',
      'default_value': False,
      'pdb_type': None,
      'gui_type': None,
    },
    {
      'type': 'string',
      'name': 'plugin_version',
      'default_value': pg.config.PLUGIN_VERSION,
      'pdb_type': None,
      'gui_type': None,
    },
  ])
  
  settings.add(settings_gui.create_gui_settings())
  
  settings['main'].add([actions.create(
    name='procedures',
    initial_actions=[builtin_procedures.BUILTIN_PROCEDURES['use_layer_size']]),
  ])
  
  visible_constraint_dict = dict(builtin_constraints.BUILTIN_CONSTRAINTS['visible'])
  visible_constraint_dict['enabled'] = False
  visible_constraint_dict['also_apply_to_parent_folders'] = True
  
  settings['main'].add([actions.create(
    name='constraints',
    initial_actions=[
      builtin_constraints.BUILTIN_CONSTRAINTS['layers'],
      visible_constraint_dict]),
  ])
  
  settings['main/procedures'].connect_event(
    'after-add-action', _on_after_add_procedure, settings['main'])
  
  settings['main/constraints'].connect_event(
    'after-add-action',
    _on_after_add_constraint,
    settings['main/selected_layers'],
    settings['special/image'])
  
  return settings


def _on_after_add_procedure(procedures, procedure, orig_procedure_dict, main_settings):
  if procedure['orig_name'].value == 'export':
    _set_initial_output_directory_in_export(
      procedure['arguments/output_directory'],
      main_settings['output_directory'])
    
    _set_sensitive_for_image_filename_pattern_in_export(
      procedure['arguments/export_mode'],
      procedure['arguments/single_image_filename_pattern'])
    
    procedure['arguments/export_mode'].connect_event(
      'value-changed',
      _set_sensitive_for_image_filename_pattern_in_export,
      procedure['arguments/single_image_filename_pattern'])


def _set_initial_output_directory_in_export(
      export_output_directory_setting, output_directory_setting):
  # The check avoids plug-in failing to display the GUI due to an invalid
  # directory.
  if output_directory_setting.value:
    export_output_directory_setting.set_value(output_directory_setting.value)


def _set_sensitive_for_image_filename_pattern_in_export(
      export_mode_setting, single_image_filename_pattern_setting):
  if export_mode_setting.value == export_.ExportModes.ENTIRE_IMAGE_AT_ONCE:
    single_image_filename_pattern_setting.gui.set_sensitive(True)
  else:
    single_image_filename_pattern_setting.gui.set_sensitive(False)


def _on_after_add_constraint(
      constraints,
      constraint,
      orig_constraint_dict,
      selected_items_setting,
      image_setting):
  if constraint['orig_name'].value == 'selected_in_preview':
    constraint['arguments/selected_layers'].gui.set_visible(False)
    _sync_selected_items_and_only_selected_items_constraint(
      selected_items_setting, constraint, image_setting)


def _sync_selected_items_and_only_selected_items_constraint(
      selected_items_setting, constraint, image_setting):
  
  def _on_selected_items_changed(
        selected_items_setting, only_selected_items_constraint, image_setting):
    if image_setting.value is not None:
      only_selected_items_constraint['arguments/selected_layers'].set_value(
        selected_items_setting.value[image_setting.value.ID])
  
  _on_selected_items_changed(selected_items_setting, constraint, image_setting)
  
  selected_items_setting.connect_event(
    'value-changed', _on_selected_items_changed, constraint, image_setting)


#===============================================================================


def setup_image_ids_and_filepaths_settings(
      image_ids_dict_setting,
      image_filepaths_dict_setting,
      assign_image_id_to_filepath_func=None,
      assign_image_id_to_filepath_func_args=None,
      assign_filepath_to_image_id_func=None,
      assign_filepath_to_image_id_func_args=None):
  """
  Set up a connection between a setting with a dict of (image ID, value) pairs
  and a setting with a dict of (image file path, value) pairs. This function
  makes the two settings act like one - the former stored in a session-wide
  setting source, and the latter in a persistent setting source.
  
  The rationale behind using two settings is that the IDs of images do not
  change during a GIMP session while the their file paths can.
  
  Optionally, instead of direct assignment of values between the settings, you
  may pass callbacks that convert values (separate callbacks for first setting
  value to second and vice versa) along with optional arguments. The callbacks
  must accept at least four arguments - current image ID, current image file
  path, the first setting and the second setting.
  """
  if assign_image_id_to_filepath_func is None:
    assign_image_id_to_filepath_func = _default_assign_image_id_to_filepath
  
  if assign_image_id_to_filepath_func_args is None:
    assign_image_id_to_filepath_func_args = []
  
  if assign_filepath_to_image_id_func is None:
    assign_filepath_to_image_id_func = _default_assign_image_filepath_to_id
  
  if assign_filepath_to_image_id_func_args is None:
    assign_filepath_to_image_id_func_args = []
  
  image_filepaths_dict_setting.connect_event(
    'after-load-group', _remove_invalid_image_filepaths)
  
  image_filepaths_dict_setting.connect_event(
    'before-save',
    _update_image_filepaths,
    image_ids_dict_setting,
    assign_image_id_to_filepath_func,
    assign_image_id_to_filepath_func_args)
  
  image_ids_dict_setting.connect_event(
    'after-load-group',
    _update_image_ids,
    image_filepaths_dict_setting,
    assign_filepath_to_image_id_func,
    assign_filepath_to_image_id_func_args)


def _default_assign_image_id_to_filepath(
      image_id, image_filepath, image_ids_setting, image_filepaths_setting):
  image_filepaths_setting.value[image_filepath] = image_ids_setting.value[image_id]


def _default_assign_image_filepath_to_id(
      image_id, image_filepath, image_ids_setting, image_filepaths_setting):
  image_ids_setting.value[image_id] = image_filepaths_setting.value[image_filepath]


def _remove_invalid_image_filepaths(image_filepaths_dict_setting):
  for image_filepath, values in list(image_filepaths_dict_setting.value.items()):
    if not(os.path.isfile(image_filepath) and values):
      del image_filepaths_dict_setting.value[image_filepath]


def _update_image_filepaths(
      image_filepaths_dict_setting,
      image_ids_dict_setting,
      assign_image_id_to_filepath_func,
      assign_image_id_to_filepath_func_args):
  current_images = gimp.image_list()
  
  for image in current_images:
    if image.ID in image_ids_dict_setting.value and image.filename:
      assign_image_id_to_filepath_func(
        image.ID,
        os.path.abspath(image.filename),
        image_ids_dict_setting,
        image_filepaths_dict_setting,
        *assign_image_id_to_filepath_func_args)


def _update_image_ids(
      image_ids_dict_setting,
      image_filepaths_dict_setting,
      assign_filepath_to_image_id_func,
      assign_filepath_to_image_id_func_args):
  current_images = gimp.image_list()
  
  for image in current_images:
    if (image.ID not in image_ids_dict_setting.value
        and image.filename in image_filepaths_dict_setting.value):
      assign_filepath_to_image_id_func(
        image.ID,
        os.path.abspath(image.filename),
        image_ids_dict_setting,
        image_filepaths_dict_setting,
        *assign_filepath_to_image_id_func_args)


def item_ids_to_names(
      image_id, image_filepath, image_ids_setting, image_filepaths_setting, item_tree):
  image_filepaths_setting.value[image_filepath] = set(
    [item_tree[item_id].orig_name for item_id in image_ids_setting.value[image_id]
     if item_id in item_tree])


def item_names_to_ids(
      image_id, image_filepath, image_ids_setting, image_filepaths_setting, item_tree):
  image_ids_setting.value[image_id] = set(
    [item_tree[item_orig_name].raw.ID
     for item_orig_name in image_filepaths_setting.value[image_filepath]
     if item_orig_name in item_tree])


def item_id_to_name(
      image_id, image_filepath, image_ids_setting, image_filepaths_setting, item_tree):
  item_id = image_ids_setting.value[image_id]
  image_filepaths_setting.value[image_filepath] = (
    item_tree[item_id].orig_name if item_id in item_tree else None)


def item_name_to_id(
      image_id, image_filepath, image_ids_setting, image_filepaths_setting, item_tree):
  item_orig_name = image_filepaths_setting.value[image_filepath]
  image_ids_setting.value[image_id] = (
    item_tree[item_orig_name].raw.ID if item_orig_name in item_tree else None)
