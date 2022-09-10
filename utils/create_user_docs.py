#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of Export Layers.
#
# Copyright (C) 2013-2019 khalim19 <khalim19@gmail.com>
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

"""Generating user documentation from GitHub Pages files."""

from __future__ import absolute_import, division, print_function, unicode_literals
from export_layers import pygimplib as pg
from future.builtins import *

import io
import os
import shutil
import sys

import psutil
import requests
import yaml

from utils import process_local_docs


MODULE_DIRPATH = os.path.dirname(pg.utils.get_current_module_filepath())

FILE_ENCODING = 'utf-8'

PAGE_CONFIG_FILENAME = '_config.yml'
SITE_DIRNAME = '_site'
JEKYLL_SERVER_LOCALHOST_IP = '127.0.0.1'
JEKYLL_SERVER_PORT = '4000'


def run_github_page_locally(github_page_dirpath):
  run_github_page_locally_process = psutil.Popen(
    [os.path.join(MODULE_DIRPATH, 'run_github_page_locally.sh'), '--release'])
  
  page_config_filepath = os.path.join(github_page_dirpath, PAGE_CONFIG_FILENAME)
  
  with io.open(page_config_filepath, 'r', encoding=FILE_ENCODING) as page_config_file:
    page_config = yaml.load(page_config_file.read())
  
  page_ready = False
  
  while not page_ready:
    try:
      requests.get(
        'http://{}:{}{}/'.format(
          JEKYLL_SERVER_LOCALHOST_IP, JEKYLL_SERVER_PORT, page_config['baseurl']))
    except requests.ConnectionError:
      pass
    else:
      page_ready = True
  
  for child in run_github_page_locally_process.children(recursive=True):
    child.kill()
  
  run_github_page_locally_process.kill()


def _process_local_docs(github_page_dirpath, output_dirpath):
  copy_directory(os.path.join(github_page_dirpath, SITE_DIRNAME), output_dirpath)
  
  process_local_docs.main(
    output_dirpath,
    os.path.join(github_page_dirpath, PAGE_CONFIG_FILENAME))


def copy_directory(source_dirpath, dest_dirpath):
  for name in os.listdir(source_dirpath):
    if os.path.isdir(os.path.join(source_dirpath, name)):
      shutil.copytree(
        os.path.join(source_dirpath, name),
        os.path.join(dest_dirpath, name))
    else:
      shutil.copy2(
        os.path.join(source_dirpath, name),
        os.path.join(dest_dirpath, name))


#===============================================================================


def main(github_page_dirpath, output_dirpath):
  run_github_page_locally(github_page_dirpath)
  _process_local_docs(github_page_dirpath, output_dirpath)


if __name__ == '__main__':
  github_page_absolute_dirpath = os.path.abspath(sys.argv[1])
  output_absolute_dirpath = os.path.abspath(sys.argv[2])
  
  main(github_page_absolute_dirpath, output_absolute_dirpath)
