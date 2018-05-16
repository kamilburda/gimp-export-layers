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
This module contains helper classes and functions for `pgsetting*` modules.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

#===============================================================================


def get_pdb_name(setting_name):
  """
  Return setting name suitable for the description of the setting in the GIMP
  PDB.
  """
  
  return setting_name.replace("_", "-")


def value_to_str_prefix(value):
  """
  Return stringified setting value useful as a prefix to an error message.
  
  If `value` is empty or None, return empty string.
  """
  
  if value:
    return '"{0}": '.format(value)
  else:
    return ""


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
  """
  Generate setting description from a display name.
  
  Underscores in display names used as mnemonics are usually undesired in
  descriptions, hence their removal.
  """
  
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
    root_path = _get_setting_path(
      relative_path_setting_group.parents + [relative_path_setting_group])
    if setting_path.startswith(root_path):
      return setting_path[len(root_path + SETTING_PATH_SEPARATOR):]
  
  return setting_path
