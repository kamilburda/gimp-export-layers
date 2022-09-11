# -*- coding: utf-8 -*-

"""Functions to display message dialogs."""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import pygtk
pygtk.require('2.0')
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
