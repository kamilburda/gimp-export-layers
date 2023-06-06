# -*- coding: utf-8 -*-

"""Steps to upgrade the plug-in to the latest version (e.g. due to files or
settings being reorganized or removed).
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import ast
import collections
import os
import re
import shutil
import types

import pygtk
pygtk.require('2.0')
import gtk

import gimp
from gimp import pdb
import gimpenums

from export_layers import pygimplib as pg

from export_layers import actions as actions_
from export_layers import builtin_constraints
from export_layers import builtin_procedures
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
  
  persistent_sources = _get_persistent_sources(sources)
  
  if _is_fresh_start(persistent_sources):
    _save_plugin_version(settings, sources)
    return FRESH_START, ''
  
  current_version = pg.version.Version.parse(pg.config.PLUGIN_VERSION)
  
  status, message = pg.setting.Persistor.load([settings['main/plugin_version']], sources)
  
  if status == pg.setting.Persistor.READ_FAIL:
    fix_element_paths_for_pickle(
      sources, _FIX_PICKLE_HANDLERS, current_version, pg.config.SOURCE_NAME.encode('utf-8'))
    
    status, message = pg.setting.Persistor.load([settings['main/plugin_version']], sources)
  
  previous_version = pg.version.Version.parse(settings['main/plugin_version'].value)
  
  if status == pg.setting.Persistor.SUCCESS and previous_version == current_version:
    return NO_ACTION, message
  
  if (status == pg.setting.Persistor.SUCCESS
      and previous_version >= MIN_VERSION_WITHOUT_CLEAN_REINSTALL):
    _save_plugin_version(settings, sources)
    
    handle_update(settings, sources, _UPDATE_HANDLERS, previous_version, current_version)
    
    return UPDATE, message
  
  if handle_invalid == 'ask_to_clear':
    response = messages.display_message(
      _('Due to significant changes in the plug-in, settings need to be reset. Proceed?'),
      gtk.MESSAGE_WARNING,
      buttons=gtk.BUTTONS_YES_NO,
      button_response_id_to_focus=gtk.RESPONSE_NO)
    
    if response == gtk.RESPONSE_YES:
      clear_setting_sources(settings, sources)
      return CLEAR_SETTINGS, message
    else:
      return ABORT, message
  elif handle_invalid == 'clear':
    clear_setting_sources(settings, sources)
    return CLEAR_SETTINGS, message
  else:
    return ABORT, message


def _get_persistent_sources(sources):
  try:
    persistent_sources = sources['persistent']
  except KeyError:
    raise ValueError('at least one persistent source must be specified to run update()')
  
  if not isinstance(persistent_sources, collections.Iterable):
    return [persistent_sources]
  else:
    return persistent_sources


def clear_setting_sources(settings, sources=None):
  if sources is None:
    sources = pg.setting.Persistor.get_default_setting_sources()
  
  pg.setting.Persistor.clear(sources)
  
  _save_plugin_version(settings, sources)


def handle_update(settings, sources, update_handlers, previous_version, current_version):
  for version_str, update_handler in update_handlers.items():
    if previous_version < pg.version.Version.parse(version_str) <= current_version:
      update_handler(settings, sources)


def fix_element_paths_for_pickle(sources, fix_pickle_handlers, current_version, key):
  for version_str, fix_pickle_handler in fix_pickle_handlers.items():
    if pg.version.Version.parse(version_str) <= current_version:
      fix_pickle_handler(sources, key)


def rename_settings(settings_to_rename, sources):
  for source in sources.values():
    data = source.read_data_from_source()
    
    if data:
      for orig_setting_name, new_setting_name in settings_to_rename:
        if orig_setting_name in data:
          data[new_setting_name] = data[orig_setting_name]
          del data[orig_setting_name]
      
      source.write_data_to_source(data)


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


def _refresh_actions(
      actions_list, actions_root, old_action_prefix, new_action_prefix, builtin_actions_dict):
  removed_actions = []
  
  for index, action in enumerate(actions_list):
    if action.name.startswith(old_action_prefix):
      removed_actions.append((index, action))
      actions_.remove(actions_root, action.name)
  
  for index, removed_action in removed_actions:
    if new_action_prefix in builtin_actions_dict:
      action_dict = builtin_actions_dict[new_action_prefix]
      action_dict['enabled'] = removed_action['enabled'].value
      action = actions_.add(actions_root, action_dict)
      actions_.reorder(actions_root, action.name, index)
  
  return removed_actions


def _remove_actions(actions_list, actions_root, action_prefix):
  removed_actions_and_indexes = []
  
  for index, action in enumerate(actions_list):
    if action.name.startswith(action_prefix):
      actions_.remove(actions_root, action.name)
      removed_actions_and_indexes.append((action, index))
  
  return removed_actions_and_indexes


def _rename_generic_setting_in_actions(actions_list, actions, orig_name, new_name, new_type):
  for action in actions_list:
    if orig_name in action:
      if new_name in action:
        action[new_name].set_value(action[orig_name].value)
      else:
        action.add([
          {
            'type': new_type,
            'name': new_name,
            'default_value': action[orig_name].value,
            'gui_type': None,
          },
        ])
      
      action.remove([orig_name])
  
  for added_data_dict in actions['_added_data'].value:
    if orig_name in added_data_dict:
      added_data_dict[new_name] = added_data_dict[orig_name]
      del added_data_dict[orig_name]
  
  added_data_values_keys_to_rename = [
    key for key in actions['_added_data_values'].value
    if key.endswith(pg.setting.SETTING_PATH_SEPARATOR + orig_name)
  ]
  for key in added_data_values_keys_to_rename:
    new_key = re.sub(
      pg.setting.SETTING_PATH_SEPARATOR + orig_name + r'$',
      pg.setting.SETTING_PATH_SEPARATOR + new_name,
      key)
    actions['_added_data_values'].value[new_key] = actions['_added_data_values'].value[key]
    del actions['_added_data_values'].value[key]


def _get_action_settings(settings):
  return [
    setting for setting in settings.walk()
    if isinstance(setting, pg.setting.Setting) and 'action' in setting.parent.tags
  ]


def _get_actions(settings):
  return [
    setting for setting in settings.walk(include_groups=True)
    if isinstance(setting, pg.setting.Group) and 'action' in setting.tags
  ]


def _is_fresh_start(persistent_sources):
  return all(not source.has_data() for source in persistent_sources)


def _save_plugin_version(settings, sources):
  settings['main/plugin_version'].reset()
  pg.setting.Persistor.save([settings['main/plugin_version']], sources)


def _try_remove_file(filepath):
  try:
    os.remove(filepath)
  except Exception:
    pass


def _update_to_3_3_1(settings, sources):
  rename_settings(
    [
      ('gui/export_name_preview_sensitive',
       'gui/name_preview_sensitive'),
      ('gui/export_image_preview_sensitive',
       'gui/image_preview_sensitive'),
      ('gui/export_image_preview_automatic_update',
       'gui/image_preview_automatic_update'),
      ('gui/export_image_preview_automatic_update_if_below_maximum_duration',
       'gui/image_preview_automatic_update_if_below_maximum_duration'),
      ('gui_session/export_name_preview_layers_collapsed_state',
       'gui_session/name_preview_layers_collapsed_state'),
      ('gui_session/export_image_preview_displayed_layers',
       'gui_session/image_preview_displayed_layers'),
      ('gui_persistent/export_name_preview_layers_collapsed_state',
       'gui_persistent/name_preview_layers_collapsed_state'),
      ('gui_persistent/export_image_preview_displayed_layers',
       'gui_persistent/image_preview_displayed_layers'),
    ],
    sources)
  
  settings['main/layer_filename_pattern'].load(sources)
  settings['main/layer_filename_pattern'].set_value(
    replace_field_arguments_in_pattern(
      settings['main/layer_filename_pattern'].value,
      [
        ['layer name', 'keep extension', '%e'],
        ['layer name', 'keep only identical extension', '%i']
        ['image name', 'keep extension', '%e'],
        ['layer path', r'\$\$', '%c'],
        ['tags', r'\$\$', '%t'],
      ]))
  settings['main/layer_filename_pattern'].save(sources)


def _update_to_3_3_2(settings, sources):
  _remove_obsolete_pygimplib_files_3_3_2()
  _remove_obsolete_plugin_files_3_3_2()
  
  settings['main/layer_filename_pattern'].load(sources)
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
  settings['main/layer_filename_pattern'].save(sources)
  
  settings['main/procedures'].load(sources)
  settings['main/constraints'].load(sources)
  
  procedures = _get_actions(settings['main/procedures'])
  constraints = _get_actions(settings['main/constraints'])
  
  _refresh_actions(
    procedures,
    settings['main/procedures'],
    'use_file_extensions_in_layer_names',
    'use_file_extension_in_layer_name',
    builtin_procedures.BUILTIN_PROCEDURES,
  )
  
  _refresh_actions(
    procedures,
    settings['main/procedures'],
    'ignore_folder_structure',
    'ignore_folder_structure',
    builtin_procedures.BUILTIN_PROCEDURES,
  )
  
  _rename_generic_setting_in_actions(
    procedures, settings['main/procedures'], 'operation_groups', 'action_groups', 'list')
  _rename_generic_setting_in_actions(
    constraints, settings['main/constraints'], 'operation_groups', 'action_groups', 'list')
  
  settings['main/procedures'].save(sources)
  actions_.clear(settings['main/procedures'])
  settings['main/constraints'].save(sources)
  actions_.clear(settings['main/constraints'])


def _update_to_3_3_5(settings, sources):
  _try_remove_file(os.path.join(pg.config.PLUGIN_SUBDIRPATH, 'settings_plugin.py'))
  _try_remove_file(os.path.join(pg.config.PLUGIN_SUBDIRPATH, 'settings_plugin.pyc'))


def _update_to_3_4(settings, sources):
  _try_remove_file(os.path.join(pg.config.PLUGIN_SUBDIRPATH, 'exportlayers.py'))
  _try_remove_file(os.path.join(pg.config.PLUGIN_SUBDIRPATH, 'exportlayers.pyc'))
  _try_remove_file(os.path.join(pg.PYGIMPLIB_DIRPATH, 'executor.py'))
  _try_remove_file(os.path.join(pg.PYGIMPLIB_DIRPATH, 'executor.pyc'))
  
  rename_settings(
    [
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
    ],
    sources)
  
  settings['main/procedures'].load(sources)
  
  procedures = _get_actions(settings['main/procedures'])
  
  _refresh_actions(
    procedures,
    settings['main/procedures'],
    'rename_layer',
    'rename',
    builtin_procedures.BUILTIN_PROCEDURES,
  )
  
  removed_autocrop_background = _remove_actions(
    procedures, settings['main/procedures'], 'autocrop_background')
  if removed_autocrop_background:
    # While there may be multiple such procedures with different tags, only a
    # single procedure will be added back.
    old_action, old_action_index = removed_autocrop_background[0]
    new_action = actions_.add(settings['main/procedures'], pdb.plug_in_autocrop_layer)
    new_action['arguments/drawable'].set_value('background_layer')
    new_action['enabled'].set_value(old_action['enabled'].value)
    actions_.reorder(settings['main/procedures'], new_action, old_action_index)
  
  removed_autocrop_foreground = _remove_actions(
    procedures, settings['main/procedures'], 'autocrop_foreground')
  if removed_autocrop_foreground:
    # While there may be multiple such procedures with different tags, only a
    # single procedure will be added back.
    old_action, old_action_index = removed_autocrop_foreground[0]
    new_action = actions_.add(settings['main/procedures'], pdb.plug_in_autocrop_layer)
    actions_.reorder(settings['main/procedures'], new_action, old_action_index)
    new_action['arguments/drawable'].set_value('foreground_layer')
    new_action['enabled'].set_value(old_action['enabled'].value)
  
  removed_use_file_extension = _remove_actions(
    procedures, settings['main/procedures'], 'use_file_extension_in_item_name')
  if removed_use_file_extension:
    # Use the last removed action as the previous actions had no effect.
    old_action, old_action_index = removed_use_file_extension[-1]
    new_action = actions_.add(
      settings['main/procedures'], builtin_procedures.BUILTIN_PROCEDURES['export'])
    actions_.reorder(settings['main/procedures'], new_action, old_action_index)
    new_action['arguments/output_directory'].set_value(settings['main/output_directory'].value)
    new_action['arguments/file_extension'].set_value(settings['main/file_extension'].value)
    new_action['arguments/use_file_extension_in_item_name'].set_value(old_action['enabled'].value)
  
  for action in actions_.walk(settings['main/procedures']):
    if action.get_value('is_pdb_procedure', False):
      action['origin'].set_item('gimp_pdb')
    
    if action['origin'].is_item('builtin'):
      action['function'].set_value('')
  
  settings['main/procedures'].save(sources)
  
  actions_.clear(settings['main/procedures'])
  
  settings['main/constraints'].load(sources)
  
  constraints = _get_actions(settings['main/constraints'])
  
  removed_include_layers = _remove_actions(
    constraints, settings['main/constraints'], 'include_layers')
  removed_include_layer_groups = _remove_actions(
    constraints, settings['main/constraints'], 'include_layer_groups')
  _remove_actions(constraints, settings['main/constraints'], 'include_empty_layer_groups')
  
  if (not removed_include_layers
      or (removed_include_layers
          and not removed_include_layers[0][0]['enabled'].value)):
    actions_.add(
      settings['main/constraints'], builtin_constraints.BUILTIN_CONSTRAINTS['layer_groups'])
  
  if (not removed_include_layer_groups
      or (removed_include_layer_groups
          and not removed_include_layer_groups[0][0]['enabled'].value)):
    actions_.add(
      settings['main/constraints'], builtin_constraints.BUILTIN_CONSTRAINTS['layers'])
  
  _refresh_actions(
    constraints,
    settings['main/constraints'],
    'only_visible_layers',
    'visible',
    builtin_constraints.BUILTIN_CONSTRAINTS,
  )
  
  for action in actions_.walk(settings['main/constraints']):
    if action['orig_name'].value == 'visible':
      action['also_apply_to_parent_folders'].set_value(True)
  
  _refresh_actions(
    constraints,
    settings['main/constraints'],
    'only_toplevel_layers',
    'top_level',
    builtin_constraints.BUILTIN_CONSTRAINTS,
  )
  
  _refresh_actions(
    constraints,
    settings['main/constraints'],
    'only_layers_with_tags',
    'with_tags',
    builtin_constraints.BUILTIN_CONSTRAINTS,
  )
  
  _refresh_actions(
    constraints,
    settings['main/constraints'],
    'only_layers_without_tags',
    'without_tags',
    builtin_constraints.BUILTIN_CONSTRAINTS,
  )
  
  _refresh_actions(
    constraints,
    settings['main/constraints'],
    'only_layers_matching_file_extension',
    'matching_file_extension',
    builtin_constraints.BUILTIN_CONSTRAINTS,
  )
  
  _refresh_actions(
    constraints,
    settings['main/constraints'],
    'only_selected_layers',
    'selected_in_preview',
    builtin_constraints.BUILTIN_CONSTRAINTS,
  )
  
  for action in actions_.walk(settings['main/constraints']):
    if action.get_value('is_pdb_procedure', False):
      action['origin'].set_item('gimp_pdb')
    
    if action['origin'].is_item('builtin'):
      action['function'].set_value('')
    
    if 'subfilter' in action:
      action.remove(['subfilter'])
  
  settings['main/constraints'].save(sources)
  
  actions_.clear(settings['main/constraints'])


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


def _fix_pickle_paths(paths_to_rename, sources, key):
  for source in sources.values():
    if isinstance(source, pg.setting.sources.GimpShelfSource):
      _fix_pickle_paths_in_session_source(paths_to_rename, key)
    elif isinstance(source, pg.setting.sources.GimpParasiteSource):
      _fix_pickle_paths_in_persistent_source(paths_to_rename, key)
    elif isinstance(source, pg.setting.sources.PickleFileSource):
      _fix_pickle_paths_in_pickle_file_source(paths_to_rename, key, source)


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


def _fix_pickle_paths_in_pickle_file_source(paths_to_rename, key, source):
  # Silently ignore errors. The update will eventually throw an error later
  # outside this function which are properly handled and the error message is
  # displayed to the user.
  try:
    all_data = source.read_all_data()
  except Exception:
    return
  
  if all_data is None or key not in all_data:
    return
  
  contents = ast.literal_eval(all_data[key])
  
  new_contents = contents
  for old_path, new_path in paths_to_rename:
    new_contents = new_contents.replace(old_path, new_path)
  
  all_data[key] = repr(new_contents)
  
  try:
    source.write_all_data(all_data)
  except Exception:
    return


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
      (b'builtin_procedures\nuse_file_extension_in_layer_name',
       b'builtin_procedures\nuse_file_extension_in_item_name'),
      (b'builtin_procedures\nremove_folder_hierarchy_from_layer',
       b'builtin_procedures\nremove_folder_hierarchy_from_item'),
      (b'builtin_constraints\nis_layer_in_selected_layers',
       b'builtin_constraints\nis_item_in_selected_items'),
    ],
    sources, key)


def _fix_pickle_paths_3_4(sources, key):
  _fix_pickle_paths(
    [
      (b'export_layers.pygimplib.setting.settings\nSetting',
       b'export_layers.pygimplib.setting.settings\nGenericSetting'),
      (b'builtin_constraints\nis_empty_group',
       b'export_layers.pygimplib.utils\nempty_func'),
      (b'builtin_procedures\nuse_file_extension_in_item_name',
       b'export_layers.pygimplib.utils\nempty_func'),
      (b'builtin_procedures\ninsert_background_layer',
       b'background_foreground\ninsert_background_layer'),
      (b'builtin_procedures\ninsert_foreground_layer',
       b'background_foreground\ninsert_foreground_layer'),
      (b'builtin_procedures\nis_path_visible',
       b'builtin_procedures\nis_visible'),
      (b'builtin_procedures\nautocrop_tagged_layer',
       b'export_layers.pygimplib.utils\nempty_func'),
      (b'builtin_procedures\nuse_file_extension_in_item_name',
       b'export_layers.pygimplib.utils\nempty_func'),
    ],
    sources, key)


_UPDATE_HANDLERS = collections.OrderedDict([
  ('3.3.1', _update_to_3_3_1),
  ('3.3.2', _update_to_3_3_2),
  ('3.3.5', _update_to_3_3_5),
  ('3.4', _update_to_3_4),
])


_FIX_PICKLE_HANDLERS = collections.OrderedDict([
  ('3.3.2', _fix_pickle_paths_3_3_2),
  ('3.3.5', _fix_pickle_paths_3_3_5),
  ('3.4', _fix_pickle_paths_3_4),
])
