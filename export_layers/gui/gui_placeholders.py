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
This module defines GUI for placeholder GIMP objects (images, layers). During
processing, these placeholders are replaced with real objects.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import gimpui

from export_layers import pygimplib as pg


class GimpObjectPlaceholdersComboBoxPresenter(pg.setting.GtkPresenter):
  """
  This class is a `setting.presenter.Presenter` subclass for
  `gimpui.IntComboBox` elements used for `placeholders.PlaceholderSetting`.
  
  Value: `placeholders.PlaceholderSetting` instance selected in the combo box.
  """
  
  _VALUE_CHANGED_SIGNAL = "changed"
  
  def _create_gui_element(self, setting):
    placeholder_names_and_values = []
    
    for index, placeholder in enumerate(setting.get_allowed_placeholders()):
      placeholder_names_and_values.extend(
        (placeholder.display_name.encode(pg.GTK_CHARACTER_ENCODING), index))
    
    return gimpui.IntComboBox(tuple(placeholder_names_and_values))
  
  def _get_value(self):
    return self._setting.get_allowed_placeholder_names()[self._element.get_active()]
  
  def _set_value(self, value):
    self._element.set_active(self._setting.get_allowed_placeholder_names().index(value))
