# -*- coding: utf-8 -*-
#
# Copyright (C) 2014-2017 khalim19
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

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import unittest

from .. import pgoverwrite

#===============================================================================


class InteractiveOverwriteChooserStub(pgoverwrite.InteractiveOverwriteChooser):
  
  def __init__(self, values_and_display_names, default_value, default_response):
    super().__init__(
      values_and_display_names, default_value, default_response)
    
    self._values = [value for value, unused_ in self.values_and_display_names]
  
  def _choose(self, filename):
    if self._overwrite_mode not in self._values:
      self._overwrite_mode = self.default_response
    
    return self._overwrite_mode
  
  def set_overwrite_mode(self, overwrite_mode):
    self._overwrite_mode = overwrite_mode


#===============================================================================


class TestInteractiveOverwriteChooser(unittest.TestCase):

  _OVERWRITE_MODES = SKIP, REPLACE, RENAME_NEW, RENAME_EXISTING = (0, 1, 2, 3)
  
  def setUp(self):
    self.values_and_display_names = [
      (self.SKIP, "Skip"), (self.REPLACE, "Replace"),
      (self.RENAME_NEW, "Rename new"), (self.RENAME_EXISTING, "Rename existing")]
    self.default_value = self.REPLACE
    self.default_response = self.SKIP
    self.overwrite_chooser = InteractiveOverwriteChooserStub(
      self.values_and_display_names, self.default_value, self.default_response)
  
  def test_choose_overwrite_default_value(self):
    self.overwrite_chooser.choose()
    self.assertEqual(self.overwrite_chooser.overwrite_mode, self.default_value)

  def test_choose_overwrite(self):
    for mode in self._OVERWRITE_MODES:
      self.overwrite_chooser.set_overwrite_mode(mode)
      self.overwrite_chooser.choose()
      self.assertEqual(self.overwrite_chooser.overwrite_mode, mode)
    
  def test_choose_overwrite_default_response(self):
    self.overwrite_chooser.set_overwrite_mode(-1)
    self.overwrite_chooser.choose()
    self.assertEqual(self.overwrite_chooser.overwrite_mode, self.default_response)
