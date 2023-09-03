# -*- coding: utf-8 -*-

"""Plug-in configuration.

Use `c` to access, create or modify configuration entries.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import os


c.PLUGIN_NAME = 'export_layers'
c.PLUGINS_DIRPATH = os.path.dirname(os.path.dirname(c.PYGIMPLIB_DIRPATH))
c.PLUGIN_SUBDIRPATH = os.path.join(c.PLUGINS_DIRPATH, c.PLUGIN_NAME)
c.LOCALE_DIRPATH = os.path.join(c.PLUGIN_SUBDIRPATH, 'locale')

c.PLUGINS_LOG_DIRPATHS.insert(0, c.PLUGIN_SUBDIRPATH)

c.LOG_MODE = 'exceptions'

c.PLUGIN_TITLE = lambda: _('Export Layers')
c.PLUGIN_VERSION = '4.0.2'
c.PLUGIN_VERSION_RELEASE_DATE = 'September 03, 2023'
c.AUTHOR_NAME = 'Kamil Burda'
c.COPYRIGHT_YEARS = '2013-2023'
c.PAGE_URL = 'https://kamilburda.github.io/gimp-export-layers'
c.DOCS_URL = c.PAGE_URL + '/sections'
c.LOCAL_DOCS_PATH = os.path.join(c.PLUGIN_SUBDIRPATH, 'docs', 'sections', 'index.html')
c.REPOSITORY_USERNAME = 'kamilburda'
c.REPOSITORY_NAME = 'gimp-export-layers'
c.REPOSITORY_URL = 'https://github.com/kamilburda/gimp-export-layers'
c.BUG_REPORT_URL_LIST = [
  ('GitHub', 'https://github.com/kamilburda/gimp-export-layers/issues')
]

# If True, display each step of image/layer editing in GIMP.
c.DEBUG_IMAGE_PROCESSING = False
