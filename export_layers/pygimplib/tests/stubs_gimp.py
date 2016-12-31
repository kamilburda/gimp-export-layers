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
This module provides stubs for GIMP objects, classes, etc. that can be used in
unit tests.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

from .. import pgconstants

#===============================================================================


class PdbStub(object):
  
  def __init__(self):
    self._attr_name = b""
  
  def __getattr__(self, name):
    self._attr_name = name
    return self._call
  
  def _call(self, *args):
    return self._attr_name
  
  def gimp_image_new(self, width, height, image_type):
    image = ImageStub()
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
    return type(item) == LayerGroupStub
  
  def gimp_item_set_visible(self, item, visible):
    item.visible = visible


#===============================================================================


class ParasiteStub(object):
  
  def __init__(self, name, flags, data):
    self.name = name
    self.flags = flags
    self.data = data


class ParasiteFunctionsStub(object):
  
  def __init__(self):
    self._parasites = {}
  
  def parasite_find(self, name):
    if name in self._parasites:
      return self._parasites[name]
    else:
      return None
  
  def parasite_list(self):
    return list(self._parasites.keys())
  
  def parasite_attach(self, parasite):
    self._parasites[parasite.name] = parasite
  
  def parasite_detach(self, parasite_name):
    if parasite_name in self._parasites:
      del self._parasites[parasite_name]


#===============================================================================

_IMAGE_FIRST_AVAILABLE_ID = 0
_ITEM_FIRST_AVAILABLE_ID = 0


class ImageStub(ParasiteFunctionsStub):
  
  _IMAGE_FIRST_AVAILABLE_ID = 0
  
  def __init__(self, name=None):
    super().__init__()
    
    global _IMAGE_FIRST_AVAILABLE_ID
    
    self.ID = _IMAGE_FIRST_AVAILABLE_ID
    self.width = 0
    self.height = 0
    self.image_type = None
    self.layers = []
    self.name = name.encode(pgconstants.GIMP_CHARACTER_ENCODING) if name is not None else b""
    self.filename = b""
    self.uri = b""
    self.valid = True
    
    _IMAGE_FIRST_AVAILABLE_ID += 1


class ItemStub(ParasiteFunctionsStub):
  
  def __init__(self, name=None, visible=True):
    super().__init__()
    
    global _ITEM_FIRST_AVAILABLE_ID
    
    self.ID = _ITEM_FIRST_AVAILABLE_ID
    self.width = 0
    self.height = 0
    self.valid = True
    self.visible = visible
    self.offsets = (0, 0)
    self.name = name.encode(pgconstants.GIMP_CHARACTER_ENCODING) if name is not None else b""
    self.image = None
    self.children = []
    
    _ITEM_FIRST_AVAILABLE_ID += 1


class LayerStub(ItemStub):
  
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    
    self.parent = None


class LayerGroupStub(LayerStub):
  
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
  
  @property
  def layers(self):
    return self.children
  
  @layers.setter
  def layers(self, val):
    self.children = val


#===============================================================================


class GimpModuleStub(ParasiteFunctionsStub):
  
  pdb = PdbStub
  Parasite = ParasiteStub
  Image = ImageStub
  Item = ItemStub
  Layer = LayerStub
  GroupLayer = LayerGroupStub


#===============================================================================


class ShelfStub(object):
  
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
