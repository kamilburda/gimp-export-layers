# -*- coding: utf-8 -*-

"""Custom setting classes specific to the plug-in."""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

from export_layers import pygimplib as pg

from export_layers import renamer as renamer_


class FilenamePatternEntryPresenter(pg.setting.presenters_gtk.ExtendedEntryPresenter):
  """`pygimplib.setting.Presenter` subclass for
  `pygimplib.gui.FilenamePatternEntry` elements.
  
  Value: Text in the entry.
  """
  
  def _create_gui_element(self, setting):
    return pg.gui.FilenamePatternEntry(renamer_.get_field_descriptions(renamer_.FIELDS))


class FilenamePatternSetting(pg.setting.StringSetting):
  
  _ALLOWED_GUI_TYPES = [
    FilenamePatternEntryPresenter,
    pg.SettingGuiTypes.extended_entry,
    pg.SettingGuiTypes.entry,
  ]
  
  def _assign_value(self, value):
    if not value:
      self._value = self._default_value
    else:
      self._value = value
