#-------------------------------------------------------------------------------
#
# This file is part of libgimpplugin.
#
# Copyright (C) 2014 khalim19 <khalim19@gmail.com>
# 
# libgimpplugin is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# libgimpplugin is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with libgimpplugin.  If not, see <http://www.gnu.org/licenses/>.
#
#-------------------------------------------------------------------------------

"""
This module contains mock objects for GIMP objects, classes, etc.,
that can be used in unit tests.
"""

#===============================================================================

class MockPDB(object):
  
  def __init__(self):
    self._attr_name = ""
  
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
    return image.valid
  
  def gimp_item_is_group(self, item):
    return type(item) == MockLayerGroup
  
  def gimp_item_set_visible(self, item, visible):
    item.visible = visible

class MockImage(object):
  
  def __init__(self, name=""):
    self.ID = 0
    self.width = 0
    self.height = 0
    self.image_type = None
    self.layers = []
    self.name = name
    self.filename = ""
    self.uri = ""
    self.valid = True

class MockItem(object):
  
  def __init__(self, name="", visible=True):
    self.ID = 0
    self.width = 0
    self.height = 0
    self.valid = True
    self.visible = visible
    self.offsets = (0, 0)
    self.name = name
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
    self._shelf[key] = ''
  
  def has_key(self, key):
    return key in self._shelf
