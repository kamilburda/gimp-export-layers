# -*- coding: utf-8 -*-
#
# Copyright (C) 2014-2019 khalim19
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

import os
import unittest

import parameterized

from .. import pgpath


class TestUniquifyString(unittest.TestCase):
  
  @parameterized.parameterized.expand([
    ("one_identical_string", "one", ["one", "two", "three"], "one (1)"),
    
    ("identical_string_and_existing_string_with_uniquifier",
     "one", ["one", "one (1)", "three"], "one (2)"),
    
    ("multiple_identical_strings", "one", ["one", "one", "three"], "one (1)"),
    
    ("existing_string_with_uniquifier",
     "one (1)", ["one (1)", "two", "three"], "one (1) (1)"),
    
    ("multiple_existing_strings_with_uniquifier",
     "one (1)", ["one (1)", "one (2)", "three"], "one (1) (1)"),
  ])
  def test_uniquify_string(
        self, test_case_name_suffix, str_, existing_strings, expected_str):
    self.assertEqual(pgpath.uniquify_string(str_, existing_strings), expected_str)
  
  @parameterized.parameterized.expand([
    ("one_identical_string",
     "one.png", ["one.png", "two", "three"], "one (1).png"),
    
    ("identical_string_and_existing_string_with_uniquifier",
     "one.png", ["one.png", "one (1).png", "three"], "one (2).png"),
    
    ("existing_string_with_uniquifier",
     "one (1).png", ["one (1).png", "two", "three"], "one (1) (1).png"),
  ])
  def test_uniquify_string_with_custom_uniquifier_position(
        self, test_case_name_suffix, str_, existing_strings, expected_str):
    self.assertEqual(
      pgpath.uniquify_string(str_, existing_strings, len(str_) - len(".png")),
      expected_str)


def _get_field_value(arg1=1, arg2=2):
  return "{}{}".format(arg1, arg2)


def _get_field_value_with_required_args(arg1, arg2, arg3):
  return "{}{}{}".format(arg1, arg2, arg3)


def _get_field_value_with_varargs(arg1, *args):
  return "{}_{}".format(arg1, "-".join(args))


def _get_field_value_with_kwargs(arg1=1, arg2=2, **kwargs):
  return "{}_{}".format(arg1, "-".join(kwargs.values()))


def _get_field_value_raising_exception(arg1=1, arg2=2):
  raise ValueError("invalid argument values")


def _generate_number():
  i = 1
  while True:
    yield i
    i += 1


def _generate_string_with_single_character(character="a"):
  while True:
    yield character
    character += "a"


class TestStringPatternGenerator(unittest.TestCase):
  
  @parameterized.parameterized.expand([
    ("empty_string", "", ""),
    ("nonempty_string", "image", "image"),
    ("string_containing_field_delimiters", "[image]", "[image]"),
  ])
  def test_generate_without_fields(
        self, test_case_name_suffix, pattern, expected_output):
    self.assertEqual(pgpath.StringPatternGenerator(pattern).generate(), expected_output)
  
  @parameterized.parameterized.expand([
    ("fields_without_arguments_with_constant_value",
     [("field1", lambda: "1"),
      ("field2", lambda: "2"),
      ("field3", lambda: "3")],
     "img_[field1][field2]_[field3]",
     "img_12_3"),
    
    ("field_with_explicit_arguments",
     [("field", _get_field_value)], "img_[field, 3, 4]", "img_34"),
    
    ("field_with_explicit_arguments_of_length_more_than_one",
     [("field", _get_field_value)], "img_[field, one, two]", "img_onetwo"),
    
    ("field_with_last_default_argument",
     [("field", _get_field_value)], "img_[field, 3]", "img_32"),
    
    ("field_with_default_arguments",
     [("field", _get_field_value)], "img_[field]", "img_12"),
    
    ("field_with_default_arguments_with_trailing_comma",
     [("field", _get_field_value)], "img_[field,]", "img_12"),
    
    ("field_with_default_arguments_with_trailing_comma_and_space",
     [("field", _get_field_value)], "img_[field, ]", "img_12"),
    
    ("field_with_explicit_arguments_with_trailing_comma_and_space",
     [("field", _get_field_value)], "img_[field, 3, 4, ]", "img_34"),
    
    ("field_with_last_default_argument_with_trailing_comma_and_space",
     [("field", _get_field_value)], "img_[field, 3, ]", "img_32"),
    
    ("field_with_more_args_than_func",
     [("field", _get_field_value)], "img_[field, 3, 4, 5]", "img_[field, 3, 4, 5]"),
    
    ("field_with_zero_args_for_func_with_required_args",
     [("field", _get_field_value_with_required_args)],
     "img_[field]",
     "img_[field]"),
    
    ("field_with_fewer_args_than_required",
     [("field", _get_field_value_with_required_args)],
     "img_[field, 3]",
     "img_[field, 3]"),
    
    ("field_with_one_arg_less_than_required",
     [("field", _get_field_value_with_required_args)],
     "img_[field, 3, 4]",
     "img_[field, 3, 4]"),
    
    ("field_with_no_varargs_for_func_with_varargs",
     [("field", _get_field_value_with_varargs)],
     "img_[field, 3]",
     "img_3_"),
    
    ("field_with_varargs_for_func_with_varargs",
     [("field", _get_field_value_with_varargs)],
     "img_[field, 3, 4, 5, 6]",
     "img_3_4-5-6"),
    
    ("field_args_with_explicit_delimiters",
     [("field", _get_field_value)], "img_[field, [3], [4],]", "img_34"),
    
    ("field_args_of_length_more_than_one_with_explicit_delimiters",
     [("field", _get_field_value)], "img_[field, [one], [two],]", "img_onetwo"),
    
    ("field_with_multiple_spaces_between_args",
     [("field", _get_field_value)], "img_[field,   3,  4  ]", "img_34"),
    
    ("field_args_with_explicit_delimiters_escape_spaces_and_arg_delimiters",
     [("field", _get_field_value)], "img_[field, [3, ], [4, ],]", "img_3, 4, "),
    
    ("field_args_with_escaped_delimiters_on_arg_bounds",
     [("field", _get_field_value)],
     "img_[field, [[[3, ]]], [[[4, ]]],]",
     "img_[3, ][4, ]"),
    
    ("field_args_with_escaped_delimiters_inside_args",
     [("field", _get_field_value)], "img_[field, [on[[e], [t[[w]]o],]", "img_on[et[w]o"),
    
    ("field_with_function_raising_exception_returns_pattern",
     [("field", _get_field_value_raising_exception)], "img_[field]", "img_[field]"),
    
    ("unrecognized_field_is_not_processed",
     [("unrecognized field", _get_field_value)],
     "img_[field]",
     "img_[field]"),
    
    ("field_with_delimiters_is_not_processed",
     [(r"\[field\]", _generate_number)],
     "img_[field]",
     "img_[field]"),
    
    ("escaped_delimiters",
     [("field", _get_field_value)], "img_[[field]]", "img_[field]"),
    
    ("escaped_delimiters_alongside_fields",
     [("field", _get_field_value)], "[[img [[1]]_[field]", "[img [1]_12"),
    
    ("uneven_number_of_opening_and_closing_delimiters",
     [("field", _get_field_value)], "img_[field, [1[, ]", "img_[field, [1[, ]"),
    
    ("escaped_opening_delimiter",
     [("field", _get_field_value)], "img_[[field", "img_[field"),
    
    ("unescaped_opening_delimiter",
     [("field", _get_field_value)], "img_[field", "img_[field"),
    
    ("unescaped_opening_delimiter_at_end",
     [("field", _get_field_value)], "img_[field][", "img_12["),
    
    ("escaped_closing_delimiter",
     [("field", _get_field_value)], "img_field]]", "img_field]"),
    
    ("unescaped_closing_delimiter",
     [("field", _get_field_value)], "img_field]", "img_field]"),
    
    ("escaped_opening_delimiter_and_unescaped_closing_delimiter",
     [("field", _get_field_value)], "img_[[field]", "img_[field]"),
    
    ("unescaped_opening_delimiter_and_escaped_closing_delimiter",
     [("field", _get_field_value)], "img_[field]]", "img_12]"),
    
    ("escaped_delimiters_at_ends_fields_fields_inside",
     [("field", _get_field_value)], "img_[[field] [field]]", "img_[field] 12]"),
    
    ("unescaped_opening_and_closing_delimiters_at_end",
     [("field", _get_field_value)], "img_[field[]", "img_[field[]"),
  ])
  def test_generate_with_fields(
        self, test_case_name_suffix, fields, pattern, expected_output):
    self.assertEqual(
      pgpath.StringPatternGenerator(pattern, fields).generate(),
      expected_output)
  
  @parameterized.parameterized.expand([
    ("field_with_explicit_arguments",
     [("field", _get_field_value)], "img_[field, 3, 4]", "img_34"),
    
    ("field_with_explicit_arguments_of_length_more_than_one",
     [("field", _get_field_value)], "img_[field, one, two]", "img_onetwo"),
    
    ("field_with_last_default_argument",
     [("field", _get_field_value)], "img_[field, 3]", "img_32"),
    
    ("field_with_default_arguments",
     [("field", _get_field_value)], "img_[field]", "img_12"),
  ])
  def test_generate_multiple_times_yields_same_field(
        self, test_case_name_suffix, fields, pattern, expected_output):
    generator = pgpath.StringPatternGenerator(pattern, fields)
    num_repeats = 3
    
    outputs = [generator.generate() for unused_ in range(num_repeats)]
    
    self.assertListEqual(outputs, [expected_output] * num_repeats)
  
  @parameterized.parameterized.expand([
    ("regex_single_matching_character",
     [(r"^[0-9]+$", _generate_number)], "img_[0]", ["img_1", "img_2", "img_3"]),
    
    ("regex_multiple_matching_characters",
     [(r"^[0-9]+$", _generate_number)], "img_[42]", ["img_1", "img_2", "img_3"]),
    
    ("multple_fields_matching_regex",
     [(r"^[0-9]+$", _generate_number)],
     "img_[42]_[0]",
     ["img_1_2", "img_3_4", "img_5_6"]),
    
    ("non_matching_regex",
     [(r"^[0-9]+$", _generate_number)],
     "img_[abc]",
     ["img_[abc]"]),
    
    ("multiple_fields_one_matching_regex",
     [(r"^[0-9]+$", _generate_number),
      (r"^[a-z]+$", _generate_string_with_single_character)],
     "img_[42]_[##]",
     ["img_1_[##]", "img_2_[##]", "img_3_[##]"]),
    
    ("multiple_matching_regexes_takes_first_matching_regex",
     [(r"^[0-9]+$", _generate_number),
      (r"^[0-9a-z]+$", _generate_string_with_single_character)],
     "img_[42]",
     ["img_1", "img_2", "img_3"]),
  ])
  def test_generate_with_field_as_regex(
        self, test_case_name_suffix, fields, pattern, expected_outputs):
    generators = []
    
    processed_fields = []
    
    for field_regex, generator_func in fields:
      gen = generator_func()
      generators.append(gen)
      processed_fields.append((field_regex, lambda gen=gen: next(gen)))
    
    generator = pgpath.StringPatternGenerator(pattern, processed_fields)
    outputs = [generator.generate() for unused_ in range(len(expected_outputs))]
    
    self.assertEqual(outputs, expected_outputs)
  
  @parameterized.parameterized.expand([
    ("one_field", "img_[field]", ["img_1", "img_2", "img_3"]),
    ("multiple_fields", "img_[field]_[field]", ["img_1_2", "img_3_4", "img_5_6"]),
  ])
  def test_generate_with_field_generator(
        self, test_case_name_suffix, pattern, expected_outputs):
    field_value_generator = _generate_number()
    fields = [("field", lambda: next(field_value_generator))]
    
    generator = pgpath.StringPatternGenerator(pattern, fields)
    outputs = [generator.generate() for unused_ in range(len(expected_outputs))]
    
    self.assertListEqual(outputs, expected_outputs)
  
  @parameterized.parameterized.expand([
    ("with_all_args", "img_[field, 3, 4]", "img_34"),
    ("with_no_args", "img_[field]", "img_12"),
  ])
  def test_generate_with_fields_with_bound_method(
        self, test_case_name_suffix, pattern, expected_output):
    class _Field(object):
      
      def get_field_value(self, arg1=1, arg2=2):
        return "{}{}".format(arg1, arg2)
    
    generator = pgpath.StringPatternGenerator(
      pattern, [("field", _Field().get_field_value)])
    self.assertEqual(generator.generate(), expected_output)
  
  def test_generate_field_function_with_kwargs_raises_error(self):
    with self.assertRaises(ValueError):
      pgpath.StringPatternGenerator(
        "[field, -]", [("field", _get_field_value_with_kwargs)])
  
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
    self.assertEqual(get_field_at_position("[[[layer name]", 3), "layer name")
    
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
          "zero",
          "0n3",
          "two",
          ",o_O_;-()" + os.sep + os.sep + os.sep,
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
