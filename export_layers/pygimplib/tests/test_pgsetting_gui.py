# -*- coding: utf-8 -*-
#
# Copyright (C) 2014-2018 khalim19
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
from .. import pgsetting


def test_basic_settings_and_gui():
  test_settings_and_gui(_get_basic_settings())


def test_array_settings_and_gui():
  test_settings_and_gui(_get_array_settings())


def test_settings_and_gui(setting_items):
  settings = []
  
  for item in setting_items:
    setting_type = item[1]
    setting_type_args = [item[0]] + list(item[2:])
    
    for gui_type in setting_type._ALLOWED_GUI_TYPES:
      settings.append(setting_type(*setting_type_args, gui_type=gui_type))
  
  dialog = gtk.Dialog()
  
  vbox = gtk.VBox()
  vbox.set_spacing(5)
  
  SETTING_TYPE_LABEL_WIDTH = 100
  SETTING_GUI_ELEMENT_WIDTH = 400
  SETTING_VALUE_LABEL_WIDTH = 150
  SETTING_VALUE_CHANGED_CALL_COUNT_LABEL_WIDTH = 50
  
  hbox_labels = gtk.HBox()
  hbox_labels.set_spacing(5)
  
  setting_type_title_label = gtk.Label("Type")
  setting_type_title_label.set_alignment(0.0, 0.5)
  setting_type_title_label.set_size_request(SETTING_TYPE_LABEL_WIDTH, -1)
  hbox_labels.pack_start(setting_type_title_label, fill=True, expand=True)
  
  setting_gui_title_label = gtk.Label("GUI")
  setting_gui_title_label.set_alignment(0.0, 0.5)
  setting_gui_title_label.set_size_request(SETTING_GUI_ELEMENT_WIDTH, -1)
  hbox_labels.pack_start(setting_gui_title_label, fill=True, expand=True)
  
  setting_value_title_label = gtk.Label("Value")
  setting_value_title_label.set_alignment(0.0, 0.5)
  setting_value_title_label.set_size_request(SETTING_VALUE_LABEL_WIDTH, -1)
  hbox_labels.pack_start(setting_value_title_label, fill=True, expand=True)
  
  setting_call_count_title_label = gtk.Label("Call count")
  setting_call_count_title_label.set_alignment(0.0, 0.5)
  setting_call_count_title_label.set_size_request(
    SETTING_VALUE_CHANGED_CALL_COUNT_LABEL_WIDTH, -1)
  hbox_labels.pack_start(setting_call_count_title_label, fill=True, expand=True)
  
  vbox.pack_start(hbox_labels, fill=True, expand=True)
  
  for setting in settings:
    setting_type_label = gtk.Label(setting.display_name)
    setting_type_label.set_alignment(0.0, 0.5)
    setting_type_label.set_size_request(SETTING_TYPE_LABEL_WIDTH, -1)
    
    setting.set_gui()
    setting.gui.element.set_size_request(SETTING_GUI_ELEMENT_WIDTH, -1)
    
    setting_value_label = gtk.Label()
    setting_value_label.set_alignment(0.0, 0.5)
    setting_value_label.set_size_request(SETTING_VALUE_LABEL_WIDTH, -1)
    
    setting_value_changed_call_count_label = gtk.Label(b"0")
    setting_value_changed_call_count_label.set_alignment(0.0, 0.5)
    setting_value_changed_call_count_label.set_size_request(
      SETTING_VALUE_CHANGED_CALL_COUNT_LABEL_WIDTH, -1)
    
    _set_setting_value_label(setting, setting_value_label)
    
    setting.connect_event(
      "value-changed",
      _on_setting_value_changed,
      setting_value_label,
      setting_value_changed_call_count_label)
    
    hbox = gtk.HBox()
    hbox.set_spacing(5)
    hbox.pack_start(setting_type_label, fill=True, expand=True)
    hbox.pack_start(setting.gui.element, fill=True, expand=True)
    hbox.pack_start(setting_value_label, fill=True, expand=True)
    hbox.pack_start(setting_value_changed_call_count_label, fill=True, expand=True)
    
    vbox.pack_start(hbox, fill=True, expand=True)
  
  reset_button = dialog.add_button("Reset", gtk.RESPONSE_OK)
  reset_button.connect("clicked", _on_reset_button_clicked, settings)
  
  scrolled_window = gtk.ScrolledWindow()
  scrolled_window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
  scrolled_window.add_with_viewport(vbox)
  scrolled_window.get_child().set_shadow_type(gtk.SHADOW_NONE)
  
  dialog.vbox.pack_start(scrolled_window, fill=True, expand=True)
  dialog.set_border_width(5)
  dialog.set_default_size(800, 800)
  
  dialog.show_all()


def _get_basic_settings():
  image = _create_test_image()
  
  return [
    ("integer", pgsetting.SettingTypes.integer, 0),
    ("float", pgsetting.SettingTypes.float, 0),
    ("boolean", pgsetting.SettingTypes.boolean, False),
    ("enumerated",
     pgsetting.SettingTypes.enumerated,
     "non_interactive",
     [("interactive", "RUN-INTERACTIVE"),
      ("non_interactive", "RUN-NONINTERACTIVE"),
      ("run_with_last_vals", "RUN-WITH-LAST-VALS")],),
    ("string", pgsetting.SettingTypes.string, "Test"),
    
    ("image", pgsetting.SettingTypes.image, image),
    ("drawable", pgsetting.SettingTypes.drawable, image.layers[0]),
    ("layer", pgsetting.SettingTypes.layer, image.layers[0]),
    ("channel", pgsetting.SettingTypes.channel, image.channels[0]),
    ("selection", pgsetting.SettingTypes.selection, pdb.gimp_image_get_selection(image)),
    ("vectors", pgsetting.SettingTypes.vectors, image.vectors[0]),
    
    ("color", pgsetting.SettingTypes.color, gimpcolor.RGB(0, 0, 255)),
    ("parasite", pgsetting.SettingTypes.parasite, gimp.Parasite("Test", 0, "data")),
    ("display", pgsetting.SettingTypes.display, gimp.Display(image)),
    ("pdb_status", pgsetting.SettingTypes.pdb_status, "PDB_SUCCESS"),
    
    ("file_extension", pgsetting.SettingTypes.file_extension, "png"),
    ("directory", pgsetting.SettingTypes.directory, gimp.directory),
    
    ("brush", pgsetting.SettingTypes.brush, ()),
    ("font", pgsetting.SettingTypes.font, ""),
    ("gradient", pgsetting.SettingTypes.gradient, ""),
    ("palette", pgsetting.SettingTypes.palette, ""),
    ("pattern", pgsetting.SettingTypes.pattern, ""),
  ]


def _get_array_settings():
  return [
    ("array_of_booleans",
     pgsetting.SettingTypes.array,
     (True, False, True),
     pgsetting.SettingTypes.boolean,
     True,
     3,
     10),
    
    ("array_of_floats",
     pgsetting.SettingTypes.array,
     (5.0, 10.0, 30.0),
     pgsetting.SettingTypes.float,
     1.0,
     3,
     10),
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
