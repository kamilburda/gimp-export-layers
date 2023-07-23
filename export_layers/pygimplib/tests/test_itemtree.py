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
    
    self.ITEM = pgitemtree.TYPE_ITEM
    self.GROUP = pgitemtree.TYPE_GROUP
    self.FOLDER = pgitemtree.TYPE_FOLDER
    
    self.FOLDER_KEY = pgitemtree.FOLDER_KEY
    
    self.item_properties = [
      ('Corners',
       self.FOLDER,
       [],
       [('top-left-corner', self.ITEM),
        ('top-right-corner', self.ITEM),
        ('top-left-corner:', self.FOLDER),
        ('top-left-corner:', self.GROUP),
        ('top-left-corner::', self.FOLDER),
        ('top-left-corner::', self.GROUP)]),
      ('top-left-corner', self.ITEM, [('Corners', self.FOLDER)], []),
      ('top-right-corner', self.ITEM, [('Corners', self.FOLDER)], []),
      ('top-left-corner:', self.FOLDER, [('Corners', self.FOLDER)], []),
      ('top-left-corner:', self.GROUP, [('Corners', self.FOLDER)], []),
      ('top-left-corner::',
       self.FOLDER,
       [('Corners', self.FOLDER)],
       [('bottom-right-corner', self.ITEM), ('bottom-left-corner', self.ITEM)]),
      ('bottom-right-corner',
       self.ITEM,
       [('Corners', self.FOLDER), ('top-left-corner::', self.FOLDER)],
       []),
      ('bottom-left-corner',
       self.ITEM,
       [('Corners', self.FOLDER), ('top-left-corner::', self.FOLDER)],
       []),
      ('top-left-corner::', self.GROUP, [('Corners', self.FOLDER)], []),
      ('Corners', self.GROUP, [], []),
      ('Frames', self.FOLDER, [], [('top-frame', self.ITEM)]),
      ('top-frame', self.ITEM, [('Frames', self.FOLDER)], []),
      ('Frames', self.GROUP, [], []),
      ('main-background.jpg', self.ITEM, [], []),
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
      
      for (expected_parent_name, expected_parent_type), parent in zip(parents, item.parents):
        self.assertEqual(parent.orig_name, expected_parent_name)
        self.assertEqual(parent.type, expected_parent_type)
      
      for (expected_child_name, expected_child_type), child in zip(children, item.children):
        self.assertEqual(child.orig_name, expected_child_name)
        self.assertEqual(child.type, expected_child_type)
      
      self.assertEqual(item.parents, list(item.orig_parents))
      self.assertEqual(item.children, list(item.orig_children))
  
  def test_iter_with_different_item_types_excluded(self):
    limited_item_properties = [properties[:2] for properties in self.item_properties]
    
    item_properties_without_empty_groups = list(limited_item_properties)
    del item_properties_without_empty_groups[
      item_properties_without_empty_groups.index(
        ('Overlay', self.FOLDER)) + 1]
    del item_properties_without_empty_groups[
      item_properties_without_empty_groups.index(
        ('top-left-corner:', self.FOLDER)) + 1]
    
    item_properties_without_folders_and_empty_groups = [
      (name, type_) for name, type_ in limited_item_properties if type_ != self.FOLDER]
    del item_properties_without_folders_and_empty_groups[
      item_properties_without_folders_and_empty_groups.index(
        ('Overlay', self.GROUP))]
    del item_properties_without_folders_and_empty_groups[
      item_properties_without_folders_and_empty_groups.index(
        ('top-left-corner:', self.GROUP))]
    
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
    
    self.item_tree.filter.add(lambda item: item.type == self.ITEM)
    
    self.assertEqual(len(self.item_tree), 6)
  
  def test_prev(self):
    self.assertEqual(
      self.item_tree.prev(self.item_tree['top-frame']),
      self.item_tree[('Frames', self.FOLDER_KEY)])
    self.assertEqual(
      self.item_tree.prev(self.item_tree['top-right-corner']),
      self.item_tree['top-left-corner'])
    
    self.assertEqual(
      self.item_tree.prev(self.item_tree['top-frame']),
      self.item_tree[('Frames', self.FOLDER_KEY)])
    self.assertEqual(
      self.item_tree.prev(self.item_tree['top-frame'], with_folders=False),
      self.item_tree['Corners'])
    
    self.assertEqual(
      self.item_tree.prev(self.item_tree[('top-left-corner::', self.FOLDER_KEY)]),
      self.item_tree[('top-left-corner:', self.FOLDER_KEY)])
    self.assertEqual(
      self.item_tree.prev(
        self.item_tree[('top-left-corner::', self.FOLDER_KEY)], with_empty_groups=True),
      self.item_tree['top-left-corner:'])
    
    self.assertEqual(
      self.item_tree.prev(self.item_tree[('Corners', self.FOLDER_KEY)]),
      None)
    
    self.item_tree.filter.add(lambda item: item.type != self.ITEM)
    self.assertEqual(
      self.item_tree.prev(self.item_tree['top-left-corner::']),
      self.item_tree[('top-left-corner::', self.FOLDER_KEY)])
    self.assertEqual(
      self.item_tree.prev(self.item_tree['top-left-corner::'], filtered=False),
      self.item_tree['bottom-left-corner'])
  
  def test_next(self):
    self.assertEqual(
      self.item_tree.next(self.item_tree[('Frames', self.FOLDER_KEY)]),
      self.item_tree['top-frame'])
    self.assertEqual(
      self.item_tree.next(self.item_tree['top-left-corner']),
      self.item_tree['top-right-corner'])
    
    self.assertEqual(
      self.item_tree.next(self.item_tree['Corners']),
      self.item_tree[('Frames', self.FOLDER_KEY)])
    self.assertEqual(
      self.item_tree.next(self.item_tree['Corners'], with_folders=False),
      self.item_tree['top-frame'])
    
    self.assertEqual(
      self.item_tree.next(self.item_tree[('Overlay', self.FOLDER_KEY)]),
      None)
    self.assertEqual(
      self.item_tree.next(
        self.item_tree[('Overlay', self.FOLDER_KEY)], with_empty_groups=True),
      self.item_tree['Overlay'])
    
    self.assertEqual(
      self.item_tree.next(self.item_tree['Overlay']),
      None)
    
    self.item_tree.filter.add(lambda item: item.type != self.ITEM)
    self.assertEqual(
      self.item_tree.next(self.item_tree[('Corners', self.FOLDER_KEY)]),
      self.item_tree[('top-left-corner:', self.FOLDER_KEY)])
    self.assertEqual(
      self.item_tree.next(self.item_tree[('Corners', self.FOLDER_KEY)], filtered=False),
      self.item_tree['top-left-corner'])


@mock.patch(
  pgutils.get_pygimplib_module_path() + '.itemtree.pdb', new=stubs_gimp.PdbStub())
class TestItem(unittest.TestCase):
  
  @mock.patch(
    pgutils.get_pygimplib_module_path() + '.itemtree.pdb', new=stubs_gimp.PdbStub())
  def setUp(self):
    self.ITEM = pgitemtree.TYPE_ITEM
    self.GROUP = pgitemtree.TYPE_GROUP
    self.FOLDER = pgitemtree.TYPE_FOLDER
    
    self.item = pgitemtree.Item(
      stubs_gimp.LayerStub('main-background.jpg'), self.ITEM)
  
  def test_str(self):
    self.assertEqual(str(self.item), '<Item "main-background.jpg">')
    
    self.item.name = 'main-background'
    
    self.assertEqual(str(self.item), '<Item "main-background.jpg">')
  
  def test_repr(self):
    self.assertEqual(
      repr(self.item),
      '<{}.itemtree.Item "main-background.jpg {}" at {}>'.format(
        pgutils.get_pygimplib_module_path(),
        type(self.item.raw),
        hex(id(self.item)).rstrip('L'),
      ),
    )
  
  def test_reset_without_tags(self):
    self.item.name = 'main'
    self.item.parents = ['one', 'two']
    self.item.children = ['three', 'four']
    self.item.tags.add('five')
    
    self.item.reset()
    
    self.assertEqual(self.item.name, 'main-background.jpg')
    self.assertEqual(self.item.parents, [])
    self.assertEqual(self.item.children, [])
    self.assertEqual(self.item.tags, set(['five']))
  
  def test_reset_with_tags(self):
    self.item.name = 'main'
    self.item.parents = ['one', 'two']
    self.item.children = ['three', 'four']
    
    self.item.reset(tags=True)
    
    self.assertEqual(self.item.name, 'main-background.jpg')
    self.assertEqual(self.item.parents, [])
    self.assertEqual(self.item.children, [])
    self.assertEqual(self.item.tags, set([]))
  
  def test_push_and_pop_state(self):
    self.item.name = 'main'
    self.item.parents = ['one', 'two']
    self.item.children = ['three', 'four']
    self.item.tags.add('five')
    
    self.item.push_state()
    self.item.reset(tags=True)
    self.item.pop_state()
    
    self.assertEqual(self.item.name, 'main')
    self.assertEqual(self.item.parents, ['one', 'two'])
    self.assertEqual(self.item.children, ['three', 'four'])
    self.assertEqual(self.item.tags, set(['five']))
  
  def test_pop_state_with_no_saved_state(self):
    self.item.name = 'main'
    self.item.parents = ['one', 'two']
    self.item.children = ['three', 'four']
    self.item.tags.add('five')
    
    self.item.pop_state()
    
    self.assertEqual(self.item.name, 'main')
    self.assertEqual(self.item.parents, ['one', 'two'])
    self.assertEqual(self.item.children, ['three', 'four'])
    self.assertEqual(self.item.tags, set(['five']))
  
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
    
    item = pgitemtree.Item(layer, self.ITEM, tags_source_name=item_tags_source_name)
    self.assertIn('background', item.tags)
  
  @mock.patch(
    pgutils.get_pygimplib_module_path() + '.itemtree.gimp',
    new=stubs_gimp.GimpModuleStub())
  def test_initial_tags_with_invalid_data(self):
    item_tags_source_name = 'test'
    
    layer = stubs_gimp.LayerStub('layer')
    layer.parasite_attach(
      stubs_gimp.ParasiteStub(item_tags_source_name, 0, 'invalid_data'))
    
    item = pgitemtree.Item(layer, self.ITEM, tags_source_name=item_tags_source_name)
    self.assertFalse(item.tags)
  
  @mock.patch(
    pgutils.get_pygimplib_module_path() + '.itemtree.gimp',
    new=stubs_gimp.GimpModuleStub())
  def test_initial_tags_for_item_as_folder(self):
    item_tags_source_name = 'test'
    folder_tags_source_name = item_tags_source_name + '_' + pgitemtree.FOLDER_KEY
    
    layer = stubs_gimp.LayerStub('layer')
    layer.parasite_attach(
      stubs_gimp.ParasiteStub(folder_tags_source_name, 0, pickle.dumps(set(['background']))))
    
    item = pgitemtree.Item(layer, self.FOLDER, tags_source_name=item_tags_source_name)
    self.assertEqual(item.tags_source_name, folder_tags_source_name)
    self.assertIn('background', item.tags)
  
  @mock.patch(
    pgutils.get_pygimplib_module_path() + '.itemtree.gimp',
    new=stubs_gimp.GimpModuleStub())
  def test_initial_tags_for_item_as_folder_unrecognized_source_name(self):
    item_tags_source_name = 'test'
    folder_tags_source_name = item_tags_source_name + '_' + pgitemtree.FOLDER_KEY
    
    layer = stubs_gimp.LayerStub('layer')
    layer.parasite_attach(
      stubs_gimp.ParasiteStub(item_tags_source_name, 0, pickle.dumps(set(['background']))))
    
    item = pgitemtree.Item(layer, self.FOLDER, tags_source_name=item_tags_source_name)
    self.assertEqual(item.tags_source_name, folder_tags_source_name)
    self.assertNotIn('background', item.tags)
