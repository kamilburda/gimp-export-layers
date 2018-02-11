#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
This script processes HTML files from a Jekyll-generated page so that they can
be used without running the Jekyll server (e.g. included in release packages
as user documentation).
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import collections
import io
import os
import pathlib
import re
import shutil
import sys

import HTMLParser
try:
  import xml.etree.cElementTree as ElementTree
except ImportError:
  import xml.etree.ElementTree as ElementTree

import yaml

#===============================================================================

FILE_ENCODING = "utf-8"

FILENAMES_TO_REMOVE = [
  "Gemfile",
  "Gemfile.lock",
  "robots.txt",
  "sitemap.xml",
]

RELATIVE_PATHS_TO_MOVE = collections.OrderedDict([
  ("index.html", "Readme.html"),
  ("favicon.ico", "docs/favicon.ico"),
  ("assets", "docs/assets"),
  ("images", "docs/images"),
  ("sections", "docs/sections"),
])

HTML_DOCTYPE_DECLARATION = "<!DOCTYPE html>"
INDEX_HTML = "index.html"

HTML_VOID_ELEMENTS = set([
  "area", "base", "br", "col", "embed", "hr", "img", "input", "keygen", "link",
  "menuitem", "meta", "param", "source", "track", "wbr"
])

HTML_ELEMENTS_WITH_URLS = collections.OrderedDict([
  ("a", ["href"]),
  ("applet", ["codebase"]),
  ("area", ["href"]),
  ("base", ["href"]),
  ("blockquote", ["cite"]),
  ("body", ["background"]),
  ("del", ["cite"]),
  ("form", ["action"]),
  ("frame", ["longdesc", "src"]),
  ("head", ["profile"]),
  ("iframe", ["longdesc", "src"]),
  ("img", ["longdesc", "src", "usemap"]),
  ("input", ["src", "usemap"]),
  ("ins", ["cite"]),
  ("link", ["href"]),
  ("object", ["classid", "codebase", "data", "usemap"]),
  ("q", ["cite"]),
  ("script", ["src"]),
  ("audio", ["src"]),
  ("button", ["formaction"]),
  ("command", ["icon"]),
  ("embed", ["src"]),
  ("html", ["manifest"]),
  ("input", ["formaction"]),
  ("source", ["src"]),
  ("video", ["poster", "src"]),
])

PAGE_CONFIG_FILENAME = "_config.yml"
PAGE_CONFIG = None


class LocalJekyllHTMLParser(HTMLParser.HTMLParser):
  
  def __init__(self):
    HTMLParser.HTMLParser.__init__(self)
    self.tree_builder = ElementTree.TreeBuilder()
    self.tree = None
  
  def handle_starttag(self, tag, attributes):
    self.tree_builder.start(tag, collections.OrderedDict(attributes))
    if tag in HTML_VOID_ELEMENTS:
      self.tree_builder.end(tag)
  
  def handle_endtag(self, tag):
    self.tree_builder.end(tag)
  
  def handle_startendtag(self, tag, attributes):
    self.tree_builder.start(tag, collections.OrderedDict(attributes))
    self.tree_builder.end(tag)

  def handle_data(self, data):
    self.tree_builder.data(data)

  def close(self):
    HTMLParser.HTMLParser.close(self)
    self.tree = ElementTree.ElementTree(self.tree_builder.close())


def find_all_html_elements_recursive(html_tree, match):
  elements_to_traverse = [html_tree.getroot()]
  matches = []
  
  while elements_to_traverse:
    element = elements_to_traverse.pop(0)
    
    matches.extend(element.findall(match))
    
    elements_to_traverse.extend(list(element))
  
  return matches
  

#===============================================================================


def get_html_filepaths(site_dirpath):
  html_filepaths = []
  
  for root, unused_, filenames in os.walk(site_dirpath):
    for filename in filenames:
      if filename.endswith(".html"):
        html_filepaths.append(os.path.join(root, filename))
  
  return html_filepaths


def remove_redundant_files(site_dirpath):
  for filename in FILENAMES_TO_REMOVE:
    filepath_to_remove = os.path.join(site_dirpath, filename)
    if os.path.isfile(filepath_to_remove):
      os.remove(filepath_to_remove)


def remove_baseurl_in_url_attributes(html_relative_filepath, html_tree):
  html_relative_filepath_components = pathlib.Path(html_relative_filepath).parts
  
  if len(html_relative_filepath_components) == 0:
    return
  
  if len(html_relative_filepath_components) == 1:
    new_baseurl = "."
  else:
    new_baseurl = "../" * (len(html_relative_filepath_components) - 1)
    new_baseurl = new_baseurl.rstrip("/")
  
  def _get_relative_url_without_baseurl(url_attribute_value):
    new_url_attribute_value = url_attribute_value
    new_url_attribute_value = re.sub(
      r"^" + re.escape(PAGE_CONFIG["baseurl"]), new_baseurl, new_url_attribute_value)
    new_url_attribute_value = re.sub(r"/$", r"/" + INDEX_HTML, new_url_attribute_value)
    
    return new_url_attribute_value
  
  _modify_url_attributes(html_tree, _get_relative_url_without_baseurl)


def rename_paths_in_url_attributes(
      relative_paths_to_rename, html_relative_filepath, html_tree):
  """
  Rename paths in URL attributes according to the `relative_paths_to_rename`
  parameter.
  """
  
  def _get_renamed_url(url_attribute_value):
    is_url_attribute_relative_path = url_attribute_value.startswith(".")
    
    if not is_url_attribute_relative_path:
      return url_attribute_value
    
    html_relative_dirpath = os.path.dirname(html_relative_filepath)
    
    resolved_relative_url = pathlib.Path(
      os.path.relpath(
        os.path.normpath(
          os.path.join(html_relative_dirpath, url_attribute_value)),
        os.path.dirname(html_relative_dirpath))
    ).as_posix()
    
    renamed_resolved_relative_url = _rename_resolved_relative_path(
      resolved_relative_url)
    
    if renamed_resolved_relative_url is None:
      return url_attribute_value
    
    renamed_html_relative_dirpath = _rename_resolved_relative_path(
      html_relative_dirpath)
    
    if renamed_html_relative_dirpath is None:
      renamed_html_relative_dirpath = html_relative_dirpath
    
    new_url_attribute_value = os.path.relpath(
      renamed_resolved_relative_url, renamed_html_relative_dirpath)
    
    if not new_url_attribute_value.startswith("."):
      new_url_attribute_value = os.path.join(".", new_url_attribute_value)
    
    new_url_attribute_value = pathlib.Path(new_url_attribute_value).as_posix()
    
    return new_url_attribute_value
  
  def _rename_resolved_relative_path(resolved_relative_path):
    matching_relative_paths_to_rename = [
      (orig_relative_path, renamed_relative_path)
      for orig_relative_path, renamed_relative_path in relative_paths_to_rename.items()
      if resolved_relative_path.startswith(orig_relative_path)]
    
    if not matching_relative_paths_to_rename:
      return None
    
    orig_relative_path, renamed_relative_path = matching_relative_paths_to_rename[0]
    
    renamed_resolved_relative_path = re.sub(
      re.escape(orig_relative_path), renamed_relative_path,
      resolved_relative_path, count=1)
    
    return renamed_resolved_relative_path
  
  _modify_url_attributes(html_tree, _get_renamed_url)


def _modify_url_attributes(html_tree, get_new_url_attribute_value_func):
  for tag, attributes in HTML_ELEMENTS_WITH_URLS.items():
    elements_to_fix = find_all_html_elements_recursive(html_tree, tag)
    
    for element in elements_to_fix:
      for attribute in attributes:
        attribute_value = element.get(attribute)
        if attribute_value is not None:
          element.set(attribute, get_new_url_attribute_value_func(attribute_value))


def reorganize_files(site_dirpath):
  """
  Place all files except the top HTML file in one folder. Rename files for
  improved readability.
  """
  
  for orig_relative_path, renamed_relative_path in RELATIVE_PATHS_TO_MOVE.items():
    orig_path = os.path.normpath(os.path.join(site_dirpath, orig_relative_path))
    renamed_path = os.path.normpath(os.path.join(site_dirpath, renamed_relative_path))
    
    if not os.path.exists(os.path.dirname(renamed_path)):
      os.makedirs(os.path.dirname(renamed_path))
    
    shutil.move(orig_path, renamed_path)


def write_to_html_file(html_tree, html_file):
  html_file.write(bytes(HTML_DOCTYPE_DECLARATION) + b"\n")
  html_tree.write(html_file, encoding=FILE_ENCODING, xml_declaration=False, method="html")


#===============================================================================


def main(site_dirpath, page_config_filepath):
  global PAGE_CONFIG
  
  with io.open(page_config_filepath, "r", encoding=FILE_ENCODING) as page_config_file:
    PAGE_CONFIG = yaml.load(page_config_file.read())
  
  remove_redundant_files(site_dirpath)
  
  for html_filepath in get_html_filepaths(site_dirpath):
    parser = LocalJekyllHTMLParser()
    
    with io.open(html_filepath, "r", encoding=FILE_ENCODING) as html_file:
      parser.feed(html_file.read())
    
    parser.close()
    
    html_relative_filepath = os.path.relpath(html_filepath, site_dirpath)
    
    remove_baseurl_in_url_attributes(html_relative_filepath, parser.tree)
    rename_paths_in_url_attributes(
      RELATIVE_PATHS_TO_MOVE, html_relative_filepath, parser.tree)
    
    with io.open(html_filepath, "wb") as html_file:
      write_to_html_file(parser.tree, html_file)
  
  reorganize_files(site_dirpath)


if __name__ == "__main__":
  main(sys.argv[1], sys.argv[2])
