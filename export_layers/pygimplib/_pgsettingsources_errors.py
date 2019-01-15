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

"""
This module defines exceptions used in `pgsettingsources` and
`pgsettingpersistor` modules.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

__all__ = [
  "SettingSourceError",
  "SettingsNotFoundInSourceError",
  "SettingSourceNotFoundError",
  "SettingSourceReadError",
  "SettingSourceInvalidFormatError",
  "SettingSourceWriteError",
]


class SettingSourceError(Exception):
  pass


class SettingsNotFoundInSourceError(SettingSourceError):
  pass


class SettingSourceNotFoundError(SettingSourceError):
  pass


class SettingSourceReadError(SettingSourceError):
  pass


class SettingSourceInvalidFormatError(SettingSourceError):
  pass


class SettingSourceWriteError(SettingSourceError):
  pass
