# -*- coding: utf-8 -*-
#
# This file is part of pygimplib.
#
# Copyright (C) 2014-2016 khalim19 <khalim19@gmail.com>
#
# pygimplib is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pygimplib is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pygimplib.  If not, see <http://www.gnu.org/licenses/>.
#

"""
This module defines custom GTK cell renderers.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import pygtk
pygtk.require("2.0")
import gtk
import gobject

#===============================================================================


class CellRendererTextList(gtk.CellRendererText):
  
  """
  This is a custom text-based cell renderer that can accept a list of strings.
  """
  
  __gproperties__ = {
    b"text-list": (
      gobject.TYPE_PYOBJECT,
      b"list of strings",
      "List of strings to render",
      gobject.PARAM_READWRITE
    ),
    b"markup-list": (
      gobject.TYPE_PYOBJECT,
      b"list of strings in markup",
      "List of strings with markup to render",
      gobject.PARAM_WRITABLE
    ),
    b"text-list-separator": (
      gobject.TYPE_STRING,
      b"separator for list of strings",
      'Text separator for the list of strings ("text-list" and "markup-list" properties)',
      ", ",     # Default value
      gobject.PARAM_READWRITE
    ),
  }
  
  def __init__(self):
    gtk.CellRendererText.__init__(self)
    
    self.text_list = None
    self.markup_list = None
    self.text_list_separator = ", "
  
  def do_get_property(self, property_):
    attr_name = self._property_name_to_attr(property_.name)
    if hasattr(self, attr_name):
      return getattr(self, attr_name)
    else:
      return gtk.CellRendererText.get_property(self, property_.name)
  
  def do_set_property(self, property_, value):
    attr_name = self._property_name_to_attr(property_.name)
    if hasattr(self, attr_name):
      if (property_.name in ["text-list", "markup-list"]
          and not(isinstance(value, list) or isinstance(value, tuple))):
        raise AttributeError("not a list or tuple")
      
      setattr(self, attr_name, value)
      
      self._evaluate_text_property(property_.name)
  
  def _evaluate_text_property(self, property_name):
    """
    Change the "text" or "markup" property according to the value of
    "text-list", "markup-list" and "text-list-separator" properties.
    """
    
    def _set_text():
      new_text = self.text_list_separator.join(self.text_list)
      gtk.CellRendererText.set_property(self, "text", new_text)
    
    def _set_markup():
      new_text = self.text_list_separator.join(self.markup_list)
      gtk.CellRendererText.set_property(self, "markup", new_text)
    
    if property_name == "text-list":
      _set_text()
      self.markup_list = None
    elif property_name == "markup-list":
      _set_markup()
      self.text_list = None
    elif property_name == "text-list-separator":
      if self.text_list is not None:
        _set_text()
      elif self.markup_list is not None:
        _set_markup()
  
  @staticmethod
  def _property_name_to_attr(property_name):
    return property_name.replace("-", "_")


#===============================================================================

gobject.type_register(CellRendererTextList)
