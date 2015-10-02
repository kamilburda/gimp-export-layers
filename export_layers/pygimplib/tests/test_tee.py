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

import sys
from StringIO import StringIO

import unittest

from ..lib import mock

from .. import tee

#===============================================================================


@mock.patch("sys.stdout", new=StringIO())
class TestTee(unittest.TestCase):
  
  def setUp(self):
    self.string_file = StringIO()
  
  def test_write(self):
    tee.Tee(sys.stdout, self.string_file, log_header_title="Test Header")
    
    print("Hello")
    self.assertTrue(self.string_file.getvalue().endswith("Hello\n"))
    self.assertTrue("Test Header" in self.string_file.getvalue())
    
    print("Hi There Again")
    self.assertTrue(self.string_file.getvalue().endswith("Hello\nHi There Again\n"))
  
  def test_start_and_stop(self):
    tee_stdout = tee.Tee(sys.stdout, self.string_file, log_header_title="Test Header", start=False)
    
    print("Hi There")
    self.assertFalse(self.string_file.getvalue().endswith("Hi There\n"))
    
    tee_stdout.start(self.string_file)
    print("Hello")
    self.assertTrue(self.string_file.getvalue().endswith("Hello\n"))
    
    string_value = self.string_file.getvalue()
    tee_stdout.stop()
    print("Hi There Again")
    self.assertFalse(string_value.endswith("Hi There Again\n"))
  
  def test_invalid_stream(self):
    with self.assertRaises(ValueError):
      tee.Tee('invalid_stream', self.string_file, log_header_title="Test Header", start=False)
  