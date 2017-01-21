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
This module defines constants used in other modules.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

from . import pgutils

#===============================================================================

_LOG_OUTPUT_MODES = (
  LOG_EXCEPTIONS_ONLY, LOG_OUTPUT_FILES, LOG_OUTPUT_GIMP_CONSOLE) = (0, 1, 2)

GTK_CHARACTER_ENCODING = "utf-8"
GIMP_CHARACTER_ENCODING = "utf-8"
TEXT_FILE_CHARACTER_ENDOCING = "utf-8"

PYGIMPLIB_MODULE_PATH = pgutils.get_module_root(__name__, "pygimplib")
