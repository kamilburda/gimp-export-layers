# -*- coding: utf-8 -*-
#
# Copyright (C) 2014-2019 khalim19
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
