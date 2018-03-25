# -*- coding: utf-8 -*-
#
# This file is part of Export Layers.
#
# Copyright (C) 2013-2016 khalim19 <khalim19@gmail.com>
#
# Export Layers is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Export Layers is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Export Layers.  If not, see <http://www.gnu.org/licenses/>.

"""
This module defines plug-in configuration.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import os

from export_layers import pygimplib

#===============================================================================


def init():
  """
  Initialize pygimplib configuration entries for this plug-in.
  """
  
  pygimplib.config.PLUGIN_NAME = "export_layers"
  
  pygimplib.config.PLUGIN_SUBDIRPATH = os.path.join(
    pygimplib.config.PLUGINS_DIRPATH, pygimplib.config.PLUGIN_NAME)
  
  pygimplib.config.LOCALE_DIRPATH = os.path.join(
    pygimplib.config.PLUGINS_DIRPATH, pygimplib.config.PLUGIN_NAME, "locale")
  
  pygimplib.config.LOG_MODE = pygimplib.pgconstants.LOG_EXCEPTIONS_ONLY
  
  pygimplib.config.PLUGIN_TITLE = lambda: _("Export Layers")
  pygimplib.config.PLUGIN_VERSION = "3.0"
  pygimplib.config.PAGE_URL = "https://khalim19.github.io/gimp-plugin-export-layers"
  pygimplib.config.REPOSITORY_URL = (
    "https://github.com/khalim19/gimp-plugin-export-layers")
  pygimplib.config.BUG_REPORT_URL_LIST = [
    ("GitHub", "https://github.com/khalim19/gimp-plugin-export-layers/issues")
  ]
  
  pygimplib.config.COPYRIGHT_YEARS = "2014-2017"
  
  # If True, display each step of image/layer editing in GIMP.
  pygimplib.config.DEBUG_IMAGE_PROCESSING = False
