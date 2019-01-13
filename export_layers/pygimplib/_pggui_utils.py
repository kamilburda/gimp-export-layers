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
This module defines miscellaneous utility functions dealing with GTK widgets.

This module should not be used directly. Use `pggui` as the contents of this
module are included in `pggui`.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import pygtk
pygtk.require("2.0")
import gtk
import pango

__all__ = [
  "get_toplevel_window",
  "label_fits_text",
  "get_label_full_text_width",
  "menu_popup_below_widget",
  "get_position_below_widget",
]


def get_toplevel_window(widget):
  """
  Return the toplevel window (`gtk.Window`) for the specified widget
  (`gtk.Widget`). If the widget has no toplevel window, return None.
  """
  toplevel_widget = widget.get_toplevel()
  if toplevel_widget.flags() & gtk.TOPLEVEL:
    return toplevel_widget
  else:
    return None


def label_fits_text(label, use_markup=True):
  """
  If the `label` is wide enough to display the entire text, return `True`,
  otherwise `False`. If `use_markup` is `True`, treat the label text as
  marked-up text.
  """
  return (label.get_layout().get_pixel_size()[0]
          >= get_label_full_text_width(label, use_markup))


def get_label_full_text_width(label, use_markup=True):
  """
  Return the pixel width of the label text. If `use_markup` is `True`, treat the
  label text as marked-up text.
  """
  full_text_layout = pango.Layout(label.get_pango_context())
  
  if use_markup:
    full_text_layout.set_markup_with_accel(label.get_label(), "_")
  else:
    full_text_layout.set_text(label.get_text())
  
  return full_text_layout.get_pixel_size()[0]


def menu_popup_below_widget(
      menu,
      widget,
      parent_menu_shell=None,
      parent_menu_item=None,
      button=0,
      activate_time=0):
  """
  Display popup of the specified menu below the specified widget. If the widget
  has no associated top-level window, display the popup on the cursor position.
  """
  position_below_widget = get_position_below_widget(widget)
  
  if position_below_widget is not None:
    menu.popup(
      parent_menu_shell,
      parent_menu_item,
      lambda menu_: (position_below_widget[0], position_below_widget[1], True),
      button,
      activate_time)
  else:
    menu.popup(parent_menu_shell, parent_menu_item, None, button, activate_time)


def get_position_below_widget(widget):
  toplevel_window = get_toplevel_window(widget)
  
  if toplevel_window is not None:
    toplevel_window_position = toplevel_window.get_window().get_origin()
    widget_allocation = widget.get_allocation()
    return (
      toplevel_window_position[0] + widget_allocation.x,
      toplevel_window_position[1] + widget_allocation.y + widget_allocation.height)
  else:
    return None
