#! /usr/bin/env python
#
#-------------------------------------------------------------------------------
#
# This file is part of Export Layers.
#
# Copyright (C) 2013-2015 khalim19 <khalim19@gmail.com>
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

This script requires `pathspec` library for matching files using patterns:
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
import re
import inspect

import subprocess
import tempfile
import shutil
import zipfile

import pathspec

from export_layers import constants

from export_layers.pygimplib import pgpath

#===============================================================================

RESOURCES_PATH = os.path.dirname(inspect.getfile(inspect.currentframe()))
PLUGINS_PATH = os.path.dirname(RESOURCES_PATH)

OUTPUT_FILENAME_PREFIX = "export-layers"
OUTPUT_FILENAME_SUFFIX = ".zip"

INCLUDE_LIST_FILENAME = "./make_package_included_files.txt"

FILENAMES_TO_RENAME = {
  "README.md": "Readme.txt",
  "CHANGELOG.md": "Changelog.txt",
  "Readme for Translators.md": "Readme for Translators.txt",
}

NUM_LEADING_SPACES_TO_TRIM = 4

#===============================================================================


def _prepare_files(file_to_read, file_to_write):
  file_to_read.seek(0)
  file_to_write.seek(0)
  file_to_write.truncate()


def _trim_leading_spaces(file_to_read, file_to_write, num_leading_spaces):
  line = file_to_read.readline()
  while line:
    if not line.strip():
      # Write back the empty/whitespace-only line.
      file_to_write.write(line)
      
      # Trim leading spaces from subsequent lines.
      line = file_to_read.readline()
      while line.startswith(' ' * num_leading_spaces):
        file_to_write.write(line.lstrip(' '))
        line = file_to_read.readline()
    else:
      file_to_write.write(line)
      line = file_to_read.readline()


def _rename_filenames_inside_file(file_to_read, file_to_write, filenames_to_rename):
  """
  Rename the filenames inside the file that were or will be renamed using the
  `filenames_to_rename` dict.
  """
  
  filenames_to_rename_patterns = {}
  for src_filename, dest_filename in filenames_to_rename.items():
    src_filename_pattern = re.escape(src_filename).replace('\\ ', "\\s")
    filenames_to_rename_patterns[src_filename_pattern] = dest_filename
  
  for line in file_to_read:
    processed_line = line
    for src_filename_pattern, dest_filename in filenames_to_rename_patterns.items():
      processed_line = re.sub(src_filename_pattern, lambda match: dest_filename, processed_line)
    file_to_write.write(processed_line)


def process_file(filename, *process_functions_and_args):
  temp_dir = tempfile.mkdtemp()
  temp_filename_copy = os.path.join(temp_dir, "temp")
  shutil.copy2(filename, temp_filename_copy)
  
  temp_file_copy = open(temp_filename_copy, 'r+')
  temp_file = tempfile.NamedTemporaryFile('r+', dir=temp_dir, delete=False)
  
  last_modified_filename = None
  file_to_read = temp_file_copy
  file_to_write = temp_file
  for function_and_args in process_functions_and_args:
    _prepare_files(file_to_read, file_to_write)
    
    process_function = function_and_args[0]
    process_function_additional_args = function_and_args[1:]
    process_function(file_to_read, file_to_write, *process_function_additional_args)
    
    last_modified_filename = file_to_write.name
    file_to_read, file_to_write = file_to_write, file_to_read
  
  temp_file_copy.close()
  temp_file.close()
  
  shutil.copy2(last_modified_filename, filename)
  
  os.remove(temp_filename_copy)
  os.remove(temp_file.name)
  os.rmdir(temp_dir)


# key: filename
# value: list of (function, additional function arguments) as arguments to `process_file`
FILES_TO_PROCESS = {
  FILENAMES_TO_RENAME["README.md"]: [
    (_trim_leading_spaces, NUM_LEADING_SPACES_TO_TRIM),
    (_rename_filenames_inside_file, FILENAMES_TO_RENAME)
  ]
}


#===============================================================================


def _print_program_message(message, stream=sys.stdout):
  print(os.path.basename(sys.argv[0]) + ": " + message, file=stream)


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
    
    if os.name == "nt":
      _print_program_message("Warning: Cannot set Unix-style permissions on Windows", sys.stderr)
      return
    
    for root, dirs, files in os.walk(path):
      for dir_ in dirs:
        os.chmod(os.path.join(root, dir_), perms)
      for file_ in files:
        os.chmod(os.path.join(root, file_), perms)
  
  def _generate_pot_file(source_dir, version):
    if os.name == "nt":
      _print_program_message("Warning: Cannot generate .pot file on Windows", sys.stderr)
      return
    
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
      process_file(temp_file, *FILES_TO_PROCESS[filename])
  
  with zipfile.ZipFile(output_file, "w", zipfile.ZIP_STORED) as zip_file:
    for temp_file, file_ in zip(temp_files, files_relative_paths):
      zip_file.write(temp_file, file_)
  
  shutil.rmtree(temp_dir)


#===============================================================================


if __name__ == "__main__":
  output_file = OUTPUT_FILENAME_PREFIX + '-' + constants.PLUGIN_VERSION + OUTPUT_FILENAME_SUFFIX
  make_package(PLUGINS_PATH, output_file, constants.PLUGIN_VERSION)
