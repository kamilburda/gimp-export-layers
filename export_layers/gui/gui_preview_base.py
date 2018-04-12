# -*- coding: utf-8 -*-
#
# This file is part of Export Layers.
#
# Copyright (C) 2013-2017 khalim19 <khalim19@gmail.com>
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
This module defines the base class for preview widgets.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

#===============================================================================


class ExportPreview(object):
  
  def __init__(self):
    self._update_locked = False
    self._lock_keys = set()
    
    self._should_enable_sensitive = None
    
    self._settings_events_to_temporarily_disable = {}
  
  def update(self, should_enable_sensitive=None):
    """
    Update the export preview if update is not locked (see `lock_update`).
    
    If `should_enable_sensitive` is True/False, enable/disable sensitive state
    immediately if the preview is not locked, or apply the state once the
    preview is no longer locked. If `should_enable_sensitive` is None, preserve
    the sensitive state.
    """
    
    pass
  
  def set_sensitive(self, sensitive):
    """
    Set the sensitivity of the preview (True = sensitive, False = insensitive).
    """
    
    pass
  
  def lock_update(self, lock, key=None):
    """
    If `lock` is True, calling `update` will have no effect. Passing False to
    `lock` will enable updating the preview again.
    
    If `key` is specified to lock the update, the same key must be specified to
    unlock the preview. Multiple keys can be used to lock the preview; to unlock
    the preview, call this method with each of the keys.
    
    If `key` is specified and `lock` is False and the key was not used to lock
    the preview before, nothing happens.
    
    If `key` is None, lock/unlock the preview regardless of which function
    called this method. Passing None also removes previous keys that were used
    to lock the preview.
    """
    
    if key is None:
      self._lock_keys.clear()
      self._update_locked = lock
    else:
      if lock:
        self._lock_keys.add(key)
      else:
        if key in self._lock_keys:
          self._lock_keys.remove(key)
      
      self._update_locked = bool(self._lock_keys)
  
  def temporarily_disable_setting_events_on_update(self, settings_and_event_ids):
    self._settings_events_to_temporarily_disable = settings_and_event_ids
