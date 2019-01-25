#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of Export Layers.
#
# Copyright (C) 2013-2019 khalim19 <khalim19@gmail.com>
#
# Export Layers is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Export Layers is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Export Layers.  If not, see <https://www.gnu.org/licenses/>.

"""
This module provides a class to store and increment version numbers.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from export_layers import pygimplib
from future.builtins import *

import re


class Version(object):
  
  def __init__(
        self, major=None, minor=None, patch=None, prerelease=None, prerelease_patch=None):
    self.major = major
    self.minor = minor
    self.patch = patch
    self.prerelease = prerelease
    self.prerelease_patch = prerelease_patch
  
  def __str__(self):
    version_str = "{}.{}".format(self.major, self.minor)
    
    if self.patch is not None:
      version_str += ".{}".format(self.patch)
    
    if self.prerelease is not None:
      version_str += "-{}".format(self.prerelease)
      if self.prerelease_patch is not None:
        version_str += ".{}".format(self.prerelease_patch)
    
    return version_str
  
  def increment(self, component_to_increment, prerelease=None):
    """
    Increment the version as per `component_to_increment` and `prerelease`.
    
    `component_to_increment` can be `"major"`, `"minor"` or `"patch"`. Given the
    format `X.Y.Z`, `"major"` increments `X`, `"minor"` increments `Y` and
    `"patch"` increments `Z`. If `patch` attribute is `None` and `"patch"` is
    specified, `1` will be assigned (e.g. `3.3` becomes `3.3.1`).
    
    If the `prerelease` string is not `None` and non-empty, append the
    pre-release to the version. For example, `3.3` with `"major"` compoment and
    `"alpha"` as the pre-release string becomes `4.0-alpha`.
    
    If the version already has the same pre-release, append a number to the
    pre-release (e.g. `4.0-alpha` becomes `4.0-alpha.2`).
    
    If the version already has a different pre-release (lexically earlier than
    `prerelease`), replace the existing pre-release with `prerelease` (e.g.
    `4.0-alpha` with the `"beta"` pre-release becomes `4.0-beta`).
    
    Raises:
    
    * `ValueError`:
      
      * Invalid value for `component_to_increment`.
      * The specified `prerelease` contains non-alphanumeric characters or is
        lexically earlier than the existing `prerelease` attribute.
    """
    if component_to_increment not in ["major", "minor", "patch"]:
      raise ValueError("invalid version component '{}'".format(component_to_increment))
    
    if prerelease:
      if not re.search(r"^[a-zA-Z0-9]+$", prerelease):
        raise ValueError("invalid pre-release format '{}'".format(prerelease))
      
      if prerelease < self.prerelease:
        raise ValueError(
          "the specified pre-release '{}' is lexically earlier than "
          "the existing pre-release '{}'".format(prerelease, self.prerelease))
    
    if not prerelease:
      prerelease = None
    
    def increment_major():
      self.major += 1
      self.minor = 0
      self.patch = None
    
    def increment_minor():
      self.minor += 1
      self.patch = None
    
    def increment_patch():
      if self.patch is None:
        self.patch = 0
      self.patch += 1
    
    def clear_prerelease():
      self.prerelease = None
      self.prerelease_patch = None
    
    def set_new_prerelease():
      self.prerelease = prerelease
      self.prerelease_patch = None
    
    def increment_prerelease():
      if self.prerelease_patch is None:
        self.prerelease_patch = 1
      self.prerelease_patch += 1
    
    if component_to_increment == "major":
      increment_component_func = increment_major
    elif component_to_increment == "minor":
      increment_component_func = increment_minor
    elif component_to_increment == "patch":
      increment_component_func = increment_patch
    
    if prerelease is None:
      increment_component_func()
      clear_prerelease()
    else:
      if self.prerelease is None:
        increment_component_func()
        set_new_prerelease()
      else:
        if prerelease == self.prerelease:
          increment_prerelease()
        else:
          set_new_prerelease()
  
  @classmethod
  def parse(cls, version_str):
    """
    Parse the `version_str` string and return a `Version` instance.
    
    Raises:
    
    * `InvalidVersionFormatError` - `version_str` has invalid format.
    """
    ver = Version()
    cls._fill_version_components(ver, version_str)
    return ver
  
  @classmethod
  def _fill_version_components(cls, version_obj, version_str):
    version_str_components = version_str.split("-")
    
    if len(version_str_components) > 2:
      raise InvalidVersionFormatError
    
    cls._set_main_version_components(version_obj, version_str_components[0])
    
    if len(version_str_components) == 2:
      cls._set_prerelease_version_components(version_obj, version_str_components[1])
  
  @classmethod
  def _set_main_version_components(cls, version_obj, main_str_components):
    match = re.search(r'^([0-9]+?)\.([0-9]+?)$', main_str_components)
    
    if match is None:
      match = re.search(r'^([0-9]+?)\.([0-9]+?)\.([1-9]+?)$', main_str_components)
      if match is None:
        raise InvalidVersionFormatError
    
    match_groups = match.groups()
    version_obj.major = int(match_groups[0])
    version_obj.minor = int(match_groups[1])
    if len(match_groups) == 3:
      version_obj.patch = int(match_groups[2])
  
  @classmethod
  def _set_prerelease_version_components(cls, version_obj, prerelease_str_components):
    match = re.search(r'^([a-zA-Z0-9]+?)$', prerelease_str_components)
    
    if match is None:
      match = re.search(r'^([a-zA-Z0-9]+?)\.([2-9]+?)$', prerelease_str_components)
      if match is None:
        raise InvalidVersionFormatError
    
    match_groups = match.groups()
    version_obj.prerelease = match_groups[0]
    if len(match_groups) == 2:
      version_obj.prerelease_patch = int(match_groups[1])


class InvalidVersionFormatError(Exception):
  pass
