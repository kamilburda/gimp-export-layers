#!/usr/bin/env python
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

from export_layers import batcher as batcher_
from export_layers import exceptions
from export_layers import settings_main
from export_layers import update
from export_layers import utils as utils_
from export_layers.gui import main as gui_main


SETTINGS = settings_main.create_settings()


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
  
  layer_tree = pg.itemtree.LayerTree(image, name=pg.config.SOURCE_NAME)
  
  status, unused_ = update.update(
    SETTINGS, 'ask_to_clear' if run_mode == gimpenums.RUN_INTERACTIVE else 'clear')
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
    'If the plug-in is run for the first time (i.e. no last values exist),'
    ' default values will be used.'),
  author=pg.config.AUTHOR_NAME,
  copyright_notice=pg.config.AUTHOR_NAME,
  date=pg.config.COPYRIGHT_YEARS,
  menu_name=_('E_xport Layers (repeat)'),
  menu_path='<Image>/File/Export',
  parameters=[SETTINGS['special']]
)
def plug_in_export_layers_repeat(run_mode, image):
  layer_tree = pg.itemtree.LayerTree(image, name=pg.config.SOURCE_NAME)
  
  status, unused_ = update.update(
    SETTINGS, 'ask_to_clear' if run_mode == gimpenums.RUN_INTERACTIVE else 'clear')
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


@pg.procedure(
  blurb=_('Run "{}" with the specified configuration file').format(pg.config.PLUGIN_TITLE),
  description=_(
    'The configuration file can be obtained by exporting settings'
    " in the plug-in's interactive dialog."
    ' This procedure will fail if the specified configuration file does not exist'
    ' or is not valid.'),
  author=pg.config.AUTHOR_NAME,
  copyright_notice=pg.config.AUTHOR_NAME,
  date=pg.config.COPYRIGHT_YEARS,
  parameters=[
    SETTINGS['special/run_mode'],
    SETTINGS['special/image'],
    pg.setting.StringSetting(name='config_filepath', display_name=_('Path to configuration file'))]
)
def plug_in_export_layers_with_config(run_mode, image, config_filepath):
  if not config_filepath or not os.path.isfile(config_filepath):
    sys.exit(1)
  
  layer_tree = pg.itemtree.LayerTree(image, name=pg.config.SOURCE_NAME)
  
  if config_filepath.endswith('.pkl'):
    setting_source_class = pg.setting.PickleFileSource
  else:
    setting_source_class = pg.setting.JsonFileSource
  
  setting_source = setting_source_class(
    pg.config.SOURCE_NAME, config_filepath, source_type='persistent')
  
  status, unused_ = update.update(
    SETTINGS, handle_invalid='abort', sources={'persistent': setting_source})
  if status == update.ABORT:
    sys.exit(1)
  
  load_result = SETTINGS.load({'persistent': setting_source})
  if load_result.status not in [
       pg.setting.Persistor.SUCCESS, pg.setting.Persistor.PARTIAL_SUCCESS]:
    sys.exit(1)
  
  _run_plugin_noninteractive(gimpenums.RUN_NONINTERACTIVE, layer_tree)


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
  batcher = batcher_.Batcher(
    run_mode, layer_tree.image, SETTINGS['main/procedures'], SETTINGS['main/constraints'])
  
  try:
    batcher.run(item_tree=layer_tree, **utils_.get_settings_for_batcher(SETTINGS['main']))
  except exceptions.BatcherCancelError:
    pass


if __name__ == '__main__':
  pg.main()
