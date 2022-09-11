# -*- coding: utf-8 -*-

"""GTK progress bar updater."""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import pygtk
pygtk.require("2.0")
import gtk

from .. import progress as pgprogress

__all__ = [
  "GtkProgressUpdater",
]


class GtkProgressUpdater(pgprogress.ProgressUpdater):
  
  def _fill_progress_bar(self):
    self.progress_bar.set_fraction(self._num_finished_tasks / self.num_total_tasks)
    self._force_update()
  
  def _set_text_progress_bar(self, text):
    self.progress_bar.set_text(text)
    self._force_update()
  
  def _force_update(self):
    # This is necessary for the GTK progress bar to be updated properly.
    # See http://faq.pygtk.org/index.py?req=show&file=faq23.020.htp
    while gtk.events_pending():
      gtk.main_iteration()
