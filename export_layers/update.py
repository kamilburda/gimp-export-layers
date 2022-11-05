# -*- coding: utf-8 -*-

"""Steps to upgrade the plug-in to the latest version (e.g. due to files or
settings being reorganized or removed).
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import collections
import os
import re
import shutil
import types

import pygtk
pygtk.require('2.0')
import gtk

import gimp
import gimpenums

from export_layers import pygimplib as pg

from export_layers import actions as actions_
from export_layers import builtin_procedures
from export_layers.gui import messages


MIN_VERSION_WITHOUT_CLEAN_REINSTALL = pg.version.Version.parse('3.3')

_UPDATE_STATUSES = (FRESH_START, UPDATE, CLEAR_SETTINGS, NO_ACTION, ABORT) = (0, 1, 2, 3, 4)


def update(settings, prompt_on_clear=False):
  """
  Update to the latest version of the plug-in. This includes renaming settings
  or replacing obsolete procedures.
  
  Return one of the following values:
  
  * `FRESH_START` - The plug-in was never used before or has no settings stored.
  
  * `UPDATE` - The plug-in was successfully updated to the latest version.
  
  * `CLEAR_SETTINGS` - An old version of the plug-in (incompatible with the
    changes in later versions) was used that required clearing stored settings.
  
  * `NO_ACTION` - No update was performed as the plug-in version remains the
    same.
  
  * `ABORT` - No update was performed. This value is returned if the user
    cancelled clearing settings interactively.
  
  If `prompt_on_clear` is `True` and the plug-in requires clearing settings,
  display a message dialog to prompt the user to proceed with clearing. If 'No'
  is chosen, do not clear settings and return `ABORT`.
  """
  if _is_fresh_start():
    _save_plugin_version(settings)
    return FRESH_START
  
  current_version = pg.version.Version.parse(pg.config.PLUGIN_VERSION)
  
  status, unused_ = pg.setting.Persistor.load(
    [settings['main/plugin_version']], [pg.config.PERSISTENT_SOURCE])
  
  if (status == pg.setting.Persistor.READ_FAIL
      and current_version >= pg.version.Version(3, 3, 2)):
    _fix_module_paths_in_parasites_3_3_2()
    
    status, unused_ = pg.setting.Persistor.load(
      [settings['main/plugin_version']], [pg.config.PERSISTENT_SOURCE])
  
  previous_version = pg.version.Version.parse(settings['main/plugin_version'].value)
  
  if status == pg.setting.Persistor.SUCCESS and previous_version == current_version:
    return NO_ACTION
  
  if (status == pg.setting.Persistor.SUCCESS
      and previous_version >= MIN_VERSION_WITHOUT_CLEAN_REINSTALL):
    _save_plugin_version(settings)
    
    handle_update(settings, _UPDATE_HANDLERS, previous_version, current_version)
    
    return UPDATE
  
  if prompt_on_clear:
    response = messages.display_message(
      _('Due to significant changes in the plug-in, settings need to be reset. Proceed?'),
      gtk.MESSAGE_WARNING,
      buttons=gtk.BUTTONS_YES_NO,
      button_response_id_to_focus=gtk.RESPONSE_NO)
    
    if response == gtk.RESPONSE_YES:
      clear_setting_sources(settings)
      return CLEAR_SETTINGS
    else:
      return ABORT
  else:
    clear_setting_sources(settings)
    return CLEAR_SETTINGS


def clear_setting_sources(settings, sources=None):
  if sources is None:
    sources = [pg.config.SESSION_SOURCE, pg.config.PERSISTENT_SOURCE]
  
  pg.setting.Persistor.clear(sources)
  
  _save_plugin_version(settings)


def handle_update(settings, update_handlers, previous_version, current_version):
  for version_str, update_handler in update_handlers.items():
    if previous_version < pg.version.Version.parse(version_str) <= current_version:
      update_handler(settings)


def rename_settings(settings_to_rename):
  for source in [pg.config.SESSION_SOURCE, pg.config.PERSISTENT_SOURCE]:
    data_dict = source.read_dict()
    
    if data_dict:
      for orig_setting_name, new_setting_name in settings_to_rename:
        if orig_setting_name in data_dict:
          data_dict[new_setting_name] = data_dict[orig_setting_name]
          del data_dict[orig_setting_name]
      
      source.write_dict(data_dict)


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


def _update_to_3_3_1(settings):
  rename_settings([
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
  ])
  
  settings['main/layer_filename_pattern'].load()
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
  settings['main/layer_filename_pattern'].save()


def _update_to_3_3_2(settings):
  _remove_obsolete_pygimplib_files_3_3_2()
  _remove_obsolete_plugin_files_3_3_2()
  
  settings['main/layer_filename_pattern'].load()
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
  settings['main/layer_filename_pattern'].save()
  
  settings['main/procedures'].load()
  settings['main/constraints'].load()
  
  procedures = _get_actions(settings['main/procedures'])
  constraints = _get_actions(settings['main/constraints'])
  
  _refresh_actions(
    procedures,
    settings['main/procedures'],
    'use_file_extensions_in_layer_names',
    'use_file_extension_in_layer_name',
  )
  
  _refresh_actions(
    procedures,
    settings['main/procedures'],
    'ignore_folder_structure',
    'ignore_folder_structure',
  )
  
  _rename_generic_setting_in_actions(
    procedures, settings['main/procedures'], 'operation_groups', 'action_groups')
  _rename_generic_setting_in_actions(
    constraints, settings['main/constraints'], 'operation_groups', 'action_groups')
  
  settings['main/procedures'].save()
  actions_.clear(settings['main/procedures'])
  settings['main/constraints'].save()
  actions_.clear(settings['main/constraints'])


def _update_to_3_4(settings):
  plugin_subdirectory_dirpath = pg.config.PLUGIN_SUBDIRPATH
  _try_remove_file(os.path.join(plugin_subdirectory_dirpath, 'settings_plugin.py'))
  _try_remove_file(os.path.join(plugin_subdirectory_dirpath, 'settings_plugin.pyc'))


def _refresh_actions(actions_list, actions_root, old_action_prefix, new_action_prefix):
  removed_actions = []
  for index, action in enumerate(actions_list):
    if action.name.startswith(old_action_prefix):
      removed_actions.append((index, action))
      actions_.remove(actions_root, action.name)
  
  for index, removed_action in removed_actions:
    action_dict = builtin_procedures.BUILTIN_PROCEDURES[new_action_prefix]
    action_dict['enabled'] = removed_action['enabled'].value
    action = actions_.add(actions_root, action_dict)
    actions_.reorder(actions_root, action.name, index)


def _rename_generic_setting_in_actions(actions_list, actions, orig_name, new_name):
  for action in actions_list:
    if orig_name in action:
      if new_name in action:
        action[new_name].set_value(action[orig_name].value)
      else:
        action.add([
          {
            'type': pg.SettingTypes.generic,
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


def _is_fresh_start():
  return not pg.config.PERSISTENT_SOURCE.has_data()


def _save_plugin_version(settings):
  settings['main/plugin_version'].reset()
  pg.setting.Persistor.save(
    [settings['main/plugin_version']], [pg.config.PERSISTENT_SOURCE])


def _try_remove_file(filepath):
  try:
    os.remove(filepath)
  except Exception:
    pass


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


def _fix_module_paths_in_parasites_3_3_2():
  key = b'plug_in_export_layers'
  paths_to_rename = [
    (b'export_layers.pygimplib.pgsetting', b'export_layers.pygimplib.setting'),
    (b'export_layers.pygimplib.pgutils', b'export_layers.pygimplib.utils'),
  ]
  
  persistent_parasite = gimp.parasite_find(key)
  if persistent_parasite is not None:
    new_data = persistent_parasite.data
    for old_path, new_path in paths_to_rename:
      new_data = new_data.replace(old_path, new_path)
    
    gimp.parasite_attach(
        gimp.Parasite('plug_in_export_layers', gimpenums.PARASITE_PERSISTENT, new_data))
  
  try:
    session_parasite = gimp.get_data(key)
  except gimp.error:
    session_parasite = None
  
  if session_parasite:
    new_data = session_parasite
    for old_path, new_path in paths_to_rename:
      new_data = new_data.replace(old_path, new_path)
    
    gimp.set_data(key, new_data)


_UPDATE_HANDLERS = collections.OrderedDict([
  ('3.3.1', _update_to_3_3_1),
  ('3.3.2', _update_to_3_3_2),
  ('3.4', _update_to_3_4),
])
