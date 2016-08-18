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

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

str = unicode

import abc
import collections
import os
import re

import gimp

pdb = gimp.pdb

from . import objectfilter
from . import pgfileformats
from . import pgpath

#===============================================================================


class ItemData(object):
  
  """
  This class is an interface to store all items (and item groups) of a certain
  type (e.g. layers, channels or paths) of a GIMP image in an ordered
  dictionary, allowing to access the items via their IDs or names and get
  various custom attributes derived from the existing item attributes.
  
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
    self._image = image
    self.is_filtered = is_filtered
    
    self._filter_match_type = filter_match_type
    
    # Filters applied to all items in self._itemdata
    self._filter = objectfilter.ObjectFilter(self._filter_match_type)
    
    # Contains all items in the item tree (including item groups).
    # key: `_ItemDataElement.item.ID`
    # value: `_ItemDataElement` object
    self._itemdata = collections.OrderedDict()
    # key: `_ItemDataElement.orig_name` (derived from `gimp.Item.name`, which is unique)
    # value: `_ItemDataElement` object
    self._itemdata_names = {}
    
    # key: `_ItemDataElement` object (parent) or None (root of the item tree)
    # value: set of `_ItemDataElement` objects
    self._uniquified_itemdata = {}
    # key: `_ItemDataElement` object (parent) or None (root of the item tree)
    # value: set of `_ItemDataElement.name` strings
    self._uniquified_itemdata_names = {}
    
    self._validated_itemdata = set()
    
    self._fill_item_data()
  
  @property
  def image(self):
    return self._image
  
  @property
  def filter(self):
    return self._filter
  
  def __getitem__(self, id_or_name):
    """
    Access an `_ItemDataElement` object by its `_ItemDataElement.item.ID`
    attribute or its `orig_name` attribute.
    """
    
    try:
      item_elem = self._itemdata[id_or_name]
    except KeyError:
      item_elem = self._itemdata_names[id_or_name]
    
    return item_elem
  
  def __contains__(self, id_or_name):
    """
    Return True if an `_ItemDataElement` object is in the item data, specified
    by its `_ItemDataElement.item.ID` attribute or its `orig_name` attribute.
    Return False otherwise.
    """
    
    return id_or_name in self._itemdata or id_or_name in self._itemdata_names
  
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
          self._uniquified_itemdata_names[parent] = set()
        
        if elem not in self._uniquified_itemdata[parent]:
          if elem.name in self._uniquified_itemdata_names[parent]:
            if elem == item_elem:
              position = uniquifier_position
            else:
              position = uniquifier_position_parents
            
            elem.name = pgpath.uniquify_string(elem.name, self._uniquified_itemdata_names[parent], position)
          
          self._uniquified_itemdata[parent].add(elem)
          self._uniquified_itemdata_names[parent].add(elem.name)
    else:
      # Use None as the root of the item tree.
      parent = None
      
      if parent not in self._uniquified_itemdata_names:
        self._uniquified_itemdata_names[parent] = set()
      
      item_elem.name = pgpath.uniquify_string(
        item_elem.name, self._uniquified_itemdata_names[parent], uniquifier_position)
      self._uniquified_itemdata_names[parent].add(item_elem.name)
  
  def validate_name(self, item_elem, force_validation=False):
    """
    Validate the `name` attribute of the specified item and all of its parents
    if not validated already or if `force_validation` is True.
    """
    
    for elem in item_elem.parents + [item_elem]:
      if elem not in self._validated_itemdata or force_validation:
        elem.name = pgpath.FilenameValidator.validate(elem.name)
        self._validated_itemdata.add(elem)
  
  def reset_name(self, item_elem):
    """
    Reset the name of the specified item to its original name. In addition,
    allow the item to be validated or uniquified again (using `validate_name`
    or `uniquify_name`, respectively).
    """
    
    item_elem.name = item_elem.orig_name
    
    if item_elem in self._validated_itemdata:
      self._validated_itemdata.remove(item_elem)
    if item_elem.parent in self._uniquified_itemdata:
      self._uniquified_itemdata[item_elem.parent].remove(item_elem)
  
  def add_tag(self, item_elem, tag):
    """
    Add the specified tag to the specified item. Prepend the tag to the original
    item name as well. If the tag already exists, do nothing.
    
    If the original item name was modified externally (by GIMP in order to
    ensure that item names are unique), return True, otherwise return False.
    """
    
    if tag in item_elem.tags:
      return False
    
    item_elem.tags.add(tag)
    
    new_item_name = "[{0}] {1}".format(tag, item_elem.orig_name)
    
    item_name_modified_externally = self._rename_item_elem(item_elem, new_item_name)
    return item_name_modified_externally
  
  def remove_tag(self, item_elem, tag):
    """
    Remove the specified tag from the specified item. Remove the tag from the
    original item name as well. If the original item name contains the tag
    multiple times, all of the occurrences of the tag are removed.
    
    If the original item name was modified externally (by GIMP in order to
    ensure that item names are unique), return True, otherwise return False.
    
    If the tag does not exist in the item name, raise `ValueError`.
    """
    
    if tag not in item_elem.tags:
      raise ValueError("tag '{0}' not found in _ItemDataElement '{1}'".format(tag, item_elem.orig_name))
    
    item_elem.tags.remove(tag)
    
    _unused, index = _parse_tags(item_elem.orig_name)
    tags_str = item_elem.orig_name[:index]
    tags_str_processed = re.sub(r"\[" + re.escape(tag) + r"\] *", r"", tags_str)
    
    new_item_name = (tags_str_processed + item_elem.orig_name[index:])
    
    item_name_modified_externally = self._rename_item_elem(item_elem, new_item_name)
    return item_name_modified_externally
  
  def reset_item_elements(self):
    """
    Reset `name` and `tags` attributes of all `_ItemDataElement` instances
    (regardless of instance filtering) and clear cache for already uniquified
    and validated `_ItemDataElement` instances.
    """
    
    for item_elem in self._itemdata.values():
      item_elem.name = item_elem.orig_name
      item_elem.tags.clear()
    
    self._uniquified_itemdata.clear()
    self._uniquified_itemdata_names.clear()
    self._validated_itemdata.clear()
  
  def reset_filter(self):
    """
    Reset the filter applied to this object.
    """
    
    self._filter = objectfilter.ObjectFilter(self._filter_match_type)
  
  def _rename_item_elem(self, item_elem, new_item_name):
    new_item_name_encoded = new_item_name.encode()
    
    item_elem.item.name = new_item_name_encoded
    
    del self._itemdata_names[item_elem.orig_name]
    
    # We break the convention here and access the `_ItemDataElement._orig_name`
    # private attribute.
    item_elem._orig_name = item_elem.item.name.decode()
    
    self._itemdata_names[item_elem.orig_name] = item_elem
    
    item_name_modified_externally = item_elem.orig_name != new_item_name
    return item_name_modified_externally
  
  def _fill_item_data(self):
    """
    Fill the `_itemdata` and `_itemdata_names` dictionaries.
    """
    
    child_items = self._get_children_from_image(self._image)
    child_item_elems = [_ItemDataElement(item, [], None) for item in child_items]
    
    item_elem_tree = child_item_elems
    
    while item_elem_tree:
      item_elem = item_elem_tree.pop(0)
      
      self._itemdata[item_elem.item.ID] = item_elem
      self._itemdata_names[item_elem.orig_name] = item_elem
      
      item_elem_parents = list(item_elem.parents)
      if self._is_group(item_elem.item):
        child_items = self._get_children_from_item(item_elem.item)
      else:
        child_items = None
      
      if child_items is not None:
        item_elem_parents.append(item_elem)
        child_item_elems = [_ItemDataElement(item, item_elem_parents, None) for item in child_items]
        
        # We break the convention here and access the `_ItemDataElement._children`
        # private attribute.
        item_elem._children = child_item_elems
        
        for child_item_elem in reversed(child_item_elems):
          item_elem_tree.insert(0, child_item_elem)
  
  @abc.abstractmethod
  def _get_children_from_image(self, image):
    """
    Return a list of immediate child items from the specified image.
    
    If no child items exist, return an empty list.
    """
    
    pass
  
  def _get_children_from_item(self, item):
    """
    Return a list of immediate child items from the specified item.
    
    If no child items exist, return an empty list.
    """
    
    return item.children
  
  def _is_group(self, item):
    return pdb.gimp_item_is_group(item)


class LayerData(ItemData):
  
  def _get_children_from_image(self, image):
    return image.layers
  
  def _get_children_from_item(self, item):
    return item.layers
  
  def _is_group(self, item):
    return isinstance(item, gimp.GroupLayer)


class ChannelData(ItemData):
  
  def _get_children_from_image(self, image):
    return image.channels


class PathData(ItemData):
  
  def _get_children_from_image(self, image):
    return image.vectors


#===============================================================================

  
def _parse_tags(str_):
  index = 0
  start_of_tag_index = 0
  is_inside_tag = False
  tag_name = ""
  tags = []
  
  while index < len(str_):
    if str_[index].isspace():
      if is_inside_tag:
        tag_name += str_[index]
    elif str_[index] == "[":
      if not is_inside_tag:
        is_inside_tag = True
        start_of_tag_index = index
      else:
        index = start_of_tag_index
        break
    elif str_[index] == "]":
      if not tag_name.strip() and is_inside_tag:
        index = start_of_tag_index
        break
      
      if is_inside_tag:
        is_inside_tag = False
        tags.append(tag_name)
        tag_name = ""
      else:
        break
    else:
      if is_inside_tag:
        tag_name += str_[index]
      else:
        break
    index += 1
  
  return tags, index


#===============================================================================


def get_file_extension(filename):
  """
  Get file extension from `filename`, in lowercase.
  
  If `filename` has no file extension, return an empty string.
  """
  
  name_lowercase = filename.lower()
  
  if "." not in name_lowercase:
    return ""
  
  file_extension = name_lowercase
  
  while file_extension:
    next_period_index = file_extension.find(".")
    if next_period_index == -1:
      return file_extension
    
    file_extension = file_extension[next_period_index + 1:]
    if file_extension in pgfileformats.file_formats_dict:
      return file_extension
  
  return ""


def set_file_extension(filename, file_extension):
  """
  Set file extension in `filename` and return the new filename.
  
  To remove the file extension from `filename`, pass an empty string, None, or a
  period (".").
  """
  
  filename_extension = get_file_extension(filename)
  
  if filename_extension:
    filename_without_extension = filename[0:len(filename) - len(filename_extension) - 1]
  else:
    filename_without_extension = filename
    if filename_without_extension.endswith("."):
      filename_without_extension = filename_without_extension.rstrip(".")
  
  if file_extension and file_extension.startswith("."):
    file_extension = file_extension.lstrip(".")
  
  if file_extension:
    file_extension = file_extension.lower()
    new_filename = ".".join((filename_without_extension, file_extension))
  else:
    new_filename = filename_without_extension
  
  return new_filename


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
  
  * `children` (read-only) - List of `_ItemDataElement` children for this item.
  
  * `name` - Item name as a `unicode` string, initially equal to the `orig_name`
     attribute. Modify this attribute instead of `gimp.Item.name` to avoid
     modifying the original item.
  
  * `tags` - Set of arbitrary strings attached to the item. Tags can also be
    parsed from the item name by calling `parse_tags`.
  
  * `level` (read-only) - Integer indicating which level in the item tree is
    the item positioned at. 0 means the item is at the top level. The higher
    the level, the deeper the item is in the item tree.
  
  * `parent` (read-only) - Immediate `_ItemDataElement` parent of this object.
    If this object has no parent, return None.
  
  * `orig_name` (read-only) - Original `gimp.Item.name` as a `unicode` string.
  
  * `item_type` (read-only) - Item type - one of the following:
      * `ITEM` - normal item,
      * `NONEMPTY_GROUP` - non-empty item group (contains children),
      * `EMPTY_GROUP` - empty item group (contains no children).
  
  * `path_visible` (read-only) - Visibility of all item's parents and this
    item. If all items are visible, `path_visible` is True. If at least one
    of these items is invisible, `path_visible` is False.
  """
  
  _ITEM_TYPES = ITEM, NONEMPTY_GROUP, EMPTY_GROUP = (0, 1, 2)
  
  def __init__(self, item, parents=None, children=None):
    if item is None:
      raise TypeError("item cannot be None")
    
    self._item = item
    self._parents = parents if parents is not None else []
    self._children = children
    
    self.name = item.name.decode()
    self.tags = set()
    
    self._orig_name = self.name
    self._level = len(self._parents)
    self._parent = self._parents[-1] if self._parents else None
    self._item_type = None
    self._path_visible = None
  
  @property
  def item(self):
    return self._item
  
  @property
  def parents(self):
    return self._parents
  
  @property
  def children(self):
    return self._children
  
  @property
  def orig_name(self):
    return self._orig_name
  
  @property
  def level(self):
    return self._level
  
  @property
  def parent(self):
    return self._parent
  
  @property
  def item_type(self):
    if self._item_type is None:
      if self._children is None:
        self._item_type = self.ITEM
      else:
        if self._children:
          self._item_type = self.NONEMPTY_GROUP
        else:
          self._item_type = self.EMPTY_GROUP
    
    return self._item_type
  
  @property
  def path_visible(self):
    if self._path_visible is None:
      self._path_visible = self._get_path_visibility()
    
    return self._path_visible
  
  def __str__(self):
    return "<{0} '{1}'>".format(type(self).__name__, self.orig_name)
  
  def get_file_extension(self):
    """
    Get file extension from the `name` attribute, in lowercase.
    
    If `name` has no file extension, return an empty string.
    """
    
    return get_file_extension(self.name)
  
  def set_file_extension(self, file_extension):
    """
    Set file extension in the `name` attribute.
    
    To remove the file extension from `name`, pass an empty string, None, or a
    period (".").
    """
    
    self.name = set_file_extension(self.name, file_extension)
  
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
  
  def parse_tags(self):
    """
    Parse tags from the item name. Example:
    
      [background] Layer
    
    inserts "background" to the set of tags and sets "Layer" as the new item
    name.
    
    Tags are only parsed from the beginning of item name. Whitespace between
    tags, before the first tag and after the last tag is removed.
    
    To prevent a tag from being parsed, surround it by nested square
    brackets, e.g. "[[background]]".
    """
    
    tags, index = _parse_tags(self.name)
    
    if tags:
      self.name = self.name[index:]
      self.tags.update(tags)
  
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
