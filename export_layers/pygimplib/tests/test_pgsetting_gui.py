# -*- coding: utf-8 -*-
#
# Copyright (C) 2014-2019 khalim19
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
This module creates a test GUI for all available setting types and exercises
"setting value changed" events connected to the GUI elements.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import pygtk
pygtk.require("2.0")
import gtk

import gimp
from gimp import pdb
import gimpcolor
import gimpenums

from .. import pgconstants
from .. import pggui
from .. import pgsetting


def test_basic_settings_and_gui():
  test_settings_and_gui(_get_basic_settings())


def test_array_settings_and_gui():
  test_settings_and_gui(_get_array_settings())


def test_settings_and_gui(setting_items):
  pggui.set_gui_excepthook("Test GUI for Settings", "")
  pggui.set_gui_excepthook_additional_callback(_display_message_on_setting_value_error)
  
  settings = []
  
  for item in setting_items:
    setting_type = item.pop("type")
    
    for gui_type in setting_type.get_allowed_gui_types():
      item["gui_type"] = gui_type
      settings.append(setting_type(**item))
  
  dialog = gtk.Dialog()
  
  SETTING_GUI_ELEMENT_WIDTH = 450
  SETTING_VALUE_LABEL_WIDTH = 150
  
  setting_type_title_label = gtk.Label("<b>Type</b>")
  setting_type_title_label.set_use_markup(True)
  setting_type_title_label.set_alignment(0.0, 0.5)
  
  setting_gui_title_label = gtk.Label("<b>GUI</b>")
  setting_gui_title_label.set_use_markup(True)
  setting_gui_title_label.set_alignment(0.0, 0.5)
  
  setting_value_title_label = gtk.Label("<b>Value</b>")
  setting_value_title_label.set_use_markup(True)
  setting_value_title_label.set_alignment(0.0, 0.5)
  
  setting_call_count_title_label = gtk.Label("<b>Call count</b>")
  setting_call_count_title_label.set_use_markup(True)
  setting_call_count_title_label.set_alignment(0.0, 0.5)
  
  table = gtk.Table(homogeneous=False)
  table.set_row_spacings(6)
  table.set_col_spacings(5)
  
  table.attach(setting_type_title_label, 0, 1, 0, 1, yoptions=0)
  table.attach(setting_gui_title_label, 1, 2, 0, 1, yoptions=0)
  table.attach(setting_value_title_label, 2, 3, 0, 1, yoptions=0)
  table.attach(setting_call_count_title_label, 3, 4, 0, 1, yoptions=0)
  
  for i, setting in enumerate(settings):
    setting_type_label = gtk.Label(setting.display_name)
    setting_type_label.set_alignment(0.0, 0.5)
    
    setting.set_gui()
    setting.gui.element.set_property("width-request", SETTING_GUI_ELEMENT_WIDTH)
    
    _check_setting_gui_interface(setting)
    
    setting_value_label = gtk.Label()
    setting_value_label.set_alignment(0.0, 0.5)
    setting_value_label.set_property("width-request", SETTING_VALUE_LABEL_WIDTH)
    
    setting_value_changed_call_count_label = gtk.Label(b"0")
    setting_value_changed_call_count_label.set_alignment(0.0, 0.5)
    
    _set_setting_value_label(setting, setting_value_label)
    
    setting.connect_event(
      "value-changed",
      _on_setting_value_changed,
      setting_value_label,
      setting_value_changed_call_count_label)
    
    table.attach(setting_type_label, 0, 1, i + 1, i + 2)
    table.attach(setting.gui.element, 1, 2, i + 1, i + 2)
    table.attach(setting_value_label, 2, 3, i + 1, i + 2)
    table.attach(setting_value_changed_call_count_label, 3, 4, i + 1, i + 2)
  
  reset_button = dialog.add_button("Reset", gtk.RESPONSE_OK)
  reset_button.connect("clicked", _on_reset_button_clicked, settings)
  
  scrolled_window = gtk.ScrolledWindow()
  scrolled_window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
  scrolled_window.add_with_viewport(table)
  scrolled_window.get_child().set_shadow_type(gtk.SHADOW_NONE)
  
  dialog.vbox.pack_start(scrolled_window, expand=True, fill=True)
  dialog.set_border_width(5)
  dialog.set_default_size(850, 800)
  
  dialog.show_all()


def _get_basic_settings():
  image = _create_test_image()
  
  return [
    {
      "name": "integer",
      "type": pgsetting.SettingTypes.integer,
    },
    {
      "name": "float",
      "type": pgsetting.SettingTypes.float,
    },
    {
      "name": "boolean",
      "type": pgsetting.SettingTypes.boolean,
    },
    {
     "name": "enumerated",
     "type": pgsetting.SettingTypes.enumerated,
     "items": [("interactive", "RUN-INTERACTIVE"),
      ("non_interactive", "RUN-NONINTERACTIVE"),
      ("run_with_last_vals", "RUN-WITH-LAST-VALS")],
     "default_value": "non_interactive",
    },
    {
      "name": "string",
      "type": pgsetting.SettingTypes.string,
      "default_value": "Test",
    },
    
    {
      "name": "image",
      "type": pgsetting.SettingTypes.image,
      "default_value": image,
    },
    {
      "name": "item",
      "type": pgsetting.SettingTypes.item,
      "default_value": image.layers[0],
    },
    {
      "name": "drawable",
      "type": pgsetting.SettingTypes.drawable,
      "default_value": image.layers[0],
    },
    {
      "name": "layer",
      "type": pgsetting.SettingTypes.layer,
      "default_value": image.layers[0],
    },
    {
      "name": "channel",
      "type": pgsetting.SettingTypes.channel,
      "default_value": image.channels[0],
    },
    {
      "name": "selection",
      "type": pgsetting.SettingTypes.selection,
      "default_value": pdb.gimp_image_get_selection(image),
    },
    {
      "name": "vectors",
      "type": pgsetting.SettingTypes.vectors,
      "default_value": image.vectors[0],
    },
    
    {
      "name": "color",
      "type": pgsetting.SettingTypes.color,
    },
    {
      "name": "parasite",
      "type": pgsetting.SettingTypes.parasite,
    },
    {
      "name": "display",
      "type": pgsetting.SettingTypes.display,
      "default_value": gimp.Display(image),
    },
    {
      "name": "pdb_status",
      "type": pgsetting.SettingTypes.pdb_status,
    },
    
    {
      "name": "file_extension",
      "type": pgsetting.SettingTypes.file_extension,
      "default_value": "png",
    },
    {
      "name": "directory",
      "type": pgsetting.SettingTypes.directory,
    },
    
    {
      "name": "brush",
      "type": pgsetting.SettingTypes.brush,
    },
    {
      "name": "font",
      "type": pgsetting.SettingTypes.font,
    },
    {
      "name": "gradient",
      "type": pgsetting.SettingTypes.gradient,
    },
    {
      "name": "palette",
      "type": pgsetting.SettingTypes.palette,
    },
    {
      "name": "pattern",
      "type": pgsetting.SettingTypes.pattern,
    },
  ]


def _get_array_settings():
  return [
    {
     "type": pgsetting.SettingTypes.array,
     "name": "array_of_booleans",
     "default_value": (True, False, True),
     "element_type": pgsetting.SettingTypes.boolean,
     "element_default_value": True,
     "min_size": 3,
     "max_size": 10,
    },
    
    {
     "type": pgsetting.SettingTypes.array,
     "name": "array_of_floats",
     "default_value": (5.0, 10.0, 30.0),
     "element_type": pgsetting.SettingTypes.float,
     "element_default_value": 1.0,
     "min_size": 3,
     "max_size": 10,
    },
    
    {
     "type": pgsetting.SettingTypes.array,
     "name": "2D_array_of_floats",
     "display_name": "2D array of floats",
     "default_value": ((1.0, 5.0, 10.0), (2.0, 15.0, 25.0), (-5.0, 10.0, 40.0)),
     "element_type": pgsetting.SettingTypes.array,
     "element_default_value": (0.0, 0.0, 0.0),
     "min_size": 3,
     "max_size": 10,
     "element_element_type": pgsetting.SettingTypes.float,
     "element_element_default_value": 1.0,
     "element_min_size": 1,
     "element_max_size": 3,
    },
  ]


def _on_setting_value_changed(
      setting, setting_value_label, setting_value_changed_call_count_label):
  _set_setting_value_label(setting, setting_value_label)
  
  setting_value_changed_call_count_label.set_label(
    str(int(setting_value_changed_call_count_label.get_label()) + 1))


def _on_reset_button_clicked(button, settings):
  for setting in settings:
    setting.reset()


def _set_setting_value_label(setting, setting_value_label):
  if isinstance(setting, pgsetting.ParasiteSetting):
    setting_value_str = "'{}', {}, '{}'".format(
      setting.value.name,
      setting.value.flags,
      setting.value.data).encode(pgconstants.GTK_CHARACTER_ENCODING)
  else:
    setting_value_str = str(setting.value).encode(pgconstants.GTK_CHARACTER_ENCODING)
  
  setting_value_label.set_label(setting_value_str)


def _check_setting_gui_interface(setting):
  setting.gui.set_sensitive(True)
  setting.gui.set_visible(True)
  
  assert setting.gui.get_sensitive()
  assert setting.gui.get_visible()


def _create_test_image():
  image = pdb.gimp_image_new(100, 100, gimpenums.RGB)
  
  layers = [
    pdb.gimp_layer_new(
      image, 50, 20, gimpenums.RGBA_IMAGE, "Layer 1", 100.0, gimpenums.NORMAL_MODE),
    pdb.gimp_layer_new(
      image, 10, 10, gimpenums.RGBA_IMAGE, "Layer 2", 50.0, gimpenums.DISSOLVE_MODE),
  ]
  
  channels = [
    pdb.gimp_channel_new(image, 100, 100, "Channel 1", 100.0, gimpcolor.RGB(0, 0, 0)),
    pdb.gimp_channel_new(image, 100, 100, "Channel 2", 50.0, gimpcolor.RGB(1, 0, 0)),
  ]
  
  vectors_list = [
    pdb.gimp_vectors_new(image, "Vectors 1"),
    pdb.gimp_vectors_new(image, "Vectors 2"),
  ]
  
  for layer, channel, vectors in reversed(list(zip(layers, channels, vectors_list))):
    pdb.gimp_image_insert_layer(image, layer, None, 0)
    pdb.gimp_image_insert_channel(image, channel, None, 0)
    pdb.gimp_image_insert_vectors(image, vectors, None, 0)
  
  return image


def _display_message_on_setting_value_error(exc_type, exc_value, exc_traceback):
  if issubclass(exc_type, pgsetting.SettingValueError):
    gimp.message(str(exc_value).encode(pgconstants.GIMP_CHARACTER_ENCODING))
    return True
  else:
    return False
