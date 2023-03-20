# -*- coding: utf-8 -*-

"""Making item names in `pygimplib.itemtree.ItemTree` unique.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

from export_layers import pygimplib as pg


class ItemUniquifier(object):
  """Class renaming `pygimplib.ItemTree.Item` instances to be unique under the
  same parent.
  """
  
  def __init__(self, generator=None):
    self.generator = generator
    
    # key: `Item` instance (parent) or None (item tree root)
    # value: set of `Item` instances
    self._uniquified_items = {}
    
    # key: `Item` instance (parent) or None (item tree root)
    # value: set of `Item.name` strings
    self._uniquified_item_names = {}
  
  def uniquify(self, item, position=None):
    """Renames the `Item` instance by making it unique among all other `Item`
    instances under the same parent `Item`.
    
    To achieve uniquification, a substring in the form of `' (<number>)'` is
    inserted at the end of the item names.
    
    Calling the method with the same `Item` instance will have no effect as
    that instance will be marked as visited. Call `reset()` to clear cache of
    items that were passed to this function.
    
    Parameters:
    
    * `item` - `Item` instance whose `name` attribute will be uniquified.
    
    * `position` - Position (index) where a unique substring is inserted into
      the item's name. If `None`, insert the substring at the end of the name
      (i.e. append it).
    """
    parent = item.parent
    
    if parent not in self._uniquified_items:
      self._uniquified_items[parent] = set()
      self._uniquified_item_names[parent] = set()
    
    already_visited = item in self._uniquified_items[parent]
    if not already_visited:
      self._uniquified_items[parent].add(item)
      
      has_same_name = item.name in self._uniquified_item_names[parent]
      if has_same_name:
        item.name = pg.path.uniquify_string(
          item.name, self._uniquified_item_names[parent], position, generator=self.generator)
      
      self._uniquified_item_names[parent].add(item.name)
  
  def reset(self):
    """Clears cache of items passed to `uniquify()`."""
    self._uniquified_items = {}
    self._uniquified_item_names = {}
