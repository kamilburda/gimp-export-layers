# -*- coding: utf-8 -*-
#
# Copyright (C) 2014-2019 khalim19
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
This module contains functions dealing with file extensions.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

from .. import fileformats as pgfileformats

__all__ = [
  'get_file_extension',
  'get_filename_with_new_file_extension',
]


def get_file_extension(filename):
  """
  Get file extension from `filename` in lowercase.
  
  If `filename` has no file extension, return an empty string.
  
  If `filename` has multiple periods, it is checked against
  `fileformats.file_formats_dict` for a matching file extension containing
  periods. If there is no such extension, return the substring after the last
  period.
  """
  filename_lowercase = filename.lower()
  
  if '.' not in filename_lowercase:
    return ''
  
  file_extension = filename_lowercase
  
  while file_extension:
    next_period_index = file_extension.find('.')
    if next_period_index == -1:
      return file_extension
    
    file_extension = file_extension[next_period_index + 1:]
    if file_extension in pgfileformats.file_formats_dict:
      return file_extension
  
  return ''


def get_filename_with_new_file_extension(
      filename, file_extension, keep_extra_trailing_periods=False):
  """
  Return a new filename with the specified new file extension.
  
  To remove the file extension from `filename`, pass an empty string, `None`, or
  a period ('.').
  
  If `keep_extra_trailing_periods` is `True`, do not remove duplicate periods
  before the file extension.
  """
  filename_extension = get_file_extension(filename)
  
  if filename_extension:
    filename_without_extension = filename[0:len(filename) - len(filename_extension) - 1]
  else:
    filename_without_extension = filename
    if filename_without_extension.endswith('.') and not keep_extra_trailing_periods:
      filename_without_extension = filename_without_extension.rstrip('.')
  
  if file_extension and file_extension.startswith('.'):
    file_extension = file_extension.lstrip('.')
  
  if file_extension:
    file_extension = file_extension.lower()
    new_filename = '.'.join((filename_without_extension, file_extension))
  else:
    new_filename = filename_without_extension
  
  return new_filename
