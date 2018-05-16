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
plugins_dirpath = os.path.join(gimp.directory, "plug-ins")
sys.path.append(plugins_dirpath)
sys.path.append(<path to parent directory of pygimplib>)
sys.path.append(<path to pygimplib directory>)
import pygimplib
import pgruntests
pgruntests.run_tests(plugins_dirpath)

* To repeat the tests, paste the following to the console:

imp.reload(pgruntests)
pgruntests.run_tests(plugins_dirpath)
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
      dirpath, test_module_name_prefix="test_", modules=None, ignored_modules=None,
      output_stream=sys.stderr):
  """
  Execute all modules containing unit tests located in the specified directory
  path. The names of the unit test modules start with the specified prefix.
  
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
  
  for unused_, module_name, unused_ in pkgutil.walk_packages(path=[dirpath]):
    if should_append(module_name):
      module_names.append(module_name)
  
  for module_name in module_names:
    module = load_module(module_name)
    if module_name.split(".")[-1].startswith(test_module_name_prefix):
      run_test(module, stream=output_stream)
