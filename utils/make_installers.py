#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of Export Layers.
#
# Copyright (C) 2013-2018 khalim19 <khalim19@gmail.com>
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
This script creates installers for releases from the plug-in source.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from export_layers import pygimplib
from future.builtins import *

import collections
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
from export_layers.pygimplib import pglogging
from export_layers.pygimplib import pgpath
from export_layers.pygimplib import pgutils

from utils import create_user_docs
from utils import process_local_docs

import export_layers.config
export_layers.config.init()

pygimplib.config.LOG_MODE = pglogging.LOG_NONE

pygimplib.init()

#===============================================================================

MODULE_DIRPATH = os.path.dirname(pgutils.get_current_module_filepath())
PLUGINS_DIRPATH = os.path.dirname(MODULE_DIRPATH)
INSTALLERS_DIRPATH = os.path.join(PLUGINS_DIRPATH, "installers")

TEMP_INPUT_DIRPATH = os.path.join(INSTALLERS_DIRPATH, "temp_input")
OUTPUT_DIRPATH_DEFAULT = os.path.join(INSTALLERS_DIRPATH, "output")

INCLUDE_LIST_FILEPATH = os.path.join(MODULE_DIRPATH, "make_installers_included_files.txt")

GITHUB_PAGE_DIRPATH = os.path.join(PLUGINS_DIRPATH, "docs", "gh-pages")
GITHUB_PAGE_UTILS_DIRPATH = os.path.join(PLUGINS_DIRPATH, "docs", "GitHub_page")

#===============================================================================


def make_installers(
      input_dirpath, installer_dirpath, force_if_dirty, installers, generate_docs):
  temp_repo_files_dirpath = tempfile.mkdtemp()
  
  relative_filepaths_with_git_filters = (
    _prepare_repo_files_for_packaging(
      input_dirpath, temp_repo_files_dirpath, force_if_dirty))
  
  _generate_translation_files(pygimplib.config.LOCALE_DIRPATH)

  temp_dirpath = TEMP_INPUT_DIRPATH
  
  _create_temp_dirpath(temp_dirpath)
  
  if generate_docs:
    _create_user_docs(os.path.join(temp_dirpath, pygimplib.config.PLUGIN_NAME))
  
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
  
  _create_installers(
    installer_dirpath, temp_dirpath, temp_filepaths, relative_filepaths, installers)
  
  _restore_repo_files(
    temp_repo_files_dirpath, input_dirpath, relative_filepaths_with_git_filters)
  
  shutil.rmtree(temp_dirpath)
  shutil.rmtree(temp_repo_files_dirpath)
  _remove_pot_files(pygimplib.config.LOCALE_DIRPATH)


def _create_temp_dirpath(temp_dirpath):
  if os.path.isdir(temp_dirpath):
    shutil.rmtree(temp_dirpath)
  elif os.path.isfile(temp_dirpath):
    os.remove(temp_dirpath)
    
  pgpath.make_dirs(temp_dirpath)


def _prepare_repo_files_for_packaging(
      repository_dirpath, dirpath_with_original_files_with_git_filters, force_if_dirty):
  repo = git.Repo(repository_dirpath)
  
  if not force_if_dirty and repo.git.status("--porcelain"):
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


def _generate_translation_files(source_dirpath):
  _remove_pot_files(source_dirpath)
  
  _generate_pot_file(source_dirpath)
  _generate_mo_files(source_dirpath)


def _generate_pot_file(source_dirpath):
  orig_cwd = os.getcwdu()
  os.chdir(source_dirpath)
  
  subprocess.call([
    "./generate_pot.sh",
    pygimplib.config.PLUGIN_NAME,
    pygimplib.config.PLUGIN_VERSION,
    pygimplib.config.DOMAIN_NAME,
    pygimplib.config.AUTHOR_NAME,
    pygimplib.config.AUTHOR_CONTACT,
  ])
  
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
  create_user_docs.main(
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


#===============================================================================


def _create_installers(
      installer_dirpath, input_dirpath, input_filepaths, output_filepaths, installers):
  installer_funcs = collections.OrderedDict([
    ("windows", _create_windows_installer),
    ("linux", _create_linux_installer),
    ("macos", _create_macos_installer),
    ("zip", _create_zip_archive),
  ])
  
  if "all" in installers:
    installer_funcs_to_execute = list(installer_funcs.values())
  else:
    installer_funcs_to_execute = [
      installer_funcs[installer] for installer in installers
      if installer in installer_funcs]
  
  for installer_func in installer_funcs_to_execute:
    installer_func(installer_dirpath, input_dirpath, input_filepaths, output_filepaths)


def _create_windows_installer(
      installer_dirpath, input_dirpath, input_filepaths, output_filepaths):
  installer_filename_prefix = "{0}-{1}-windows".format(
    pygimplib.config.PLUGIN_NAME, pygimplib.config.PLUGIN_VERSION)
  
  installer_filepath = os.path.join(installer_dirpath, installer_filename_prefix + ".exe")
  
  WINDOWS_INSTALLER_SCRIPT_DIRPATH = os.path.join(INSTALLERS_DIRPATH, "windows")
  WINDOWS_INSTALLER_SCRIPT_FILENAME = "installer.iss"
  WINDOWS_INSTALLER_COMPILER_COMMAND = "compile_installer.bat"
  
  orig_cwd = os.getcwd()
  os.chdir(WINDOWS_INSTALLER_SCRIPT_DIRPATH)
  
  return_code = subprocess.call([
    "cmd.exe",
    "/c",
    WINDOWS_INSTALLER_COMPILER_COMMAND,
    pygimplib.config.PLUGIN_NAME,
    pygimplib.config.PLUGIN_VERSION,
    pygimplib.config.AUTHOR_NAME,
    os.path.relpath(input_dirpath, WINDOWS_INSTALLER_SCRIPT_DIRPATH),
    os.path.relpath(installer_dirpath, WINDOWS_INSTALLER_SCRIPT_DIRPATH),
    installer_filename_prefix,
    WINDOWS_INSTALLER_SCRIPT_FILENAME,
  ])
  
  os.chdir(orig_cwd)
  
  if return_code == 0:
    print("Windows installer successfully created:", installer_filepath)
  else:
    print("Failed to create Windows installer:", installer_filepath)


def _create_linux_installer(
      installer_dirpath, input_dirpath, input_filepaths, output_filepaths):
  _create_unix_installer(
    installer_dirpath, input_dirpath, input_filepaths, output_filepaths,
    platform_id="linux", platform_name="Linux")


def _create_macos_installer(
      installer_dirpath, input_dirpath, input_filepaths, output_filepaths):
  _create_unix_installer(
    installer_dirpath, input_dirpath, input_filepaths, output_filepaths,
    platform_id="macos", platform_name="macOS")


def _create_unix_installer(
      installer_dirpath, input_dirpath, input_filepaths, output_filepaths,
      platform_id, platform_name):
  installer_filename = "{0}-{1}-{2}.run".format(
    pygimplib.config.PLUGIN_NAME, pygimplib.config.PLUGIN_VERSION, platform_id)
  installer_filepath = os.path.join(installer_dirpath, installer_filename)
  
  installer_script_filename = "installer.sh"
  installer_script_filepath = os.path.join(
    INSTALLERS_DIRPATH, "unix", installer_script_filename)
  
  shutil.copy2(
    installer_script_filepath,
    os.path.join(input_dirpath, installer_script_filename))
  
  return_code = subprocess.call([
    "makeself",
    input_dirpath,
    installer_filepath,
    "{0} - GIMP plug-in".format(pygimplib.config.PLUGIN_TITLE),
    os.path.join(".", installer_script_filename),
    "--os",
    platform_id
  ])
  
  if return_code == 0:
    package_filepath = os.path.join(
      installer_dirpath, re.sub(r".run$", r".zip", installer_filename))
    
    with zipfile.ZipFile(package_filepath, "w", zipfile.ZIP_STORED) as package_file:
      package_file.write(installer_filepath, installer_filename)
    
    os.remove(installer_filepath)
    
    print("{0} package successfully created:".format(platform_name), package_filepath)
  else:
    print("Failed to create {0} installer:".format(platform_name), installer_filepath)


def _create_zip_archive(
      installer_dirpath, input_dirpath, input_filepaths, output_filepaths):
  archive_filename = "{0}-{1}.zip".format(
    pygimplib.config.PLUGIN_NAME, pygimplib.config.PLUGIN_VERSION)
  archive_filepath = os.path.join(installer_dirpath, archive_filename)
  
  readme_relative_filepath = "Readme.html"
  readme_filepath = os.path.join(
    input_dirpath, pygimplib.config.PLUGIN_NAME, readme_relative_filepath)
  
  can_create_toplevel_readme = readme_filepath in input_filepaths
  
  if can_create_toplevel_readme:
    input_filepaths.append(_create_toplevel_readme_for_zip_archive(readme_filepath))
    output_filepaths.append(readme_relative_filepath)
  
  with zipfile.ZipFile(archive_filepath, "w", zipfile.ZIP_STORED) as archive_file:
    for input_filepath, output_filepath in zip(input_filepaths, output_filepaths):
      archive_file.write(input_filepath, output_filepath)
  
  print("ZIP archive successfully created:", archive_filepath)
  
  if can_create_toplevel_readme:
    input_filepaths.pop()
    output_filepaths.pop()


def _create_toplevel_readme_for_zip_archive(readme_filepath):
  def add_directory_to_url(url_attribute_value):
    return re.sub(
      r"^docs",
      "{0}/docs".format(pygimplib.config.PLUGIN_NAME),
      url_attribute_value)
  
  toplevel_readme_filepath = os.path.join(
    os.path.dirname(os.path.dirname(readme_filepath)), os.path.basename(readme_filepath))
  
  shutil.copy2(readme_filepath, toplevel_readme_filepath)
  
  process_local_docs.modify_url_attributes_in_file(
    readme_filepath,
    add_directory_to_url,
    toplevel_readme_filepath,
    os.path.join(GITHUB_PAGE_DIRPATH, create_user_docs.PAGE_CONFIG_FILENAME))
  
  return toplevel_readme_filepath


#===============================================================================


def main(
      destination_dirpath=None,
      force_if_dirty=False,
      installers="zip",
      generate_docs=True):
  installer_dirpath = (
    destination_dirpath if destination_dirpath else OUTPUT_DIRPATH_DEFAULT)
  pgpath.make_dirs(installer_dirpath)
  
  installers = installers.replace(" ", "").split(",")
  
  make_installers(
    PLUGINS_DIRPATH, installer_dirpath, force_if_dirty, installers, generate_docs)


if __name__ == "__main__":
  main(sys.argv[1:])
