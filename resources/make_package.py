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

from export_layers import constants

from export_layers.pylibgimpplugin import libfiles

#===============================================================================

RESOURCES_PATH = os.path.dirname(inspect.getfile(inspect.currentframe()))
PLUGINS_PATH = os.path.dirname(RESOURCES_PATH)

OUTPUT_FILENAME_PREFIX = "export-layers"
OUTPUT_FILENAME_SUFFIX = ".zip"

IGNORE_LIST = """
.git*
.git/
resources/
*.pyc
*.pyo
*.log
*.json
.settings/
.project
.pydevproject
LICENSE
"""

FILENAMES_TO_RENAME = {
  "README.md" : "Readme.txt",
  "CHANGELOG.md" : "Changelog.txt",
  "Readme for Translators.md" : "Readme for Translators.txt",
}

#===============================================================================

def _parse_ignore_list(ignore_str):
  ignore_str = ignore_str.strip()
  
  ignored_files = []
  ignored_dirs = []
  
  for elem in ignore_str.split('\n'):
    elem = elem.strip()
    if elem.endswith('/'):
      ignored_dirs.append(elem[:-1])
    else:
      ignored_files.append(elem)
  
  return ignored_files, ignored_dirs


def _get_filtered_files(input_directory):
  
  def _should_ignore_root(root, ignored_dirs):
    for dir_ in ignored_dirs:
      if dir_ in libfiles.split_path(root):
        return True
    return False
  
  
  filtered_files = []
  ignored_files, ignored_dirs = _parse_ignore_list(IGNORE_LIST)
  
  for root, dirs, files in os.walk(input_directory):
    if _should_ignore_root(root, ignored_dirs):
      continue
    
    dirs = [dir_ for dir_ in dirs if dir_ not in ignored_dirs]
    
    files_ = set(files)
    for file_ in files:
      for ignored_file in ignored_files:
        if ignored_file.startswith("*"):
          if file_.endswith(ignored_file[1:]):
            files_.remove(file_)
            break
        elif ignored_file.endswith("*"):
          if file_.startswith(ignored_file[:-1]):
            files_.remove(file_)
            break
        else:
          if file_ == ignored_file:
            files_.remove(file_)
            break
    
    files = list(files_)
    
    filtered_files.extend([os.path.join(root, file_) for file_ in files])
  
  return filtered_files

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
  
  def _generate_pot_file(version):
    orig_cwd = os.getcwdu()
    os.chdir(os.path.join(RESOURCES_PATH, "locale_resources"))
    
    subprocess.call(["./generate_pot.sh", version])
    
    os.chdir(orig_cwd)
  
  
  files = _get_filtered_files(input_directory)
  files_relative_paths = [file_[len(input_directory) + 1:] for file_ in files]
  
  for i, rel_file_path in enumerate(files_relative_paths):
    filename = os.path.basename(rel_file_path)
    if filename in FILENAMES_TO_RENAME:
      files_relative_paths[i] = os.path.join(os.path.dirname(rel_file_path), FILENAMES_TO_RENAME[filename])
  
  temp_dir = tempfile.mkdtemp()
  temp_files = [os.path.join(temp_dir, file_) for file_ in files_relative_paths]
  
  for src_file, temp_file in zip(files, temp_files):
    dirname = os.path.dirname(temp_file)
    if not os.path.exists(dirname):
      libfiles.make_dirs(dirname)
    shutil.copy2(src_file, temp_file)
  
  _set_permissions(temp_dir, 0o755)
  
  _generate_pot_file(version)
  
  with zipfile.ZipFile(output_file, "w", zipfile.ZIP_STORED) as zip_file:
    for temp_file, file_ in zip(temp_files, files_relative_paths):
      zip_file.write(temp_file, file_)
  
  shutil.rmtree(temp_dir)
  
#===============================================================================

if __name__ == "__main__":
  output_file = OUTPUT_FILENAME_PREFIX +  '-' + constants.PLUGIN_VERSION + OUTPUT_FILENAME_SUFFIX
  
  if os.name == 'nt':
    print(os.path.basename(sys.argv[0]) + ": Error: Script can't run on Windows " +
          "because Unix-style permissions need to be set",
          file=sys.stderr)
    sys.exit(1)
  
  make_package(PLUGINS_PATH, output_file, constants.PLUGIN_VERSION)
