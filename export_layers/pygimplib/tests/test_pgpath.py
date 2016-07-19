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

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

str = unicode

import datetime
import os
import unittest

from .. import pgpath

#===============================================================================


class TestUniquifyString(unittest.TestCase):
  
  def test_uniquify_string(self):
    self.assertEqual("one (1)", pgpath.uniquify_string("one", ["one", "two", "three"]))
    self.assertEqual("one (2)", pgpath.uniquify_string("one", ["one", "one (1)", "three"]))
    
    self.assertEqual("one. (1)", pgpath.uniquify_string("one.", ["one.", "two", "three"]))
    self.assertEqual("one (1) (1)", pgpath.uniquify_string("one (1)", ["one (1)", "two", "three"]))
    self.assertEqual("one (1) (1)", pgpath.uniquify_string("one (1)", ["one (1)", "one (2)", "three"]))
  
  def test_uniquify_string_insert_before_file_extension(self):
    
    def _get_file_extension_start_position(str_):
      position = str_.rfind(".")
      if position == -1:
        position = len(str_)
      return position
    
    def _test_uniquify_with_file_extension(input_str, existing_strings, expected_uniquified_str):
      self.assertEqual(expected_uniquified_str, pgpath.uniquify_string(
        input_str, existing_strings,
        _get_file_extension_start_position(input_str)))
    
    _test_uniquify_with_file_extension("one.jpg", ["one.jpg", "two", "three"],
                                       "one (1).jpg")
    _test_uniquify_with_file_extension("one.jpg", ["one.jpg", "one (1).jpg", "two", "three"],
                                       "one (2).jpg")
    _test_uniquify_with_file_extension("one", ["one", "two", "three"],
                                       "one (1)")
    _test_uniquify_with_file_extension("one.", ["one.", "two", "three"],
                                       "one (1).")
    _test_uniquify_with_file_extension("one (1).jpg", ["one (1).jpg", "two", "three"],
                                       "one (1) (1).jpg")
  
  def test_uniquify_string_insert_before_file_extension_with_periods(self):
    input_str = "one.xcf.gz"
    self.assertEqual("one (1).xcf.gz",
                     pgpath.uniquify_string(input_str, [input_str, "two", "three"],
                                            len(input_str) - len(".xcf.gz")))


#===============================================================================


class TestStringPatternGenerator(unittest.TestCase):
  
  def _test_generate(self, pattern, *expected_outputs):
    generator = pgpath.StringPatternGenerator(pattern)
    for output in expected_outputs:
      self.assertEqual(generator.generate(), output)
  
  def _test_generate_with_field(self, field_name, field_func, pattern, *expected_outputs):
    generator = pgpath.StringPatternGenerator(pattern, {field_name: field_func})
    for output in expected_outputs:
      self.assertEqual(generator.generate(), output)
  
  def _test_generate_with_fields(self, fields, pattern, *expected_outputs):
    generator = pgpath.StringPatternGenerator(pattern, fields)
    for output in expected_outputs:
      self.assertEqual(generator.generate(), output)
  
  def _test_generate_with_field_generator(self, field_name, field_generator_func, pattern, *expected_outputs):
    field_generator = field_generator_func()
    fields = {field_name: lambda: next(field_generator)}
    generator = pgpath.StringPatternGenerator(pattern, fields)
    for output in expected_outputs:
      self.assertEqual(generator.generate(), output)
  
  def test_generate_default_number_empty_pattern(self):
    self._test_generate("", "001", "002", "003", "004", "005", "006", "007", "008", "009", "010")

  def test_generate_default_number(self):
    self._test_generate("image", "image001", "image002", "image003")
  
  def test_generate_number(self):
    self._test_generate("image1", "image1", "image2")
    self._test_generate("image01", "image01", "image02")
    self._test_generate("image001", "image001", "image002")
    self._test_generate("001", "001", "002")
    self._test_generate("image005", "image005", "image006")
    self._test_generate("image9", "image9", "image10")
    self._test_generate("image09", "image09", "image10")
    self._test_generate("image_001", "image_001", "image_002")
    self._test_generate("001image", "001image", "002image")
    self._test_generate("001_image", "001_image", "002_image")
    self._test_generate("image_001001", "image_001001", "image_001002")
    self._test_generate("image_001_001", "image_001_001", "image_001_002")
    self._test_generate("001_001_image", "001_001_image", "002_001_image")
    self._test_generate("001_image_001", "001_image_001", "001_image_002")
    self._test_generate("image_pwn3r_001", "image_pwn3r_001", "image_pwn3r_002")
    self._test_generate("image_pwn3r", "image_pwn3r001", "image_pwn3r002")
    self._test_generate("image_pwn3r1337", "image_pwn3r1337", "image_pwn3r1338")
    self._test_generate("001_image_pwn3r", "001_image_pwn3r", "002_image_pwn3r")
    self._test_generate("001image_pwn3r", "001image_pwn3r", "002image_pwn3r")
    self._test_generate("image_001_pwn3r", "image_001_pwn3r001", "image_001_pwn3r002")
    
  def test_generate_with_fields(self):
    def _get_layer_name():
      for layer_name in ["layer one", "layer two", "layer three"]:
        yield layer_name
    
    self._test_generate_with_field_generator(
      "layer name", _get_layer_name, "[layer name]_001",
      "layer one_001", "layer two_002", "layer three_003")
    self._test_generate_with_field_generator(
      "layer name", _get_layer_name, "[layer name]",
      "layer one", "layer two", "layer three")
    self._test_generate_with_field_generator(
      "layer name", _get_layer_name, "[layer name]_[layer name]_001",
      "layer one_layer two_001")
    self._test_generate_with_field_generator(
      "layer name", _get_layer_name, "[layer name][layer name]_001",
      "layer onelayer two_001")
    
    self._test_generate_with_fields(
      {"field1": lambda: "value1", "field2": lambda: "value2", "field3": lambda: "value3"},
      "image_[field1][field2]_[field3]_001",
      "image_value1value2_value3_001", "image_value1value2_value3_002", "image_value1value2_value3_003")
    
    self._test_generate_with_fields(
      {"field": lambda arg1, arg2: "value" + str(arg1) + str(arg2), "bar": lambda: "another value"},
      ("Hi there [field, 1, 2][another field][another field]_[another field], "
       "I am [bar] and [bazbaz] and this is [001] and [baz]"),
      ("Hi there value12[another field][another field]_[another field], "
       "I am another value and [bazbaz] and this is 001 and [baz]"),
      ("Hi there value12[another field][another field]_[another field], "
       "I am another value and [bazbaz] and this is 002 and [baz]"),
      ("Hi there value12[another field][another field]_[another field], "
       "I am another value and [bazbaz] and this is 003 and [baz]"),)
    
    self._test_generate_with_field_generator(
      "different field", _get_layer_name, "[layer name]_001",
      "[layer name]_001", "[layer name]_002", "[layer name]_003")
    self._test_generate_with_field_generator(
      "layer name", _get_layer_name, "[unrecognized field]_001",
      "[unrecognized field]_001", "[unrecognized field]_002", "[unrecognized field]_003")
    self._test_generate_with_field_generator(
      "[layer name]", _get_layer_name, "[layer name]_001",
      "[layer name]_001", "[layer name]_002", "[layer name]_003")
    
    self._test_generate_with_field_generator(
      "layer name", _get_layer_name, "[[layer name]]_001",
      "[layer name]_001", "[layer name]_002", "[layer name]_003")
    self._test_generate_with_field_generator(
      "layer name", _get_layer_name, "[[layer name]]",
      "[layer name]001", "[layer name]002", "[layer name]003")
    self._test_generate_with_field_generator(
      "layer name", _get_layer_name, "[layer name_001",
      "[layer name_001", "[layer name_002", "[layer name_003")
    self._test_generate_with_field_generator(
      "layer name", _get_layer_name, "[layer [name",
      "[layer [name001", "[layer [name002", "[layer [name003")
    self._test_generate_with_field_generator(
      "layer name", _get_layer_name, " [layer [name",
      " [layer [name001", " [layer [name002", " [layer [name003")
    self._test_generate_with_field_generator(
      "layer name", _get_layer_name, "[[layer name_001",
      "[layer name_001", "[layer name_002", "[layer name_003")
    self._test_generate_with_field_generator(
      "layer name", _get_layer_name, "[[layer [[name]]_[layer name]_001",
      "[layer [name]_layer one_001", "[layer [name]_layer two_002", "[layer [name]_layer three_003")
    
    self._test_generate_with_field_generator(
      "layer name", _get_layer_name, "[[layer name]_001",
      "[layer name]_001", "[layer name]_002", "[layer name]_003")
    self._test_generate_with_field_generator(
      "layer name", _get_layer_name, "layer name]_001",
      "layer name]_001", "layer name]_002", "layer name]_003")
    self._test_generate_with_field_generator(
      "layer name", _get_layer_name, "layer ]name]",
      "layer ]name]001", "layer ]name]002", "layer ]name]003")
    self._test_generate_with_field_generator(
      "layer name", _get_layer_name, "layer name]]_001",
      "layer name]_001", "layer name]_002", "layer name]_003")
    self._test_generate_with_field_generator(
      "layer name", _get_layer_name, "[[layer ]]name]]_[layer name]_001",
      "[layer ]name]_layer one_001", "[layer ]name]_layer two_002", "[layer ]name]_layer three_003")
    self._test_generate_with_field_generator(
      "layer name", _get_layer_name, "[layer name]]_001",
      "layer one]_001", "layer two]_002", "layer three]_003")
    
    self._test_generate_with_field_generator(
      "layer name", _get_layer_name, "[layer name[]_001",
      "[layer name[]_001", "[layer name[]_002", "[layer name[]_003")
    self._test_generate_with_field_generator(
      "layer name", _get_layer_name, "]layer name[]_001",
      "]layer name[]_001", "]layer name[]_002", "]layer name[]_003")
    self._test_generate_with_field_generator(
      "layer name", _get_layer_name, "]layer name][_001",
      "]layer name][_001", "]layer name][_002", "]layer name][_003")
    self._test_generate_with_field_generator(
      "layer name", _get_layer_name, "[layer name][_001",
      "layer one[_001", "layer two[_002", "layer three[_003")
    
    self._test_generate_with_field_generator(
      "layer name", _get_layer_name, "[[layer name]] [[layer name]]_001",
      "[layer name] [layer name]_001", "[layer name] [layer name]_002", "[layer name] [layer name]_003")
    self._test_generate_with_field_generator(
      "layer name", _get_layer_name, "[[layer name] [layer name]]_001",
      "[layer name] layer one]_001", "[layer name] layer two]_002", "[layer name] layer three]_003")
  
  def test_generate_with_number_field(self):
    self._test_generate_with_fields(
      {}, "image[001]",
      "image001", "image002", "image003")
    self._test_generate_with_fields(
      {}, "image[001]_2016-07-16",
      "image001_2016-07-16", "image002_2016-07-16", "image003_2016-07-16")
    self._test_generate_with_fields(
      {}, "image[001]_[01]_2016-07-16",
      "image001_01_2016-07-16", "image002_02_2016-07-16", "image003_03_2016-07-16")
  
  def test_generate_with_fields_with_args(self):
    def _get_date(date_format):
      return datetime.datetime(2016, 7, 16, hour=23).strftime(date_format)
    
    def _get_date_with_default(date_format="%d.%m.%Y"):
      return datetime.datetime(2016, 7, 16, hour=23).strftime(date_format)
    
    def _get_joined_args(separator, *args):
      return separator.join(args)
    
    self._test_generate_with_field(
      "date", _get_date, "[date, %Y-%m-%d]_001",
      "2016-07-16_001", "2016-07-16_002", "2016-07-16_003")
    self._test_generate_with_field(
      "joined args", _get_joined_args, "[joined args, -, one, two, three]_001",
      "one-two-three_001", "one-two-three_002", "one-two-three_003")
    self._test_generate_with_field(
      "joined args", _get_joined_args, "[joined args, -, [one], [two], [three],]_001",
      "one-two-three_001", "one-two-three_002", "one-two-three_003")
    
    self._test_generate_with_field(
      "joined args", _get_joined_args, "[joined args, -, [one, ], [two, ], [three, ],]_001",
      "one, -two, -three, _001", "one, -two, -three, _002", "one, -two, -three, _003")
    self._test_generate_with_field(
      "joined args", _get_joined_args, "[joined args, -, [[[one, ]]], [[[two, ]]], [[[three, ]]],]_001",
      "[one, ]-[two, ]-[three, ]_001", "[one, ]-[two, ]-[three, ]_002", "[one, ]-[two, ]-[three, ]_003")
    self._test_generate_with_field(
      "joined args", _get_joined_args, "[joined args, -, [one[, ]_001",
      "[joined args, -, [one[, ]_001", "[joined args, -, [one[, ]_002", "[joined args, -, [one[, ]_003")
    self._test_generate_with_field(
      "joined args", _get_joined_args, "[joined args, -, [on[[e], [t[[w]]o], [thre]]e],]_001",
      "on[e-t[w]o-thre]e_001", "on[e-t[w]o-thre]e_002", "on[e-t[w]o-thre]e_003")
    
    self._test_generate_with_field(
      "date", _get_date, "[date]_001",
      "[date]_001", "[date]_002", "[date]_003")
    self._test_generate_with_field(
      "date", _get_date, "[date, %Y-%m-%d, more_args]_001",
      "[date, %Y-%m-%d, more_args]_001", "[date, %Y-%m-%d, more_args]_002", "[date, %Y-%m-%d, more_args]_003")
    
    self._test_generate_with_field(
      "date", _get_date_with_default, "[date, %Y-%m-%d]_001",
      "2016-07-16_001", "2016-07-16_002", "2016-07-16_003")
    self._test_generate_with_field(
      "date", _get_date_with_default, "[date]_001",
      "16.07.2016_001", "16.07.2016_002", "16.07.2016_003")
    self._test_generate_with_field(
      "date", _get_date_with_default, "[date, ]_001",
      "16.07.2016_001", "16.07.2016_002", "16.07.2016_003")
    self._test_generate_with_field(
      "date", _get_date_with_default, "[date, %Y-%m-%d, more_args]_001",
      "[date, %Y-%m-%d, more_args]_001", "[date, %Y-%m-%d, more_args]_002", "[date, %Y-%m-%d, more_args]_003")
  
  def test_generate_with_fields_invalid_field_function(self):
    def _get_joined_kwargs_values(separator, **kwargs):
      return separator.join(list(kwargs.values()))
    
    with self.assertRaises(ValueError):
      pgpath.StringPatternGenerator("[joined kwargs, -]_001", {"joined kwargs": _get_joined_kwargs_values})
    

#===============================================================================


class TestGetFileExtension(unittest.TestCase):
  
  def test_get_file_extension(self):
    self.assertEqual("jpg", pgpath.get_file_extension("picture.jpg"))
    self.assertEqual("jpg", pgpath.get_file_extension("picture.JPG"))
    self.assertEqual("jpg", pgpath.get_file_extension("picture.jPg"))
    self.assertEqual("", pgpath.get_file_extension("picture."))
    self.assertEqual("", pgpath.get_file_extension("picture"))
    self.assertEqual("JPG", pgpath.get_file_extension("picture.JPG", to_lowercase=False))


#===============================================================================


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
    
    if os.name == "nt":
      self.assertTrue(self.validator.is_valid(
        os.path.join("C:" + os.sep + "two", "three"))[0])
    else:
      self.assertFalse(self.validator.is_valid(
        os.path.join("C:" + os.sep + "two", "three"))[0])
    
    self.assertFalse(self.validator.is_valid(
      os.path.join("C:|" + os.sep + "two", "three"))[0])
    self.assertFalse(self.validator.is_valid(
      os.path.join(" one", "two", "three "))[0])
    self.assertTrue(self.validator.is_valid(
      os.path.join("one", " two", "three"))[0])
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
    
    if os.name == "nt":
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
