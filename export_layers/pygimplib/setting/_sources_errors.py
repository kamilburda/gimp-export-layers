# -*- coding: utf-8 -*-

"""Exceptions used in `setting.sources` and `setting.persistor` modules."""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import traceback as traceback_

__all__ = [
  'SourceError',
  'SourceNotFoundError',
  'SourceReadError',
  'SourceInvalidFormatError',
  'SourceWriteError',
]


class SourceError(Exception):
  
  def __init__(self, message=''):
    super().__init__(message)
    
    self.traceback = traceback_.format_exc()
  
  def __str__(self):
    if self.traceback and not self.message:
      return self.traceback
    else:
      return self.message


class SourceNotFoundError(SourceError):
  pass


class SourceInvalidFormatError(SourceError):
  pass


class SourceReadError(SourceError):
  pass


class SourceWriteError(SourceError):
  pass
