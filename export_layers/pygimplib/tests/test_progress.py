#-------------------------------------------------------------------------------
#
# This file is part of pygimplib.
#
# Copyright (C) 2014, 2015 khalim19 <khalim19@gmail.com>
#
# pygimplib is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pygimplib is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pygimplib.  If not, see <http://www.gnu.org/licenses/>.
#
#-------------------------------------------------------------------------------

#===============================================================================

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division

str = unicode

#===============================================================================

import unittest

from .. import progress

#===============================================================================


class MockProgressBar(object):
  
  def __init__(self):
    self.text = ""
    self.fraction = 0.0


class MockProgressUpdater(progress.ProgressUpdater):
  
  def _update_progress_bar(self):
    self.progress_bar.fraction = self._num_finished_tasks / self.num_total_tasks
  
  def _set_text_progress_bar(self, text):
    self.progress_bar.text = text


#===============================================================================


class TestProgressUpdater(unittest.TestCase):
  
  def setUp(self):
    self.num_total_tasks = 10
    
    self.progress_bar = MockProgressBar()
    self.progress_updater = MockProgressUpdater(self.progress_bar, num_total_tasks=10)
  
  def test_update_tasks(self):
    self.progress_updater.update_tasks(self.num_total_tasks / 2)
    self.assertEqual(self.progress_updater.num_finished_tasks, self.num_total_tasks / 2)
    self.progress_updater.update_tasks(2)
    self.assertEqual(self.progress_updater.num_finished_tasks, self.num_total_tasks / 2 + 2)
  
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
  
