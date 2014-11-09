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

from export_layers.pylibgimpplugin import settings
from export_layers.pylibgimpplugin import libfiles
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
    self['run_mode'].display_name = _("The run mode")
    
    self._add(settings.ImageSetting('image', None))
    self['image'].display_name = _("Image")
    
    self._add(settings.BoolSetting('first_run', True))
    self['first_run'].can_be_registered_to_pdb = False
    self['first_run'].description = _(
      "True if the plug-in successfully ran for the first time "
      "in one GIMP session, False for subsequent runs."
    )


class MainSettings(settings.SettingContainer):
  
  def _create_settings(self):
    
    self._add(settings.FileExtensionSetting('file_extension', ""))
    self['file_extension'].display_name = _("File extension")
    self['file_extension'].description = _(
      "Type in file extension, with or without the leading period. "
      "To export in RAW format, type \"data\"."
    )
    
    self._add(settings.DirectorySetting('output_directory', gimp.user_directory(1)))   # "Documents" directory
    self['output_directory'].display_name = _("Output directory")
    
    self._add(settings.BoolSetting('layer_groups_as_directories', False))
    self['layer_groups_as_directories'].display_name = _("Treat layer groups as directories")
    self['layer_groups_as_directories'].description = _(
      "If enabled, layers will be exported to subdirectories corresponding to the layer groups.\n"
      "If disabled, all layers will be exported to the output directory on the same level "
      "and no subdirectories will be created."
    )
    
    self._add(settings.BoolSetting('ignore_invisible', False))
    self['ignore_invisible'].display_name = _("Ignore invisible layers")
    self['ignore_invisible'].description = _(
      "If enabled, invisible layers will not be exported. Visible layers within "
      "invisible layer groups will also not be exported."
    )
    
    self._add(settings.BoolSetting('autocrop', False))
    self['autocrop'].display_name = _("Autocrop layers")
    self['autocrop'].description = _(
      "If enabled, layers will be autocropped before being exported."
    )
    
    self._add(settings.BoolSetting('use_image_size', False))
    self['use_image_size'].display_name = _("Use image size")
    self['use_image_size'].description = _(
      "If enabled, layers will be resized (but not scaled) to the image size. This is "
      "useful if you want to keep the size of the image canvas and the layer position "
      "within the image. If layers are partially outside the image canvas, "
      "they will be cut off."
    )
    
    self._add(
      settings.EnumSetting(
        'file_ext_mode', 'no_special_handling',
        [('no_special_handling', _("No special handling")),
         ('only_matching_file_extension', _("Export only layers matching file extension")),
         ('use_as_file_extensions', _("Use as file extensions"))]
      )
    )
    self['file_ext_mode'].display_name = _("File extensions in layer names")
    
    self._add(
      settings.EnumSetting(
        'strip_mode', 'identical',
        [('always', _("Always strip file extension")),
         ('identical', _("Strip identical file extension")),
         ('never', _("Never strip file extension"))]
      )
    )
    self['strip_mode'].display_name = _("File extension stripping")
    self['strip_mode'].description = _(
      "Determines when to strip file extensions from layer names (including the period)."
    )
    
    self._add(
      settings.EnumSetting(
        'square_bracketed_mode', 'normal',
        [('normal', _("Treat as normal layers")),
         ('background', _("Treat as background layers")),
         ('ignore', _("Ignore")),
         ('ignore_other', _("Ignore other layers"))]
      )
    )
    self['square_bracketed_mode'].display_name = _("Layer names in [square brackets]")
    
    self._add(settings.BoolSetting('crop_to_background', False))
    self['crop_to_background'].display_name = _("Crop to background")
    self['crop_to_background'].description = _(
      "If enabled, layers will be cropped to the size of the background layers instead of their own size."
    )
    
    self._add(settings.BoolSetting('merge_layer_groups', False))
    self['merge_layer_groups'].display_name = _("Merge layer groups")
    self['merge_layer_groups'].description = _(
      "If enabled, each top-level layer group is merged into one layer. The name "
      "of each merged layer is the name of the corresponding top-level layer group."
    )
    
    self._add(settings.BoolSetting('empty_directories', False))
    self['empty_directories'].display_name = _("Create directories for empty layer groups")
    self['empty_directories'].description = _(
      "If enabled, empty subdirectories from empty layers groups are created."
    )
    
    self._add(settings.BoolSetting('ignore_layer_modes', False))
    self['ignore_layer_modes'].display_name = _("Ignore layer modes")
    self['ignore_layer_modes'].description = _(
      "If enabled, the layer mode for each layer is set to Normal. This is "
      "useful for layers with opacity less than 100% and a layer mode different "
      "than Normal or Dissolve, which would normally be completely invisible "
      "if a file format supporting alpha channel is used (such as PNG)."
    )
    
    self._add(
      settings.EnumSetting(
       'overwrite_mode', 'rename_new',
       [('replace', _("Replace"), exportlayers.OverwriteHandler.REPLACE),
        ('skip', _("Skip"), exportlayers.OverwriteHandler.SKIP),
        ('rename_new', _("Rename new file"), exportlayers.OverwriteHandler.RENAME_NEW),
        ('rename_existing', _("Rename existing file"), exportlayers.OverwriteHandler.RENAME_EXISTING),
        ('cancel', _("Cancel"), exportlayers.OverwriteHandler.CANCEL)]
      )
    )
    self['overwrite_mode'].display_name = _("Overwrite mode (non-interactive run mode only)")
    self['overwrite_mode'].description = _(
      "Indicates how to handle conflicting files. Skipped layers "
      "will not be regarded as exported."
    )
    
    #---------------------------------------------------------------------------
    
    self['file_ext_mode'].description = _(
      'If "{0}" is selected, "{1}" must still be '
      'specified (for layers with invalid or no file extension).'
    ).format(self['file_ext_mode'].options_display_names['use_as_file_extensions'],
             self['file_extension'].display_name)
    
    self['square_bracketed_mode'].description = _(
      '"{0}": these layers will be used as a background for all other layers '
      'and will not be exported separately.\n'
      '"{1}": these layers will not be exported (and will not be treated as '
      'background layers).\n'
      '"{2}": all other layers will not be exported.'
    ).format(self['square_bracketed_mode'].options_display_names['background'],
             self['square_bracketed_mode'].options_display_names['ignore'],
             self['square_bracketed_mode'].options_display_names['ignore_other'])
    
    self['file_extension'].error_messages['default_needed'] = _(
      "You need to specify default file extension for layers with invalid or no extension."
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
    
    def streamline_file_ext_mode(file_ext_mode, file_extension, strip_mode):
      if file_ext_mode.value == file_ext_mode.options['no_special_handling']:
        strip_mode.ui_enabled = True
        file_extension.error_messages[libfiles.FileExtensionValidator.IS_EMPTY] = ""
      elif file_ext_mode.value == file_ext_mode.options['only_matching_file_extension']:
        strip_mode.value = strip_mode.options['never']
        strip_mode.ui_enabled = False
        file_extension.error_messages[libfiles.FileExtensionValidator.IS_EMPTY] = ""
      elif file_ext_mode.value == file_ext_mode.options['use_as_file_extensions']:
        strip_mode.value = strip_mode.options['never']
        strip_mode.ui_enabled = False
        file_extension.error_messages[libfiles.FileExtensionValidator.IS_EMPTY] = (
          file_extension.error_messages['default_needed']
        )
    
    def streamline_merge_layer_groups(merge_layer_groups, layer_groups_as_directories):
      if merge_layer_groups.value:
        layer_groups_as_directories.value = False
        layer_groups_as_directories.ui_enabled = False
      else:
        layer_groups_as_directories.ui_enabled = True
    
    def streamline_autocrop(autocrop, square_bracketed_mode, crop_to_background):
      if autocrop.value and square_bracketed_mode.value == square_bracketed_mode.options['background']:
        crop_to_background.ui_enabled = True
      else:
        crop_to_background.value = False
        crop_to_background.ui_enabled = False
    
    def streamline_square_bracketed_mode(square_bracketed_mode, autocrop, crop_to_background):
      if autocrop.value and square_bracketed_mode.value == square_bracketed_mode.options['background']:
        crop_to_background.ui_enabled = True
      else:
        crop_to_background.value = False
        crop_to_background.ui_enabled = False
    
    #---------------------------------------------------------------------------
    
    self['layer_groups_as_directories'].set_streamline_func(
      streamline_layer_groups_as_directories, self['empty_directories'], self['merge_layer_groups']
    )
    self['file_ext_mode'].set_streamline_func(
      streamline_file_ext_mode, self['file_extension'], self['strip_mode']
    )
    self['merge_layer_groups'].set_streamline_func(
      streamline_merge_layer_groups, self['layer_groups_as_directories']
    )
    self['autocrop'].set_streamline_func(
      streamline_autocrop, self['square_bracketed_mode'], self['crop_to_background']
    )
    self['square_bracketed_mode'].set_streamline_func(
      streamline_square_bracketed_mode, self['autocrop'], self['crop_to_background']
    )
