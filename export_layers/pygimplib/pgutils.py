#
# This file is part of pygimplib.
#
# Copyright (C) 2014, 2015 khalim19 <khalim19@gmail.com>
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
This module:
* defines custom functions to handle invocation of functions with a delay
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

str = unicode

import gobject

#===============================================================================


_timer_ids = {}


def timeout_add_strict(interval, callback, *callback_args, **callback_kwargs):
  """
  This is a wrapper for `gobject.timeout_add`, which calls the specified
  callback at regular intervals (in milliseconds).
  
  Additionally, if the same callback is called again before the timeout, the
  first invocation will be canceled. If different functions are called before
  the timeout, they will all be invoked normally.
  
  This function also supports keyword arguments to the callback.
  """
  
  global _timer_ids
  
  def _callback_wrapper(callback_args, callback_kwargs):
    retval = callback(*callback_args, **callback_kwargs)
    if callback in _timer_ids:
      del _timer_ids[callback]
    
    return retval
  
  timeout_remove_strict(callback)
  
  _timer_ids[callback] = gobject.timeout_add(interval, _callback_wrapper, callback_args, callback_kwargs)
  
  return _timer_ids[callback]


def timeout_remove_strict(callback):
  """
  Remove a callback scheduled by `timeout_add_strict()`. If no such
  callback exists, do nothing.
  """
  
  if callback in _timer_ids:
    gobject.source_remove(_timer_ids[callback])
    del _timer_ids[callback]
