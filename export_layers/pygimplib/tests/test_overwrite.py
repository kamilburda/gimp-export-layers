#-------------------------------------------------------------------------------
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
#-------------------------------------------------------------------------------

#===============================================================================

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division

str = unicode

#===============================================================================

import unittest

from .. import overwrite

#===============================================================================


class MockInteractiveOverwriteChooser(overwrite.InteractiveOverwriteChooser):
  
  def __init__(self, values_and_display_names, default_value, default_response):
    super(MockInteractiveOverwriteChooser, self).__init__(values_and_display_names, default_value, default_response)
    
    self._values = [value for value, unused_ in self.values_and_display_names]
  
  def _choose(self, filename):
    if self._overwrite_mode not in self._values:
      self._overwrite_mode = self.default_response
    
    return self._overwrite_mode
  
  def mock_set_overwrite_mode(self, overwrite_mode):
    self._overwrite_mode = overwrite_mode


#===============================================================================


class TestInteractiveOverwriteChooser(unittest.TestCase):
  
  def setUp(self):
    self.overwrite_modes = self.SKIP, self.REPLACE, self.RENAME_NEW, self.RENAME_EXISTING = (0, 1, 2, 3)
    self.values_and_display_names = [(self.SKIP, "Skip"), (self.REPLACE, "Replace"),
                                     (self.RENAME_NEW, "Rename new"), (self.RENAME_EXISTING, "Rename existing")]
    self.default_value = self.REPLACE
    self.default_response = self.SKIP
    self.overwrite_chooser = MockInteractiveOverwriteChooser(self.values_and_display_names, self.default_value,
                                                             self.default_response)
  
  def test_choose_overwrite_default_value(self):
    self.overwrite_chooser.choose()
    self.assertEqual(self.overwrite_chooser.overwrite_mode, self.default_value)

  def test_choose_overwrite(self):
    for mode in self.overwrite_modes:
      self.overwrite_chooser.mock_set_overwrite_mode(mode)
      self.overwrite_chooser.choose()
      self.assertEqual(self.overwrite_chooser.overwrite_mode, mode)
    
  def test_choose_overwrite_default_response(self):
    self.overwrite_chooser.mock_set_overwrite_mode(-1)
    self.overwrite_chooser.choose()
    self.assertEqual(self.overwrite_chooser.overwrite_mode, self.default_response)

