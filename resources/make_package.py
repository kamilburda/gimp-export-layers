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

RESOURCES_DIRPATH = os.path.dirname(pgutils.get_current_module_filepath())
PLUGINS_DIRPATH = os.path.dirname(RESOURCES_DIRPATH)

OUTPUT_FILENAME_PREFIX = pygimplib.config.PLUGIN_NAME
OUTPUT_FILE_EXTENSION = "zip"

INCLUDE_LIST_FILEPATH = "./make_package_included_files.txt"

FILENAMES_TO_RENAME = {
  "README.md": "Readme.txt",
  "CHANGELOG.md": "Changelog.txt",
  "README for Translators.md": "Readme for Translators.txt",
  "LICENSE": "License.txt"}

NUM_LEADING_SPACES_TO_TRIM = 4

#===============================================================================


def process_file(filepath, *process_functions_and_args):
  
  def _prepare_files(file_to_read, file_to_write):
    file_to_read.seek(0)
    file_to_write.seek(0)
    file_to_write.truncate()
  
  def _create_temp_file(dirpath, mode, encoding):
    temp_file = tempfile.NamedTemporaryFile(mode, dir=dirpath, delete=False)
    temp_file.close()
    temp_file = io.open(temp_file.name, mode, encoding=encoding)
    
    return temp_file
  
  temp_dirpath = tempfile.mkdtemp()
  temp_file_copy_path = os.path.join(temp_dirpath, "temp")
  shutil.copy2(filepath, temp_file_copy_path)
  
  temp_file_copy = io.open(
    temp_file_copy_path, "r+", encoding=pgconstants.TEXT_FILE_CHARACTER_ENDOCING)
  temp_file = _create_temp_file(
    temp_dirpath, "r+", pgconstants.TEXT_FILE_CHARACTER_ENDOCING)
  
  last_modified_filepath = None
  file_to_read = temp_file_copy
  file_to_write = temp_file
  for function_and_args in process_functions_and_args:
    _prepare_files(file_to_read, file_to_write)
    
    process_function = function_and_args[0]
    process_function_additional_args = function_and_args[1:]
    process_function(file_to_read, file_to_write, *process_function_additional_args)
    
    last_modified_filepath = file_to_write.name
    file_to_read, file_to_write = file_to_write, file_to_read
  
  temp_file_copy.close()
  temp_file.close()
  
  shutil.copy2(last_modified_filepath, filepath)
  
  os.remove(temp_file_copy_path)
  os.remove(temp_file.name)
  os.rmdir(temp_dirpath)


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


FILENAMES_TO_PROCESS = {
  FILENAMES_TO_RENAME["README.md"]: [
    (_trim_leading_spaces, NUM_LEADING_SPACES_TO_TRIM),
    (_rename_filenames_inside_file, FILENAMES_TO_RENAME),
    (_remove_download_link,)
  ]
}

#===============================================================================


def make_package(input_dirpath, output_filepath, version):
  
  _generate_pot_file(pygimplib.config.LOCALE_DIRPATH, version)
  
  filepaths = _get_filtered_filepaths(input_dirpath, INCLUDE_LIST_FILEPATH)
  relative_filepaths = [filepath[len(input_dirpath) + 1:] for filepath in filepaths]
  relative_renamed_filepaths = _get_relative_renamed_filepaths(relative_filepaths)
  
  temp_dirpath = tempfile.mkdtemp()
  temp_filepaths = [
    os.path.join(temp_dirpath, relative_filepath)
    for relative_filepath in relative_renamed_filepaths]
  
  _create_temp_filepaths(filepaths, temp_filepaths)
  
  _set_permissions(temp_dirpath, 0o755)
  
  _process_files(temp_filepaths)
  
  _create_package_file(output_filepath, temp_filepaths, relative_renamed_filepaths)
  
  shutil.rmtree(temp_dirpath)


def _get_filtered_filepaths(dirpath, pattern_filepath):
  with io.open(
         pattern_filepath, "r",
         encoding=pgconstants.TEXT_FILE_CHARACTER_ENDOCING) as file_:
    spec = pathspec.PathSpec.from_lines(
      pathspec.patterns.gitwildmatch.GitWildMatchPattern, file_)
  
  return [os.path.join(dirpath, match) for match in spec.match_tree(dirpath)]


def _generate_pot_file(source_dirpath, version):
  if os.name == "nt":
    print("Warning: Cannot generate .pot file on Windows", file=sys.stderr)
    return
  
  for filename in os.listdir(source_dirpath):
    if os.path.isfile(os.path.join(source_dirpath, filename)):
      if filename.endswith(".pot"):
        os.remove(os.path.join(source_dirpath, filename))
   
  orig_cwd = os.getcwdu()
  os.chdir(source_dirpath)
  subprocess.call(["./generate_pot.sh", version])
  os.chdir(orig_cwd)


def _get_relative_renamed_filepaths(relative_filepaths):
  relative_renamed_filepaths = []
  
  for relative_filepath in relative_filepaths:
    if os.path.basename(relative_filepath) in FILENAMES_TO_RENAME:
      relative_renamed_filepaths.append(
        os.path.join(
          os.path.dirname(relative_filepath),
          FILENAMES_TO_RENAME[os.path.basename(relative_filepath)]))
    else:
      relative_renamed_filepaths.append(relative_filepath)
  
  return relative_renamed_filepaths


def _create_temp_filepaths(filepaths, temp_filepaths):
  for src_filepath, temp_filepath in zip(filepaths, temp_filepaths):
    dirpath = os.path.dirname(temp_filepath)
    if not os.path.exists(dirpath):
      pgpath.make_dirs(dirpath)
    shutil.copy2(src_filepath, temp_filepath)


def _set_permissions(dirpath, permissions):
  """
  Set file permissions on all files and subdirectories in the given directory
  path.
  """
  
  if os.name == "nt":
    print("Warning: Cannot set Unix-style permissions on Windows", file=sys.stderr)
    return
  
  for root, subdirpaths, filenames in os.walk(dirpath):
    for subdirpath in subdirpaths:
      os.chmod(os.path.join(root, subdirpath), permissions)
    for filename in filenames:
      os.chmod(os.path.join(root, filename), permissions)


def _process_files(filepaths):
  for filepath in filepaths:
    filename = os.path.basename(filepath)
    
    if filename in FILENAMES_TO_PROCESS:
      process_file(filepath, *FILENAMES_TO_PROCESS[filename])
    
    if filename in FILENAMES_TO_PROCESS or filename in FILENAMES_TO_RENAME.values():
      _set_windows_newlines(filepath)


def _set_windows_newlines(filepath):
  # This makes sure that even Notepad (which can only handle \r\n newlines) can
  # properly display the readme.
  
  encoding = pgconstants.TEXT_FILE_CHARACTER_ENDOCING
  
  with io.open(filepath, "r", encoding=encoding) as file_:
    contents = file_.read()
  
  with io.open(filepath, "w", newline="\r\n", encoding=encoding) as file_:
    file_.write(contents)


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
