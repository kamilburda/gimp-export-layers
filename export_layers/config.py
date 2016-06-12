#
# This file is part of Export Layers.
#
# Copyright (C) 2013-2015 khalim19 <khalim19@gmail.com>
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
#

"""
This module defines plug-in configuration.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

str = unicode

import os

import export_layers.pygimplib as pygimplib

from export_layers.pygimplib import log_output

#===============================================================================

pygimplib.config.PLUGIN_NAME = "export_layers"
pygimplib.config.LOCALE_PATH = os.path.join(pygimplib.config.PLUGIN_PATH, "locale")
pygimplib.config.DOMAIN_NAME = "gimp-" + pygimplib.config.PLUGIN_NAME.replace("_", "-")

pygimplib.config.LOG_MODE = log_output.EXCEPTIONS_ONLY

pygimplib.config.PLUGIN_TITLE = lambda: _("Export Layers")
pygimplib.config.PLUGIN_VERSION = "2.5"
pygimplib.config.BUG_REPORT_URI_LIST = [
  # ("GIMP Plugin Registry", "http://registry.gimp.org/node/28268"),
  ("GitHub", "https://github.com/khalim19/gimp-plugin-export-layers/issues")
]

# If True, display each step of image/layer editing in GIMP.
pygimplib.config.DEBUG_IMAGE_PROCESSING = False
