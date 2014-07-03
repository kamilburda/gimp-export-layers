#-------------------------------------------------------------------------------
#
# This file is part of libgimpplugin.
#
# Copyright (C) 2014 khalim19 <khalim19@gmail.com>
# 
# libgimpplugin is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# libgimpplugin is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with libgimpplugin.  If not, see <http://www.gnu.org/licenses/>.
#
#-------------------------------------------------------------------------------

"""
This module:
* defines an ordered, dict-like container to store items
"""

#=============================================================================== 

import abc
from collections import OrderedDict

#===============================================================================

class Container(object):
  
  __metaclass__ = abc.ABCMeta
  
  def __init__(self):
    self._items = OrderedDict()
  
  def __getitem__(self, key):
    return self._items[key]
  
  def __setitem__(self, key, value):
    self._items[key] = value
  
  def __contains__(self, key):
    return key in self._items[key]
  
  def __delitem__(self, key):
    del self._items[key]
  
  def __iter__(self):
    """
    Iterate over values (unlike dict, which iterates over keys).
    """
    for item in self._items.values():
      yield item
  
  def __len__(self):
    return len(self._items)
