# -*- coding: utf-8 -*-

"""Management of version numbers (particularly incrementing)."""

from __future__ import absolute_import, division, print_function, unicode_literals
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
    version_str = '{}.{}'.format(self.major, self.minor)
    
    if self.patch is not None:
      version_str += '.{}'.format(self.patch)
    
    if self.prerelease is not None:
      version_str += '-{}'.format(self.prerelease)
      if self.prerelease_patch is not None:
        version_str += '.{}'.format(self.prerelease_patch)
    
    return version_str
  
  def __repr__(self):
    return '{}({}, {}, {}, {}, {})'.format(
      self.__class__.__name__, self.major, self.minor, self.patch,
      '"' + self.prerelease + '"' if self.prerelease is not None else self.prerelease,
      self.prerelease_patch)
  
  def __lt__(self, other_version):
    this_version_main_components = self._get_main_components_tuple(self)
    other_version_main_components = self._get_main_components_tuple(other_version)
    
    if this_version_main_components < other_version_main_components:
      return True
    elif this_version_main_components > other_version_main_components:
      return False
    else:
      if self.prerelease is not None and other_version.prerelease is None:
        return True
      elif self.prerelease is not None and other_version.prerelease is not None:
        if self.prerelease < other_version.prerelease:
          return True
        elif self.prerelease > other_version.prerelease:
          return False
        else:
          return (
            self._get_default_number(self.prerelease_patch)
            < self._get_default_number(other_version.prerelease_patch))
      else:
        return False
  
  def __le__(self, other_version):
    return self.__lt__(other_version) or self.__eq__(other_version)
  
  def __eq__(self, other_version):
    return (
      (self._get_main_components_tuple(self)
       == self._get_main_components_tuple(other_version))
      and self.prerelease == other_version.prerelease
      and (self._get_default_number(self.prerelease_patch)
           == self._get_default_number(other_version.prerelease_patch)))
  
  def __ne__(self, other_version):
    return not self.__eq__(other_version)
  
  def __gt__(self, other_version):
    return not self.__le__(other_version)
  
  def __ge__(self, other_version):
    return not self.__lt__(other_version)
  
  def increment(self, component_to_increment, prerelease=None):
    """
    Increment the version as per `component_to_increment` and `prerelease`.
    
    `component_to_increment` can be `'major'`, `'minor'` or `'patch'`. Given the
    format `X.Y.Z`, `'major'` increments `X`, `'minor'` increments `Y` and
    `'patch'` increments `Z`. If `patch` attribute is `None` and `'patch'` is
    specified, `1` will be assigned (e.g. `3.3` becomes `3.3.1`).
    
    If the `prerelease` string is not `None` and non-empty, append the
    pre-release to the version. For example, `3.3` with `'major'` compoment and
    `'alpha'` as the pre-release string becomes `4.0-alpha`.
    
    If the version already has the same pre-release, append a number to the
    pre-release (e.g. `4.0-alpha` becomes `4.0-alpha.2`).
    
    If the version already has a different pre-release (lexically earlier than
    `prerelease`), replace the existing pre-release with `prerelease` (e.g.
    `4.0-alpha` with the `'beta'` pre-release becomes `4.0-beta`).
    
    Raises:
    
    * `ValueError`:
      
      * Invalid value for `component_to_increment`.
      * The specified `prerelease` contains non-alphanumeric characters or is
        lexically earlier than the existing `prerelease` attribute.
    """
    if component_to_increment not in ['major', 'minor', 'patch']:
      raise ValueError('invalid version component "{}"'.format(component_to_increment))
    
    if prerelease:
      if not re.search(r'^[a-zA-Z0-9]+$', prerelease):
        raise ValueError('invalid pre-release format "{}"'.format(prerelease))
      
      if prerelease < self.prerelease:
        raise ValueError(
          'the specified pre-release "{}" is lexically earlier than'
          ' the existing pre-release "{}"'.format(prerelease, self.prerelease))
    
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
    
    if component_to_increment == 'major':
      increment_component_func = increment_major
    elif component_to_increment == 'minor':
      increment_component_func = increment_minor
    elif component_to_increment == 'patch':
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
    version_str_components = version_str.split('-')
    
    if len(version_str_components) > 2:
      raise InvalidVersionFormatError
    
    cls._set_main_version_components(version_obj, version_str_components[0])
    
    if len(version_str_components) == 2:
      cls._set_prerelease_version_components(version_obj, version_str_components[1])
  
  @classmethod
  def _set_main_version_components(cls, version_obj, main_str_components):
    match = re.search(r'^([0-9]+?)\.([0-9]+?)$', main_str_components)
    
    if match is None:
      match = re.search(r'^([0-9]+?)\.([0-9]+?)\.([1-9][0-9]*)$', main_str_components)
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
      match = re.search(
        r'^([a-zA-Z0-9]+?)\.([2-9]|[1-9][0-9]+)$', prerelease_str_components)
      if match is None:
        raise InvalidVersionFormatError
    
    match_groups = match.groups()
    version_obj.prerelease = match_groups[0]
    if len(match_groups) == 2:
      version_obj.prerelease_patch = int(match_groups[1])
  
  @staticmethod
  def _get_main_components_tuple(ver):
    return tuple(
      number if number is not None else -1
      for number in [ver.major, ver.minor, ver.patch])
  
  @staticmethod
  def _get_default_number(component):
    return component if component is not None else -1


class InvalidVersionFormatError(Exception):
  pass
