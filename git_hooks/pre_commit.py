#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
This script provides automatic update and staging of end-user documentation
files when "raw" documentation files have been changed.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import inspect
import os
import sys

import git

GIT_HOOKS_DIRPATH = os.path.abspath(
  os.path.dirname(inspect.getfile(inspect.currentframe())))

REPOSITORY_ROOT_DIRPATH = os.path.dirname(os.path.dirname(GIT_HOOKS_DIRPATH))

sys.path.append(REPOSITORY_ROOT_DIRPATH)

from utils import sync_docs

#===============================================================================


def get_synced_files_to_stage(staged_filepaths, filepaths_to_sync):
  return [
    filepaths_to_sync[staged_filepath]
    for staged_filepath in staged_filepaths if staged_filepath in filepaths_to_sync]


def filepath_matches_gitignore(repo, filepath):
  try:
    repo.git.check_ignore(filepath)
  except git.exc.GitCommandError:
    return False
  else:
    return True


def main():
  repo = git.Repo(REPOSITORY_ROOT_DIRPATH)
  
  staged_filepaths = [
    os.path.normpath(os.path.join(REPOSITORY_ROOT_DIRPATH, diff.a_path))
    for diff in repo.index.diff("HEAD")]
  
  filepaths_to_sync = sync_docs.get_filepaths(sync_docs.PATHS_TO_PREPROCESS_FILEPATH)
  filepaths_to_sync.update(sync_docs.get_filepaths(sync_docs.PATHS_TO_COPY_FILEPATH))
  
  sync_docs.main()
  
  synced_filepaths_to_stage = (
    get_synced_files_to_stage(staged_filepaths, filepaths_to_sync))
  
  filtered_synced_filepaths_to_stage = [
    filepath for filepath in synced_filepaths_to_stage
    if not filepath_matches_gitignore(repo, filepath)]
  
  repo.git.add(filtered_synced_filepaths_to_stage)


if __name__ == "__main__":
  main()
