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

import string
import os

import unittest

from .. import libfiles

#===============================================================================

class TestUniquifyString(unittest.TestCase):
  
  def test_uniquify_string(self):
    self.assertEqual('one (1)', libfiles.uniquify_string('one', ['one', 'two', 'three']))
    self.assertEqual('one (2)', libfiles.uniquify_string('one', ['one', 'one (1)', 'three']))
    self.assertEqual('one (1).jpg', libfiles.uniquify_string('one.jpg', ['one.jpg', 'two', 'three'],
                                                             place_before_file_extension=True))
    self.assertEqual('one (2).jpg', libfiles.uniquify_string('one.jpg', ['one.jpg', 'one (1).jpg', 'three'],
                                                             place_before_file_extension=True))
    self.assertEqual('one (1)', libfiles.uniquify_string('one', ['one', 'two', 'three'],
                                                         place_before_file_extension=True))
    self.assertEqual('one. (1)', libfiles.uniquify_string('one.', ['one.', 'two', 'three'],
                                                          place_before_file_extension=True))
    self.assertEqual('one. (1)', libfiles.uniquify_string('one.', ['one.', 'two', 'three']))
    self.assertEqual('one (1) (1)', libfiles.uniquify_string('one (1)', ['one (1)', 'two', 'three']))
    self.assertEqual('one (1) (1)', libfiles.uniquify_string('one (1)', ['one (1)', 'one (2)', 'three']))
    self.assertEqual('one (1) (1).jpg', libfiles.uniquify_string('one (1).jpg', ['one (1).jpg', 'two', 'three'],
                                                                 place_before_file_extension=True))


class TestGetFileExtension(unittest.TestCase):
  
  def test_get_file_extension(self):
    self.assertEqual("jpg", libfiles.get_file_extension("picture.jpg"))
    self.assertEqual("jpg", libfiles.get_file_extension("picture.JPG"))
    self.assertEqual("jpg", libfiles.get_file_extension("picture.jPg"))
    self.assertEqual("", libfiles.get_file_extension("picture."))
    self.assertEqual("", libfiles.get_file_extension("picture"))


class TestStringValidator(unittest.TestCase):
  
  def setUp(self):
    self.allowed_characters = string.ascii_letters + string.digits + " "
    self.validator = libfiles.StringValidator(self.allowed_characters)
  
  def test_validate(self):
    self.assertFalse(self.validator.is_valid("H:%#$#i *\There"))
    self.assertEqual(self.validator.validate("H:%#$#i *\There"), "Hi There")


class TestDirnameValidator(unittest.TestCase):
  
  def setUp(self):
    self.validator = libfiles.DirnameValidator()
  
  def test_validate(self):
    if os.name == 'nt':
      self.assertTrue(self.validator.is_valid(os.path.join("C:", os.sep, "Program Files", "test")))
      
      invalid_dirname = os.path.join("C:", os.sep, "/\\Progr:*?am Files", "test")
      valid_dirname = os.path.join("C:", os.sep, "Program Files", "test")
      self.assertEqual(self.validator.validate(invalid_dirname), valid_dirname)
    else:
      self.assertTrue(self.validator.is_valid(os.path.join(os.sep, "Program Files", "test")))
      
      invalid_dirname = os.path.join(os.sep, "/\\Progr:*?am Files", "test")
      valid_dirname = os.path.join(os.sep, "\\Program Files", "test")
      self.assertEqual(self.validator.validate(invalid_dirname), valid_dirname)
