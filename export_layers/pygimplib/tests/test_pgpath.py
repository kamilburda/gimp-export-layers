# -*- coding: utf-8 -*-
#
# Copyright (C) 2014-2018 khalim19
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

import datetime
import os
import unittest

from .. import pgpath

#===============================================================================


class TestUniquifyString(unittest.TestCase):
  
  def test_uniquify_string(self):
    self.assertEqual(
      pgpath.uniquify_string("one", ["one", "two", "three"]), "one (1)")
    self.assertEqual(
      pgpath.uniquify_string("one", ["one", "one (1)", "three"]), "one (2)")
    
    self.assertEqual(
      pgpath.uniquify_string("one.", ["one.", "two", "three"]), "one. (1)")
    self.assertEqual(
      pgpath.uniquify_string("one (1)", ["one (1)", "two", "three"]), "one (1) (1)")
    self.assertEqual(
      pgpath.uniquify_string("one (1)", ["one (1)", "one (2)", "three"]), "one (1) (1)")
  
  def test_uniquify_string_insert_before_file_extension(self):
    
    def _get_file_extension_start_position(str_):
      position = str_.rfind(".")
      if position == -1:
        position = len(str_)
      return position
    
    def _test_uniquify_with_file_extension(
          input_str, existing_strings, expected_uniquified_str):
      self.assertEqual(
        pgpath.uniquify_string(
          input_str, existing_strings, _get_file_extension_start_position(input_str)),
        expected_uniquified_str)
    
    _test_uniquify_with_file_extension(
      "one.jpg", ["one.jpg", "two", "three"], "one (1).jpg")
    _test_uniquify_with_file_extension(
      "one.jpg", ["one.jpg", "one (1).jpg", "two", "three"], "one (2).jpg")
    _test_uniquify_with_file_extension(
      "one", ["one", "two", "three"], "one (1)")
    _test_uniquify_with_file_extension(
      "one.", ["one.", "two", "three"], "one (1).")
    _test_uniquify_with_file_extension(
      "one (1).jpg", ["one (1).jpg", "two", "three"], "one (1) (1).jpg")
  
  def test_uniquify_string_insert_before_file_extension_with_periods(self):
    input_str = "one.xcf.gz"
    self.assertEqual(
      "one (1).xcf.gz",
      pgpath.uniquify_string(
        input_str, [input_str, "two", "three"], len(input_str) - len(".xcf.gz")))


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
  
  def _test_generate_with_field_generator(
        self, field_name, field_generator_func, pattern, *expected_outputs):
    field_generator = field_generator_func()
    fields = {field_name: lambda: next(field_generator)}
    generator = pgpath.StringPatternGenerator(pattern, fields)
    for output in expected_outputs:
      self.assertEqual(generator.generate(), output)
  
  def _test_reset_numbering(self, pattern, *expected_outputs):
    generator = pgpath.StringPatternGenerator(pattern)
    for unused_ in range(3):
      generator.generate()
    generator.reset_numbering()
    for output in expected_outputs:
      self.assertEqual(generator.generate(), output)
  
  def _test_set_number_generator(self, pattern, *expected_outputs):
    generator = pgpath.StringPatternGenerator(pattern)
    for unused_ in range(3):
      generator.generate()
    number_generators = generator.get_number_generators()
    generator.reset_numbering()
    generator.set_number_generators(number_generators)
    for output in expected_outputs:
      self.assertEqual(generator.generate(), output)
  
  def test_generate(self):
    self._test_generate("", "")
    self._test_generate("image", "image")
    self._test_generate("image001", "image001", "image001")
    self._test_generate("001", "001", "001")
    self._test_generate("001_image_001", "001_image_001", "001_image_001")
    
  def test_generate_with_fields(self):
    def _get_layer_name():
      for layer_name in ["layer one", "layer two", "layer three"]:
        yield layer_name
    
    self._test_generate_with_field_generator(
      "layer name", _get_layer_name,
      "[layer name]", "layer one", "layer two", "layer three")
    self._test_generate_with_field_generator(
      "layer name", _get_layer_name,
      "[layer name]_001", "layer one_001", "layer two_001", "layer three_001")
    self._test_generate_with_field_generator(
      "layer name", _get_layer_name,
      "[layer name]_[layer name]", "layer one_layer two")
    
    self._test_generate_with_fields(
      {"field1": lambda: "value1",
       "field2": lambda: "value2",
       "field3": lambda: "value3"},
      "image_[field1][field2]_[field3]",
      "image_value1value2_value3",
      "image_value1value2_value3",
      "image_value1value2_value3")
    
    self._test_generate_with_fields(
      {"field": lambda arg1, arg2: "value" + str(arg1) + str(arg2),
       "bar": lambda: "another value"},
      ("Hi there [field, 1, 2][another field][another field]_[another field], "
       "I am [bar] and [bazbaz] and this is [001] and [baz]"),
      ("Hi there value12[another field][another field]_[another field], "
       "I am another value and [bazbaz] and this is 001 and [baz]"),
      ("Hi there value12[another field][another field]_[another field], "
       "I am another value and [bazbaz] and this is 002 and [baz]"),
      ("Hi there value12[another field][another field]_[another field], "
       "I am another value and [bazbaz] and this is 003 and [baz]"),)
    
    self._test_generate_with_field_generator(
      "different field", _get_layer_name, "[layer name]", "[layer name]")
    self._test_generate_with_field_generator(
      "layer name", _get_layer_name, "[unrecognized field]", "[unrecognized field]")
    self._test_generate_with_field_generator(
      "[layer name]", _get_layer_name, "[layer name]", "[layer name]")
    
    self._test_generate_with_field_generator(
      "layer name", _get_layer_name, "[[layer name]]", "[layer name]")
    self._test_generate_with_field_generator(
      "layer name", _get_layer_name, "[layer name", "[layer name")
    self._test_generate_with_field_generator(
      "layer name", _get_layer_name, "[layer [name", "[layer [name")
    self._test_generate_with_field_generator(
      "layer name", _get_layer_name, "[[layer name", "[layer name")
    self._test_generate_with_field_generator(
      "layer name", _get_layer_name, "[[layer [[name]]_[layer name]",
      "[layer [name]_layer one")
    self._test_generate_with_field_generator(
      "layer name", _get_layer_name, "[[layer name]", "[layer name]")
    self._test_generate_with_field_generator(
      "layer name", _get_layer_name, "layer name]", "layer name]")
    self._test_generate_with_field_generator(
      "layer name", _get_layer_name, "layer ]name]", "layer ]name]")
    self._test_generate_with_field_generator(
      "layer name", _get_layer_name, "layer name]]", "layer name]")
    self._test_generate_with_field_generator(
      "layer name", _get_layer_name, "[[layer ]]name]]_[layer name]",
      "[layer ]name]_layer one")
    self._test_generate_with_field_generator(
      "layer name", _get_layer_name, "[layer name]]", "layer one]")
    self._test_generate_with_field_generator(
      "layer name", _get_layer_name, "[layer name[]", "[layer name[]")
    self._test_generate_with_field_generator(
      "layer name", _get_layer_name, "]layer name[]", "]layer name[]")
    self._test_generate_with_field_generator(
      "layer name", _get_layer_name, "]layer name][", "]layer name][")
    self._test_generate_with_field_generator(
      "layer name", _get_layer_name, "[layer name][", "layer one[",
      "layer two[", "layer three[")
    self._test_generate_with_field_generator(
      "layer name", _get_layer_name, "[[layer name]] [[layer name]]",
      "[layer name] [layer name]")
    self._test_generate_with_field_generator(
      "layer name", _get_layer_name, "[[layer name] [layer name]]",
      "[layer name] layer one]", "[layer name] layer two]",
      "[layer name] layer three]")
  
  def test_generate_with_number_field(self):
    self._test_generate_with_fields(
      {}, "image[001]", "image001", "image002", "image003")
    self._test_generate_with_fields(
      {}, "image[01]", "image01", "image02", "image03")
    self._test_generate_with_fields(
      {}, "image[009]", "image009", "image010", "image011")
    self._test_generate_with_fields(
      {}, "image[001]_[001]", "image001_002", "image003_004", "image005_006")
    self._test_generate_with_fields(
      {}, "image[001]_2016-07-16",
      "image001_2016-07-16", "image002_2016-07-16", "image003_2016-07-16")
    self._test_generate_with_fields(
      {}, "image[001]_[05]_2016-07-16",
      "image001_05_2016-07-16", "image002_06_2016-07-16", "image003_07_2016-07-16")
  
  def test_generate_with_fields_with_args(self):
    def _get_date(date_format):
      return datetime.datetime(2016, 7, 16, hour=23).strftime(date_format)
    
    def _get_date_with_default(date_format="%d.%m.%Y"):
      return datetime.datetime(2016, 7, 16, hour=23).strftime(date_format)
    
    def _get_joined_args(separator, *args):
      return separator.join(args)
    
    self._test_generate_with_field(
      "date", _get_date, "[date, %Y-%m-%d]", "2016-07-16")
    self._test_generate_with_field(
      "joined args", _get_joined_args,
      "[joined args, -, one, two, three]", "one-two-three")
    self._test_generate_with_field(
      "joined args", _get_joined_args,
      "[joined args, -, [one], [two], [three],]", "one-two-three")
    self._test_generate_with_field(
      "joined args", _get_joined_args,
      "[joined args, -, [one, ], [two, ], [three, ],]", "one, -two, -three, ")
    self._test_generate_with_field(
      "joined args", _get_joined_args,
      "[joined args, -, [[[one, ]]], [[[two, ]]], [[[three, ]]],]",
      "[one, ]-[two, ]-[three, ]")
    self._test_generate_with_field(
      "joined args", _get_joined_args,
      "[joined args, -, [one[, ]", "[joined args, -, [one[, ]")
    self._test_generate_with_field(
      "joined args", _get_joined_args,
      "[joined args, -, [on[[e], [t[[w]]o], [thre]]e],]", "on[e-t[w]o-thre]e")
    
    self._test_generate_with_field(
      "date", _get_date, "[date]", "[date]")
    self._test_generate_with_field(
      "date", _get_date, "[date, %Y-%m-%d, more_args]", "[date, %Y-%m-%d, more_args]")
    
    self._test_generate_with_field(
      "date", _get_date_with_default, "[date, %Y-%m-%d]", "2016-07-16")
    self._test_generate_with_field(
      "date", _get_date_with_default, "[date]", "16.07.2016")
    self._test_generate_with_field(
      "date", _get_date_with_default, "[date, ]", "16.07.2016")
    self._test_generate_with_field(
      "date", _get_date_with_default,
      "[date, %Y-%m-%d, more_args]", "[date, %Y-%m-%d, more_args]")
  
  def test_generate_with_fields_with_bound_method(self):
    class _DateGenerator(object):
      @staticmethod
      def get_date(date_format):
        return datetime.datetime(2016, 7, 16, hour=23).strftime(date_format)
    
    self._test_generate_with_field(
      "date", _DateGenerator().get_date, "[date, %Y-%m-%d]", "2016-07-16")
  
  def test_generate_with_fields_with_invalid_arguments(self):
    def _get_invalid_date(date_format):
      raise ValueError("invalid date format {}".format(date_format))
    
    self._test_generate_with_field(
      "date", _get_invalid_date, "[date, %Y-%m-%d]", "[date, %Y-%m-%d]")
  
  def test_generate_with_fields_invalid_field_function(self):
    def _get_joined_kwargs_values(separator, **kwargs):
      return separator.join(kwargs.values())
    
    with self.assertRaises(ValueError):
      pgpath.StringPatternGenerator(
        "[joined kwargs, -]", {"joined kwargs": _get_joined_kwargs_values})
  
  def test_reset_numbering(self):
    self._test_reset_numbering("image[001]", "image001", "image002")
    self._test_reset_numbering("image[005]", "image005", "image006")
    self._test_reset_numbering("image[999]", "image999", "image1000")
    self._test_reset_numbering("image[001]_[001]", "image001_002", "image003_004")
    self._test_reset_numbering("image[001]_[005]", "image001_005", "image002_006")
  
  def test_set_number_generator(self):
    self._test_set_number_generator("image[001]", "image004", "image005")
    self._test_set_number_generator("image[001]_[001]", "image007_008", "image009_010")
    self._test_set_number_generator("image[001]_[005]", "image004_008", "image005_009")
  
    generator = pgpath.StringPatternGenerator("image[001]")
    with self.assertRaises(ValueError):
      generator.set_number_generators([])
    with self.assertRaises(ValueError):
      generator.set_number_generators([object(), object()])
  
  def test_get_field_at_position(self):
    get_field_at_position = pgpath.StringPatternGenerator.get_field_at_position
    
    self.assertEqual(get_field_at_position("", 0), None)
    self.assertEqual(get_field_at_position("image001", 0), None)
    self.assertEqual(get_field_at_position("image001", 5), None)
    self.assertEqual(get_field_at_position("[layer name]", 0), None)
    self.assertEqual(get_field_at_position("[layer name]", 1), "layer name")
    self.assertEqual(get_field_at_position("[layer name]", 5), "layer name")
    self.assertEqual(get_field_at_position("[layer name]", 11), "layer name")
    self.assertEqual(get_field_at_position("[layer name]", 12), None)
    self.assertEqual(get_field_at_position("[[layer name]", 1), None)
    self.assertEqual(get_field_at_position("[[layer name]", 2), None)
    self.assertEqual(get_field_at_position("[[layer name]", 3), None)
    self.assertEqual(get_field_at_position("[[[layer name]", 1), None)
    self.assertEqual(get_field_at_position("[[[layer name]", 2), None)
    self.assertTrue(get_field_at_position("[[[layer name]", 3), "layer name")
    
    self.assertEqual(get_field_at_position("layer [name]", 2), None)
    self.assertEqual(get_field_at_position("layer [name]", 6), None)
    self.assertEqual(get_field_at_position("layer [name]", 7), "name")
    self.assertEqual(get_field_at_position("layer [name] name", 7), "name")
    self.assertEqual(
      get_field_at_position("layer [name][layer] name", 7), "name")
    self.assertEqual(
      get_field_at_position("layer [name][layer] name", 13), "layer")
    self.assertEqual(
      get_field_at_position("layer [name] [layer] name", 7), "name")
    self.assertEqual(
      get_field_at_position("layer [name] [layer] name", 14), "layer")
    self.assertEqual(get_field_at_position("layer [name] [layer] name", 13), None)
    
    self.assertEqual(get_field_at_position("layer [[layer [[ name]", 2), None)
    self.assertEqual(get_field_at_position("layer [[layer [[ name]", 6), None)
    self.assertEqual(get_field_at_position("layer [[layer [[ name]", 7), None)
    self.assertEqual(get_field_at_position("layer [[layer [[ name]", 8), None)
    self.assertEqual(get_field_at_position("layer [[layer [[ name]", 14), None)
    self.assertEqual(get_field_at_position("layer [[layer [[ name]", 15), None)
    self.assertEqual(get_field_at_position("layer [[layer [[ name]", 16), None)
    self.assertEqual(get_field_at_position("layer [[layer [[[name]", 16), None)
    self.assertEqual(
      get_field_at_position("layer [[layer [[[name]", 17), "name")
    
    self.assertEqual(get_field_at_position("[layer name", 0), None)
    self.assertEqual(get_field_at_position("[layer name", 1), None)
    self.assertEqual(get_field_at_position("[layer [name", 7), None)
    self.assertEqual(get_field_at_position("[layer [name", 8), None)
    
    self.assertEqual(get_field_at_position("[layer name]", 100), None)
    self.assertEqual(get_field_at_position("[layer name]", -1), None)


#===============================================================================


class TestGetFileExtension(unittest.TestCase):

  def test_nominal_case(self):
    self.assertEqual(pgpath.get_file_extension("background.jpg"), "jpg")
  
  def test_return_lowercase(self):
    self.assertEqual(pgpath.get_file_extension("background.JPG"), "jpg")
  
  def test_string_beginning_with_period(self):
    self.assertEqual(pgpath.get_file_extension(".jpg"), "jpg")
  
  def test_no_extension(self):
    self.assertEqual(pgpath.get_file_extension("main-background"), "")
    self.assertEqual(pgpath.get_file_extension("main-background."), "")
    self.assertEqual(pgpath.get_file_extension("."), "")
  
  def test_unrecognized_extension(self):
    self.assertEqual(pgpath.get_file_extension("main-background.aaa"), "aaa")
    self.assertEqual(pgpath.get_file_extension(".aaa"), "aaa")
  
  def test_multiple_periods(self):
    self.assertEqual(pgpath.get_file_extension("main-background.xcf.bz2"), "xcf.bz2")
  
  def test_multiple_periods_unrecognized_extension(self):
    self.assertEqual(pgpath.get_file_extension("main-background.aaa.bbb"), "bbb")


class TestGetFilenameWithNewFileExtension(unittest.TestCase):
  
  def test_nominal_case(self):
    self.assertEqual(
      pgpath.get_filename_with_new_file_extension("background.jpg", "png"),
      "background.png")
    self.assertEqual(
      pgpath.get_filename_with_new_file_extension("background.jpg", ".png"),
      "background.png")
    self.assertEqual(
      pgpath.get_filename_with_new_file_extension("background.", "png"),
      "background.png")
  
  def test_set_lowercase(self):
    self.assertEqual(
      pgpath.get_filename_with_new_file_extension("background.jpg", "PNG"),
      "background.png")
  
  def test_no_extension(self):
    self.assertEqual(
      pgpath.get_filename_with_new_file_extension("background.jpg", None),
      "background")
    self.assertEqual(
      pgpath.get_filename_with_new_file_extension("background.jpg", "."),
      "background")
  
  def test_from_multiple_periods(self):
    self.assertEqual(
      pgpath.get_filename_with_new_file_extension("background.xcf.bz2", "png"),
      "background.png")
  
  def test_from_single_period_within_multiple_periods(self):
    self.assertEqual(
      pgpath.get_filename_with_new_file_extension(
        "background.aaa.jpg", "png"), "background.aaa.png")
  
  def test_multiple_consecutive_periods(self):
    self.assertEqual(
      pgpath.get_filename_with_new_file_extension("background..jpg", "png"),
      "background..png")
  
  def test_remove_trailing_periods(self):
    self.assertEqual(
      pgpath.get_filename_with_new_file_extension("background.", "png"),
      "background.png")
  
  def test_keep_extra_trailing_periods(self):
    self.assertEqual(
      pgpath.get_filename_with_new_file_extension("background.", "png", True),
      "background..png")
    self.assertEqual(
      pgpath.get_filename_with_new_file_extension("background..", "png", True),
      "background...png")


#===============================================================================


class TestFilenameValidator(unittest.TestCase):
  
  def setUp(self):
    self.validator = pgpath.FilenameValidator
  
  def test_is_valid(self):
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
    
  def test_validate(self):
    self.assertEqual(self.validator.validate("one"), "one")
    self.assertEqual(
      self.validator.validate("0n3_two_,o_O_;-()three.jpg"),
      "0n3_two_,o_O_;-()three.jpg")
    self.assertEqual(self.validator.validate("one/two\x09\x7f\\:|"), "onetwo")
    self.assertEqual(self.validator.validate(""), "Untitled")
    self.assertEqual(self.validator.validate(" one "), "one")
    self.assertEqual(self.validator.validate("one."), "one")
    self.assertEqual(self.validator.validate(".one"), ".one")
    self.assertEqual(self.validator.validate("NUL"), "NUL (1)")
    self.assertEqual(self.validator.validate("NUL.txt"), "NUL (1).txt")
  

class TestFilepathValidator(unittest.TestCase):
  
  def setUp(self):
    self.validator = pgpath.FilepathValidator
  
  def test_is_valid(self):
    self.assertEqual(
      self.validator.is_valid(os.path.join("one", "two", "three")), (True, []))
    self.assertTrue(
      self.validator.is_valid(
        os.path.join(
          "zero", "0n3", "two", ",o_O_;-()" + os.sep + os.sep + os.sep,
          "three.jpg" + os.sep))[0])
    self.assertFalse(
      self.validator.is_valid(os.path.join("one", "two", "\x09\x7f", ":|"))[0])
    self.assertFalse(
      self.validator.is_valid(os.path.join("one", ":two", "three"))[0])
    
    if os.name == "nt":
      self.assertTrue(
        self.validator.is_valid(os.path.join("C:" + os.sep + "two", "three"))[0])
    else:
      self.assertFalse(
        self.validator.is_valid(os.path.join("C:" + os.sep + "two", "three"))[0])
    
    self.assertFalse(
      self.validator.is_valid(os.path.join("C:|" + os.sep + "two", "three"))[0])
    self.assertFalse(self.validator.is_valid(os.path.join(" one", "two", "three "))[0])
    self.assertTrue(self.validator.is_valid(os.path.join("one", " two", "three"))[0])
    self.assertFalse(self.validator.is_valid(os.path.join("one", "two ", "three"))[0])
    self.assertFalse(self.validator.is_valid(os.path.join("one", "two", "three."))[0])
    self.assertFalse(self.validator.is_valid(os.path.join("one.", "two.", "three"))[0])
    self.assertTrue(self.validator.is_valid(os.path.join(".one", "two", ".three"))[0])
    self.assertFalse(self.validator.is_valid(os.path.join("one", "two", "NUL"))[0])
    self.assertFalse(self.validator.is_valid(os.path.join("one", "two", "NUL.txt"))[0])
    self.assertFalse(self.validator.is_valid(os.path.join("one", "NUL", "three"))[0])
    self.assertTrue(self.validator.is_valid(os.path.join("one", "NUL (1)", "three"))[0])
    self.assertFalse(self.validator.is_valid("")[0])
  
  def test_validate(self):
    self.assertEqual(
      self.validator.validate(os.path.join("one", "two", "three")),
      os.path.join("one", "two", "three"))
    self.assertEqual(
      self.validator.validate(
        os.path.join(
          "zero", "0n3", "two", ",o_O_;-()" + os.sep + os.sep + os.sep,
          "three.jpg" + os.sep)),
      os.path.join("zero", "0n3", "two", ",o_O_;-()", "three.jpg"))
    self.assertEqual(
      self.validator.validate(os.path.join("one", "two\x09\x7f", "three:|")),
      os.path.join("one", "two", "three"))
    self.assertEqual(
      self.validator.validate(os.path.join("one", ":two", "three")),
      os.path.join("one", "two", "three"))
    
    if os.name == "nt":
      self.assertEqual(
        self.validator.validate(os.path.join("C:" + os.sep + "two", "three")),
        os.path.join("C:" + os.sep + "two", "three"))
      self.assertEqual(
        self.validator.validate(os.path.join("C:|one" + os.sep + "two", "three")),
        os.path.join("C:", "one", "two", "three"))
      self.assertEqual(
        self.validator.validate(os.path.join("C:|" + os.sep + "two", "three")),
        os.path.join("C:", "two", "three"))
    else:
      self.assertEqual(
        self.validator.validate(os.path.join("C:" + os.sep + "two", "three")),
        os.path.join("C" + os.sep + "two", "three"))
      self.assertEqual(
        self.validator.validate(os.path.join("C:|one" + os.sep + "two", "three")),
        os.path.join("Cone", "two", "three"))
      self.assertEqual(
        self.validator.validate(os.path.join("C:|" + os.sep + "two", "three")),
        os.path.join("C", "two", "three"))
    
    self.assertEqual(
      self.validator.validate(os.path.join(" one", "two", "three ")),
      os.path.join("one", "two", "three"))
    self.assertEqual(
      self.validator.validate(os.path.join("one", "two ", "three")),
      os.path.join("one", "two", "three"))
    self.assertEqual(
      self.validator.validate(os.path.join("one", "two", "three.")),
      os.path.join("one", "two", "three"))
    self.assertEqual(
      self.validator.validate(os.path.join("one.", "two.", "three")),
      os.path.join("one", "two", "three"))
    self.assertEqual(
      self.validator.validate(os.path.join(".one", "two", ".three")),
      os.path.join(".one", "two", ".three"))
    self.assertEqual(
      self.validator.validate(os.path.join("one", "two", "NUL")),
      os.path.join("one", "two", "NUL (1)"))
    self.assertEqual(
      self.validator.validate(os.path.join("one", "two", "NUL:|.txt")),
      os.path.join("one", "two", "NUL (1).txt"))
    self.assertEqual(
      self.validator.validate(os.path.join("one", "NUL", "three")),
      os.path.join("one", "NUL (1)", "three"))
    self.assertEqual(
      self.validator.validate(os.path.join("one", "NUL (1)", "three")),
      os.path.join("one", "NUL (1)", "three"))
    
    self.assertEqual(self.validator.validate(""), ".")
    self.assertEqual(self.validator.validate("|"), ".")
    self.assertEqual(
      self.validator.validate(os.path.join("one", ":|", "three")),
      os.path.join("one", "three"))


class TestFileExtensionValidator(unittest.TestCase):
  
  def setUp(self):
    self.validator = pgpath.FileExtensionValidator
  
  def test_is_valid(self):
    self.assertEqual(self.validator.is_valid("jpg"), (True, []))
    self.assertTrue(self.validator.is_valid(".jpg")[0])
    self.assertTrue(self.validator.is_valid("tar.gz")[0])
    self.assertFalse(self.validator.is_valid("one/two\x09\x7f\\:|")[0])
    self.assertFalse(self.validator.is_valid("")[0])
    self.assertFalse(self.validator.is_valid(" jpg ")[0])
    self.assertFalse(self.validator.is_valid("jpg.")[0])
  
  def test_validate(self):
    self.assertEqual(self.validator.validate("jpg"), "jpg")
    self.assertEqual(self.validator.validate(".jpg"), ".jpg")
    self.assertEqual(self.validator.validate("tar.gz"), "tar.gz")
    self.assertEqual(self.validator.validate("one/two\x09\x7f\\:|"), "onetwo")
    self.assertEqual(self.validator.validate(" jpg "), " jpg")
    self.assertEqual(self.validator.validate("jpg."), "jpg")
    
    self.assertEqual(self.validator.validate(""), "")
