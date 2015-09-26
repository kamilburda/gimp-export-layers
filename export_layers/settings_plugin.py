#-------------------------------------------------------------------------------
#
# This file is part of Export Layers.
#
# Copyright (C) 2013-2015 khalim19 <khalim19@gmail.com>
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
#-------------------------------------------------------------------------------

"""
This module defines the plug-in settings.
"""

#===============================================================================

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division

str = unicode

#===============================================================================

import gimp
import gimpenums

from export_layers.pygimplib import pgsetting
from export_layers.pygimplib import pgsettinggroup
from export_layers.pygimplib import pgpath
from export_layers import exportlayers

#===============================================================================


def create_settings():
  
  #-----------------------------------------------------------------------------
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
      'pdb_type': pgsetting.SettingPdbTypes.none
    },
  ])
  
  #-----------------------------------------------------------------------------
  # Main settings
  #-----------------------------------------------------------------------------
  
  main_settings = pgsettinggroup.SettingGroup('main', [
    {
      'type': pgsetting.SettingTypes.file_extension,
      'name': 'file_extension',
      'default_value': "png",
      'display_name': "File extension",
      'error_messages': {
         'default_needed': _(
            "You need to specify default file extension for layers with invalid or no extension.")
      }
    },
    {
      'type': pgsetting.SettingTypes.directory,
      'name': 'output_directory',
      'default_value': gimp.user_directory(1),   # "Documents" directory
      'display_name': _("Output directory"),
      'error_messages': {
         pgpath.DirectoryPathValidator.IS_EMPTY: _("Output directory is not specified.")
      }
    },
    {
      'type': pgsetting.SettingTypes.boolean,
      'name': 'layer_groups_as_folders',
      'default_value': False,
      'display_name': _("Treat layer groups as folders")
    },
    {
      'type': pgsetting.SettingTypes.boolean,
      'name': 'ignore_invisible',
      'default_value': False,
      'display_name': _("Ignore invisible layers")
    },
    {
      'type': pgsetting.SettingTypes.boolean,
      'name': 'autocrop',
      'default_value': False,
      'display_name': _("Autocrop layers")
    },
    {
      'type': pgsetting.SettingTypes.boolean,
      'name': 'use_image_size',
      'default_value': False,
      'display_name': _("Use image size")
    },
    {
      'type': pgsetting.SettingTypes.enumerated,
      'name': 'file_ext_mode',
      'default_value': 'no_special_handling',
      'items': [('no_special_handling', _("No special handling")),
                ('only_matching_file_extension', _("Export only layers matching file extension")),
                ('use_as_file_extensions', _("Use as file extensions"))],
      'display_name': _("File extensions in layer names")
    },
    {
      'type': pgsetting.SettingTypes.enumerated,
      'name': 'strip_mode',
      'default_value': 'always',
      'items': [('always', _("Always strip file extension")),
                ('identical', _("Strip identical file extension")),
                ('never', _("Never strip file extension"))],
      'display_name': _("File extension stripping")
    },
    {
      'type': pgsetting.SettingTypes.enumerated,
      'name': 'square_bracketed_mode',
      'default_value': 'normal',
      'items': [('normal', _("Treat as normal layers")),
                ('background', _("Treat as background layers")),
                ('ignore', _("Ignore")),
                ('ignore_other', _("Ignore other layers"))],
      'display_name': _("Layer names in [square brackets]")
    },
    {
      'type': pgsetting.SettingTypes.boolean,
      'name': 'crop_to_background',
      'default_value': False,
      'display_name': _("Crop to background")
    },
    {
      'type': pgsetting.SettingTypes.boolean,
      'name': 'merge_layer_groups',
      'default_value': False,
      'display_name': _("Merge layer groups")
    },
    {
      'type': pgsetting.SettingTypes.boolean,
      'name': 'empty_folders',
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
      'type': pgsetting.SettingTypes.enumerated,
      'name': 'overwrite_mode',
      'default_value': 'rename_new',
      'items': [('replace', _("_Replace"), exportlayers.OverwriteHandler.REPLACE),
                ('skip', _("_Skip"), exportlayers.OverwriteHandler.SKIP),
                ('rename_new', _("Rename _new file"), exportlayers.OverwriteHandler.RENAME_NEW),
                ('rename_existing', _("Rename _existing file"), exportlayers.OverwriteHandler.RENAME_EXISTING),
                ('cancel', _("_Cancel"), exportlayers.OverwriteHandler.CANCEL)],
      'display_name': _("Overwrite mode (non-interactive run mode only)")
    },
  ])
  
  #-----------------------------------------------------------------------------
  
  def on_layer_groups_as_folders_changed(layer_groups_as_folders, empty_folders, merge_layer_groups):
    if not layer_groups_as_folders.value:
      empty_folders.set_value(False)
      empty_folders.gui.set_enabled(False)
      merge_layer_groups.gui.set_enabled(True)
    else:
      empty_folders.gui.set_enabled(True)
      merge_layer_groups.gui.set_enabled(False)
      merge_layer_groups.set_value(False)
  
  def on_file_ext_mode_changed(file_ext_mode, file_extension, strip_mode):
    if file_ext_mode.value == file_ext_mode.items['no_special_handling']:
      strip_mode.set_value(strip_mode.default_value)
      strip_mode.gui.set_enabled(True)
      file_extension.error_messages[pgpath.FileExtensionValidator.IS_EMPTY] = ""
    elif file_ext_mode.value == file_ext_mode.items['only_matching_file_extension']:
      strip_mode.set_value(strip_mode.items['never'])
      strip_mode.gui.set_enabled(False)
      file_extension.error_messages[pgpath.FileExtensionValidator.IS_EMPTY] = ""
    elif file_ext_mode.value == file_ext_mode.items['use_as_file_extensions']:
      strip_mode.set_value(strip_mode.items['never'])
      strip_mode.gui.set_enabled(False)
      file_extension.error_messages[pgpath.FileExtensionValidator.IS_EMPTY] = (
        file_extension.error_messages['default_needed']
      )
  
  def on_merge_layer_groups_changed(merge_layer_groups, layer_groups_as_folders):
    if merge_layer_groups.value:
      layer_groups_as_folders.set_value(False)
      layer_groups_as_folders.gui.set_enabled(False)
    else:
      layer_groups_as_folders.gui.set_enabled(True)
  
  def on_autocrop_changed(autocrop, square_bracketed_mode, crop_to_background):
    if autocrop.value and square_bracketed_mode.value == square_bracketed_mode.items['background']:
      crop_to_background.gui.set_enabled(True)
    else:
      crop_to_background.set_value(False)
      crop_to_background.gui.set_enabled(False)
  
  def on_square_bracketed_mode_changed(square_bracketed_mode, autocrop, crop_to_background):
    on_autocrop_changed(autocrop, square_bracketed_mode, crop_to_background)
  
  #-----------------------------------------------------------------------------
  
  main_settings['layer_groups_as_folders'].connect_value_changed_event(
    on_layer_groups_as_folders_changed, [main_settings['empty_folders'], main_settings['merge_layer_groups']]
  )
  main_settings['file_ext_mode'].connect_value_changed_event(
    on_file_ext_mode_changed, [main_settings['file_extension'], main_settings['strip_mode']]
  )
  main_settings['merge_layer_groups'].connect_value_changed_event(
    on_merge_layer_groups_changed, [main_settings['layer_groups_as_folders']]
  )
  main_settings['autocrop'].connect_value_changed_event(
    on_autocrop_changed, [main_settings['square_bracketed_mode'], main_settings['crop_to_background']]
  )
  main_settings['square_bracketed_mode'].connect_value_changed_event(
    on_square_bracketed_mode_changed, [main_settings['autocrop'], main_settings['crop_to_background']]
  )
  
  #-----------------------------------------------------------------------------
  
  main_settings.set_ignore_tags({
    'output_directory': ['reset'],
  })
  
  #-----------------------------------------------------------------------------
  
  settings = pgsettinggroup.SettingGroup('all_settings', [special_settings, main_settings])
  
  return settings


#===============================================================================


def add_gui_settings(settings):
  
  gui_settings = pgsettinggroup.SettingGroup('gui', [
    {
      'type': pgsetting.SettingTypes.generic,
      'name': 'dialog_position',
      'default_value': ()
    },
    {
      'type': pgsetting.SettingTypes.boolean,
      'name': 'advanced_settings_expanded',
      'default_value': False
    },
  ])
  
  session_only_gui_settings = pgsettinggroup.SettingGroup('gui_session', [
    {
      'type': pgsetting.SettingTypes.image_IDs_and_directories,
      'name': 'image_ids_and_directories',
      'default_value': {}
    },
  ])
  
  #-----------------------------------------------------------------------------
  
  settings.add([gui_settings, session_only_gui_settings])
  
  settings.set_ignore_tags({
    'gui': ['reset'],
    'gui_session': ['reset'],
  })
