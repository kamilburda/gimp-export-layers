# -*- coding: utf-8 -*-

"""Tests for the `itemtree` module.

Because the public interface to test is identical for all `ItemTree` subclasses,
it is sufficient to test `itemtree` using one of the subclasses. `LayerTree`
was chosen for this purpose.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import collections
import os
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


class FilterRules(object):
  
  @staticmethod
  def is_item(item):
    return item.item_type == item.ITEM
  
  @staticmethod
  def is_item_or_empty_group(item):
    return item.item_type in (item.ITEM, item.EMPTY_GROUP)
  
  @staticmethod
  def is_path_visible(item):
    return item.path_visible
  
  @staticmethod
  def has_matching_file_extension(item, file_extension):
    return item.name.endswith('.' + file_extension)


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
          bottom-right-corner:
          bottom-left-corner
        }
      }
      Corners: {
        top-left-corner:::
      }
      Frames {
        top-frame
      }
      main-background.jpg
      main-background.jpg:
      Overlay {
      }
      Corners::
      top-left-corner::::
      main-background.jpg:: {
        alt-frames
        alt-corners
      }
    """
    
    image = utils_itemtree.parse_layers(items_string)
    self.item_tree = pgitemtree.LayerTree(image)
  
  def test_get_item_tree_element_attributes(self):
    item_tree = collections.OrderedDict([
      ('Corners',
       [[],
        ['top-left-corner', 'top-right-corner',
         'top-left-corner:', 'top-left-corner::']]),
      ('top-left-corner', [['Corners'], None]),
      ('top-right-corner', [['Corners'], None]),
      ('top-left-corner:', [['Corners'], []]),
      ('top-left-corner::',
       [['Corners'],
        ['bottom-right-corner', 'bottom-right-corner:', 'bottom-left-corner']]),
      ('bottom-right-corner', [['Corners', 'top-left-corner::'], None]),
      ('bottom-right-corner:', [['Corners', 'top-left-corner::'], None]),
      ('bottom-left-corner', [['Corners', 'top-left-corner::'], None]),
      ('Corners:', [[], ['top-left-corner:::']]),
      ('top-left-corner:::', [['Corners:'], None]),
      ('Frames', [[], ['top-frame']]),
      ('top-frame', [['Frames'], None]),
      ('main-background.jpg', [[], None]),
      ('main-background.jpg:', [[], None]),
      ('Overlay', [[], []]),
      ('Corners::', [[], None]),
      ('top-left-corner::::', [[], None]),
      ('main-background.jpg::', [[], ['alt-frames', 'alt-corners']]),
      ('alt-frames', [['main-background.jpg::'], None]),
      ('alt-corners', [['main-background.jpg::'], None]),
    ])
    
    for item, orig_name in zip(self.item_tree, item_tree):
      self.assertEqual(item.orig_name, orig_name)
    
    for item, parents_and_children in zip(
          self.item_tree, item_tree.values()):
      parents = parents_and_children[0]
      children = parents_and_children[1]
      
      self.assertListEqual([parent.orig_name for parent in item.parents], parents)
      
      if children is not None:
        self.assertListEqual([child.orig_name for child in item.children], children)
      else:
        self.assertIsNone(item.children)
      
      self.assertEqual(item.parents, list(item.orig_parents))
      self.assertEqual(
        item.children,
        list(item.orig_children) if item.orig_children is not None else None)
  
  def test_get_len(self):
    item_count_total = 20
    item_count_only_items = 13
    
    self.assertEqual(len(self.item_tree), item_count_total)
    
    self.item_tree.is_filtered = True
    self.item_tree.filter.add(FilterRules.is_item)
    
    self.assertEqual(len(self.item_tree), item_count_only_items)
  
  def test_get_filepath(self):
    output_dirpath = os.path.join('D:', os.sep, 'testgimp')
    
    # `item` with parents
    item = self.item_tree['bottom-right-corner']
    
    self.assertEqual(
      item.get_filepath(output_dirpath),
      os.path.join(output_dirpath, 'Corners', 'top-left-corner::', item.name))
    self.assertEqual(
      item.get_filepath(output_dirpath, include_item_path=False),
      os.path.join(output_dirpath, item.name))
    self.assertEqual(
      item.get_filepath('testgimp'),
      os.path.join(
        os.getcwd(), 'testgimp', 'Corners', 'top-left-corner::', item.name))
    self.assertEqual(
      item.get_filepath(None),
      os.path.join(
        os.getcwd(), 'Corners', 'top-left-corner::', item.name))
    
    itemtree_empty_group = self.item_tree['top-left-corner:']
    
    self.assertEqual(
      itemtree_empty_group.get_filepath(output_dirpath),
      os.path.join(output_dirpath, 'Corners', itemtree_empty_group.name))
    self.assertEqual(
      itemtree_empty_group.get_filepath(output_dirpath, include_item_path=False),
      os.path.join(output_dirpath, itemtree_empty_group.name))
    
    itemtree_empty_group_no_parents = self.item_tree['Overlay']
    
    self.assertEqual(
      itemtree_empty_group_no_parents.get_filepath(output_dirpath),
      os.path.join(output_dirpath, itemtree_empty_group_no_parents.name))
    self.assertEqual(
      itemtree_empty_group_no_parents.get_filepath(output_dirpath),
      itemtree_empty_group_no_parents.get_filepath(output_dirpath, include_item_path=False))
  
  #-----------------------------------------------------------------------------
  
  def test_uniquify_without_groups(self):
    uniquified_names = collections.OrderedDict([
      ('top-left-corner', 'top-left-corner'),
      ('top-right-corner', 'top-right-corner'),
      ('top-left-corner:', 'top-left-corner (1)'),
      ('bottom-right-corner', 'bottom-right-corner'),
      ('bottom-right-corner:', 'bottom-right-corner (1)'),
      ('bottom-left-corner', 'bottom-left-corner'),
      ('top-left-corner:::', 'top-left-corner (2)'),
      ('top-frame', 'top-frame'),
      ('main-background.jpg', 'main-background.jpg'),
      ('main-background.jpg:', 'main-background.jpg (1)'),
      ('Corners', 'Corners'),
      ('top-left-corner::::', 'top-left-corner (3)')
    ])
    
    # This is to make uniquification work properly for these tests. The code is
    # not inside `uniquify_names()` as the code that uses this method may need
    # to uniquify non-empty groups in some scenarios (such as when merging
    # non-empty groups into items, which would not match the filter).
    self.item_tree.is_filtered = True
    self.item_tree.filter.add(FilterRules.is_item_or_empty_group)
    
    for item in self.item_tree:
      self.item_tree.validate_name(item)
      self.item_tree.uniquify_name(item, include_item_path=False)
    self._compare_uniquified_without_parents(self.item_tree, uniquified_names)
  
  def _compare_uniquified_without_parents(self, item_tree, uniquified_names):
    for key, name in uniquified_names.items():
      self.assertEqual(
        item_tree[key].name,
        name,
        '"{}": "{}" != "{}"'.format(key, item_tree[key].name, name))
  
  def test_uniquify_with_groups(self):
    uniquified_names = collections.OrderedDict([
      ('Corners', ['Corners']),
      ('top-left-corner', ['Corners', 'top-left-corner']),
      ('top-right-corner', ['Corners', 'top-right-corner']),
      ('top-left-corner:', ['Corners', 'top-left-corner (1)']),
      ('top-left-corner::', ['Corners', 'top-left-corner (2)']),
      ('bottom-right-corner',
       ['Corners', 'top-left-corner (2)', 'bottom-right-corner']),
      ('bottom-right-corner:',
       ['Corners', 'top-left-corner (2)', 'bottom-right-corner (1)']),
      ('bottom-left-corner',
       ['Corners', 'top-left-corner (2)', 'bottom-left-corner']),
      ('Corners:', ['Corners (1)']),
      ('top-left-corner:::', ['Corners (1)', 'top-left-corner']),
      ('Frames', ['Frames']),
      ('top-frame', ['Frames', 'top-frame']),
      ('main-background.jpg', ['main-background.jpg']),
      ('main-background.jpg:', ['main-background.jpg (1)']),
      ('Corners::', ['Corners (2)']),
      ('top-left-corner::::', ['top-left-corner']),
      ('main-background.jpg::', ['main-background.jpg (2)']),
      ('alt-frames', ['main-background.jpg (2)', 'alt-frames']),
      ('alt-corners', ['main-background.jpg (2)', 'alt-corners']),
    ])
    
    self.item_tree.is_filtered = True
    self.item_tree.filter.add(FilterRules.is_item_or_empty_group)
    
    for item in self.item_tree:
      self.item_tree.validate_name(item)
      self.item_tree.uniquify_name(item, include_item_path=True)
    self._compare_uniquified_with_parents(self.item_tree, uniquified_names)
  
  def test_uniquify_with_regards_to_file_extension(self):
    def _get_file_extension_start_position(str_):
      position = str_.rfind('.')
      if position == -1:
        position = len(str_)
      return position
    
    uniquified_names = collections.OrderedDict([
      ('main-background.jpg', ['main-background.jpg']),
      ('main-background.jpg:', ['main-background (1).jpg']),
      ('main-background.jpg::', ['main-background.jpg (1)'])
    ])
    
    self.item_tree.is_filtered = True
    self.item_tree.filter.add(FilterRules.is_item_or_empty_group)
    
    for item in self.item_tree:
      self.item_tree.validate_name(item)
      self.item_tree.uniquify_name(
        item,
        include_item_path=True,
        uniquifier_position=_get_file_extension_start_position(item.name))
    self._compare_uniquified_with_parents(self.item_tree, uniquified_names)
  
  def _compare_uniquified_with_parents(self, item_tree, uniquified_names):
    for key, item_path in uniquified_names.items():
      path_components, name = item_path[:-1], item_path[-1]
      self.assertEqual(
        item_tree[key].get_path_components(),
        path_components,
        'parents: "{}": "{}" != "{}"'.format(
          key, item_tree[key].get_path_components(), path_components))
      self.assertEqual(
        item_tree[key].name,
        name,
        'item name: "{}": "{}" != "{}"'.format(key, item_tree[key].name, name))
  
  def test_reset_name(self):
    self.item_tree['Corners'].name = 'Corners.png'
    
    self.item_tree.validate_name(self.item_tree['Corners'])
    self.item_tree.uniquify_name(self.item_tree['Corners'])
    
    self.item_tree.validate_name(self.item_tree['Corners::'])
    self.item_tree.uniquify_name(self.item_tree['Corners::'])
    
    self.item_tree.reset_name(self.item_tree['Corners'])
    
    self.item_tree.validate_name(self.item_tree['Corners'])
    self.item_tree.uniquify_name(self.item_tree['Corners'])
    
    self.assertEqual(self.item_tree['Corners::'].name, 'Corners')
    self.assertEqual(self.item_tree['Corners'].name, 'Corners (1)')
  
  def test_reset_all_names(self):
    self.item_tree['Corners'].name = 'Corners.png'
    self.item_tree['Corners:'].name = 'Corners.png:'
    
    self.item_tree.validate_name(self.item_tree['Corners'])
    self.item_tree.uniquify_name(self.item_tree['Corners'])
    self.item_tree.validate_name(self.item_tree['Corners:'])
    self.item_tree.uniquify_name(self.item_tree['Corners:'])
    
    self.item_tree.reset_all_names()
    
    self.assertEqual(self.item_tree['Corners'].name, 'Corners')
    self.assertEqual(self.item_tree['Corners:'].name, 'Corners:')


@mock.patch(
  pgutils.get_pygimplib_module_path() + '.itemtree.pdb', new=stubs_gimp.PdbStub())
class TestLayerTreeElement(unittest.TestCase):
  
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
  
  def test_get_base_name(self):
    self.item.name = 'main-background'
    self.assertEqual(self.item.get_base_name(), 'main-background')
    self.item.name = 'main-background.'
    self.assertEqual(self.item.get_base_name(), 'main-background.')
    self.item.name = 'main-background.jpg'
    self.assertEqual(self.item.get_base_name(), 'main-background')
    self.item.name = 'main-background..jpg'
    self.assertEqual(self.item.get_base_name(), 'main-background.')
    self.item.name = '..jpg'
    self.assertEqual(self.item.get_base_name(), '.')
    self.item.name = '.jpg'
    self.assertEqual(self.item.get_base_name(), '')
    self.item.name = '.'
    self.assertEqual(self.item.get_base_name(), '.')
  
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
