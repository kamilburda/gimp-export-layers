# -*- coding: utf-8 -*-

"""Functions related to directory manipulations, imported before the rest of
pygimplib is initialized.

This module should not be used directly. Use the `path` package as the contents
of this module are included in the package.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

str = unicode

import os

__all__ = [
  'make_dirs',
  'split_path',
]


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
      # in Windows (e.g. `os.makedirs('C:\\')`).
      pass
    else:
      raise


def split_path(path):
  """
  Split the specified path into separate path components.
  """
  path = os.path.normpath(path)
  path_components = []
  
  head = path
  while True:
    head, tail = os.path.split(head)
    if tail:
      path_components.insert(0, tail)
    else:
      if head:
        path_components.insert(0, head)
      break
  
  return path_components
