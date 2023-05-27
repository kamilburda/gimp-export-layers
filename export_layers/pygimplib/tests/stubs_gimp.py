# -*- coding: utf-8 -*-

"""Stubs for GIMP objects, classes, etc. usable in automated tests."""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import itertools

from .. import utils as pgutils


class PdbStub(object):
  
  def __init__(self):
    self._attr_name = b''
  
  def __getattr__(self, name):
    self._attr_name = name
    return self._call
  
  def _call(self, *args):
    return self._attr_name
  
  @staticmethod
  def gimp_image_new(width, height, image_type):
    image = ImageStub()
    image.width = width
    image.height = height
    image.image_type = image_type
    image.filename = None
    
    return image
  
  @staticmethod
  def gimp_image_delete(image):
    image.valid = False
  
  @staticmethod
  def gimp_image_is_valid(image):
    if image is not None:
      return image.valid
    else:
      return False
  
  @staticmethod
  def gimp_item_is_group(item):
    return isinstance(item, LayerGroupStub)
  
  @staticmethod
  def gimp_item_set_visible(item, visible):
    item.visible = visible
  
  @staticmethod
  def gimp_item_get_children(item):
    return len(item.children), item.children
  
  @staticmethod
  def gimp_image_set_filename(image, filename):
    image.filename = filename


class PdbProcedureStub(object):
  
  def __init__(
        self,
        name,
        type_,
        params,
        return_vals=None,
        author='',
        blurb='',
        help_='',
        copyright_='',
        date=''):
    self.proc_name = name
    self.proc_type = type_
    self.params = params
    self.return_vals = return_vals if return_vals is not None else ()
    self.proc_author = author
    self.proc_blurb = blurb
    self.proc_help = help_
    self.proc_copyright = copyright_
    self.proc_date = date
  
  def __call__(self, *args, **kwargs):
    pass
  
  @property
  def nparams(self):
    return len(self.params)
  
  @property
  def nreturn_vals(self):
    return len(self.return_vals)


class ParasiteStub(object):
  
  def __init__(self, name, flags, data):
    self.name = name
    self.flags = flags
    self.data = data


class ParasiteFunctionsStubMixin(object):
  
  def __init__(self):
    self._parasites = {}
  
  def parasite_find(self, name):
    if name in self._parasites:
      return self._parasites[name]
    else:
      return None
  
  def parasite_list(self):
    return list(self._parasites)
  
  def parasite_attach(self, parasite):
    self._parasites[parasite.name] = parasite
  
  def parasite_detach(self, parasite_name):
    if parasite_name in self._parasites:
      del self._parasites[parasite_name]


class ImageStub(ParasiteFunctionsStubMixin):
  
  _image_id_counter = itertools.count(start=1)
  
  def __init__(self, name=None):
    super().__init__()
    
    self.ID = self._image_id_counter.next()
    self.width = 0
    self.height = 0
    self.image_type = None
    self.layers = []
    self.name = pgutils.safe_encode_gimp(name)
    self.filename = b''
    self.uri = b''
    self.valid = True


class ItemStub(ParasiteFunctionsStubMixin):
  
  _item_id_counter = itertools.count(start=1)
  
  def __init__(self, name=None, visible=True, parent=None):
    super().__init__()
    
    self.ID = self._item_id_counter.next()
    self.width = 0
    self.height = 0
    self.valid = True
    self.visible = visible
    self.offsets = (0, 0)
    self.name = pgutils.safe_encode_gimp(name)
    self.image = None
    self.children = []
    self.parent = parent


class LayerStub(ItemStub):
  pass


class LayerGroupStub(LayerStub):
  
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
  
  @property
  def layers(self):
    return self.children
  
  @layers.setter
  def layers(self, val):
    self.children = val


class ChannelStub(ItemStub):
  pass


class VectorsStub(ItemStub):
  pass


class DisplayStub(ParasiteFunctionsStubMixin):
  
  def __init__(self, id_=None):
    self.ID = id_


class GimpModuleStub(ParasiteFunctionsStubMixin):
  
  pdb = PdbStub
  Parasite = ParasiteStub
  Image = ImageStub
  Item = ItemStub
  Layer = LayerStub
  GroupLayer = LayerGroupStub
  Channel = ChannelStub
  Vectors = VectorsStub
  Display = DisplayStub


class ShelfStub(object):
  
  def __init__(self):
    self._shelf = {}
  
  def __getitem__(self, key):
    return self._shelf[key]
  
  def __setitem__(self, key, value):
    self._shelf[key] = value
  
  def __delitem__(self, key):
    self._shelf[key] = b''
  
  def has_key(self, key):
    return key in self._shelf
