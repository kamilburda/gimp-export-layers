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

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

str = unicode

import unittest

from .. import pgsettingutils

#===============================================================================


class TestSettingAttributeGenerators(unittest.TestCase):
  
  def test_get_processed_display_name(self):
    self.assertEqual(
      pgsettingutils.get_processed_display_name(None, 'my_setting_name'), "My setting name")
    self.assertEqual(
      pgsettingutils.get_processed_display_name("My display name", 'my_setting_name'), "My display name")
  
  def test_get_processed_description(self):
    self.assertEqual(
      pgsettingutils.get_processed_description(None, 'My _Setting Name'), "My Setting Name")
    self.assertEqual(
      pgsettingutils.get_processed_description("My description", 'My _Setting Name'), "My description")
