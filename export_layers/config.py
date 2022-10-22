# -*- coding: utf-8 -*-

"""Plug-in configuration.

Use `c` to access, create or modify configuration entries.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import os


c.PLUGIN_NAME = 'export_layers'
c.PLUGIN_SUBDIRPATH = os.path.join(c.PLUGINS_DIRPATH, c.PLUGIN_NAME)
c.LOCALE_DIRPATH = os.path.join(c.PLUGINS_DIRPATH, c.PLUGIN_NAME, 'locale')

c.LOG_MODE = 'exceptions'

c.PLUGIN_TITLE = lambda: _('Export Layers')
c.PLUGIN_VERSION = '3.3.2'
c.PLUGIN_VERSION_RELEASE_DATE = 'October 22, 2022'
c.AUTHOR_NAME = 'khalim19'
c.COPYRIGHT_YEARS = '2013-2022'
c.PAGE_URL = 'https://khalim19.github.io/gimp-plugin-export-layers'
c.DOCS_URL = c.PAGE_URL + '/sections'
c.LOCAL_DOCS_PATH = os.path.join(c.PLUGIN_SUBDIRPATH, 'docs', 'sections', 'index.html')
c.REPOSITORY_NAME = 'gimp-plugin-export-layers'
c.REPOSITORY_URL = 'https://github.com/khalim19/gimp-plugin-export-layers'
c.BUG_REPORT_URL_LIST = [
  ('GitHub', 'https://github.com/khalim19/gimp-plugin-export-layers/issues')
]

# If True, display each step of image/layer editing in GIMP.
c.DEBUG_IMAGE_PROCESSING = False
