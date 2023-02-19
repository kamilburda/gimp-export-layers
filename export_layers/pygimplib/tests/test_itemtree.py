# -*- coding: utf-8 -*-

"""Tests for the `itemtree` module.

Because the public interface to test is identical for all `ItemTree` subclasses,
it is sufficient to test `itemtree` using one of the subclasses. `LayerTree`
was chosen for this purpose.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import unittest

try:
  import cPickle as pickle
except ImportError:
  import pickle

import mock

from . import stubs_gimp
from . import utils_itemtree
from .. import itemtree as pgitemtree
from .. import utils as pgutils


@mock.patch(
  pgutils.get_pygimplib_module_path() + '.itemtree.pdb',
  new=stubs_gimp.PdbStub())
@mock.patch(
  pgutils.get_pygimplib_module_path() + '.itemtree.gimp.GroupLayer',
  new=stubs_gimp.LayerGroupStub)
class TestLayerTree(unittest.TestCase):

  @mock.patch(
    pgutils.get_pygimplib_module_path() + '.itemtree.pdb',
    new=stubs_gimp.PdbStub())
  @mock.patch(
    pgutils.get_pygimplib_module_path() + '.itemtree.gimp.GroupLayer',
    new=stubs_gimp.LayerGroupStub)
  def setUp(self):
    items_string = """
      Corners {
        top-left-corner
        top-right-corner
        top-left-corner: {
        }
        top-left-corner:: {
          bottom-right-corner
          bottom-left-corner
        }
      }
      Frames {
        top-frame
      }
      main-background.jpg
      Overlay {
      }
    """
    
    image = utils_itemtree.parse_layers(items_string)
    self.item_tree = pgitemtree.LayerTree(image)
    
    self.ITEM = pgitemtree._Item.ITEM
    self.GROUP = pgitemtree._Item.GROUP
    self.FOLDER = pgitemtree._Item.FOLDER
    
    self.item_properties = [
      ('Corners',
       self.FOLDER,
       [],
       ['top-left-corner', 'top-right-corner', 'top-left-corner:', 'top-left-corner::']),
      ('Corners',
       self.GROUP,
       [],
       ['top-left-corner', 'top-right-corner', 'top-left-corner:', 'top-left-corner::']),
      ('top-left-corner', self.ITEM, ['Corners'], None),
      ('top-right-corner', self.ITEM, ['Corners'], None),
      ('top-left-corner:', self.FOLDER, ['Corners'], []),
      ('top-left-corner:', self.GROUP, ['Corners'], []),
      ('top-left-corner::',
       self.FOLDER, ['Corners'], ['bottom-right-corner', 'bottom-left-corner']),
      ('top-left-corner::',
       self.GROUP, ['Corners'], ['bottom-right-corner', 'bottom-left-corner']),
      ('bottom-right-corner', self.ITEM, ['Corners', 'top-left-corner::'], None),
      ('bottom-left-corner', self.ITEM, ['Corners', 'top-left-corner::'], None),
      ('Frames', self.FOLDER, [], ['top-frame']),
      ('Frames', self.GROUP, [], ['top-frame']),
      ('top-frame', self.ITEM, ['Frames'], None),
      ('main-background.jpg', self.ITEM, [], None),
      ('Overlay', self.FOLDER, [], []),
      ('Overlay', self.GROUP, [], []),
    ]
  
  def test_item_attributes(self):
    for item, properties in zip(
          self.item_tree.iter(with_folders=True, with_empty_groups=True), self.item_properties):
      self.assertEqual(item.orig_name, properties[0])
      self.assertEqual(item.type, properties[1])
      
      parents = properties[2]
      children = properties[3]
      
      self.assertListEqual([parent.orig_name for parent in item.parents], parents)
      if children is not None:
        self.assertListEqual([child.orig_name for child in item.children], children)
      else:
        self.assertIsNone(item.children)
      
      self.assertEqual(item.parents, list(item.orig_parents))
      self.assertEqual(
        item.children,
        list(item.orig_children) if item.orig_children is not None else None)
  
  def test_iter_with_different_item_types_excluded(self):
    limited_item_properties = [properties[:2] for properties in self.item_properties]
    
    item_properties_without_empty_groups = list(limited_item_properties)
    del item_properties_without_empty_groups[
      item_properties_without_empty_groups.index(
        ('Overlay', pgitemtree._Item.FOLDER)) + 1]
    del item_properties_without_empty_groups[
      item_properties_without_empty_groups.index(
        ('top-left-corner:', pgitemtree._Item.FOLDER)) + 1]
    
    item_properties_without_folders_and_empty_groups = [
      (name, type_) for name, type_ in limited_item_properties if type_ != self.FOLDER]
    del item_properties_without_folders_and_empty_groups[
      item_properties_without_folders_and_empty_groups.index(
        ('Overlay', pgitemtree._Item.GROUP))]
    del item_properties_without_folders_and_empty_groups[
      item_properties_without_folders_and_empty_groups.index(
        ('top-left-corner:', pgitemtree._Item.GROUP))]
    
    for item, (item_name, item_type) in zip(
          self.item_tree.iter(with_empty_groups=True), limited_item_properties):
      self.assertEqual(item.name, item_name)
      self.assertEqual(item.type, item_type)
    
    for item, (item_name, item_type) in zip(
          self.item_tree.iter(), item_properties_without_empty_groups):
      self.assertEqual(item.name, item_name)
      self.assertEqual(item.type, item_type)
    
    for item, (item_name, item_type) in zip(
          self.item_tree.iter(with_folders=False),
          item_properties_without_folders_and_empty_groups):
      self.assertEqual(item.name, item_name)
      self.assertEqual(item.type, item_type)
    
    for item, (item_name, item_type) in zip(
          self.item_tree,
          item_properties_without_folders_and_empty_groups):
      self.assertEqual(item.name, item_name)
      self.assertEqual(item.type, item_type)
  
  def test_len(self):
    self.assertEqual(len(list(self.item_tree.iter())), 14)
    self.assertEqual(len(list(self.item_tree.iter(with_empty_groups=True))), 16)
    
    self.assertEqual(len(self.item_tree), 9)
    
    self.item_tree.is_filtered = True
    self.item_tree.filter.add(lambda item: item.type == item.ITEM)
    
    self.assertEqual(len(self.item_tree), 6)


@mock.patch(
  pgutils.get_pygimplib_module_path() + '.itemtree.pdb', new=stubs_gimp.PdbStub())
class TestItem(unittest.TestCase):
  
  @mock.patch(
    pgutils.get_pygimplib_module_path() + '.itemtree.pdb', new=stubs_gimp.PdbStub())
  def setUp(self):
    self.item = pgitemtree._Item(
      stubs_gimp.LayerStub('main-background.jpg'))
  
  def test_str(self):
    self.assertEqual(str(self.item), '<_Item "main-background.jpg">')
    
    self.item.name = 'main-background'
    
    self.assertEqual(str(self.item), '<_Item "main-background.jpg">')
  
  def test_repr(self):
    self.assertEqual(
      repr(self.item),
      '<pygimplib.itemtree._Item "main-background.jpg {}" at {}>'.format(
        type(self.item.raw),
        hex(id(self.item)).rstrip('L'),
      ),
    )
  
  @mock.patch(
    pgutils.get_pygimplib_module_path() + '.itemtree.gimp',
    new=stubs_gimp.GimpModuleStub())
  def test_add_tag(self):
    self.assertEqual(self.item.tags, set())
    
    self.item.add_tag('background')
    self.assertIn('background', self.item.tags)
    
    self.item.add_tag('foreground')
    self.assertIn('background', self.item.tags)
    self.assertIn('foreground', self.item.tags)
  
  @mock.patch(
    pgutils.get_pygimplib_module_path() + '.itemtree.gimp',
    new=stubs_gimp.GimpModuleStub())
  def test_remove_tag(self):
    self.assertEqual(self.item.tags, set())
    
    with self.assertRaises(ValueError):
      self.item.remove_tag('background')
    
    self.item.add_tag('background')
    self.item.remove_tag('background')
    
    self.assertNotIn('background', self.item.tags)
    self.assertFalse(self.item.tags)
    self.assertFalse(self.item.raw.parasite_list())
  
  @mock.patch(
    pgutils.get_pygimplib_module_path() + '.itemtree.gimp',
    new=stubs_gimp.GimpModuleStub())
  def test_initial_tags(self):
    item_tags_source_name = 'test'
    
    layer = stubs_gimp.LayerStub('layer')
    layer.parasite_attach(
      stubs_gimp.ParasiteStub(item_tags_source_name, 0, pickle.dumps(set(['background']))))
    
    item = pgitemtree._Item(layer, tags_source_name=item_tags_source_name)
    self.assertIn('background', item.tags)
  
  @mock.patch(
    pgutils.get_pygimplib_module_path() + '.itemtree.gimp',
    new=stubs_gimp.GimpModuleStub())
  def test_initial_tags_with_invalid_data(self):
    item_tags_source_name = 'test'
    
    layer = stubs_gimp.LayerStub('layer')
    layer.parasite_attach(
      stubs_gimp.ParasiteStub(item_tags_source_name, 0, 'invalid_data'))
    
    item = pgitemtree._Item(layer, tags_source_name=item_tags_source_name)
    self.assertFalse(item.tags)
