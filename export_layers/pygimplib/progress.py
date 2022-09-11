# -*- coding: utf-8 -*-

"""Interface for updating the progress of the work done so far."""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *


class ProgressUpdater(object):
  """
  This class wraps the behavior of a progress bar used in GUIs.
  
  This class in particular can be used if no progress update is desired.
  
  To use this in the GUI for a progress bar, subclass this class and override
  the `_fill_progress_bar()` and `_set_text_progress_bar()` methods.
  
  Attributes:
  
  * `progress_bar` - Progress bar (GUI element).
  
  * `num_total_tasks` - Number of total tasks to complete.
  
  * `num_finished_tasks` (read-only) - Number of tasks finished so far.
  """
  
  def __init__(self, progress_bar, num_total_tasks=0):
    self.progress_bar = progress_bar
    self.num_total_tasks = num_total_tasks
    
    self._num_finished_tasks = 0
  
  @property
  def num_finished_tasks(self):
    return self._num_finished_tasks
  
  def update_tasks(self, num_tasks=1):
    """
    Advance the progress bar by a given number of tasks finished.
    
    Raises:
    
    * `ValueError` - Number of finished tasks exceeds the number of total tasks.
    """
    if self._num_finished_tasks + num_tasks > self.num_total_tasks:
      raise ValueError('number of finished tasks exceeds the number of total tasks')
    
    self._num_finished_tasks += num_tasks
    
    self._fill_progress_bar()
  
  def update_text(self, text):
    """
    Update text in the progress bar. Use `None` or an empty string to remove the
    text.
    """
    if text is None:
      text = ''
    self._set_text_progress_bar(text)
  
  def reset(self):
    """
    Empty the progress bar and remove its text.
    """
    self._num_finished_tasks = 0
    if self.num_total_tasks > 0:
      self._fill_progress_bar()
    self._set_text_progress_bar('')
  
  def _fill_progress_bar(self):
    """
    Fill in `num_finished_tasks`/`num_total_tasks` fraction of the progress bar.
    
    This is a method to be overridden by a subclass that implements a
    GUI-specific progress updater.
    """
    pass
  
  def _set_text_progress_bar(self, text):
    """
    Set the text of the progress bar.
    
    This is a method to be overridden by a subclass that implements a
    GUI-specific progress updater.
    """
    pass
