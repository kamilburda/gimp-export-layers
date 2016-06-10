#
# pygimplib - Collection of modules to improve development of Python GIMP plug-ins
#
# Copyright (C) 2014, 2015 khalim19 <khalim19@gmail.com>
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

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

str = unicode

import functools
import gettext
import inspect
import os
import types

try:
  import gimp
  import gimpenums
  import gimpplugin

  from . import pgsettingpersistor
  from . import pggui
except ImportError:
  _gimp_dependent_modules_imported = False
else:
  _gimp_dependent_modules_imported = True

#===============================================================================

# Redirect stdout or stderr to:
# * DEBUG_FILE - log files,
# * DEBUG_GIMP_CONSOLE - GIMP error console
_DEBUG_OPTIONS = (DEBUG_NONE, DEBUG_FILE, DEBUG_GIMP_CONSOLE) = (0, 1, 2)

#===============================================================================



class _Config(object):
  
  def __init__(self):
    self._can_modify_config = True
  
  def init_config(self):
    self._can_modify_config = False
  
  def __setattr__(self, name, value):
    if not hasattr(self, '_can_modify_config') or self._can_modify_config:
      super(_Config, self).__setattr__(name, value)
    else:
      raise TypeError("cannot modify plug-in configuration after calling '{0}'".format(self.init_config.__name__))


def _init_config(config):
  config.PLUGIN_NAME = "gimp_plugin"
  config.PLUGIN_TITLE = "GIMP Plug-in"
  config.PLUGIN_VERSION = "1.0"

  config.DOMAIN_NAME = config.PLUGIN_NAME
  config.LOCALE_PATH = gimp.locale_directory
  
  config.BUG_REPORT_URI_LIST = []
  
  config.DEBUG = DEBUG_NONE
  
  _init_config_builtin(config)


def _init_config_builtin(config):
  current_module_path = os.path.dirname(inspect.getfile(inspect.currentframe()))
  
  config.PLUGINS_DIRECTORY = os.path.dirname(current_module_path)

  config.PLUGIN_DIRNAME = config.PLUGIN_NAME
  config.PLUGIN_PATH = os.path.join(config.PLUGINS_DIRECTORY, config.PLUGIN_DIRNAME)
  
  config.SOURCE_SESSION_NAME = "plug_in_" + config.PLUGIN_NAME + "_"
  config.SOURCE_PERSISTENT_NAME = "plug_in_" + config.PLUGIN_NAME
  
  config.PLUGINS_LOG_STDOUT_PATH = os.path.join(config.PLUGIN_PATH, config.PLUGIN_NAME + ".log")
  config.PLUGINS_LOG_STDERR_PATH = os.path.join(config.PLUGIN_PATH, config.PLUGIN_NAME + "_error.log")
  
  # These are alternate paths that can be used to log output to the
  # `[user directory]/[GIMP directory]/plug-ins` directory in case the plug-in was
  # installed system-wide (e.g. in `Program Files` on Windows) and there is no
  # permission to create log files there.
  config.PLUGINS_DIRECTORY_ALTERNATE = None
  config.PLUGIN_PATH_ALTERNATE = None
  config.PLUGINS_LOG_STDOUT_PATH_ALTERNATE = None
  config.PLUGINS_LOG_STDERR_PATH_ALTERNATE = None
  
  if _gimp_dependent_modules_imported:
    config.PLUGINS_DIRECTORY_ALTERNATE = os.path.join(gimp.directory, "plug-ins")
    if config.PLUGINS_DIRECTORY_ALTERNATE != config.PLUGINS_DIRECTORY:
      config.PLUGIN_PATH_ALTERNATE = os.path.join(config.PLUGINS_DIRECTORY_ALTERNATE, config.PLUGIN_DIRNAME)
      config.PLUGINS_LOG_STDOUT_PATH_ALTERNATE = os.path.join(
        config.PLUGIN_PATH_ALTERNATE, config.PLUGIN_NAME + ".log")
      config.PLUGINS_LOG_STDERR_PATH_ALTERNATE = os.path.join(
        config.PLUGIN_PATH_ALTERNATE, config.PLUGIN_NAME + "_error.log")


def _init_config_builtin_derived(config):
  config.SOURCE_SESSION = pgsettingpersistor.SessionPersistentSettingSource(config.SOURCE_SESSION_NAME)
  config.SOURCE_PERSISTENT = pgsettingpersistor.PersistentSettingSource(config.SOURCE_PERSISTENT_NAME)


#===============================================================================

config = _Config()

_init_config(config)

#===============================================================================

if _gimp_dependent_modules_imported:
  
  class GimpPlugin(gimpplugin.plugin):
    
    def __init__(self):
      _init_config_builtin(config)
      _init_config_builtin_derived(config)
      
      self.init_additional_config()
      
      procedures_to_register = [method_name for method_name in dir(self)
                                if method_name.startswith("plug_in") and callable(getattr(self, method_name))]
      for procedure_name in procedures_to_register:
        self._set_gui_excepthook(procedure_name)
    
    def init_additional_config(self):
      pass
  
    def _set_gui_excepthook(self, procedure_name):
      
      def _set_gui_excepthook_wrapper(procedure):
        
        @functools.wraps(procedure)
        def procedure_wrapper(self, run_mode, *args):
          if run_mode == gimpenums.RUN_INTERACTIVE:
            return pggui.set_gui_excepthook(config.PLUGIN_TITLE,
              report_uri_list=config.BUG_REPORT_URI_LIST)(procedure)(run_mode, *args)
          else:
            return procedure(run_mode, *args)
        
        return types.MethodType(procedure_wrapper, self, self.__class__)
      
      procedure = getattr(self, procedure_name)
      setattr(self, procedure_name, _set_gui_excepthook_wrapper(procedure))
