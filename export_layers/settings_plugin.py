#
# This file is part of Export Layers.
#
# Copyright (C) 2013-2016 khalim19 <khalim19@gmail.com>
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
# along with Export Layers.  If not, see <http://www.gnu.org/licenses/>.
#

"""
This module defines the plug-in settings.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

str = unicode

import collections
import os

import gimp
import gimpenums

import export_layers.pygimplib as pygimplib

from export_layers.pygimplib import overwrite
from export_layers.pygimplib import pgpath
from export_layers.pygimplib import pgsetting
from export_layers.pygimplib import pgsettinggroup

#===============================================================================


def create_settings():
  
  # Special settings
  #-----------------------------------------------------------------------------
  
  # These settings require special handling in the code, hence their separation
  # from the other settings.
  
  special_settings = pgsettinggroup.SettingGroup('special', [
    {
      'type': pgsetting.SettingTypes.enumerated,
      'name': 'run_mode',
      'default_value': 'non_interactive',
      'items': [('interactive', "RUN-INTERACTIVE", gimpenums.RUN_INTERACTIVE),
                ('non_interactive', "RUN-NONINTERACTIVE", gimpenums.RUN_NONINTERACTIVE),
                ('run_with_last_vals', "RUN-WITH-LAST-VALS", gimpenums.RUN_WITH_LAST_VALS)],
      'display_name': _("The run mode")
    },
    {
      'type': pgsetting.SettingTypes.image,
      'name': 'image',
      'default_value': None,
      'display_name': _("Image")
    },
    {
      'type': pgsetting.SettingTypes.boolean,
      'name': 'first_plugin_run',
      'default_value': True,
      'pdb_type': None,
      'setting_sources': [pygimplib.config.SOURCE_SESSION]
    },
  ])
  
  # Main settings
  #-----------------------------------------------------------------------------
  
  main_settings = pgsettinggroup.SettingGroup('main', [
    {
      'type': pgsetting.SettingTypes.file_extension,
      'name': 'file_extension',
      'default_value': "png",
      'display_name': "File extension"
    },
    {
      'type': pgsetting.SettingTypes.string,
      'name': 'output_directory',
      'default_value': gimp.user_directory(1),   # "Documents" directory
      'display_name': _("Output directory"),
      'gui_type': None
    },
    {
      'type': pgsetting.SettingTypes.boolean,
      'name': 'layer_groups_as_folders',
      'default_value': False,
      'display_name': _("Treat layer groups as folders")
    },
    {
      'type': pgsetting.SettingTypes.boolean,
      'name': 'only_visible_layers',
      'default_value': False,
      'display_name': _("Only visible layers")
    },
    {
      'type': pgsetting.SettingTypes.boolean,
      'name': 'use_image_size',
      'default_value': False,
      'display_name': _("Use image size")
    },
    {
      'type': pgsetting.SettingTypes.string,
      'name': 'layer_filename_pattern',
      'default_value': "[layer name]",
      'display_name': _("Layer filename pattern"),
      'description': _("Layer filename pattern (empty string = layer name)"),
      'gui_type': None
    },
    {
      'type': pgsetting.SettingTypes.boolean,
      'name': 'export_only_selected_layers',
      'default_value': False,
      'display_name': _("Export only selected layers"),
      'pdb_type': None
    },
    {
      'type': pgsetting.SettingTypes.generic,
      'name': 'selected_layers',
      # key: image ID; value: set of selected layer IDs
      'default_value': collections.defaultdict(set),
      'display_name': _("Selected layers"),
      'pdb_type': None,
      'setting_sources': [pygimplib.config.SOURCE_SESSION]
    },
    {
      'type': pgsetting.SettingTypes.generic,
      'name': 'selected_layers_persistent',
      # key: image filename; value: set of selected layer names
      'default_value': collections.defaultdict(set),
      'display_name': _("Selected layers"),
      'pdb_type': None,
      'setting_sources': [pygimplib.config.SOURCE_PERSISTENT]
    },
    {
      'type': pgsetting.SettingTypes.enumerated,
      'name': 'overwrite_mode',
      'default_value': 'rename_new',
      'items': [('replace', _("_Replace"), overwrite.OverwriteModes.REPLACE),
                ('skip', _("_Skip"), overwrite.OverwriteModes.SKIP),
                ('rename_new', _("Rename _new file"), overwrite.OverwriteModes.RENAME_NEW),
                ('rename_existing', _("Rename _existing file"), overwrite.OverwriteModes.RENAME_EXISTING),
                ('cancel', _("_Cancel"), overwrite.OverwriteModes.CANCEL)],
      'display_name': _("Overwrite mode (non-interactive run mode only)")
    },
  ], setting_sources=[pygimplib.config.SOURCE_SESSION, pygimplib.config.SOURCE_PERSISTENT])
  
  # Additional settings - operations and filters
  #-----------------------------------------------------------------------------
  
  more_operations_settings = pgsettinggroup.SettingGroup('more_operations', [
    {
      'type': pgsetting.SettingTypes.boolean,
      'name': 'merge_layer_groups',
      'default_value': False,
      'display_name': _("Merge layer groups")
    },
    {
      'type': pgsetting.SettingTypes.boolean,
      'name': 'insert_background_layers',
      'default_value': False,
      'display_name': _("Insert background layers")
    },
    {
      'type': pgsetting.SettingTypes.boolean,
      'name': 'insert_foreground_layers',
      'default_value': False,
      'display_name': _("Insert foreground layers")
    },
    {
      'type': pgsetting.SettingTypes.boolean,
      'name': 'inherit_transparency_from_layer_groups',
      'default_value': False,
      'display_name': _("Inherit transparency from layer groups"),
    },
    {
      'type': pgsetting.SettingTypes.boolean,
      'name': 'create_folders_for_empty_groups',
      'default_value': False,
      'display_name': _("Create folders for empty layer groups")
    },
    {
      'type': pgsetting.SettingTypes.boolean,
      'name': 'ignore_layer_modes',
      'default_value': False,
      'display_name': _("Ignore layer modes")
    },
    {
      'type': pgsetting.SettingTypes.boolean,
      'name': 'autocrop',
      'default_value': False,
      'display_name': _("Autocrop")
    },
    {
      'type': pgsetting.SettingTypes.boolean,
      'name': 'autocrop_to_background',
      'default_value': False,
      'display_name': _("Autocrop to background")
    },
    {
      'type': pgsetting.SettingTypes.boolean,
      'name': 'autocrop_to_foreground',
      'default_value': False,
      'display_name': _("Autocrop to foreground")
    },
    {
      'type': pgsetting.SettingTypes.boolean,
      'name': 'use_file_extensions_in_layer_names',
      'default_value': False,
      'display_name': _("Use file extensions in layer names")
    },
  ], pdb_type=None, setting_sources=[pygimplib.config.SOURCE_SESSION, pygimplib.config.SOURCE_PERSISTENT])
  
  more_filters_settings = pgsettinggroup.SettingGroup('more_filters', [
    {
      'type': pgsetting.SettingTypes.boolean,
      'name': 'only_layers_matching_file_extension',
      'default_value': False,
      'display_name': _("Only layers matching file extension")
    },
    {
      'type': pgsetting.SettingTypes.boolean,
      'name': 'only_non_tagged_layers',
      'default_value': False,
      'display_name': _("Only non-tagged layers")
    },
    {
      'type': pgsetting.SettingTypes.boolean,
      'name': 'only_tagged_layers',
      'default_value': False,
      'display_name': _("Only tagged layers")
    },
  ], pdb_type=None, setting_sources=[pygimplib.config.SOURCE_SESSION, pygimplib.config.SOURCE_PERSISTENT])
  
  main_settings.add([more_operations_settings, more_filters_settings])
  
  #-----------------------------------------------------------------------------
  
  def on_layer_groups_as_folders_changed(layer_groups_as_folders, create_folders_for_empty_groups,
                                         merge_layer_groups):
    if not layer_groups_as_folders.value:
      create_folders_for_empty_groups.set_value(False)
      create_folders_for_empty_groups.gui.set_enabled(False)
      merge_layer_groups.gui.set_enabled(True)
    else:
      create_folders_for_empty_groups.gui.set_enabled(True)
      merge_layer_groups.gui.set_enabled(False)
      merge_layer_groups.set_value(False)
  
  def on_use_file_extensions_in_layer_names_changed(use_file_extensions_in_layer_names, file_extension):
    if not use_file_extensions_in_layer_names.value:
      file_extension.error_messages[pgpath.FileValidatorErrorStatuses.IS_EMPTY] = ""
    else:
      file_extension.error_messages[pgpath.FileValidatorErrorStatuses.IS_EMPTY] = _(
        "You need to specify default file extension for layers with invalid or no extension.")
  
  def on_merge_layer_groups_changed(merge_layer_groups, layer_groups_as_folders):
    if merge_layer_groups.value:
      layer_groups_as_folders.set_value(False)
      layer_groups_as_folders.gui.set_enabled(False)
    else:
      layer_groups_as_folders.gui.set_enabled(True)
  
  #-----------------------------------------------------------------------------
  
  main_settings['layer_groups_as_folders'].connect_event('value-changed',
    on_layer_groups_as_folders_changed, main_settings['more_operations/create_folders_for_empty_groups'],
    main_settings['more_operations/merge_layer_groups'])
  
  main_settings['more_operations/use_file_extensions_in_layer_names'].connect_event('value-changed',
    on_use_file_extensions_in_layer_names_changed, main_settings['file_extension'])
  
  main_settings['more_operations/merge_layer_groups'].connect_event('value-changed',
    on_merge_layer_groups_changed, main_settings['layer_groups_as_folders'])
  
  #-----------------------------------------------------------------------------
  
  settings = pgsettinggroup.SettingGroup('all_settings', [special_settings, main_settings])
  
  settings.set_ignore_tags({
    'special': ['reset', 'load', 'save'],
    'main/output_directory': ['reset']
  })
  
  #-----------------------------------------------------------------------------
  
  return settings


#===============================================================================


def setup_image_ids_and_filenames_settings(image_ids_dict_setting, image_filenames_dict_setting,
                                           convert_value_first_second_func=None,
                                           convert_value_first_second_func_args=None,
                                           convert_value_second_first_func=None,
                                           convert_value_second_first_func_args=None):
  """
  Set up a connection between a setting with a dict of (image ID, value) pairs
  and a setting with a dict of (image filename, value) pairs. This function
  makes the two settings act like one - the former stored in a
  session-persistent setting source, and the latter in a persistent setting
  source.
  
  The rationale behind using two settings is that the IDs of images do not
  change during a GIMP session while the their filenames can.
  
  Optionally, instead of direct assignment of values between the settings, you
  may pass callbacks that convert values (separate callbacks for first setting
  value to second and vice versa) along with optional arguments. The callbacks
  must accept at least four arguments - current image ID, current image filename
  (full path), the first setting and the second setting.
  """
  
  def _assign_image_ids_to_filenames(image_id, image_filename, image_ids_setting, image_filenames_setting):
    image_filenames_setting.value[image_filename] = image_ids_setting.value[image_id]
  
  def _assign_image_filenames_to_ids(image_id, image_filename, image_ids_setting, image_filenames_setting):
    image_ids_setting.value[image_id] = image_filenames_setting.value[image_filename]
  
  _first_second_assign_func = (
    convert_value_first_second_func if convert_value_first_second_func is not None
    else _assign_image_ids_to_filenames)
  
  if convert_value_first_second_func_args is None:
    convert_value_first_second_func_args = []
  
  _second_first_assign_func = (
    convert_value_second_first_func if convert_value_second_first_func is not None
    else _assign_image_filenames_to_ids)
  
  if convert_value_second_first_func_args is None:
    convert_value_second_first_func_args = []
  
  def _remove_invalid_image_filenames(image_filenames_dict_setting):
    for image_filename, values in list(image_filenames_dict_setting.value.items()):
      if not(os.path.isfile(image_filename) and values):
        del image_filenames_dict_setting.value[image_filename]
  
  def _update_image_filenames(image_filenames_dict_setting, image_ids_dict_setting):
    current_images = gimp.image_list()
    
    for image in current_images:
      if image.ID in image_ids_dict_setting.value and image.filename:
        _first_second_assign_func(
          image.ID, os.path.abspath(image.filename),
          image_ids_dict_setting, image_filenames_dict_setting, *convert_value_first_second_func_args)
  
  def _update_image_ids(image_ids_dict_setting, image_filenames_dict_setting):
    current_images = gimp.image_list()
    
    for image in current_images:
      if image.ID not in image_ids_dict_setting.value and image.filename in image_filenames_dict_setting.value:
        _second_first_assign_func(
          image.ID, os.path.abspath(image.filename),
          image_ids_dict_setting, image_filenames_dict_setting, *convert_value_second_first_func_args)
  
  image_filenames_dict_setting.connect_event('after-load-group', _remove_invalid_image_filenames)
  image_filenames_dict_setting.connect_event('before-save', _update_image_filenames, image_ids_dict_setting)
  image_ids_dict_setting.connect_event('after-load-group', _update_image_ids, image_filenames_dict_setting)


def convert_set_of_layer_ids_to_names(image_id, image_filename, image_ids_setting,
                                      image_filenames_setting, layer_tree):
  image_filenames_setting.value[image_filename] = set(
    [layer_tree[layer_id].orig_name for layer_id in image_ids_setting.value[image_id]
     if layer_id in layer_tree])


def convert_set_of_layer_names_to_ids(image_id, image_filename, image_ids_setting,
                                      image_filenames_setting, layer_tree):
  image_ids_setting.value[image_id] = set(
    [layer_tree[layer_orig_name].item.ID for layer_orig_name in image_filenames_setting.value[image_filename]
     if layer_orig_name in layer_tree])


def convert_layer_id_to_name(image_id, image_filename, image_ids_setting,
                             image_filenames_setting, layer_tree):
  layer_id = image_ids_setting.value[image_id]
  image_filenames_setting.value[image_filename] = (
    layer_tree[layer_id].orig_name if layer_id in layer_tree else None)


def convert_layer_name_to_id(image_id, image_filename, image_ids_setting,
                             image_filenames_setting, layer_tree):
  layer_orig_name = image_filenames_setting.value[image_filename]
  image_ids_setting.value[image_id] = (
    layer_tree[layer_orig_name].item.ID if layer_orig_name in layer_tree else None)
