# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import io
import sys
import unittest

import mock
import parameterized

from .. import logging as pglogging
from .. import utils as pgutils


class TestCreateLogFile(unittest.TestCase):
  
  @parameterized.parameterized.expand([
    ('valid_file_and_first_dirpath',
     ['file'], [None, None], 'file', 1),
    
    ('valid_file_and_second_dirpath',
     ['file'], [OSError(), None], 'file', 2),
    
    ('valid_file_invalid_dirpath',
     ['file'], [OSError(), OSError()], None, 2),
    
    ('valid_second_file',
     [IOError(), 'file'], [None, None], 'file', 2),
    
    ('invalid_file',
     IOError(), [None, None], None, 2),
  ])
  @mock.patch(pgutils.get_pygimplib_module_path() + '.logging._path_dirs.make_dirs')
  @mock.patch(pgutils.get_pygimplib_module_path() + '.logging.io.open')
  def test_create_log_file(
        self,
        test_case_name_suffix,
        io_open_side_effect,
        make_dirs_side_effect,
        expected_result,
        expected_num_calls_make_dirs,
        mock_io_open,
        mock_make_dirs):
    log_dirpaths = ['dirpath_1', 'dirpath_2']
    log_filename = 'output.log'
    
    mock_io_open.side_effect = io_open_side_effect
    mock_make_dirs.side_effect = make_dirs_side_effect
        
    log_file = pglogging.create_log_file(log_dirpaths, log_filename)
    
    self.assertEqual(log_file, expected_result)
    self.assertEqual(mock_make_dirs.call_count, expected_num_calls_make_dirs)


@mock.patch('sys.stdout', new=io.StringIO())
class TestTee(unittest.TestCase):
  
  def setUp(self):
    self.string_file = io.StringIO()
  
  def test_write(self):
    pglogging.Tee(sys.stdout, self.string_file, log_header_title='Test Header')
    
    print('Hello')
    self.assertTrue(self.string_file.getvalue().endswith('Hello\n'))
    self.assertTrue('Test Header' in self.string_file.getvalue())
    
    print('Hi There Again')
    self.assertTrue(self.string_file.getvalue().endswith('Hello\nHi There Again\n'))
  
  def test_start_and_stop(self):
    tee_stdout = pglogging.Tee(
      sys.stdout,
      self.string_file,
      log_header_title='Test Header',
      start=False)
    
    print('Hi There')
    self.assertFalse(self.string_file.getvalue().endswith('Hi There\n'))
    
    tee_stdout.start(self.string_file)
    print('Hello')
    self.assertTrue(self.string_file.getvalue().endswith('Hello\n'))
    
    string_value = self.string_file.getvalue()
    tee_stdout.stop()
    print('Hi There Again')
    self.assertFalse(string_value.endswith('Hi There Again\n'))
  
  def test_invalid_stream(self):
    with self.assertRaises(ValueError):
      pglogging.Tee(
        'invalid_stream', self.string_file, log_header_title='Test Header', start=False)
