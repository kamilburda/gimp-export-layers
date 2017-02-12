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

import unittest

from .. import pgprogress

#===============================================================================


class ProgressBarStub(object):
  
  def __init__(self):
    self.text = ""
    self.fraction = 0.0


class ProgressUpdaterStub(pgprogress.ProgressUpdater):
  
  def _update_progress_bar(self):
    self.progress_bar.fraction = self._num_finished_tasks / self.num_total_tasks
  
  def _set_text_progress_bar(self, text):
    self.progress_bar.text = text


#===============================================================================


class TestProgressUpdater(unittest.TestCase):
  
  def setUp(self):
    self.num_total_tasks = 10
    
    self.progress_bar = ProgressBarStub()
    self.progress_updater = ProgressUpdaterStub(self.progress_bar, num_total_tasks=10)
  
  def test_update_tasks(self):
    self.progress_updater.update_tasks(self.num_total_tasks / 2)
    self.assertEqual(self.progress_updater.num_finished_tasks, self.num_total_tasks / 2)
    self.progress_updater.update_tasks(2)
    self.assertEqual(
      self.progress_updater.num_finished_tasks, self.num_total_tasks / 2 + 2)
  
  def test_update_text(self):
    self.progress_updater.update_text("Hi there")
    self.assertEqual(self.progress_updater.progress_bar.text, "Hi there")
    self.progress_updater.update_text(None)
    self.assertEqual(self.progress_updater.progress_bar.text, "")
  
  def test_update_with_num_finished_tasks_greater_than_num_tasks(self):
    with self.assertRaises(ValueError):
      self.progress_updater.update_tasks(self.num_total_tasks + 1)
  
  def test_update_with_zero_num_finished_tasks(self):
    self.progress_updater.num_total_tasks = 0
    with self.assertRaises(ValueError):
      self.progress_updater.update_tasks(1)
  
  def test_reset(self):
    self.progress_updater.update_text("Hi there")
    self.progress_updater.update_tasks(2)
    self.progress_updater.reset()
    
    self.assertEqual(self.progress_updater.num_finished_tasks, 0)
    self.assertEqual(self.progress_updater.progress_bar.text, "")
