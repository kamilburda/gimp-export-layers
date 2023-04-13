# -*- coding: utf-8 -*-

"""Renaming layer names according to the specified pattern.

The pattern can contain one or more fields provided in this module.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import collections
import datetime
import re
import string

from export_layers import pygimplib as pg

from export_layers import actions


class ItemRenamer(object):
  
  def __init__(self, pattern, fields_raw=None):
    self._filename_pattern = pg.path.StringPattern(
      pattern=pattern,
      fields=_get_fields_and_substitute_funcs(_init_fields(fields_raw)))
  
  def rename(self, batcher, item=None):
    if item is None:
      item = batcher.current_item
    
    return self._filename_pattern.substitute(batcher, item)


def _get_fields_and_substitute_funcs(fields):
  return {
    field.regex: field.substitute_func
    for field in fields if field.substitute_func is not None}


def _init_fields(fields_raw):
  if fields_raw is None:
    fields_raw = _FIELDS_LIST
  
  fields = []
  
  for field_raw in fields_raw:
    # Use a copy to avoid modifying the original that could be reused.
    field_raw_copy = field_raw.copy()
    
    field_type = field_raw_copy.pop('type')
    fields.append(field_type(**field_raw_copy))
  
  return fields


def get_field_descriptions(fields):
  descriptions = []
  
  for field in fields.values():
    if isinstance(field, Field):
      descriptions.append(
        (field.display_name, field.str_to_insert, field.regex, str(field)))
    else:
      descriptions.append(
        (field['display_name'], field['str_to_insert'], field['regex'],
         _get_formatted_examples(field['examples_lines'])))
  
  return descriptions


def _get_formatted_examples(examples_lines):
  if not examples_lines:
    return ''
  
  formatted_examples_lines = []
  
  for example_line in examples_lines:
    if len(example_line) > 1:
      formatted_examples_lines.append(' \u2192 '.join(example_line))
    else:
      formatted_examples_lines.append(*example_line)
  
  return '\n'.join(['<b>{}</b>'.format(_('Examples'))] + formatted_examples_lines)


class Field(object):
  
  def __init__(
        self,
        regex,
        substitute_func,
        display_name,
        str_to_insert,
        examples_lines):
    self._regex = regex
    self._substitute_func = substitute_func
    self._display_name = display_name
    self._str_to_insert = str_to_insert
    self._examples_lines = examples_lines
  
  def __str__(self):
    return self.examples
  
  @property
  def regex(self):
    return self._regex
  
  @property
  def substitute_func(self):
    return self._substitute_func
  
  @property
  def display_name(self):
    return self._display_name
  
  @property
  def str_to_insert(self):
    return self._str_to_insert
  
  @property
  def examples_lines(self):
    return self._examples_lines
  
  @property
  def examples(self):
    return _get_formatted_examples(self._examples_lines)


class NumberField(Field):
  
  def __init__(
        self,
        regex,
        display_name,
        str_to_insert,
        examples_lines):
    super().__init__(
      regex,
      self._get_number,
      display_name,
      str_to_insert,
      examples_lines,
    )
    
    # key: field value
    # value: dict of (parent or None, number generator) pairs
    self._global_number_generators = collections.defaultdict(dict)
  
  @staticmethod
  def generate_number(initial_number, padding, ascending=True):
    i = initial_number
    if ascending:
      increment = 1
    else:
      increment = -1
    
    while True:
      str_i = str(i)
      
      if len(str_i) < padding:
        str_i = '0' * (padding - len(str_i)) + str_i
      
      yield str_i
      i += increment
  
  def _get_number(self, batcher, item, field_value, *args):
    reset_numbering_on_parent = True
    ascending = True
    padding = None
    
    for arg in args:
      if arg == '%n':
        reset_numbering_on_parent = False
      elif arg.startswith('%d'):
        ascending = False
        try:
          padding = int(arg[len('%d'):])
        except ValueError:
          pass
    
    if reset_numbering_on_parent:
      parent_item = item.parent if item.parent is not None else None
      parent_id = parent_item.raw.ID if parent_item is not None else None
    else:
      parent_item = None
      parent_id = None
    
    if parent_id not in self._global_number_generators[field_value]:
      padding = padding if padding is not None else len(field_value)
      
      initial_number = int(field_value)
      
      if initial_number == 0 and not ascending:
        if reset_numbering_on_parent:
          if parent_item is not None:
            initial_number = len([
              tree_item for tree_item in batcher.item_tree
              if tree_item.depth == parent_item.depth + 1 and tree_item.parent == parent_item])
          else:
            initial_number = len(
              [tree_item for tree_item in batcher.item_tree if tree_item.depth == 0])
        else:
          initial_number = len(batcher.item_tree)
      
      self._global_number_generators[field_value][parent_id] = self.generate_number(
        initial_number, padding, ascending)
    
    return next(self._global_number_generators[field_value][parent_id])


class _PercentTemplate(string.Template):
  
  delimiter = '%'


def _get_layer_name(batcher, item, field_value, file_extension_strip_mode=''):
  if file_extension_strip_mode in ['%e', '%i']:
    file_extension = pg.path.get_file_extension(item.orig_name)
    if file_extension:
      if file_extension_strip_mode == '%i':
        if file_extension == batcher.file_extension:
          return item.name
      else:
        return item.name
  
  return pg.path.get_filename_root(item.name)


def _get_image_name(batcher, item, field_value, keep_extension_str=''):
  if batcher.current_image is not None and batcher.current_image.name is not None:
    image_name = batcher.current_image.name
  else:
    image_name = _('Untitled')
  
  if keep_extension_str == '%e':
    return image_name
  else:
    return pg.path.get_filename_with_new_file_extension(image_name, '')


def _get_layer_path(
      batcher, item, field_value, separator='-', wrapper=None, file_extension_strip_mode=''):
  path_component_token = '%c'
  
  if wrapper is None:
    wrapper = '{}'
  else:
    if path_component_token in wrapper:
      wrapper = wrapper.replace(path_component_token, '{}')
    else:
      wrapper = '{}'
  
  path_components = [parent.name for parent in item.parents]
  path_components += [_get_layer_name(batcher, item, field_value, file_extension_strip_mode)]
  
  return separator.join([wrapper.format(path_component) for path_component in path_components])


def _get_tags(batcher, item, field_value, *args):
  tags_to_insert = []
  
  def _insert_tag(tag):
    if tag in actions.BUILTIN_TAGS:
      tag_display_name = actions.BUILTIN_TAGS[tag]
    else:
      tag_display_name = tag
    tags_to_insert.append(tag_display_name)
  
  def _get_tag_from_tag_display_name(tag_display_name):
    builtin_tags_keys = list(actions.BUILTIN_TAGS)
    builtin_tags_values = list(actions.BUILTIN_TAGS.values())
    return builtin_tags_keys[builtin_tags_values.index(tag_display_name)]
  
  def _insert_all_tags():
    for tag in item.tags:
      _insert_tag(tag)
    
    tags_to_insert.sort(key=lambda tag: tag.lower())
  
  def _insert_specified_tags(tags):
    for tag in tags:
      if tag in actions.BUILTIN_TAGS:
        continue
      if tag in actions.BUILTIN_TAGS.values():
        tag = _get_tag_from_tag_display_name(tag)
      if tag in item.tags:
        _insert_tag(tag)
  
  tag_separator = '-'
  tag_wrapper = '{}'
  tag_token = '%t'
  
  if not args:
    _insert_all_tags()
  else:
    if len(args) < 2:
      _insert_specified_tags(args)
    else:
      if tag_token in args[1]:
        tag_separator = args[0]
        tag_wrapper = args[1].replace(tag_token, '{}')
        
        if len(args) > 2:
          _insert_specified_tags(args[2:])
        else:
          _insert_all_tags()
      else:
        _insert_specified_tags(args)
  
  return tag_separator.join([tag_wrapper.format(tag) for tag in tags_to_insert])


def _get_current_date(batcher, item, field_value, date_format='%Y-%m-%d'):
  return datetime.datetime.now().strftime(date_format)


def _get_attributes(batcher, item, field_value, pattern, measure='%px'):
  image = batcher.current_image
  
  fields = {
    'iw': image.width,
    'ih': image.height,
  }
  
  layer_fields = {}
  
  if measure == '%px':
    layer_fields = {
      'w': item.raw.width,
      'h': item.raw.height,
      'x': item.raw.offsets[0],
      'y': item.raw.offsets[1],
    }
  elif measure.startswith('%pc'):
    match = re.match(r'^' + re.escape('%pc') + r'([0-9]*)$', measure)
    
    if match is not None:
      if match.group(1):
        round_digits = int(match.group(1))
      else:
        round_digits = 2
      
      layer_fields = {
        'w': round(item.raw.width / image.width, round_digits),
        'h': round(item.raw.height / image.height, round_digits),
        'x': round(item.raw.offsets[0] / image.width, round_digits),
        'y': round(item.raw.offsets[1] / image.height, round_digits),
      }
  
  fields.update(layer_fields)
  
  return _PercentTemplate(pattern).safe_substitute(fields)


def _replace(
      batcher, item, field_value, field_to_replace_str, pattern, replacement, *count_and_flags):
  field_name, field_args = pg.path.StringPattern.parse_field(field_to_replace_str)
  
  try:
    field_func = FIELDS[field_name]['substitute_func']
  except KeyError:
    return ''
  
  str_to_process = field_func(batcher, item, field_name, *field_args)
  
  count = 0
  flags = 0
  
  if len(count_and_flags) >= 1:
    try:
      count = int(count_and_flags[0])
    except ValueError:
      pass
  
  for flag_name in count_and_flags[1:]:
    flags |= getattr(re, flag_name.upper())
  
  return re.sub(pattern, replacement, str_to_process, count=count, flags=flags)


_FIELDS_LIST = [
  {
    'type': NumberField,
    'regex': '^[0-9]+$',
    'display_name': _('image001'),
    'str_to_insert': 'image[001]',
    'examples_lines': [
      ['[001]', '001, 002, ...'],
      ['[1]', '1, 2, ...'],
      ['[005]', '005, 006, ...'],
      [_('To continue numbering across layer groups, use %n.')],
      ['[001, %n]', '001, 002, ...'],
      [_('To use descending numbers, use %d.')],
      [_('Suppose that the number of layers is 5:')],
      ['[000, %d]', '005, 004, ...'],
      ['[10, %d2]', '10, 09, ...'],
    ],
  },
  {
    'type': Field,
    'regex': 'layer name',
    'substitute_func': _get_layer_name,
    'display_name': _('Layer name'),
    'str_to_insert': '[layer name]',
    'examples_lines': [
      [_('Suppose that a layer is named "Frame.png" and the file extension is "png".')],
      ['[layer name]', 'Frame'],
      ['[layer name, %e]', 'Frame.png'],
      ['[layer name, %i]', 'Frame.png'],
      [_('Suppose that a layer is named "Frame.jpg".')],
      ['[layer name]', 'Frame'],
      ['[layer name, %e]', 'Frame.jpg'],
      ['[layer name, %i]', 'Frame'],
    ],
  },
  {
    'type': Field,
    'regex': 'image name',
    'substitute_func': _get_image_name,
    'display_name': _('Image name'),
    'str_to_insert': '[image name]',
    'examples_lines': [
      [_('Suppose that the image is named "Image.xcf".')],
      ['[image name]', 'Image'],
      ['[image name, %e]', 'Image.xcf'],
    ],
  },
  {
    'type': Field,
    'regex': 'layer path',
    'substitute_func': _get_layer_path,
    'display_name': _('Layer path'),
    'str_to_insert': '[layer path]',
    'examples_lines': [
      [_('Suppose that a layer named "Left" has parent groups named "Hands" and "Body".')],
      ['[layer path]', 'Body-Hands-Left'],
      ['[layer path, _]', 'Body_Hands_Left'],
      ['[layer path, _, (%c)]', '(Body)_(Hands)_(Left)'],
      [_('Suppose that the layer is named "Left.jpg" and the file extension is "png".')],
      ['[layer path]', 'Body-Hands-Left'],
      ['[layer path, -, %c, %e]', 'Body-Hands-Left.jpg'],
      ['[layer path, -, %c, %i]', 'Body-Hands-Left'],
    ],
  },
  {
    'type': Field,
    'regex': 'replace',
    'substitute_func': _replace,
    'display_name': _('Replace'),
    'str_to_insert': '[replace]',
    'examples_lines': [
      [_('Suppose that a layer is named "Animal copy #1".')],
      ['[replace, [layer name], [a], [b] ]', 'Animbl copy #1'],
      [_('You can use the regular expression syntax as defined in the "re" module for Python.')],
      ['[replace, [layer name], [ copy(?: #[[0-9]]+)*$], [] ]', 'Animal'],
      [_('You can specify the number of replacements and flags as defined in the "re" module for Python.')],
      ['[replace, [layer name], [a], [b], 1, ignorecase]', 'bnimal copy #1'],
    ],
  },
  {
    'type': Field,
    'regex': 'tags',
    'substitute_func': _get_tags,
    'display_name': _('Tags'),
    'str_to_insert': '[tags]',
    'examples_lines': [
      [_('Suppose that a layer has tags "left", "middle" and "right".')],
      ['[tags]', 'left-middle-right'],
      ['[tags, left, right]', 'left-right'],
      ['[tags, _, (%t)]', '(left)_(middle)_(right)'],
      ['[tags, _, (%t), left, right]', '(left)_(right)'],
    ],
  },
  {
    'type': Field,
    'regex': 'current date',
    'substitute_func': _get_current_date,
    'display_name': _('Current date'),
    'str_to_insert': '[current date]',
    'examples_lines': [
      ['[current date]', '2019-01-28'],
      [_('Custom date format uses formatting as per the "strftime" function in Python.')],
      ['[current date, %m.%d.%Y_%H-%M]', '28.01.2019_19-04'],
    ],
  },
  {
    'type': Field,
    'regex': 'attributes',
    'substitute_func': _get_attributes,
    'display_name': _('Attributes'),
    'str_to_insert': '[attributes]',
    'examples_lines': [
      [_('Suppose that a layer has width, height, <i>x</i>-offset and <i>y</i>-offset\n'
         'of 1000, 270, 0 and 40 pixels, respectively,\n'
         'and the image has width and height of 1000 and 500 pixels, respectively.')],
      ['[attributes, %w-%h-%x-%y]', '1000-270-0-40'],
      ['[attributes, %w-%h-%x-%y, %pc]', '1.0-0.54-0.0-0.08'],
      ['[attributes, %w-%h-%x-%y, %pc1]', '1.0-0.5-0.0-0.1'],
      ['[attributes, %iw-%ih]', '1000-500'],
    ],
  },
]

FIELDS = collections.OrderedDict([(field['regex'], field) for field in _FIELDS_LIST])
