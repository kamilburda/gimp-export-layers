# -*- coding: utf-8 -*-

"""Custom setting classes specific to the plug-in."""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import collections
import types

import gimp

from export_layers import pygimplib as pg

from export_layers import renamer as renamer_


class FilenamePatternEntryPresenter(pg.setting.presenters_gtk.ExtendedEntryPresenter):
  """`pygimplib.setting.Presenter` subclass for
  `pygimplib.gui.FilenamePatternEntry` elements.
  
  Value: Text in the entry.
  """
  
  def _create_gui_element(self, setting):
    return pg.gui.FilenamePatternEntry(renamer_.get_field_descriptions(renamer_.FIELDS))


class FilenamePatternSetting(pg.setting.StringSetting):
  
  _ALLOWED_GUI_TYPES = [
    FilenamePatternEntryPresenter,
    pg.SettingGuiTypes.extended_entry,
    pg.SettingGuiTypes.entry,
  ]
  
  def _assign_value(self, value):
    if not value:
      self._value = self._default_value
    else:
      self._value = value


class ImagesAndGimpItemsSetting(pg.setting.Setting):
  """Class for settings representing a mapping of (GIMP image ID, GIMP item IDs)
  pairs.
  
  The mapping is implemented as `collections.defaultdict(set)`.
  
  A GIMP item ID can be represented as an integer or an (ID, FOLDER_KEY) tuple,
  where `FOLDER_KEY` is a string literal defined in `pygimplib.itemtree`.
  
  When storing this setting to a persistent source, images are stored as file
  paths and items are stored as (item class name, item path) or (item class
  name, item path, FOLDER_KEY) tuples. Item class name and item path are
  described in `pygimplib.pdbutils.get_item_from_image_and_item_path()`.
  
  Default value: `collections.defaultdict(set)`
  """
  
  _ALLOWED_PDB_TYPES = []
  _ALLOWED_GUI_TYPES = []
  _DEFAULT_DEFAULT_VALUE = lambda self: collections.defaultdict(set)
  
  def _raw_to_value(self, raw_value):
    if isinstance(raw_value, dict):
      value = collections.defaultdict(set)
      
      for key, items in raw_value.items():
        if isinstance(key, types.StringTypes):
          image = pg.pdbutils.find_image_by_filepath(key)
        else:
          image = pg.pdbutils.find_image_by_id(key)
        
        if image is None:
          continue
        
        image_id = image.ID
        
        if not isinstance(items, collections.Iterable) or isinstance(items, types.StringTypes):
          raise TypeError('expected a list-like, found {}'.format(items))
        
        processed_items = set()
        
        for item in items:
          if isinstance(item, (list, tuple)):
            if len(item) not in [2, 3]:
              raise ValueError(
                'list-likes representing items must contain exactly 2 or 3 elements'
                ' (has {})'.format(len(item)))
            
            if isinstance(item[0], int):  # (item ID, item type)
              item_object = gimp.Item.from_id(item[0])
              if item_object is not None:
                processed_items.add(tuple(item))
            else:
              if len(item) == 3:
                item_type = item[2]
                item_class_name_and_path = item[:2]
              else:
                item_type = None
                item_class_name_and_path = item
              
              item_object = pg.pdbutils.get_item_from_image_and_item_path(
                image, *item_class_name_and_path)
              
              if item_object is not None:
                if item_type is None:
                  processed_items.add(item_object.ID)
                else:
                  processed_items.add((item_object.ID, item_type))
          else:
            item_object = gimp.Item.from_id(item)
            if item_object is not None:
              processed_items.add(item)
        
        value[image_id] = processed_items
    else:
      value = raw_value
    
    return value
  
  def _value_to_raw(self, value, source_type):
    raw_value = {}
    
    if source_type == 'session':
      for image_id, item_ids in value.items():
        raw_value[image_id] = list(
          item_id if isinstance(item_id, int) else list(item_id) for item_id in item_ids)
    else:
      for image_id, item_ids in value.items():
        image = pg.pdbutils.find_image_by_id(image_id)
        
        if image is None or image.filename is None:
          continue
        
        image_filepath = pg.utils.safe_decode_gimp(image.filename)
        
        raw_value[image_filepath] = []
        
        for item_id in item_ids:
          if isinstance(item_id, (list, tuple)):
            if len(item_id) != 2:
              raise ValueError(
                'list-likes representing items must contain exactly 2 elements'
                ' (has {})'.format(len(item_id)))
            
            item = gimp.Item.from_id(item_id[0])
            item_type = item_id[1]
          else:
            item = gimp.Item.from_id(item_id)
            item_type = None
          
          if item is None:
            continue
          
          item_as_path = pg.pdbutils.get_item_as_path(item, include_image=False)
          
          if item_as_path is not None:
            if item_type is None:
              raw_value[image_filepath].append(item_as_path)
            else:
              raw_value[image_filepath].append(item_as_path + [item_type])
    
    return raw_value
  
  def _init_error_messages(self):
    self.error_messages['value_must_be_dict'] = _('Value must be a dictionary.')
  
  def _validate(self, value):
    if not isinstance(value, dict):
      raise pg.setting.SettingValueError(
        pg.setting.value_to_str_prefix(value) + self.error_messages['value_must_be_dict'])
