# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals

import inspect
import os
import sys
import traceback

PYGIMPLIB_DIRPATH = os.path.realpath(os.path.dirname(inspect.getfile(inspect.currentframe())))

try:
  import gimp
except ImportError:
  _gimp_dependent_modules_imported = False
else:
  _gimp_dependent_modules_imported = True

from . import logging


if _gimp_dependent_modules_imported:
  # Enable logging as early as possible to capture any unexpected errors (such
  # as missing modules) before pygimplib is fully initialized.
  logging.log_output(
    log_mode='exceptions',
    log_dirpaths=[os.path.dirname(PYGIMPLIB_DIRPATH), PYGIMPLIB_DIRPATH],
    log_stdout_filename=None,
    log_stderr_filename='error.log',
    log_header_title='pygimplib')

if _gimp_dependent_modules_imported:
  from . import _gui_messages
  
  _gui_messages.set_gui_excepthook(title=None, app_name=None)


def _setup_import_of_external_lib_modules(dirpath):
  """
  Add directory paths containing external libraries for pygimplib to `sys.path`
  so that modules from these external libraries can be imported as system
  modules (i.e. without using absolute or explicit relative imports).
  
  Modules with the same name that are already installed system-wide override the
  external library modules from `pygimplib`.
  """
  for filename in os.listdir(dirpath):
    external_libs_dirpath = os.path.join(dirpath, filename)
    if os.path.isdir(external_libs_dirpath) and external_libs_dirpath not in sys.path:
      sys.path.append(external_libs_dirpath)


_setup_import_of_external_lib_modules(os.path.join(PYGIMPLIB_DIRPATH, '_lib'))


from future.builtins import (
  ascii, bytes, chr, dict, filter, hex, input, int, list, map, next, object,
  oct, open, pow, range, round, str, super, zip)

import __builtin__
import collections
import gettext

from .constants import *

from . import utils
from . import version

if _gimp_dependent_modules_imported:
  import gimpenums
  import gimpui
  
  from . import invoker
  from . import fileformats
  from . import invocation
  from . import gui
  from . import itemtree
  from . import objectfilter
  from . import overwrite
  from . import path
  from . import pdbutils
  from . import progress
  from . import setting
  
  from gimp import pdb
  from .setting import SettingGuiTypes
  from .setting import SettingTypes

__all__ = [
  # Modules
  'logging',
  'utils',
  'version',
  # Global elements imported to or defined in this module
  'config',
  'init',
]

if _gimp_dependent_modules_imported:
  __all__.extend([
    # Modules
    'invoker',
    'fileformats',
    'invocation',
    'gui',
    'itemtree',
    'objectfilter',
    'overwrite',
    'path',
    'pdbutils',
    'progress',
    'setting',
    # Global elements imported to or defined in this module
    'pdb',
    'procedure',
    'main',
    'SettingGuiTypes',
    'SettingTypes',
  ])


config = None


class _Config(object):
  
  def __init__(self):
    super().__setattr__('_config', {})
  
  def __setattr__(self, name, value):
    self._config[name] = value
  
  def __getattr__(self, name):
    if name not in self._config:
      raise AttributeError('configuration entry "{}" not found'.format(name))
    
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
  
  def _get_domain_name(root_plugin_dirpath):
    if root_plugin_dirpath is None:
      return 'gimp20-python'
    else:
      return 'gimp-plugin-' + config.PLUGIN_NAME.replace('_', '-')
  
  config = _Config()
  
  config.PYGIMPLIB_DIRPATH = PYGIMPLIB_DIRPATH
  
  root_plugin_dirpath = _get_root_plugin_dirpath()
  
  if root_plugin_dirpath is not None:
    config._DEFAULT_PLUGIN_NAME = os.path.basename(root_plugin_dirpath)
    config.PLUGIN_DIRPATH = root_plugin_dirpath
    config.PLUGINS_DIRPATH = os.path.dirname(root_plugin_dirpath)
    config.DEFAULT_LOGS_DIRPATH = lambda: config.PLUGIN_DIRPATH
  else:
    # Fallback in case root_plugin_dirpath is None for some reason
    config._DEFAULT_PLUGIN_NAME = 'gimp_plugin'
    config.PLUGIN_DIRPATH = os.path.dirname(PYGIMPLIB_DIRPATH)
    config.PLUGINS_DIRPATH = os.path.dirname(config.PLUGIN_DIRPATH)
    config.DEFAULT_LOGS_DIRPATH = os.path.dirname(PYGIMPLIB_DIRPATH)
  
  config.PLUGIN_NAME = config._DEFAULT_PLUGIN_NAME
  config.PLUGIN_TITLE = lambda: config.PLUGIN_NAME
  config.PLUGIN_VERSION = '1.0'
  
  config.LOCALE_DIRPATH = (
    lambda: os.path.join(config.PLUGINS_DIRPATH, config.PLUGIN_NAME, 'locale'))
  config.DOMAIN_NAME = lambda: _get_domain_name(root_plugin_dirpath)
  
  config.BUG_REPORT_URL_LIST = []
  
  if _gimp_dependent_modules_imported:
    config.LOG_MODE = 'exceptions'
  else:
    config.LOG_MODE = 'none'
  
  _init_config_builtin(config)
  
  _init_config_from_file()
  
  _init_config_builtin_delayed(config)


def _get_root_plugin_dirpath():
  frame_stack = inspect.stack()
  
  if frame_stack:
    return os.path.dirname(frame_stack[-1][1])
  else:
    return None


def _init_config_builtin(config):
  config.PLUGINS_LOG_DIRPATHS = []
  config.PLUGINS_LOG_DIRPATHS.append(config.DEFAULT_LOGS_DIRPATH)
  
  if _gimp_dependent_modules_imported:
    plugins_dirpath_alternate = os.path.join(gimp.directory, 'plug-ins')
    if plugins_dirpath_alternate != config.DEFAULT_LOGS_DIRPATH:
      # Add `[user directory]/[GIMP directory]/plug-ins` as another log path in
      # case the plug-in was installed system-wide and there is no permission to
      # create log files there.
      config.PLUGINS_LOG_DIRPATHS.append(plugins_dirpath_alternate)
  
  config.PLUGINS_LOG_STDOUT_DIRPATH = config.DEFAULT_LOGS_DIRPATH
  config.PLUGINS_LOG_STDERR_DIRPATH = config.DEFAULT_LOGS_DIRPATH
  
  config.PLUGINS_LOG_STDOUT_FILENAME = 'output.log'
  config.PLUGINS_LOG_STDERR_FILENAME = 'error.log'
  
  config.GIMP_CONSOLE_MESSAGE_DELAY_MILLISECONDS = 50


def _init_config_from_file():
  orig_builtin_c = None
  if hasattr(__builtin__, 'c'):
    orig_builtin_c = __builtin__.c
  
  __builtin__.c = config
  
  try:
    # Prefer a development version of config if it exists. This is handy if you
    # need to keep a clean config in the remote repository and a local config
    # for development purposes.
    from .. import config_dev as plugin_config
  except ImportError:
    try:
      from .. import config as plugin_config
    except ImportError:
      pass
  
  if orig_builtin_c is None:
    del __builtin__.c
  else:
    __builtin__.c = orig_builtin_c


def _init_config_builtin_delayed(config):
  
  def _get_setting_source_name():
    if config.PLUGIN_NAME.startswith('plug_in'):
      return config.PLUGIN_NAME
    else:
      return 'plug_in_' + config.PLUGIN_NAME
  
  if _gimp_dependent_modules_imported:
    config.SOURCE_NAME = _get_setting_source_name()
    config.SESSION_SOURCE = setting.GimpShelfSource(config.SOURCE_NAME)
    config.PERSISTENT_SOURCE = setting.GimpParasiteSource(config.SOURCE_NAME)
    
    setting.persistor.Persistor.set_default_setting_sources(collections.OrderedDict([
      ('session', config.SESSION_SOURCE),
      ('persistent', config.PERSISTENT_SOURCE)]))
  
  gettext.install(config.DOMAIN_NAME, config.LOCALE_DIRPATH, unicode=True)
  
  if _gimp_dependent_modules_imported or config.LOG_MODE != 'gimp_console':
    logging.log_output(
      config.LOG_MODE, config.PLUGINS_LOG_DIRPATHS,
      config.PLUGINS_LOG_STDOUT_FILENAME, config.PLUGINS_LOG_STDERR_FILENAME,
      config.PLUGIN_TITLE, config.GIMP_CONSOLE_MESSAGE_DELAY_MILLISECONDS)


_init_config()


if _gimp_dependent_modules_imported:
  
  _procedures = collections.OrderedDict()
  _procedures_names = collections.OrderedDict()
  
  def procedure(**kwargs):
    """Installs a function as a GIMP procedure.
    
    Use this function as a decorator over a function to be exposed to the GIMP
    procedural database (PDB).
    
    The installed procedure can then be accessed via the GIMP (PDB) and,
    optionally, from the GIMP user interface.
    
    The function name is used as the procedure name as found in the GIMP PDB.
    
    The following keyword arguments are accepted:
    
    * `blurb` - Short description of the procedure.
    
    * `description` - More detailed information about the procedure.
    
    * `author` - Author of the plug-in.
    
    * `copyright_holder` - Copyright holder of the plug-in.
    
    * `date` - Dates (usually years) at which the plug-in development was
      active.
    
    * `menu_name` - Name of the menu entry in the GIMP user interface.
    
    * `menu_path` - Path of the menu entry in the GIMP user interface.
    
    * `image_types` - Image types to which the procedure applies (e.g. RGB or
      indexed). Defaults to `'*'` (any image type).
    
    * `parameters` - Procedure parameters. This is a list of tuples of three
      elements: `(PDB type, name, description)`. Alternatively, you may pass a
      `setting.Group` instance or a list of `setting.Group` instances containing
      plug-in settings.
    
    * `return_values` - Return values of the procedure, usable when calling the
      procedure programmatically. The format of `return_values` is the same as
      `parameters`.
    
    Example:
      
      import pygimplib as pg
      
      \@pg.procedure(
        blurb='Export layers as separate images',
        author='John Doe',
        menu_name=_('E_xport Layers...'),
        menu_path='<Image>/File/Export',
        parameters=[
          (gimpenums.PDB_INT32, 'run-mode', 'The run mode'),
          (gimpenums.PDB_IMAGE, 'image', 'The current image'),
          (gimpenums.PDB_STRING, 'dirpath', 'Output directory path')]
      )
      def plug_in_export_layers(run_mode, image, *args):
        ...
    """
    
    def procedure_wrapper(procedure):
      _procedures[procedure] = kwargs
      _procedures_names[procedure.__name__] = procedure
      return procedure
    
    return procedure_wrapper
  
  def main():
    """Enables installation and running of GIMP procedures.
    
    Call this function at the end of your main plug-in file.
    """
    gimp.main(None, None, _query, _run)
  
  def _install_procedure(
        procedure,
        blurb='',
        description='',
        author='',
        copyright_notice='',
        date='',
        menu_name='',
        menu_path=None,
        image_types='*',
        parameters=None,
        return_values=None):
    
    def _get_pdb_params(params):
      pdb_params = []
      
      if params:
        has_settings = isinstance(
          params[0], (setting.Setting, setting.Group))
        if has_settings:
          pdb_params = setting.create_params(*params)
        else:
          pdb_params = params
      
      return pdb_params
    
    gimp.install_procedure(
      procedure.__name__,
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
      gimp.menu_register(procedure.__name__, menu_path)
  
  def _query():
    gimp.domain_register(config.DOMAIN_NAME, config.LOCALE_DIRPATH)
    
    for procedure, kwargs in _procedures.items():
      _install_procedure(procedure, **kwargs)
  
  def _run(procedure_name, procedure_params):
    procedure = _add_gui_excepthook(
      _procedures_names[procedure_name], procedure_params[0])
    
    if hasattr(gimpui, 'gimp_ui_init'):
      gimpui.gimp_ui_init()
    
    procedure(*procedure_params)
  
  def _add_gui_excepthook(procedure, run_mode):
    if run_mode == gimpenums.RUN_INTERACTIVE:
      gui.set_gui_excepthook_additional_callback(
        _display_message_on_setting_value_error)
      
      add_gui_excepthook_func = gui.add_gui_excepthook(
        title=config.PLUGIN_TITLE,
        app_name=config.PLUGIN_TITLE,
        report_uri_list=config.BUG_REPORT_URL_LIST)
      
      return add_gui_excepthook_func(procedure)
    else:
      return procedure
  
  def _display_message_on_setting_value_error(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, setting.SettingValueError):
      gimp.message(utils.safe_encode_gimp(str(exc_value)))
      return True
    else:
      return False
