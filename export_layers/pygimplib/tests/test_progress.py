# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import unittest

from .. import progress as pgprogress


class ProgressBarStub(object):
  
  def __init__(self):
    self.text = ''
    self.fraction = 0.0


class ProgressUpdaterStub(pgprogress.ProgressUpdater):
  
  def _update_progress_bar(self):
    self.progress_bar.fraction = self._num_finished_tasks / self.num_total_tasks
  
  def _set_text_progress_bar(self, text):
    self.progress_bar.text = text


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
    self.progress_updater.update_text('Hi there')
    self.assertEqual(self.progress_updater.progress_bar.text, 'Hi there')
    self.progress_updater.update_text(None)
    self.assertEqual(self.progress_updater.progress_bar.text, '')
  
  def test_update_with_num_finished_tasks_greater_than_num_tasks(self):
    with self.assertRaises(ValueError):
      self.progress_updater.update_tasks(self.num_total_tasks + 1)
  
  def test_update_with_zero_num_finished_tasks(self):
    self.progress_updater.num_total_tasks = 0
    with self.assertRaises(ValueError):
      self.progress_updater.update_tasks(1)
  
  def test_reset(self):
    self.progress_updater.update_text('Hi there')
    self.progress_updater.update_tasks(2)
    self.progress_updater.reset()
    
    self.assertEqual(self.progress_updater.num_finished_tasks, 0)
    self.assertEqual(self.progress_updater.progress_bar.text, '')
