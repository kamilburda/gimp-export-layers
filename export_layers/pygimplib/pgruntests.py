# -*- coding: utf-8 -*-
#
# This file is part of pygimplib.
#
# Copyright (C) 2014-2016 khalim19 <khalim19@gmail.com>
#
# pygimplib is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pygimplib is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pygimplib.  If not, see <http://www.gnu.org/licenses/>.
#

"""
This module can be used to unit-test modules which require GIMP to be running.

All modules starting with the "test_" prefix will be executed as unit tests.

All modules not starting with the "test_" prefix will be loaded/reloaded before
executing the unit tests.

To run unit tests in GIMP:

* Open up the Python-Fu console (Filters -> Python-Fu -> Console).
* Run the following commands (you can copy-paste the lines to the console):

import imp
import os
import sys
plugins_path = os.path.join(gimp.directory, "plug-ins")
sys.path.append(plugins_path)
sys.path.append(<path to parent directory of pygimplib>)
sys.path.append(<path to pygimplib directory>)
import pygimplib
import pgruntests
pgruntests.run_tests(path=plugins_path)

* To repeat the tests, paste the following to the console:

imp.reload(pgruntests)
pgruntests.run_tests(path=plugins_path)
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import imp
import importlib
import pkgutil
import sys
import types
import unittest

#===============================================================================


def _fix_streams_for_unittest():
  # In the GIMP Python-Fu console, `sys.stdout` and `sys.stderr` are missing
  # the `flush()` method, which needs to be defined in order for the `unittest`
  # module to work properly.
  def flush(self):
    pass
  
  for stream in [sys.stdout, sys.stderr]:
    flush_func = getattr(stream, "flush", None)
    if flush_func is None or not callable(stream.flush):
      stream.flush = types.MethodType(flush, stream)


def run_test(module, stream=sys.stderr):
  test_suite = unittest.TestLoader().loadTestsFromModule(module)
  test_runner = unittest.TextTestRunner(stream=stream)
  test_runner.run(test_suite)


def load_module(module_name):
  """
  If not imported, import the module specified by its name.
  If already imported, reload the module.
  """
  
  if module_name not in sys.modules:
    module = importlib.import_module(module_name)
  else:
    module = imp.reload(sys.modules[module_name])
  
  return module


def run_tests(
      path, test_module_name_prefix="test_", modules=None, ignored_modules=None,
      output_stream=sys.stderr):
  """
  Execute all modules containing unit tests located in the `path` directory. The
  names of the unit test modules start with the specified prefix.
  
  `ignored_modules` is a list of prefixes matching unit test modules or packages
  to ignore.
  
  If `modules` is None, include all modules, except for those specified in
  `ignored_modules`. If `modules` is not None, include only modules matching the
  prefixes specified in `modules`. `ignored_modules` can be used to exclude
  submodules in `modules`.
  
  `output_stream` prints the unit test output using the specified output stream.
  """
  
  _fix_streams_for_unittest()
  
  module_names = []
  
  if ignored_modules is None:
    ignored_modules = []
  
  if modules is None:
    should_append = (
      lambda module_name: (
        not any(
          module_name.startswith(ignored_module) for ignored_module in ignored_modules)))
  else:
    should_append = (
      lambda module_name: (
        any(module_name.startswith(module) for module in modules)
        and not any(
          module_name.startswith(ignored_module) for ignored_module in ignored_modules)))
  
  for unused_, module_name, unused_ in pkgutil.walk_packages(path=[path]):
    if should_append(module_name):
      module_names.append(module_name)
  
  for module_name in module_names:
    module = load_module(module_name)
    if module_name.split(".")[-1].startswith(test_module_name_prefix):
      run_test(module, stream=output_stream)
