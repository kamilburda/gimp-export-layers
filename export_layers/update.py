# -*- coding: utf-8 -*-
#
# This file is part of Export Layers.
#
# Copyright (C) 2013-2019 khalim19 <khalim19@gmail.com>
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

"""
This module provides necessary steps to update the plug-in to the latest version
(e.g. due to settings being reorganized or removed).
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import collections
import os
import shutil
import types

import pygtk
pygtk.require("2.0")
import gtk

from export_layers import pygimplib as pg

from export_layers.gui import messages


MIN_VERSION_WITHOUT_CLEAN_REINSTALL = pg.version.Version.parse("3.3")

_UPDATE_STATUSES = (FRESH_START, UPDATE, CLEAR_SETTINGS, ABORT) = (0, 1, 2, 3)


def update(settings, prompt_on_clear=False):
  """
  Update to the latest version of the plug-in. This includes renaming settings
  or replacing obsolete procedures.
  
  Return one of the following values:
  
  * `FRESH_START` - The plug-in was never used before or has no settings stored.
  
  * `UPDATE` - The plug-in was successfully updated to the latest version.
  
  * `CLEAR_SETTINGS` - An old version of the plug-in (incompatible with the
    changes in later versions) was used that required clearing stored settings.
    
  * `ABORT` - No update was performed. This value is returned if the user
    cancelled clearing settings interactively.
  
  If `prompt_on_clear` is `True` and the plug-in requires clearing settings,
  display a message dialog to prompt the user to proceed with clearing. If "No"
  is chosen, do not clear settings and return `ABORT`.
  """
  if _is_fresh_start():
    _save_plugin_version(settings)
    return FRESH_START
  
  status, unused_ = pg.setting.Persistor.load(
    [settings["main/plugin_version"]], [pg.config.PERSISTENT_SOURCE])
  
  previous_version = pg.version.Version.parse(settings["main/plugin_version"].value)
  
  if (status == pg.setting.Persistor.SUCCESS
      and previous_version >= MIN_VERSION_WITHOUT_CLEAN_REINSTALL):
    _save_plugin_version(settings)
    
    current_version = pg.version.Version.parse(pg.config.PLUGIN_VERSION)
    handle_update(settings, _UPDATE_HANDLERS, previous_version, current_version)
    
    return UPDATE
  
  if prompt_on_clear:
    response = messages.display_message(
      _("Due to significant changes in the plug-in, settings need to be reset. Proceed?"),
      gtk.MESSAGE_WARNING,
      buttons=gtk.BUTTONS_YES_NO,
      button_response_id_to_focus=gtk.RESPONSE_NO)
    
    if response == gtk.RESPONSE_YES:
      clear_setting_sources(settings)
      return CLEAR_SETTINGS
    else:
      return ABORT
  else:
    clear_setting_sources(settings)
    return CLEAR_SETTINGS


def clear_setting_sources(settings):
  pg.setting.Persistor.clear([pg.config.SESSION_SOURCE, pg.config.PERSISTENT_SOURCE])
  
  _save_plugin_version(settings)


def handle_update(settings, update_handlers, previous_version, current_version):
  for version_str, update_handler in update_handlers.items():
    if previous_version < pg.version.Version.parse(version_str) <= current_version:
      update_handler(settings)


def rename_settings(settings_to_rename):
  for source in [pg.config.SESSION_SOURCE, pg.config.PERSISTENT_SOURCE]:
    data_dict = source.read_dict()
    
    if data_dict:
      for orig_setting_name, new_setting_name in settings_to_rename:
        if orig_setting_name in data_dict:
          data_dict[new_setting_name] = data_dict[orig_setting_name]
          del data_dict[orig_setting_name]
      
      source.write_dict(data_dict)


def replace_field_arguments_in_pattern(
      pattern, field_regexes_and_argument_values_and_replacements):
  
  def _replace_field_arguments(field_arguments, values_and_replacements):
    replaced_field_arguments = []
    
    for argument in field_arguments:
      replaced_argument = argument
      
      for value, replacement in values_and_replacements:
        replaced_argument = replaced_argument.replace(value, replacement)
      
      replaced_field_arguments.append(replaced_argument)
    
    return replaced_field_arguments
  
  string_pattern = pg.path.StringPattern(
    pattern,
    fields={
      field_regex: lambda *args: None
      for field_regex in field_regexes_and_argument_values_and_replacements})
  
  processed_pattern_parts = []
  
  for part in string_pattern.pattern_parts:
    if isinstance(part, types.StringTypes):
      processed_pattern_parts.append(part)
    else:
      field_regex = part[0]
      
      if field_regex not in field_regexes_and_argument_values_and_replacements:
        continue
      
      field_components = [field_regex]
      
      if len(part) > 1:
        field_components.append(
          _replace_field_arguments(
            part[1],
            field_regexes_and_argument_values_and_replacements[field_regex]))
      
      processed_pattern_parts.append(field_components)
  
  return pg.path.StringPattern.reconstruct_pattern(processed_pattern_parts)


def _is_fresh_start():
  return not pg.config.PERSISTENT_SOURCE.has_data()


def _save_plugin_version(settings):
  settings["main/plugin_version"].reset()
  pg.setting.Persistor.save(
    [settings["main/plugin_version"]], [pg.config.PERSISTENT_SOURCE])


def _remove_obsolete_pygimplib_files():
  for filename in os.listdir(pg.PYGIMPLIB_DIRPATH):
    filepath = os.path.join(pg.PYGIMPLIB_DIRPATH, filename)
    
    if filename.startswith("pg") or filename.startswith("_pg"):
      if os.path.isfile(filepath):
        try:
          os.remove(filepath)
        except Exception:
          pass
      elif os.path.isdir(filepath):
        shutil.rmtree(filepath, ignore_errors=True)
    elif filename == "lib":
      if os.path.isdir(filepath):
        shutil.rmtree(filepath, ignore_errors=True)


def _remove_obsolete_plugin_files():
  gui_package_dirpath = os.path.join(pg.config.PLUGIN_SUBDIRPATH, "gui")
  
  for filename in os.listdir(gui_package_dirpath):
    filepath = os.path.join(gui_package_dirpath, filename)
    
    if filename.startswith("gui_") and os.path.isfile(filepath):
      try:
        os.remove(filepath)
      except Exception:
        pass


def _update_to_3_3_1(settings):
  rename_settings([
    ("gui/export_name_preview_sensitive",
     "gui/name_preview_sensitive"),
    ("gui/export_image_preview_sensitive",
     "gui/image_preview_sensitive"),
    ("gui/export_image_preview_automatic_update",
     "gui/image_preview_automatic_update"),
    ("gui/export_image_preview_automatic_update_if_below_maximum_duration",
     "gui/image_preview_automatic_update_if_below_maximum_duration"),
    ("gui_session/export_name_preview_layers_collapsed_state",
     "gui_session/name_preview_layers_collapsed_state"),
    ("gui_session/export_image_preview_displayed_layers",
     "gui_session/image_preview_displayed_layers"),
    ("gui_persistent/export_name_preview_layers_collapsed_state",
     "gui_persistent/name_preview_layers_collapsed_state"),
    ("gui_persistent/export_image_preview_displayed_layers",
     "gui_persistent/image_preview_displayed_layers"),
  ])
  
  settings["main/layer_filename_pattern"].load()
  
  settings["main/layer_filename_pattern"].set_value(
    replace_field_arguments_in_pattern(
      settings["main/layer_filename_pattern"].value,
      {
        "layer name": [("keep extension", "%e"), ("keep only identical extension", "%i")],
        "image name": [("keep extension", "%e")],
        "layer path": [("$$", "%c")],
        "tags": [("$$", "%t")],
      }))
  
  settings["main/layer_filename_pattern"].save()


def _update_to_3_4(settings):
  _remove_obsolete_pygimplib_files()
  _remove_obsolete_plugin_files()


_UPDATE_HANDLERS = collections.OrderedDict([
  ("3.3.1", _update_to_3_3_1),
  ("3.4", _update_to_3_4),
])
