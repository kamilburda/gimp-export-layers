#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division, print_function, unicode_literals
from future.builtins import *

import unittest

import parameterized

from .. import version as pgversion


class TestVersion(unittest.TestCase):
  
  @parameterized.parameterized.expand([
    ['major_minor', '3.3', (3, 3, None, None, None)],
    ['major_minor_patch', '3.3.1', (3, 3, 1, None, None)],
    ['major_minor_patch_with_more_digits', '3.3.10', (3, 3, 10, None, None)],
    ['major_minor_prerelease', '3.3-alpha', (3, 3, None, 'alpha', None)],
    ['major_minor_prerelease_patch', '3.3-alpha.2', (3, 3, None, 'alpha', 2)],
    ['major_minor_prerelease_patch_with_more_digits',
     '3.3-alpha.10', (3, 3, None, 'alpha', 10)],
    ['major_minor_patch_prerelease_patch', '3.3.1-alpha.2', (3, 3, 1, 'alpha', 2)],
  ])
  def test_parse_version_string(
        self, test_case_name_suffix, version_str, expected_values):
    ver = pgversion.Version.parse(version_str)
    self.assertTupleEqual(
      (ver.major, ver.minor, ver.patch, ver.prerelease, ver.prerelease_patch),
      expected_values)
  
  @parameterized.parameterized.expand([
    ['redundant_hyphens', '3.3-alpha-beta'],
    ['invalid_main_components', '3#3'],
    ['invalid_main_components_patch', '3.3#1'],
    ['negative_major', '-3.3'],
    ['negative_minor', '3.-3'],
    ['negative_patch', '3.3.-1'],
    ['zero_patch', '3.3.0'],
    ['invalid_prerelease', '3.3-al#pha'],
    ['invalid_prerelease_patch', '3.3-alpha.#'],
    ['negative_prerelease_patch', '3.3-alpha.-2'],
    ['zero_prerelease_patch', '3.3-alpha.0'],
    ['one_prerelease_patch', '3.3-alpha.1'],
  ])
  def test_parse_version_string_invalid_format_raises_error(
        self, test_case_name_suffix, version_str):
    with self.assertRaises(pgversion.InvalidVersionFormatError):
      pgversion.Version.parse(version_str)
  
  @parameterized.parameterized.expand([
    ['major_minor', (3, 3, None, None, None), '3.3'],
    ['major_minor_patch', (3, 3, 1, None, None), '3.3.1'],
    ['major_minor_prerelease', (3, 3, None, 'alpha', None), '3.3-alpha'],
    ['major_minor_prerelease_patch', (3, 3, None, 'alpha', 2), '3.3-alpha.2'],
    ['major_minor_patch_prerelease_patch', (3, 3, 1, 'alpha', 2), '3.3.1-alpha.2'],
  ])
  def test_str(self, test_case_name_suffix, version_values, expected_str):
    self.assertEqual(str(pgversion.Version(*version_values)), expected_str)
  
  @parameterized.parameterized.expand([
    ['major_minor', (3, 3, None, None, None), 'Version(3, 3, None, None, None)'],
    ['major_minor_patch_prerelease_patch', (3, 3, 1, 'alpha', 2), 'Version(3, 3, 1, "alpha", 2)'],
  ])
  def test_repr(self, test_case_name_suffix, version_values, expected_str):
    self.assertEqual(repr(pgversion.Version(*version_values)), expected_str)
  
  @parameterized.parameterized.expand([
    ['major', (3, 3, None, None, None), 'major', '4.0'],
    ['major_with_patch', (3, 3, 1, None, None), 'major', '4.0'],
    ['minor', (3, 3, None, None, None), 'minor', '3.4'],
    ['minor_with_patch', (3, 3, 1, None, None), 'minor', '3.4'],
    ['patch', (3, 3, None, None, None), 'patch', '3.3.1'],
    ['patch_with_patch', (3, 3, 1, None, None), 'patch', '3.3.2'],
    ['major_with_prerelease', (3, 3, None, 'alpha', None), 'major', '4.0'],
    ['major_with_prerelease_patch', (3, 3, None, 'alpha', 2), 'major', '4.0'],
    ['major_with_patch_prerelease_patch', (3, 3, 1, 'alpha', 2), 'major', '4.0'],
    ['minor_with_prerelease', (3, 3, None, 'alpha', None), 'minor', '3.4'],
    ['minor_with_prerelease_patch', (3, 3, None, 'alpha', 2), 'minor', '3.4'],
    ['minor_with_patch_prerelease_patch', (3, 3, 1, 'alpha', 2), 'minor', '3.4'],
    ['patch_with_prerelease', (3, 3, None, 'alpha', None), 'patch', '3.3.1'],
    ['patch_with_prerelease_patch', (3, 3, None, 'alpha', 2), 'patch', '3.3.1'],
    ['patch_with_patch_prerelease_patch', (3, 3, 1, 'alpha', 2), 'patch', '3.3.2'],
  ])
  def test_increment(
        self,
        test_case_name_suffix,
        version_values,
        component_to_increment,
        expected_str):
    ver = pgversion.Version(*version_values)
    ver.increment(component_to_increment)
    self.assertEqual(str(ver), expected_str)
  
  @parameterized.parameterized.expand([
    ['new_major', (3, 3, 1, None, None), 'major', 'alpha', '4.0-alpha'],
    ['new_minor', (3, 3, 1, None, None), 'minor', 'alpha', '3.4-alpha'],
    ['new_patch', (3, 3, 1, None, None), 'patch', 'alpha', '3.3.2-alpha'],
    ['same_major', (4, 0, None, 'alpha', None), 'major', 'alpha', '4.0-alpha.2'],
    ['same_minor', (3, 3, None, 'alpha', None), 'minor', 'alpha', '3.3-alpha.2'],
    ['same_patch', (3, 3, 1, 'alpha', None), 'patch', 'alpha', '3.3.1-alpha.2'],
    ['same_nonfirst_major', (4, 0, None, 'alpha', 2), 'major', 'alpha', '4.0-alpha.3'],
    ['same_nonfirst_minor', (3, 3, None, 'alpha', 2), 'minor', 'alpha', '3.3-alpha.3'],
    ['same_nonfirst_patch', (3, 3, 1, 'alpha', 2), 'patch', 'alpha', '3.3.1-alpha.3'],
    ['new_prerelease_same_major',
     (4, 0, None, 'alpha', None), 'major', 'beta', '4.0-beta'],
    ['new_prerelease_same_minor',
     (3, 3, None, 'alpha', None), 'major', 'beta', '3.3-beta'],
    ['new_prerelease_same_patch',
     (3, 3, 1, 'alpha', None), 'major', 'beta', '3.3.1-beta'],
    ['new_prerelease_same_nonfirst_major',
     (4, 0, None, 'alpha', 2), 'major', 'beta', '4.0-beta'],
    ['new_prerelease_same_nonfirst_minor',
     (3, 3, None, 'alpha', 2), 'major', 'beta', '3.3-beta'],
    ['new_prerelease_same_nonfirst_patch',
     (3, 3, 1, 'alpha', 2), 'major', 'beta', '3.3.1-beta'],
    ['empty_prerelease_assumes_no_prerelease',
     (3, 3, 1, None, None), 'major', '', '4.0'],
  ])
  def test_increment_with_prerelease(
        self,
        test_case_name_suffix,
        version_values,
        component_to_increment,
        prerelease,
        expected_str):
    ver = pgversion.Version(*version_values)
    ver.increment(component_to_increment, prerelease)
    self.assertEqual(str(ver), expected_str)
  
  @parameterized.parameterized.expand([
    ['invalid_main_component', (3, 3, 1, None, None), 'invalid', None],
    ['invalid_prerelease_format', (3, 3, 1, None, None), 'patch', 'al#pha'],
    ['new_prerelease_same_major_lexically_earlier',
     (4, 0, None, 'beta', None), 'major', 'alpha'],
    ['new_prerelease_same_minor_lexically_earlier',
     (3, 3, None, 'beta', None), 'minor', 'alpha'],
    ['new_prerelease_same_patch_lexically_earlier',
     (3, 3, 1, 'beta', None), 'patch', 'alpha'],
  ])
  def test_increment_invalid_parameters_raise_error(
        self,
        test_case_name_suffix,
        version_values,
        component_to_increment,
        prerelease):
    ver = pgversion.Version(*version_values)
    with self.assertRaises(ValueError):
      ver.increment(component_to_increment, prerelease)
  
  @parameterized.parameterized.expand([
    ['first_is_less', '3.3', '3.4', True],
    ['first_is_greater', '3.3', '3.2', False],
    ['equal', '3.3', '3.3', False],
    ['digits_compared_as_numbers', '3.3', '3.10', True],
    ['prerelease_and_no_prerelease', '3.3-alpha', '3.3', True],
    ['no_prerelease_and_prerelease', '3.3', '3.3-alpha', False],
    ['different_prereleases_first_is_less', '3.3-alpha', '3.3-beta', True],
    ['different_prereleases_first_is_greater', '3.3-alpha', '3.3-beta', True],
    ['same_prereleases', '3.3-alpha', '3.3-alpha', False],
    ['prerelease_and_prerelease_with_patch', '3.3-alpha', '3.3-alpha.2', True],
    ['same_prereleases_with_same_patches', '3.3-alpha.2', '3.3-alpha.2', False],
    ['same_prereleases_first_patch_less', '3.3-alpha.2', '3.3-alpha.3', True],
    ['same_prereleases_first_patch_greater', '3.3-alpha.3', '3.3-alpha.2', False],
    ['prerelease_patch_digits_compared_as_number', '3.3-alpha.2', '3.3-alpha.10', True],
  ])
  def test_less_than(self, test_case_name_suffix, ver1_str, ver2_str, result):
    ver1 = pgversion.Version.parse(ver1_str)
    ver2 = pgversion.Version.parse(ver2_str)
    
    if result:
      self.assertTrue(ver1 < ver2)
    else:
      self.assertFalse(ver1 < ver2)
  
  @parameterized.parameterized.expand([
    ['equal', '3.3', '3.3', True],
    ['not_equal', '3.3', '3.4', False],
    ['equal_with_patch', '3.3.1', '3.3.1', True],
    ['not_equal_with_patch', '3.3.1', '3.3.2', False],
    ['equal_prerelease', '3.3-alpha', '3.3-alpha', True],
    ['not_equal_prerelease', '3.3-alpha', '3.3-beta', False],
    ['equal_prerelease_patch', '3.3-alpha.2', '3.3-alpha.2', True],
    ['not_equal_prerelease_patch', '3.3-alpha.2', '3.3-alpha.3', False],
  ])
  def test_equal(self, test_case_name_suffix, ver1_str, ver2_str, result):
    ver1 = pgversion.Version.parse(ver1_str)
    ver2 = pgversion.Version.parse(ver2_str)
    
    if result:
      self.assertEqual(ver1, ver2)
    else:
      self.assertNotEqual(ver1, ver2)
