# -*- coding: utf-8 -*-

"""Widget containing a text label that can be optionally edited."""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import pygtk
pygtk.require('2.0')
import gtk
import gobject

__all__ = [
  'EditableLabel',
]


class EditableLabel(gtk.VBox):
  """
  This class is a GTK widget that displays a label and an edit button to allow
  editing the label. Pressing `Enter` or focusing out of the editable text entry
  displays the label again.
  
  Signals:
  
  * `'changed'` - The user finished editing the label text.
  """
  
  _LABEL_EDIT_BUTTON_SPACING = 4
  
  __gsignals__ = {b'changed': (gobject.SIGNAL_RUN_FIRST, None, ())}
  
  def __init__(self, text=None, **kwargs):
    super().__init__(self, **kwargs)
    
    self._label = gtk.Label(text)
    self._label.set_alignment(0.0, 0.5)
    self._label.show_all()
    self._label.set_no_show_all(True)
    
    self._button_edit = gtk.Button()
    self._button_edit.set_relief(gtk.RELIEF_NONE)
    self._button_edit_icon = gtk.image_new_from_pixbuf(
      self._button_edit.render_icon(gtk.STOCK_EDIT, gtk.ICON_SIZE_MENU))
    self._button_edit.add(self._button_edit_icon)
    
    self._hbox = gtk.HBox(homogeneous=False)
    self._hbox.set_spacing(self._LABEL_EDIT_BUTTON_SPACING)
    self._hbox.pack_start(self._label, expand=True, fill=True)
    self._hbox.pack_start(self._button_edit, expand=False, fill=False)
    
    self._entry = gtk.Entry()
    self._entry.show_all()
    self._entry.set_no_show_all(True)
    
    self._entry.hide()
    
    self.pack_start(self._hbox, expand=False, fill=False)
    self.pack_start(self._entry, expand=False, fill=False)
    
    self._button_edit.connect('clicked', self._on_button_edit_clicked)
    self._entry.connect('activate', self._on_entry_finished_editing)
    self._entry.connect('focus-out-event', self._on_entry_finished_editing)
  
  @property
  def label(self):
    return self._label
  
  def _on_button_edit_clicked(self, button):
    self._hbox.hide()
    
    self._entry.set_text(self._label.get_text())
    self._entry.grab_focus()
    self._entry.set_position(-1)
    self._entry.show()
  
  def _on_entry_finished_editing(self, entry, *args):
    self._entry.hide()
    
    self._label.set_text(self._entry.get_text())
    self._hbox.show()
    
    self.emit('changed')


gobject.type_register(EditableLabel)
