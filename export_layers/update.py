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

import pygtk
pygtk.require("2.0")
import gtk

from export_layers import pygimplib
from export_layers.pygimplib import pgsettingpersistor
from export_layers.pygimplib import pgversion

from export_layers.gui import messages


MIN_VERSION_WITHOUT_CLEAN_REINSTALL = pgversion.Version.parse("3.3")

_UPDATE_STATUSES = (FRESH_START, UPDATE, CLEAR_SETTINGS, ABORT) = (0, 1, 2, 3)


def update(settings, prompt_on_clear=False):
  """
  Update to the latest version of the plug-in.
  
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
  
  current_version = pgversion.Version.parse(pygimplib.config.PLUGIN_VERSION)
  
  status, unused_ = pgsettingpersistor.SettingPersistor.load(
    [settings["main/plugin_version"]], [pygimplib.config.SOURCE_PERSISTENT])
  
  if (status == pgsettingpersistor.SettingPersistor.SUCCESS
      and (pgversion.Version.parse(settings["main/plugin_version"].value)
           >= MIN_VERSION_WITHOUT_CLEAN_REINSTALL)):
    _save_plugin_version(settings)
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
  pgsettingpersistor.SettingPersistor.clear(
    [pygimplib.config.SOURCE_SESSION, pygimplib.config.SOURCE_PERSISTENT])
  
  _save_plugin_version(settings)


def _is_fresh_start():
  return not pygimplib.config.SOURCE_PERSISTENT.has_data()


def _save_plugin_version(settings):
  settings["main/plugin_version"].reset()
  pgsettingpersistor.SettingPersistor.save(
    [settings["main/plugin_version"]], [pygimplib.config.SOURCE_PERSISTENT])
