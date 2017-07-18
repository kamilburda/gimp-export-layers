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
# along with Export Layers.  If not, see <http://www.gnu.org/licenses/>.

"""
This script pre-processes documents (readmes, sites), replacing specially
formatted lines containing a command and arguments with the corresponding
content.

Currently only the following command is provided:
* `{% include-section <relative file path>:<section>[arguments]... %}`:
  replaces the line with the section from the specified file. For example,
  `{% include-section README.md:Features %}` replaces the line with the
  contents of the section "Features" from the file `README.md` in the same
  directory as the file containing this line.
  
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


def preprocess_contents(source_filepaths, dest_filepaths):
  for source_filepath, dest_filepath in zip(source_filepaths, dest_filepaths):
    with io.open(source_filepath, "r", encoding=pgconstants.TEXT_FILE_ENCODING) as file_:
      source_file_contents = file_.read()
    
    preprocessed_contents = _preprocess_contents(source_filepath, source_file_contents)
    
    with io.open(dest_filepath, "w", encoding=pgconstants.TEXT_FILE_ENCODING) as file_:
      file_.writelines(preprocessed_contents)


def _preprocess_contents(source_filepath, contents):
  for match in list(re.finditer(r"( *)(\{% include-section (.*?) %\})", contents)):
    token_args = _parse_token_args(source_filepath, "include-section", match.group(3))
    section = _process_token_args("include-section", token_args)
    
    leading_spacing = match.group(1)
    dest_contents = (
      "{% capture markdown-insert %}\n"
      + section + "\n" + leading_spacing
      + "{% endcapture %}"
      + "\n" + leading_spacing + "{{ markdown-insert | markdownify }}")
    contents = contents.replace(match.group(2), dest_contents, 1)
  
  return contents


def _parse_token_args(source_filepath, token_name, token_args_str):
  args_match = re.search(r"\[.*\]$", token_args_str)
  if args_match:
    relative_document_filepath = (
      token_args_str[:len(token_args_str) - len(args_match.group())])
  else:
    relative_document_filepath = token_args_str
  
  document_relative_filepath_components = relative_document_filepath.strip('"').split("/")
  if ":" in document_relative_filepath_components[-1]:
    document_relative_filepath_components[-1], document_section_name = (
      document_relative_filepath_components[-1].split(":"))
  else:
    document_section_name = ""
  
  document_filepath = os.path.normpath(
    os.path.join(
      os.path.dirname(source_filepath), *document_relative_filepath_components))
  
  print(document_filepath)
  
  token_args = [document_filepath, document_section_name]
  
  for token_arg_item in _TOKEN_ARG_FUNCS[token_name]:
    token_arg_item.parse_func_retvals = []
  
  if args_match:
    for token_arg_item in _TOKEN_ARG_FUNCS[token_name]:
      token_arg_match = re.search(
        r"\[(" + token_arg_item.token_arg_match_pattern + r")\]", args_match.group())
      if token_arg_match:
        token_arg_item.parse_func_retvals = [
          token_arg_item.parse_func(token_arg_match.group(1))]
  
  return token_args


def _process_token_args(token_name, token_args):
  document_filepath = token_args[0]
  section_name = token_args[1]
  with io.open(
         document_filepath, "r", encoding=pgconstants.TEXT_FILE_ENCODING) as document:
    document_contents = document.read()
    if section_name:
      section_header, section_contents = _find_section(document_contents, section_name)
    else:
      section_header, section_contents = "", document_contents
  
  for token_arg_item in _TOKEN_ARG_FUNCS[token_name]:
    if token_arg_item.parse_func_retvals:
      section_header, section_contents = token_arg_item.process_func(
        section_header, section_contents, *token_arg_item.parse_func_retvals)
  
  return section_header + section_contents


def _find_section(contents, section_name):
  section_header = ""
  section_contents = ""
  
  match_section = re.search("(" + section_name + ")" + r"\n[=-]+\n", contents)
  if match_section:
    start_of_section_contents = match_section.end() + 1
    next_section = re.search(r".*?\n[=-]+\n", contents[start_of_section_contents:])
    
    section_header = contents[match_section.start():match_section.end()]
    if next_section:
      section_contents = contents[
        match_section.end():start_of_section_contents + next_section.start() - 1]
    else:
      section_contents = contents[match_section.end():]
  
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


class TokenArgItem(object):
  
  def __init__(self, token_arg_match_pattern, parse_func, process_func):
    self.token_arg_match_pattern = token_arg_match_pattern
    self.parse_func = parse_func
    self.process_func = process_func
    
    self.parse_func_retvals = []


_TOKEN_ARG_FUNCS = {
  "include-section": [
    TokenArgItem(
      r"[0-9]+:?[0-9]*", _parse_sentence_indices, _get_sentences_from_section),
    TokenArgItem(
      r"no-header", lambda arg_str: arg_str == "no-header", _strip_section_header)
  ]
}

#===============================================================================


def main(source_dirpath, dest_dirpath):
  source_relative_filepaths = []
  for root, unused_, filenames in os.walk(source_dirpath):
    for filename in filenames:
      source_relative_filepaths.append(
        os.path.normpath(os.path.join(os.path.relpath(root, source_dirpath), filename)))
  
  preprocess_contents(
    [os.path.join(source_dirpath, relative_filepath)
     for relative_filepath in source_relative_filepaths],
    [os.path.join(dest_dirpath, relative_filepath)
     for relative_filepath in source_relative_filepaths])


if __name__ == "__main__":
  main(*sys.argv[:2])
