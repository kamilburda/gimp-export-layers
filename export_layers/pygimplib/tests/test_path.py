# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import os
import unittest

import parameterized

from .. import path as pgpath


class TestUniquifyString(unittest.TestCase):
  
  @parameterized.parameterized.expand([
    ('one_identical_string', 'one', ['one', 'two', 'three'], 'one (1)'),
    
    ('identical_string_and_existing_string_with_unique_substring',
     'one', ['one', 'one (1)', 'three'], 'one (2)'),
    
    ('multiple_identical_strings', 'one', ['one', 'one', 'three'], 'one (1)'),
    
    ('existing_string_with_unique_substring',
     'one (1)', ['one (1)', 'two', 'three'], 'one (1) (1)'),
    
    ('multiple_existing_strings_with_unique_substring',
     'one (1)', ['one (1)', 'one (2)', 'three'], 'one (1) (1)'),
  ])
  def test_uniquify_string(
        self, test_case_name_suffix, str_, existing_strings, expected_str):
    self.assertEqual(pgpath.uniquify_string(str_, existing_strings), expected_str)
  
  @parameterized.parameterized.expand([
    ('one_identical_string',
     'one.png', ['one.png', 'two', 'three'], 'one (1).png'),
    
    ('identical_string_and_existing_string_with_unique_substring',
     'one.png', ['one.png', 'one (1).png', 'three'], 'one (2).png'),
    
    ('existing_string_with_unique_substring',
     'one (1).png', ['one (1).png', 'two', 'three'], 'one (1) (1).png'),
  ])
  def test_uniquify_string_with_custom_position(
        self, test_case_name_suffix, str_, existing_strings, expected_str):
    self.assertEqual(
      pgpath.uniquify_string(str_, existing_strings, len(str_) - len('.png')),
      expected_str)


def _get_field_value(field, arg1=1, arg2=2):
  return '{}{}'.format(arg1, arg2)


def _get_field_value_with_required_args(field, arg1, arg2, arg3):
  return '{}{}{}'.format(arg1, arg2, arg3)


def _get_field_value_with_varargs(field, arg1, *args):
  return '{}_{}'.format(arg1, '-'.join(args))


def _get_field_value_with_kwargs(field, arg1=1, arg2=2, **kwargs):
  return '{}_{}'.format(arg1, '-'.join(kwargs.values()))


def _get_field_value_raising_exception(field, arg1=1, arg2=2):
  raise ValueError('invalid argument values')


def _generate_number():
  i = 1
  while True:
    yield i
    i += 1


def _generate_string_with_single_character(character='a'):
  while True:
    yield character
    character += 'a'


class TestStringPattern(unittest.TestCase):
  
  @parameterized.parameterized.expand([
    ('empty_string', '', ''),
    ('nonempty_string', 'image', 'image'),
    ('string_containing_field_delimiters', '[image]', '[image]'),
  ])
  def test_generate_without_fields(
        self, test_case_name_suffix, pattern, expected_output):
    self.assertEqual(pgpath.StringPattern(pattern).substitute(), expected_output)
  
  @parameterized.parameterized.expand([
    ('fields_without_arguments_with_constant_value',
     [('field1', lambda field: '1'),
      ('field2', lambda field: '2'),
      ('field3', lambda field: '3')],
     'img_[field1][field2]_[field3]',
     'img_12_3'),
    
    ('field_with_explicit_arguments',
     [('field', _get_field_value)], 'img_[field, 3, 4]', 'img_34'),
    
    ('field_with_explicit_arguments_of_length_more_than_one',
     [('field', _get_field_value)], 'img_[field, one, two]', 'img_onetwo'),
    
    ('field_with_last_default_argument',
     [('field', _get_field_value)], 'img_[field, 3]', 'img_32'),
    
    ('field_with_default_arguments',
     [('field', _get_field_value)], 'img_[field]', 'img_12'),
    
    ('field_with_default_arguments_with_trailing_comma',
     [('field', _get_field_value)], 'img_[field,]', 'img_12'),
    
    ('field_with_default_arguments_with_trailing_comma_and_space',
     [('field', _get_field_value)], 'img_[field, ]', 'img_12'),
    
    ('field_with_explicit_arguments_with_trailing_comma_and_space',
     [('field', _get_field_value)], 'img_[field, 3, 4, ]', 'img_34'),
    
    ('field_with_last_default_argument_with_trailing_comma_and_space',
     [('field', _get_field_value)], 'img_[field, 3, ]', 'img_32'),
    
    ('field_with_more_args_than_func',
     [('field', _get_field_value)], 'img_[field, 3, 4, 5]', 'img_[field, 3, 4, 5]'),
    
    ('field_with_zero_args_for_func_with_required_args',
     [('field', _get_field_value_with_required_args)],
     'img_[field]',
     'img_[field]'),
    
    ('field_with_fewer_args_than_required',
     [('field', _get_field_value_with_required_args)],
     'img_[field, 3]',
     'img_[field, 3]'),
    
    ('field_with_one_arg_less_than_required',
     [('field', _get_field_value_with_required_args)],
     'img_[field, 3, 4]',
     'img_[field, 3, 4]'),
    
    ('field_with_no_varargs_for_func_with_varargs',
     [('field', _get_field_value_with_varargs)],
     'img_[field, 3]',
     'img_3_'),
    
    ('field_with_varargs_for_func_with_varargs',
     [('field', _get_field_value_with_varargs)],
     'img_[field, 3, 4, 5, 6]',
     'img_3_4-5-6'),
    
    ('field_args_with_explicit_delimiters',
     [('field', _get_field_value)], 'img_[field, [3], [4],]', 'img_34'),
    
    ('field_args_of_length_more_than_one_with_explicit_delimiters',
     [('field', _get_field_value)], 'img_[field, [one], [two],]', 'img_onetwo'),
    
    ('field_with_multiple_spaces_between_args',
     [('field', _get_field_value)], 'img_[field,   3,  4  ]', 'img_34'),
    
    ('field_args_with_explicit_delimiters_escape_spaces_and_arg_delimiters',
     [('field', _get_field_value)], 'img_[field, [3, ], [4, ],]', 'img_3, 4, '),
    
    ('field_args_with_escaped_delimiters_on_arg_bounds',
     [('field', _get_field_value)],
     'img_[field, [[[3, ]]], [[[4, ]]],]',
     'img_[3, ][4, ]'),
    
    ('field_args_with_escaped_delimiters_inside_args',
     [('field', _get_field_value)], 'img_[field, [on[[e], [t[[w]]o],]', 'img_on[et[w]o'),
    
    ('field_with_function_raising_exception_returns_pattern',
     [('field', _get_field_value_raising_exception)], 'img_[field]', 'img_[field]'),
    
    ('unrecognized_field_is_not_processed',
     [('unrecognized field', _get_field_value)],
     'img_[field]',
     'img_[field]'),
    
    ('field_with_delimiters_is_not_processed',
     [(r'\[field\]', _generate_number)],
     'img_[field]',
     'img_[field]'),
    
    ('escaped_delimiters',
     [('field', _get_field_value)], 'img_[[field]]', 'img_[field]'),
    
    ('escaped_delimiters_alongside_fields',
     [('field', _get_field_value)], '[[img [[1]]_[field]', '[img [1]_12'),
    
    ('uneven_number_of_opening_and_closing_delimiters',
     [('field', _get_field_value)], 'img_[field, [1[, ]', 'img_[field, [1[, ]'),
    
    ('escaped_opening_delimiter',
     [('field', _get_field_value)], 'img_[[field', 'img_[field'),
    
    ('unescaped_opening_delimiter',
     [('field', _get_field_value)], 'img_[field', 'img_[field'),
    
    ('unescaped_opening_delimiter_at_end',
     [('field', _get_field_value)], 'img_[field][', 'img_12['),
    
    ('escaped_closing_delimiter',
     [('field', _get_field_value)], 'img_field]]', 'img_field]'),
    
    ('unescaped_closing_delimiter',
     [('field', _get_field_value)], 'img_field]', 'img_field]'),
    
    ('escaped_opening_delimiter_and_unescaped_closing_delimiter',
     [('field', _get_field_value)], 'img_[[field]', 'img_[field]'),
    
    ('unescaped_opening_delimiter_and_escaped_closing_delimiter',
     [('field', _get_field_value)], 'img_[field]]', 'img_12]'),
    
    ('escaped_delimiters_at_ends_fields_fields_inside',
     [('field', _get_field_value)], 'img_[[field] [field]]', 'img_[field] 12]'),
    
    ('unescaped_opening_and_closing_delimiters_at_end',
     [('field', _get_field_value)], 'img_[field[]', 'img_[field[]'),
  ])
  def test_generate_with_fields(
        self, test_case_name_suffix, fields, pattern, expected_output):
    self.assertEqual(pgpath.StringPattern(pattern, fields).substitute(), expected_output)
  
  @parameterized.parameterized.expand([
    ('field_with_explicit_arguments',
     [('field', _get_field_value)], 'img_[field, 3, 4]', 'img_34'),
    
    ('field_with_explicit_arguments_of_length_more_than_one',
     [('field', _get_field_value)], 'img_[field, one, two]', 'img_onetwo'),
    
    ('field_with_last_default_argument',
     [('field', _get_field_value)], 'img_[field, 3]', 'img_32'),
    
    ('field_with_default_arguments',
     [('field', _get_field_value)], 'img_[field]', 'img_12'),
  ])
  def test_generate_multiple_times_yields_same_field(
        self, test_case_name_suffix, fields, pattern, expected_output):
    string_pattern = pgpath.StringPattern(pattern, fields)
    num_repeats = 3
    
    outputs = [string_pattern.substitute() for unused_ in range(num_repeats)]
    
    self.assertListEqual(outputs, [expected_output] * num_repeats)
  
  @parameterized.parameterized.expand([
    ('regex_single_matching_character',
     [(r'^[0-9]+$', _generate_number)], 'img_[0]', ['img_1', 'img_2', 'img_3']),
    
    ('regex_multiple_matching_characters',
     [(r'^[0-9]+$', _generate_number)], 'img_[42]', ['img_1', 'img_2', 'img_3']),
    
    ('multple_fields_matching_regex',
     [(r'^[0-9]+$', _generate_number)],
     'img_[42]_[0]',
     ['img_1_2', 'img_3_4', 'img_5_6']),
    
    ('non_matching_regex',
     [(r'^[0-9]+$', _generate_number)],
     'img_[abc]',
     ['img_[abc]']),
    
    ('multiple_fields_one_matching_regex',
     [(r'^[0-9]+$', _generate_number),
      (r'^[a-z]+$', _generate_string_with_single_character)],
     'img_[42]_[##]',
     ['img_1_[##]', 'img_2_[##]', 'img_3_[##]']),
    
    ('multiple_matching_regexes_takes_first_matching_regex',
     [(r'^[0-9]+$', _generate_number),
      (r'^[0-9a-z]+$', _generate_string_with_single_character)],
     'img_[42]',
     ['img_1', 'img_2', 'img_3']),
  ])
  def test_generate_with_field_as_regex(
        self, test_case_name_suffix, fields, pattern, expected_outputs):
    generators = []
    processed_fields = []
    
    for field_regex, generator_func in fields:
      generator = generator_func()
      generators.append(generator)
      processed_fields.append(
        (field_regex, lambda field, generator=generator: next(generator)))
    
    string_pattern = pgpath.StringPattern(pattern, processed_fields)
    outputs = [string_pattern.substitute() for unused_ in range(len(expected_outputs))]
    
    self.assertEqual(outputs, expected_outputs)
  
  @parameterized.parameterized.expand([
    ('one_field', 'img_[field]', ['img_1', 'img_2', 'img_3']),
    ('multiple_fields', 'img_[field]_[field]', ['img_1_2', 'img_3_4', 'img_5_6']),
  ])
  def test_generate_with_field_generator(
        self, test_case_name_suffix, pattern, expected_outputs):
    field_value_generator = _generate_number()
    fields = [('field', lambda field: next(field_value_generator))]
    
    string_pattern = pgpath.StringPattern(pattern, fields)
    outputs = [string_pattern.substitute() for unused_ in range(len(expected_outputs))]
    
    self.assertListEqual(outputs, expected_outputs)
  
  @parameterized.parameterized.expand([
    ('with_all_args', 'img_[field, 3, 4]', 'img_34'),
    ('with_no_args', 'img_[field]', 'img_12'),
  ])
  def test_generate_with_fields_with_bound_method(
        self, test_case_name_suffix, pattern, expected_output):
    class _Field(object):
      
      def get_field_value(self, field, arg1=1, arg2=2):
        return '{}{}'.format(arg1, arg2)
    
    string_pattern = pgpath.StringPattern(pattern, [('field', _Field().get_field_value)])
    self.assertEqual(string_pattern.substitute(), expected_output)
  
  def test_generate_field_function_with_kwargs_raises_error(self):
    with self.assertRaises(ValueError):
      pgpath.StringPattern('[field, 3, 4]', [('field', _get_field_value_with_kwargs)])
  
  @parameterized.parameterized.expand([
    ('', '', 0, None),
    ('', 'img_12', 0, None),
    ('', 'img_12', 3, None),
    ('', '[layer name]', 0, None),
    ('', '[layer name]', 1, 'layer name'),
    ('', '[layer name]', 5, 'layer name'),
    ('', '[layer name]', 11, 'layer name'),
    ('', '[layer name]', 12, None),
    ('', '[[layer name]', 1, None),
    ('', '[[layer name]', 2, None),
    ('', '[[layer name]', 3, None),
    ('', '[[[layer name]', 1, None),
    ('', '[[[layer name]', 2, None),
    ('', '[[[layer name]', 3, 'layer name'),
    
    ('', 'layer [name]', 2, None),
    ('', 'layer [name]', 6, None),
    ('', 'layer [name]', 7, 'name'),
    ('', 'layer [name] name', 7, 'name'),
    ('', 'layer [name][layer] name', 7, 'name'),
    ('', 'layer [name][layer] name', 13, 'layer'),
    ('', 'layer [name] [layer] name', 7, 'name'),
    ('', 'layer [name] [layer] name', 14, 'layer'),
    ('', 'layer [name] [layer] name', 13, None),
    
    ('', 'layer [[layer [[ name]', 2, None),
    ('', 'layer [[layer [[ name]', 6, None),
    ('', 'layer [[layer [[ name]', 7, None),
    ('', 'layer [[layer [[ name]', 8, None),
    ('', 'layer [[layer [[ name]', 14, None),
    ('', 'layer [[layer [[ name]', 15, None),
    ('', 'layer [[layer [[ name]', 16, None),
    ('', 'layer [[layer [[[name]', 16, None),
    ('', 'layer [[layer [[[name]', 17, 'name'),
    
    ('', '[layer name', 0, None),
    ('', '[layer name', 1, None),
    ('', '[layer [name', 7, None),
    ('', '[layer [name', 8, None),
    
    ('position_greater_than_pattern_length_returns_none', '[layer name]', 100, None),
    ('negative_position_returns_none', '[layer name]', -1, None),
  ])
  def test_get_field_at_position(
        self, test_case_name_suffix, pattern, position, expected_output):
    self.assertEqual(
      pgpath.StringPattern.get_field_at_position(pattern, position), expected_output)
  
  @parameterized.parameterized.expand([
    ('no_fields', ['img_12', '_345'], 'img_12_345'),
    ('single_field_without_arguments', ['img_', ['field']], 'img_[field]'),
    ('single_field_with_one_argument', ['img_', ['field', [3]]], 'img_[field, 3]'),
    ('single_field_with_multiple_arguments',
     ['img_', ['field', [3, 4]]], 'img_[field, 3, 4]'),
    ('multiple_fields',
     ['img_', ['field', [3, 4]], '_layer_', ['field2'], '.png'],
     'img_[field, 3, 4]_layer_[field2].png'),
  ])
  def test_reconstruct_pattern(
        self, test_case_name_suffix, pattern_parts, expected_str):
    self.assertEqual(
      pgpath.StringPattern.reconstruct_pattern(pattern_parts), expected_str)
  
  def test_reconstruct_pattern_empty_list_for_field_raises_error(self):
    with self.assertRaises(ValueError):
      pgpath.StringPattern.reconstruct_pattern(['img_', []])


class TestGetFileExtension(unittest.TestCase):
  
  @parameterized.parameterized.expand([
    ('', 'background.jpg', 'jpg'),
    ('empty_string', '', ''),
    ('case_sensitive', 'background.JPG', 'JPG'),
    ('string_beginning_with_period', '.jpg', 'jpg'),
    ('no_extension', 'main-background', ''),
    ('no_extension_with_trailing_period', 'main-background.', ''),
    ('single_period_as_string', '.', ''),
    ('unrecognized_extension', 'main-background.aaa', 'aaa'),
    ('string_beginning_with_period_with_unrecognized_extension', '.aaa', 'aaa'),
    ('multiple_periods_with_recognized_extension', 'main-background.xcf.bz2', 'xcf.bz2'),
    ('multiple_periods_with_unrecognized_extension', 'main-background.aaa.bbb', 'bbb'),
  ])
  def test_get_file_extension(self, test_case_name_suffix, str_, expected_output):
    self.assertEqual(pgpath.get_file_extension(str_), expected_output)


class TestGetFilenameWithNewFileExtension(unittest.TestCase):
  
  @parameterized.parameterized.expand([
    ('', 'background.jpg', 'png', 'background.png'),
    ('empty_string', '', 'png', '.png'),
    ('string_without_extension', 'background', 'png', 'background.png'),
    ('new_extension_with_leading_period', 'background.jpg', '.png', 'background.png'),
    ('string_with_trailing_period', 'background.', 'png', 'background.png'),
    ('new_extension_is_set_lowercase', 'background.jpg', 'PNG', 'background.PNG'),
    ('empty_new_extension_removes_extension', 'background.jpg', '', 'background'),
    ('new_extension_as_none_removes_extension', 'background.jpg', None, 'background'),
    ('new_extension_as_single_period_removes_extension',
     'background.jpg', '.', 'background'),
    ('extension_with_multiple_periods_in_string',
     'background.xcf.bz2', 'png', 'background.png'),
    ('multiple_periods_in_string_single_period_for_extension',
     'background.aaa.jpg', 'png', 'background.aaa.png'),
    ('multiple_consecutive_periods',
     'background..jpg', 'png', 'background..png'),
    ('keep_extra_single_trailing_period',
     'background.', 'png', 'background..png', True),
    ('keep_extra_multiple_trailing_periods',
     'background..', 'png', 'background...png', True),
  ])
  def test_get_filename_with_new_file_extension(
        self,
        test_case_name_suffix,
        str_,
        new_file_extension,
        expected_output,
        keep_extra_trailing_periods=False):
    self.assertEqual(
      pgpath.get_filename_with_new_file_extension(
        str_, new_file_extension, keep_extra_trailing_periods),
      expected_output)


class TestGetBaseName(unittest.TestCase):
  
  @parameterized.parameterized.expand([
    ('main-background', 'main-background'),
    ('main-background.', 'main-background.'),
    ('main-background.jpg', 'main-background'),
    ('main-background..jpg', 'main-background.'),
    ('..jpg', '.'),
    ('.jpg', ''),
    ('.', '.'),
    ('', ''),
  ])
  def test_get_filename_root(self, filename, expected_output):
    self.assertEqual(pgpath.get_filename_root(filename), expected_output)


class TestFilenameValidator(unittest.TestCase):
  
  def test_is_valid_returns_no_status_messages(self):
    self.assertEqual(pgpath.FilenameValidator.is_valid('one'), (True, []))
  
  @parameterized.parameterized.expand([
    ('', '0n3_two_,o_O_;-()three.jpg', True),
    ('', 'one/two\x09\x7f\\:|', False),
    ('', '', False),
    ('', ' one ', False),
    ('', 'one.', False),
    ('', '.one', True),
    ('', 'NUL', False),
    ('', 'NUL.txt', False),
    ('', 'NUL (1)', True),
  ])
  def test_is_valid(self, test_case_name_suffix, str_, expected_is_valid):
    if expected_is_valid:
      self.assertTrue(pgpath.FilenameValidator.is_valid(str_)[0])
    else:
      self.assertFalse(pgpath.FilenameValidator.is_valid(str_)[0])
  
  @parameterized.parameterized.expand([
    ('', 'one', 'one'),
    ('', '0n3_two_,o_O_;-()three.jpg', '0n3_two_,o_O_;-()three.jpg'),
    ('', 'one/two\x09\x7f\\:|', 'onetwo'),
    ('', '', 'Untitled'),
    ('', ' one ', 'one'),
    ('', 'one.', 'one'),
    ('', '.one', '.one'),
    ('', 'NUL', 'NUL (1)'),
    ('', 'NUL.txt', 'NUL (1).txt'),
  ])
  def test_validate(self, test_case_name_suffix, str_, expected_output):
    self.assertEqual(pgpath.FilenameValidator.validate(str_), expected_output)
  

class TestFilepathValidator(unittest.TestCase):
  
  def test_is_valid_returns_no_status_messages(self):
    self.assertEqual(
      pgpath.FilepathValidator.is_valid(os.path.join('one', 'two', 'three')),
      (True, []))
  
  @parameterized.parameterized.expand([
    ('', [
      'zero', '0n3', 'two', ',o_O_;-()' + os.sep + os.sep + os.sep, 'three.jpg' + os.sep],
     True),
    ('', ['one', 'two', '\x09\x7f', ':|'], False),
    ('', ['one', ':two', 'three'], False),
    ('', ['C:|' + os.sep + 'two', 'three'], False),
    ('', [' one', 'two', 'three '], False),
    ('', ['one', ' two', 'three'], True),
    ('', ['one', 'two ', 'three'], False),
    ('', ['one', 'two', 'three.'], False),
    ('', ['one.', 'two.', 'three'], False),
    ('', ['.one', 'two', '.three'], True),
    ('', ['one', 'two', 'NUL'], False),
    ('', ['one', 'two', 'NUL.txt'], False),
    ('', ['one', 'NUL', 'three'], False),
    ('', ['one', 'NUL (1)', 'three'], True),
    ('', [''], False),
    ('', ['C:' + os.sep + 'two', 'three'], True, 'nt'),
    ('', ['C:' + os.sep + 'two', 'three'], False, 'posix'),
  ])
  def test_is_valid(
        self, test_case_name_suffix, path_components, expected_is_valid, os_name=None):
    if os_name is not None and os.name != os_name:
      return
    
    if expected_is_valid:
      self.assertTrue(
        pgpath.FilepathValidator.is_valid(os.path.join(*path_components))[0])
    else:
      self.assertFalse(
        pgpath.FilepathValidator.is_valid(os.path.join(*path_components))[0])
  
  @parameterized.parameterized.expand([
    ('',
     ['one', 'two', 'three'],
     ['one', 'two', 'three']),
    ('',
     ['zero', '0n3', 'two', ',o_O_;-()' + os.sep + os.sep + os.sep, 'three.jpg' + os.sep],
     ['zero', '0n3', 'two', ',o_O_;-()', 'three.jpg']),
    ('',
     ['one', 'two\x09\x7f', 'three:|'],
     ['one', 'two', 'three']),
    ('',
     ['one', ':two', 'three'],
     ['one', 'two', 'three']),
    ('',
     [' one', 'two', 'three '],
     ['one', 'two', 'three']),
    ('',
     ['one', 'two ', 'three'],
     ['one', 'two', 'three']),
    ('',
     ['one', 'two', 'three.'],
     ['one', 'two', 'three']),
    ('',
     ['one.', 'two.', 'three'],
     ['one', 'two', 'three']),
    ('',
     ['.one', 'two', '.three'],
     ['.one', 'two', '.three']),
    ('',
     ['one', 'two', 'NUL'],
     ['one', 'two', 'NUL (1)']),
    ('',
     ['one', 'two', 'NUL:|.txt'],
     ['one', 'two', 'NUL (1).txt']),
    ('',
     ['one', 'NUL', 'three'],
     ['one', 'NUL (1)', 'three']),
    ('',
     ['one', 'NUL (1)', 'three'],
     ['one', 'NUL (1)', 'three']),
    ('',
     ['one', ':|', 'three'],
     ['one', 'three']),
    ('',
     [''],
     ['.']),
    ('',
     ['|'],
     ['.']),
    ('',
     ['C:' + os.sep + 'two', 'three'],
     ['C:' + os.sep + 'two', 'three'],
     'nt'),
    ('',
     ['C:|one' + os.sep + 'two', 'three'],
     ['C:', 'one', 'two', 'three'],
     'nt'),
    ('',
     ['C:|' + os.sep + 'two', 'three'],
     ['C:', 'two', 'three'],
     'nt'),
    ('',
     ['C:' + os.sep + 'two', 'three'],
     ['C' + os.sep + 'two', 'three'],
     'posix'),
    ('',
     ['C:|one' + os.sep + 'two', 'three'],
     ['Cone', 'two', 'three'],
     'posix'),
    ('',
     ['C:|' + os.sep + 'two', 'three'],
     ['C', 'two', 'three'],
     'posix'),
  ])
  def test_validate(
        self,
        test_case_name_suffix,
        path_components,
        expected_path_components,
        os_name=None):
    if os_name is not None and os.name != os_name:
      return
    
    self.assertEqual(
      pgpath.FilepathValidator.validate(os.path.join(*path_components)),
      os.path.join(*expected_path_components))


class TestFileExtensionValidator(unittest.TestCase):
  
  def test_is_valid_returns_no_status_messages(self):
    self.assertEqual(pgpath.FileExtensionValidator.is_valid('jpg'), (True, []))
  
  @parameterized.parameterized.expand([
    ('', '.jpg', True),
    ('', 'tar.gz', True),
    ('', 'one/two\x09\x7f\\:|', False),
    ('', '', False),
    ('', ' jpg ', False),
    ('', 'jpg.', False),
  ])
  def test_is_valid(self, test_case_name_suffix, str_, expected_is_valid):
    if expected_is_valid:
      self.assertTrue(pgpath.FileExtensionValidator.is_valid(str_)[0])
    else:
      self.assertFalse(pgpath.FileExtensionValidator.is_valid(str_)[0])
  
  @parameterized.parameterized.expand([
    ('', 'jpg', 'jpg'),
    ('', '.jpg', '.jpg'),
    ('', 'tar.gz', 'tar.gz'),
    ('', ' jpg ', ' jpg'),
    ('', 'jpg.', 'jpg'),
    ('', '', ''),
    ('', 'one/two\x09\x7f\\:|', 'onetwo'),
  ])
  def test_validate(self, test_case_name_suffix, str_, expected_output):
    self.assertEqual(pgpath.FileExtensionValidator.validate(str_), expected_output)
