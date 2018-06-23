# -*- coding: utf-8 -*-
#
# Copyright (C) 2014-2018 khalim19
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
This module contains functions related to directory manipulations.

This module should not be used directly. Use `pgpath` as the contents of this
module are included in `pgpath`.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import os

__all__ = [
  "make_dirs"
]

#===============================================================================

# Taken from StackOverflow: http://stackoverflow.com/
# Question: http://stackoverflow.com/questions/600268/mkdir-p-functionality-in-python
# Answer:
# http://stackoverflow.com/questions/600268/mkdir-p-functionality-in-python/600612#600612
def make_dirs(dirpath):
  """
  Recursively create directories from the specified directory path.
  
  Do not raise exception if the directory path already exists.
  """
  try:
    os.makedirs(dirpath)
  except OSError as exc:
    if exc.errno == os.errno.EEXIST and os.path.isdir(dirpath):
      pass
    elif exc.errno == os.errno.EACCES and os.path.isdir(dirpath):
      # This can happen if `os.makedirs` is called on a root directory
      # in Windows (e.g. `os.makedirs("C:\\")`).
      pass
    else:
      raise
