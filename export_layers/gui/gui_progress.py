# -*- coding: utf-8 -*-
#
# This file is part of Export Layers.
#
# Copyright (C) 2013-2016 khalim19 <khalim19@gmail.com>
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
# along with Export Layers.  If not, see <http://www.gnu.org/licenses/>.
#

"""
This module defines a progress indicator for processed items.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import pygtk
pygtk.require("2.0")
import gtk
import pango

import gimp

from ..pygimplib import pgutils

#===============================================================================


class ItemProgressIndicator(object):
  
  """
  This class defines a progress indicator suitable for currently processed
  items.
  
  The widget consists of two progress bars. The first progress bar indicates the
  number of items successfully processed. The second progress bar, placed
  directly below the first, indicates the status of the item being currently
  processed.
  """
  
  def __init__(
        self, progress_bar_for_item_status_height=10, spacing_between_progress_bars=3):
    self._progress_bar_for_item_status_height = progress_bar_for_item_status_height
    self._spacing_between_progress_bars = spacing_between_progress_bars
    
    self._progress_callback = None
    
    self._init_gui()
  
  @property
  def widget(self):
    return self._vbox_progress_bars
  
  @property
  def progress_bar_for_items(self):
    return self._progress_bar_for_items
  
  @property
  def progress_bar_for_item_status(self):
    return self._progress_bar_for_item_status
  
  def _init_gui(self):
    self._progress_bar_for_items = gtk.ProgressBar()
    self._progress_bar_for_items.set_ellipsize(pango.ELLIPSIZE_MIDDLE)
    
    self._progress_bar_for_item_status = gtk.ProgressBar()
    self._progress_bar_for_item_status.set_size_request(-1, self._progress_bar_for_item_status_height)
    
    self._vbox_progress_bars = gtk.VBox()
    self._vbox_progress_bars.set_spacing(self._spacing_between_progress_bars)
    self._vbox_progress_bars.pack_start(self._progress_bar_for_items, expand=False, fill=False)
    self._vbox_progress_bars.pack_start(self._progress_bar_for_item_status, expand=False, fill=False)
  
  def install_progress_for_status(
        self, progress_set_value=None, progress_reset_value=None):
    """
    Initialize the progress bar for the current item status to update according
    to GIMP PDB calls.
    """
    
    if progress_set_value is None:
      progress_set_value = self._progress_set_value
    
    if progress_reset_value is None:
      def progress_reset_value_default(*args):
        progress_set_value(0.0)
      
      progress_reset_value = progress_reset_value_default
    
    self._progress_callback = gimp.progress_install(
      progress_reset_value, progress_reset_value, pgutils.empty_func, progress_set_value)
  
  def _progress_set_value(self, fraction):
    self._progress_bar_for_item_status.set_fraction(fraction)
    while gtk.events_pending():
      gtk.main_iteration()
  
  def uninstall_progress_for_status(self):
    """
    Reset the progress bar for the current item status so that it no longer
    updates according to GIMP PDB calls.
    """
    
    if self._progress_callback is not None:
      gimp.progress_uninstall(self._progress_callback)
      self._progress_callback = None
