# -*- coding: utf-8 -*-

"""Helper classes and functions for modules in the `setting` package."""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import collections
import itertools
import types

__all__ = [
  'SETTING_PATH_SEPARATOR',
  'SETTING_ATTRIBUTE_SEPARATOR',
  'SettingParentMixin',
  'SettingEventsMixin',
  'get_pdb_name',
  'get_setting_name',
  'value_to_str_prefix',
  'get_processed_display_name',
  'generate_display_name',
  'get_processed_description',
  'generate_description',
  'get_setting_path',
  'check_setting_name',
]


SETTING_PATH_SEPARATOR = '/'
SETTING_ATTRIBUTE_SEPARATOR = '.'


class SettingParentMixin(object):
  """
  This mixin provides `Setting` and `Group` instances with a parent reference,
  allowing settings and groups to form a tree-like structure.
  """
  
  def __init__(self):
    super().__init__()
    
    self._parent = None
  
  @property
  def parent(self):
    return self._parent
  
  @property
  def parents(self):
    """
    Return a list of parents (setting groups), starting from the topmost parent.
    """
    parent = self._parent
    parents = []
    
    while parent is not None:
      parents.insert(0, parent)
      parent = parent.parent
    
    return parents
  
  def _set_as_parent_for_setting(self, setting):
    setting._parent = self


class SettingEventsMixin(object):
  """
  This mixin provides `Setting` and `Group` instances with the capability of
  setting up and invoking events.
  """
  
  _event_handler_id_counter = itertools.count(start=1)
  
  def __init__(self):
    super().__init__()
    
    # key: event type
    # value: collections.OrderedDict{
    #   event handler ID: [event handler, arguments, keyword arguments, is enabled]}
    self._event_handlers = collections.defaultdict(collections.OrderedDict)
    
    # This allows faster lookup of events via IDs.
    # key: event handler ID; value: event type
    self._event_handler_ids_and_types = {}
  
  def connect_event(
        self, event_type, event_handler, *event_handler_args, **event_handler_kwargs):
    """
    Connect an event handler.
    
    `event_type` can be an arbitrary string. To invoke an event manually, call
    `invoke_event`.
    
    Several event types are invoked automatically. For the list of such event
    types, consult the documentation for `Setting` or `Group` classes.
    
    The `event_handler` function must always contain at least one argument -
    the instance this method is called from (a setting or a setting group).
    
    Multiple event handlers can be connected. Each new event handler is invoked
    as the last.
    
    Parameters:
    
    * `event_type` - Event type as a string.
    
    * `event_handler` - Function to be called when the event given by
      `event_type` is invoked.
    
    * `*event_handler_args` - Arguments to `event_handler`.
    
    * `**event_handler_kwargs` - Keyword arguments to `event_handler`.
    
    Returns:
    
    * `event_id` - Numeric ID of the event handler (can be used to remove the
      event via `remove_event`).
    
    Raises:
    
    * `TypeError` - `event_handler` is not a function or the wrong number of
      arguments was passed in `event_handler_args`.
    """
    if not callable(event_handler):
      raise TypeError('not a function')
    
    event_id = self._event_handler_id_counter.next()
    self._event_handlers[event_type][event_id] = [
      event_handler, event_handler_args, event_handler_kwargs, True]
    self._event_handler_ids_and_types[event_id] = event_type
    
    return event_id
  
  def remove_event(self, event_id):
    """
    Remove the event handler specified by its ID as returned by
    `connect_event()`.
    """
    if event_id not in self._event_handler_ids_and_types:
      raise ValueError('event handler with ID {} does not exist'.format(event_id))
    
    event_type = self._event_handler_ids_and_types[event_id]
    del self._event_handlers[event_type][event_id]
    del self._event_handler_ids_and_types[event_id]
  
  def set_event_enabled(self, event_id, enabled):
    """
    Enable or disable the event handler specified by its ID.
    
    If the event ID is already enabled and `enabled` is `True` or is already
    disabled and `enabled` is `False`, do nothing.
    
    Raises:
    
    * `ValueError` - Event ID is invalid.
    """
    if not self.has_event(event_id):
      raise ValueError('event ID {} is invalid'.format(event_id))
    
    event_type = self._event_handler_ids_and_types[event_id]
    self._event_handlers[event_type][event_id][3] = enabled
  
  def has_event(self, event_id):
    """
    Return `True` if the event handler specified by its ID is connected to the
    setting, `False` otherwise.
    """
    return event_id in self._event_handler_ids_and_types
  
  def invoke_event(self, event_type, *additional_args, **additional_kwargs):
    """
    Call all connected event handlers of the specified event type.
    
    Additional arguments and keyword arguments are passed via
    `*additional_args` and `**additional_kwargs`, respectively. These arguments
    are prepended to the arguments specified in `connect_event` (if any).
    The same keyword arguments in `connect_event` override keyword arguments in
    `**additional_kwargs`.
    """
    for (event_handler,
         args,
         kwargs,
         enabled) in self._event_handlers[event_type].values():
      if enabled:
        event_handler_args = additional_args + tuple(args)
        event_handler_kwargs = dict(additional_kwargs, **kwargs)
        event_handler(self, *event_handler_args, **event_handler_kwargs)


def get_pdb_name(setting_name):
  """
  Return name suitable for the description of the setting in the GIMP PDB.
  """
  return setting_name.replace('_', '-')


def get_setting_name(pdb_name):
  """
  Return setting name based on the specified name from GIMP PDB.
  """
  return pdb_name.replace('-', '_')


def value_to_str_prefix(value):
  """
  Return stringified setting value useful as a prefix to an error message.
  
  If `value` is empty or `None`, return empty string.
  """
  if value:
    return '"{}": '.format(value)
  else:
    return ''


def get_processed_display_name(setting_display_name, setting_name):
  if setting_display_name is not None:
    return setting_display_name
  else:
    return generate_display_name(setting_name)


def generate_display_name(setting_name):
  return setting_name.replace('_', ' ').capitalize()


def get_processed_description(setting_description, setting_display_name):
  if setting_description is not None:
    return setting_description
  else:
    return generate_description(setting_display_name)


def generate_description(display_name):
  """
  Generate setting description from a display name.
  
  Underscores in display names used as mnemonics are usually undesired in
  descriptions, hence their removal.
  """
  return display_name.replace('_', '')


def get_setting_path(setting, relative_path_group=None):
  """
  Get the full setting path consisting of names of parent setting groups and the
  specified setting. The path components are separated by '/'.
  
  If `relative_path_group` is specified, the setting group is used to
  relativize the setting path. If the path of the setting group to the topmost
  parent does not match, return the full path.
  
  If `relative_path_group` is equal to `'root'` and the setting has at
  least one parent, omit the topmost group.
  """
  def _get_setting_path(path_components):
    return SETTING_PATH_SEPARATOR.join([setting.name for setting in path_components])
  
  if relative_path_group == 'root':
    if setting.parents:
      setting_path_without_root = _get_setting_path(
        (setting.parents + [setting])[1:])
      return setting_path_without_root
    else:
      return setting.name
  else:
    setting_path = _get_setting_path(setting.parents + [setting])
    
    if relative_path_group is not None:
      root_path = _get_setting_path(
        relative_path_group.parents + [relative_path_group])
      if setting_path.startswith(root_path):
        return setting_path[len(root_path + SETTING_PATH_SEPARATOR):]
    
    return setting_path


def check_setting_name(setting_name):
  """
  Check if the specified setting name is valid. If not, raise `ValueError`.
  
  A setting name must not contain `SETTING_PATH_SEPARATOR` or
  `SETTING_ATTRIBUTE_SEPARATOR`.
  """
  if not isinstance(setting_name, types.StringTypes):
    raise TypeError('setting name must be a string')
  
  if (SETTING_PATH_SEPARATOR in setting_name
      or SETTING_ATTRIBUTE_SEPARATOR in setting_name):
    raise ValueError('setting name "{}" is not valid'.format(setting_name))
