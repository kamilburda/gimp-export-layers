#-------------------------------------------------------------------------------
#
# This file is part of Export Layers.
#
# Copyright (C) 2013, 2014 khalim19 <khalim19@gmail.com>
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
This module:
* defines plug-in settings
"""

#===============================================================================

from __future__ import absolute_import
from __future__ import print_function
#from __future__ import unicode_literals
from __future__ import division

#===============================================================================

import gimp
import gimpenums

from export_layers.pylibgimpplugin import settings
from export_layers import exportlayers

#===============================================================================

class SpecialSettings(settings.SettingContainer):
  
  """
  These settings require special handling in the code,
  hence their separation from the main settings.
  """
  
  def _create_settings(self):
    
    self._add(
      settings.EnumSetting(
        'run_mode', 'non_interactive',
        [('interactive', "RUN-INTERACTIVE", gimpenums.RUN_INTERACTIVE),
         ('non_interactive', "RUN-NONINTERACTIVE", gimpenums.RUN_NONINTERACTIVE),
         ('run_with_last_vals', "RUN-WITH-LAST-VALS", gimpenums.RUN_WITH_LAST_VALS)]
      )
    )
    self['run_mode'].display_name = "The run mode"
    
    self._add(settings.ImageSetting('image', None))
    self['image'].display_name = "Image"
    
    self._add(settings.BoolSetting('first_run', True))
    self['first_run'].can_be_registered_to_pdb = False
    self['first_run'].description = (
      "True if the plug-in is successfully run for the first time "
      "in one GIMP session, False for subsequent runs."
    )

class MainSettings(settings.SettingContainer):
  
  def _create_settings(self):
    
    self._add(settings.NonEmptyStringSetting('file_format', ""))
    self['file_format'].display_name = "File format"
    self['file_format'].description = (
      "Type in file extension, with or without the leading period. "
      "To export in raw format, type \"raw\"."
    )
    
    self._add(settings.StringSetting('output_directory', gimp.user_directory(1)))   # Documents directory
    self['output_directory'].display_name = "Output directory"
    
    self._add(settings.BoolSetting('layer_groups_as_directories', False))
    self['layer_groups_as_directories'].display_name = "Treat layer groups as directories"
    self['layer_groups_as_directories'].description = (
      "If enabled, layers will be exported to subdirectories corresponding to the layer groups.\n"
      "If disabled, all layers will be exported to the output directory on the same level "
      "and no subdirectories will be created."
    )
    
    self._add(settings.BoolSetting('ignore_invisible', False))
    self['ignore_invisible'].display_name = "Ignore invisible layers"
    self['ignore_invisible'].description = (
      "If enabled, invisible layers will not be exported. Visible layers within "
      "invisible layer groups will also not be exported."
    )
    
    self._add(settings.BoolSetting('autocrop', False))
    self['autocrop'].display_name = "Autocrop layers"
    self['autocrop'].description = (
      "If enabled, layers will be autocropped before being exported."
    )
    
    self._add(settings.BoolSetting('use_image_size', False))
    self['use_image_size'].display_name = "Use image size instead of layer size"
    self['use_image_size'].description = (
      "If enabled, layers will be resized (but not scaled) to the image size. This is "
      "useful if you want to keep the size of the image canvas and the layer position "
      "within the image. If layers are partially outside the image canvas, "
      "they will be cut off. If you want to export the entire layer, "
      "leave this setting disabled."
    )
    
    self._add(
      settings.EnumSetting(
       'overwrite_mode', 'rename_new',
       [('replace', "Replace", exportlayers.OverwriteHandler.REPLACE),
        ('skip', "Skip", exportlayers.OverwriteHandler.SKIP),
        ('rename_new', "Rename new file", exportlayers.OverwriteHandler.RENAME_NEW),
        ('rename_existing', "Rename existing file", exportlayers.OverwriteHandler.RENAME_EXISTING),
        ('cancel', "Cancel", exportlayers.OverwriteHandler.CANCEL)]
      )
    )
    self['overwrite_mode'].display_name = "Overwrite mode (non-interactive run mode only)"
    self['overwrite_mode'].description = (
      "Indicates how to handle conflicting files. Skipped layers "
      "will not be regarded as exported."
    )
    
    self._add(
      settings.EnumSetting(
        'file_ext_mode', 'no_handling',
        [('no_handling', "No special handling"),
         ('only_matching_file_format', "Export only layers matching file format"),
         ('use_as_file_format', "Use as file formats")]
      )
    )
    self['file_ext_mode'].display_name = "File extensions in layer names"
    
    self._add(
      settings.EnumSetting(
        'strip_mode', 'identical',
        [('always', "Always strip file extension"),
         ('identical', "Strip identical to file format"),
         ('never', "Never strip file extension")]
      )
    )
    self['strip_mode'].display_name = "File extension stripping"
    
    self._add(
      settings.EnumSetting(
        'square_bracketed_mode', 'normal',
        [('normal', "Treat as normal layers"),
         ('background', "Treat as background layers"),
         ('ignore', "Ignore"),
         ('ignore_other', "Ignore other layers")]
      )
    )
    self['square_bracketed_mode'].display_name = "Layer names in [square brackets]"
    
    self._add(settings.BoolSetting('crop_to_background', False))
    self['crop_to_background'].display_name = "Crop to background"
    self['crop_to_background'].description = (
      "If enabled, layers will be cropped to the size of the background layers instead of their own size."
    )
    
    self._add(settings.BoolSetting('merge_layer_groups', False))
    self['merge_layer_groups'].display_name = "Merge layer groups"
    self['merge_layer_groups'].description = (
      "If enabled, each top-level layer group is merged into one layer. The name "
      "of each merged layer is the name of the corresponding top-level layer group."
    )
    
    self._add(settings.BoolSetting('empty_directories', False))
    self['empty_directories'].display_name = "Create directories for empty layer groups"
    self['empty_directories'].description = (
      "If enabled, empty subdirectories from empty layers groups are created."
    )
    
    self._add(settings.BoolSetting('ignore_layer_modes', False))
    self['ignore_layer_modes'].display_name = "Ignore layer modes"
    self['ignore_layer_modes'].description = (
      "Sets the layer mode of each layer to Normal. This is useful for layers "
      "with opacity less than 100% and a layer mode different than Normal or "
      "Dissolve, which would normally be completely invisible if a file format "
      "supporting alpha channel is used (such as PNG)."
    )
    
    
    self['file_ext_mode'].description = (
      'If "' + self['file_ext_mode'].options_display_names['use_as_file_format'] + '" is selected, '
      '"' + self['file_format'].display_name + '" must still be specified '
      '(for layers with invalid or no file extension).'
    )
    self['square_bracketed_mode'].description = (
      '"' + self['square_bracketed_mode'].options_display_names['background'] + '": '
      'these layers will be used as a background for all other layers and will not be exported separately.\n'
      '"' + self['square_bracketed_mode'].options_display_names['ignore'] + '": '
      'these layers will not be exported (and will not be treated as background layers).\n'
      '"' + self['square_bracketed_mode'].options_display_names['ignore_other'] + '": '
      'all other layers will not be exported.'
    )
    self['strip_mode'].description = (
      "Determines when to strip file extensions from layer names (including the period)."
    )
    
    self['file_format'].error_messages['not_specified'] = "file format not specified"
    self['file_format'].error_messages['default_needed'] = (
      "you need to specify default file format for layers with invalid or no format"
    )
    
    #---------------------------------------------------------------------------
    
    def streamline_layer_groups_as_directories(layer_groups_as_directories,
                                               empty_directories, merge_layer_groups):
      if not layer_groups_as_directories.value:
        empty_directories.value = False
        empty_directories.ui_enabled = False
        merge_layer_groups.ui_enabled = True
      else:
        empty_directories.ui_enabled = True
        merge_layer_groups.ui_enabled = False
        merge_layer_groups.value = False
    
    def streamline_file_ext_mode(file_ext_mode, file_format, strip_mode):
      if file_ext_mode.value == file_ext_mode.options['no_handling']:
        strip_mode.value = strip_mode.default_value
        strip_mode.ui_enabled = True
        file_format.error_messages['invalid_value'] = file_format.error_messages['not_specified']
      elif file_ext_mode.value == file_ext_mode.options['only_matching_file_format']:
        strip_mode.value = strip_mode.options['never']
        strip_mode.ui_enabled = False
        file_format.error_messages['invalid_value'] = file_format.error_messages['not_specified']
      elif file_ext_mode.value == file_ext_mode.options['use_as_file_format']:
        strip_mode.value = strip_mode.options['never']
        strip_mode.ui_enabled = False
        file_format.error_messages['invalid_value'] = file_format.error_messages['default_needed']
    
    def streamline_merge_layer_groups(merge_layer_groups, layer_groups_as_directories):
      if merge_layer_groups.value:
        layer_groups_as_directories.value = False
        layer_groups_as_directories.ui_enabled = False
      else:
        layer_groups_as_directories.ui_enabled = True
    
    def streamline_autocrop(autocrop, crop_to_background):
      if autocrop.value:
        crop_to_background.ui_enabled = True
      else:
        crop_to_background.value = False
        crop_to_background.ui_enabled = False
    
    self['layer_groups_as_directories'].set_streamline_func(
      streamline_layer_groups_as_directories, self['empty_directories'], self['merge_layer_groups']
    )
    self['file_ext_mode'].set_streamline_func(
      streamline_file_ext_mode, self['file_format'], self['strip_mode']
    )
    self['merge_layer_groups'].set_streamline_func(
      streamline_merge_layer_groups, self['layer_groups_as_directories']
    )
    self['autocrop'].set_streamline_func(
      streamline_autocrop, self['crop_to_background']
    )
