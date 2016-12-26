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
This module defines:
* overwrite chooser - an indication on how to handle existing files (skip,
  replace, rename, etc.),
* `handle_overwrite` convenience function to handle conflicting files.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *
import future.utils

import abc
import os

from . import pgpath

#===============================================================================


class OverwriteChooser(future.utils.with_metaclass(abc.ABCMeta, object)):
  
  """
  This class is an interface to indicate how to handle existing files.
  
  Attributes:
  
  * `overwrite_mode` (read-only) - Overwrite mode chosen by the user.
  """
  
  @abc.abstractmethod
  def overwrite_mode(self):
    pass
  
  @abc.abstractmethod
  def choose(self, filename=None):
    """
    Return a value indicating how to handle the conflicting file
    by letting the user choose the value.
    
    The actual overwrite modes (possible values one of which the user chooses)
    and the implementation of handling conflicting files are left to the
    programmer using the return value provided by this method.
    
    Parameters:
    
    * `filename` - Filename that conflicts with an existing file.
      `OverwriteChooser` use the filename to simply display it to the user.
      Defaults to None.
    """
    
    pass


class NoninteractiveOverwriteChooser(OverwriteChooser):
  
  """
  This class simply stores overwrite mode specified upon the object
  instantiation. The object is suitable to use in a non-interactive environment,
  i.e. with no user interaction.
  """
  
  def __init__(self, overwrite_mode):
    super().__init__()
    self._overwrite_mode = overwrite_mode
  
  @property
  def overwrite_mode(self):
    return self._overwrite_mode
  
  def choose(self, filename=None):
    return self._overwrite_mode


class InteractiveOverwriteChooser(future.utils.with_metaclass(abc.ABCMeta, OverwriteChooser)):
  
  """
  This class is an interface for interactive overwrite choosers, requiring
  the user choose the overwrite mode.
  
  Additional attributes:
  
  * `values_and_display_names` - List of (value, display name) tuples which
    define overwrite modes and their human-readable names.
  
  * `default_value` - Default value. Must be one of the values in the
    `values_and_display_names` list.
  
  * `default_response` - Default value to return if the user made a choice that
    returns a value not in `values_and_display_names`. `default_response`
    does not have to be any of the values in `values_and_display_names`.
  
  * `is_apply_to_all` (read-only) - Whether the user-made choice applies to the
    current file (False) or to the current and all subsequent files (True).
  """
  
  def __init__(self, values_and_display_names, default_value, default_response):
    super().__init__()
    
    self.values_and_display_names = values_and_display_names
    self._values = [value for value, _unused in self.values_and_display_names]
    
    if default_value not in self._values:
      raise ValueError(
        "invalid default value '{0}'; must be one of the following: {1}".format(default_value, self._values))
    
    self.default_value = default_value
    self.default_response = default_response

    self._overwrite_mode = self.default_value
    self._is_apply_to_all = False
  
  @property
  def overwrite_mode(self):
    return self._overwrite_mode
  
  @property
  def is_apply_to_all(self):
    return self._is_apply_to_all
  
  def choose(self, filename=None):
    if self._overwrite_mode is None or not self._is_apply_to_all:
      return self._choose(filename)
    else:
      return self._overwrite_mode
  
  @abc.abstractmethod
  def _choose(self, filename):
    """
    Let the user choose the overwrite mode and return it.
    
    If the choice results in a value that is not in `values_and_display_names`,
    return `default_response`.
    """
    
    pass


#===============================================================================


class OverwriteModes(object):
  """
  This class defines common overwrite modes for convenience.
  """
  
  OVERWRITE_MODES = REPLACE, SKIP, RENAME_NEW, RENAME_EXISTING, CANCEL = (0, 1, 2, 3, 4)


def handle_overwrite(filename, overwrite_chooser, uniquifier_position=None):
  """
  If a file with the specified filename exists, handle the filename conflict
  by executing the `overwrite_chooser` (an `OverwriteChooser` instance).
  `filename` indicates a filename for a new file to be saved.
  
  `overwrite_chooser` should support all overwrite modes specified in
  `OverwriteModes`. `RENAME_NEW` mode renames `filename`.
  `RENAME_EXISTING` renames the existing file in the file system.
  
  If the overwrite mode indicates that the filename should be renamed and
  `uniquifier_position` is not None, the `uniquifier_position` specifies where
  in the filename to insert a unique substring (" (number)"). By default, the
  uniquifier is inserted at the end of the filename to be renamed.
  
  Returns:
  
    * the overwrite mode as returned by `overwrite_chooser`, which the caller
      of this function can further use (especially `SKIP` or `CANCEL` values),
    
    * the filename passed as the argument, modified if `RENAME_NEW` mode is
      returned.
  """
  
  if os.path.exists(filename):
    overwrite_chooser.choose(filename=os.path.abspath(filename))
    
    if overwrite_chooser.overwrite_mode in (OverwriteModes.RENAME_NEW, OverwriteModes.RENAME_EXISTING):
      uniq_filename = pgpath.uniquify_filename(filename, uniquifier_position)
      if overwrite_chooser.overwrite_mode == OverwriteModes.RENAME_NEW:
        filename = uniq_filename
      else:
        os.rename(filename, uniq_filename)
  
  return overwrite_chooser.overwrite_mode, filename
