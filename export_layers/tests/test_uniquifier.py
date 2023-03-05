# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import collections
import unittest

import mock

from export_layers import pygimplib as pg

from export_layers.pygimplib.tests import stubs_gimp
from export_layers.pygimplib.tests import utils_itemtree

from export_layers import uniquifier


class TestUniquify(unittest.TestCase):
  
  @mock.patch(
    pg.utils.get_pygimplib_module_path() + '.itemtree.pdb',
    new=stubs_gimp.PdbStub())
  @mock.patch(
    pg.utils.get_pygimplib_module_path() + '.itemtree.gimp.GroupLayer',
    new=stubs_gimp.LayerGroupStub)
  def setUp(self):
    self.uniquifier = uniquifier.ItemUniquifier()
    
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
      Corners::
      top-left-corner::::
      main-background.jpg:: {
        alt-frames
        alt-corners
      }
    """
    
    image = utils_itemtree.parse_layers(items_string)
    self.item_tree = pg.itemtree.LayerTree(image)
  
  @mock.patch(
    pg.utils.get_pygimplib_module_path() + '.itemtree.pdb',
    new=stubs_gimp.PdbStub())
  @mock.patch(
    pg.utils.get_pygimplib_module_path() + '.itemtree.gimp.GroupLayer',
    new=stubs_gimp.LayerGroupStub)
  def test_uniquify(self):
    uniquified_names = collections.OrderedDict([
      (('Corners', 'folder'), ['Corners']),
      ('Corners', ['Corners (1)']),
      ('top-left-corner', ['Corners', 'top-left-corner']),
      ('top-right-corner', ['Corners', 'top-right-corner']),
      (('top-left-corner:', 'folder'), ['Corners', 'top-left-corner (1)']),
      (('top-left-corner::', 'folder'), ['Corners', 'top-left-corner (2)']),
      ('top-left-corner::', ['Corners', 'top-left-corner (3)']),
      ('bottom-right-corner',
       ['Corners', 'top-left-corner (2)', 'bottom-right-corner']),
      ('bottom-right-corner:',
       ['Corners', 'top-left-corner (2)', 'bottom-right-corner (1)']),
      ('bottom-left-corner',
       ['Corners', 'top-left-corner (2)', 'bottom-left-corner']),
      (('Corners:', 'folder'), ['Corners (2)']),
      ('Corners:', ['Corners (3)']),
      ('top-left-corner:::', ['Corners (2)', 'top-left-corner']),
      (('Frames', 'folder'), ['Frames']),
      ('Frames', ['Frames (1)']),
      ('top-frame', ['Frames', 'top-frame']),
      ('main-background.jpg', ['main-background.jpg']),
      ('main-background.jpg:', ['main-background.jpg (1)']),
      ('Corners::', ['Corners (4)']),
      ('top-left-corner::::', ['top-left-corner']),
      (('main-background.jpg::', 'folder'), ['main-background.jpg (2)']),
      ('main-background.jpg::', ['main-background.jpg (3)']),
      ('alt-frames', ['main-background.jpg (2)', 'alt-frames']),
      ('alt-corners', ['main-background.jpg (2)', 'alt-corners']),
    ])
    
    for item in self.item_tree.iter():
      self._preprocess_name(item)
      self.uniquifier.uniquify(item)
    
    self._compare_uniquified_names(self.item_tree, uniquified_names)
  
  @mock.patch(
    pg.utils.get_pygimplib_module_path() + '.itemtree.pdb',
    new=stubs_gimp.PdbStub())
  @mock.patch(
    pg.utils.get_pygimplib_module_path() + '.itemtree.gimp.GroupLayer',
    new=stubs_gimp.LayerGroupStub)
  def test_uniquify_with_custom_position(self):
    def _get_file_extension_start_position(str_):
      position = str_.rfind('.')
      if position == -1:
        position = len(str_)
      return position
    
    names_to_uniquify = collections.OrderedDict([
      ('main-background.jpg', ['main-background.jpg']),
      ('main-background.jpg:', ['main-background (1).jpg']),
      (('main-background.jpg::', 'folder'), ['main-background.jpg (1)']),
      ('main-background.jpg::', ['main-background (2).jpg']),
    ])
    
    for item_name in names_to_uniquify:
      item = self.item_tree[item_name]
      
      self._preprocess_name(item)
      if item.type == pg.itemtree.TYPE_FOLDER:
        self.uniquifier.uniquify(item)
      else:
        self.uniquifier.uniquify(item, position=_get_file_extension_start_position(item.name))
    
    self._compare_uniquified_names(self.item_tree, names_to_uniquify)
  
  @mock.patch(
    pg.utils.get_pygimplib_module_path() + '.itemtree.pdb',
    new=stubs_gimp.PdbStub())
  @mock.patch(
    pg.utils.get_pygimplib_module_path() + '.itemtree.gimp.GroupLayer',
    new=stubs_gimp.LayerGroupStub)
  def test_uniquify_does_not_modify_already_passed_items(self):
    names_to_uniquify = collections.OrderedDict([
      ('main-background.jpg', ['main-background.jpg']),
      ('main-background.jpg:', ['main-background.jpg (1)']),
      (('main-background.jpg::', 'folder'), ['main-background.jpg (2)']),
      ('main-background.jpg::', ['main-background.jpg (3)']),
    ])
    
    for item_name in names_to_uniquify:
      item = self.item_tree[item_name]
      
      self._preprocess_name(item)
      self.uniquifier.uniquify(item)
    
    for item_name in names_to_uniquify:
      item = self.item_tree[item_name]
      self.uniquifier.uniquify(item)
    
    self._compare_uniquified_names(self.item_tree, names_to_uniquify)
  
  @mock.patch(
    pg.utils.get_pygimplib_module_path() + '.itemtree.pdb',
    new=stubs_gimp.PdbStub())
  @mock.patch(
    pg.utils.get_pygimplib_module_path() + '.itemtree.gimp.GroupLayer',
    new=stubs_gimp.LayerGroupStub)
  def test_reset(self):
    names_to_uniquify = collections.OrderedDict([
      ('main-background.jpg', ['main-background.jpg']),
      ('main-background.jpg:', ['main-background.jpg (1)']),
    ])
    
    for item_name in names_to_uniquify:
      item = self.item_tree[item_name]
      
      self._preprocess_name(item)
      self.uniquifier.uniquify(item)
    
    self.uniquifier.reset()
    
    self.item_tree['main-background.jpg:'].name = 'main-background.jpg'
    
    for item_name in names_to_uniquify:
      item = self.item_tree[item_name]
      self.uniquifier.uniquify(item)
    
    self._compare_uniquified_names(self.item_tree, names_to_uniquify)
  
  def _compare_uniquified_names(self, item_tree, uniquified_names):
    for key, item_path in uniquified_names.items():
      expected_path_components, name = item_path[:-1], item_path[-1]
      actual_path_components = [parent.name for parent in item_tree[key].parents]
      
      self.assertEqual(
        actual_path_components,
        expected_path_components,
        'parents: "{}": "{}" != "{}"'.format(
          key, actual_path_components, expected_path_components))
      self.assertEqual(
        item_tree[key].name,
        name,
        'item name: "{}": "{}" != "{}"'.format(key, item_tree[key].name, name))
  
  @staticmethod
  def _preprocess_name(item):
    item.name = item.name.replace(':', '')
