#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals

import inspect
import os
import sys


# Allow importing modules in directories in the 'plug-ins' directory.
current_module_dirpath = os.path.dirname(inspect.getfile(inspect.currentframe()))
if current_module_dirpath not in sys.path:
  sys.path.append(current_module_dirpath)

# Disable overlay scrollbar (notably used in Ubuntu) to be consistent with the
# Export menu.
os.environ['LIBOVERLAY_SCROLLBAR'] = '0'


from export_layers import pygimplib as pg
from future.builtins import *

import gimpenums

from export_layers import exportlayers
from export_layers import settings_plugin
from export_layers import update
from export_layers.gui import main as gui_main


SETTINGS = settings_plugin.create_settings()


@pg.procedure(
  blurb=_('Export layers as separate images'),
  author=pg.config.AUTHOR_NAME,
  copyright_notice=pg.config.AUTHOR_NAME,
  date=pg.config.COPYRIGHT_YEARS,
  menu_name=_('E_xport Layers...'),
  menu_path='<Image>/File/Export',
  parameters=[SETTINGS['special'], SETTINGS['main']]
)
def plug_in_export_layers(run_mode, image, *args):
  SETTINGS['special/run_mode'].set_value(run_mode)
  SETTINGS['special/image'].set_value(image)
  
  layer_tree = pg.itemtree.LayerTree(image, name=pg.config.SOURCE_NAME, is_filtered=True)
  _setup_settings_additional(SETTINGS, layer_tree)
  
  status = update.update(SETTINGS, run_mode == gimpenums.RUN_INTERACTIVE)
  if status == update.ABORT:
    return
  
  if run_mode == gimpenums.RUN_INTERACTIVE:
    _run_export_layers_interactive(layer_tree)
  elif run_mode == gimpenums.RUN_WITH_LAST_VALS:
    _run_with_last_vals(layer_tree)
  else:
    _run_noninteractive(layer_tree, args)


@pg.procedure(
  blurb=_('Run "{}" with the last values specified').format(pg.config.PLUGIN_TITLE),
  description=_(
    'If the plug-in is run for the first time (i.e. no last values exist), '
    'default values will be used.'),
  author=pg.config.AUTHOR_NAME,
  copyright_notice=pg.config.AUTHOR_NAME,
  date=pg.config.COPYRIGHT_YEARS,
  menu_name=_('E_xport Layers (repeat)'),
  menu_path='<Image>/File/Export',
  parameters=[SETTINGS['special']]
)
def plug_in_export_layers_repeat(run_mode, image):
  layer_tree = pg.itemtree.LayerTree(image, name=pg.config.SOURCE_NAME, is_filtered=True)
  _setup_settings_additional(SETTINGS, layer_tree)
  
  status = update.update(SETTINGS, run_mode == gimpenums.RUN_INTERACTIVE)
  if status == update.ABORT:
    return
  
  if run_mode == gimpenums.RUN_INTERACTIVE:
    SETTINGS['special/first_plugin_run'].load()
    if SETTINGS['special/first_plugin_run'].value:
      _run_export_layers_interactive(layer_tree)
    else:
      _run_export_layers_repeat_interactive(layer_tree)
  else:
    _run_with_last_vals(layer_tree)


def _setup_settings_additional(settings, layer_tree):
  settings_plugin.setup_image_ids_and_filepaths_settings(
    settings['main/selected_layers'],
    settings['main/selected_layers_persistent'],
    settings_plugin.convert_set_of_layer_ids_to_names, [layer_tree],
    settings_plugin.convert_set_of_layer_names_to_ids, [layer_tree])


def _run_noninteractive(layer_tree, args):
  main_settings = [
    setting for setting in SETTINGS['main'].walk()
    if setting.can_be_registered_to_pdb()]
  
  for setting, arg in zip(main_settings, pg.setting.iter_args(args, main_settings)):
    setting.set_value(arg)
  
  _run_plugin_noninteractive(gimpenums.RUN_NONINTERACTIVE, layer_tree)


def _run_with_last_vals(layer_tree):
  SETTINGS['main'].load()
  
  _run_plugin_noninteractive(gimpenums.RUN_WITH_LAST_VALS, layer_tree)


def _run_export_layers_interactive(layer_tree):
  gui_main.ExportLayersDialog(layer_tree, SETTINGS)


def _run_export_layers_repeat_interactive(layer_tree):
  gui_main.ExportLayersRepeatDialog(layer_tree, SETTINGS)


def _run_plugin_noninteractive(run_mode, layer_tree):
  layer_exporter = exportlayers.LayerExporter(
    run_mode, layer_tree.image, SETTINGS['main'])
  
  try:
    layer_exporter.export(layer_tree=layer_tree)
  except exportlayers.ExportLayersCancelError:
    pass


if __name__ == '__main__':
  pg.main()
