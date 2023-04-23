# -*- coding: utf-8 -*-

"""Managing items of a GIMP image (e.g. layers) in a tree-like structure."""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *
import future.utils

import abc
import collections

try:
  import cPickle as pickle
except ImportError:
  import pickle

import gimp
from gimp import pdb
import gimpenums

from . import objectfilter as pgobjectfilter
from . import utils as pgutils


TYPE_ITEM, TYPE_GROUP, TYPE_FOLDER = (0, 1, 2)

FOLDER_KEY = 'folder'
"""Key used to access items as folders in `ItemTree` via `__getitem__()`.
See `ItemTree.__getitem__()` for more information.
"""


@future.utils.python_2_unicode_compatible
class ItemTree(future.utils.with_metaclass(abc.ABCMeta, object)):
  """Interface to store `gimp.Item` objects in a tree-like structure.
  
  Use one of the subclasses for items of a certain type:
  
    * `LayerTree` for layers,
    
    * `ChannelTree` for channels,
    
    * `VectorTree` for vectors (paths).
  
  Each item in the tree is an `Item` instance. Each item contains `gimp.Item`
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
    `Item.tags` for more information.
  
  * `is_filtered` - If `True`, ignore items that do not match the filter
    (`ObjectFilter`) in this object when iterating.
  
  * `filter` - `ObjectFilter` instance that allows filtering items based on
    rules.
  """
  
  def __init__(
        self,
        image,
        name=None,
        is_filtered=True,
        filter_match_type=pgobjectfilter.ObjectFilter.MATCH_ALL):
    self._image = image
    self._name = name
    self.is_filtered = is_filtered
    self._filter_match_type = filter_match_type
    
    # Filters applied to all items in `self._itemtree`
    self.filter = pgobjectfilter.ObjectFilter(self._filter_match_type)
    
    # Contains all items in the item tree (including item groups).
    # key: `Item.raw.ID` or (`Item.raw.ID`, `FOLDER_KEY`) in case of folders
    # value: `Item` instance
    self._itemtree = collections.OrderedDict()
    
    # key:
    #  `Item.orig_name` (derived from `Item.raw.name`)
    #   or (`Item.raw.ID`, `FOLDER_KEY`) in case of folders
    # value: `Item` instance
    self._itemtree_names = {}
    
    self._build_tree()
  
  @property
  def image(self):
    return self._image
  
  @property
  def name(self):
    return self._name
  
  def __getitem__(self, id_or_name):
    """Returns an `Item` object by its ID or original name.
    
    An item's ID is the `Item.raw.ID` attribute. An item's original name is the
    `Item.orig_name` attribute.
    
    To access an item group as a folder, pass a tuple `(ID or name, 'folder')`.
    For example:
        
        item_tree['Frames', 'folder']
    """
    try:
      return self._itemtree[id_or_name]
    except KeyError:
      return self._itemtree_names[id_or_name]
  
  def __contains__(self, id_or_name):
    """Returns `True` if an `Item` object is in the item tree, regardless of
    filters. Return `False` otherwise. The `Item` object is specified by its
    `Item.raw.ID` attribute or its `orig_name` attribute.
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
    
    * `item` - The current `Item` object.
    """
    return self.iter(with_folders=False, with_empty_groups=False)
  
  def iter(self, with_folders=True, with_empty_groups=False, filtered=True):
    """Iterates over items, optionally including folders and empty item groups.
    
    Parameters:
    
    * `with_folders` - If `True`, include folders. Topmost folders are yielded
      first. Items are always yielded after all of its parent folders.
    
    * `with_empty_groups` - If `True`, include empty item groups. Empty item
      groups as folders are still yielded if `with_folders` is `True`.
    
    * `filtered` - If `True` and `is_filtered` attribute is also `True`, iterate
      only over items matching the filter. Set this to `False` if you need to
      iterate over all items.
    
    Yields:
    
    * `item` - The current `Item` object.
    """
    for item in self._itemtree.values():
      should_yield_item = True
      
      if not with_folders and item.type == TYPE_FOLDER:
        should_yield_item = False
      
      if (not with_empty_groups
          and (item.type == TYPE_GROUP and not pdb.gimp_item_get_children(item.raw)[1])):
        should_yield_item = False
      
      if should_yield_item:
        if (filtered and self.is_filtered) and not self.filter.is_match(item):
          should_yield_item = False
      
      if should_yield_item:
        yield item
  
  def iter_all(self):
    """Iterates over all items.
    
    This is equivalent to `iter(with_folders=True, with_empty_groups=True,
    filtered=False)`.
    
    Yields:
    
    * `item` - The current `Item` object.
    """
    for item in self._itemtree.values():
      yield item
  
  def prev(self, item, with_folders=True, with_empty_groups=False, filtered=True):
    """Returns the previous item in the tree.
    
    Depending on the values of parameters, some items may be skipped. For the
    description of the parameters, see `iter()`.
    """
    return self._prev_next(item, with_folders, with_empty_groups, filtered, 'prev')
  
  def next(self, item, with_folders=True, with_empty_groups=False, filtered=True):
    """Returns the next item in the tree.
    
    Depending on the values of parameters, some items may be skipped. For the
    description of the parameters, see `iter()`.
    """
    return self._prev_next(item, with_folders, with_empty_groups, filtered, 'next')
  
  def _prev_next(self, item, with_folders, with_empty_groups, filtered, adjacent_attr_name):
    adjacent_item = item
    
    while True:
      adjacent_item = getattr(adjacent_item, adjacent_attr_name)
      
      if adjacent_item is None:
        break
      
      if with_folders:
        if adjacent_item.type == TYPE_FOLDER:
          break
      else:
        if adjacent_item.type == TYPE_FOLDER:
          continue
      
      if with_empty_groups:
        if (adjacent_item.type == TYPE_GROUP
            and not pdb.gimp_item_get_children(adjacent_item.raw)[1]):
          break
      else:
        if (adjacent_item.type == TYPE_GROUP
            and not pdb.gimp_item_get_children(adjacent_item.raw)[1]):
          continue
      
      if filtered and self.is_filtered:
        if self.filter.is_match(adjacent_item):
          break
      else:
        break
    
    return adjacent_item
  
  def reset_filter(self):
    """Resets the filter, creating a new empty `ObjectFilter`."""
    self.filter = pgobjectfilter.ObjectFilter(self._filter_match_type)
  
  def _build_tree(self):
    child_items = []
    for raw_item in self._get_children_from_image(self._image):
      if self._is_group(raw_item):
        child_items.append(Item(raw_item, TYPE_FOLDER, [], [], None, None, self._name))
        child_items.append(Item(raw_item, TYPE_GROUP, [], [], None, None, self._name))
      else:
        child_items.append(Item(raw_item, TYPE_ITEM, [], [], None, None, self._name))
    
    item_tree = child_items
    item_list = []
    
    while item_tree:
      item = item_tree.pop(0)
      item_list.append(item)
      
      if item.type == TYPE_FOLDER:
        self._itemtree[(item.raw.ID, FOLDER_KEY)] = item
        self._itemtree_names[(item.orig_name, FOLDER_KEY)] = item
        
        parents_for_child = list(item.parents)
        parents_for_child.append(item)
        
        child_items = []
        for raw_item in self._get_children_from_raw_item(item.raw):
          if self._is_group(raw_item):
            child_items.append(
              Item(raw_item, TYPE_FOLDER, parents_for_child, [], None, None, self._name))
            child_items.append(
              Item(raw_item, TYPE_GROUP, parents_for_child, [], None, None, self._name))
          else:
            child_items.append(
              Item(raw_item, TYPE_ITEM, parents_for_child, [], None, None, self._name))
        
        # We break the convention here and access a private attribute from `Item`.
        item._orig_children = child_items
        item.children = child_items
        
        for child_item in reversed(child_items):
          item_tree.insert(0, child_item)
      else:
        self._itemtree[item.raw.ID] = item
        self._itemtree_names[item.orig_name] = item
    
    for i in range(1, len(item_list) - 1):
      # We break the convention here and access private attributes from `Item`.
      item_list[i]._prev_item = item_list[i - 1]
      item_list[i]._next_item = item_list[i + 1]
    
    if len(item_list) > 1:
      item_list[0]._next_item = item_list[1]
      item_list[-1]._prev_item = item_list[-2]
  
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
class Item(object):
  """Wrapper for a `gimp.Item` object containing additional attributes.
  
  Note that the attributes will not be up to date if changes were made to the
  original `gimp.Item` object.
  
  Attributes:
  
  * `raw` (read-only) - Underlying `gimp.Item` object wrapped by this instance.
  
  * `type` (read-only) - Item type - one of the following:
      * `TYPE_ITEM` - regular item
      * `TYPE_GROUP` - item group (item whose raw `gimp.Item` is a group with
        children; this `Item` has no children and acts as a regular item)
      * `TYPE_FOLDER` - item containing children (raw item is a group with
        children)
  
  * `parents` - List of `Item` parents for this item, sorted from the topmost
    parent to the bottommost (immediate) parent.
  
  * `children` - List of `Item` children for this item.
  
  * `depth` (read-only) - Integer indicating the depth of the item in the item
    tree. 0 means the item is at the top level. The greater the depth, the lower
    the item is in the item tree.
  
  * `parent` (read-only) - Immediate `Item` parent of this object.
    If this object has no parent, return `None`.
  
  * `name` - Item name as a string, initially equal to `orig_name`. Modify this
     attribute instead of `gimp.Item.name` to avoid modifying the original item.
  
  * `prev` - Previous `Item` in the `ItemTree`, or `None` if there is no
    previous item.
  
  * `next` - Next `Item` in the `ItemTree`, or `None` if there is no next item.
  
  * `tags` - Set of arbitrary strings attached to the item. Tags can be used for
    a variety of purposes, such as special handling of items with specific tags.
    Tags are stored persistently in the `gimp.Item` object (`item` attribute) as
    parasites. The name of the parasite source is given by the
    `tags_source_name` attribute.
  
  * `orig_name` (read-only) - Original `gimp.Item.name` as a string. This
    attribute may be used to access `Item`s in `ItemTree`.
  
  * `orig_parents` (read-only) - Initial `parents` of this item.
  
  * `orig_children` (read-only) - Initial `children` of this item.
  
  * `orig_tags` (read-only) - Initial `tags` of this item.
  
  * `tags_source_name` - Name of the persistent source for the `tags` attribute.
    Defaults to `'tags'` if `None`. If `type` is `FOLDER`, `'_folder'` is
    appended to `tags_source_name`.
  """
  
  def __init__(
        self, raw_item, item_type, parents=None, children=None, prev_item=None, next_item=None,
        tags_source_name=None):
    if raw_item is None:
      raise TypeError('item cannot be None')
    
    self._raw_item = raw_item
    self._type = item_type
    self._parents = parents if parents is not None else []
    self._children = children if children is not None else []
    self._prev_item = prev_item
    self._next_item = next_item
    
    self.name = pgutils.safe_decode_gimp(raw_item.name)
    
    self._tags_source_name = _get_effective_tags_source_name(
      tags_source_name if tags_source_name else 'tags', self._type)
    
    self._tags = self._load_tags()
    
    self._orig_name = self.name
    self._orig_parents = self._parents
    self._orig_children = self._children
    self._orig_tags = set(self._tags)
    
    self._item_attributes = ['name', '_parents', '_children', '_tags']
    
    self._saved_states = []
  
  @property
  def raw(self):
    return self._raw_item
  
  @property
  def type(self):
    return self._type
  
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
  def prev(self):
    return self._prev_item
  
  @property
  def next(self):
    return self._next_item
  
  @property
  def tags(self):
    return self._tags
  
  @property
  def tags_source_name(self):
    return self._tags_source_name
  
  @property
  def orig_name(self):
    return self._orig_name
  
  @property
  def orig_parents(self):
    return iter(self._orig_parents)
  
  @property
  def orig_children(self):
    return iter(self._orig_children)
  
  @property
  def orig_tags(self):
    return iter(self._orig_tags)
  
  def __str__(self):
    return pgutils.stringify_object(self, self.orig_name)
  
  def __repr__(self):
    return pgutils.reprify_object(
      self, ' '.join([self.orig_name, str(type(self.raw))]))
  
  def push_state(self):
    """Saves the current values of item's attributes that can be modified.
    
    To restore the last saved values, call `pop_state()`.
    """
    self._saved_states.append({
      attr_name: getattr(self, attr_name) for attr_name in self._item_attributes})
  
  def pop_state(self):
    """Sets the values of item's attributes to the values from the last call to
    `push_state()`.
    
    Calling `pop_state()` without any saved state (e.g. when `push_state()` has
    never been called before) does nothing.
    """
    try:
      saved_states = self._saved_states.pop()
    except IndexError:
      return
    
    for attr_name, attr_value in saved_states.items():
      setattr(self, attr_name, attr_value)
  
  def reset(self, tags=False):
    """Resets the item's attributes to the values upon its instantiation.
    
    Is `tags` is `True`, also reset tags.
    """
    self.name = self._orig_name
    self._parents = list(self._orig_parents)
    self._children = list(self._orig_children)
    if tags:
      self._tags = set(self._orig_tags)
  
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
  
  def _save_tags(self):
    """Saves tags persistently to the item."""
    set_tags_for_raw_item(self._raw_item, self._tags, self._tags_source_name)
  
  def _load_tags(self):
    return get_tags_from_raw_item(self._raw_item, self._tags_source_name)


def get_tags_from_raw_item(raw_item, source_name, item_type=None):
  """Obtains a set of tags from a `gimp.Item` instance, i.e. a raw item.
  
  `tags_source_name` is the name of the persistent source (parasite) to obtain
  tags from.
  """
  parasite = raw_item.parasite_find(_get_effective_tags_source_name(source_name, item_type))
  if parasite:
    try:
      tags = pickle.loads(parasite.data)
    except Exception:
      tags = set()
    
    return tags
  else:
    return set()


def set_tags_for_raw_item(raw_item, tags, source_name, item_type=None):
  remove_tags_from_raw_item(raw_item, source_name, item_type)
  
  if tags:
    raw_item.parasite_attach(
      gimp.Parasite(
        _get_effective_tags_source_name(source_name, item_type),
        gimpenums.PARASITE_PERSISTENT | gimpenums.PARASITE_UNDOABLE,
        pickle.dumps(tags)))


def remove_tags_from_raw_item(raw_item, source_name, item_type=None):
  raw_item.parasite_detach(_get_effective_tags_source_name(source_name, item_type))


def _get_effective_tags_source_name(source_name, item_type=None):
  if item_type == TYPE_FOLDER:
    return source_name + '_' + FOLDER_KEY
  else:
    return source_name
