#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""Creating installers for releases from the plug-in source."""

from __future__ import absolute_import, division, print_function, unicode_literals

import os
import sys
import inspect

UTILS_DIRPATH = os.path.abspath(os.path.dirname(inspect.getfile(inspect.currentframe())))

PLUGINS_DIRPATH = os.path.dirname(UTILS_DIRPATH)
PLUGIN_SUBDIRPATH = os.path.join(PLUGINS_DIRPATH, 'export_layers')
PYGIMPLIB_DIRPATH = os.path.join(PLUGIN_SUBDIRPATH, 'pygimplib')

sys.path.extend([
  UTILS_DIRPATH,
  PLUGINS_DIRPATH,
  PLUGIN_SUBDIRPATH,
  PYGIMPLIB_DIRPATH])

from export_layers import pygimplib as pg
from future.builtins import *

import argparse
import collections
import io
import pathlib
import re
import shutil
import subprocess
import tempfile
import zipfile

import git
import pathspec

from export_layers.pygimplib import _path_dirs

from utils import create_user_docs
from utils import process_local_docs

pg.config.LOG_MODE = 'none'


INSTALLERS_DIRPATH = os.path.join(PLUGINS_DIRPATH, 'installers')

TEMP_INPUT_DIRPATH = os.path.join(INSTALLERS_DIRPATH, 'temp_input')
OUTPUT_DIRPATH_DEFAULT = os.path.join(INSTALLERS_DIRPATH, 'output')

INCLUDE_LIST_FILEPATH = os.path.join(UTILS_DIRPATH, 'make_installers_included_files.txt')

GITHUB_PAGE_DIRPATH = os.path.join(PLUGINS_DIRPATH, 'docs', 'gh-pages')

README_RELATIVE_FILEPATH = os.path.join('docs', 'sections', 'index.html')
README_RELATIVE_OUTPUT_FILEPATH = os.path.join('Readme.html')


def make_installers(
      input_dirpath=PLUGINS_DIRPATH,
      installer_dirpath=OUTPUT_DIRPATH_DEFAULT,
      force_if_dirty=False,
      installers=None,
      generate_docs=True):
  _path_dirs.make_dirs(installer_dirpath)
  
  temp_repo_files_dirpath = tempfile.mkdtemp()
  
  relative_filepaths_with_git_filters = (
    _prepare_repo_files_for_packaging(
      input_dirpath, temp_repo_files_dirpath, force_if_dirty))
  
  _compile_translation_files(pg.config.LOCALE_DIRPATH)

  temp_dirpath = TEMP_INPUT_DIRPATH
  
  _create_temp_dirpath(temp_dirpath)
  
  if generate_docs:
    _create_user_docs(os.path.join(temp_dirpath, pg.config.PLUGIN_NAME))
  
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


def _create_temp_dirpath(temp_dirpath):
  if os.path.isdir(temp_dirpath):
    shutil.rmtree(temp_dirpath)
  elif os.path.isfile(temp_dirpath):
    os.remove(temp_dirpath)
    
  _path_dirs.make_dirs(temp_dirpath)


def _prepare_repo_files_for_packaging(
      repository_dirpath, dirpath_with_original_files_with_git_filters, force_if_dirty):
  repo = git.Repo(repository_dirpath)
  
  if not force_if_dirty and repo.git.status('--porcelain'):
    print(('Repository contains local changes.'
           ' Please remove or commit changes before proceeding.'),
          file=sys.stderr)
    exit(1)
  
  path_specs = _get_path_specs_with_git_filters_from_gitattributes(repository_dirpath)
  
  spec_obj = pathspec.PathSpec.from_lines(
    pathspec.patterns.gitwildmatch.GitWildMatchPattern, path_specs)
  
  relative_filepaths_with_git_filters = [
    match for match in spec_obj.match_tree(repository_dirpath)]
  
  _move_files_with_filters_to_temporary_location(
    repository_dirpath,
    relative_filepaths_with_git_filters,
    dirpath_with_original_files_with_git_filters)
  
  _reset_files_with_filters_and_activate_smudge_filters(repo, path_specs)
  
  return relative_filepaths_with_git_filters


def _move_files_with_filters_to_temporary_location(
      repository_dirpath,
      relative_filepaths_with_git_filters,
      dirpath_with_original_files_with_git_filters):
  for relative_filepath in relative_filepaths_with_git_filters:
    src_filepath = os.path.join(repository_dirpath, relative_filepath)
    dest_filepath = os.path.join(
      dirpath_with_original_files_with_git_filters, relative_filepath)
    
    _path_dirs.make_dirs(os.path.dirname(dest_filepath))
    shutil.copy2(src_filepath, dest_filepath)
    os.remove(src_filepath)


def _reset_files_with_filters_and_activate_smudge_filters(repo, path_specs):
  for path_spec in path_specs:
    repo.git.checkout(path_spec)


def _restore_repo_files(
      dirpath_with_original_files_with_git_filters,
      repository_dirpath,
      relative_filepaths_with_git_filters):
  for relative_filepath in relative_filepaths_with_git_filters:
    shutil.copy2(
      os.path.join(dirpath_with_original_files_with_git_filters, relative_filepath),
      os.path.join(repository_dirpath, relative_filepath))


def _get_path_specs_with_git_filters_from_gitattributes(repository_dirpath):
  path_specs = []
  
  with io.open(os.path.join(repository_dirpath, '.gitattributes')) as gitattributes_file:
    for line in gitattributes_file:
      match = re.search(r'\s*(.*?)\s+filter=', line)
      if match:
        path_specs.append(match.group(1))
  
  return path_specs


def _get_filtered_filepaths(dirpath, pattern_filepath):
  with io.open(pattern_filepath, 'r', encoding=pg.TEXT_FILE_ENCODING) as file_:
    spec_obj = pathspec.PathSpec.from_lines(
      pathspec.patterns.gitwildmatch.GitWildMatchPattern, file_)
  
  return [os.path.join(dirpath, match) for match in spec_obj.match_tree(dirpath)]


def _get_relative_filepaths(filepaths, root_dirpath):
  return [filepath[len(root_dirpath) + 1:] for filepath in filepaths]


def _compile_translation_files(source_dirpath):
  orig_cwd = os.getcwdu()
  os.chdir(source_dirpath)
  
  for root_dirpath, unused_, filenames in os.walk(source_dirpath):
    for filename in filenames:
      if (os.path.isfile(os.path.join(root_dirpath, filename))
          and filename.endswith('.po')):
        po_file = os.path.join(root_dirpath, filename)
        language = _path_dirs.split_path(root_dirpath)[-2]
        subprocess.call(['./generate_mo.sh', po_file, language])
  
  os.chdir(orig_cwd)


def _copy_files_to_temp_filepaths(filepaths, temp_filepaths):
  for src_filepath, temp_filepath in zip(filepaths, temp_filepaths):
    dirpath = os.path.dirname(temp_filepath)
    if not os.path.exists(dirpath):
      _path_dirs.make_dirs(dirpath)
    shutil.copy2(src_filepath, temp_filepath)


def _create_user_docs(dirpath):
  create_user_docs.main(GITHUB_PAGE_DIRPATH, dirpath)


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
  if installers is None:
    installers = []
  
  installers = list(collections.OrderedDict.fromkeys(installers))
  
  installer_funcs = collections.OrderedDict([
    ('zip', _create_zip_archive),
  ])
  
  if 'all' in installers:
    installer_funcs_to_invoke = list(installer_funcs.values())
  else:
    installer_funcs_to_invoke = [
      installer_funcs[installer] for installer in installers
      if installer in installer_funcs]
  
  for installer_func in installer_funcs_to_invoke:
    installer_func(installer_dirpath, input_dirpath, input_filepaths, output_filepaths)


def _create_zip_archive(
      installer_dirpath, input_dirpath, input_filepaths, output_filepaths):
  archive_filename = '{}-{}.zip'.format(
    pg.config.PLUGIN_NAME, pg.config.PLUGIN_VERSION)
  archive_filepath = os.path.join(installer_dirpath, archive_filename)
  
  readme_filepath = os.path.join(
    input_dirpath, pg.config.PLUGIN_NAME, README_RELATIVE_FILEPATH)
  
  can_create_toplevel_readme = readme_filepath in input_filepaths
  
  if can_create_toplevel_readme:
    input_filepaths.append(_create_toplevel_readme_for_zip_archive(readme_filepath))
    output_filepaths.append(README_RELATIVE_OUTPUT_FILEPATH)
  
  with zipfile.ZipFile(archive_filepath, 'w', zipfile.ZIP_STORED) as archive_file:
    for input_filepath, output_filepath in zip(input_filepaths, output_filepaths):
      archive_file.write(input_filepath, output_filepath)
  
  print('ZIP archive successfully created:', archive_filepath)
  
  if can_create_toplevel_readme:
    input_filepaths.pop()
    output_filepaths.pop()


def _create_toplevel_readme_for_zip_archive(readme_filepath):
  def _modify_relative_paths(url_attribute_value):
    url_filepath = os.path.join(os.path.dirname(readme_filepath), url_attribute_value)
    
    if not os.path.exists(url_filepath):
      return url_attribute_value
    
    new_url_attribute_value = os.path.relpath(
      os.path.normpath(url_filepath), TEMP_INPUT_DIRPATH)
    
    return pathlib.Path(new_url_attribute_value).as_posix()
  
  toplevel_readme_filepath = os.path.join(
    TEMP_INPUT_DIRPATH, os.path.basename(readme_filepath))
  
  shutil.copy2(readme_filepath, toplevel_readme_filepath)
  
  process_local_docs.modify_url_attributes_in_file(
    readme_filepath,
    _modify_relative_paths,
    toplevel_readme_filepath,
    os.path.join(GITHUB_PAGE_DIRPATH, create_user_docs.PAGE_CONFIG_FILENAME))
  
  return toplevel_readme_filepath


#===============================================================================


def main():
  parser = argparse.ArgumentParser(description='Create installers for the GIMP plug-in.')
  parser.add_argument(
    '-d',
    '--dest-dir',
    default=OUTPUT_DIRPATH_DEFAULT,
    help='destination directory of the created installers',
    metavar='DIRECTORY',
    dest='installer_dirpath')
  parser.add_argument(
    '-f',
    '--force',
    action='store_true',
    default=False,
    help='make installers even if the repository contains local changes',
    dest='force_if_dirty')
  parser.add_argument(
    '-i',
    '--installers',
    nargs='*',
    default=['zip'],
    choices=['zip', 'all'],
    help='installers to create',
    dest='installers')
  parser.add_argument(
    '-n',
    '--no-docs',
    action='store_false',
    default=True,
    help='do not generate documentation',
    dest='generate_docs')
  
  parsed_args = parser.parse_args(sys.argv[1:])
  make_installers(**dict(parsed_args.__dict__))


if __name__ == '__main__':
  main()
