#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of Export Layers.
#
# Copyright (C) 2013-2017 khalim19 <khalim19@gmail.com>
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
This script pre-processes documents (HTML pages, plain text files), replacing
lines containing a Liquid-style tag and its arguments with the corresponding
content.

Usage:
`<script name> <source file paths> <destination file paths>`

Each file from the list of source file paths must have a counterpart in the
destination file paths list. Thus the length of the two lists must be identical.

The following tags can be specified in the documents:
* `{% include-section <relative file path> <arguments>... %}`:
  Replace the entire line containing this expression with the contents of the
  specified file.
  
  Optional arguments to `include-section`:
  * `section=<section name>` - Instead of the entire contents, insert only the
    contents from the section <section name>. A section is a valid Markdown
    section heading (underlining headers with "=" or "-", or using leading "#"s
    separated from headers by a single space).
  * `sentences=<index number>` or `sentences=<start index:end index>` - pick
    chosen sentence(s) from sections by indexes using the Python slice notation.
    Index starts from 0.
  * `no-header=(True | False)` - exclude section header. "False" by default. If
    no section is specified, the first section header is ignored.
  
  Examples:
      {% include-section "docs/README.md" section=Features no-header=True %}
      {% include-section "docs/README.md" section="Known Issues" %}
      {% include-section "docs/README.md" section=License sentences=0 %}

* `{% include-config <pygimplib configuration entry> %}`:
  Replace the expression with the corresponding configuration entry in
  `pygimplib.config`. If no such entry is found, the expression is not replaced.
  
  Examples:
  `{% include-config "PLUGIN_NAME" %}` will insert a pygimplib configuration
  entry titled `"PLUGIN_NAME"`, e.g. "export_layers".
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from export_layers import pygimplib
from future.builtins import *
import future.utils

import abc
import io
import os
import re
import sys

from export_layers.pygimplib import pgconstants

import export_layers.config
export_layers.config.init()

pygimplib.init()

#===============================================================================


def preprocess_contents(source_filepaths, dest_filepaths):
  for source_filepath, dest_filepath in zip(source_filepaths, dest_filepaths):
    with io.open(source_filepath, "r", encoding=pgconstants.TEXT_FILE_ENCODING) as file_:
      source_file_contents = file_.read()
    
    preprocessed_contents = source_file_contents
    
    for tag_name, tag_class in _TAGS.items():
      tag = tag_class(source_filepath, _TAG_MATCHING_REGEXES[tag_name])
      preprocessed_contents = _preprocess_contents(
        source_filepath, tag, preprocessed_contents)
    
    with io.open(dest_filepath, "w", encoding=pgconstants.TEXT_FILE_ENCODING) as file_:
      file_.writelines(preprocessed_contents)


def _preprocess_contents(source_filepath, tag, file_contents):
  for match in list(re.finditer(tag.matching_regex, file_contents)):
    tag_args = parse_args(tag.get_args_from_match(match))
    tag.process_args(tag_args["args"], tag_args["optional_args"])
    
    new_contents = tag.get_contents()
    file_contents = file_contents.replace(
      tag.get_match_to_be_replaced(match), new_contents, 1)
  
  return file_contents


#===============================================================================


def parse_args(args_str):
  
  def _parse_optional_arg(args_str_to_parse, optional_arg_name_match):
    optional_arg_name = args_str_to_parse[:optional_arg_name_match.end(1)]
    args_str_to_parse = args_str_to_parse[optional_arg_name_match.end(1) + 1:]
    
    optional_arg_value_with_quotes_match = (
      re.search(r'"(.+?)"(\s|$)', args_str_to_parse))
    
    if optional_arg_value_with_quotes_match is not None:
      optional_arg_value = optional_arg_value_with_quotes_match.group(1)
      args_str_to_parse = (
        args_str_to_parse[optional_arg_value_with_quotes_match.end(1) + 1:].lstrip())
    else:
      optional_arg_value_without_quotes_match = (
        re.search(r'(.+?)(\s|$)', args_str_to_parse))
      
      if optional_arg_value_without_quotes_match is not None:
        optional_arg_value = optional_arg_value_without_quotes_match.group(1)
        args_str_to_parse = (
          args_str_to_parse[optional_arg_value_without_quotes_match.end(1) + 1:].lstrip())
      else:
        raise ValueError(
          'missing value for optional argument "{0}"'.format(optional_arg_name))
    
    return args_str_to_parse, optional_arg_name, optional_arg_value
  
  parsed_args = {"args": [], "optional_args": {}}
  
  quote_char = '"'
  optional_arg_separator_char = "="
  
  args_str = args_str.strip()
  args_str_to_parse = args_str
  
  while args_str_to_parse:
    if args_str_to_parse[0] == quote_char:
      args_str_to_parse = args_str_to_parse[1:]
      
      end_quote_index = args_str_to_parse.find(quote_char)
      if end_quote_index != -1:
        parsed_args["args"].append(args_str_to_parse[:end_quote_index])
        args_str_to_parse = args_str_to_parse[end_quote_index + 1:].lstrip()
      else:
        raise ValueError("missing closing '{0}': {1}".format(quote_char, args_str))
    else:
      optional_arg_name_match = (
        re.search(r"^(\S+?)" + optional_arg_separator_char, args_str_to_parse))
      
      if optional_arg_name_match is not None:
        args_str_to_parse, optional_arg_name, optional_arg_value = (
          _parse_optional_arg(args_str_to_parse, optional_arg_name_match))
        parsed_args["optional_args"][optional_arg_name] = optional_arg_value
      else:
        space_or_end_match = re.search(r"(.+?)(\s+|$)", args_str_to_parse)
        
        if space_or_end_match is not None:
          next_space_index = space_or_end_match.end(1)
          parsed_args["args"].append(args_str_to_parse[:next_space_index])
          args_str_to_parse = args_str_to_parse[next_space_index:].lstrip()
        else:
          args_str_to_parse = ""
  
  return parsed_args


#===============================================================================


class CustomLiquidTag(future.utils.with_metaclass(abc.ABCMeta, object)):
  
  def __init__(self, source_filepath, matching_regex):
    self.source_filepath = source_filepath
    self.matching_regex = matching_regex
    
    self.args = []
    self.optional_args = {}
  
  @abc.abstractmethod
  def get_args_from_match(self, match):
    pass
  
  @abc.abstractmethod
  def get_match_to_be_replaced(self, match):
    pass
  
  @abc.abstractmethod
  def process_args(self, args, optional_args):
    pass
  
  @abc.abstractmethod
  def get_contents(self):
    pass
  

class IncludeSectionTag(CustomLiquidTag):
  
  def get_args_from_match(self, match):
    return match.group(3)
  
  def get_match_to_be_replaced(self, match):
    return match.group(2)
  
  def process_args(self, args, optional_args):
    self.args = [self._process_filepath_arg(args[0])]
    self.optional_args = self._process_optional_args(optional_args)
  
  def get_contents(self):
    document_filepath = self.args[0]
    section_name = self.optional_args["section"]
    
    with io.open(
           document_filepath, "r", encoding=pgconstants.TEXT_FILE_ENCODING) as document:
      document_contents = document.read()
      if not section_name and not self.optional_args["no-header"]:
        section_header, section_contents = "", document_contents
      else:
        section_header, section_contents = (
          self._find_section(document_contents, section_name))
    
    section_header, section_contents = self._get_sentences_from_section(
      section_header, section_contents, self.optional_args["sentences"])
    
    section_header, section_contents = self._strip_section_header(
      section_header, section_contents, self.optional_args["no-header"])
    
    return section_header + section_contents
  
  def _process_filepath_arg(self, relative_filepath):
    return os.path.normpath(
      os.path.join(os.path.dirname(self.source_filepath), relative_filepath))
  
  def _process_optional_args(self, optional_args):
    processed_optional_args = {}
    
    processed_optional_args["section"] = optional_args.get("section", "")
    processed_optional_args["sentences"] = (
      self._parse_sentence_indices(optional_args.get("sentences", "")))
    processed_optional_args["no-header"] = (
      self._parse_bool_from_str(optional_args.get("no-header", "False")))
    
    return processed_optional_args
  
  @staticmethod
  def _parse_sentence_indices(arg_str):
    if not arg_str:
      return []
    
    sentence_indices_str = arg_str.split(":")[:2]
    sentence_indices = []
    for index_str in sentence_indices_str:
      try:
        index = int(index_str)
      except (ValueError, TypeError):
        index = None
      sentence_indices.append(index)
    
    return sentence_indices
  
  @staticmethod
  def _parse_bool_from_str(arg_str):
    return arg_str.lower() == "true"
  
  @staticmethod
  def _find_section(contents, section_name):
    
    def _get_section_contents(contents, start_of_section_contents, end_of_section_header):
      next_section_match_regex = (
        "\n"
        + "("
        + r"#+ .*?\n"
        + "|"
        + r".*?\n[=-]+\n"
        + ")")
      next_section_match = re.search(
        next_section_match_regex, contents[start_of_section_contents:])
      
      if next_section_match:
        start_of_next_section_header = next_section_match.start(1)
        end_of_section_contents = (
          start_of_section_contents + start_of_next_section_header - 1)
        
        return contents[end_of_section_header:end_of_section_contents]
      else:
        return contents[end_of_section_header:]
    
    section_header = ""
    section_contents = ""
    
    if section_name:
      section_name_pattern = re.escape(section_name)
    else:
      section_name_pattern = r".*?"
    
    section_match_regex = (
      r"(^|\n)"
      + "("
      + "(" + section_name_pattern + ")" + r"\n[=-]+\n"
      + "|"
      + r"#+ " + "(" + section_name_pattern + ")" + r"\n"
      + ")")
    
    section_match = re.search(section_match_regex, contents)
    if section_match:
      start_of_section_header = section_match.start(2)
      end_of_section_header = section_match.end(2)
      
      start_of_section_contents = end_of_section_header + 1
      
      section_header = contents[start_of_section_header:end_of_section_header]
      
      if section_name:
        section_contents = _get_section_contents(
          contents, start_of_section_contents, end_of_section_header)
      else:
        section_contents = contents[end_of_section_header:]
    
    section_contents = section_contents.rstrip("\n")
    
    return section_header, section_contents
  
  @staticmethod
  def _get_sentences_from_section(section_header, section_contents, sentence_indices):
    if sentence_indices:
      sentences = re.split(r"\.[ \n]", section_contents)
      
      if len(sentence_indices) == 1:
        section_sentences = sentences[sentence_indices[0]].strip()
        if not section_sentences.endswith("."):
          section_sentences += "."
        
        return section_header, section_sentences
      elif len(sentence_indices) == 2:
        section_sentences = ". ".join(
          sentence.strip()
          for sentence in sentences[sentence_indices[0]:sentence_indices[1]])
        
        if not section_sentences.endswith("."):
          section_sentences += '.'
        
        return section_header, section_sentences
    
    return section_header, section_contents
  
  @staticmethod
  def _strip_section_header(section_header, section_contents, should_strip_header):
    if should_strip_header:
      return "", section_contents
    else:
      return section_header, section_contents


class IncludeConfigTag(CustomLiquidTag):
  
  def get_args_from_match(self, match):
    return match.group(2)
  
  def get_match_to_be_replaced(self, match):
    return match.group(1)
  
  def process_args(self, args, optional_args):
    self.args = args
  
  def get_contents(self):
    return getattr(pygimplib.config, self.args[0], "") if self.args else ""


#===============================================================================

_TAGS = {
  "include-section": IncludeSectionTag,
  "include-config": IncludeConfigTag,
}

_TAG_MATCHING_REGEXES = {
  "include-section": r"( *)(\{% include-section (.*?) %\})",
  "include-config": r"(\{% include-config (.*?) %\})",
}

#===============================================================================


def main(source_filepaths, dest_filepaths):
  if len(source_filepaths) != len(dest_filepaths):
    print(
      "Lists of source and destination file paths are not the same length",
      file=sys.stderr)
    sys.exit(1)
  
  preprocess_contents(source_filepaths, dest_filepaths)


if __name__ == "__main__":
  main(sys.argv[1], sys.argv[2])
