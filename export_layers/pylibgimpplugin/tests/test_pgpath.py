#-------------------------------------------------------------------------------
#
# This file is part of pylibgimpplugin.
#
# Copyright (C) 2014 khalim19 <khalim19@gmail.com>
#
# pylibgimpplugin is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pylibgimpplugin is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pylibgimpplugin.  If not, see <http://www.gnu.org/licenses/>.
#
#-------------------------------------------------------------------------------

#===============================================================================

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division

str = unicode

#===============================================================================

import os

import unittest

from .. import pgpath

#===============================================================================

class TestUniquifyString(unittest.TestCase):
  
  def test_uniquify_string(self):
    self.assertEqual('one (1)', pgpath.uniquify_string('one', ['one', 'two', 'three']))
    self.assertEqual('one (2)', pgpath.uniquify_string('one', ['one', 'one (1)', 'three']))
    self.assertEqual('one (1).jpg', pgpath.uniquify_string('one.jpg', ['one.jpg', 'two', 'three'],
                                                             place_before_file_extension=True))
    self.assertEqual('one (2).jpg', pgpath.uniquify_string('one.jpg', ['one.jpg', 'one (1).jpg', 'three'],
                                                             place_before_file_extension=True))
    self.assertEqual('one (1)', pgpath.uniquify_string('one', ['one', 'two', 'three'],
                                                         place_before_file_extension=True))
    self.assertEqual('one. (1)', pgpath.uniquify_string('one.', ['one.', 'two', 'three'],
                                                          place_before_file_extension=True))
    self.assertEqual('one. (1)', pgpath.uniquify_string('one.', ['one.', 'two', 'three']))
    self.assertEqual('one (1) (1)', pgpath.uniquify_string('one (1)', ['one (1)', 'two', 'three']))
    self.assertEqual('one (1) (1)', pgpath.uniquify_string('one (1)', ['one (1)', 'one (2)', 'three']))
    self.assertEqual('one (1) (1).jpg', pgpath.uniquify_string('one (1).jpg', ['one (1).jpg', 'two', 'three'],
                                                                 place_before_file_extension=True))


class TestGetFileExtension(unittest.TestCase):
  
  def test_get_file_extension(self):
    self.assertEqual("jpg", pgpath.get_file_extension("picture.jpg"))
    self.assertEqual("jpg", pgpath.get_file_extension("picture.JPG"))
    self.assertEqual("jpg", pgpath.get_file_extension("picture.jPg"))
    self.assertEqual("", pgpath.get_file_extension("picture."))
    self.assertEqual("", pgpath.get_file_extension("picture"))
    self.assertEqual("JPG", pgpath.get_file_extension("picture.JPG", to_lowercase=False))


class TestFilenameValidator(unittest.TestCase):
  
  def setUp(self):
    self.validator = pgpath.FilenameValidator
  
  def test_checks_if_filename_is_valid(self):
    self.assertEqual(self.validator.is_valid("one"), (True, []))
    self.assertTrue(self.validator.is_valid("0n3_two_,o_O_;-()three.jpg")[0])
    self.assertFalse(self.validator.is_valid("one/two\x09\x7f\\:|")[0])
    self.assertFalse(self.validator.is_valid("")[0])
    self.assertFalse(self.validator.is_valid(" one ")[0])
    self.assertFalse(self.validator.is_valid("one.")[0])
    self.assertTrue(self.validator.is_valid(".one")[0])
    self.assertFalse(self.validator.is_valid("NUL")[0])
    self.assertFalse(self.validator.is_valid("NUL.txt")[0])
    self.assertTrue(self.validator.is_valid("NUL (1)")[0])
    
  def test_validates_filename(self):
    self.assertEqual(self.validator.validate("one"), "one")
    self.assertEqual(self.validator.validate("0n3_two_,o_O_;-()three.jpg"), "0n3_two_,o_O_;-()three.jpg")
    self.assertEqual(self.validator.validate("one/two\x09\x7f\\:|"), "onetwo")
    self.assertEqual(self.validator.validate(""), "Untitled")
    self.assertEqual(self.validator.validate(" one "), "one")
    self.assertEqual(self.validator.validate("one."), "one")
    self.assertEqual(self.validator.validate(".one"), ".one")
    self.assertEqual(self.validator.validate("NUL"), "NUL (1)")
    self.assertEqual(self.validator.validate("NUL.txt"), "NUL (1).txt")
  

class TestFilePathValidator(unittest.TestCase):
  
  def setUp(self):
    self.validator = pgpath.FilePathValidator
  
  def test_checks_if_filepath_is_valid(self):
    self.assertEqual(self.validator.is_valid(os.path.join("one", "two", "three")),
                     (True, []))
    self.assertTrue(self.validator.is_valid(
      os.path.join("zero", "0n3", "two", ",o_O_;-()" + os.sep + os.sep + os.sep, "three.jpg" + os.sep))[0])
    self.assertFalse(self.validator.is_valid(
      os.path.join("one", "two", "\x09\x7f", ":|"))[0])
    self.assertFalse(self.validator.is_valid(
      os.path.join("one", ":two", "three"))[0])
    
    if os.name == 'nt':
      self.assertTrue(self.validator.is_valid(
        os.path.join("C:" + os.sep + "two", "three"))[0])
    else:
      self.assertFalse(self.validator.is_valid(
        os.path.join("C:" + os.sep + "two", "three"))[0])
    
    self.assertFalse(self.validator.is_valid(
      os.path.join("C:|" + os.sep + "two", "three"))[0])
    self.assertFalse(self.validator.is_valid(
      os.path.join(" one", "two", "three "))[0])
    self.assertFalse(self.validator.is_valid(
      os.path.join("one", "two ", "three"))[0])
    self.assertFalse(self.validator.is_valid(
      os.path.join("one", "two", "three."))[0])
    self.assertFalse(self.validator.is_valid(
      os.path.join("one.", "two.", "three"))[0])
    self.assertTrue(self.validator.is_valid(
      os.path.join(".one", "two", ".three"))[0])
    self.assertFalse(self.validator.is_valid(
      os.path.join("one", "two", "NUL"))[0])
    self.assertFalse(self.validator.is_valid(
      os.path.join("one", "two", "NUL.txt"))[0])
    self.assertFalse(self.validator.is_valid(
      os.path.join("one", "NUL", "three"))[0])
    self.assertTrue(self.validator.is_valid(
      os.path.join("one", "NUL (1)", "three"))[0])
    self.assertFalse(self.validator.is_valid("")[0])
  
  def test_validates_filepath(self):
    self.assertEqual(
      self.validator.validate(os.path.join("one", "two", "three")),
      os.path.join("one", "two", "three")
    )
    self.assertEqual(
      self.validator.validate(os.path.join("zero", "0n3", "two", ",o_O_;-()" +
                                           os.sep + os.sep + os.sep, "three.jpg" + os.sep)),
      os.path.join("zero", "0n3", "two", ",o_O_;-()", "three.jpg")
    )
    self.assertEqual(
      self.validator.validate(os.path.join("one", "two\x09\x7f", "three:|")),
      os.path.join("one", "two", "three")
    )
    self.assertEqual(
      self.validator.validate(os.path.join("one", ":two", "three")),
      os.path.join("one", "two", "three")
    )
    
    if os.name == 'nt':
      self.assertEqual(
        self.validator.validate(os.path.join("C:" + os.sep + "two", "three")),
        os.path.join("C:" + os.sep + "two", "three")
      )
      self.assertEqual(
        self.validator.validate(os.path.join("C:|one" + os.sep + "two", "three")),
        os.path.join("C:", "one", "two", "three")
      )
      self.assertEqual(self.validator.validate(os.path.join("C:|" + os.sep + "two", "three")),
                       os.path.join("C:", "two", "three"))
    else:
      self.assertEqual(
        self.validator.validate(os.path.join("C:" + os.sep + "two", "three")),
        os.path.join("C" + os.sep + "two", "three")
      )
      self.assertEqual(
        self.validator.validate(os.path.join("C:|one" + os.sep + "two", "three")),
        os.path.join("Cone", "two", "three")
      )
      self.assertEqual(self.validator.validate(os.path.join("C:|" + os.sep + "two", "three")),
                       os.path.join("C", "two", "three"))
    
    self.assertEqual(
      self.validator.validate(os.path.join(" one", "two", "three ")),
      os.path.join("one", "two", "three")
    )
    self.assertEqual(
      self.validator.validate(os.path.join("one", "two ", "three")),
      os.path.join("one", "two", "three")
    )
    self.assertEqual(
      self.validator.validate(os.path.join("one", "two", "three.")),
      os.path.join("one", "two", "three")
    )
    self.assertEqual(
      self.validator.validate(os.path.join("one.", "two.", "three")),
      os.path.join("one", "two", "three")
    )
    self.assertEqual(
      self.validator.validate(os.path.join(".one", "two", ".three")),
      os.path.join(".one", "two", ".three")
    )
    self.assertEqual(
      self.validator.validate(os.path.join("one", "two", "NUL")),
      os.path.join("one", "two", "NUL (1)")
    )
    self.assertEqual(
      self.validator.validate(os.path.join("one", "two", "NUL:|.txt")),
      os.path.join("one", "two", "NUL (1).txt")
    )
    self.assertEqual(
      self.validator.validate(os.path.join("one", "NUL", "three")),
      os.path.join("one", "NUL (1)", "three")
    )
    self.assertEqual(
      self.validator.validate(os.path.join("one", "NUL (1)", "three")),
      os.path.join("one", "NUL (1)", "three")
    )
    
    self.assertEqual(self.validator.validate(""), ".")
    self.assertEqual(self.validator.validate("|"), ".")
    self.assertEqual(self.validator.validate(os.path.join("one", ":|", "three")),
                     os.path.join("one", "three"))


class TestFileExtensionValidator(unittest.TestCase):
  
  def setUp(self):
    self.validator = pgpath.FileExtensionValidator
  
  def test_checks_if_filename_is_valid(self):
    self.assertEqual(self.validator.is_valid("jpg"), (True, []))
    self.assertTrue(self.validator.is_valid(".jpg")[0])
    self.assertTrue(self.validator.is_valid("tar.gz")[0])
    self.assertFalse(self.validator.is_valid("one/two\x09\x7f\\:|")[0])
    self.assertFalse(self.validator.is_valid("")[0])
    self.assertFalse(self.validator.is_valid(" jpg ")[0])
    self.assertFalse(self.validator.is_valid("jpg.")[0])
  
  def test_validates_filename(self):
    self.assertEqual(self.validator.validate("jpg"), "jpg")
    self.assertEqual(self.validator.validate(".jpg"), ".jpg")
    self.assertEqual(self.validator.validate("tar.gz"), "tar.gz")
    self.assertEqual(self.validator.validate("one/two\x09\x7f\\:|"), "onetwo")
    self.assertEqual(self.validator.validate(" jpg "), " jpg")
    self.assertEqual(self.validator.validate("jpg."), "jpg")
    
    self.assertEqual(self.validator.validate(""), "")
  