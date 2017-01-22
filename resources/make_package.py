#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of Export Layers.
#
# Copyright (C) 2013-2016 khalim19 <khalim19@gmail.com>
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

"""
This script creates a ZIP package for releases from the plug-in source.

This script requires the `pathspec` library (for matching files by patterns):
https://github.com/cpburnz/python-path-specification
"""

from __future__ import absolute_import, division, print_function, unicode_literals
import export_layers.pygimplib as pygimplib
from future.builtins import *

import io
import os
import re
import shutil
import subprocess
import tempfile
import sys
import zipfile

import pathspec

import export_layers.config
from export_layers.pygimplib import pgconstants
from export_layers.pygimplib import pgpath
from export_layers.pygimplib import pgutils

#===============================================================================

export_layers.config.init()

pygimplib.init()

RESOURCES_PATH = os.path.dirname(pgutils.get_current_module_file_path())
PLUGINS_PATH = os.path.dirname(RESOURCES_PATH)

OUTPUT_FILENAME_PREFIX = "export-layers"
OUTPUT_FILENAME_EXTENSION = "zip"

INCLUDE_LIST_FILENAME = "./make_package_included_files.txt"

FILENAMES_TO_RENAME = {
  "README.md": "Readme.txt",
  "CHANGELOG.md": "Changelog.txt",
  "Readme for Translators.md": "Readme for Translators.txt",
}

NUM_LEADING_SPACES_TO_TRIM = 4

#===============================================================================


def process_file(file_path, *process_functions_and_args):
  
  def _prepare_files(file_to_read, file_to_write):
    file_to_read.seek(0)
    file_to_write.seek(0)
    file_to_write.truncate()
  
  def _create_temp_file(temp_dir, mode, encoding):
    temp_file = tempfile.NamedTemporaryFile(mode, dir=temp_dir, delete=False)
    temp_file.close()
    temp_file = io.open(temp_file.name, mode, encoding=encoding)
    
    return temp_file
  
  temp_dir = tempfile.mkdtemp()
  temp_filename_copy = os.path.join(temp_dir, "temp")
  shutil.copy2(file_path, temp_filename_copy)
  
  temp_file_copy = io.open(
    temp_filename_copy, "r+", encoding=pgconstants.TEXT_FILE_CHARACTER_ENDOCING)
  temp_file = _create_temp_file(temp_dir, "r+", pgconstants.TEXT_FILE_CHARACTER_ENDOCING)
  
  last_modified_file_path = None
  file_to_read = temp_file_copy
  file_to_write = temp_file
  for function_and_args in process_functions_and_args:
    _prepare_files(file_to_read, file_to_write)
    
    process_function = function_and_args[0]
    process_function_additional_args = function_and_args[1:]
    process_function(file_to_read, file_to_write, *process_function_additional_args)
    
    last_modified_file_path = file_to_write.name
    file_to_read, file_to_write = file_to_write, file_to_read
  
  temp_file_copy.close()
  temp_file.close()
  
  shutil.copy2(last_modified_file_path, file_path)
  
  os.remove(temp_filename_copy)
  os.remove(temp_file.name)
  os.rmdir(temp_dir)


#===============================================================================


def _trim_leading_spaces(file_to_read, file_to_write, num_leading_spaces):
  line = file_to_read.readline()
  while line:
    if not line.strip():
      # Write back the empty/whitespace-only line.
      file_to_write.write(line)
      
      # Trim leading spaces from subsequent lines.
      line = file_to_read.readline()
      while line.startswith(" " * num_leading_spaces):
        file_to_write.write(line.lstrip(" "))
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
    src_filename_pattern = re.escape(src_filename).replace("\\ ", "\\s")
    filenames_to_rename_patterns[src_filename_pattern] = dest_filename
  
  for line in file_to_read:
    processed_line = line
    for src_filename_pattern, dest_filename in filenames_to_rename_patterns.items():
      processed_line = re.sub(
        src_filename_pattern, lambda match: dest_filename, processed_line)
    file_to_write.write(processed_line)


def _remove_download_link(file_to_read, file_to_write):
  line = file_to_read.readline()
  while line:
    if "download latest release" not in line.lower():
      file_to_write.write(line)
    else:
      break
    line = file_to_read.readline()
  
  # Skip the download link
  line = file_to_read.readline()
  # Skip empty line
  line = file_to_read.readline()
  
  while line:
    file_to_write.write(line)
    line = file_to_read.readline()


FILES_TO_PROCESS = {
  FILENAMES_TO_RENAME["README.md"]: [
    (_trim_leading_spaces, NUM_LEADING_SPACES_TO_TRIM),
    (_rename_filenames_inside_file, FILENAMES_TO_RENAME),
    (_remove_download_link,)
  ]
}

#===============================================================================


def make_package(input_directory, output_file_path, version):
  
  _generate_pot_file(pygimplib.config.LOCALE_PATH, version)
  
  file_paths = _get_filtered_file_paths(input_directory, INCLUDE_LIST_FILENAME)
  relative_file_paths = [
    file_path[len(input_directory) + 1:] for file_path in file_paths]
  relative_renamed_file_paths = _get_relative_renamed_file_paths(relative_file_paths)
  
  temp_dir = tempfile.mkdtemp()
  temp_file_paths = [
    os.path.join(temp_dir, relative_file_path)
    for relative_file_path in relative_renamed_file_paths]
  
  _create_temp_file_paths(file_paths, temp_file_paths)
  
  _set_permissions(temp_dir, 0o755)
  
  _process_files(temp_file_paths)
  
  _create_package_file(output_file_path, temp_file_paths, relative_renamed_file_paths)
  
  shutil.rmtree(temp_dir)


def _get_filtered_file_paths(directory, pattern_file):
  with io.open(
         pattern_file, "r",
         encoding=pgconstants.TEXT_FILE_CHARACTER_ENDOCING) as file_:
    spec = pathspec.PathSpec.from_lines(
      pathspec.patterns.gitwildmatch.GitWildMatchPattern, file_)
  
  return [os.path.join(directory, match) for match in spec.match_tree(directory)]


def _generate_pot_file(source_dir, version):
  if os.name == "nt":
    print("Warning: Cannot generate .pot file on Windows", file=sys.stderr)
    return
  
  for file_ in os.listdir(source_dir):
    if os.path.isfile(os.path.join(source_dir, file_)):
      if file_.endswith(".pot"):
        os.remove(os.path.join(source_dir, file_))
   
  orig_cwd = os.getcwdu()
  os.chdir(source_dir)
  subprocess.call(["./generate_pot.sh", version])
  os.chdir(orig_cwd)


def _get_relative_renamed_file_paths(relative_file_paths):
  relative_renamed_file_paths = []
  
  for relative_file_path in relative_file_paths:
    if os.path.basename(relative_file_path) in FILENAMES_TO_RENAME:
      relative_renamed_file_paths.append(
        os.path.join(
          os.path.dirname(relative_file_path),
          FILENAMES_TO_RENAME[os.path.basename(relative_file_path)]))
    else:
      relative_renamed_file_paths.append(relative_file_path)
  
  return relative_renamed_file_paths


def _create_temp_file_paths(file_paths, temp_file_paths):
  for src_file_path, temp_file_path in zip(file_paths, temp_file_paths):
    dirname = os.path.dirname(temp_file_path)
    if not os.path.exists(dirname):
      pgpath.make_dirs(dirname)
    shutil.copy2(src_file_path, temp_file_path)


def _set_permissions(path, permissions):
  """
  Set file permissions on all files and subdirectories in a given path.
  """
  
  if os.name == "nt":
    print("Warning: Cannot set Unix-style permissions on Windows", file=sys.stderr)
    return
  
  for root, dirs, files in os.walk(path):
    for dir_ in dirs:
      os.chmod(os.path.join(root, dir_), permissions)
    for file_ in files:
      os.chmod(os.path.join(root, file_), permissions)


def _process_files(file_paths):
  for file_path in file_paths:
    filename = os.path.basename(file_path)
    
    if filename in FILES_TO_PROCESS:
      process_file(file_path, *FILES_TO_PROCESS[filename])
    
    if filename in FILES_TO_PROCESS or filename in FILENAMES_TO_RENAME.values():
      _set_windows_newlines(file_path)


def _set_windows_newlines(file_path):
  # This makes sure that even Notepad (which can only handle \r\n newlines) can
  # properly display the readme.
  
  encoding = pgconstants.TEXT_FILE_CHARACTER_ENDOCING
  
  with io.open(file_path, "r", encoding=encoding) as file_:
    contents = file_.read()
  
  with io.open(file_path, "w", newline="\r\n", encoding=encoding) as file_:
    file_.write(contents)


def _create_package_file(package_file_path, input_file_paths, output_file_paths):
  with zipfile.ZipFile(package_file_path, "w", zipfile.ZIP_STORED) as package_file:
    for input_file_path, output_file_path in zip(input_file_paths, output_file_paths):
      package_file.write(input_file_path, output_file_path)


#===============================================================================


def main():
  output_file_path = "{0}-{1}.{2}".format(
    OUTPUT_FILENAME_PREFIX, pygimplib.config.PLUGIN_VERSION, OUTPUT_FILENAME_EXTENSION)
  
  make_package(PLUGINS_PATH, output_file_path, pygimplib.config.PLUGIN_VERSION)
  
  print("Package successfully created:", os.path.join(PLUGINS_PATH, output_file_path))


if __name__ == "__main__":
  main()
