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
This module contains helper classes and functions for `pgsetting*` modules.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

#===============================================================================


def get_processed_display_name(setting_display_name, setting_name):
  if setting_display_name is not None:
    return setting_display_name
  else:
    return generate_display_name(setting_name)


def generate_display_name(setting_name):
  return setting_name.replace("_", " ").capitalize()


def get_processed_description(setting_description, setting_display_name):
  if setting_description is not None:
    return setting_description
  else:
    return generate_description(setting_display_name)


def generate_description(display_name):
  # Underscores in display names used as mnemonics are usually undesired in
  # descriptions, hence their removal.
  return display_name.replace("_", "")


#===============================================================================


class SettingParentMixin(object):
  
  """
  This mixin provides `Setting` and `SettingGroup` objects with a parent
  reference, allowing settings and groups to form a tree-like structure.
  """
  
  def __init__(self):
    self._parent = None
  
  @property
  def parent(self):
    return self._parent
  
  @property
  def parents(self):
    """
    Return a list of parents (setting groups), starting from the topmost parent.
    """
    
    parent = self._parent
    parents = []
    
    while parent is not None:
      parents.insert(0, parent)
      parent = parent.parent
    
    return parents
  
  def _set_as_parent_for_setting(self, setting):
    setting._parent = self


#===============================================================================


SETTING_PATH_SEPARATOR = "/"


def get_setting_path(setting, relative_path_setting_group=None):
  """
  Get the full setting path consisting of names of parent setting groups and the
  specified setting. The path components are separated by "/".
  
  If `relative_path_setting_group` is specified, the setting group is used to
  relativize the setting path. If the path of the setting group to the topmost
  parent does not match, return the full path.
  """
  
  def _get_setting_path(path_components):
    return SETTING_PATH_SEPARATOR.join([setting.name for setting in path_components])
  
  setting_path = _get_setting_path(setting.parents + [setting])
  
  if relative_path_setting_group is not None:
    root_path = _get_setting_path(relative_path_setting_group.parents + [relative_path_setting_group])
    if setting_path.startswith(root_path):
      return setting_path[len(root_path + SETTING_PATH_SEPARATOR):]
  
  return setting_path
