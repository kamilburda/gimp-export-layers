# -*- coding: utf-8 -*-

"""Constants used in other modules."""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

from . import utils as pgutils

__all__ = [
  'GTK_CHARACTER_ENCODING',
  'GIMP_CHARACTER_ENCODING',
  'TEXT_FILE_ENCODING',
  'PYGIMPLIB_MODULE_PATH',
]


GTK_CHARACTER_ENCODING = 'utf-8'
GIMP_CHARACTER_ENCODING = 'utf-8'
TEXT_FILE_ENCODING = 'utf-8'

PYGIMPLIB_MODULE_PATH = pgutils.get_module_root(__name__, 'pygimplib')
