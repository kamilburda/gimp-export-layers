#-------------------------------------------------------------------------------
#
# This file is part of libgimpplugin.
#
# Copyright (C) 2014 khalim19 <khalim19@gmail.com>
# 
# libgimpplugin is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# libgimpplugin is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with libgimpplugin.  If not, see <http://www.gnu.org/licenses/>.
#
#-------------------------------------------------------------------------------

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
    self.progress_bar.fraction = float(self._num_finished_tasks) / self.num_total_tasks
  
  def _set_text_progress_bar(self, text):
    self.progress_bar.text = text

#===============================================================================

class TestProgressUpdater(unittest.TestCase):
  
  def setUp(self):
    self.num_total_tasks = 10
    
    self.progress_bar = MockProgressBar()
    self.progress_updater = MockProgressUpdater(self.progress_bar, num_total_tasks=10)
  
  def test_update_no_params(self):
    self.progress_updater.update()
    self.assertEqual(self.progress_updater.progress_bar.fraction, 0)
    self.assertEqual(self.progress_updater.progress_bar.text, "")
  
  def test_update_with_params(self):
    self.progress_updater.update(self.num_total_tasks / 2, "Hi there")
    self.assertEqual(self.progress_updater.num_finished_tasks, self.num_total_tasks / 2)
    self.assertEqual(self.progress_updater.progress_bar.text, "Hi there")
    
    self.progress_updater.update(2)
    self.assertEqual(self.progress_updater.num_finished_tasks, self.num_total_tasks / 2 + 2)
    self.assertEqual(self.progress_updater.progress_bar.text, "Hi there")
    
  def test_update_with_num_finished_tasks_greater_than_num_tasks(self):
    with self.assertRaises(ValueError):
      self.progress_updater.update(self.num_total_tasks + 1)
  
  def test_reset(self):
    self.progress_updater.update(5, "Hi there")
    
    self.progress_updater.reset()
    
    self.assertEqual(self.progress_updater.num_finished_tasks, 0)
    self.assertEqual(self.progress_updater.progress_bar.text, "")
  
  def test_text_is_none(self):
    self.progress_updater.update(0, "Hi there")
    self.progress_updater.update(1, None)
    self.assertEqual(self.progress_updater.progress_bar.text, "Hi there")
  
