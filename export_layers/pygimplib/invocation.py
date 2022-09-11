# -*- coding: utf-8 -*-

"""Functions to invoke other functions in various ways, e.g. with a timeout."""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import os

import gimp
import gobject


_timer_ids = {}


def timeout_add(interval, callback, *callback_args):
  """
  This is a thin wrapper of `gobject.timeout_add()` that 'fixes' the function
  failing to work on Windows on GIMP 2.10 by setting the interval to zero.
  """
  if os.name == 'nt' and ((2, 10, 0) <= gimp.version < (2, 10, 6)):
    return gobject.timeout_add(0, callback, *callback_args)
  else:
    return gobject.timeout_add(interval, callback, *callback_args)


def timeout_add_strict(interval, callback, *callback_args, **callback_kwargs):
  """
  This is a wrapper for `gobject.timeout_add()`, which calls the specified
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
  
  _timer_ids[callback] = timeout_add(
    interval, _callback_wrapper, callback_args, callback_kwargs)
  
  return _timer_ids[callback]


def timeout_remove_strict(callback):
  """
  Remove a callback scheduled by `timeout_add_strict()`. If no such callback
  exists, do nothing.
  """
  if callback in _timer_ids:
    gobject.source_remove(_timer_ids[callback])
    del _timer_ids[callback]
