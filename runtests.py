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

"""
This GIMP plug-in runs automated tests for modules requiring GIMP to be running.

By default, all modules starting with the `"test_"` prefix will be executed.

To run tests in GIMP:

* Open up the Python-Fu console (Filters -> Python-Fu -> Console).
* Run the following commands (you can copy-paste the lines to the console):

pdb.plug_in_run_tests(<directory path to the plug-in under test>)

To repeat the tests, simply call the procedure again.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import inspect
import os
import sys

# Fix Windows installation failing to import modules from subdirectories in the
# "plug-ins" directory.
if os.name == "nt":
  current_module_dirpath = os.path.dirname(inspect.getfile(inspect.currentframe()))
  if current_module_dirpath not in sys.path:
    sys.path.append(current_module_dirpath)

from export_layers import pygimplib as pg
from future.builtins import *

import importlib
import io
import pkgutil
import unittest

import gimpenums

pg.init()


def run_tests(
      dirpath,
      test_module_name_prefix="test_",
      modules=None,
      ignored_modules=None,
      output_stream="stderr"):
  """
  Execute all modules containing tests located in the specified directory path.
  The names of the test modules start with the specified prefix.
  
  `ignored_modules` is a list of prefixes matching test modules or packages to
  ignore.
  
  If `modules` is `None` or empty, include all modules, except those specified
  in `ignored_modules`. If `modules` is not `None`, include only modules
  matching the prefixes specified in `modules`. `ignored_modules` can be used to
  exclude submodules in `modules`.
  
  `output_stream` is the name of the stream to print the output to - `"stdout"`,
  `"stderr"` or a file path. Defaults to `"stderr"`.
  """
  module_names = []
  
  if not ignored_modules:
    ignored_modules = []
  
  if not modules:
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
  
  for importer, module_name, is_package in pkgutil.walk_packages(path=[dirpath]):
    if should_append(module_name):
      if is_package:
        sys.path.append(importer.path)
      
      module_names.append(module_name)
  
  stream = _get_output_stream(output_stream)
  
  for module_name in module_names:
    module = importlib.import_module(module_name)
    if module_name.split(".")[-1].startswith(test_module_name_prefix):
      run_test(module, stream=stream)
  
  stream.close()


def run_test(module, stream=sys.stderr):
  test_suite = unittest.TestLoader().loadTestsFromModule(module)
  test_runner = unittest.TextTestRunner(stream=stream)
  test_runner.run(test_suite)


def _get_output_stream(stream_or_filepath):
  if hasattr(sys, stream_or_filepath):
    return _Stream(getattr(sys, stream_or_filepath))
  else:
    return io.open(stream_or_filepath, "wb")
  

class _Stream(object):
  
  def __init__(self, stream):
    self.stream = stream
  
  def write(self, data):
    self.stream.write(data)
  
  def flush(self):
    if hasattr(self.stream, "flush"):
      self.stream.flush()
  
  def close(self):
    pass


SETTINGS = pg.setting.SettingGroup("settings")
SETTINGS.add([
  {
    "type": pg.setting.SettingTypes.enumerated,
    "name": "run_mode",
    "default_value": "non_interactive",
    "items": [
      ("interactive", "RUN-INTERACTIVE", gimpenums.RUN_INTERACTIVE),
      ("non_interactive", "RUN-NONINTERACTIVE", gimpenums.RUN_NONINTERACTIVE),
      ("run_with_last_vals", "RUN-WITH-LAST-VALS", gimpenums.RUN_WITH_LAST_VALS)],
    "display_name": "The run mode",
    "tags": ["ignore_load", "ignore_save"],
  },
  {
    "type": pg.setting.SettingTypes.string,
    "name": "dirpath",
    "description": "Directory path containing test modules",
  },
  {
    "type": pg.setting.SettingTypes.string,
    "name": "prefix",
    "description": "Prefix of test modules",
  },
  {
    "type": pg.setting.SettingTypes.array,
    "name": "modules",
    "element_type": pg.setting.SettingTypes.string,
    "description": "Modules to include",
  },
  {
    "type": pg.setting.SettingTypes.array,
    "name": "ignored_modules",
    "element_type": pg.setting.SettingTypes.string,
    "description": "Modules to ignore",
  },
  {
    "type": pg.setting.SettingTypes.string,
    "name": "output_stream",
    "description": "Output stream",
  },
])


@pg.procedure(
  blurb="Run automated tests in the specified directory path.",
  parameters=[SETTINGS],
)
def plug_in_run_tests(run_mode, *args):
  processed_args = list(pg.setting.iter_args([run_mode] + list(args), SETTINGS))
  run_tests(*processed_args[1:])


if __name__ == "__main__":
  pg.main()
