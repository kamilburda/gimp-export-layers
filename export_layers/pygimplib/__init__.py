# -*- coding: utf-8 -*-
#
# pygimplib - Library to improve development of Python GIMP plug-ins
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

from __future__ import absolute_import, division, print_function, unicode_literals

import collections
import functools
import gettext
import inspect
import os
import sys
import types

#===============================================================================

def _setup_import_of_external_lib_modules(lib_directory):
  """
  Add directories containing external libraries for pygimplib to `sys.path` so
  that modules from these external libraries can be imported as system modules
  (i.e. without using absolute or explicit relative imports).
  
  Modules with the same name that are already installed system-wide are
  overridden by the external library modules from pygimplib.
  """
  
  for filename in os.listdir(lib_directory):
    lib_file_path = os.path.join(lib_directory, filename)
    if os.path.isdir(lib_file_path) and lib_file_path not in sys.path:
      _insert_library_to_system_path(lib_file_path)


def _insert_library_to_system_path(lib_path):
  # Path must be inserted at the second position:
  # https://docs.python.org/3/library/sys.html#sys.path
  sys.path.insert(1, lib_path)


_PYGIMPLIB_PATH = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
_LIB_SUBDIRECTORY_PATH = os.path.join(_PYGIMPLIB_PATH, "lib")

_setup_import_of_external_lib_modules(_LIB_SUBDIRECTORY_PATH)

#===============================================================================

from future.builtins import *

try:
  import gimp
  import gimpenums
  import gimpplugin
  
  from . import pggui
  from . import pglogging
  from . import pgsetting
  from . import pgsettinggroup
  from . import pgsettingsources
  from . import pgsettingpdb
except ImportError:
  _gimp_dependent_modules_imported = False
else:
  _gimp_dependent_modules_imported = True

from . import pgconstants

#===============================================================================


class _Config(object):
  
  def __init__(self):
    super().__setattr__("_config", {})
    self._config["_can_modify_config"] = True
  
  def __setattr__(self, name, value):
    if self._can_modify_config:
      self._config[name] = value
    else:
      raise TypeError("cannot modify configuration after plug-in initialization")
  
  def __getattr__(self, name):
    if name not in self._config:
      raise AttributeError("configuration entry '{0}' not found".format(name))
    
    attr = self._config[name]
    
    if callable(attr):
      return attr()
    else:
      return attr


def _init_config():
  global config
  
  if config is not None:
    return
  
  def _get_domain_name():
    if config.PLUGIN_NAME == config._DEFAULT_PLUGIN_NAME:
      return "gimp20-python"
    else:
      return "gimp-plugin-" + config.PLUGIN_NAME.replace("_", "-")
  
  config = _Config()
  
  config._DEFAULT_PLUGIN_NAME = "gimp_plugin"
  config.PLUGIN_NAME = config._DEFAULT_PLUGIN_NAME
  config.PLUGIN_TITLE = lambda: config.PLUGIN_NAME
  config.PLUGIN_VERSION = "1.0"
  
  config.LOCALE_PATH = lambda: os.path.join(config.PLUGIN_PATH, "locale")
  config.DOMAIN_NAME = _get_domain_name
  
  config.BUG_REPORT_URI_LIST = []
  
  pygimplib_directory = os.path.dirname(inspect.getfile(inspect.currentframe()))
  config.PLUGIN_PATH = os.path.dirname(pygimplib_directory)
  
  if _gimp_dependent_modules_imported:
    config.LOG_MODE = pgconstants.LOG_EXCEPTIONS_ONLY
  
  gettext.install(config.DOMAIN_NAME, config.LOCALE_PATH, unicode=True)
  
  _init_config_builtin(config)


def _init_config_builtin(config):
  
  def _get_setting_source_name():
    if config.PLUGIN_NAME.startswith("plug_in"):
      return config.PLUGIN_NAME
    else:
      return "plug_in_" + config.PLUGIN_NAME
  
  config.SOURCE_SESSION_NAME = _get_setting_source_name()
  config.SOURCE_PERSISTENT_NAME = _get_setting_source_name()
  
  config.PLUGINS_LOG_DIRNAMES = []
  config.PLUGINS_LOG_DIRNAMES.append(config.PLUGIN_PATH)
  
  if _gimp_dependent_modules_imported:
    plugins_directory_alternate = os.path.join(gimp.directory, "plug-ins")
    if plugins_directory_alternate != config.PLUGIN_PATH:
      # Add `[user directory]/[GIMP directory]/plug-ins` as another log path in
      # case the plug-in was installed system-wide and there is no permission to
      # create log files there.
      config.PLUGINS_LOG_DIRNAMES.append(plugins_directory_alternate)
  
  config.PLUGINS_LOG_STDOUT_DIRNAME = config.PLUGINS_LOG_DIRNAMES[0]
  config.PLUGINS_LOG_STDERR_DIRNAME = config.PLUGINS_LOG_DIRNAMES[0]
  
  config.PLUGINS_LOG_STDOUT_FILENAME = config.PLUGIN_NAME + ".log"
  config.PLUGINS_LOG_STDERR_FILENAME = config.PLUGIN_NAME + "_error.log"
  
  config.GIMP_CONSOLE_MESSAGE_DELAY_MILLISECONDS = 50


def _init_config_builtin_delayed(config):
  if _gimp_dependent_modules_imported:
    config.SOURCE_SESSION = pgsettingsources.SessionPersistentSettingSource(config.SOURCE_SESSION_NAME)
    config.SOURCE_PERSISTENT = pgsettingsources.PersistentSettingSource(config.SOURCE_PERSISTENT_NAME)


#===============================================================================

config = None

_init_config()

#===============================================================================

_is_initialized = False

def init():
  global _is_initialized
  
  if _is_initialized:
    return
  
  _init_config_builtin(config)
  _init_config_builtin_delayed(config)
  
  gettext.install(config.DOMAIN_NAME, config.LOCALE_PATH, unicode=True)
  
  if _gimp_dependent_modules_imported:
    pglogging.log_output(
      config.LOG_MODE, config.PLUGINS_LOG_DIRNAMES, config.PLUGINS_LOG_STDOUT_FILENAME,
      config.PLUGINS_LOG_STDERR_FILENAME, config.PLUGIN_TITLE, config.GIMP_CONSOLE_MESSAGE_DELAY_MILLISECONDS)
  
  _is_initialized = True


#===============================================================================

if _gimp_dependent_modules_imported:
  
  _plugins = collections.OrderedDict()
  _plugins_names = collections.OrderedDict()
  
  def plugin(*plugin_args, **plugin_kwargs):
    
    def plugin_wrapper(procedure):
      _plugins[procedure] = (plugin_args, plugin_kwargs)
      _plugins_names[procedure.__name__] = procedure
      return procedure
    
    return plugin_wrapper
  
  def main():
    gimp.main(None, None, _query, _run)
  
  def install_plugin(plugin_procedure, blurb="", description="",
                     author="", copyright_notice="", date="",
                     menu_name="", menu_path=None, image_types="*",
                     parameters=None, return_values=None):
    
    def _get_pdb_params(params):
      pdb_params = []
      
      if params:
        has_settings = isinstance(params[0], (pgsetting.Setting, pgsettinggroup.SettingGroup))
        if has_settings:
          pdb_params = pgsettingpdb.PdbParamCreator.create_params(*params)
        else:
          pdb_params = params
      
      return pdb_params
    
    gimp.install_procedure(
      plugin_procedure.__name__,
      blurb,
      description,
      author,
      copyright_notice,
      date,
      menu_name,
      image_types,
      gimpenums.PLUGIN,
      _get_pdb_params(parameters),
      _get_pdb_params(return_values))
    
    if menu_path:
      gimp.menu_register(plugin_procedure.__name__, menu_path)
  
  def _query():
    gimp.domain_register(config.DOMAIN_NAME, config.LOCALE_PATH)
    
    for plugin_procedure, plugin_args_and_kwargs in _plugins.items():
      install_plugin(plugin_procedure, *plugin_args_and_kwargs[0], **plugin_args_and_kwargs[1])
  
  def _run(procedure_name, procedure_params):
    if config.PLUGIN_NAME == config._DEFAULT_PLUGIN_NAME:
      config.PLUGIN_NAME = procedure_name
    
    init()
    
    config._can_modify_config = False
    
    procedure = _set_gui_excepthook(_plugins_names[procedure_name], procedure_params[0])
    procedure(*procedure_params)
  
  def _set_gui_excepthook(procedure, run_mode):
    if run_mode == gimpenums.RUN_INTERACTIVE:
      set_gui_excepthook_func = pggui.set_gui_excepthook(
        title=config.PLUGIN_TITLE, app_name=config.PLUGIN_TITLE, report_uri_list=config.BUG_REPORT_URI_LIST)
      return set_gui_excepthook_func(procedure)
    else:
      return procedure
