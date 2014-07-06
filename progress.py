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

"""
This module:
* defines the interface to update the progress of the work done so far
"""

#===============================================================================

class ProgressUpdater(object):
  
  """
  This class in particular can be used if no progress update is desired.
  
  To use this e.g. in the GUI for a progress bar, one needs to subclass this class
  and define _fill_progress_bar and _set_text_progress_bar methods.
  """
  
  def __init__(self, progress_bar, num_total_tasks=0):
    self.progress_bar = progress_bar
    
    self.num_total_tasks = num_total_tasks
    self._num_finished_tasks = 0
  
  @property
  def num_finished_tasks(self):
    return self._num_finished_tasks
  
  def update(self, num_tasks=0, text=None):
    """
    Advance the progress bar by a given number of finished tasks.
    
    If text is not None, set new text on the progress bar.
    If text is None, the text on the progress bar is preserved.
    """
    if num_tasks != 0:
      if self._num_finished_tasks + num_tasks > self.num_total_tasks:
        raise ValueError("Number of finished tasks exceeds the number of total tasks")
      else:
        self._num_finished_tasks += num_tasks
      
      self._fill_progress_bar()
    
    self._set_text(text)
  
  def reset(self):
    self._num_finished_tasks = 0
    if self.num_total_tasks > 0:
      self._fill_progress_bar()
    self._set_text("")
  
  def _set_text(self, text):
    if text is not None:
      self._set_text_progress_bar(text)
  
  def _fill_progress_bar(self):
    """
    Fill in _num_finished_tasks/num_total_tasks fraction of the progress bar.
    """
    pass
  
  def _set_text_progress_bar(self, text):
    pass
