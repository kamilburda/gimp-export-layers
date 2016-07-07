#! /usr/bin/env python
#
# Export Layers - GIMP plug-in that exports layers as separate images
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

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

str = unicode

import os

try:
  # Disable overlay scrolling (notably used in Ubuntu) to be consistent with the
  # Export menu.
  os.environ['LIBOVERLAY_SCROLLBAR'] = "0"
except Exception:
  pass

import gimpenums

import export_layers.pygimplib as pygimplib
import export_layers.config

pygimplib.init()

from export_layers.pygimplib import pgsettingpersistor

from export_layers import exportlayers
from export_layers import gui_plugin
from export_layers import settings_plugin

#===============================================================================


settings = settings_plugin.create_settings()


@pygimplib.plugin(
  blurb=_("Export layers as separate images"),
  author="khalim19 <khalim19@gmail.com>",
  copyright_notice="khalim19",
  date="2013-2016",
  menu_name=_("E_xport Layers..."),
  menu_path="<Image>/File/Export",
  parameters=[settings['special'], settings['main']]
)
def plug_in_export_layers(run_mode, image, *args):
  settings['special/run_mode'].set_value(run_mode)
  settings['special/image'].set_value(image)
  
  if run_mode == gimpenums.RUN_INTERACTIVE:
    _run_export_layers_interactive(image)
  elif run_mode == gimpenums.RUN_WITH_LAST_VALS:
    _run_with_last_vals(image)
  else:
    _run_noninteractive(image, args)


@pygimplib.plugin(
  blurb=_("Run \"{0}\" with the last values specified").format(pygimplib.config.PLUGIN_TITLE),
  description=_("If the plug-in is run for the first time (i.e. no last values exist), "
                "default values will be used."),
  author="khalim19 <khalim19@gmail.com>",
  copyright_notice="khalim19",
  date="2013-2016",
  menu_name=_("E_xport Layers (repeat)"),
  menu_path="<Image>/File/Export",
  parameters=[settings['special']]
)
def plug_in_export_layers_repeat(run_mode, image):
  if run_mode == gimpenums.RUN_INTERACTIVE:
    settings['special/first_plugin_run'].load()
    if settings['special/first_plugin_run'].value:
      _run_export_layers_interactive(image)
    else:
      _run_export_layers_repeat_interactive(image)
  else:
    _run_with_last_vals(image)


def _run_noninteractive(image, args):
  for setting, arg in zip(settings['main'], args):
    if isinstance(arg, bytes):
      arg = arg.decode()
    setting.set_value(arg)
  
  _run_plugin_noninteractive(gimpenums.RUN_NONINTERACTIVE, image)


def _run_with_last_vals(image):
  status, status_message = settings['main'].load()
  if status == pgsettingpersistor.SettingPersistor.READ_FAIL:
    print(status_message)
  
  _run_plugin_noninteractive(gimpenums.RUN_WITH_LAST_VALS, image)


def _run_export_layers_interactive(image):
  gui_plugin.export_layers_gui(image, settings)


def _run_export_layers_repeat_interactive(image):
  gui_plugin.export_layers_repeat_gui(image, settings)


def _run_plugin_noninteractive(run_mode, image):
  layer_exporter = exportlayers.LayerExporter(run_mode, image, settings['main'])
  
  try:
    layer_exporter.export_layers()
  except exportlayers.ExportLayersCancelError as e:
    print(str(e))
  except exportlayers.ExportLayersError as e:
    print(str(e))
    raise


#===============================================================================

pygimplib.main()
