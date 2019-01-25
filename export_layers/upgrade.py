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
This module determines the current plug-in version and performs compatibility
updates if upgrading from an earlier version.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import pygtk
pygtk.require("2.0")
import gtk

from export_layers import pygimplib
from export_layers.pygimplib import pgsettingpersistor

from export_layers.gui import messages


MIN_VERSION_WITHOUT_CLEAN_REINSTALL = "3.3"


def upgrade(settings, prompt_on_clean_reinstall=False):
  if _is_fresh_start():
    _save_plugin_version(settings)
    return False
  
  current_version = pygimplib.config.PLUGIN_VERSION
  
  status, unused_ = pgsettingpersistor.SettingPersistor.load(
    [settings["main/plugin_version"]], [pygimplib.config.SOURCE_PERSISTENT])
  
  if (status == pgsettingpersistor.SettingPersistor.SUCCESS
      and settings["main/plugin_version"].value >= MIN_VERSION_WITHOUT_CLEAN_REINSTALL):
    _save_plugin_version(settings)
    return False
  
  if prompt_on_clean_reinstall:
    response = messages.display_message(
      _("Due to significant changes in the plug-in, settings need to be reset. Proceed?"),
      gtk.MESSAGE_WARNING,
      buttons=gtk.BUTTONS_YES_NO,
      button_response_id_to_focus=gtk.RESPONSE_NO)
    
    if response == gtk.RESPONSE_YES:
      clear_setting_sources(settings)
      return False
    else:
      return True
  else:
    clear_setting_sources(settings)
    return False


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
