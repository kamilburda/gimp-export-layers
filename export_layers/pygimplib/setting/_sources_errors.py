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
This module defines exceptions used in `setting.sources` and `setting.persistor`
modules.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

__all__ = [
  "SourceError",
  "SettingsNotFoundInSourceError",
  "SourceNotFoundError",
  "SourceReadError",
  "SourceInvalidFormatError",
  "SourceWriteError",
]


class SourceError(Exception):
  pass


class SettingsNotFoundInSourceError(SourceError):
  
  def __init__(self, message, settings_not_found=None):
    super().__init__(message)
    
    self.settings_not_found = settings_not_found if settings_not_found is not None else []


class SourceNotFoundError(SourceError):
  pass


class SourceReadError(SourceError):
  pass


class SourceInvalidFormatError(SourceError):
  pass


class SourceWriteError(SourceError):
  pass
