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

Currently, only the following tag is provided:
* `{% include-section <relative file path>:<section>[arguments]... %}`:
  replaces the line with the section from the specified file. For example,
  `{% include-section README.md:Features %}` replaces the line with the
  contents of the section "Features" from the file `README.md` in the same
  directory as the file containing this line.
  
  A section is a valid Markdown section heading (underlining headers with "="
  or "-", or using leading "#"s separated from headers by a single space).
  
  Optional arguments to `include-section`:
  * `[index]` or `[start index:end index]`: pick chosen sentence(s) from
    sections using Python slice notation
  * `[no-header]` - exclude section header
"""

from __future__ import absolute_import, division, print_function, unicode_literals
import pygimplib
from future.builtins import *

import io
import os
import re
import sys

from pygimplib import pgconstants

import export_layers.config
export_layers.config.init()

pygimplib.init()

#===============================================================================


def preprocess_contents(source_filepaths, dest_filepaths, insert_markdownify_tag):
  for source_filepath, dest_filepath in zip(source_filepaths, dest_filepaths):
    with io.open(source_filepath, "r", encoding=pgconstants.TEXT_FILE_ENCODING) as file_:
      source_file_contents = file_.read()
    
    preprocessed_contents = _preprocess_contents(
      source_filepath, source_file_contents, insert_markdownify_tag)
    
    with io.open(dest_filepath, "w", encoding=pgconstants.TEXT_FILE_ENCODING) as file_:
      file_.writelines(preprocessed_contents)


def _preprocess_contents(source_filepath, file_contents, insert_markdownify_tag):
  for match in list(re.finditer(r"( *)(\{% include-section (.*?) %\})", file_contents)):
    tag_args = _parse_tag_args(source_filepath, "include-section", match.group(3))
    section_contents = _process_tag_args("include-section", tag_args)
    
    if insert_markdownify_tag:
      leading_spacing = match.group(1)
      dest_contents = (
        "{% capture markdown-insert %}\n"
        + section_contents + "\n" + leading_spacing
        + "{% endcapture %}"
        + "\n" + leading_spacing + "{{ markdown-insert | markdownify }}")
      file_contents = file_contents.replace(match.group(2), dest_contents, 1)
    else:
      file_contents = file_contents.replace(match.group(2), section_contents, 1)
  
  return file_contents


def _parse_tag_args(source_filepath, tag_name, tag_args_str):
  args_match = re.search(r"\[.*\]$", tag_args_str)
  if args_match:
    relative_document_filepath = (
      tag_args_str[:len(tag_args_str) - len(args_match.group())])
  else:
    relative_document_filepath = tag_args_str
  
  document_relative_filepath_components = relative_document_filepath.strip('"').split("/")
  if ":" in document_relative_filepath_components[-1]:
    document_relative_filepath_components[-1], document_section_name = (
      document_relative_filepath_components[-1].split(":"))
  else:
    document_section_name = ""
  
  document_filepath = os.path.normpath(
    os.path.join(
      os.path.dirname(source_filepath), *document_relative_filepath_components))
  
  tag_args = [document_filepath, document_section_name]
  
  for tag_arg_item in _TAG_ARGUMENTS[tag_name]:
    tag_arg_item.parse_func_retvals = []
  
  if args_match:
    for tag_arg_item in _TAG_ARGUMENTS[tag_name]:
      tag_arg_match = re.search(
        r"\[(" + tag_arg_item.tag_arg_match_pattern + r")\]", args_match.group())
      if tag_arg_match:
        tag_arg_item.parse_func_retvals = [
          tag_arg_item.parse_func(tag_arg_match.group(1))]
  
  return tag_args


def _process_tag_args(tag_name, tag_args):
  document_filepath = tag_args[0]
  section_name = tag_args[1]
  with io.open(
         document_filepath, "r", encoding=pgconstants.TEXT_FILE_ENCODING) as document:
    document_contents = document.read()
    if section_name:
      section_header, section_contents = _find_section(document_contents, section_name)
    else:
      section_header, section_contents = "", document_contents
  
  for tag_arg_item in _TAG_ARGUMENTS[tag_name]:
    if tag_arg_item.parse_func_retvals:
      section_header, section_contents = tag_arg_item.process_func(
        section_header, section_contents, *tag_arg_item.parse_func_retvals)
  
  return section_header + section_contents


def _find_section(contents, section_name):
  section_header = ""
  section_contents = ""
  
  section_match_regex = (
    r"(^|\n)"
    + "("
    + "(" + re.escape(section_name) + ")" + r"\n[=-]+\n"
    + "|"
    + r"#+ " + "(" + re.escape(section_name) + ")" + r"\n"
    + ")")
  
  next_section_match_regex = (
    "\n"
    + "("
    + r"#+ .*?\n"
    + "|"
    + r".*?\n[=-]+\n"
    + ")")
  
  section_match = re.search(section_match_regex, contents)
  if section_match:
    start_of_section_header = section_match.start(2)
    end_of_section_header = section_match.end(2)
    
    start_of_section_contents = end_of_section_header + 1
    next_section_match = re.search(
      next_section_match_regex, contents[start_of_section_contents:])
    
    section_header = contents[start_of_section_header:end_of_section_header]
    if next_section_match:
      start_of_next_section_header = next_section_match.start(1)
      end_of_section_contents = (
        start_of_section_contents + start_of_next_section_header - 1)
      
      section_contents = contents[end_of_section_header:end_of_section_contents]
    else:
      section_contents = contents[end_of_section_header:]
  
  section_contents = section_contents.rstrip("\n")
  
  return section_header, section_contents


#===============================================================================


def _parse_sentence_indices(arg_str):
  sentence_indices_str = arg_str.split(":")
  sentence_indices = []
  for index_str in sentence_indices_str:
    try:
      index = int(index_str)
    except (ValueError, TypeError):
      index = None
    sentence_indices.append(index)
  
  return sentence_indices


def _get_sentences_from_section(section_header, section_contents, sentence_indices):
  if sentence_indices:
    sentences = re.split(r"(\.[ \n])", section_contents)
    
    if len(sentence_indices) == 1:
      section_sentences = sentences[sentence_indices[0]]
      if sentence_indices[0] < len(sentences) - 1:
        section_sentences += sentences[sentence_indices[0] + 1]
      
      return section_header, section_sentences
    elif len(sentence_indices) == 2:
      section_sentences = "" if sentence_indices[0] == 0 else "\n"
      sentence_index = sentence_indices[0]
      if not sentence_indices[1]:
        sentence_indices[1] = len(sentences)
      
      while sentence_index < sentence_indices[1]:
        section_sentences += sentences[sentence_index]
        if sentence_index < len(sentences) - 1:
          section_sentences += sentences[sentence_index + 1]
          sentence_index += 1
        sentence_index += 1
      
      return section_header, section_sentences
  
  return section_header, section_contents


def _strip_section_header(section_header, section_contents, should_strip_header):
  if should_strip_header:
    return "", section_contents
  else:
    return section_header, section_contents


class TagArgument(object):
  
  def __init__(self, tag_arg_match_pattern, parse_func, process_func):
    self.tag_arg_match_pattern = tag_arg_match_pattern
    self.parse_func = parse_func
    self.process_func = process_func
    
    self.parse_func_retvals = []


_TAG_ARGUMENTS = {
  "include-section": [
    TagArgument(
      r"[0-9]+:?[0-9]*", _parse_sentence_indices, _get_sentences_from_section),
    TagArgument(
      r"no-header", lambda arg_str: arg_str == "no-header", _strip_section_header)
  ]
}

#===============================================================================


def main(source_filepaths, dest_filepaths, insert_markdownify_tag=True):
  if len(source_filepaths) != len(dest_filepaths):
    print(
      "Lists of source and destination file paths are not the same length",
      file=sys.stderr)
    sys.exit(1)
  
  preprocess_contents(source_filepaths, dest_filepaths, insert_markdownify_tag)


if __name__ == "__main__":
  main(*sys.argv[1:])
