#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# Export Layers - GIMP plug-in that exports layers as separate images
#
# Copyright (C) 2013-2018 khalim19 <khalim19@gmail.com>
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
# along with Export Layers.  If not, see <https://www.gnu.org/licenses/>.

from __future__ import absolute_import, division, print_function, unicode_literals

import inspect
import os
import sys

# Fix Windows installation failing to import modules from the `export_layers`
# folder.
if os.name == "nt":
  current_module_dirpath = os.path.dirname(inspect.getfile(inspect.currentframe()))
  if current_module_dirpath not in sys.path:
    sys.path.append(current_module_dirpath)

# Disable overlay scrollbar (notably used in Ubuntu) to be consistent with the
# Export menu.
os.environ["LIBOVERLAY_SCROLLBAR"] = "0"

from export_layers import pygimplib
from future.builtins import *

import gimpenums

from export_layers.pygimplib import pgitemtree
from export_layers.pygimplib import pgconstants

import export_layers.config
export_layers.config.init()

from export_layers import exportlayers
from export_layers import settings_plugin
from export_layers.gui import gui_plugin

pygimplib.init()

#===============================================================================

SETTINGS = settings_plugin.create_settings()

#===============================================================================

@pygimplib.plugin(
  blurb=_("Export layers as separate images"),
  author="{0} <{1}>".format(
    pygimplib.config.AUTHOR_NAME, pygimplib.config.AUTHOR_CONTACT),
  copyright_notice=pygimplib.config.AUTHOR_NAME,
  date=pygimplib.config.COPYRIGHT_YEARS,
  menu_name=_("E_xport Layers..."),
  menu_path="<Image>/File/Export",
  parameters=[SETTINGS["special"], SETTINGS["main"]]
)
def plug_in_export_layers(run_mode, image, *args):
  SETTINGS["special/run_mode"].set_value(run_mode)
  SETTINGS["special/image"].set_value(image)
  
  layer_tree = pgitemtree.LayerTree(
    image, name=pygimplib.config.SOURCE_PERSISTENT_NAME, is_filtered=True)
  _setup_settings_additional(SETTINGS, layer_tree)
  
  if run_mode == gimpenums.RUN_INTERACTIVE:
    _run_export_layers_interactive(layer_tree)
  elif run_mode == gimpenums.RUN_WITH_LAST_VALS:
    _run_with_last_vals(layer_tree)
  else:
    _run_noninteractive(layer_tree, args)


@pygimplib.plugin(
  blurb=_('Run "{0}" with the last values specified').format(
    pygimplib.config.PLUGIN_TITLE),
  description=_(
    "If the plug-in is run for the first time (i.e. no last values exist), "
    "default values will be used."),
  author="{0} <{1}>".format(
    pygimplib.config.AUTHOR_NAME, pygimplib.config.AUTHOR_CONTACT),
  copyright_notice=pygimplib.config.AUTHOR_NAME,
  date=pygimplib.config.COPYRIGHT_YEARS,
  menu_name=_("E_xport Layers (repeat)"),
  menu_path="<Image>/File/Export",
  parameters=[SETTINGS["special"]]
)
def plug_in_export_layers_repeat(run_mode, image):
  layer_tree = pgitemtree.LayerTree(
    image, name=pygimplib.config.SOURCE_PERSISTENT_NAME, is_filtered=True)
  _setup_settings_additional(SETTINGS, layer_tree)
  
  if run_mode == gimpenums.RUN_INTERACTIVE:
    SETTINGS["special/first_plugin_run"].load()
    if SETTINGS["special/first_plugin_run"].value:
      _run_export_layers_interactive(layer_tree)
    else:
      _run_export_layers_repeat_interactive(layer_tree)
  else:
    _run_with_last_vals(layer_tree)


def _setup_settings_additional(settings, layer_tree):
  settings_plugin.setup_image_ids_and_filepaths_settings(
    settings["main/selected_layers"],
    settings["main/selected_layers_persistent"],
    settings_plugin.convert_set_of_layer_ids_to_names, [layer_tree],
    settings_plugin.convert_set_of_layer_names_to_ids, [layer_tree])


def _run_noninteractive(layer_tree, args):
  main_settings = [
    setting for setting in SETTINGS["main"].walk()
    if setting.can_be_registered_to_pdb()]
  
  for setting, arg in zip(main_settings, args):
    if isinstance(arg, bytes):
      arg = arg.decode(pgconstants.GIMP_CHARACTER_ENCODING)
    setting.set_value(arg)
  
  _run_plugin_noninteractive(gimpenums.RUN_NONINTERACTIVE, layer_tree)


def _run_with_last_vals(layer_tree):
  SETTINGS["main"].load()
  
  _run_plugin_noninteractive(gimpenums.RUN_WITH_LAST_VALS, layer_tree)


def _run_export_layers_interactive(layer_tree):
  gui_plugin.ExportLayersGui(layer_tree, SETTINGS)


def _run_export_layers_repeat_interactive(layer_tree):
  gui_plugin.ExportLayersRepeatGui(layer_tree, SETTINGS)


def _run_plugin_noninteractive(run_mode, layer_tree):
  layer_exporter = exportlayers.LayerExporter(
    run_mode, layer_tree.image, SETTINGS["main"])
  
  try:
    layer_exporter.export(layer_tree=layer_tree)
  except exportlayers.ExportLayersCancelError:
    pass


#===============================================================================

pygimplib.main()
