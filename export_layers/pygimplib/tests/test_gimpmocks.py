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

from . import gimpmocks

#===============================================================================


class TestMockPDB(unittest.TestCase):
  
  def setUp(self):
    self.pdb = gimpmocks.MockPDB()
  
  def test_known_pdb_func(self):
    image = gimpmocks.MockImage()
    image.valid = False
    self.assertFalse(self.pdb.gimp_image_is_valid(image))
  
  def test_unknown_pdb_func(self):
    self.assertTrue(callable(self.pdb.plug_in_autocrop))
    self.assertEqual(self.pdb.plug_in_autocrop(), b"plug_in_autocrop")
    self.assertEqual(self.pdb.plug_in_autocrop("some random args", 1, 2, 3),
                     b"plug_in_autocrop")
