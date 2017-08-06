#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
This script generates local HTML documentation from a Jekyll-generated page.

To achieve this, the `_site` directory of a Jekyll-generated page is rendered
locally without having to run the Jekyll server.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import collections
import io
import os
import pathlib
import re
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


def remove_redundant_files(site_dirpath):
  for filename in FILENAMES_TO_REMOVE:
    filepath_to_remove = os.path.join(site_dirpath, filename)
    if os.path.isfile(filepath_to_remove):
      os.remove(filepath_to_remove)


def fix_links_in_html_file(html_relative_filepath, html_tree):
  html_relative_filepath_components = pathlib.Path(html_relative_filepath).parts
  
  if len(html_relative_filepath_components) == 0:
    return
  
  if len(html_relative_filepath_components) == 1:
    new_baseurl = "."
  else:
    new_baseurl = "../" * (len(html_relative_filepath_components) - 1)
    new_baseurl = new_baseurl.rstrip("/")
  
  for tag, attributes in HTML_ELEMENTS_WITH_URLS.items():
    elements_to_fix = find_all_html_elements_recursive(html_tree, tag)
    
    for element in elements_to_fix:
      for attribute in attributes:
        href = element.get(attribute)
        if href is not None:
          new_href = href
          new_href = re.sub(
            r"^" + re.escape(PAGE_CONFIG["baseurl"]), new_baseurl, new_href)
          new_href = re.sub(r"/$", r"/" + INDEX_HTML, new_href)
          
          element.set(attribute, new_href)


def get_html_filepaths(site_dirpath):
  html_filepaths = []
  
  for root, unused_, filenames in os.walk(site_dirpath):
    for filename in filenames:
      if filename.endswith(".html"):
        html_filepaths.append(os.path.join(root, filename))
  
  return html_filepaths


def reorganize_files(site_dirpath):
  """
  Place all files except `index.html` in one folder.
  """
  
  pass


def write_to_html_file(html_tree, html_file):
  html_file.write(bytes(HTML_DOCTYPE_DECLARATION) + b"\n")
  html_tree.write(html_file, encoding=FILE_ENCODING, xml_declaration=False, method="html")


#===============================================================================


def main(site_dirpath):
  global PAGE_CONFIG
  
  page_config_filepath = os.path.join(os.path.dirname(site_dirpath), PAGE_CONFIG_FILENAME)
  with io.open(page_config_filepath, "r") as page_config_file:
    PAGE_CONFIG = yaml.load(page_config_file.read())
  
  remove_redundant_files(site_dirpath)
  
  reorganize_files(site_dirpath)
  
  for html_filepath in get_html_filepaths(site_dirpath):
    parser = LocalJekyllHTMLParser()
    
    with io.open(html_filepath, "r", encoding=FILE_ENCODING) as html_file:
      parser.feed(html_file.read())
    
    parser.close()
    
    fix_links_in_html_file(os.path.relpath(html_filepath, site_dirpath), parser.tree)
    
    with io.open(html_filepath, "wb") as html_file:
      write_to_html_file(parser.tree, html_file)


if __name__ == "__main__":
  main(sys.argv[1])
