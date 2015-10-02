#-------------------------------------------------------------------------------
#
# This file is part of pygimplib.
#
# Copyright (C) 2014, 2015 khalim19 <khalim19@gmail.com>
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
#-------------------------------------------------------------------------------

"""
This module contains mock objects for GIMP objects, classes, etc. that can be
used in unit tests.
"""

#===============================================================================

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division

str = unicode

#===============================================================================


class MockPDB(object):
  
  def __init__(self):
    self._attr_name = b""
  
  def __getattr__(self, name):
    self._attr_name = name
    return self._call
  
  def _call(self, *args):
    return self._attr_name
  
  def gimp_image_new(self, width, height, image_type):
    image = MockImage()
    image.width = width
    image.height = height
    image.image_type = image_type
    
    return image
  
  def gimp_image_delete(self, image):
    image.valid = False
  
  def gimp_image_is_valid(self, image):
    if image is not None:
      return image.valid
    else:
      return False
  
  def gimp_item_is_group(self, item):
    return type(item) == MockLayerGroup
  
  def gimp_item_set_visible(self, item, visible):
    item.visible = visible


class MockImage(object):
  
  def __init__(self, name=None):
    self.ID = 0
    self.width = 0
    self.height = 0
    self.image_type = None
    self.layers = []
    self.name = name.encode() if name is not None else b""
    self.filename = b""
    self.uri = b""
    self.valid = True


class MockItem(object):
  
  def __init__(self, name=None, visible=True):
    self.ID = 0
    self.width = 0
    self.height = 0
    self.valid = True
    self.visible = visible
    self.offsets = (0, 0)
    self.name = name.encode() if name is not None else b""
    self.image = None
    self.children = []


class MockLayer(MockItem):
  
  def __init__(self, *args, **kwargs):
    super(MockLayer, self).__init__(*args, **kwargs)
    
    self.parent = None


class MockLayerGroup(MockLayer):
  
  def __init__(self, *args, **kwargs):
    super(MockLayerGroup, self).__init__(*args, **kwargs)
  
  @property
  def layers(self):
    return self.children
  
  @layers.setter
  def layers(self, val):
    self.children = val


class MockGimpShelf(object):
  
  def __init__(self):
    self._shelf = {}
  
  def __getitem__(self, key):
    return self._shelf[key]
  
  def __setitem__(self, key, value):
    self._shelf[key] = value
  
  def __delitem__(self, key):
    self._shelf[key] = b""
  
  def has_key(self, key):
    return key in self._shelf


class MockGimpParasite(object):
  
  class Parasite(object):
    
    def __init__(self, name, flags, data):
      self.name = name
      self.flags = flags
      self.data = data
  
  def __init__(self):
    self._parasites = {}
  
  def parasite_find(self, name):
    if name in self._parasites:
      return self._parasites[name]
    else:
      return None
  
  def parasite_attach(self, parasite):
    self._parasites[parasite.name] = parasite

