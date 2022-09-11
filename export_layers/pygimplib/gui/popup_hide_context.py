# -*- coding: utf-8 -*-

"""Class simplifying hiding a popup window based on user actions."""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import gobject

from . import utils as utils_

__all__ = [
  'PopupHideContext',
]


class PopupHideContext(object):
  """
  This class provides a simplified interface for connecting events to hide the
  specified popup window. If the user presses a button outside the popup or
  focuses out of the widget that spawned the popup, the popup is hidden.
  """
  
  def __init__(self, popup_to_hide, popup_owner_widget, hide_callback=None):
    """
    Parameters:
    
    * `popup_to_hide` - A `gtk.Window` instance representing a popup to hide.
    
    * `popup_owner_widget` - A `gtk.Widget` instance that spawned the popup.
    
    * `hide_callback` - A function to hide the popup. If `None`,
      `popup_to_hide.hide()` is used to hide the popup.
    """
    self._popup_to_hide = popup_to_hide
    self._popup_owner_widget = popup_owner_widget
    self._hide_callback = (
      hide_callback if hide_callback is not None else self._popup_to_hide.hide)
    
    self._button_press_emission_hook_id = None
    self._toplevel_configure_event_id = None
    self._toplevel_position = None
    self._widgets_with_entered_pointers = set()
    
    self._popup_owner_widget.connect(
      'focus-out-event', self._on_popup_owner_widget_focus_out_event)
  
  def connect_button_press_events_for_hiding(self):
    self._button_press_emission_hook_id = gobject.add_emission_hook(
      self._popup_owner_widget,
      'button-press-event',
      self._on_emission_hook_button_press_event)
    
    toplevel = utils_.get_toplevel_window(self._popup_owner_widget)
    if toplevel is not None:
      toplevel.get_group().add_window(self._popup_to_hide)
      # Button presses on the window decoration cannot be intercepted via the
      # `'button-press-event'` emission hooks, hence this workaround.
      self._toplevel_configure_event_id = toplevel.connect(
        'configure-event', self._on_toplevel_configure_event)
      self._toplevel_position = toplevel.get_position()
  
  def disconnect_button_press_events_for_hiding(self):
    if self._button_press_emission_hook_id is not None:
      gobject.remove_emission_hook(
        self._popup_owner_widget,
        'button-press-event',
        self._button_press_emission_hook_id)
    
    toplevel = utils_.get_toplevel_window(self._popup_owner_widget)
    if (toplevel is not None
        and self._toplevel_configure_event_id is not None
        and toplevel.handler_is_connected(self._toplevel_configure_event_id)):
      toplevel.disconnect(self._toplevel_configure_event_id)
      self._toplevel_configure_event_id = None
  
  def exclude_widget_from_hiding_with_button_press(self, widget):
    widget.connect('enter-notify-event', self._on_widget_enter_notify_event)
    widget.connect('leave-notify-event', self._on_widget_leave_notify_event)
  
  def _on_popup_owner_widget_focus_out_event(self, widget, event):
    self._hide_callback()
  
  def _on_emission_hook_button_press_event(self, widget, event):
    if self._widgets_with_entered_pointers:
      return True
    else:
      self._hide_callback()
      return False
  
  def _on_toplevel_configure_event(self, toplevel, event):
    if self._toplevel_position != toplevel.get_position():
      self._hide_callback()
    
    self._toplevel_position = toplevel.get_position()
  
  def _on_widget_enter_notify_event(self, widget, event):
    self._widgets_with_entered_pointers.add(widget)
  
  def _on_widget_leave_notify_event(self, widget, event):
    self._widgets_with_entered_pointers.discard(widget)
