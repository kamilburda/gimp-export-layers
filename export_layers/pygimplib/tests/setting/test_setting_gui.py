# -*- coding: utf-8 -*-

"""Test GUI for all available setting types.

The GUI also exercises 'setting value changed' events connected to the GUI
elements.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import pygtk
pygtk.require('2.0')
import gtk

import gimp
from gimp import pdb
import gimpcolor
import gimpenums

from ... import gui as pggui
from ... import utils as pgutils

from ...setting import settings as settings_


def test_basic_settings_and_gui():
  test_settings_and_gui(_get_basic_settings())


def test_array_settings_and_gui():
  test_settings_and_gui(_get_array_settings())


def test_settings_and_gui(setting_items):
  pggui.set_gui_excepthook('Test GUI for Settings', '')
  pggui.set_gui_excepthook_additional_callback(_display_message_on_setting_value_error)
  
  settings = []
  
  for item in setting_items:
    setting_type = item.pop('type')
    
    for gui_type in setting_type.get_allowed_gui_types():
      item['gui_type'] = gui_type
      settings.append(setting_type(**item))
  
  dialog = gtk.Dialog()
  
  SETTING_GUI_ELEMENT_WIDTH = 450
  SETTING_VALUE_LABEL_WIDTH = 150
  
  setting_type_title_label = gtk.Label('<b>Type</b>')
  setting_type_title_label.set_use_markup(True)
  setting_type_title_label.set_alignment(0.0, 0.5)
  
  setting_gui_title_label = gtk.Label('<b>GUI</b>')
  setting_gui_title_label.set_use_markup(True)
  setting_gui_title_label.set_alignment(0.0, 0.5)
  
  setting_value_title_label = gtk.Label('<b>Value</b>')
  setting_value_title_label.set_use_markup(True)
  setting_value_title_label.set_alignment(0.0, 0.5)
  
  setting_call_count_title_label = gtk.Label('<b>Call count</b>')
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
    setting.gui.element.set_property('width-request', SETTING_GUI_ELEMENT_WIDTH)
    
    _check_setting_gui_interface(setting)
    
    setting_value_label = gtk.Label()
    setting_value_label.set_alignment(0.0, 0.5)
    setting_value_label.set_property('width-request', SETTING_VALUE_LABEL_WIDTH)
    
    setting_value_changed_call_count_label = gtk.Label(b'0')
    setting_value_changed_call_count_label.set_alignment(0.0, 0.5)
    
    _set_setting_value_label(setting, setting_value_label)
    
    setting.connect_event(
      'value-changed',
      _on_setting_value_changed,
      setting_value_label,
      setting_value_changed_call_count_label)
    
    table.attach(setting_type_label, 0, 1, i + 1, i + 2)
    table.attach(setting.gui.element, 1, 2, i + 1, i + 2)
    table.attach(setting_value_label, 2, 3, i + 1, i + 2)
    table.attach(setting_value_changed_call_count_label, 3, 4, i + 1, i + 2)
  
  reset_button = dialog.add_button('Reset', gtk.RESPONSE_OK)
  reset_button.connect('clicked', _on_reset_button_clicked, settings)
  
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
      'name': 'integer',
      'type': 'integer',
    },
    {
      'name': 'float',
      'type': 'float',
    },
    {
      'name': 'boolean',
      'type': 'boolean',
    },
    {
     'name': 'options',
     'type': 'options',
     'items': [('interactive', 'RUN-INTERACTIVE'),
      ('non_interactive', 'RUN-NONINTERACTIVE'),
      ('run_with_last_vals', 'RUN-WITH-LAST-VALS')],
     'default_value': 'non_interactive',
    },
    {
      'name': 'string',
      'type': 'string',
      'default_value': 'Test',
    },
    
    {
      'name': 'image',
      'type': 'image',
      'default_value': image,
    },
    {
      'name': 'item',
      'type': 'item',
      'default_value': image.layers[0],
    },
    {
      'name': 'drawable',
      'type': 'drawable',
      'default_value': image.layers[0],
    },
    {
      'name': 'layer',
      'type': 'layer',
      'default_value': image.layers[0],
    },
    {
      'name': 'channel',
      'type': 'channel',
      'default_value': image.channels[0],
    },
    {
      'name': 'selection',
      'type': 'selection',
      'default_value': pdb.gimp_image_get_selection(image),
    },
    {
      'name': 'vectors',
      'type': 'vectors',
      'default_value': image.vectors[0],
    },
    
    {
      'name': 'color',
      'type': 'color',
    },
    {
      'name': 'parasite',
      'type': 'parasite',
    },
    {
      'name': 'display',
      'type': 'display',
      'default_value': gimp.Display(image),
    },
    {
      'name': 'pdb_status',
      'type': 'pdb_status',
    },
    
    {
      'name': 'file_extension',
      'type': 'file_extension',
      'default_value': 'png',
    },
    {
      'name': 'directory',
      'type': 'directory',
    },
    
    {
      'name': 'brush',
      'type': 'brush',
    },
    {
      'name': 'font',
      'type': 'font',
    },
    {
      'name': 'gradient',
      'type': 'gradient',
    },
    {
      'name': 'palette',
      'type': 'palette',
    },
    {
      'name': 'pattern',
      'type': 'pattern',
    },
  ]


def _get_array_settings():
  return [
    {
     'type': 'array',
     'name': 'array_of_booleans',
     'default_value': (True, False, True),
     'element_type': 'boolean',
     'element_default_value': True,
     'min_size': 3,
     'max_size': 10,
    },
    
    {
     'type': 'array',
     'name': 'array_of_floats',
     'default_value': (5.0, 10.0, 30.0),
     'element_type': 'float',
     'element_default_value': 1.0,
     'min_size': 3,
     'max_size': 10,
    },
    
    {
     'type': 'array',
     'name': '2D_array_of_floats',
     'display_name': '2D array of floats',
     'default_value': ((1.0, 5.0, 10.0), (2.0, 15.0, 25.0), (-5.0, 10.0, 40.0)),
     'element_type': 'array',
     'element_default_value': (0.0, 0.0, 0.0),
     'min_size': 3,
     'max_size': 10,
     'element_element_type': 'float',
     'element_element_default_value': 1.0,
     'element_min_size': 1,
     'element_max_size': 3,
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
  if isinstance(setting, settings_.ParasiteSetting):
    setting_value_str = pgutils.safe_encode_gtk('"{}", {}, "{}"'.format(
      setting.value.name,
      setting.value.flags,
      setting.value.data))
  else:
    setting_value_str = pgutils.safe_encode_gtk(str(setting.value))
  
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
      image, 50, 20, gimpenums.RGBA_IMAGE, 'Layer 1', 100.0, gimpenums.NORMAL_MODE),
    pdb.gimp_layer_new(
      image, 10, 10, gimpenums.RGBA_IMAGE, 'Layer 2', 50.0, gimpenums.DISSOLVE_MODE),
  ]
  
  channels = [
    pdb.gimp_channel_new(image, 100, 100, 'Channel 1', 100.0, gimpcolor.RGB(0, 0, 0)),
    pdb.gimp_channel_new(image, 100, 100, 'Channel 2', 50.0, gimpcolor.RGB(1, 0, 0)),
  ]
  
  vectors_list = [
    pdb.gimp_vectors_new(image, 'Vectors 1'),
    pdb.gimp_vectors_new(image, 'Vectors 2'),
  ]
  
  for layer, channel, vectors in reversed(list(zip(layers, channels, vectors_list))):
    pdb.gimp_image_insert_layer(image, layer, None, 0)
    pdb.gimp_image_insert_channel(image, channel, None, 0)
    pdb.gimp_image_insert_vectors(image, vectors, None, 0)
  
  return image


def _display_message_on_setting_value_error(exc_type, exc_value, exc_traceback):
  if issubclass(exc_type, settings_.SettingValueError):
    gimp.message(pgutils.safe_encode_gimp(str(exc_value)))
    return True
  else:
    return False
