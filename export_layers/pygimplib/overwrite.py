# -*- coding: utf-8 -*-

"""Handling of conflicting files - overwrite, skip, etc."""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *
import future.utils

import abc
import os

from . import path as pgpath


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
  def choose(self, filepath=None):
    """
    Return a value indicating how to handle the conflicting file
    by letting the user choose the value.
    
    The actual overwrite modes (possible values one of which the user chooses)
    and the implementation of handling conflicting files are left to the
    programmer using the return value provided by this method.
    
    Parameters:
    
    * `filepath` - File path that conflicts with an existing file. This class
      uses the file path to simply display it to the user. Defaults to `None`.
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
  
  def choose(self, filepath=None):
    return self._overwrite_mode


class InteractiveOverwriteChooser(
        future.utils.with_metaclass(abc.ABCMeta, OverwriteChooser)):
  """
  This class is an interface for interactive overwrite choosers, requiring
  the user choose the overwrite mode.
  
  Additional attributes:
  
  * `values_and_display_names` - List of (value, display name) tuples which
    define overwrite modes and their human-readable names.
  
  * `default_value` - Default value. Must be one of the values in the
    `values_and_display_names` list.
  
  * `default_response` - Default value to return if the user made a choice that
    returns a value not in `values_and_display_names`. `default_response` does
    not have to be any of the values in `values_and_display_names`.
  
  * `is_apply_to_all` (read-only) - Whether the user-made choice applies to the
    current file (`False`) or to the current and all subsequent files (`True`).
  """
  
  def __init__(self, values_and_display_names, default_value, default_response):
    super().__init__()
    
    self.values_and_display_names = values_and_display_names
    self._values = [value for value, unused_ in self.values_and_display_names]
    
    if default_value not in self._values:
      raise ValueError(
        'invalid default value "{}"; must be one of the following: {}'.format(
          default_value, self._values))
    
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
  
  def choose(self, filepath=None):
    if self._overwrite_mode is None or not self._is_apply_to_all:
      return self._choose(filepath)
    else:
      return self._overwrite_mode
  
  @abc.abstractmethod
  def _choose(self, filepath):
    """
    Let the user choose the overwrite mode and return it.
    
    If the choice results in a value that is not in `values_and_display_names`,
    return `default_response`.
    """
    pass


def handle_overwrite(filepath, overwrite_chooser, position=None):
  """
  If a file with the specified file path exists, handle the file path conflict
  via `overwrite_chooser` (an `OverwriteChooser` instance).
  `filepath` indicates a file path for a new file to be saved.
  
  `overwrite_chooser` should support all overwrite modes specified in
  `OverwriteModes`. `RENAME_NEW` mode renames `filepath`.
  `RENAME_EXISTING` renames the existing file in the file system.
  
  If the overwrite mode indicates that the file path should be renamed and
  `position` is not `None`, the `position` specifies where in the file path to
  insert a unique substring (`' (number)'`). By default, the substring is
  inserted at the end of the file path to be renamed.
  
  Returns:
  
    * the overwrite mode as returned by `overwrite_chooser`, which the caller
      of this function can further use (especially `SKIP` or `CANCEL` values),
    
    * the file path passed as the argument, modified if `RENAME_NEW` mode is
      returned.
  """
  if os.path.exists(filepath):
    overwrite_chooser.choose(filepath=os.path.abspath(filepath))
    
    if overwrite_chooser.overwrite_mode in (
         OverwriteModes.RENAME_NEW, OverwriteModes.RENAME_EXISTING):
      uniq_filepath = pgpath.uniquify_filepath(filepath, position)
      if overwrite_chooser.overwrite_mode == OverwriteModes.RENAME_NEW:
        filepath = uniq_filepath
      else:
        os.rename(filepath, uniq_filepath)
  
    return overwrite_chooser.overwrite_mode, filepath
  else:
    return OverwriteModes.DO_NOTHING, filepath


class OverwriteModes(object):
  """
  This class defines common overwrite modes for convenience.
  
  `SKIP` should be used if a file path already exists and no action should be
  taken.
  
  `DO_NOTHING` should be used if a file path does not exist and no action should
  be taken.
  
  `CANCEL` should be used if the user terminated the overwrite chooser (e.g.
  closed the overwrite dialog when an interactive chooser is used).
  """
  
  OVERWRITE_MODES = REPLACE, SKIP, RENAME_NEW, RENAME_EXISTING, CANCEL, DO_NOTHING = (
    0, 1, 2, 3, 4, 5)
