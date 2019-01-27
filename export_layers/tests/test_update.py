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

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import collections

import pygtk
pygtk.require("2.0")
import gtk

import unittest

import mock
import parameterized

from export_layers import pygimplib
from export_layers.pygimplib import pgconstants
from export_layers.pygimplib import pgsetting
from export_layers.pygimplib import pgsettinggroup
from export_layers.pygimplib import pgsettingpersistor
from export_layers.pygimplib import pgversion

from export_layers.pygimplib.tests import stubs_gimp

from .. import update

pygimplib.init()


@mock.patch(
  pgconstants.PYGIMPLIB_MODULE_PATH + ".pgsettingsources.gimpshelf.shelf",
  new_callable=stubs_gimp.ShelfStub)
@mock.patch(
  pgconstants.PYGIMPLIB_MODULE_PATH + ".pgsettingsources.gimp",
  new_callable=stubs_gimp.GimpModuleStub)
@mock.patch("export_layers.update.handle_update")
class TestUpdate(unittest.TestCase):
  
  def setUp(self):
    self.settings = pgsettinggroup.create_groups({
      "name": "all_settings",
      "groups": [
        {
          "name": "main",
          "setting_attributes": {
            "setting_sources": [pygimplib.config.SOURCE_PERSISTENT]},
        }
      ]
    })
    
    self.current_version = "3.3"
    self.new_version = "3.4"
    self.old_incompatible_version = "0.1"
    
    self.settings["main"].add([
      {
        "type": pgsetting.SettingTypes.generic,
        "name": "plugin_version",
        "default_value": self.new_version,
        "pdb_type": None,
        "gui_type": None,
      },
      {
        "type": pgsetting.SettingTypes.generic,
        "name": "test_setting",
        "default_value": "test",
        "pdb_type": None,
        "gui_type": None,
      },
    ])
  
  def test_fresh_start_stores_new_version(
        self, mock_handle_update, mock_persistent_source, mock_session_source):
    self.assertFalse(pygimplib.config.SOURCE_PERSISTENT.has_data())
    
    status = update.update(self.settings)
    
    self.assertEqual(status, update.FRESH_START)
    self.assertEqual(self.settings["main/plugin_version"].value, self.new_version)
    
    status, unused_ = self.settings["main/plugin_version"].load()
    self.assertEqual(self.settings["main/plugin_version"].value, self.new_version)
    self.assertEqual(status, pgsettingpersistor.SettingPersistor.SUCCESS)
  
  def test_minimum_version_or_later_is_overwritten_by_new_version(
        self, mock_handle_update, mock_persistent_source, mock_session_source):
    self.settings["main/plugin_version"].set_value(self.current_version)
    self.settings["main/plugin_version"].save()
    
    status = update.update(self.settings)
    
    self.assertEqual(status, update.UPDATE)
    self.assertEqual(self.settings["main/plugin_version"].value, self.new_version)
  
  def test_persistent_source_has_data_but_not_version_clears_setting_sources(
        self, mock_handle_update, mock_persistent_source, mock_session_source):
    self.settings["main/test_setting"].save()
    
    status = update.update(self.settings)
    
    self.assertEqual(status, update.CLEAR_SETTINGS)
    self.assertEqual(self.settings["main/plugin_version"].value, self.new_version)
  
  def test_less_than_minimum_version_clears_setting_sources(
        self, mock_handle_update, mock_persistent_source, mock_session_source):
    self.settings["main/plugin_version"].set_value(self.old_incompatible_version)
    self.settings["main"].save()
    
    status = update.update(self.settings)
    
    self.assertEqual(status, update.CLEAR_SETTINGS)
    self.assertEqual(self.settings["main/plugin_version"].value, self.new_version)
    self.assertEqual(
      self.settings["main/test_setting"].load()[0],
      pgsettingpersistor.SettingPersistor.NOT_ALL_SETTINGS_FOUND)
  
  @mock.patch("export_layers.gui.messages.display_message")
  def test_prompt_on_clear_positive_response(
        self,
        mock_display_message,
        mock_handle_update,
        mock_persistent_source,
        mock_session_source):
    mock_display_message.return_value = gtk.RESPONSE_YES
    
    self.settings["main/plugin_version"].set_value(self.old_incompatible_version)
    self.settings["main"].save()
    
    status = update.update(self.settings, prompt_on_clear=True)
    self.assertEqual(status, update.CLEAR_SETTINGS)
    self.assertEqual(self.settings["main/plugin_version"].value, self.new_version)
    self.assertEqual(
      self.settings["main/test_setting"].load()[0],
      pgsettingpersistor.SettingPersistor.NOT_ALL_SETTINGS_FOUND)
  
  @mock.patch("export_layers.gui.messages.display_message")
  def test_prompt_on_clear_negative_response(
        self,
        mock_display_message,
        mock_handle_update,
        mock_persistent_source,
        mock_session_source):
    mock_display_message.return_value = gtk.RESPONSE_NO
    
    self.settings["main/plugin_version"].set_value(self.old_incompatible_version)
    self.settings["main"].save()
    
    status = update.update(self.settings, prompt_on_clear=True)
    self.assertEqual(status, update.ABORT)
    self.assertEqual(
      self.settings["main/plugin_version"].value, self.old_incompatible_version)
    self.assertEqual(
      self.settings["main/test_setting"].load()[0],
      pgsettingpersistor.SettingPersistor.SUCCESS)
  

class TestHandleUpdate(unittest.TestCase):
  
  def setUp(self):
    self.update_handlers = collections.OrderedDict([
      ("3.3.1", lambda *args, **kwargs: self._executed_handlers.append("3.3.1")),
      ("3.4", lambda *args, **kwargs: self._executed_handlers.append("3.4")),
      ("3.5", lambda *args, **kwargs: self._executed_handlers.append("3.5")),
    ])
    
    self._executed_handlers = []
    
    self.settings = pgsettinggroup.SettingGroup("settings")
  
  @parameterized.parameterized.expand([
    ["previous_version_earlier_than_all_handlers_execute_one_handler",
     "3.3", "3.3.1", ["3.3.1"]],
    ["previous_version_earlier_than_all_handlers_execute_multiple_handlers",
     "3.3", "3.4", ["3.3.1", "3.4"]],
    ["equal_previous_and_current_version_execute_no_handler",
     "3.5", "3.5", []],
    ["equal_previous_and_current_version_and_globally_not_latest_execute_no_handler",
     "3.3.1", "3.3.1", []],
    ["previous_version_equal_to_first_handler_execute_one_handler",
     "3.3.1", "3.4", ["3.4"]],
    ["previous_version_equal_to_latest_handler_execute_no_handler",
     "3.5", "3.6", []],
    ["previous_greater_than_handlers_execute_no_handler",
     "3.6", "3.6", []],
  ])
  def test_handle_update(
        self,
        test_case_name_suffix,
        previous_version_str,
        current_version_str,
        executed_handlers):
    self._executed_handlers = []
    
    update.handle_update(
      self.settings,
      self.update_handlers,
      pgversion.Version.parse(previous_version_str),
      pgversion.Version.parse(current_version_str))
    
    self.assertEqual(self._executed_handlers, executed_handlers)
