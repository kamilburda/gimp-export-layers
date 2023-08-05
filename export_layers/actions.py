# -*- coding: utf-8 -*-

"""Creation and management of plug-in actions - procedures and constraints.

Most functions take a setting group containing actions as its first argument.

Many functions define events invoked on the setting group containing actions.
These events include:

* `'before-add-action'` - invoked when:
  * calling `add()` before adding an action,
  * calling `clear()` before resetting actions (due to initial actions
    being added back).
  
  Arguments: action dictionary to be added

* `'after-add-action'` - invoked when:
  * calling `add()` after adding an action,
  * calling `setting.Group.load()` or `setting.Persistor.load()` after loading
    an action (loading an action counts as adding).
  * calling `clear()` after resetting actions (due to initial actions
    being added back).
  
  Arguments:
  
  * created action,
  
  * original action dictionary (same as in `'before-add-action'`). When this
    event is triggered in `setting.Group.load()` or `setting.Persistor.load()`,
    this argument is `None` as there is no way to obtain the original
    dictionary.

* `'before-reorder-action'` - invoked when calling `reorder()` before
  reordering an action.
  
  Arguments: action, position before reordering

* `'after-reorder-action'` - invoked when calling `reorder()` after reordering
  an action.
  
  Arguments: action, position before reordering, new position

* `'before-remove-action'` - invoked when calling `remove()` before removing an
  action.
  
  Arguments: action to be removed

* `'after-remove-action'` - invoked when calling `remove()` after removing an
  action.
  
  Arguments: name of the removed action

* `'before-clear-actions'` - invoked when calling `clear()` before clearing
  actions.

* `'after-clear-actions'` - invoked when calling `clear()` after clearing
  actions.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import gimpenums

from export_layers import pygimplib as pg

from export_layers import placeholders


BUILTIN_TAGS = {
  'background': _('Background'),
  'foreground': _('Foreground'),
}

DEFAULT_PROCEDURES_GROUP = 'default_procedures'
DEFAULT_CONSTRAINTS_GROUP = 'default_constraints'

_DEFAULT_ACTION_TYPE = 'procedure'
_REQUIRED_ACTION_FIELDS = ['name']

_ACTIONS_AND_INITIAL_ACTION_DICTS = {}


def create(name, initial_actions=None):
  """Creates a `setting.Group` instance containing actions.
  
  Parameters:
  * `name` - name of the `setting.Group` instance.
  * `initial_actions` - list of dictionaries describing actions to be
    added by default. Calling `clear()` will reset the actions returned by
    this function to the initial actions. By default, no initial actions
    are added.
  
  Each created action in the returned group is a `setting.Group` instance. Each
  action contains the following settings or child groups:
  * `'function'` - Name of the function to call. If `'origin'` is `'builtin'`,
    then the function is an empty string and the function must be replaced
    during processing with a function object. This allows the function to be
    saved to a persistent setting source.
  * `'origin'` - Type of the function. If `'builtin'`, the function is defined
    directly in the plug-in. If `'gimp_pdb'`, the function is taken from the
    GIMP PDB. The origin affects how the function is modified (wrapped) during
    processing in the `batcher` module.
  * `'arguments'` - Arguments to `'function'` as a `setting.Group` instance
    containing arguments as separate `Setting` instances.
  * `'enabled'` - Whether the action should be applied or not.
  * `'display_name'` - The display name (human-readable name) of the action.
  * `'action_group'` - List of groups the action belongs to, used in
    `pygimplib.invoker.Invoker` and `batcher.Batcher`.
  * `'orig_name'` - The original name of the action. If an action with the
    same `'name'` field (see below) was previously added, the name of the new
    action is made unique to allow lookup of both actions. Otherwise,
    `'orig_name'` is equal to `'name'`.
  * `'tags'` - Additional tags added to each action (the `setting.Group`
    instance).
  * `'more_options_expanded'` - If `True`, display additional options for an
    action when editing the action interactively.
  * `'enabled_for_previews'` - If `True`, this indicates that the action can be
    applied in the preview.
  * `'display_options_on_create'` - If `True`, display action edit dialog upon
    adding an action interactively.
  
  Each dictionary in the `initial_actions` list may contain the following
  fields:
  * `'name'` - This field is required. This is the `name` attribute of the
    created action.
  * `'type'` - Action type. See below for details.
  * `'function'`
  * `'origin'`
  * `'arguments'` - Specified as list of dictionaries defining settings. Each
    dictionary must contain required attributes and can contain optional
    attributes as stated in `setting.Group.add()`.
  * `'enabled'`
  * `'display_name'`
  * `'action_group'`
  * `'tags'`
  * `'more_options_expanded'`
  * `'enabled_for_previews'`
  * `'display_options_on_create'`
  
  Depending on the specified `'type'`, the dictionary may contain additional
  fields and `create` may generate additional settings.
  
  Allowed values for `'type'`:
  * `'procedure'` (default) - Represents a procedure. `'action_group'`
    defaults to `DEFAULT_PROCEDURES_GROUP` if not defined.
  * `'constraint'` - Represents a constraint. `'action_group'` defaults to
    `DEFAULT_CONSTRAINTS_GROUP` if not defined.
  
  Additional allowed fields for type `'constraint'` include:
  * `'also_apply_to_parent_folders'` - If `True`, apply the constraint to parent
    groups (folders) as well. The constraint is then satisfied only if the item
    and all of its parents satisfy the constraint.
  
  Custom fields are accepted as well. For each field, a separate setting is
  created, using the field name as the setting name.
  
  Raises:
  * `ValueError` - invalid `'type'` or missing required fields in
    `initial_actions`.
  """
  actions = pg.setting.Group(
    name=name,
    setting_attributes={
      'pdb_type': None,
      'setting_sources': None,
    })
  
  _ACTIONS_AND_INITIAL_ACTION_DICTS[actions] = initial_actions
  
  _create_initial_actions(actions, initial_actions)
  
  actions.connect_event('before-load', lambda group: clear(group, add_initial_actions=False))
  actions.connect_event('after-load', _set_up_action_after_loading)
  
  return actions


def _create_initial_actions(actions, initial_actions):
  if initial_actions is not None:
    for action_dict in initial_actions:
      add(actions, action_dict)


def _set_up_action_after_loading(actions):
  for action in actions:
    _set_up_action_post_creation(action)
    actions.invoke_event('after-add-action', action, None)


def add(actions, action_dict_or_function):
  """
  Add an action to the `actions` setting group.
  
  `action_dict_or_function` can be one of the following:
  * a dictionary - see `create()` for required and accepted fields.
  * a PDB procedure.
  
  Objects of other types passed to `action_dict_or_function` raise
  `TypeError`.
  
  The same action can be added multiple times. Each action will be
  assigned a unique name and display name (e.g. `'rename'` and `'Rename'`
  for the first action, `'rename_2'` and `'Rename (2)'` for the second
  action, and so on).
  """
  if isinstance(action_dict_or_function, dict):
    action_dict = dict(action_dict_or_function)
  else:
    if pg.pdbutils.is_pdb_procedure(action_dict_or_function):
      action_dict = get_action_dict_for_pdb_procedure(action_dict_or_function)
    else:
      raise TypeError(
        '"{}" is not a valid object - pass a dict or a PDB procedure'.format(
          action_dict_or_function))
  
  _check_required_fields(action_dict)
  
  orig_action_dict = dict(action_dict)
  
  actions.invoke_event('before-add-action', action_dict)
  
  _uniquify_name_and_display_name(actions, action_dict)
  
  action = _create_action_by_type(**action_dict)
  
  actions.add([action])
  
  actions.invoke_event('after-add-action', action, orig_action_dict)
  
  return action


def _check_required_fields(action_kwargs):
  for required_field in _REQUIRED_ACTION_FIELDS:
    if required_field not in action_kwargs:
      raise ValueError('missing required field: "{}"'.format(required_field))


def _uniquify_name_and_display_name(actions, action_dict):
  action_dict['orig_name'] = action_dict['name']
  action_dict['name'] = _uniquify_action_name(actions, action_dict['name'])
  if 'display_name' in action_dict:
    action_dict['display_name'] = _uniquify_action_display_name(
      actions, action_dict['display_name'])


def _uniquify_action_name(actions, name):
  """
  Return `name` modified to not match the name of any existing action in
  `actions`.
  """
  
  def _generate_unique_action_name():
    i = 2
    while True:
      yield '_{}'.format(i)
      i += 1
  
  return (
    pg.path.uniquify_string(
      name,
      [action.name for action in walk(actions)],
      generator=_generate_unique_action_name()))


def _uniquify_action_display_name(actions, display_name):
  """
  Return `display_name` modified to not match the display name of any existing
  action in `actions`.
  """
  
  def _generate_unique_display_name():
    i = 2
    while True:
      yield ' ({})'.format(i)
      i += 1
  
  return (
    pg.path.uniquify_string(
      display_name,
      [action['display_name'].value for action in walk(actions)],
      generator=_generate_unique_display_name()))


def _create_action_by_type(**kwargs):
  type_ = kwargs.pop('type', _DEFAULT_ACTION_TYPE)
  
  if type_ not in _ACTION_TYPES_AND_FUNCTIONS:
    raise ValueError(
      'invalid type "{}"; valid values: {}'.format(
        type_, list(_ACTION_TYPES_AND_FUNCTIONS)))
  
  return _ACTION_TYPES_AND_FUNCTIONS[type_](**kwargs)


def _create_action(
      name,
      function='',
      origin='builtin',
      arguments=None,
      enabled=True,
      display_name=None,
      description=None,
      action_groups=None,
      tags=None,
      more_options_expanded=False,
      enabled_for_previews=True,
      display_options_on_create=False,
      orig_name=None):
  action = pg.setting.Group(
    name,
    tags=tags,
    setting_attributes={
      'pdb_type': None,
      'setting_sources': None,
    })
  
  arguments_group = pg.setting.Group(
    'arguments',
    setting_attributes={
      'pdb_type': None,
      'setting_sources': None,
    })
  
  if arguments:
    arguments_group.add(arguments)
  
  action.add([
    {
      'type': 'string',
      'name': 'function',
      'default_value': function,
      'setting_sources': None,
      'gui_type': None,
    },
    {
      'type': 'options',
      'name': 'origin',
      'default_value': origin,
      'items': [
        ('builtin', _('Built-in')),
        ('gimp_pdb', _('GIMP PDB procedure'))],
      'gui_type': None,
    },
    arguments_group,
    {
      'type': 'boolean',
      'name': 'enabled',
      'default_value': enabled,
    },
    {
      'type': 'string',
      'name': 'display_name',
      'default_value': display_name,
      'gui_type': None,
      'tags': ['ignore_initialize_gui'],
    },
    {
      'type': 'string',
      'name': 'description',
      'default_value': description,
      'gui_type': None,
    },
    {
      'type': 'list',
      'name': 'action_groups',
      'default_value': action_groups,
      'nullable': True,
      'gui_type': None,
    },
    {
      'type': 'boolean',
      'name': 'more_options_expanded',
      'default_value': more_options_expanded,
      'display_name': _('_More options'),
      'gui_type': 'expander',
    },
    {
      'type': 'boolean',
      'name': 'enabled_for_previews',
      'default_value': enabled_for_previews,
      'display_name': _('Enable for previews'),
    },
    {
      'type': 'boolean',
      'name': 'display_options_on_create',
      'default_value': display_options_on_create,
      'gui_type': None,
    },
  ])
  
  action.add([
    {
      'type': 'string',
      'name': 'orig_name',
      'default_value': orig_name if orig_name is not None else name,
      'gui_type': None,
    },
  ])
  
  _set_up_action_post_creation(action)
  
  return action


def _create_procedure(
      name,
      additional_tags=None,
      action_groups=(DEFAULT_PROCEDURES_GROUP,),
      **kwargs):
  tags = ['action', 'procedure']
  if additional_tags is not None:
    tags += additional_tags
  
  if action_groups is not None:
    action_groups = list(action_groups)
  
  return _create_action(
    name,
    action_groups=action_groups,
    tags=tags,
    **kwargs)


def _create_constraint(
      name,
      additional_tags=None,
      action_groups=(DEFAULT_CONSTRAINTS_GROUP,),
      also_apply_to_parent_folders=False,
      **kwargs):
  tags = ['action', 'constraint']
  if additional_tags is not None:
    tags += additional_tags
  
  if action_groups is not None:
    action_groups = list(action_groups)
  
  constraint = _create_action(
    name,
    action_groups=action_groups,
    tags=tags,
    **kwargs)
  
  constraint.add([
    {
      'type': 'boolean',
      'name': 'also_apply_to_parent_folders',
      'default_value': also_apply_to_parent_folders,
      'display_name': _('Also apply to parent folders'),
    },
  ])
  
  return constraint


def _set_up_action_post_creation(action):
  action['enabled'].connect_event(
    'after-set-gui',
    _set_display_name_for_enabled_gui,
    action['display_name'])
  
  if action['origin'].is_item('gimp_pdb'):
    _connect_events_to_sync_array_and_array_length_arguments(action)
    _hide_gui_for_run_mode_and_array_length_arguments(action)


def _set_display_name_for_enabled_gui(setting_enabled, setting_display_name):
  setting_display_name.set_gui(
    gui_type='check_button_label',
    gui_element=setting_enabled.gui.element)


def _connect_events_to_sync_array_and_array_length_arguments(action):
  
  def _increment_array_length(
        array_setting, insertion_index, value, array_length_setting):
    array_length_setting.set_value(array_length_setting.value + 1)
  
  def _decrement_array_length(
        array_setting, insertion_index, array_length_setting):
    array_length_setting.set_value(array_length_setting.value - 1)
  
  for length_setting, array_setting in _get_array_length_and_array_settings(action):
    array_setting.connect_event(
      'after-add-element', _increment_array_length, length_setting)
    array_setting.connect_event(
      'before-delete-element', _decrement_array_length, length_setting)


def _hide_gui_for_run_mode_and_array_length_arguments(action):
  first_argument = next(iter(action['arguments']), None)
  if first_argument is not None and first_argument.display_name == 'run-mode':
    first_argument.gui.set_visible(False)
  
  for length_setting, unused_ in _get_array_length_and_array_settings(action):
    length_setting.gui.set_visible(False)


def _get_array_length_and_array_settings(action):
  array_length_and_array_settings = []
  previous_setting = None
  
  for setting in action['arguments']:
    if isinstance(setting, pg.setting.ArraySetting) and previous_setting is not None:
      array_length_and_array_settings.append((previous_setting, setting))
    
    previous_setting = setting
  
  return array_length_and_array_settings


def get_action_dict_for_pdb_procedure(pdb_procedure):
  """Returns a dictionary representing the specified GIMP PDB procedure that can
  be added to a setting group for actions via `add()`.
  
  The `'function'` field contains the PDB procedure name.
  
  If the procedure contains arguments with the same name, each subsequent
  identical name is made unique (since arguments are internally represented as
  `pygimplib.setting.Setting` instances, whose names must be unique within a
  setting group).
  """
  
  def _generate_unique_pdb_procedure_argument_name():
    i = 2
    while True:
      yield '-{}'.format(i)
      i += 1
  
  action_dict = {
    'name': pg.utils.safe_decode_gimp(pdb_procedure.proc_name),
    'function': pg.utils.safe_decode_gimp(pdb_procedure.proc_name),
    'origin': 'gimp_pdb',
    'arguments': [],
    'display_name': pg.utils.safe_decode_gimp(pdb_procedure.proc_name),
    'display_options_on_create': True,
  }
  
  pdb_procedure_argument_names = []
  
  for index, (pdb_param_type, pdb_param_name, unused_) in enumerate(pdb_procedure.params):
    processed_pdb_param_name = pg.utils.safe_decode_gimp(pdb_param_name)
    
    try:
      setting_type = pg.setting.PDB_TYPES_TO_SETTING_TYPES_MAP[pdb_param_type]
    except KeyError:
      raise UnsupportedPdbProcedureError(action_dict['name'], pdb_param_type)
    
    unique_pdb_param_name = pg.path.uniquify_string(
      processed_pdb_param_name,
      pdb_procedure_argument_names,
      generator=_generate_unique_pdb_procedure_argument_name())
    
    pdb_procedure_argument_names.append(unique_pdb_param_name)
    
    if isinstance(setting_type, dict):
      arguments_dict = dict(setting_type)
      arguments_dict['name'] = unique_pdb_param_name
      arguments_dict['display_name'] = processed_pdb_param_name
    else:
      arguments_dict = {
        'type': setting_type,
        'name': unique_pdb_param_name,
        'display_name': processed_pdb_param_name,
      }
    
    if pdb_param_type in placeholders.PDB_TYPES_TO_PLACEHOLDER_SETTING_TYPES_MAP:
      arguments_dict['type'] = (
        placeholders.PDB_TYPES_TO_PLACEHOLDER_SETTING_TYPES_MAP[pdb_param_type])
    
    if index == 0 and processed_pdb_param_name == 'run-mode':
      arguments_dict['default_value'] = gimpenums.RUN_NONINTERACTIVE
    
    action_dict['arguments'].append(arguments_dict)
  
  return action_dict


def reorder(actions, action_name, new_position):
  """
  Modify the position of the added action given by its name to the new
  position specified as an integer.
  
  A negative position functions as an n-th to last position (-1 for last, -2
  for second to last, etc.).
  
  Raises:
  * `ValueError` - `action_name` not found in `actions`.
  """
  current_position = get_index(actions, action_name)
  
  if current_position is None:
    raise ValueError('action "{}" not found in actions named "{}"'.format(
      action_name, actions.name))
  
  action = actions[action_name]
  
  actions.invoke_event('before-reorder-action', action, current_position)
  
  actions.reorder(action_name, new_position)
  
  actions.invoke_event('after-reorder-action', action, current_position, new_position)


def remove(actions, action_name):
  """
  Remove the action specified by its name from `actions`.
  
  Raises:
  * `ValueError` - `action_name` not found in `actions`.
  """
  if action_name not in actions:
    raise ValueError('action "{}" not found in actions named "{}"'.format(
      action_name, actions.name))
  
  action = actions[action_name]
  
  actions.invoke_event('before-remove-action', action)
  
  actions.remove([action_name])
  
  actions.invoke_event('after-remove-action', action_name)


def get_index(actions, action_name):
  """Returns the index of the action matching `action_name`.
  
  If there is no such action, return `None`.
  """
  return next(
    (index for index, action in enumerate(actions)
     if action.name == action_name),
    None)


def clear(actions, add_initial_actions=True):
  """Removes all added actions.
  
  If `add_initial_actions` is `True`, add back actions specified as
  `initial_actions` in `create()` after removing all actions.
  """
  actions.invoke_event('before-clear-actions')
  
  actions.remove([action.name for action in actions])
  
  if add_initial_actions:
    if actions in _ACTIONS_AND_INITIAL_ACTION_DICTS:
      _create_initial_actions(actions, _ACTIONS_AND_INITIAL_ACTION_DICTS[actions])
  
  actions.invoke_event('after-clear-actions')


def walk(actions, action_type=None, setting_name=None):
  """
  Walk (iterate over) a setting group containing actions.
  
  The value of `action_type` determines what types of actions to iterate
  over. If `action_type` is `None`, iterate over all actions. For allowed
  action types, see `create()`. Invalid values for `action_type` raise
  `ValueError`.
  
  If `setting_name` is `None`, iterate over each setting group representing the
  entire action.
  
  If `setting_name` is not `None`, iterate over each setting or subgroup inside
  each action. For example, `'enabled'` yields the `'enabled'` setting for
  each action. For the list of possible names of settings and subgroups, see
  `create()`.
  """
  action_types = list(_ACTION_TYPES_AND_FUNCTIONS)
  
  if action_type is not None and action_type not in action_types:
    raise ValueError('invalid action type "{}"'.format(action_type))
  
  def has_matching_type(action):
    if action_type is None:
      return any(type_ in action.tags for type_ in action_types)
    else:
      return action_type in action.tags
  
  for action in actions:
    if not has_matching_type(action):
      continue
    
    if setting_name is None:
      yield action
    else:
      if setting_name in action:
        yield action[setting_name]


_ACTION_TYPES_AND_FUNCTIONS = {
  'procedure': _create_procedure,
  'constraint': _create_constraint,
}


class UnsupportedPdbProcedureError(Exception):
  
  def __init__(self, procedure_name, unsupported_param_type):
    self.procedure_name = procedure_name
    self.unsupported_param_type = unsupported_param_type
