#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""Creating a new plug-in release."""

from __future__ import absolute_import, division, print_function, unicode_literals

import collections
import distutils.util
import getpass
import inspect
import io
import json
import os
import re
import requests
import signal
import shutil
import subprocess
import sys
import time
import traceback

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

import git

from utils import make_installers
from utils import preprocess_document_contents


# HACK: This fixes GitPython throwing errors when the `str` type from the
# `future` library is not accepted as a string when GitPython calls
# subprocesses.
str = unicode


GITHUB_PAGE_DIRPATH = os.path.join(PLUGINS_DIRPATH, 'docs', 'gh-pages')
GITHUB_PAGE_BRANCH = 'gh-pages'

VERSION_STRING_FORMAT = 'major.minor[.patch[-prerelease[.patch]]]'

PLUGIN_CONFIG_FILEPATH = os.path.join(PLUGIN_SUBDIRPATH, 'config.py')
PLUGIN_CONFIG_DEV_FILEPATH = os.path.join(PLUGIN_SUBDIRPATH, 'config_dev.py')
CHANGELOG_FILEPATH = os.path.join(PLUGINS_DIRPATH, 'CHANGELOG.md')

INSTALLERS_OUTPUT_DIRPATH = make_installers.OUTPUT_DIRPATH_DEFAULT

FILE_EXTENSIONS_AND_MIME_TYPES = {
  'zip': 'application/x-zip-compressed',
  'exe': 'application/x-msdownload',
}

PROMPT_NO_EXIT_STATUS = 2


def make_release(**kwargs):
  repo = git.Repo(PLUGINS_DIRPATH)
  gh_pages_repo = git.Repo(GITHUB_PAGE_DIRPATH)
  
  release_metadata = _ReleaseMetadata(
    repo,
    gh_pages_repo,
    current_version=pg.config.PLUGIN_VERSION,
    released_versions=repo.git.tag('-l').strip('\n').split('\n'),
    username=pg.config.REPOSITORY_USERNAME,
    remote_repo_name=pg.config.REPOSITORY_NAME,
    **kwargs)
  
  def handle_sigint(signal, frame):
    _print_error('\nPerforming rollback and aborting.')
    _rollback(release_metadata)
    sys.exit(1)
  
  signal.signal(signal.SIGINT, handle_sigint)
  
  try:
    _make_release(release_metadata)
  except Exception:
    _print_error(
      '\nThe following error has occurred:\n{}\nPerforming rollback and aborting.'.format(
        traceback.format_exc()))
    _rollback(release_metadata)
    sys.exit(1)


def _make_release(release_metadata):
  _check_branches_for_local_changes(release_metadata)
  
  print('Active branch:', release_metadata.repo.active_branch.name)
  
  release_metadata.new_version = _get_next_version(release_metadata)
  
  _check_if_tag_with_new_version_already_exists(release_metadata)
  
  if release_metadata.interactive:
    _prompt_to_proceed()
  
  release_metadata.access_token = _get_access_token(release_metadata)
  
  _get_release_notes_and_modify_changelog_first_header(release_metadata)
  
  _update_version_and_release_date_in_config(release_metadata, PLUGIN_CONFIG_FILEPATH)
  if os.path.isfile(PLUGIN_CONFIG_DEV_FILEPATH):
    _update_version_and_release_date_in_config(release_metadata, PLUGIN_CONFIG_DEV_FILEPATH)
  
  _generate_translation_file(release_metadata)
  
  _create_release_commit(release_metadata, release_metadata.repo)
  _create_release_tag(release_metadata)
  
  _prepare_gh_pages_for_update(release_metadata)
  _create_release_commit(release_metadata, release_metadata.gh_pages_repo)
  
  _make_installers(release_metadata)
  
  _push_release_commit(release_metadata, release_metadata.repo)
  _push_release_tag(release_metadata)
  _push_release_commit(
    release_metadata,
    release_metadata.gh_pages_repo,
    release_metadata.gh_pages_repo.active_branch.name)
  
  _create_github_release(release_metadata)


def _check_branches_for_local_changes(release_metadata):
  if (not release_metadata.force
      and _has_active_branch_local_changes(release_metadata.repo)):
    _print_error_and_exit(
      'Repository contains local changes.'
      ' Please remove or commit changes before proceeding.')
  
  if _has_active_branch_local_changes(release_metadata.gh_pages_repo):
    _print_error_and_exit(
      ('Repository in the "{}" branch contains local changes.'
       ' Please remove or commit changes before proceeding.').format(
         release_metadata.gh_pages_repo.active_branch.name))


def _has_active_branch_local_changes(repo):
  return bool(repo.git.status('--porcelain'))


def _check_if_tag_with_new_version_already_exists(release_metadata):
  if release_metadata.repo.git.tag('-l', release_metadata.new_version):
    _print_error_and_exit(
      ('Repository already contains tag "{}", indicating that such a version'
       ' is already released.').format(release_metadata.new_version))


def _get_next_version(release_metadata):
  try:
    ver = pg.version.Version.parse(release_metadata.current_version)
  except pg.version.InvalidVersionFormatError:
    _print_error_and_exit(
      'Version string "{}" has invalid format; valid format: {}'.format(
        release_metadata.current_version, VERSION_STRING_FORMAT))
  
  try:
    ver.increment(release_metadata.release_type, release_metadata.prerelease)
  except ValueError as e:
    _print_error_and_exit(str(e))
  
  print('Current version:', release_metadata.current_version)
  print('New version:', str(ver))
  
  return str(ver)


def _get_access_token(release_metadata):
  if release_metadata.dry_run:
    return None
  
  return getpass.getpass('Enter your GitHub access token:')


def _prompt_to_proceed():
  response = input('Proceed with release? [y/n] ')
  
  try:
    should_proceed = distutils.util.strtobool(response)
  except ValueError:
    should_proceed = False
  
  if not should_proceed:
    _print_error_and_exit('Aborting.', PROMPT_NO_EXIT_STATUS)


def _get_release_notes_and_modify_changelog_first_header(release_metadata):
  with io.open(CHANGELOG_FILEPATH, 'r', encoding=pg.TEXT_FILE_ENCODING) as file_:
    changelog_contents = file_.read()
  
  header_raw, release_notes = (
    preprocess_document_contents.find_section(changelog_contents))
  
  first_level_header_pattern = r'(# (.*?)\n|(.*?)\n=+\n)'
  match = re.search(first_level_header_pattern, header_raw)
  if (match
      and all(header not in release_metadata.released_versions
              for header in [match.group(2), match.group(3)])):
    
    release_metadata.new_version_release_notes = release_notes.strip()
    
    print('Replacing header name "{}" in the changelog with the new version'.format(
      match.group(2) or match.group(3)))
    
    if release_metadata.dry_run:
      return
    
    if match.group(2):
      changelog_contents = re.sub(
        r'# .*?\n', r'# ' + release_metadata.new_version + r'\n',
        changelog_contents,
        count=1)
    elif match.group(3):
      changelog_contents = re.sub(
        r'.*?\n=+\n',
        (release_metadata.new_version
         + r'\n'
         + '=' * len(release_metadata.new_version)
         + '\n'),
        changelog_contents,
        count=1)
  
    with io.open(CHANGELOG_FILEPATH, 'w', encoding=pg.TEXT_FILE_ENCODING) as file_:
      file_.write(changelog_contents)


def _update_version_and_release_date_in_config(release_metadata, plugin_config_filepath):
  pg.config.PLUGIN_VERSION = release_metadata.new_version
  pg.config.PLUGIN_VERSION_RELEASE_DATE = release_metadata.new_version_release_date
  
  entries_to_modify = collections.OrderedDict([
    ('PLUGIN_VERSION', release_metadata.new_version),
    ('PLUGIN_VERSION_RELEASE_DATE', release_metadata.new_version_release_date)])
  
  print('Modifying the following entries in file "{}": {}'.format(
    plugin_config_filepath, ', '.join(entries_to_modify)))
  
  if release_metadata.dry_run:
    return
  
  with io.open(
         plugin_config_filepath, 'r', encoding=pg.TEXT_FILE_ENCODING) as config_file:
    lines = config_file.readlines()
  
  def get_entry_pattern(entry):
    return r'^(c\.' + re.escape(entry) + " = )'(.*)'$"
  
  entries_to_find = dict(entries_to_modify)
  
  for i, line in enumerate(lines):
    for entry_name, new_entry_value in list(entries_to_find.items()):
      if re.search(get_entry_pattern(entry_name), line):
        lines[i] = re.sub(
          get_entry_pattern(entry_name), r"\1'" + new_entry_value + "'", line)
        del entries_to_find[entry_name]
    
    if not entries_to_find:
      break
  
  if entries_to_find:
    _print_error_and_exit('Error: missing the following entries in file "{}": {}'.format(
      plugin_config_filepath, ', '.join(entries_to_find)))
  
  with io.open(
         plugin_config_filepath, 'w', encoding=pg.TEXT_FILE_ENCODING) as config_file:
    config_file.writelines(lines)


def _generate_translation_file(release_metadata):
  print('Generating .pot file for translations')
  
  if release_metadata.dry_run and not release_metadata.force_make_output:
    return
  
  orig_cwd = os.getcwdu()
  os.chdir(pg.config.LOCALE_DIRPATH)
  
  subprocess.call([
    './generate_pot.sh',
    pg.config.PLUGIN_NAME,
    release_metadata.new_version,
    pg.config.DOMAIN_NAME,
    pg.config.AUTHOR_NAME,
  ])
  
  os.chdir(orig_cwd)


def _create_release_commit(release_metadata, repo):
  print('Creating release commit from branch "{}"'.format(repo.active_branch.name))
  
  if release_metadata.dry_run:
    return
  
  repo.git.add('--all')
  repo.git.commit('-m', _get_release_message_header(release_metadata))
  
  # Amend the commit as git hooks may have modified additional files.
  repo.git.add('--all')
  repo.git.commit('--amend', '--no-edit')


def _create_release_tag(release_metadata):
  print('Creating tag "{}"'.format(release_metadata.release_tag))
  
  if release_metadata.dry_run:
    return
  
  release_metadata.repo.git.tag(
    '-a',
    release_metadata.new_version,
    '-m',
    _get_release_message_header(release_metadata))


def _get_release_message_header(release_metadata):
  return 'Release {}'.format(release_metadata.new_version)


def _prepare_gh_pages_for_update(release_metadata):
  print('Preparing branch "{}" for update'.format(
    release_metadata.gh_pages_repo.active_branch.name))
  
  if release_metadata.dry_run:
    return
  
  for dirname in ['images', 'sections']:
    shutil.rmtree(os.path.join(GITHUB_PAGE_DIRPATH, dirname))
    shutil.copytree(
      os.path.join(GITHUB_PAGE_DIRPATH, 'dev', dirname),
      os.path.join(GITHUB_PAGE_DIRPATH, dirname))


def _make_installers(release_metadata):
  print('Creating installers')
  
  if release_metadata.dry_run and not release_metadata.force_make_output:
    return
  
  if os.path.isdir(INSTALLERS_OUTPUT_DIRPATH):
    shutil.rmtree(INSTALLERS_OUTPUT_DIRPATH)
  
  make_installers.make_installers(
    force_if_dirty=release_metadata.force, installers=release_metadata.installers)


def _push_release_commit(release_metadata, repo, remote_branch=None):
  if remote_branch is None:
    remote_branch = release_metadata.remote_branch
  
  print('Pushing release commit from branch "{}" to remote "{} {}"'.format(
    repo.active_branch.name, release_metadata.remote_name, remote_branch))
  
  if release_metadata.dry_run:
    return
  
  repo.git.push(release_metadata.remote_name, '{}:{}'.format(
    repo.active_branch.name, remote_branch))


def _push_release_tag(release_metadata):
  print('Pushing tag "{}" to remote "{}"'.format(
    release_metadata.release_tag, release_metadata.remote_name))
  
  if release_metadata.dry_run:
    return
  
  release_metadata.repo.git.push(
    release_metadata.remote_name, release_metadata.release_tag)


def _create_github_release(release_metadata):
  print('Creating GitHub release')
  
  if release_metadata.dry_run:
    return
  
  releases_url = 'https://api.github.com/repos/{}/{}/releases'.format(
    release_metadata.username, release_metadata.remote_repo_name)
  
  data_dict = {
    'tag_name': release_metadata.release_tag,
    'target_commitish': release_metadata.remote_branch,
    'name': release_metadata.release_tag,
    'body': release_metadata.new_version_release_notes,
  }
  
  access_token_header = {
    'Accept': 'application/vnd.github+json',
    'Authorization': 'Bearer {}'.format(release_metadata.access_token),
  }
  
  response = requests.post(
    releases_url, headers=access_token_header, data=json.dumps(data_dict))
  
  response.raise_for_status()
  
  upload_url = re.sub(r'^(.*)\{.*?$', r'\1', response.json()['upload_url'])
  
  _upload_installers_to_github(release_metadata, upload_url, access_token_header)


def _upload_installers_to_github(release_metadata, upload_url, access_token_header):
  for root_dirpath, unused_, files in os.walk(INSTALLERS_OUTPUT_DIRPATH):
    for filename in files:
      unused_, file_extension = os.path.splitext(filename)
      if file_extension:
        file_extension = file_extension[1:]
        if file_extension not in FILE_EXTENSIONS_AND_MIME_TYPES:
          continue
      else:
        continue
      
      with io.open(os.path.join(root_dirpath, filename), 'rb') as file_:
        file_contents = file_.read()
      
      headers = dict(access_token_header)
      headers['Content-Type'] = FILE_EXTENSIONS_AND_MIME_TYPES[file_extension]
      
      response = requests.post(
        upload_url, headers=headers, data=file_contents, params={'name': filename})
      
      response.raise_for_status()


def _rollback(release_metadata):
  if release_metadata.dry_run:
    return
  
  try:
    release_metadata.repo.git.tag('-d', release_metadata.new_version)
  except git.GitCommandError:
    pass
  
  if os.path.isdir(INSTALLERS_OUTPUT_DIRPATH):
    shutil.rmtree(INSTALLERS_OUTPUT_DIRPATH)
  
  release_metadata.repo.git.reset(
    '--hard', release_metadata.last_commit_id_before_release)
  release_metadata.gh_pages_repo.git.reset(
    '--hard', release_metadata.last_gh_pages_commit_id_before_release)


def _print_error_and_exit(message, exit_status=1):
  _print_error(message)
  sys.exit(exit_status)


def _print_error(message):
  print(message, file=sys.stderr)


class _ReleaseMetadata(object):
  
  def __init__(self, repo, gh_pages_repo, **kwargs):
    self._repo = repo
    self._gh_pages_repo = gh_pages_repo
    
    self.new_version = None
    self.new_version_release_notes = ''
    self.new_version_release_date = time.strftime('%B %d, %Y', time.gmtime())
    
    self._last_commit_id_before_release = self._repo.git.rev_parse('HEAD')
    self._last_gh_pages_commit_id_before_release = (
      self._gh_pages_repo.git.rev_parse('HEAD'))
    
    for name, value in kwargs.items():
      if hasattr(self, name):
        raise TypeError(
          ('keyword argument "{}" already exists in class {}; to prevent name clashes,'
           ' rename conflicting script options').format(name, self.__class__.__name__))
      
      pg.utils.create_read_only_property(self, name, value)
  
  @property
  def repo(self):
    return self._repo
  
  @property
  def gh_pages_repo(self):
    return self._gh_pages_repo
  
  @property
  def last_commit_id_before_release(self):
    return self._last_commit_id_before_release
  
  @property
  def last_gh_pages_commit_id_before_release(self):
    return self._last_gh_pages_commit_id_before_release
  
  @property
  def release_tag(self):
    return self.new_version


#===============================================================================


def parse_args(args):
  parser = argparse.ArgumentParser(
    description='Create a new release for the GIMP plug-in.')
  
  parser.add_argument(
    'release_type',
    choices=['major', 'minor', 'patch'],
    help='the type of the new release')
  
  parser.add_argument(
    '-f',
    '--force',
    action='store_true',
    default=False,
    help='make release even if the repository contains local changes',
    dest='force')
  
  parser.add_argument(
    '-i',
    '--installers',
    nargs='*',
    default=['all'],
    choices=['zip', 'all'],
    help=(
      'installers to create; see help for "make_installers.py" for more information'),
    dest='installers')
  
  parser.add_argument(
    '-n',
    '--dry-run',
    action='store_true',
    default=False,
    help='do not make an actual release, only produce output',
    dest='dry_run')
  
  parser.add_argument(
    '--force-make-output',
    action='store_true',
    default=False,
    help='make installers and translation files even if --dry-run is specified',
    dest='force_make_output')
  
  parser.add_argument(
    '-p',
    '--prerelease',
    default=None,
    help='pre-release suffix (e.g. "alpha")',
    dest='prerelease')
  
  parser.add_argument(
    '-r',
    '--remote-name',
    default='origin',
    help='name of remote (defaults to "origin")',
    dest='remote_name')
  
  parser.add_argument(
    '-b',
    '--remote-branch',
    default='main',
    help='name of the branch (defaults to "main")',
    dest='remote_branch')
  
  parser.add_argument(
    '-y',
    '--yes',
    action='store_false',
    default=True,
    help='assume "yes" as answer to all yes/no prompts',
    dest='interactive')
  
  return parser.parse_args(args)


def main():
  parsed_args = parse_args(sys.argv[1:])
  make_release(**dict(parsed_args.__dict__))


if __name__ == '__main__':
  main()
