# -*- coding: utf-8 -*-

"""Managing items of a GIMP image (e.g. layers) in a tree-like structure."""

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

from . import objectfilter as pgobjectfilter
from . import path as pgpath
from . import utils as pgutils


@future.utils.python_2_unicode_compatible
class ItemTree(future.utils.with_metaclass(abc.ABCMeta, object)):
  """Interface to store `gimp.Item` objects in a tree-like structure.
  
  Use one of the subclasses for items of a certain type:
  
    * `LayerTree` for layers,
    
    * `ChannelTree` for channels,
    
    * `VectorTree` for vectors (paths).
  
  Each item in the tree is an `_Item` instance. Each item contains `gimp.Item`
  attributes and additional derived attributes.
  
  Items can be directly accessed via their ID or name. Both ID and name are
  unique in the entire tree (GIMP readily ensures that item names are unique).
  
  Item groups (e.g. layer groups) are inserted twice in the tree - as folders
  and as items. Parents of items are always folders.
  
  `ItemTree` is a static data structure, i.e. it does not account for
  modifications, additions or removal of GIMP items by GIMP procedures outside
  this class. To refresh the contents of the tree, create a new `ItemTree`
  instance instead.
  
  Attributes:
  
  * `image` (read-only) - GIMP image to generate item tree from.
  
  * `name` (read-only) - Optional name of the item tree. The name is currently
    used as an identifier of the persistent source for tags in items. See
    `_Item.tags` for more information.
  
  * `is_filtered` - If `True`, ignore items that do not match the filter
    (`ObjectFilter`) in this object when iterating.
  
  * `filter` - `ObjectFilter` instance that allows filtering items based on
    rules.
  """
  
  FOLDER_KEY = 'folder'
  
  def __init__(
        self,
        image,
        name=None,
        is_filtered=False,
        filter_match_type=pgobjectfilter.ObjectFilter.MATCH_ALL):
    self._image = image
    self._name = name
    self.is_filtered = is_filtered
    self._filter_match_type = filter_match_type
    
    # Filters applied to all items in `self._itemtree`
    self.filter = pgobjectfilter.ObjectFilter(self._filter_match_type)
    
    # Contains all items in the item tree (including item groups).
    # key: `_Item.raw.ID` or (`_Item.raw.ID`, `FOLDER_KEY`) in case of folders
    # value: `_Item` instance
    self._itemtree = collections.OrderedDict()
    
    # key:
    #  `_Item.orig_name` (derived from `_Item.raw.name`)
    #   or (`_Item.raw.ID`, `FOLDER_KEY`) in case of folders
    # value: `_Item` instance
    self._itemtree_names = {}
    
    # key: `_Item` instance (parent) or None (item tree root)
    # value: set of `_Item` instances
    self._uniquified_itemtree = {}
    
    # key: `_Item` instance (parent) or None (item tree root)
    # value: set of `_Item.name` strings
    self._uniquified_itemtree_names = {}
    
    self._validated_itemtree = set()
    
    self._build_tree()
  
  @property
  def image(self):
    return self._image
  
  @property
  def name(self):
    return self._name
  
  def __getitem__(self, id_or_name):
    """Returns an `_Item` object by its ID or original name.
    
    An item's ID is the `_Item.raw.ID` attribute. An item's original name is the
    `_Item.orig_name` attribute.
    
    To access an item group as a folder, pass a tuple `(ID or name, 'folder')`.
    For example:
        
        item_tree[4, 'folder']
    """
    try:
      return self._itemtree[id_or_name]
    except KeyError:
      return self._itemtree_names[id_or_name]
  
  def __contains__(self, id_or_name):
    """Returns `True` if an `_Item` object is in the item tree, regardless of
    filters. Return `False` otherwise. The `_Item` object is specified by its
    `_Item.raw.ID` attribute or its `orig_name` attribute.
    """
    return id_or_name in self._itemtree or id_or_name in self._itemtree_names
  
  def __len__(self):
    """Returns the number of items in the tree.
    
    This includes immediate children of the image and nested children. Empty
    item groups (i.e. groups with no children) are excluded.
    
    The returned number of items depends on whether `is_filtered` is `True` or
    `False`.
    """
    return len([item for item in self])
  
  def __iter__(self):
    """Iterates over items, excluding folders and empty item groups.
    
    If the `is_filtered` attribute is `False`, iterate over all items. If
    `is_filtered` is `True`, iterate only over items that match the filter.
    
    Yields:
    
    * `item` - The current `_Item` object.
    """
    if not self.is_filtered:
      for item in self._itemtree.values():
        if item.type != item.FOLDER:
          yield item
    else:
      for item in self._itemtree.values():
        if item.type != item.FOLDER and self.filter.is_match(item):
          yield item
  
  def iter(self, with_folders=True, with_empty_groups=False):
    """Iterates over items, optionally including folders and empty item groups.
    
    If the `is_filtered` attribute is `False`, iterate over all items. If
    `is_filtered` is `True`, iterate only over items that match the filter.
    
    Parameters:
    
    * `with_folders` - If `True`, include folders.
    
    * `with_empty_groups` - If `True`, include empty item groups. Empty item
      groups as folders are still yielded if `with_folders` is `True`.
    
    Yields:
    
    * `item` - The current `_Item` object.
    """
    for item in self._itemtree.values():
      should_yield_item = True
      
      if not with_folders and item.type == item.FOLDER:
        should_yield_item = False
      
      if not with_empty_groups and (item.type == item.GROUP and not item.children):
        should_yield_item = False
      
      if should_yield_item:
        if self.is_filtered and not self.filter.is_match(item):
          should_yield_item = False
      
      if should_yield_item:
        yield item
  
  def uniquify_name(
        self,
        item,
        include_item_path=True,
        uniquifier_position=None,
        uniquifier_position_parents=None):
    """Makes the `name` attribute in the specified `_Item` object unique among
    all other, already uniquified `_Item` objects.
    
    To achieve uniquification, a string ("uniquifier") in the form of
    `' (<number>)'` is inserted at the end of the item names.
    
    Parameters:
    
    * `item` - `_Item` object whose `name` attribute will be uniquified.
    
    * `include_item_path` - If `True`, take the item path into account when
      uniquifying.
      
    * `uniquifier_position` - Position (index) where the uniquifier is inserted
      into the current item. If the position is `None`, insert the uniquifier at
      the end of the item name (i.e. append it).
      
    * `uniquifier_position_parents` - Position (index) where the uniquifier is
      inserted into the parents of the current item. If the position is `None`,
      insert the uniquifier at the end of the name of each parent. This
      parameter has no effect if `include_item_path` is `False`.
    """
    if include_item_path:
      for parent_or_item in list(item.parents) + [item]:
        parent = parent_or_item.parent
        
        if parent not in self._uniquified_itemtree:
          self._uniquified_itemtree[parent] = set()
          self._uniquified_itemtree_names[parent] = set()
        
        if parent_or_item not in self._uniquified_itemtree[parent]:
          if parent_or_item.name in self._uniquified_itemtree_names[parent]:
            if parent_or_item == item:
              position = uniquifier_position
            else:
              position = uniquifier_position_parents
            
            parent_or_item.name = pgpath.uniquify_string(
              parent_or_item.name, self._uniquified_itemtree_names[parent], position)
          
          self._uniquified_itemtree[parent].add(parent_or_item)
          self._uniquified_itemtree_names[parent].add(parent_or_item.name)
    else:
      # Use None as the root of the item tree.
      parent = None
      
      if parent not in self._uniquified_itemtree_names:
        self._uniquified_itemtree_names[parent] = set()
      
      item.name = pgpath.uniquify_string(
        item.name, self._uniquified_itemtree_names[parent], uniquifier_position)
      self._uniquified_itemtree_names[parent].add(item.name)
  
  def validate_name(self, item, force_validation=False):
    """Validates the `name` attribute of the specified item and all of its
    parents if not validated already or if `force_validation` is `True`.
    """
    for parent_or_item in list(item.parents) + [item]:
      if parent_or_item not in self._validated_itemtree or force_validation:
        parent_or_item.name = pgpath.FilenameValidator.validate(parent_or_item.name)
        self._validated_itemtree.add(parent_or_item)
  
  def reset_name(self, item):
    """Resets the name of the specified item to its original name.
    
    In addition, the item can be validated or uniquified again (using
    `validate_name` or `uniquify_name`, respectively).
    """
    item.name = item.orig_name
    
    if item in self._validated_itemtree:
      self._validated_itemtree.remove(item)
    if item.parent in self._uniquified_itemtree:
      self._uniquified_itemtree[item.parent].remove(item)
  
  def reset_all_names(self):
    """Resets the `name` attribute of all `_Item` instances (regardless of item
    filtering) and clears cache for already uniquified and validated `_Item`
    instances.
    """
    for item in self._itemtree.values():
      item.name = item.orig_name
    
    self._uniquified_itemtree.clear()
    self._uniquified_itemtree_names.clear()
    self._validated_itemtree.clear()
  
  def reset_filter(self):
    """Resets the filter, creating a new empty `ObjectFilter`."""
    self.filter = pgobjectfilter.ObjectFilter(self._filter_match_type)
  
  def _build_tree(self):
    child_raw_items = self._get_children_from_image(self._image)
    child_items = [_Item(raw_item, [], None, self._name) for raw_item in child_raw_items]
    
    item_tree = child_items
    
    while item_tree:
      item = item_tree.pop(0)
      
      item_parents = list(item.parents)
      
      if self._is_group(item.raw):
        child_raw_items = self._get_children_from_raw_item(item.raw)
      else:
        child_raw_items = None
      
      if child_raw_items is not None:
        folder_item = _Item(
          item.raw, item_parents, item.children, self._name, is_folder=True)
        item_parents.append(folder_item)
        
        self._itemtree[(folder_item.raw.ID, self.FOLDER_KEY)] = folder_item
        self._itemtree_names[(folder_item.orig_name, self.FOLDER_KEY)] = folder_item
      
      self._itemtree[item.raw.ID] = item
      self._itemtree_names[item.orig_name] = item
      
      if child_raw_items is not None:
        child_items = [
          _Item(raw_item, item_parents, None, self._name) for raw_item in child_raw_items]
        
        # We break the convention here and access private attributes from `_Item`.
        item._orig_children = child_items
        item._children = child_items
        
        for child_item in reversed(child_items):
          item_tree.insert(0, child_item)
  
  @abc.abstractmethod
  def _get_children_from_image(self, image):
    """Returns a list of immediate child items from the specified image.
    
    If no child items exist, an empty list is returned.
    """
    pass
  
  def _get_children_from_raw_item(self, raw_item):
    """Returns a list of immediate child items.
    
    If no child items exist, an empty list is returned.
    """
    return raw_item.children
  
  def _is_group(self, raw_item):
    return pdb.gimp_item_is_group(raw_item)


class LayerTree(ItemTree):
  
  def _get_children_from_image(self, image):
    return image.layers
  
  def _get_children_from_raw_item(self, raw_item):
    return raw_item.layers
  
  def _is_group(self, raw_item):
    return isinstance(raw_item, gimp.GroupLayer)


class ChannelTree(ItemTree):
  
  def _get_children_from_image(self, image):
    return image.channels


class VectorTree(ItemTree):
  
  def _get_children_from_image(self, image):
    return image.vectors


@future.utils.python_2_unicode_compatible
class _Item(object):
  """Wrapper for a `gimp.Item` object containing additional attributes.
  
  Note that the attributes will not be up to date if changes were made to the
  original `gimp.Item` object.
  
  Attributes:
  
  * `item` (read-only) - `gimp.Item` object.
  
  * `parents` (read-only) - List of `_Item` parents for this item, sorted from
    the topmost parent to the bottommost (immediate) parent.
  
  * `children` (read-only) - List of `_Item` children for this item.
  
  * `name` - Item name as a string, initially equal to `orig_name`. Modify this
     attribute instead of `gimp.Item.name` to avoid modifying the original item.
  
  * `depth` (read-only) - Integer indicating the depth of the item in the item
    tree. 0 means the item is at the top level. The greater the depth, the lower
    the item is in the item tree.
  
  * `parent` (read-only) - Immediate `_Item` parent of this object.
    If this object has no parent, return `None`.
  
  * `type` (read-only) - Item type - one of the following:
      * `ITEM` - regular item
      * `GROUP` - item group (contains children, but acts as an item)
      * `FOLDER` - contains children
  
  * `path_visible` (read-only) - Visibility of all item's parents and this
    item. If all items are visible, `path_visible` is `True`. If at least one
    of these items is invisible, `path_visible` is `False`.
  
  * `orig_name` (read-only) - Original `gimp.Item.name` as a string.
  
  * `tags` - Set of arbitrary strings attached to the item. Tags can be used for
    a variety of purposes, such as special handling of items with specific tags.
    Tags are stored persistently in the `gimp.Item` object (`item` attribute) as
    parasites. The name of the parasite source is given by the
    `tags_source_name` attribute.
  
  * `tags_source_name` - Name of the persistent source for the `tags` attribute.
    Defaults to `'tags'` if `None`.
  """
  
  _ITEM_TYPES = ITEM, GROUP, FOLDER = (0, 1, 2)
  
  def __init__(
        self, raw_item, parents=None, children=None, tags_source_name=None, is_folder=False):
    if raw_item is None:
      raise TypeError('item cannot be None')
    
    self._raw_item = raw_item
    self._parents = parents if parents is not None else []
    self._children = children
    self._is_folder = is_folder
    
    self.name = pgutils.safe_decode_gimp(raw_item.name)
    
    # These attributes are lazily initialized since children and parents are
    # dynamically modified while constructing the item tree.
    self._type = None
    self._path_visible = None
    
    self._orig_name = self.name
    self._orig_parents = self._parents
    self._orig_children = self._children
    
    self._tags_source_name = tags_source_name if tags_source_name else 'tags'
    self._tags = self._load_tags()
  
  @property
  def raw(self):
    return self._raw_item
  
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
  def type(self):
    if self._type is None:
      if self._is_folder:
        self._type = self.FOLDER
      else:
        if self._children is None:
          self._type = self.ITEM
        else:
          self._type = self.GROUP
    
    return self._type
  
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
  
  def __repr__(self):
    return pgutils.reprify_object(
      self, ' '.join([self.orig_name, str(type(self.raw))]))
  
  def get_file_extension(self):
    """Returns file extension from the `name` attribute, in lowercase.
    
    If `name` has no file extension, an empty string is returned.
    """
    return pgpath.get_file_extension(self.name)
  
  def get_file_extension_from_orig_name(self):
    """Returns file extension from the `orig_name` attribute, in lowercase.
    
    If `orig_name` has no file extension, an empty string is returned.
    """
    return pgpath.get_file_extension(self.orig_name)
  
  def set_file_extension(self, file_extension, keep_extra_trailing_periods=False):
    """Sets file extension in the `name` attribute.
    
    For more information, see `pgpath.get_filename_with_new_file_extension()`.
    """
    self.name = pgpath.get_filename_with_new_file_extension(
      self.name, file_extension, keep_extra_trailing_periods)
  
  def get_base_name(self):
    """Returns the item name without its file extension."""
    file_extension = self.get_file_extension()
    if file_extension:
      return self.name[:-(len(file_extension) + 1)]
    else:
      return self.name
  
  def get_filepath(self, dirpath, include_item_path=True):
    """Returns file path given the specified directory path, item name and names
    of its parents.
    
    If `include_item_path` is `True`, create file path in the following format:
      
      <directory path>/<item path components>/<item name>
    
    If `include_item_path` is `False`, create file path in the following format:
      
      <directory path>/<item name>
    
    If the directory path is not an absolute path or is `None`, prepend the
    current working directory.
    
    Item path components consist of parents' item names, starting with the
    topmost parent.
    """
    if dirpath is None:
      dirpath = ''
    
    path = os.path.abspath(dirpath)
    
    if include_item_path:
      path_components = self.get_path_components()
      if path_components:
        path = os.path.join(path, os.path.join(*path_components))
    
    return os.path.join(path, self.name)
  
  def get_path_components(self):
    """Returns a list of names of all parents of this item as path components.
    """
    return [parent.name for parent in self.parents]
  
  def add_tag(self, tag):
    """Adds the specified tag to the item.
    
    If the tag already exists, do nothing. The tag is saved to the item
    persistently.
    """
    if tag in self._tags:
      return
    
    self._tags.add(tag)
    
    self._save_tags()
  
  def remove_tag(self, tag):
    """Removes the specified tag from the item.
    
    If the tag does not exist, raise `ValueError`.
    """
    if tag not in self._tags:
      raise ValueError('tag "{}" not found in {}'.format(tag, self))
    
    self._tags.remove(tag)
    
    self._save_tags()
  
  def _get_path_visibility(self):
    """Returns `True` if this item and all of its parents are visible, `False`
    otherwise.
    """
    path_visible = True
    if not self._raw_item.visible:
      path_visible = False
    else:
      for parent in self._parents:
        if not parent.raw.visible:
          path_visible = False
          break
    return path_visible
  
  def _save_tags(self):
    """Saves tags persistently to the item."""
    self._raw_item.parasite_detach(self._tags_source_name)
    
    if self._tags:
      self._raw_item.parasite_attach(
        gimp.Parasite(
          self._tags_source_name,
          gimpenums.PARASITE_PERSISTENT | gimpenums.PARASITE_UNDOABLE,
          pickle.dumps(self._tags)))
  
  def _load_tags(self):
    parasite = self._raw_item.parasite_find(self._tags_source_name)
    if parasite:
      try:
        tags = pickle.loads(parasite.data)
      except Exception:
        tags = set()
      
      return tags
    else:
      return set()
