# -*- coding: utf-8 -*-

"""Widget for placeholder GIMP objects (images, layers) such as "Current layer".

During processing, these placeholders are replaced with real objects.
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
  
  _VALUE_CHANGED_SIGNAL = 'changed'
  
  def _create_gui_element(self, setting):
    placeholder_names_and_values = []
    
    for index, placeholder in enumerate(setting.get_allowed_placeholders()):
      placeholder_names_and_values.extend(
        (pg.utils.safe_encode_gtk(placeholder.display_name), index))
    
    return gimpui.IntComboBox(tuple(placeholder_names_and_values))
  
  def _get_value(self):
    return self._setting.get_allowed_placeholder_names()[self._element.get_active()]
  
  def _set_value(self, value):
    self._element.set_active(self._setting.get_allowed_placeholder_names().index(value))
