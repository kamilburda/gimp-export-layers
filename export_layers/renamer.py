# -*- coding: utf-8 -*-
#
# This file is part of Export Layers.
#
# Copyright (C) 2013-2019 khalim19 <khalim19@gmail.com>
#
# Export Layers is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Export Layers is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Export Layers.  If not, see <https://www.gnu.org/licenses/>.

"""
This module provides a class to rename layer names according to the specified
pattern.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import collections
import datetime
import string

from export_layers.pygimplib import pgpath

from . import operations


class LayerNameRenamer(object):
  
  def __init__(self, layer_exporter, pattern, fields=None):
    self._layer_exporter = layer_exporter
    self._pattern = pattern
    
    self._fields = fields if fields is not None else _FIELDS_LIST
    
    self._filename_pattern_generator = pgpath.StringPatternGenerator(
      pattern=self._pattern, fields=self._get_fields_and_substitute_funcs())
    
    for field in self._fields:
      field.on_renamer_init(self._filename_pattern_generator)
  
  def rename(self, layer_elem):
    for field in self._fields:
      field.process_before_rename(layer_elem)
    
    layer_elem.name = self._filename_pattern_generator.generate()
  
  def _get_fields_and_substitute_funcs(self):
    return {
      field.regex: self._get_field_substitute_func(field.substitute_func)
      for field in self._fields if field.substitute_func is not None}
  
  def _get_field_substitute_func(self, func):
    def substitute_func_wrapper(*args):
      return func(self._layer_exporter, *args)
    
    return substitute_func_wrapper


def get_field_descriptions(fields):
  return [
    (field.display_name, field.str_to_insert, str(field))
    for field in fields.values()]


class Field(object):
  
  def __init__(
        self,
        regex,
        substitute_func,
        display_name,
        str_to_insert,
        usage_lines,
        details_lines,
        examples_lines):
    self._regex = regex
    self._substitute_func = substitute_func
    self._display_name = display_name
    self._str_to_insert = str_to_insert
    self._usage_lines = usage_lines
    self._details_lines = details_lines
    self._examples_lines = examples_lines
  
  def __str__(self):
    return "\n\n".join(
      [str_ for str_ in [self.usage, self.details, self.examples] if str_])
  
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
  def usage_lines(self):
    return self._usage_lines
  
  @property
  def details_lines(self):
    return self._details_lines
  
  @property
  def examples_lines(self):
    return self._examples_lines
  
  @property
  def usage(self):
    if not self.usage_lines:
      return ""
    
    formatted_specs = []
    
    for spec in self.usage_lines:
      if spec:
        formatted_specs.append("[{}, {}]".format(self.regex, spec))
      else:
        formatted_specs.append("[{}]".format(self.regex))
    
    return "\n".join([_("Usage:")] + formatted_specs)
  
  @property
  def details(self):
    if self._details_lines:
      return "\n".join([_("Details:")] + self._details_lines)
    else:
      return ""
  
  @property
  def examples(self):
    if not self._examples_lines:
      return ""
    
    formatted_examples_lines = []
    
    for example_line in self._examples_lines:
      if len(example_line) > 1:
        formatted_examples_lines.append(" \u2192 ".join(example_line))
      else:
        formatted_examples_lines.append(*example_line)
    
    return "\n".join([_("Examples:")] + formatted_examples_lines)
  
  def on_renamer_init(self, string_pattern_generator):
    pass
  
  def process_before_rename(self, layer_elem):
    pass


class NumberField(Field):
  
  def __init__(self):
    super().__init__(
      "^[0-9]+$",
      self._get_number,
      _("image001"),
      "image[001]",
      [],
      [],
      [
        ["[001]", "001, 002, ..."],
        ["[1]", "1, 2, ..."],
        ["[005]", "005, 006, ..."],
      ],
    )
  
  def on_renamer_init(self, string_pattern_generator):
    self._number_fields = set([
      field_value
      for field_value, field_regex
      in string_pattern_generator.parsed_fields_and_matching_regexes.items()
      if field_regex == self.regex])
    
    # key: `_ItemTreeElement` parent ID (`None` for root)
    # value: dictionary of (field value, number generators) pairs
    self._parents_and_number_generators = {}
    
    self._current_parent = None
  
  def process_before_rename(self, layer_elem):
    self._current_parent = (
      layer_elem.parent.item.ID if layer_elem.parent is not None else None)
    
    if self._current_parent not in self._parents_and_number_generators:
      self._parents_and_number_generators[self._current_parent] = (
        self._get_initial_number_generators())
  
  @staticmethod
  def generate_number(padding, initial_number):
    i = initial_number
    while True:
      str_i = str(i)
      
      if len(str_i) < padding:
        str_i = "0" * (padding - len(str_i)) + str_i
      
      yield str_i
      i += 1
  
  def _get_number(self, layer_exporter, field_value):
    return next(self._parents_and_number_generators[self._current_parent][field_value])
  
  def _get_initial_number_generators(self):
    return {
      field_value: self._get_initial_number_generator(field_value)
      for field_value in self._number_fields}
  
  def _get_initial_number_generator(self, field_value):
    return self.generate_number(
      padding=len(field_value), initial_number=int(field_value))


class _PercentTemplate(string.Template):
  
  delimiter = "%"


def _get_layer_name(layer_exporter, field_value, file_extension_strip_mode=""):
  layer_elem = layer_exporter.current_layer_elem
  
  if file_extension_strip_mode in ["%e", "%i"]:
    file_extension = layer_elem.get_file_extension_from_orig_name()
    if file_extension:
      if file_extension_strip_mode == "%i":
        if file_extension == layer_exporter.default_file_extension:
          return layer_elem.name
      else:
        return layer_elem.name
  
  return layer_elem.get_base_name()


def _get_image_name(layer_exporter, field_value, keep_extension_str=""):
  image_name = (
    layer_exporter.image.name if layer_exporter.image.name is not None else _("Untitled"))
  
  if keep_extension_str == "%e":
    return image_name
  else:
    return pgpath.get_filename_with_new_file_extension(image_name, "")


def _get_layer_path(layer_exporter, field_value, separator="-", wrapper=None):
  path_component_token = "%c"
  
  if wrapper is None:
    wrapper = "{}"
  else:
    if path_component_token in wrapper:
      wrapper = wrapper.replace(path_component_token, "{}")
    else:
      wrapper = "{}"
  
  path_components = (
    [parent.name for parent in layer_exporter.current_layer_elem.parents]
    + [layer_exporter.current_layer_elem.name])
  
  return separator.join(
    [wrapper.format(path_component) for path_component in path_components])


def _get_tags(layer_exporter, field_value, *args):
  tags_to_insert = []
  
  def _insert_tag(tag):
    if tag in operations.BUILTIN_TAGS:
      tag_display_name = operations.BUILTIN_TAGS[tag]
    else:
      tag_display_name = tag
    tags_to_insert.append(tag_display_name)
  
  def _get_tag_from_tag_display_name(tag_display_name):
    builtin_tags_keys = list(operations.BUILTIN_TAGS)
    builtin_tags_values = list(operations.BUILTIN_TAGS.values())
    return builtin_tags_keys[builtin_tags_values.index(tag_display_name)]
  
  def _insert_all_tags():
    for tag in layer_exporter.current_layer_elem.tags:
      _insert_tag(tag)
    
    tags_to_insert.sort(key=lambda tag: tag.lower())
  
  def _insert_specified_tags(tags):
    for tag in tags:
      if tag in operations.BUILTIN_TAGS:
        continue
      if tag in operations.BUILTIN_TAGS.values():
        tag = _get_tag_from_tag_display_name(tag)
      if tag in layer_exporter.current_layer_elem.tags:
        _insert_tag(tag)
  
  tag_separator = "-"
  tag_wrapper = "{}"
  tag_token = "%t"
  
  if not args:
    _insert_all_tags()
  else:
    if len(args) < 2:
      _insert_specified_tags(args)
    else:
      if tag_token in args[1]:
        tag_separator = args[0]
        tag_wrapper = args[1].replace(tag_token, "{}")
        
        if len(args) > 2:
          _insert_specified_tags(args[2:])
        else:
          _insert_all_tags()
      else:
        _insert_specified_tags(args)
  
  return tag_separator.join([tag_wrapper.format(tag) for tag in tags_to_insert])


def _get_current_date(layer_exporter, field_value, date_format="%Y-%m-%d"):
  return datetime.datetime.now().strftime(date_format)


def _get_attributes(layer_exporter, field_value, pattern):
  layer_elem = layer_exporter.current_layer_elem
  image = layer_exporter.image
  
  fields = {
    "w": layer_elem.item.width,
    "h": layer_elem.item.height,
    "x": layer_elem.item.offsets[0],
    "y": layer_elem.item.offsets[1],
    "iw": image.width,
    "ih": image.height,
  }
  
  return _PercentTemplate(pattern).safe_substitute(fields)


_FIELDS_LIST = [
  NumberField(),
  Field(
    "layer name",
    _get_layer_name,
    _("Layer name"),
    "[layer name]",
    [
      "",
      "%e",
      "%i",
    ],
    [
      _("%e - keep file extension"),
      _("%i - keep file extension only if matching the specified file extension"),
    ],
    [
      [_('Suppose that a layer is named "Frame.png" and the file extension is "png".')],
      ["[layer name]", "Frame"],
      ["[layer name, %e]", "Frame.png"],
      ["[layer name, %i]", "Frame.png"],
      [_('Suppose that a layer is named "Frame.jpg".')],
      ["[layer name, %i]", "Frame"],
    ],
  ),
  Field(
    "image name",
    _get_image_name,
    _("Image name"),
    "[image name]",
    [
      "",
      "%e",
    ],
    [
      _("%e - keep image file extension"),
    ],
    [
      [_('Suppose that the image is named "Image.png" and the file extension is "png".')],
      ["[image name]", "Image"],
      ["[image name, %e]", "Image.png"],
    ],
  ),
  Field(
    "layer path",
    _get_layer_path,
    _("Layer path"),
    "[layer path]",
    [
      "",
      "<i>separator</i>",
      "<i>separator</i>, <i>wrapper</i>",
    ],
    [
      _("<i>separator</i> - string separating the layer path components "
        "(parent groups and the layer)"),
      _("<i>wrapper</i> - string wrapping each path component; "
        '"%c" denotes the component itself'),
    ],
    [
      [_('Suppose that a layer named "Left" has parent groups named '
         '"Hands" and "Body".')],
      ["[layer path]", "Body-Hands-Left"],
      ["[layer path, _]", "Body_Hands_Left"],
      ["[layer path, _, (%c)]", "(Body)_(Hands)_(Left)"],
    ],
  ),
  Field(
    "tags",
    _get_tags,
    _("Tags"),
    "[tags]",
    [
      "",
      "<i>tags...</i>",
      "<i>separator</i>, <i>wrapper</i>, <i>tags...</i>",
    ],
    [
      _("Without arguments, all tags are included. Tags that do not exist are ignored."),
      _("<i>separator</i> - string separating the tags"),
      _('<i>wrapper</i> - string wrapping each tag; "%t" denotes the tag itself'),
    ],
    [
      [_('Suppose that a layer has tags "left", "middle" and "right".')],
      ["[tags]", "left-middle-right"],
      ["[tags, left, right]", "left-right"],
      ["[tags, _, (%t), left, right]", "(left)_(right)"],
    ],
  ),
  Field(
    "current date",
    _get_current_date,
    _("Current date"),
    "[current date]",
    [
      "",
      "<i>format</i>",
    ],
    [
      _('Specify <i>format</i> as per the Python "strftime" function.'),
    ],
    [
      ["[current date]", "2019-01-28"],
      ["[current date, %m.%d.%Y_%H-%M]", "28.01.2019_19-04"],
    ],
  ),
  Field(
    "attributes",
    _get_attributes,
    _("Attributes"),
    "[attributes]",
    [
      "<i>pattern</i>",
    ],
    [
      _("<i>pattern</i> can contain the following fields:"),
      _("%w - the layer width"),
      _("%h - the layer height"),
      _("%x - the layer x-offset"),
      _("%y - the layer y-offset"),
      _("%iw - the image width"),
      _("%ih - the image height"),
    ],
    [
      ["[attributes, %w-%h-%x-%y]", "1000-500-0-40"],
    ],
  ),
]

FIELDS = collections.OrderedDict([(field.regex, field) for field in _FIELDS_LIST])
