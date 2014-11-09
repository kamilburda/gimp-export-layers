#! /usr/bin/env python
#
#-------------------------------------------------------------------------------
#
# Export Layers - GIMP plug-in that exports layers as separate images
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

#===============================================================================

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division

str = unicode

#===============================================================================

from export_layers import constants


if constants.DEBUG:
  import sys
  
  from export_layers.pylibgimpplugin import tee
  
  tee.Tee(sys.stdout, open(constants.PLUGINS_LOG_STDOUT_PATH, 'a'),
          log_header_title=constants.PLUGIN_TITLE, flush_file=True)
  tee.Tee(sys.stderr, open(constants.PLUGINS_LOG_STDERR_PATH, 'a'),
          log_header_title=constants.PLUGIN_TITLE, flush_file=True)


import gettext

gettext.install(constants.DOMAIN_NAME, constants.LOCALE_PATH, unicode=True)


import gimp
import gimpplugin
import gimpenums

from export_layers.pylibgimpplugin import settings
from export_layers.pylibgimpplugin import overwrite

from export_layers import settings_plugin
from export_layers import gui_plugin
from export_layers import exportlayers

#===============================================================================


class ExportLayersPlugin(gimpplugin.plugin):
  
  def __init__(self):
    self.special_settings = settings_plugin.SpecialSettings()
    self.main_settings = settings_plugin.MainSettings()
    
    self.gimpshelf_stream = settings.GimpShelfSettingStream(constants.SHELF_PREFIX)
    self.config_file_stream = settings.JSONFileSettingStream(constants.CONFIG_FILE)
    
    self.setting_persistor = settings.SettingPersistor([self.gimpshelf_stream], [self.gimpshelf_stream])
    
    self.export_layers_settings = []
    for setting in list(self.special_settings) + list(self.main_settings):
      if setting.can_be_registered_to_pdb:
        self.export_layers_settings.append(setting)
    
    self.export_layers_to_settings = [
      self.special_settings['run_mode'],
      self.special_settings['image'],
    ]
    
    self.export_layers_return_values = []
    self.export_layers_to_return_values = []
  
  def query(self):
    gimp.domain_register(constants.DOMAIN_NAME, constants.LOCALE_PATH)
    
    gimp.install_procedure(
      "plug_in_export_layers",
      _("Export layers as separate images in specified file format to specified "
        "directory, using layer names as filenames"),
      "",
      "khalim19 <khalim19@gmail.com>",
      "khalim19",
      "2013",
      _("E_xport Layers..."),
      "*",
      gimpenums.PLUGIN,
      self._create_plugin_params(self.export_layers_settings),
      self._create_plugin_params(self.export_layers_return_values)
    )
    gimp.install_procedure(
      "plug_in_export_layers_to",
      _("Run \"{0}\" with the last values specified").format(constants.PLUGIN_TITLE),
      _("If the plug-in is run for the first time (i.e. no last values exist), "
        "default values will be used."),
      "khalim19 <khalim19@gmail.com>",
      "khalim19",
      "2013",
      _("Export Layers _to"),
      "*",
      gimpenums.PLUGIN,
      self._create_plugin_params(self.export_layers_to_settings),
      self._create_plugin_params(self.export_layers_to_return_values)
    )
    
    gimp.menu_register("plug_in_export_layers", "<Image>/File/Export")
    gimp.menu_register("plug_in_export_layers_to", "<Image>/File/Export")
  
  def plug_in_export_layers(self, *args):
    run_mode = args[0]
    image = args[1]
    self.special_settings['run_mode'].value = run_mode
    self.special_settings['image'].value = image
    
    if run_mode == gimpenums.RUN_INTERACTIVE:
      self._run_export_layers_interactive(image)
    elif run_mode == gimpenums.RUN_WITH_LAST_VALS:
      self._run_with_last_vals(image)
    else:
      self._run_noninteractive(image, args)
  
  def plug_in_export_layers_to(self, run_mode, image):
    if run_mode == gimpenums.RUN_INTERACTIVE:
      self.setting_persistor.load([self.special_settings['first_run']])
      if self.special_settings['first_run'].value:
        self._run_export_layers_interactive(image)
      else:
        self._run_export_layers_to_interactive(image)
    else:
      self._run_with_last_vals(image)
  
  def _run_noninteractive(self, image, args):
    # Start with the third parameter - run_mode and image are already set.
    for setting, arg in zip(self.export_layers_settings[2:], args[2:]):
      if isinstance(arg, bytes):
        arg = arg.decode()
      setting.value = arg
    
    self._run_plugin_noninteractive(gimpenums.RUN_NONINTERACTIVE, image)
  
  def _run_with_last_vals(self, image):
    self.setting_persistor.read_setting_streams.append(self.config_file_stream)
    status = self.setting_persistor.load(self.main_settings)
    self.setting_persistor.read_setting_streams.pop()
    
    if status == self.setting_persistor.READ_FAIL:
      print(self.setting_persistor.status_message)
    
    self._run_plugin_noninteractive(gimpenums.RUN_WITH_LAST_VALS, image)
  
  def _run_export_layers_interactive(self, image):
    gui_plugin.export_layers_gui(image, self.main_settings, self.special_settings,
                                 self.gimpshelf_stream, self.config_file_stream)
  
  def _run_export_layers_to_interactive(self, image):
    gui_plugin.export_layers_to_gui(image, self.main_settings, self.setting_persistor)
  
  def _run_plugin_noninteractive(self, run_mode, image):
    self.main_settings.streamline(force=True)
    
    layer_exporter = exportlayers.LayerExporter(
      run_mode,
      image,
      self.main_settings,
      overwrite_chooser=overwrite.NoninteractiveOverwriteChooser(self.main_settings['overwrite_mode'].value),
      progress_updater=None
    )
    try:
      layer_exporter.export_layers()
    except exportlayers.ExportLayersCancelError as e:
      print(e.message)
    except exportlayers.ExportLayersError as e:
      print(e.message)
      raise
    
    self.special_settings['first_run'].value = False
    self.setting_persistor.save(self.main_settings, [self.special_settings['first_run']])
  
  def _create_plugin_params(self, settings):
    return [self._create_plugin_param(setting) for setting in settings]
  
  def _create_plugin_param(self, setting):
    return (setting.gimp_pdb_type, setting.name.encode(), setting.short_description.encode())

#===============================================================================

if __name__ == "__main__":
  ExportLayersPlugin().start()
