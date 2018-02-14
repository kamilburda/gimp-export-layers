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
This script creates a ZIP package for releases from the plug-in source.

This script requires the `pathspec` library (for matching file paths by
patterns): https://github.com/cpburnz/python-path-specification
"""

from __future__ import absolute_import, division, print_function, unicode_literals
import pygimplib
from future.builtins import *

import importlib
import io
import os
import shutil
import subprocess
import tempfile
import sys
import zipfile

import pathspec

from pygimplib import pgconstants
from pygimplib import pgpath
from pygimplib import pgutils

import export_layers.config
export_layers.config.init()

pygimplib.init()

#===============================================================================

MODULE_DIRPATH = os.path.dirname(pgutils.get_current_module_filepath())
RESOURCES_DIRPATH = os.path.dirname(MODULE_DIRPATH)
PLUGINS_DIRPATH = os.path.dirname(RESOURCES_DIRPATH)

OUTPUT_FILENAME_PREFIX = pygimplib.config.PLUGIN_NAME
OUTPUT_FILE_EXTENSION = "zip"

INCLUDE_LIST_FILEPATH = os.path.join(MODULE_DIRPATH, "make_package_included_files.txt")

GITHUB_PAGE_DIRPATH = os.path.join(RESOURCES_DIRPATH, "docs", "gh-pages")
GITHUB_PAGE_SCRIPTS_DIRPATH = os.path.join(RESOURCES_DIRPATH, "docs", "GitHub_page")

#===============================================================================


def make_package(input_dirpath, output_filepath, version):
  _generate_pot_file(pygimplib.config.LOCALE_DIRPATH, version)

  temp_dirpath = tempfile.mkdtemp()
  
  _create_user_docs(temp_dirpath)
  
  input_filepaths = _get_filtered_filepaths(input_dirpath, INCLUDE_LIST_FILEPATH)
  user_docs_filepaths = _get_filtered_filepaths(temp_dirpath, INCLUDE_LIST_FILEPATH)
  
  relative_filepaths = (
    _get_relative_filepaths(input_filepaths, input_dirpath)
    + _get_relative_filepaths(user_docs_filepaths, temp_dirpath))
  
  temp_filepaths = [
    os.path.join(temp_dirpath, relative_filepath)
    for relative_filepath in relative_filepaths]
  
  _copy_files_to_temp_filepaths(input_filepaths, temp_filepaths)
  
  _set_permissions(temp_dirpath, 0o755)
  
  _create_package_file(output_filepath, temp_filepaths, relative_filepaths)
  
  shutil.rmtree(temp_dirpath)
  _remove_pot_files(pygimplib.config.LOCALE_DIRPATH)


def _get_filtered_filepaths(dirpath, pattern_filepath):
  with io.open(
         pattern_filepath, "r", encoding=pgconstants.TEXT_FILE_ENCODING) as file_:
    spec = pathspec.PathSpec.from_lines(
      pathspec.patterns.gitwildmatch.GitWildMatchPattern, file_)
  
  return [os.path.join(dirpath, match) for match in spec.match_tree(dirpath)]


def _get_relative_filepaths(filepaths, root_dirpath):
  return [filepath[len(root_dirpath) + 1:] for filepath in filepaths]


def _generate_pot_file(source_dirpath, version):
  _remove_pot_files(source_dirpath)
  
  orig_cwd = os.getcwdu()
  os.chdir(source_dirpath)
  subprocess.call(["./generate_pot.sh", version])
  os.chdir(orig_cwd)


def _remove_pot_files(source_dirpath):
  for filename in os.listdir(source_dirpath):
    if os.path.isfile(os.path.join(source_dirpath, filename)):
      if filename.endswith(".pot"):
        os.remove(os.path.join(source_dirpath, filename))


def _copy_files_to_temp_filepaths(filepaths, temp_filepaths):
  for src_filepath, temp_filepath in zip(filepaths, temp_filepaths):
    dirpath = os.path.dirname(temp_filepath)
    if not os.path.exists(dirpath):
      pgpath.make_dirs(dirpath)
    shutil.copy2(src_filepath, temp_filepath)


def _create_user_docs(temp_dirpath):
  sys.path.append(MODULE_DIRPATH)
  create_user_docs_module = importlib.import_module("create_user_docs")
  
  create_user_docs_module.main(
    GITHUB_PAGE_SCRIPTS_DIRPATH, GITHUB_PAGE_DIRPATH, temp_dirpath)


def _set_permissions(dirpath, permissions):
  """
  Set file permissions on all files and subdirectories in the given directory
  path.
  """
  
  for root, subdirpaths, filenames in os.walk(dirpath):
    for subdirpath in subdirpaths:
      os.chmod(os.path.join(root, subdirpath), permissions)
    for filename in filenames:
      os.chmod(os.path.join(root, filename), permissions)


def _create_package_file(package_filepath, input_filepaths, output_filepaths):
  with zipfile.ZipFile(package_filepath, "w", zipfile.ZIP_STORED) as package_file:
    for input_filepath, output_filepath in zip(input_filepaths, output_filepaths):
      package_file.write(input_filepath, output_filepath)


#===============================================================================


def main():
  output_filepath = "{0}-{1}.{2}".format(
    OUTPUT_FILENAME_PREFIX, pygimplib.config.PLUGIN_VERSION, OUTPUT_FILE_EXTENSION)
  
  make_package(PLUGINS_DIRPATH, output_filepath, pygimplib.config.PLUGIN_VERSION)
  
  print("Package successfully created:", os.path.join(PLUGINS_DIRPATH, output_filepath))


if __name__ == "__main__":
  main()
