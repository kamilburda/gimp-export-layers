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

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import unittest

from . import stubs_gimp

#===============================================================================


class TestPdbStub(unittest.TestCase):
  
  def setUp(self):
    self.pdb = stubs_gimp.PdbStub()
  
  def test_known_pdb_func(self):
    image = stubs_gimp.ImageStub()
    image.valid = False
    self.assertFalse(self.pdb.gimp_image_is_valid(image))
  
  def test_unknown_pdb_func(self):
    self.assertTrue(callable(self.pdb.plug_in_autocrop))
    self.assertEqual(self.pdb.plug_in_autocrop(), b"plug_in_autocrop")
    self.assertEqual(self.pdb.plug_in_autocrop("some random args", 1, 2, 3), b"plug_in_autocrop")
