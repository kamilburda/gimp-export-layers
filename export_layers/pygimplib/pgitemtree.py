# -*- coding: utf-8 -*-
#
# Copyright (C) 2014-2018 khalim19
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
This module defines the following classes:

* `ItemTree` - an associative, tree-like structure that stores all GIMP items
  and item groups of a certain type

* subclasses of `ItemTree`:
  
  * `LayerTree` for layers
  
  * `ChannelTree` for channels
  
  * `VectorTree` for vectors (paths)

* `_ItemTreeElement` - wrapper for `gimp.Item` objects containing custom
  attributes derived from the original `gimp.Item` attributes
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *
import future.utils

import abc
import collections
import os

try:
  import cPickle as pickle
except ImportError:
  import pickle

import gimp
from gimp import pdb
import gimpenums

from . import pgconstants
from . import pgobjectfilter
from . import pgpath
from . import pgutils

#===============================================================================


@future.utils.python_2_unicode_compatible
class ItemTree(future.utils.with_metaclass(abc.ABCMeta, object)):
  
  """
  This class is an interface to store all items (and item groups) of a certain
  type (e.g. layers, channels or paths) of a GIMP image in an ordered
  dictionary, allowing to access the items via their IDs or names and get
  various custom attributes derived from the existing item attributes.
  
  Use one of the subclasses for items of a certain type:
  
    * `LayerTree` for layers,
    
    * `ChannelTree` for channels,
    
    * `VectorTree` for vectors (paths).
  
  For custom item attributes, see the documentation for the `_ItemTreeElement`
  class. `_ItemTreeElement` is common for all `ItemTree` subclasses.
  
  Attributes:
  
  * `image` (read-only) - GIMP image to generate item tree from.
  
  * `name` (read-only) - Optional name of the item tree. The name is currently
    used as an identifier of the persistent source for tags in items. See
    `_ItemTreeElement.tags` for more information.
  
  * `is_filtered` - If True, ignore items that do not match the filter
    (`ObjectFilter`) in this object when iterating.
  
  * `filter` - `ObjectFilter` instance where you can add or remove filter rules
    or subfilters to filter items.
  """
  
  def __init__(
        self, image, name=None, is_filtered=False,
        filter_match_type=pgobjectfilter.ObjectFilter.MATCH_ALL):
    self._image = image
    self._name = name
    self.is_filtered = is_filtered
    self._filter_match_type = filter_match_type
    
    # Filters applied to all items in `self._itemtree`
    self.filter = pgobjectfilter.ObjectFilter(self._filter_match_type)
    
    # Contains all items in the item tree (including item groups).
    # key: `_ItemTreeElement.item.ID`
    # value: `_ItemTreeElement` object
    self._itemtree = collections.OrderedDict()
    # key: `_ItemTreeElement.orig_name` (derived from `gimp.Item.name`)
    # value: `_ItemTreeElement` object
    self._itemtree_names = {}
    
    # key: `_ItemTreeElement` object (parent) or None (root of the item tree)
    # value: set of `_ItemTreeElement` objects
    self._uniquified_itemtree = {}
    # key: `_ItemTreeElement` object (parent) or None (root of the item tree)
    # value: set of `_ItemTreeElement.name` strings
    self._uniquified_itemtree_names = {}
    
    self._validated_itemtree = set()
    
    self._fill_item_tree()
  
  @property
  def image(self):
    return self._image
  
  @property
  def name(self):
    return self._name
  
  def __getitem__(self, id_or_name):
    """
    Access an `_ItemTreeElement` object by its `_ItemTreeElement.item.ID`
    attribute or its `orig_name` attribute.
    """
    
    try:
      item_elem = self._itemtree[id_or_name]
    except KeyError:
      item_elem = self._itemtree_names[id_or_name]
    
    return item_elem
  
  def __contains__(self, id_or_name):
    """
    Return True if an `_ItemTreeElement` object is in the item tree, regardless
    of filters. Return False otherwise. The `_ItemTreeElement` object is
    specified by its `_ItemTreeElement.item.ID` attribute or its `orig_name`
    attribute.
    """
    
    return id_or_name in self._itemtree or id_or_name in self._itemtree_names
  
  def __len__(self):
    """
    Return the number of all item tree elements - that is, all immediate
    children of the image and all nested children.
    """
    
    return len([item_elem for item_elem in self])
  
  def __iter__(self):
    """
    If the `is_filtered` attribute is False, iterate over all items. If
    `is_filtered` is True, iterate only over items that match the filter.
    
    Yields:
    
    * `item_elem` - The current `_ItemTreeElement` object.
    """
    
    if not self.is_filtered:
      for item_elem in self._itemtree.values():
        yield item_elem
    else:
      for item_elem in self._itemtree.values():
        if self.filter.is_match(item_elem):
          yield item_elem
  
  def uniquify_name(
        self, item_elem, include_item_path=True,
        uniquifier_position=None, uniquifier_position_parents=None):
    """
    Make the `name` attribute in the specified `_ItemTreeElement` object
    unique among all other, already uniquified `_ItemTreeElement` objects.
    
    To achieve uniquification, a string ("uniquifier") in the form of
    " (<number>)" is inserted at the end of the item names.
    
    Parameters:
    
    * `item_elem` - `_ItemTreeElement` object whose `name` attribute
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
      for elem in list(item_elem.parents) + [item_elem]:
        parent = elem.parent
        
        if parent not in self._uniquified_itemtree:
          self._uniquified_itemtree[parent] = set()
          self._uniquified_itemtree_names[parent] = set()
        
        if elem not in self._uniquified_itemtree[parent]:
          if elem.name in self._uniquified_itemtree_names[parent]:
            if elem == item_elem:
              position = uniquifier_position
            else:
              position = uniquifier_position_parents
            
            elem.name = pgpath.uniquify_string(
              elem.name, self._uniquified_itemtree_names[parent], position)
          
          self._uniquified_itemtree[parent].add(elem)
          self._uniquified_itemtree_names[parent].add(elem.name)
    else:
      # Use None as the root of the item tree.
      parent = None
      
      if parent not in self._uniquified_itemtree_names:
        self._uniquified_itemtree_names[parent] = set()
      
      item_elem.name = pgpath.uniquify_string(
        item_elem.name, self._uniquified_itemtree_names[parent], uniquifier_position)
      self._uniquified_itemtree_names[parent].add(item_elem.name)
  
  def validate_name(self, item_elem, force_validation=False):
    """
    Validate the `name` attribute of the specified item and all of its parents
    if not validated already or if `force_validation` is True.
    """
    
    for elem in list(item_elem.parents) + [item_elem]:
      if elem not in self._validated_itemtree or force_validation:
        elem.name = pgpath.FilenameValidator.validate(elem.name)
        self._validated_itemtree.add(elem)
  
  def reset_name(self, item_elem):
    """
    Reset the name of the specified item to its original name. In addition,
    allow the item to be validated or uniquified again (using `validate_name`
    or `uniquify_name`, respectively).
    """
    
    item_elem.name = item_elem.orig_name
    
    if item_elem in self._validated_itemtree:
      self._validated_itemtree.remove(item_elem)
    if item_elem.parent in self._uniquified_itemtree:
      self._uniquified_itemtree[item_elem.parent].remove(item_elem)
  
  def reset_all_names(self):
    """
    Reset the `name` attribute of all `_ItemTreeElement` instances (regardless
    of item filtering) and clear cache for already uniquified and validated
    `_ItemTreeElement` instances.
    """
    
    for item_elem in self._itemtree.values():
      item_elem.name = item_elem.orig_name
    
    self._uniquified_itemtree.clear()
    self._uniquified_itemtree_names.clear()
    self._validated_itemtree.clear()
  
  def reset_filter(self):
    """
    Reset the filter, creating a new empty `ObjectFilter`.
    """
    
    self.filter = pgobjectfilter.ObjectFilter(self._filter_match_type)
  
  def _fill_item_tree(self):
    """
    Fill the `_itemtree` and `_itemtree_names` dictionaries.
    """
    
    child_items = self._get_children_from_image(self._image)
    child_item_elems = [
      _ItemTreeElement(item, [], None, self._name) for item in child_items]
    
    item_elem_tree = child_item_elems
    
    while item_elem_tree:
      item_elem = item_elem_tree.pop(0)
      
      self._itemtree[item_elem.item.ID] = item_elem
      self._itemtree_names[item_elem.orig_name] = item_elem
      
      item_elem_parents = list(item_elem.parents)
      if self._is_group(item_elem.item):
        child_items = self._get_children_from_item(item_elem.item)
      else:
        child_items = None
      
      if child_items is not None:
        item_elem_parents.append(item_elem)
        child_item_elems = [
          _ItemTreeElement(
            item, item_elem_parents, None, self._name) for item in child_items]
        
        # We break the convention here and access private attributes from
        # `_ItemTreeElement`.
        item_elem._orig_children = child_item_elems
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


class LayerTree(ItemTree):
  
  def _get_children_from_image(self, image):
    return image.layers
  
  def _get_children_from_item(self, item):
    return item.layers
  
  def _is_group(self, item):
    return isinstance(item, gimp.GroupLayer)


class ChannelTree(ItemTree):
  
  def _get_children_from_image(self, image):
    return image.channels


class VectorTree(ItemTree):
  
  def _get_children_from_image(self, image):
    return image.vectors


#===============================================================================


class _ItemTreeElement(object):
  
  """
  This class wraps a `gimp.Item` object and defines custom item attributes.
  
  Note that the attributes will not be up to date if changes were made to the
  original `gimp.Item` object.
  
  Attributes:
  
  * `item` (read-only) - `gimp.Item` object.
  
  * `parents` (read-only) - List of `_ItemTreeElement` parents for this item,
    sorted from the topmost parent to the bottommost (immediate) parent.
  
  * `children` (read-only) - List of `_ItemTreeElement` children for this item.
  
  * `name` - Item name as a `unicode` string, initially equal to the `orig_name`
     attribute. Modify this attribute instead of `gimp.Item.name` to avoid
     modifying the original item.
  
  * `depth` (read-only) - Integer indicating the depth of the item in the item
    tree. 0 means the item is at the top level. The greater the depth, the lower
    the item is in the item tree.
  
  * `parent` (read-only) - Immediate `_ItemTreeElement` parent of this object.
    If this object has no parent, return None.
  
  * `item_type` (read-only) - Item type - one of the following:
      * `ITEM` - normal item,
      * `NONEMPTY_GROUP` - non-empty item group (contains children),
      * `EMPTY_GROUP` - empty item group (contains no children).
  
  * `path_visible` (read-only) - Visibility of all item's parents and this
    item. If all items are visible, `path_visible` is True. If at least one
    of these items is invisible, `path_visible` is False.
  
  * `orig_name` (read-only) - Original `gimp.Item.name` as a Unicode string.
  
  * `tags` - Set of arbitrary strings attached to the item. Tags can be used for
    a variety of purposes, such as special handling of items with specific tags.
    Tags are stored persistently in the `gimp.Item` object (`item` attribute) as
    parasites. The name of the parasite source is given by the
    `tags_source_name` attribute.
  
  * `tags_source_name` - Name of the persistent source for the `tags` attribute.
    Defaults to "tags" if None.
  """
  
  _ITEM_TYPES = ITEM, NONEMPTY_GROUP, EMPTY_GROUP = (0, 1, 2)
  
  def __init__(self, item, parents=None, children=None, tags_source_name=None):
    if item is None:
      raise TypeError("item cannot be None")
    
    self._item = item
    self._parents = parents if parents is not None else []
    self._children = children
    
    self.name = item.name.decode(pgconstants.GIMP_CHARACTER_ENCODING)
    
    self._item_type = None
    self._path_visible = None
    
    self._orig_name = self.name
    self._orig_parents = self._parents
    self._orig_children = self._children
    
    self._tags_source_name = tags_source_name if tags_source_name else "tags"
    self._tags = self._load_tags()
  
  @property
  def item(self):
    return self._item
  
  @property
  def parents(self):
    return self._parents
  
  @parents.setter
  def parents(self, parents):
    self._parents = parents
  
  @property
  def children(self):
    return self._children
  
  @children.setter
  def children(self, children):
    self._children = children
  
  @property
  def depth(self):
    return len(self._parents)
  
  @property
  def parent(self):
    return self._parents[-1] if self._parents else None
  
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
  
  @property
  def orig_name(self):
    return self._orig_name
  
  @property
  def orig_parents(self):
    return iter(self._orig_parents)
  
  @property
  def orig_children(self):
    if self._orig_children is not None:
      return iter(self._orig_children)
    else:
      return None
  
  @property
  def tags(self):
    return self._tags
  
  @property
  def tags_source_name(self):
    return self._tags_source_name
  
  def __str__(self):
    return pgutils.stringify_object(self, self.orig_name)
  
  def get_file_extension(self):
    """
    Get file extension from the `name` attribute, in lowercase. If `name` has no
    file extension, return an empty string.
    """
    
    return pgpath.get_file_extension(self.name)
  
  def get_file_extension_from_orig_name(self):
    """
    Get file extension from the `orig_name` attribute, in lowercase. If
    `orig_name` has no file extension, return an empty string.
    """
    
    return pgpath.get_file_extension(self.orig_name)
  
  def set_file_extension(self, file_extension, keep_extra_trailing_periods=False):
    """
    Set file extension in the `name` attribute.
    
    For more information, see the
    `pgpath.get_filename_with_new_file_extension()` method.
    """
    
    self.name = pgpath.get_filename_with_new_file_extension(
      self.name, file_extension, keep_extra_trailing_periods)
  
  def get_base_name(self):
    """
    Return the item name without its file extension.
    """
    
    file_extension = self.get_file_extension()
    if file_extension:
      return self.name[:-(len(file_extension) + 1)]
    else:
      return self.name
  
  def get_filepath(self, dirpath, include_item_path=True):
    """
    Return file path given the specified directory path, item name and names of
    its parents.
    
    If `include_item_path` is True, create file path in the following format:
    <directory path>/<item path components>/<item name>
    
    If `include_item_path` is False, create file path in the following format:
    <directory path>/<item name>
    
    If the directory path is not an absolute path or is None, prepend the
    current working directory.
    
    Item path components consist of parents' item names, starting with the
    topmost parent.
    """
    
    if dirpath is None:
      dirpath = ""
    
    path = os.path.abspath(dirpath)
    
    if include_item_path:
      path_components = self.get_path_components()
      if path_components:
        path = os.path.join(path, os.path.join(*path_components))
    
    return os.path.join(path, self.name)
  
  def get_path_components(self):
    """
    Return a list of names of all parents of this item as path components.
    """
    
    return [parent.name for parent in self.parents]
  
  def add_tag(self, tag):
    """
    Add the specified tag to the item. If the tag already exists, do nothing.
    The tag is saved to the item persistently.
    """
    
    if tag in self._tags:
      return
    
    self._tags.add(tag)
    
    self._save_tags()
  
  def remove_tag(self, tag):
    """
    Remove the specified tag from the item. If the tag does not exist, raise
    `ValueError`.
    """
    
    if tag not in self._tags:
      raise ValueError("tag '{0}' not found in {1}".format(tag, self))
    
    self._tags.remove(tag)
    
    self._save_tags()
  
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
  
  def _save_tags(self):
    """
    Save tags persistently to the item.
    """
    
    self._item.parasite_detach(self._tags_source_name)
    
    if self._tags:
      self._item.parasite_attach(
        gimp.Parasite(
          self._tags_source_name,
          gimpenums.PARASITE_PERSISTENT | gimpenums.PARASITE_UNDOABLE,
          pickle.dumps(self._tags)))
  
  def _load_tags(self):
    parasite = self._item.parasite_find(self._tags_source_name)
    if parasite:
      return pickle.loads(parasite.data)
    else:
      return set()
