#! /usr/bin/env python
#
#-------------------------------------------------------------------------------
#
# This file is part of Export Layers.
#
# Copyright (C) 2013, 2014 khalim19 <khalim19@gmail.com>
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
#
#-------------------------------------------------------------------------------

"""
This script creates a .zip package for releases from the plug-in source.

This script uses `pathspec` library for matching files using patterns:
  https://github.com/cpburnz/python-path-specification
"""

#===============================================================================

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division

str = unicode

#===============================================================================

import os
import sys
import inspect

import subprocess
import tempfile
import shutil
import zipfile

import pathspec

from export_layers import constants

from export_layers.pylibgimpplugin import pgpath

#===============================================================================

RESOURCES_PATH = os.path.dirname(inspect.getfile(inspect.currentframe()))
PLUGINS_PATH = os.path.dirname(RESOURCES_PATH)

OUTPUT_FILENAME_PREFIX = "export-layers"
OUTPUT_FILENAME_SUFFIX = ".zip"

INCLUDE_LIST_FILENAME = "./make_package_included_files.txt"

FILENAMES_TO_RENAME = {
  "README.md" : "Readme.txt",
  "CHANGELOG.md" : "Changelog.txt",
  "Readme for Translators.md" : "Readme for Translators.txt",
}

#===============================================================================


def process_readme_file(readme_file):
  readme_file_copy = readme_file + '.bak'
  num_leading_spaces = 4
  
  shutil.copy2(readme_file, readme_file_copy)
  
  with open(readme_file, 'r') as f, \
       open(readme_file_copy, 'w') as temp_f:
    line = f.readline()
    while line:
      if not line.strip():
        # Write back the empty/whitespace-only line.
        temp_f.write(line)
        
        # Trim leading spaces from subsequent lines.
        line = f.readline()
        while line.startswith(' ' * num_leading_spaces):
          temp_f.write(line.lstrip(' '))
          line = f.readline()
      else:
        temp_f.write(line)
        line = f.readline()
  
  shutil.copy2(readme_file_copy, readme_file)
  os.remove(readme_file_copy)


FILES_TO_PROCESS = {
  FILENAMES_TO_RENAME["README.md"] : process_readme_file
}

#===============================================================================


def _get_filtered_files(directory, pattern_file):
  with open(pattern_file, 'r') as file_:
    spec = pathspec.PathSpec.from_lines(pathspec.GitIgnorePattern, file_)
  
  return [os.path.join(directory, match) for match in spec.match_tree(directory)]

#===============================================================================


def make_package(input_directory, output_file, version):
  
  def _set_permissions(path, perms):
    """
    Set file permissions on all files and subdirectories in a given path.
    """
    
    for root, dirs, files in os.walk(path):
      for dir_ in dirs:
        os.chmod(os.path.join(root, dir_), perms)
      for file_ in files:
        os.chmod(os.path.join(root, file_), perms)
  
  def _generate_pot_file(source_dir, version):
    for file_ in os.listdir(source_dir):
      if os.path.isfile(os.path.join(source_dir, file_)):
        if file_.endswith(".pot"):
          os.remove(os.path.join(source_dir, file_))
     
    orig_cwd = os.getcwdu()
    os.chdir(source_dir)
    subprocess.call(["./generate_pot.sh", version])
    os.chdir(orig_cwd)
  
  _generate_pot_file(constants.LOCALE_PATH, version)
  
  files = _get_filtered_files(input_directory, INCLUDE_LIST_FILENAME)
  files_relative_paths = [file_[len(input_directory) + 1:] for file_ in files]
  
  for i, rel_file_path in enumerate(files_relative_paths):
    filename = os.path.basename(rel_file_path)
    if filename in FILENAMES_TO_RENAME:
      files_relative_paths[i] = os.path.join(os.path.dirname(rel_file_path), FILENAMES_TO_RENAME[filename])
  
  temp_dir = tempfile.mkdtemp()
  temp_files = [os.path.join(temp_dir, file_rel_path) for file_rel_path in files_relative_paths]
  
  for src_file, temp_file in zip(files, temp_files):
    dirname = os.path.dirname(temp_file)
    if not os.path.exists(dirname):
      pgpath.make_dirs(dirname)
    shutil.copy2(src_file, temp_file)
  
  _set_permissions(temp_dir, 0o755)
  
  for temp_file in temp_files:
    filename = os.path.basename(temp_file)
    if filename in FILES_TO_PROCESS:
      FILES_TO_PROCESS[filename](temp_file)
  
  with zipfile.ZipFile(output_file, "w", zipfile.ZIP_STORED) as zip_file:
    for temp_file, file_ in zip(temp_files, files_relative_paths):
      zip_file.write(temp_file, file_)
  
  shutil.rmtree(temp_dir)
  
#===============================================================================

if __name__ == "__main__":
  output_file = OUTPUT_FILENAME_PREFIX + '-' + constants.PLUGIN_VERSION + OUTPUT_FILENAME_SUFFIX
  
  if os.name == 'nt':
    print(os.path.basename(sys.argv[0]) + ": Error: Can't run script on Windows " +
          "because Unix-style permissions need to be set",
          file=sys.stderr)
    sys.exit(1)
  
  make_package(PLUGINS_PATH, output_file, constants.PLUGIN_VERSION)
