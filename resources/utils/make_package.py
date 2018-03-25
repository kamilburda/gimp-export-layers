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
This script creates a ZIP package for releases from the plug-in source.

This script requires the `pathspec` library (for matching file paths by
patterns): https://github.com/cpburnz/python-path-specification
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from export_layers import pygimplib
from future.builtins import *

import importlib
import io
import os
import re
import shutil
import subprocess
import tempfile
import sys
import zipfile

import git
import pathspec

from export_layers.pygimplib import pgconstants
from export_layers.pygimplib import pgpath
from export_layers.pygimplib import pgutils

import export_layers.config
export_layers.config.init()

pygimplib.config.LOG_MODE = pgconstants.LOG_NONE

pygimplib.init()

#===============================================================================

MODULE_DIRPATH = os.path.dirname(pgutils.get_current_module_filepath())
RESOURCES_DIRPATH = os.path.dirname(MODULE_DIRPATH)
PLUGINS_DIRPATH = pygimplib.config.PLUGINS_DIRPATH

OUTPUT_FILENAME_PREFIX = pygimplib.config.PLUGIN_NAME
OUTPUT_FILE_EXTENSION = "zip"

INCLUDE_LIST_FILEPATH = os.path.join(MODULE_DIRPATH, "make_package_included_files.txt")

GITHUB_PAGE_DIRPATH = os.path.join(RESOURCES_DIRPATH, "docs", "gh-pages")
GITHUB_PAGE_UTILS_DIRPATH = os.path.join(RESOURCES_DIRPATH, "docs", "GitHub_page")

#===============================================================================


def make_package(input_dirpath, output_filepath, version):
  temp_repo_files_dirpath = tempfile.mkdtemp()
  
  relative_filepaths_with_git_filters = (
    _prepare_repo_files_for_packaging(PLUGINS_DIRPATH, temp_repo_files_dirpath))
  
  _generate_translation_files(pygimplib.config.LOCALE_DIRPATH, version)

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
  
  _restore_repo_files(
    temp_repo_files_dirpath, PLUGINS_DIRPATH, relative_filepaths_with_git_filters)
  
  shutil.rmtree(temp_dirpath)
  shutil.rmtree(temp_repo_files_dirpath)
  _remove_pot_files(pygimplib.config.LOCALE_DIRPATH)


def _prepare_repo_files_for_packaging(
      repository_dirpath, dirpath_with_original_files_with_git_filters):
  repo = git.Repo(repository_dirpath)
  
  if repo.git.status("--porcelain"):
    print(("Repository contains local changes."
           " Please remove or commit changes before proceeding."),
          file=sys.stderr)
    exit(1)
  
  path_specs = _get_path_specs_with_git_filters_from_gitattributes(repository_dirpath)
  
  spec_obj = pathspec.PathSpec.from_lines(
    pathspec.patterns.gitwildmatch.GitWildMatchPattern, path_specs)
  
  relative_filepaths_with_git_filters = [
    match for match in spec_obj.match_tree(repository_dirpath)]
  
  # Move files with filters to a temporary location
  for relative_filepath in relative_filepaths_with_git_filters:
    src_filepath = os.path.join(repository_dirpath, relative_filepath)
    dest_filepath = os.path.join(
      dirpath_with_original_files_with_git_filters, relative_filepath)
    
    pgpath.make_dirs(os.path.dirname(dest_filepath))
    shutil.copy2(src_filepath, dest_filepath)
    os.remove(src_filepath)
  
  # Reset files with filters and activate smudge filters on them.
  for path_spec in path_specs:
    repo.git.checkout(path_spec)
  
  return relative_filepaths_with_git_filters


def _restore_repo_files(
      dirpath_with_original_files_with_git_filters, repository_dirpath,
      relative_filepaths_with_git_filters):
  for relative_filepath in relative_filepaths_with_git_filters:
    shutil.copy2(
      os.path.join(dirpath_with_original_files_with_git_filters, relative_filepath),
      os.path.join(repository_dirpath, relative_filepath))


def _get_path_specs_with_git_filters_from_gitattributes(repository_dirpath):
  path_specs = []
  
  with io.open(os.path.join(repository_dirpath, ".gitattributes")) as gitattributes_file:
    for line in gitattributes_file:
      match = re.search(r"\s*(.*?)\s+filter=", line)
      if match:
        path_specs.append(match.group(1))
  
  return path_specs


def _get_filtered_filepaths(dirpath, pattern_filepath):
  with io.open(
         pattern_filepath, "r", encoding=pgconstants.TEXT_FILE_ENCODING) as file_:
    spec_obj = pathspec.PathSpec.from_lines(
      pathspec.patterns.gitwildmatch.GitWildMatchPattern, file_)
  
  return [os.path.join(dirpath, match) for match in spec_obj.match_tree(dirpath)]


def _get_relative_filepaths(filepaths, root_dirpath):
  return [filepath[len(root_dirpath) + 1:] for filepath in filepaths]


def _generate_translation_files(source_dirpath, version):
  _remove_pot_files(source_dirpath)
  
  _generate_pot_file(source_dirpath, version)
  _generate_mo_files(source_dirpath)


def _generate_pot_file(source_dirpath, version):
  orig_cwd = os.getcwdu()
  os.chdir(source_dirpath)
  subprocess.call(["./generate_pot.sh", version])
  os.chdir(orig_cwd)


def _generate_mo_files(source_dirpath):
  orig_cwd = os.getcwdu()
  os.chdir(source_dirpath)
  
  for root_dirpath, unused_, filenames in os.walk(source_dirpath):
    for filename in filenames:
      if (os.path.isfile(os.path.join(root_dirpath, filename))
          and filename.endswith(".po")):
        po_file = os.path.join(root_dirpath, filename)
        language = pgpath.split_path(root_dirpath)[-2]
        subprocess.call(["./generate_mo.sh", po_file, language])
  
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


def _create_user_docs(dirpath):
  sys.path.append(MODULE_DIRPATH)
  create_user_docs_module = importlib.import_module("create_user_docs")
  
  create_user_docs_module.main(
    GITHUB_PAGE_UTILS_DIRPATH, GITHUB_PAGE_DIRPATH, dirpath)


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


def main(destination_dirpath=None):
  output_filename = "{0}-{1}.{2}".format(
    OUTPUT_FILENAME_PREFIX, pygimplib.config.PLUGIN_VERSION, OUTPUT_FILE_EXTENSION)
  
  if not destination_dirpath:
    output_filepath = os.path.join(MODULE_DIRPATH, output_filename)
  else:
    pgpath.make_dirs(destination_dirpath)
    output_filepath = os.path.join(destination_dirpath, output_filename)
  
  make_package(PLUGINS_DIRPATH, output_filepath, pygimplib.config.PLUGIN_VERSION)
  
  print("Package successfully created:", output_filepath)


if __name__ == "__main__":
  main(sys.argv[1] if len(sys.argv) > 1 else None)
