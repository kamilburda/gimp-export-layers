# -*- coding: utf-8 -*-

"""Widget for displaying inline messages."""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import os

import pygtk
pygtk.require('2.0')
import gtk
import gobject
import pango

import gimp

from export_layers import pygimplib as pg


class MessageLabel(gtk.HBox):
  """
  This class defines a widget to display a label, and optionally additional
  information in a tooltip. The tooltip is also displayed if the
  label text does not fit the width of the parent widget.
  """
  
  _SPACING = 2
  
  def __init__(self):
    super().__init__(homogeneous=False)
    
    self._label_text = ''
    self._tooltip_text_lines = []
    self._message_type = None
    self._clear_delay = None
    
    self._init_gui()
    
    self._label_message.connect('size-allocate', self._on_label_message_size_allocate)
  
  def set_text(self, text, message_type=gtk.MESSAGE_ERROR, clear_delay=None):
    """
    Set the `text` of the label. The text is displayed in bold style.
    
    If the text is too wide to fit the label or the text has multiple lines,
    ellipsize the label and display a tooltip containing the full text.
    
    Only the first line is displayed in the label.
    
    If `clear_delay` is not `None` and `message_type` is not
    `gtk.MESSAGE_ERROR`, make the message automatically disappear after the
    specified delay in milliseconds. The timer is stopped if the tooltip is
    displayed and restarted if the tooltip gets hidden.
    """
    if not text:
      self._label_text = ''
      self._tooltip_text_lines = []
      self._label_message.set_text(self._label_text)
      return
    
    lines = text.strip().split('\n')
    
    first_line = lines[0]
    first_line = first_line[0].upper() + first_line[1:]
    if not first_line.endswith('.'):
      first_line += '.'
    
    self._label_text = first_line
    self._tooltip_text_lines = lines[1:]
    self._message_type = message_type
    self._clear_delay = clear_delay
    
    self._label_message.set_markup(
      '<b>{}</b>'.format(gobject.markup_escape_text(pg.utils.safe_encode_gtk(self._label_text))))
    
    if message_type == gtk.MESSAGE_ERROR:
      self._timeout_remove_strict(self._clear_delay, self.set_text)
    else:
      self._timeout_add_strict(self._clear_delay, self.set_text, None)
  
  def _init_gui(self):
    self._label_message = gtk.Label()
    self._label_message.set_alignment(0.0, 0.5)
    self._label_message.set_ellipsize(pango.ELLIPSIZE_END)
    
    self.set_spacing(self._SPACING)
    self.pack_start(self._label_message, expand=True, fill=True)
  
  def _on_label_message_size_allocate(self, label, allocation):
    if ((pg.gui.get_label_full_text_width(self._label_message)
         > self.get_allocation().width)
        or len(self._tooltip_text_lines) >= 1):
      lines = list(self._tooltip_text_lines) + [self._label_text]
      
      self._label_message.set_tooltip_text('\n'.join(lines).strip())
    else:
      self._label_message.set_tooltip_text(None)
  
  def _timeout_add_strict(self, delay, func, *args, **kwargs):
    if self._should_clear_text_after_delay(delay):
      pg.invocation.timeout_add_strict(delay, func, None, *args, **kwargs)
  
  def _timeout_remove_strict(self, delay, func):
    if self._should_clear_text_after_delay(delay):
      pg.invocation.timeout_remove_strict(func)
  
  def _should_clear_text_after_delay(self, clear_delay):
    return (
      clear_delay is not None
      and clear_delay > 0
      and not (os.name == 'nt' and ((2, 10, 0) <= gimp.version < (2, 10, 6))))


gobject.type_register(MessageLabel)
