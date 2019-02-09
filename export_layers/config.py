# -*- coding: utf-8 -*-
#
# This file is part of Export Layers.
#
# Copyright (C) 2013-2019 khalim19 <khalim19@gmail.com>
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
This module defines plug-in configuration. Use `c` to access, create or modify
configuration entries.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import os

c.PLUGIN_NAME = "export_layers"
c.PLUGIN_SUBDIRPATH = os.path.join(c.PLUGINS_DIRPATH, c.PLUGIN_NAME)
c.LOCALE_DIRPATH = os.path.join(c.PLUGINS_DIRPATH, c.PLUGIN_NAME, "locale")

c.LOG_MODE = "exceptions"

c.PLUGIN_TITLE = lambda: _("Export Layers")
c.PLUGIN_VERSION = "3.3.1"
c.PLUGIN_VERSION_RELEASE_DATE = "February 04, 2019"
c.AUTHOR_NAME = "khalim19"
c.AUTHOR_CONTACT = "khalim19@gmail.com"
c.COPYRIGHT_YEARS = "2013-2019"
c.PAGE_URL = "https://khalim19.github.io/gimp-plugin-export-layers"
c.DOCS_URL = c.PAGE_URL + "/sections"
c.LOCAL_DOCS_PATH = os.path.join(c.PLUGIN_SUBDIRPATH, "docs", "sections", "index.html")
c.REPOSITORY_NAME = "gimp-plugin-export-layers"
c.REPOSITORY_URL = "https://github.com/khalim19/gimp-plugin-export-layers"
c.BUG_REPORT_URL_LIST = [
  ("GitHub", "https://github.com/khalim19/gimp-plugin-export-layers/issues")
]

# If True, display each step of image/layer editing in GIMP.
c.DEBUG_IMAGE_PROCESSING = False
