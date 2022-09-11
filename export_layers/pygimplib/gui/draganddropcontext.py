# -*- coding: utf-8 -*-

"""Class providing drag-and-drop capability to any GTK widget."""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import pygtk
pygtk.require('2.0')
import gtk

__all__ = [
  'DragAndDropContext',
]


class DragAndDropContext(object):
  """
  This class adds drag-and-drop capability to the specified GTK widget.
  """
  
  def __init__(self):
    self._drag_type = self._get_unique_drag_type()
    self._last_widget_dest_drag = None
  
  def setup_drag(
        self,
        widget,
        get_drag_data_func,
        drag_data_receive_func,
        get_drag_data_args=None,
        drag_data_receive_args=None,
        scrolled_window=None):
    """
    Enable dragging for the specified `widget`.
    
    `get_drag_data_func` is a function that returns data as a string describing
    the dragged widget.
    
    `drag_data_receive_func` is a function that processes the data returned by
    `get_drag_data_func`.
    
    `get_drag_data_args` and `drag_data_receive_args` are optional arguments for
    `get_drag_data_func` and `drag_data_receive_func`, respectively.
    
    The displayed `widget` is used as the drag icon. If the item box is wrapped
    in a scrolled window, specify the `scrolled_window` instance so that the
    default drag icon is assigned if `widget` is partially hidden inside the
    scrolled window.
    """
    if get_drag_data_args is None:
      get_drag_data_args = ()
    
    if drag_data_receive_args is None:
      drag_data_receive_args = ()
    
    widget.connect(
      'drag-data-get',
      self._on_widget_drag_data_get,
      get_drag_data_func,
      get_drag_data_args)
    widget.drag_source_set(
      gtk.gdk.BUTTON1_MASK, [(self._drag_type, 0, 0)], gtk.gdk.ACTION_MOVE)
    
    widget.connect(
      'drag-data-received',
      self._on_widget_drag_data_received,
      drag_data_receive_func,
      *drag_data_receive_args)
    widget.drag_dest_set(
      gtk.DEST_DEFAULT_ALL, [(self._drag_type, 0, 0)], gtk.gdk.ACTION_MOVE)
    
    widget.connect(
      'drag-begin', self._on_widget_drag_begin, scrolled_window)
    widget.connect('drag-motion', self._on_widget_drag_motion)
    widget.connect('drag-failed', self._on_widget_drag_failed)
  
  def _get_unique_drag_type(self):
    return str('{}_{}'.format(self.__class__.__name__, id(self)))
  
  def _on_widget_drag_data_get(
        self,
        widget,
        drag_context,
        selection_data,
        info,
        timestamp,
        get_drag_data_func,
        get_drag_data_args):
    selection_data.set(selection_data.target, 8, get_drag_data_func(*get_drag_data_args))
  
  def _on_widget_drag_data_received(
        self,
        widget,
        drag_context,
        drop_x,
        drop_y,
        selection_data,
        info,
        timestamp,
        drag_data_receive_func,
        *drag_data_receive_args):
    drag_data_receive_func(selection_data.data, *drag_data_receive_args)
  
  def _on_widget_drag_begin(self, widget, drag_context, scrolled_window):
    drag_icon_pixbuf = self._get_drag_icon_pixbuf(widget, scrolled_window)
    if drag_icon_pixbuf is not None:
      drag_context.set_icon_pixbuf(drag_icon_pixbuf, 0, 0)
  
  def _on_widget_drag_motion(
        self, widget, drag_context, drop_x, drop_y, timestamp):
    self._last_widget_dest_drag = widget
  
  def _on_widget_drag_failed(self, widget, drag_context, result):
    if self._last_widget_dest_drag is not None:
      self._last_widget_dest_drag.drag_unhighlight()
      self._last_widget_dest_drag = None
  
  def _get_drag_icon_pixbuf(self, widget, scrolled_window):
    if widget.get_window() is None:
      return
    
    if (scrolled_window is not None
        and self._are_items_partially_hidden_because_of_visible_horizontal_scrollbar(
              scrolled_window)):
      return None
    
    self._setup_widget_to_add_border_to_drag_icon(widget)
    
    while gtk.events_pending():
      gtk.main_iteration()
    
    widget_allocation = widget.get_allocation()
    
    pixbuf = gtk.gdk.Pixbuf(
      gtk.gdk.COLORSPACE_RGB,
      False,
      8,
      widget_allocation.width,
      widget_allocation.height)
    
    drag_icon_pixbuf = pixbuf.get_from_drawable(
      widget.get_window(),
      widget.get_colormap(),
      0,
      0,
      0,
      0,
      widget_allocation.width,
      widget_allocation.height)
    
    self._restore_widget_after_creating_drag_icon(widget)
    
    return drag_icon_pixbuf
  
  @staticmethod
  def _are_items_partially_hidden_because_of_visible_horizontal_scrollbar(
        scrolled_window):
    return (
      scrolled_window.get_hscrollbar() is not None
      and scrolled_window.get_hscrollbar().get_mapped())
  
  def _setup_widget_to_add_border_to_drag_icon(self, widget):
    self._remove_focus_outline(widget)
    self._add_border(widget)
  
  @staticmethod
  def _remove_focus_outline(widget):
    if widget.has_focus():
      widget.set_can_focus(False)
  
  @staticmethod
  def _add_border(widget):
    widget.drag_highlight()
  
  def _restore_widget_after_creating_drag_icon(self, widget):
    self._add_focus_outline(widget)
    self._remove_border(widget)
  
  @staticmethod
  def _add_focus_outline(widget):
    widget.set_can_focus(True)
  
  @staticmethod
  def _remove_border(widget):
    widget.drag_unhighlight()
