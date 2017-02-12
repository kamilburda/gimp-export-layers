# -*- coding: utf-8 -*-
#
# Copyright (C) 2014-2017 khalim19
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

import io
import sys
import unittest

import mock

from .. import pglogging

#===============================================================================


@mock.patch("sys.stdout", new=io.StringIO())
class TestTee(unittest.TestCase):
  
  def setUp(self):
    self.string_file = io.StringIO()
  
  def test_write(self):
    pglogging.Tee(sys.stdout, self.string_file, log_header_title="Test Header")
    
    print("Hello")
    self.assertTrue(self.string_file.getvalue().endswith("Hello\n"))
    self.assertTrue("Test Header" in self.string_file.getvalue())
    
    print("Hi There Again")
    self.assertTrue(self.string_file.getvalue().endswith("Hello\nHi There Again\n"))
  
  def test_start_and_stop(self):
    tee_stdout = pglogging.Tee(
      sys.stdout, self.string_file, log_header_title="Test Header", start=False)
    
    print("Hi There")
    self.assertFalse(self.string_file.getvalue().endswith("Hi There\n"))
    
    tee_stdout.start(self.string_file)
    print("Hello")
    self.assertTrue(self.string_file.getvalue().endswith("Hello\n"))
    
    string_value = self.string_file.getvalue()
    tee_stdout.stop()
    print("Hi There Again")
    self.assertFalse(string_value.endswith("Hi There Again\n"))
  
  def test_invalid_stream(self):
    with self.assertRaises(ValueError):
      pglogging.Tee(
        "invalid_stream", self.string_file, log_header_title="Test Header", start=False)
