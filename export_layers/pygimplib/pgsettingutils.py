# -*- coding: utf-8 -*-
#
# This file is part of pygimplib.
#
# Copyright (C) 2014-2016 khalim19 <khalim19@gmail.com>
#
# pygimplib is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pygimplib is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pygimplib.  If not, see <http://www.gnu.org/licenses/>.
#

"""
This module contains various helper classes and functions for `pgsetting*`
modules.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

str = unicode

#===============================================================================


def get_processed_display_name(setting_display_name, setting_name):
  if setting_display_name is not None:
    return setting_display_name
  else:
    return generate_display_name(setting_name)


def generate_display_name(setting_name):
  return setting_name.replace("_", " ").capitalize()


def get_processed_description(setting_description, setting_display_name):
  if setting_description is not None:
    return setting_description
  else:
    return generate_description(setting_display_name)


def generate_description(display_name):
  # Underscores in display names used as mnemonics are usually undesired in
  # descriptions, hence their removal.
  return display_name.replace("_", "")
