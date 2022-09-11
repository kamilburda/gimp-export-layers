# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import inspect
import unittest

from ..setting import settings as pgsettings
from .. import utils as pgutils


class TestReprifyObject(unittest.TestCase):
  
  def test_reprify_object_without_name(self):
    s = pgsettings.Setting('file_extension')
    
    self.assertEqual(
      pgutils.reprify_object(s),
      '<pygimplib.setting.settings.Setting object at {}>'.format(hex(id(s)).rstrip('L')))
  
  def test_reprify_object_with_name(self):
    s = pgsettings.Setting('file_extension')
    
    self.assertEqual(
      pgutils.reprify_object(s, 'file_extension'),
      '<pygimplib.setting.settings.Setting "file_extension" at {}>'.format(
        hex(id(s)).rstrip('L')))


class TestGetModuleRoot(unittest.TestCase):

  def test_get_module_root(self):
    self.assertEqual(
      pgutils.get_module_root(
        'export_layers.pygimplib.tests.test_utils', 'export_layers'),
      'export_layers')
    self.assertEqual(
      pgutils.get_module_root('export_layers.pygimplib.tests.test_utils', 'pygimplib'),
      'export_layers.pygimplib')
    self.assertEqual(
      pgutils.get_module_root('export_layers.pygimplib.tests.test_utils', 'tests'),
      'export_layers.pygimplib.tests')
    self.assertEqual(
      pgutils.get_module_root(
        'export_layers.pygimplib.tests.test_utils', 'test_utils'),
      'export_layers.pygimplib.tests.test_utils')
  
  def test_get_module_root_nonexistent_name_component(self):
    self.assertEqual(
      pgutils.get_module_root(
        'export_layers.pygimplib.tests.test_utils', 'nonexistent_name_component'),
      'export_layers.pygimplib.tests.test_utils')
    
    self.assertEqual(
      pgutils.get_module_root(
        'export_layers.pygimplib.tests.test_utils', '.pygimplib'),
      'export_layers.pygimplib.tests.test_utils')
    
    self.assertEqual(
      pgutils.get_module_root(
        'export_layers.pygimplib.tests.test_utils', 'export_layers.pygimplib'),
      'export_layers.pygimplib.tests.test_utils')
  
  def test_get_module_root_empty_module_name(self):
    self.assertEqual(pgutils.get_module_root('', 'pygimplib'), '')
    self.assertEqual(pgutils.get_module_root('.', 'pygimplib'), '.')
  
  def test_get_module_root_empty_name_component(self):
    self.assertEqual(
      pgutils.get_module_root('export_layers.pygimplib.tests.test_utils', ''),
      'export_layers.pygimplib.tests.test_utils')
    
    self.assertEqual(
      pgutils.get_module_root('export_layers.pygimplib.tests.test_utils', '.'),
      'export_layers.pygimplib.tests.test_utils')


class TestGetCurrentModuleFilepath(unittest.TestCase):
  
  def test_get_current_module_filepath(self):
    self.assertEqual(
      pgutils.get_current_module_filepath(),
      inspect.getfile(inspect.currentframe()))
