# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import unittest

import mock

from .. import overwrite as pgoverwrite
from .. import utils as pgutils


class InteractiveOverwriteChooserStub(pgoverwrite.InteractiveOverwriteChooser):
  
  def __init__(self, values_and_display_names, default_value, default_response):
    super().__init__(
      values_and_display_names, default_value, default_response)
    
    self._values = [value for value, unused_ in self.values_and_display_names]
  
  def _choose(self, filepath):
    if self._overwrite_mode not in self._values:
      self._overwrite_mode = self.default_response
    
    return self._overwrite_mode
  
  def set_overwrite_mode(self, overwrite_mode):
    self._overwrite_mode = overwrite_mode


class TestInteractiveOverwriteChooser(unittest.TestCase):

  _OVERWRITE_MODES = SKIP, REPLACE, RENAME_NEW, RENAME_EXISTING = (0, 1, 2, 3)
  
  def setUp(self):
    self.values_and_display_names = [
      (self.SKIP, 'Skip'), (self.REPLACE, 'Replace'),
      (self.RENAME_NEW, 'Rename new'), (self.RENAME_EXISTING, 'Rename existing')]
    self.default_value = self.REPLACE
    self.default_response = self.SKIP
    self.overwrite_chooser = InteractiveOverwriteChooserStub(
      self.values_and_display_names, self.default_value, self.default_response)
  
  def test_choose_overwrite_default_value(self):
    self.overwrite_chooser.choose()
    self.assertEqual(self.overwrite_chooser.overwrite_mode, self.default_value)

  def test_choose_overwrite(self):
    for mode in self._OVERWRITE_MODES:
      self.overwrite_chooser.set_overwrite_mode(mode)
      self.overwrite_chooser.choose()
      self.assertEqual(self.overwrite_chooser.overwrite_mode, mode)
    
  def test_choose_overwrite_default_response(self):
    self.overwrite_chooser.set_overwrite_mode(-1)
    self.overwrite_chooser.choose()
    self.assertEqual(self.overwrite_chooser.overwrite_mode, self.default_response)


class TestHandleOverwrite(unittest.TestCase):
  
  def setUp(self):
    self.filepath = '/test/image.png'
    self.overwrite_chooser = pgoverwrite.NoninteractiveOverwriteChooser(
      pgoverwrite.OverwriteModes.REPLACE)
  
  @mock.patch(pgutils.get_pygimplib_module_path() + '.overwrite.os.path.exists')
  def test_handle_overwrite_file_exists(self, mock_os_path_exists):
    mock_os_path_exists.return_value = True
    
    self.assertEqual(
      pgoverwrite.handle_overwrite(self.filepath, self.overwrite_chooser),
      (self.overwrite_chooser.overwrite_mode, self.filepath))
  
  @mock.patch(pgutils.get_pygimplib_module_path() + '.overwrite.os.path.exists')
  def test_handle_overwrite_file_does_not_exist(self, mock_os_path_exists):
    mock_os_path_exists.return_value = False
    
    self.assertEqual(
      pgoverwrite.handle_overwrite(self.filepath, self.overwrite_chooser),
      (pgoverwrite.OverwriteModes.DO_NOTHING, self.filepath))
