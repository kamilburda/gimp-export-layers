#-------------------------------------------------------------------------------
#
# This file is part of libgimpplugin.
#
# Copyright (C) 2014 khalim19 <khalim19@gmail.com>
# 
# libgimpplugin is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# libgimpplugin is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with libgimpplugin.  If not, see <http://www.gnu.org/licenses/>.
#
#-------------------------------------------------------------------------------

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
    self.assertEqual(self.pdb.plug_in_autocrop(), "plug_in_autocrop")
    self.assertEqual(self.pdb.plug_in_autocrop("some random args", 1, 2, 3),
                     "plug_in_autocrop")
