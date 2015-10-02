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
This module defines the following classes:

* `ItemData` - an associative container that stores all GIMP items and item
  groups of a certain type

* subclasses of `ItemData`:
  
  * `LayerData` for layers
  
  * `ChannelData` for channels
  
  * `PathData` for paths

* `_ItemDataElement` - wrapper for `gimp.Item` objects containing custom
  attributes derived from the original `gimp.Item` attributes
"""

#===============================================================================

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division

str = unicode

#===============================================================================

import os
import abc

from collections import OrderedDict
from collections import namedtuple

import gimp

from . import pgfileformats
from . import pgpath
from . import objectfilter

#===============================================================================

pdb = gimp.pdb

#===============================================================================


class ItemData(object):
  
  """
  This class is an interface to store all items (and item groups) of a certain
  type (e.g. layers, channels or paths) of a GIMP image in an ordered
  dictionary, allowing to access the items via their names and get various
  custom attributes derived from the existing item attributes.
  
  Use one of the subclasses for items of a certain type:
  
    * `LayerData` for layers,
    
    * `ChannelData` for channels,
    
    * `PathData` for paths (vectors).
  
  For custom item attributes, see the documentation for the `_ItemDataElement`
  class. `_ItemDataElement` is common for all `ItemData` subclasses.
  
  Attributes:
  
  * `image` - GIMP image to get item data from.
  
  * `is_filtered` - If True, ignore items that do not match the filter
    (`ObjectFilter`) in this object when iterating.
  
  * `filter` (read-only) - `ObjectFilter` instance where you can add or remove
    filter rules or subfilters to filter items.
  """
  
  __metaclass__ = abc.ABCMeta
  
  def __init__(self, image, is_filtered=False, filter_match_type=objectfilter.ObjectFilter.MATCH_ALL):
    
    self.image = image
    
    self.is_filtered = is_filtered
    
    # Filters applied to all items in self._itemdata
    self._filter = objectfilter.ObjectFilter(filter_match_type)
    
    # Contains all items (including item groups) in the item tree.
    # key: `_ItemDataElement.orig_name` (derived from `gimp.Item.name`, which is unique)
    # value: `_ItemDataElement` object
    self._itemdata = OrderedDict()
    
    # key `_ItemDataElement` object (parent) or None (root of the item tree)
    # value: set of `_ItemDataElement` objects
    self._uniquified_itemdata = {}
    
    self._fill_item_data()
  
  @property
  def filter(self):
    return self._filter
  
  def __getitem__(self, name):
    """
    Access an `_ItemDataElement` object by its `orig_name` attribute.
    """
    
    return self._itemdata[name]
  
  def __contains__(self, name):
    """
    Return True if an `_ItemDataElement` object, specified by its `orig_name`
    attribute, is in the item data. Otherwise return False.
    """
    
    return name in self._itemdata
  
  def __len__(self):
    """
    Return the number of all item data elements - that is, all immediate
    children of the image and all nested children.
    """
    
    return len([item_elem for item_elem in self])
  
  def __iter__(self):
    """
    If `is_filtered` is False, iterate over all items. If `is_filtered` is True,
    iterate only over items that match the filter in this object.
    
    Yields:
    
    * `item_elem` - The current `_ItemDataElement` object.
    """
    
    if not self.is_filtered:
      for item_elem in self._itemdata.values():
        yield item_elem
    else:
      for item_elem in self._itemdata.values():
        if self._filter.is_match(item_elem):
          yield item_elem
  
  def _items(self):
    """
    Yield current (`gimp.Item.name`, `_ItemDataElement` object) tuple.
    """
    
    if not self.is_filtered:
      for name, item_elem in self._itemdata.items():
        yield name, item_elem
    else:
      for name, item_elem in self._itemdata.items():
        if self._filter.is_match(item_elem):
          yield name, item_elem
  
  def uniquify_name(self, item_elem, include_item_path=True,
                    uniquifier_position=None, uniquifier_position_parents=None):
    """
    Make the `name` attribute in the specified `_ItemDataElement` object
    unique among all other, already uniquified `_ItemDataElement` objects.
    
    To achieve uniquification, a string ("uniquifier") in the form of
    " (<number>)" is inserted at the end of the item names.
    
    Parameters:
    
    * `item_elem` - `_ItemDataElement` object whose `name` attribute
      will be uniquified.
    
    * `include_item_path` - If True, take the item path into account when
      uniquifying.
      
    * `uniquifier_position` - Position (index) where the uniquifier is inserted
      into the current item. If the position is None, insert the uniquifier at
      the end of the item name (i.e. append it).
      
    * `uniquifier_position_parents` - Position (index) where the uniquifier is
      inserted into the parents of the current item. If the position is None,
      insert the uniquifier at the end of the name of each parent. This
      parameter has no effect if `include_item_path` is False.
    """
    
    if include_item_path:
      for elem in item_elem.parents + [item_elem]:
        parent = elem.parent
        
        if parent not in self._uniquified_itemdata:
          self._uniquified_itemdata[parent] = set()
        
        if elem not in self._uniquified_itemdata[parent]:
          item_names = set([elem_.name for elem_ in self._uniquified_itemdata[parent]])
          if elem.name not in item_names:
            self._uniquified_itemdata[parent].add(elem)
          else:
            if elem == item_elem:
              position = uniquifier_position
            else:
              position = uniquifier_position_parents
            
            elem.name = pgpath.uniquify_string(elem.name, item_names, position)
            self._uniquified_itemdata[parent].add(elem)
    else:
      # Use None as the root of the item tree.
      parent = None
      
      if parent not in self._uniquified_itemdata:
        self._uniquified_itemdata[parent] = set()
      
      item_elem.name = pgpath.uniquify_string(
        item_elem.name, self._uniquified_itemdata[parent], uniquifier_position)
      self._uniquified_itemdata[parent].add(item_elem.name)
  
  def _fill_item_data(self):
    """
    Fill the _itemdata dictionary, containing
    <gimp.Item.name, _ItemDataElement> pairs.
    """
    
    _ItemTreeNode = namedtuple('_ItemTreeNode', ['children', 'parents'])
    item_tree = [_ItemTreeNode(self._get_children_from_image(self.image), [])]
    
    while item_tree:
      node = item_tree.pop(0)
      
      index = 0
      for item in node.children:
        parents = list(node.parents)
        item_elem = _ItemDataElement(item, parents)
        
        if pdb.gimp_item_is_group(item):
          item_tree.insert(index, _ItemTreeNode(self._get_children_from_item(item), parents + [item_elem]))
          index += 1
        
        self._itemdata[item_elem.orig_name] = item_elem
  
  @abc.abstractmethod
  def _get_children_from_image(self, image):
    """
    Return a list of immediate child items from the specified image.
    
    If no child items exist, return an empty list.
    """
    
    pass
  
  @abc.abstractmethod
  def _get_children_from_item(self, item):
    """
    Return a list of immediate child items from the specified item.
    
    If no child items exist, return an empty list.
    """
    
    pass


class LayerData(ItemData):
  
  def _get_children_from_image(self, image):
    return image.layers
  
  def _get_children_from_item(self, item):
    return item.layers


class ChannelData(ItemData):
  
  def _get_children_from_image(self, image):
    return image.channels
  
  def _get_children_from_item(self, item):
    return item.children


class PathData(ItemData):
  
  def _get_children_from_image(self, image):
    return image.vectors
  
  def _get_children_from_item(self, item):
    return item.children


#===============================================================================


class _ItemDataElement(object):
  
  """
  This class wraps a `gimp.Item` object and defines custom item attributes.
  
  Note that the attributes will not be up to date if changes were made to the
  original `gimp.Item` object.
  
  Attributes:
  
  * `item` (read-only) - `gimp.Item` object.
  
  * `parents` (read-only) - List of `_ItemDataElement` parents for this item,
    sorted from the topmost parent to the bottommost (immediate) parent.
  
  * `level` (read-only) - Integer indicating which level in the item tree is
    the item positioned at. 0 means the item is at the top level. The higher
    the level, the deeper the item is in the item tree.
  
  * `parent` (read-only) - Immediate `_ItemDataElement` parent of this object.
    If this object has no parent, return None.
  
  * `item_type` (read-only) - Item type - one of the following:
      * `ITEM` - normal item,
      * `NONEMPTY_GROUP` - non-empty item group (contains children),
      * `EMPTY_GROUP` - empty item group (contains no children).
  
  * `name` - Item name as a `unicode` string, initially equal to the `orig_name`
     attribute. Modify this attribute instead of `gimp.Item.name` to avoid
     modifying the original item.
  
  * `orig_name` (read-only) - original `gimp.Item.name` as a `unicode` string.
  
  * `path_visible` (read-only) - Visibility of all item's parents and this
    item. If all items are visible, `path_visible` is True. If at least one
    of these items is invisible, `path_visible` is False.
  """
  
  __ITEM_TYPES = ITEM, NONEMPTY_GROUP, EMPTY_GROUP = (0, 1, 2)
  
  def __init__(self, item, parents=None):
    if item is None:
      raise TypeError("item cannot be None")
    
    self.name = item.name.decode()
    self.tags = set()
    
    self._orig_name = self.name
    
    self._item = item
    self._parents = parents if parents is not None else []
    self._level = len(self._parents)
    
    if self._parents:
      self._parent = self._parents[-1]
    else:
      self._parent = None
    
    if pdb.gimp_item_is_group(self._item):
      if self._item.children:
        self._item_type = self.NONEMPTY_GROUP
      else:
        self._item_type = self.EMPTY_GROUP
    else:
      self._item_type = self.ITEM
    
    self._path_visible = self._get_path_visibility()
  
  @property
  def item(self):
    return self._item
  
  @property
  def parents(self):
    return self._parents
  
  @property
  def level(self):
    return self._level
  
  @property
  def parent(self):
    return self._parent
  
  @property
  def item_type(self):
    return self._item_type
  
  @property
  def orig_name(self):
    return self._orig_name
  
  @property
  def path_visible(self):
    return self._path_visible
  
  def get_file_extension(self):
    """
    Get file extension from the `name` attribute, in lowercase.
    
    If `name` has no file extension, return an empty string.
    """
    
    name_lowercase = self.name.lower()
    
    if "." not in name_lowercase:
      return ""
    
    file_extension = name_lowercase
    
    while file_extension:
      next_period_index = file_extension.find(".")
      if next_period_index == -1:
        return file_extension
      
      file_extension = file_extension[next_period_index+1:]
      if file_extension in pgfileformats.file_formats_dict:
        return file_extension
    
    return ""
  
  def set_file_extension(self, file_extension):
    """
    Set file extension in the `name` attribute.
    
    To remove the file extension from `name`, pass an empty string, None, or a
    period (".").
    """
    
    item_file_extension = self.get_file_extension()
    
    if item_file_extension:
      item_name_without_extension = self.name[0:len(self.name) - len(item_file_extension) - 1]
    else:
      item_name_without_extension = self.name
      if item_name_without_extension.endswith("."):
        item_name_without_extension = item_name_without_extension.rstrip(".")
    
    if file_extension and file_extension.startswith("."):
      file_extension = file_extension.lstrip(".")
    
    if file_extension:
      file_extension = file_extension.lower()
      self.name = ".".join((item_name_without_extension, file_extension))
    else:
      self.name = item_name_without_extension
  
  def get_filepath(self, directory, include_item_path=True):
    """
    Return file path given the specified directory, item name and names of its
    parents.
    
    If `include_item_path` is True, create file path in the following format:
    <directory>/<item path components>/<item name>
    
    If `include_item_path` is False, create file path in the following format:
    <directory>/<item name>
    
    If directory is not an absolute path or is None, prepend the current working
    directory.
    
    Item path components consist of parents' item names, starting with the
    topmost parent.
    """
    
    if directory is None:
      directory = ""
    
    path = os.path.abspath(directory)
    
    if include_item_path:
      path_components = self.get_path_components()
      if path_components:
        path = os.path.join(path, os.path.join(*path_components))
    
    path = os.path.join(path, self.name)
    
    return path
  
  def get_path_components(self):
    """
    Return a list of names of all parents of this item as path components.
    """
    
    return [parent.name for parent in self.parents]
  
  def validate_name(self):
    """
    Validate the `name` attribute of this item and all of its parents.
    """
    
    self.name = pgpath.FilenameValidator.validate(self.name)
    for parent in self._parents:
      parent.name = pgpath.FilenameValidator.validate(parent.name)
  
  def _get_path_visibility(self):
    """
    If this item and all of its parents are visible, return True, otherwise
    return False.
    """
    
    path_visible = True
    if not self._item.visible:
      path_visible = False
    else:
      for parent in self._parents:
        if not parent.item.visible:
          path_visible = False
          break
    return path_visible
