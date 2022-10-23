# -*- coding: utf-8 -*-

"""Combo box widget for `gimp.Item` objects."""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import collections

import pygtk
pygtk.require('2.0')
import gtk
import gobject

import gimp
import gimpui

from .. import utils as pgutils

__all__ = [
  'GimpItemComboBox',
]


class GimpItemComboBox(gtk.VBox):
  """
  This class defines a GTK widget for `gimp.Item` objects acting as an
  abstraction over GIMP objects - layers, channels and vectors.
  
  Signals:
  
  * `'changed'` - The user changed the selection either in the combo box
    containing available item types or in the combo box for the selected item
    type.
    
    Arguments:
    
    * `selected_item` - The currently selected `gimp.Item` object.
  """
  
  __gsignals__ = {b'changed': (gobject.SIGNAL_RUN_FIRST, None, (gobject.TYPE_PYOBJECT,))}
  
  _GimpItemComboBox = collections.namedtuple(
    '_GimpItemComboBox',
    ['name', 'widget', 'get_active_item_func', 'set_active_item_func', 'gimp_item_type'])
  
  _COMBO_BOX_SPACING = 4
  
  def __init__(self, constraint=None, data=None, **kwargs):
    super().__init__(homogeneous=False, spacing=self._COMBO_BOX_SPACING, **kwargs)
    
    self._displayed_item_combo_box = None
    
    self._layer_combo_box = gimpui.LayerComboBox(constraint=constraint, data=data)
    self._channel_combo_box = gimpui.ChannelComboBox(constraint=constraint, data=data)
    self._vectors_combo_box = gimpui.VectorsComboBox(constraint=constraint, data=data)
    
    self._item_combo_boxes = [
      self._GimpItemComboBox(
        _('Layer'),
        self._layer_combo_box,
        self._layer_combo_box.get_active_layer,
        self._layer_combo_box.set_active_layer,
        gimp.Layer),
      self._GimpItemComboBox(
        _('Channel'),
        self._channel_combo_box,
        self._channel_combo_box.get_active_channel,
        self._channel_combo_box.set_active_channel,
        gimp.Channel),
      self._GimpItemComboBox(
        _('Vectors'),
        self._vectors_combo_box,
        self._vectors_combo_box.get_active_vectors,
        self._vectors_combo_box.set_active_vectors,
        gimp.Vectors)]
    
    self._item_types_combo_box = gtk.combo_box_new_text()
    
    self.pack_start(self._item_types_combo_box, expand=True, fill=True)
    
    for combo_box in self._item_combo_boxes:
      combo_box.widget.show_all()
      combo_box.widget.hide()
      combo_box.widget.set_no_show_all(True)
      
      self._item_types_combo_box.append_text(pgutils.safe_encode_gtk(combo_box.name))
      
      self.pack_start(combo_box.widget, expand=True, fill=True)
      
      combo_box.widget.connect('changed', self._on_combo_box_changed)
    
    self._item_types_combo_box.connect('changed', self._on_item_types_combo_box_changed)
    
    self._item_types_combo_box.set_active(0)
  
  def get_active_item(self):
    if self._displayed_item_combo_box is not None:
      return self._displayed_item_combo_box.get_active_item_func()
    else:
      return None
  
  def set_active_item(self, item):
    for index, combo_box in enumerate(self._item_combo_boxes):
      if isinstance(item, combo_box.gimp_item_type):
        matching_combo_box = combo_box
        matching_index = index
        break
    else:
      matching_combo_box = None
    
    if matching_combo_box is None:
      raise TypeError(
        'argument must be one of the following types: {}'.format(
          ', '.join(
            str(combo_box.gimp_item_type) for combo_box in self._item_combo_boxes)))
    
    matching_combo_box.set_active_item_func(item)
    self._item_types_combo_box.set_active(matching_index)
  
  def _on_combo_box_changed(self, *args, **kwargs):
    self.emit('changed', self.get_active_item())
  
  def _on_item_types_combo_box_changed(self, combo_box):
    if self._displayed_item_combo_box is not None:
      self._displayed_item_combo_box.widget.hide()
    
    index = self._item_types_combo_box.get_active()
    self._item_combo_boxes[index].widget.show()
    
    self._displayed_item_combo_box = self._item_combo_boxes[index]
    
    self.emit('changed', self.get_active_item())


gobject.type_register(GimpItemComboBox)
