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

from __future__ import absolute_import, division, print_function, unicode_literals

import collections
import gettext
import inspect
import os
import sys

#===============================================================================


def _setup_import_of_external_lib_modules(dirpath):
  """
  Add directory paths containing external libraries for pygimplib to `sys.path`
  so that modules from these external libraries can be imported as system
  modules (i.e. without using absolute or explicit relative imports).
  
  Modules with the same name that are already installed system-wide override the
  external library modules from pygimplib.
  """
  
  for filename in os.listdir(dirpath):
    external_libs_dirpath = os.path.join(dirpath, filename)
    if os.path.isdir(external_libs_dirpath) and external_libs_dirpath not in sys.path:
      sys.path.append(external_libs_dirpath)


_PYGIMPLIB_DIRPATH = os.path.dirname(inspect.getfile(inspect.currentframe()))

_setup_import_of_external_lib_modules(os.path.join(_PYGIMPLIB_DIRPATH, "lib"))

#===============================================================================

from future.builtins import *

try:
  import gimp
  import gimpenums
  import gimpplugin
  import gimpui
  
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

config = None

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
  
  def __hasattr__(self, name):
    return name in self._config


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
  
  config.LOCALE_DIRPATH = lambda: os.path.join(config.PLUGINS_DIRPATH, "locale")
  config.DOMAIN_NAME = _get_domain_name
  
  config.BUG_REPORT_URL_LIST = []
  
  config.PLUGINS_DIRPATH = os.path.dirname(os.path.dirname(_PYGIMPLIB_DIRPATH))
  
  if _gimp_dependent_modules_imported:
    config.LOG_MODE = pgconstants.LOG_EXCEPTIONS_ONLY
  
  gettext.install(config.DOMAIN_NAME, config.LOCALE_DIRPATH, unicode=True)
  
  _init_config_builtin(config)


def _init_config_builtin(config):
  
  def _get_setting_source_name():
    if config.PLUGIN_NAME.startswith("plug_in"):
      return config.PLUGIN_NAME
    else:
      return "plug_in_" + config.PLUGIN_NAME
  
  config.SOURCE_SESSION_NAME = _get_setting_source_name()
  config.SOURCE_PERSISTENT_NAME = _get_setting_source_name()
  
  config.PLUGINS_LOG_DIRPATHS = []
  config.PLUGINS_LOG_DIRPATHS.append(config.PLUGINS_DIRPATH)
  
  if _gimp_dependent_modules_imported:
    plugins_dirpath_alternate = os.path.join(gimp.directory, "plug-ins")
    if plugins_dirpath_alternate != config.PLUGINS_DIRPATH:
      # Add `[user directory]/[GIMP directory]/plug-ins` as another log path in
      # case the plug-in was installed system-wide and there is no permission to
      # create log files there.
      config.PLUGINS_LOG_DIRPATHS.append(plugins_dirpath_alternate)
  
  config.PLUGINS_LOG_STDOUT_DIRPATH = config.PLUGINS_LOG_DIRPATHS[0]
  config.PLUGINS_LOG_STDERR_DIRPATH = config.PLUGINS_LOG_DIRPATHS[0]
  
  config.PLUGINS_LOG_STDOUT_FILENAME = config.PLUGIN_NAME + ".log"
  config.PLUGINS_LOG_STDERR_FILENAME = config.PLUGIN_NAME + "_error.log"
  
  config.GIMP_CONSOLE_MESSAGE_DELAY_MILLISECONDS = 50


def _init_config_builtin_delayed(config):
  if _gimp_dependent_modules_imported:
    config.SOURCE_SESSION = pgsettingsources.SessionPersistentSettingSource(
      config.SOURCE_SESSION_NAME)
    config.SOURCE_PERSISTENT = pgsettingsources.PersistentSettingSource(
      config.SOURCE_PERSISTENT_NAME)


#===============================================================================

_init_config()

#===============================================================================

_is_initialized = False


def init():
  global _is_initialized
  
  if _is_initialized:
    return
  
  _init_config_builtin(config)
  _init_config_builtin_delayed(config)
  
  gettext.install(config.DOMAIN_NAME, config.LOCALE_DIRPATH, unicode=True)
  
  if _gimp_dependent_modules_imported:
    pglogging.log_output(
      config.LOG_MODE, config.PLUGINS_LOG_DIRPATHS,
      config.PLUGINS_LOG_STDOUT_FILENAME, config.PLUGINS_LOG_STDERR_FILENAME,
      config.PLUGIN_TITLE, config.GIMP_CONSOLE_MESSAGE_DELAY_MILLISECONDS)
  
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
  
  def install_plugin(
        plugin_procedure, blurb="", description="",
        author="", copyright_notice="", date="",
        menu_name="", menu_path=None, image_types="*",
        parameters=None, return_values=None):
    
    def _get_pdb_params(params):
      pdb_params = []
      
      if params:
        has_settings = isinstance(
          params[0], (pgsetting.Setting, pgsettinggroup.SettingGroup))
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
    gimp.domain_register(config.DOMAIN_NAME, config.LOCALE_DIRPATH)
    
    for procedure, args_and_kwargs in _plugins.items():
      install_plugin(procedure, *args_and_kwargs[0], **args_and_kwargs[1])
  
  def _run(procedure_name, procedure_params):
    if config.PLUGIN_NAME == config._DEFAULT_PLUGIN_NAME:
      config.PLUGIN_NAME = procedure_name
    
    init()
    
    config._can_modify_config = False
    
    procedure = _set_gui_excepthook(_plugins_names[procedure_name], procedure_params[0])
    
    if hasattr(gimpui, "gimp_ui_init"):
      gimpui.gimp_ui_init()
    
    procedure(*procedure_params)
  
  def _set_gui_excepthook(procedure, run_mode):
    if run_mode == gimpenums.RUN_INTERACTIVE:
      set_gui_excepthook_func = pggui.set_gui_excepthook(
        title=config.PLUGIN_TITLE,
        app_name=config.PLUGIN_TITLE,
        report_uri_list=config.BUG_REPORT_URL_LIST)
      return set_gui_excepthook_func(procedure)
    else:
      return procedure
