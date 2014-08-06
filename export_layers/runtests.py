#-------------------------------------------------------------------------------
#
# This file is part of Export Layers.
#
# Copyright (C) 2013, 2014 khalim19 <khalim19@gmail.com>
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
# along with Export Layers.  If not, see <http://www.gnu.org/licenses/>.
#
#-------------------------------------------------------------------------------

"""
This module can be used to unit-test modules which require GIMP
to be running.

All modules not starting with "test_" prefix will be loaded/reloaded before
executing the unit tests.

All modules in the 'tests' package starting with "test_" prefix
will be executed as unit tests.

--------------------------
To run the unit tests in GIMP:
* Open up the Python-Fu console (Filters -> Python-Fu -> Console).
* Run the following commands (you can copy-paste them):

import os
import sys
sys.path.append(os.path.join(gimp.directory, "plug-ins"))
from export_layers import runtests

* Run the tests by invoking the following command:

runtests.run_tests()

* To repeat the tests, simply run the above command again.
--------------------------

If you made changes to this module, you have to reload it manually:

reload(runtests)
"""

#===============================================================================

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division

str = unicode

#===============================================================================

import os
import sys
import types

import __builtin__

import importlib
import pkgutil

import unittest

#===============================================================================

TEST_MODULE_NAME_PREFIX = "test_"
TESTS_PACKAGE_NAME = "tests"

#===============================================================================

# For `gettext`-aware modules that use "_()" and "N_()" functions, define dummy
# functions that simply return the strings, since it's not desired to translate
# them when unit-testing.

def _(s):
  return s


def N_(s):
  return s


if '_' not in __builtin__.__dict__:
  __builtin__.__dict__['_'] = _

if 'N_' not in __builtin__.__dict__:
  __builtin__.__dict__['N_'] = N_

#===============================================================================

def run_test(module, stream=sys.stderr):
  test_suite = unittest.TestLoader().loadTestsFromModule(module)
  test_runner = unittest.TextTestRunner(stream=stream)
  test_runner.run(test_suite)


def load_module(module_name):
  """
  If not imported, import module specified by its name.
  If already imported, reload the module.
  """
  
  if module_name not in sys.modules:
    module = importlib.import_module(module_name)
  else:
    module = reload(sys.modules[module_name])
  
  return module


def _fix_streams_for_unittest():
  # In the GIMP Python-Fu console, `sys.stdout` and `sys.stderr` are missing
  # the `flush()` method, which needs to be defined in order for the `unittest`
  # module to work properly.
  def flush(self):
    pass
  
  for stream in [sys.stdout, sys.stderr]:
    flush_func = getattr(stream, 'flush', None)
    if flush_func is None or not callable(stream.flush):
      stream.flush = types.MethodType(flush, stream)

#===============================================================================

def run_tests(stream=sys.stderr):
  _fix_streams_for_unittest()

  # The parent of the package had to be specified, otherwise `walk_packages`
  # would not yield modules inside subpackages for some reason...
  
  module_path = os.path.abspath(__file__)
  module_dir_path = os.path.dirname(module_path)
  
  parent_module = os.path.basename(module_dir_path)
  parent_dir_path = os.path.dirname(module_dir_path)
  
  for unused_, module_name, unused_ in pkgutil.walk_packages(path=[parent_dir_path]):
    if not module_name.startswith(parent_module):
      continue
    
    module = load_module(module_name)
    
    parts = module_name.split('.')
    if parts[-1].startswith(TEST_MODULE_NAME_PREFIX):
      run_test(module, stream=stream)
