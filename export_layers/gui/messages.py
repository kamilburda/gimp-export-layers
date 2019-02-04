# -*- coding: utf-8 -*-
#
# This file is part of Export Layers.
#
# Copyright (C) 2013-2019 khalim19 <khalim19@gmail.com>
#
# Export Layers is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Export Layers is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Export Layers.  If not, see <https://www.gnu.org/licenses/>.

"""
This module defines functions to display message dialogs.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import pygtk
pygtk.require("2.0")
import gtk

from export_layers import pygimplib as pg


def display_message(
      message,
      message_type,
      parent=None,
      buttons=gtk.BUTTONS_OK,
      message_in_text_view=False,
      button_response_id_to_focus=None):
  return pg.gui.display_message(
    message,
    message_type,
    title=pg.config.PLUGIN_TITLE,
    parent=parent,
    buttons=buttons,
    message_in_text_view=message_in_text_view,
    button_response_id_to_focus=button_response_id_to_focus)
