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

from export_layers import pygimplib as pg


def init():
  """
  Initialize pygimplib configuration entries for this plug-in.
  """
  pg.config.PLUGIN_NAME = "export_layers"
  
  pg.config.PLUGIN_SUBDIRPATH = os.path.join(
    pg.config.PLUGINS_DIRPATH, pg.config.PLUGIN_NAME)
  
  pg.config.LOCALE_DIRPATH = os.path.join(
    pg.config.PLUGINS_DIRPATH, pg.config.PLUGIN_NAME, "locale")
  
  pg.config.LOG_MODE = pg.logging.LOG_OUTPUT_FILES
  
  pg.config.PLUGIN_TITLE = lambda: _("Export Layers")
  pg.config.PLUGIN_VERSION = "3.3.1"
  pg.config.PLUGIN_VERSION_RELEASE_DATE = "February 04, 2019"
  pg.config.AUTHOR_NAME = "khalim19"
  pg.config.AUTHOR_CONTACT = "khalim19@gmail.com"
  pg.config.PAGE_URL = "https://khalim19.github.io/gimp-plugin-export-layers"
  pg.config.DOCS_URL = pg.config.PAGE_URL + "/sections"
  pg.config.REPOSITORY_NAME = "gimp-plugin-export-layers"
  pg.config.REPOSITORY_URL = (
    "https://github.com/khalim19/gimp-plugin-export-layers")
  pg.config.BUG_REPORT_URL_LIST = [
    ("GitHub", "https://github.com/khalim19/gimp-plugin-export-layers/issues")
  ]
  
  pg.config.LOCAL_DOCS_PATH = os.path.join(
    pg.config.PLUGIN_SUBDIRPATH, "docs", "sections", "index.html")
  
  pg.config.COPYRIGHT_YEARS = "2013-2019"
  
  # If True, display each step of image/layer editing in GIMP.
  pg.config.DEBUG_IMAGE_PROCESSING = False
