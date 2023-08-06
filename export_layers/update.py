# -*- coding: utf-8 -*-

"""Steps to upgrade the plug-in to the latest version (e.g. due to files or
settings being reorganized or removed).
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import collections
import os
import pickle
import re
import shutil
import types

import pygtk
pygtk.require('2.0')
import gtk

import gimp
from gimp import pdb
import gimpenums
import gimpshelf

from export_layers import pygimplib as pg

from export_layers import actions as actions_
from export_layers import builtin_constraints
from export_layers import builtin_procedures
from export_layers import utils as utils_
from export_layers.gui import messages


MIN_VERSION_WITHOUT_CLEAN_REINSTALL = pg.version.Version.parse('3.3')

_UPDATE_STATUSES = FRESH_START, UPDATE, CLEAR_SETTINGS, NO_ACTION, ABORT = 0, 1, 2, 3, 4


def update(settings, handle_invalid='ask_to_clear', sources=None):
  """Updates settings and setting sources to the latest version of the plug-in.
  
  This includes renaming settings or replacing obsolete actions.
  
  `handle_invalid` is a string indicating how to handle a failed update:
    
    * `'ask_to_clear'` - a message is displayed asking the user whether to clear
      settings. If the user chose to clear the settings, `CLEAR_SETTINGS` is
      returned, `ABORT` otherwise.
    
    * `'clear'` - settings will be cleared unconditionally and `CLEAR_SETTINGS`
      is returned.
    
    * any other value - no action is taken and `ABORT` is returned.
  
  If `sources` is `None`, default setting sources are updated. Otherwise,
  `sources` must be a dictionary of (key, source) pairs.
  
  Two values are returned - status and an accompanying message.
  
  Status can have one of the following integer values:
  
  * `FRESH_START` - The plug-in was never used before or has no settings stored.
  
  * `UPDATE` - The plug-in was successfully updated to the latest version.
  
  * `CLEAR_SETTINGS` - An old version of the plug-in (incompatible with the
    changes in later versions) was used that required clearing stored settings.
  
  * `NO_ACTION` - No update was performed as the plug-in version remains the
    same.
  
  * `ABORT` - No update was performed. This value is returned if the user
    cancelled clearing settings interactively.
  """
  if sources is None:
    sources = pg.setting.Persistor.get_default_setting_sources()
  
  if _is_fresh_start(sources):
    utils_.save_plugin_version(settings, sources)
    return FRESH_START, ''
  
  current_version = pg.version.Version.parse(pg.config.PLUGIN_VERSION)
  
  previous_version, load_status, load_message, are_procedures_loaded, are_constraints_loaded = (
    _get_version_from_sources_and_load_settings(settings, sources, current_version))
  
  if load_status == pg.setting.Persistor.SUCCESS and previous_version == current_version:
    return NO_ACTION, load_message
  
  if (load_status == pg.setting.Persistor.SUCCESS
      and previous_version >= MIN_VERSION_WITHOUT_CLEAN_REINSTALL):
    settings['main/plugin_version'].reset()
    
    handle_update(
      settings,
      sources,
      _UPDATE_HANDLERS,
      previous_version,
      current_version,
      are_procedures_loaded,
      are_constraints_loaded)
    
    return UPDATE, load_message
  
  if handle_invalid == 'ask_to_clear':
    response = messages.display_message(
      _('Due to significant changes in the plug-in, settings need to be reset. Proceed?'),
      gtk.MESSAGE_WARNING,
      buttons=gtk.BUTTONS_YES_NO,
      button_response_id_to_focus=gtk.RESPONSE_NO)
    
    if response == gtk.RESPONSE_YES:
      utils_.clear_setting_sources(settings, sources)
      return CLEAR_SETTINGS, load_message
    else:
      return ABORT, load_message
  elif handle_invalid == 'clear':
    utils_.clear_setting_sources(settings, sources)
    return CLEAR_SETTINGS, load_message
  else:
    return ABORT, load_message


def _get_version_from_sources_and_load_settings(settings, sources, current_version):
  key = pg.config.SOURCE_NAME.encode('utf-8')
  previous_version = _parse_version_using_old_format(sources, key)
  
  are_procedures_loaded = False
  are_constraints_loaded = False
  
  if previous_version is not None:
    are_procedures_loaded, are_constraints_loaded, error_message = _load_settings_with_old_format(
      settings, sources, current_version)
    
    if not error_message:
      load_status = pg.setting.Persistor.SUCCESS
      load_message = ''
    else:
      load_status = pg.setting.Persistor.FAIL
      load_message = error_message
  else:
    load_result = settings['main/plugin_version'].load()
    
    if any(status == pg.setting.Persistor.SOURCE_NOT_FOUND
           for status in load_result.statuses_per_source.values()):
      # Missing sources in this case should be ignored.
      load_status = pg.setting.Persistor.SUCCESS
    else:
      load_status = load_result.status
    
    load_message = '\n'.join(load_result.messages_per_source.values())
    previous_version = pg.version.Version.parse(settings['main/plugin_version'].value)
  
  return previous_version, load_status, load_message, are_procedures_loaded, are_constraints_loaded


def _parse_version_using_old_format(sources, key):
  parsed_version = None
  
  for source in sources.values():
    if isinstance(source, pg.setting.sources.GimpShelfSource):
      parsed_version = _parse_version_from_session_source(key)
    elif isinstance(source, pg.setting.sources.GimpParasiteSource):
      parsed_version = _parse_version_from_persistent_source(key)
    
    if parsed_version is not None:
      break
  
  if parsed_version is not None:
    return pg.version.Version.parse(parsed_version)
  else:
    return None


def _parse_version_from_session_source(key):
  try:
    session_data = gimp.get_data(key)
  except gimp.error:
    return None
  else:
    return _parse_version(session_data)


def _parse_version_from_persistent_source(key):
  parasite = gimp.parasite_find(key)
  
  if parasite is not None:
    return _parse_version(parasite.data)
  else:
    return None


def _parse_version(str_):
  str_match = re.search(r'main/plugin_version.*?\n.*?\n.*?([0-9]+\.[0-9]+(\.[0-9]+)?)', str_)
  
  if str_match is not None:
    return str_match.groups()[0]
  else:
    return None


def _load_settings_with_old_format(settings, sources, current_version):
  fix_element_paths_for_pickle(
    sources, _FIX_PICKLE_HANDLERS, current_version, pg.config.SOURCE_NAME.encode('utf-8'))
  
  error_message = _rename_settings_with_specific_settings(sources)
  if error_message:
    return False, False, error_message
  
  _add_obsolete_settings(settings)
  
  settings_not_loaded = list(settings.walk())
  
  for source in sources.values():
    if isinstance(source, pg.setting.sources.GimpShelfSource):
      settings_not_loaded, error_message = _read_settings_with_old_format(
        settings_not_loaded, OldGimpShelfSource, 'session')
    elif isinstance(source, pg.setting.sources.GimpParasiteSource):
      settings_not_loaded, error_message = _read_settings_with_old_format(
        settings_not_loaded, OldGimpParasiteSource, 'persistent')
      
    if error_message:
      return False, False, error_message
  
  are_procedures_loaded = settings['main/procedures/_added_data'] not in settings_not_loaded
  _update_format_of_actions(settings['main/procedures'], are_procedures_loaded)
  
  are_constraints_loaded = settings['main/constraints/_added_data'] not in settings_not_loaded
  _update_format_of_actions(settings['main/constraints'], are_constraints_loaded)
  
  return are_procedures_loaded, are_constraints_loaded, error_message


def _rename_settings_with_specific_settings(sources):
  return _rename_settings(
    [
      ('gui/export_name_preview_sensitive',
       'gui/name_preview_sensitive'),
      ('gui/export_image_preview_sensitive',
       'gui/image_preview_sensitive'),
      ('gui/export_image_preview_automatic_update',
       'gui/image_preview_automatic_update'),
      ('gui/export_image_preview_automatic_update_if_below_maximum_duration',
       'gui/image_preview_automatic_update_if_below_maximum_duration'),
      ('gui/dialog_position',
       'gui/size/dialog_position'),
      ('gui/dialog_size',
       'gui/size/dialog_size'),
      ('gui/paned_outside_previews_position',
       'gui/size/paned_outside_previews_position'),
      ('gui/paned_between_previews_position',
       'gui/size/paned_between_previews_position'),
      ('gui/settings_vpane_position',
       'gui/size/settings_vpane_position'),
      ('gui_session/current_directory',
       'gui/current_directory'),
    ],
    sources)


def _rename_settings(settings_to_rename, sources):
  error_message = None
  
  for source in sources.values():
    try:
      data = source.read_data_from_source()
    except Exception as e:
      error_message = str(e)
      break
    
    if data:
      for orig_setting_name, new_setting_name in settings_to_rename:
        if orig_setting_name in data:
          data[new_setting_name] = data[orig_setting_name]
          del data[orig_setting_name]
      
      source.write_data_to_source(data)
  
  return error_message


def _add_obsolete_settings(settings):
  settings['main/procedures'].add([
    {
      'type': 'list',
      'name': '_added_data',
    },
    {
      'type': 'dict',
      'name': '_added_data_values',
    },
  ])
  
  settings['main/constraints'].add([
    {
      'type': 'list',
      'name': '_added_data',
    },
    {
      'type': 'dict',
      'name': '_added_data_values',
    },
  ])


def _read_settings_with_old_format(settings, source_class, source_type):
  source = source_class(pg.config.SOURCE_NAME, source_type)
  
  settings_not_loaded = settings
  error_message = None
  
  if source.has_data():
    try:
      settings_not_loaded = source.read(settings)
    except Exception as e:
      error_message = str(e)
  
  return settings_not_loaded, error_message


class OldSource(pg.setting.sources.Source):
  
  def read(self, settings):
    settings_not_loaded = []
    
    settings_from_source = self.read_data_from_source()
    if settings_from_source is None:
      return
    
    for setting in settings:
      try:
        value = settings_from_source[setting.get_path('root')]
      except KeyError:
        settings_not_loaded.append(setting)
      else:
        try:
          setting.set_value(value)
        except pg.setting.SettingValueError:
          setting.reset()
    
    return settings_not_loaded


class OldGimpShelfSource(OldSource):
  
  def clear(self):
    gimpshelf.shelf[self._get_key()] = None
  
  def has_data(self):
    return (
      gimpshelf.shelf.has_key(self._get_key())
      and gimpshelf.shelf[self._get_key()] is not None)
  
  def read_data_from_source(self):
    try:
      return gimpshelf.shelf[self._get_key()]
    except Exception:
      return None
  
  def write_data_to_source(self, setting_names_and_values):
    gimpshelf.shelf[self._get_key()] = setting_names_and_values
  
  def _get_key(self):
    return pg.utils.safe_encode_gimp(self.source_name)


class OldGimpParasiteSource(OldSource):
  
  def clear(self):
    if gimp.parasite_find(self.source_name) is None:
      return
    
    gimp.parasite_detach(self.source_name)
  
  def has_data(self):
    return gimp.parasite_find(self.source_name) is not None
  
  def read_data_from_source(self):
    parasite = gimp.parasite_find(self.source_name)
    if parasite is None:
      return None
    
    try:
      settings_from_source = pickle.loads(parasite.data)
    except Exception:
      return None
    
    return settings_from_source
  
  def write_data_to_source(self, setting_names_and_values):
    data = pickle.dumps(setting_names_and_values)
    gimp.parasite_attach(
      gimp.Parasite(self.source_name, gimpenums.PARASITE_PERSISTENT, data))


def _update_format_of_actions(actions, are_actions_loaded):
  action_dicts = actions['_added_data'].value
  setting_values = actions['_added_data_values'].value
  
  actions_.remove(actions, '_added_data')
  actions_.remove(actions, '_added_data_values')
  
  if are_actions_loaded:
    actions_.clear(actions, add_initial_actions=False)
  
  for action_dict in action_dicts:
    if 'type' in action_dict and action_dict['type'] == pg.setting.Setting:
      action_dict['type'] = pg.setting.GenericSetting
    
    if 'orig_name' not in action_dict:
      action_dict['orig_name'] = re.sub(r'_[0-9]+$', r'', action_dict['name'])
    
    if 'arguments' in action_dict:
      for argument_dict in action_dict['arguments']:
        if 'type' in argument_dict and argument_dict['type'] == pg.setting.Setting:
          argument_dict['type'] = pg.setting.GenericSetting
    
    if 'function' in action_dict and callable(action_dict['function']):
      # Built-in actions have their functions defined in the code.
      action_dict['function'] = ''
    
    if 'operation_groups' in action_dict:
      action_dict['action_groups'] = action_dict['operation_groups']
      
      del action_dict['operation_groups']
    
    if 'subfilter' in action_dict:
      del action_dict['subfilter']
    
    if 'is_pdb_procedure' in action_dict:
      if action_dict['is_pdb_procedure']:
        action_dict['origin'] = 'gimp_pdb'
      else:
        action_dict['origin'] = 'builtin'
      
      del action_dict['is_pdb_procedure']
    
    actions_.add(actions, action_dict)
  
  for path, value in setting_values.items():
    if path.endswith('/operation_groups'):
      path = re.sub(r'/operation_groups$', r'/action_groups', path)
    
    # Skip obsolete settings and settings guaranteed to be read-only.
    if any(path.endswith(suffix) for suffix in ['/is_pdb_procedure', '/subfilter', '/function']):
      continue
    
    if path in actions:
      actions[path].set_value(value)


def handle_update(
      settings,
      sources,
      update_handlers,
      previous_version,
      current_version,
      are_procedures_loaded,
      are_constraints_loaded):
  for source in sources.values():
    source.clear()
  
  for version_str, update_handler in update_handlers.items():
    if previous_version < pg.version.Version.parse(version_str) <= current_version:
      update_handler(settings, sources, are_procedures_loaded, are_constraints_loaded)
  
  settings.save(sources)


def fix_element_paths_for_pickle(sources, fix_pickle_handlers, current_version, key):
  for version_str, fix_pickle_handler in fix_pickle_handlers.items():
    if pg.version.Version.parse(version_str) <= current_version:
      fix_pickle_handler(sources, key)


def replace_field_arguments_in_pattern(
      pattern, field_regexes_arguments_and_replacements, as_lists=False):
  string_pattern = pg.path.StringPattern(
    pattern,
    fields={item[0]: lambda *args: None for item in field_regexes_arguments_and_replacements})
  
  processed_pattern_parts = []
  
  for part in string_pattern.pattern_parts:
    if isinstance(part, types.StringTypes):
      processed_pattern_parts.append(part)
    else:
      field_regex = part[0]
      new_arguments = []
      
      if len(part) > 1:
        if not as_lists:
          for argument in part[1]:
            new_argument = argument
            for item in field_regexes_arguments_and_replacements:
              if field_regex != item[0]:
                continue
              
              new_argument = re.sub(item[1], item[2], new_argument)
            
            new_arguments.append(new_argument)
        else:
          new_arguments = list(part[1])
          
          for item in field_regexes_arguments_and_replacements:
            if field_regex != item[0]:
              continue
          
            if len(item[1]) != len(part[1]):
              continue
            
            for i in range(len(item[1])):
              new_arguments[i] = re.sub(item[1][i], item[2][i], new_arguments[i])
            
            for i in range(len(item[1]), len(item[2])):
              new_arguments.append(item[2][i])
      
      processed_pattern_parts.append((field_regex, new_arguments))
  
  return pg.path.StringPattern.reconstruct_pattern(processed_pattern_parts)


def _refresh_actions(actions, old_action_prefix, new_action_prefix, builtin_actions_dict):
  removed_actions = []
  
  actions_list = list(actions)
  
  for index, action in enumerate(actions_list):
    if action.name.startswith(old_action_prefix):
      removed_actions.append((index, action))
      actions_.remove(actions, action.name)
  
  for index, removed_action in removed_actions:
    if new_action_prefix in builtin_actions_dict:
      action_dict = builtin_actions_dict[new_action_prefix]
      action_dict['enabled'] = removed_action['enabled'].value
      action = actions_.add(actions, action_dict)
      actions_.reorder(actions, action.name, index)
  
  return removed_actions


def _remove_actions(actions, action_prefix):
  removed_actions_and_indexes = []
  
  actions_list = list(actions)
  
  for index, action in enumerate(actions_list):
    if action.name.startswith(action_prefix):
      actions_.remove(actions, action.name)
      removed_actions_and_indexes.append((action, index))
  
  return removed_actions_and_indexes


def _get_actions(settings):
  return [
    setting for setting in settings.walk(include_groups=True)
    if isinstance(setting, pg.setting.Group) and 'action' in setting.tags
  ]


def _is_fresh_start(sources):
  return all(not source.has_data() for source in sources.values())


def _try_remove_file(filepath):
  try:
    os.remove(filepath)
  except Exception:
    pass


def _update_to_3_3_1(settings, sources, *args, **kwargs):
  settings['main/layer_filename_pattern'].set_value(
    replace_field_arguments_in_pattern(
      settings['main/layer_filename_pattern'].value,
      [
        ['layer name', 'keep extension', '%e'],
        ['layer name', 'keep only identical extension', '%i'],
        ['image name', 'keep extension', '%e'],
        ['layer path', r'\$\$', '%c'],
        ['tags', r'\$\$', '%t'],
      ]))


def _update_to_3_3_2(settings, sources, *args, **kwargs):
  _remove_obsolete_pygimplib_files_3_3_2()
  _remove_obsolete_plugin_files_3_3_2()
  
  settings['main/layer_filename_pattern'].set_value(
    replace_field_arguments_in_pattern(
      settings['main/layer_filename_pattern'].value,
      [
        ['layer path', [r'(.*)', r'(.*)'], [r'\1', r'\1', '%e']],
        ['layer path', [r'(.*)'], [r'\1', '%c', '%e']],
        ['layer path', [], ['-', '%c', '%e']],
      ],
      as_lists=True,
    ))
  
  _refresh_actions(
    settings['main/procedures'],
    'ignore_folder_structure',
    'ignore_folder_structure',
    builtin_procedures.BUILTIN_PROCEDURES,
  )


def _remove_obsolete_pygimplib_files_3_3_2():
  for filename in os.listdir(pg.PYGIMPLIB_DIRPATH):
    path = os.path.join(pg.PYGIMPLIB_DIRPATH, filename)
    
    if filename.startswith('pg') or filename.startswith('_pg'):
      if os.path.isfile(path):
        _try_remove_file(path)
      elif os.path.isdir(path):
        shutil.rmtree(path, ignore_errors=True)
    elif filename == 'lib':
      if os.path.isdir(path):
        shutil.rmtree(path, ignore_errors=True)


def _remove_obsolete_plugin_files_3_3_2():
  plugin_subdirectory_dirpath = pg.config.PLUGIN_SUBDIRPATH
  
  gui_package_dirpath = os.path.join(plugin_subdirectory_dirpath, 'gui')
  for filename in os.listdir(gui_package_dirpath):
    filepath = os.path.join(gui_package_dirpath, filename)
    
    if filename.startswith('gui_'):
      _try_remove_file(filepath)
  
  _try_remove_file(os.path.join(plugin_subdirectory_dirpath, 'operations.py'))
  _try_remove_file(os.path.join(plugin_subdirectory_dirpath, 'operations.pyc'))
  _try_remove_file(os.path.join(plugin_subdirectory_dirpath, 'gui', 'operations.py'))
  _try_remove_file(os.path.join(plugin_subdirectory_dirpath, 'gui', 'operations.pyc'))


def _update_to_3_3_5(settings, sources, *args, **kwargs):
  _try_remove_file(os.path.join(pg.config.PLUGIN_SUBDIRPATH, 'settings_plugin.py'))
  _try_remove_file(os.path.join(pg.config.PLUGIN_SUBDIRPATH, 'settings_plugin.pyc'))


def _update_to_4_0(settings, sources, are_procedures_loaded=True, are_constraints_loaded=True):
  _try_remove_file(os.path.join(pg.config.PLUGIN_SUBDIRPATH, 'exportlayers.py'))
  _try_remove_file(os.path.join(pg.config.PLUGIN_SUBDIRPATH, 'exportlayers.pyc'))
  _try_remove_file(os.path.join(pg.PYGIMPLIB_DIRPATH, 'executor.py'))
  _try_remove_file(os.path.join(pg.PYGIMPLIB_DIRPATH, 'executor.pyc'))
  
  if 'gui_session' in settings:
    settings.remove(['gui_session'])
  
  if 'gui_persistent' in settings:
    settings.remove(['gui_persistent'])
  
  if 'selected_layers_persistent' in settings['main']:
    settings['main'].remove(['selected_layers_persistent'])
  
  if are_procedures_loaded:
    _refresh_actions(
      settings['main/procedures'],
      'rename_layer',
      'rename',
      builtin_procedures.BUILTIN_PROCEDURES,
    )
    
    _update_autocrop_procedures(settings['main/procedures'])
    
    _update_use_file_extensions_in_layer_names_procedure(settings['main/procedures'], settings)
  
  if are_constraints_loaded:
    _update_include_constraints(settings['main/constraints'])
    
    _refresh_actions(
      settings['main/constraints'],
      'only_visible_layers',
      'visible',
      builtin_constraints.BUILTIN_CONSTRAINTS,
    )
    
    for action in actions_.walk(settings['main/constraints']):
      if action['orig_name'].value == 'visible':
        action['also_apply_to_parent_folders'].set_value(True)
    
    _refresh_actions(
      settings['main/constraints'],
      'only_toplevel_layers',
      'top_level',
      builtin_constraints.BUILTIN_CONSTRAINTS,
    )
    
    _refresh_actions(
      settings['main/constraints'],
      'only_layers_with_tags',
      'with_tags',
      builtin_constraints.BUILTIN_CONSTRAINTS,
    )
    
    _refresh_actions(
      settings['main/constraints'],
      'only_layers_without_tags',
      'without_tags',
      builtin_constraints.BUILTIN_CONSTRAINTS,
    )
    
    _refresh_actions(
      settings['main/constraints'],
      'only_layers_matching_file_extension',
      'matching_file_extension',
      builtin_constraints.BUILTIN_CONSTRAINTS,
    )
    
    _refresh_actions(
      settings['main/constraints'],
      'only_selected_layers',
      'selected_in_preview',
      builtin_constraints.BUILTIN_CONSTRAINTS,
    )


def _update_autocrop_procedures(procedures):
  removed_autocrop_background = _remove_actions(procedures, 'autocrop_background')
  if removed_autocrop_background:
    # While there may be multiple such procedures with different tags, only a
    # single procedure will be added back.
    old_action, old_action_index = removed_autocrop_background[0]
    new_action = actions_.add(procedures, pdb.plug_in_autocrop_layer)
    new_action['arguments/drawable'].set_value('background_layer')
    new_action['enabled'].set_value(old_action['enabled'].value)
    new_action['display_name'].set_value(old_action['display_name'].value)
    actions_.reorder(procedures, new_action.name, old_action_index)
  
  removed_autocrop_foreground = _remove_actions(procedures, 'autocrop_foreground')
  if removed_autocrop_foreground:
    # While there may be multiple such procedures with different tags, only a
    # single procedure will be added back.
    old_action, old_action_index = removed_autocrop_foreground[0]
    new_action = actions_.add(procedures, pdb.plug_in_autocrop_layer)
    actions_.reorder(procedures, new_action.name, old_action_index)
    new_action['arguments/drawable'].set_value('foreground_layer')
    new_action['enabled'].set_value(old_action['enabled'].value)
    new_action['display_name'].set_value(old_action['display_name'].value)


def _update_use_file_extensions_in_layer_names_procedure(procedures, settings):
  removed_use_file_extension = _remove_actions(procedures, 'use_file_extensions_in_layer_names')
  if removed_use_file_extension:
    # Use the last removed action as the previous actions had no effect.
    old_action, old_action_index = removed_use_file_extension[-1]
    new_action = actions_.add(procedures, builtin_procedures.BUILTIN_PROCEDURES['export'])
    actions_.reorder(procedures, new_action.name, old_action_index)
    new_action['arguments/output_directory'].set_value(settings['main/output_directory'].value)
    new_action['arguments/file_extension'].set_value(settings['main/file_extension'].value)
    new_action['arguments/use_file_extension_in_item_name'].set_value(old_action['enabled'].value)


def _update_include_constraints(constraints):
  _remove_actions(constraints, 'include_empty_layer_groups')
  
  removed_include_layers = _remove_actions(constraints, 'include_layers')
  
  if (not removed_include_layers
      or (removed_include_layers
          and not removed_include_layers[0][0]['enabled'].value)):
    new_action = actions_.add(
      constraints, builtin_constraints.BUILTIN_CONSTRAINTS['layer_groups'])
    if removed_include_layers:
      actions_.reorder(constraints, new_action.name, removed_include_layers[0][1])
      
  removed_include_layer_groups = _remove_actions(constraints, 'include_layer_groups')
  
  if (not removed_include_layer_groups
      or (removed_include_layer_groups
          and not removed_include_layer_groups[0][0]['enabled'].value)):
    new_action = actions_.add(constraints, builtin_constraints.BUILTIN_CONSTRAINTS['layers'])
    if removed_include_layer_groups:
      actions_.reorder(constraints, new_action.name, removed_include_layer_groups[0][1])


def _fix_pickle_paths(paths_to_rename, sources, key):
  for source in sources.values():
    if isinstance(source, pg.setting.sources.GimpShelfSource):
      _fix_pickle_paths_in_session_source(paths_to_rename, key)
    elif isinstance(source, pg.setting.sources.GimpParasiteSource):
      _fix_pickle_paths_in_persistent_source(paths_to_rename, key)


def _fix_pickle_paths_in_session_source(paths_to_rename, key):
  try:
    session_parasite = gimp.get_data(key)
  except gimp.error:
    pass
  else:
    new_data = session_parasite
    for old_path, new_path in paths_to_rename:
      new_data = new_data.replace(old_path, new_path)
    
    gimp.set_data(key, new_data)


def _fix_pickle_paths_in_persistent_source(paths_to_rename, key):
  persistent_parasite = gimp.parasite_find(key)
  if persistent_parasite is not None:
    new_data = persistent_parasite.data
    for old_path, new_path in paths_to_rename:
      new_data = new_data.replace(old_path, new_path)
    
    gimp.parasite_attach(gimp.Parasite(key, gimpenums.PARASITE_PERSISTENT, new_data))


def _fix_pickle_paths_3_3_2(sources, key):
  _fix_pickle_paths(
    [
      (b'export_layers.pygimplib.pgsetting', b'export_layers.pygimplib.setting'),
      (b'export_layers.pygimplib.pgutils', b'export_layers.pygimplib.utils'),
    ],
    sources, key)


def _fix_pickle_paths_3_3_5(sources, key):
  _fix_pickle_paths(
    [
      (b'export_layers.builtin_procedures\nuse_file_extension_in_layer_name',
       b'export_layers.builtin_procedures\nuse_file_extension_in_item_name'),
      (b'export_layers.builtin_procedures\nremove_folder_hierarchy_from_layer',
       b'export_layers.builtin_procedures\nremove_folder_hierarchy_from_item'),
      (b'export_layers.builtin_constraints\nis_layer_in_selected_layers',
       b'export_layers.builtin_constraints\nis_item_in_selected_items'),
    ],
    sources, key)


def _fix_pickle_paths_4_0(sources, key):
  _fix_pickle_paths(
    [
      (b'export_layers.pygimplib.setting.settings\nSetting',
       b'export_layers.pygimplib.setting.settings\nGenericSetting'),
      (b'export_layers.builtin_constraints\nis_empty_group',
       b'export_layers.pygimplib.utils\nempty_func'),
      (b'export_layers.builtin_procedures\nuse_file_extension_in_item_name',
       b'export_layers.pygimplib.utils\nempty_func'),
      (b'export_layers.builtin_procedures\ninsert_background_layer',
       b'export_layers.background_foreground\ninsert_background_layer'),
      (b'export_layers.builtin_procedures\ninsert_foreground_layer',
       b'export_layers.background_foreground\ninsert_foreground_layer'),
      (b'export_layers.builtin_constraints\nis_path_visible',
       b'export_layers.builtin_constraints\nis_visible'),
      (b'export_layers.builtin_procedures\nautocrop_tagged_layer',
       b'export_layers.pygimplib.utils\nempty_func'),
      (b'export_layers.builtin_procedures\nuse_file_extension_in_item_name',
       b'export_layers.pygimplib.utils\nempty_func'),
      (b'export_layers.pygimplib.setting.settings\nImageIdsAndDirectoriesSetting',
       b'export_layers.settings_custom\nImageIdsAndDirectoriesSetting'),
    ],
    sources, key)


_UPDATE_HANDLERS = collections.OrderedDict([
  ('3.3.1', _update_to_3_3_1),
  ('3.3.2', _update_to_3_3_2),
  ('3.3.5', _update_to_3_3_5),
  ('4.0', _update_to_4_0),
])


_FIX_PICKLE_HANDLERS = collections.OrderedDict([
  ('3.3.2', _fix_pickle_paths_3_3_2),
  ('3.3.5', _fix_pickle_paths_3_3_5),
  ('4.0', _fix_pickle_paths_4_0),
])
