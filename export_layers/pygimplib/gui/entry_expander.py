# -*- coding: utf-8 -*-

"""Class modifying `gtk.Entry` instances to expand/shrink in width dynamically.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import pango

__all__ = [
  'EntryExpander',
]


class EntryExpander(object):
  """
  This class enables the specified `gtk.Entry` to have a flexible width, bounded
  by the specified minimum and maximum number of characters (width in
  characters).
  """
  
  def __init__(self, entry, minimum_width_chars, maximum_width_chars):
    self._entry = entry
    self._minimum_width_chars = minimum_width_chars
    self._maximum_width_chars = maximum_width_chars
    
    if self._minimum_width_chars > self._maximum_width_chars:
      raise ValueError(
        'minimum width in characters ({0}) cannot be greater than maximum ({1})'.format(
          self._minimum_width_chars, self._maximum_width_chars))
    
    self._minimum_width = -1
    self._maximum_width = -1
    self._entry.set_width_chars(self._minimum_width_chars)
    
    self._pango_layout = pango.Layout(self._entry.get_pango_context())
    
    self._entry.connect('changed', self._on_entry_changed)
    self._entry.connect('size-allocate', self._on_entry_size_allocate)
  
  def _on_entry_changed(self, entry):
    if self._entry.get_realized():
      self._update_entry_width()
  
  def _on_entry_size_allocate(self, entry, allocation):
    if self._minimum_width == -1:
      self._minimum_width = self._entry.get_allocation().width
      self._maximum_width = (
        int((self._minimum_width / self._minimum_width_chars)
            * self._maximum_width_chars)
        + 1)
    
    self._update_entry_width()
  
  def _update_entry_width(self):
    self._pango_layout.set_text(self._entry.get_text())
    
    offset_pixel_width = (
      (self._entry.get_layout_offsets()[0] + self._entry.get_property('scroll-offset'))
      * 2)
    text_pixel_width = self._pango_layout.get_pixel_size()[0] + offset_pixel_width
    self._entry.set_property(
      'width-request',
      max(min(text_pixel_width, self._maximum_width), self._minimum_width))
