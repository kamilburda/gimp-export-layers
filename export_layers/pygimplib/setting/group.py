# -*- coding: utf-8 -*-

"""Class that groups settings for easier setting creation and management."""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *
import future.utils

import collections
import inspect

from .. import utils as pgutils

from . import meta as meta_
from . import persistor as persistor_
from . import settings as settings_
from . import utils as utils_

__all__ = [
  'create_groups',
  'Group',
  'GroupWalkCallbacks',
]


def create_groups(setting_dict):
  """
  Create a hierarchy of setting groups (`Group` instances) from a dictionary
  containing attributes for the groups. This function simplifies adding setting
  groups (via `Group.add`).
  
  Groups are specified under the `'groups'` key as a list of dictionaries.
  
  Only `'groups'` and the names of parameters for `Group.__init__` are valid
  keys for `setting_dict`. Other keys raise `TypeError`.
  
  Example:
    settings = create_groups({
      'name': 'main',
      'groups': [
        {
          'name': 'procedures'
        },
        {
          'name': 'constraints'
        }
      ]
    })
  """
  
  group_dicts = setting_dict.pop('groups', None)
  
  if group_dicts is None:
    group_dicts = []
  
  group = Group(**setting_dict)
  
  for group_dict in group_dicts:
    group.add([create_groups(group_dict)])
  
  return group


@future.utils.python_2_unicode_compatible
class Group(
    future.utils.with_metaclass(
      meta_.GroupMeta, utils_.SettingParentMixin, utils_.SettingEventsMixin)):
  """
  This class:
  * allows to create a group of related settings (`Setting` objects),
  * allows to store existing setting groups,
  * can perform certain operations on all settings and nested groups at once.
    
  Unless otherwise stated, "settings" in the rest of the documentation for
  this class refers to both `Setting` and `Group` instances.
  
  Attributes:
  
  * `name` (read-only) - A name (string) that uniquely identifies the setting
    group.
  
  * `display_name` (read-only) - Setting group name in human-readable format.
  
  * `description` (read-only) - A more detailed description of the group. By
    default, description is derived from `display_name`.
  
  * `tags` - A set of arbitrary tags attached to the group. Tags can be used to
    e.g. iterate over a specific subset of settings.
  
  * `setting_attributes` (read-only) - Dictionary of (setting attribute: value)
    pairs to assign to each new setting created in the group. Attributes in
    individual settings override these attributes. `setting_attributes` are not
    applied to already created settings that are later added to the group via
    `add()`.
  
  * `recurse_setting_attributes` (read-only) - If `True`, `setting_attributes`
    is recursively applied to child settings of any depth. If a child group
    defines its own `setting_attributes`, it will override its parent's
    `setting_attributes`. If `False`, `setting_attributes` will only be applied
    to immediate child settings.
  """
  
  def __init__(
        self,
        name,
        display_name=None,
        description=None,
        tags=None,
        setting_attributes=None,
        recurse_setting_attributes=True):
    utils_.SettingParentMixin.__init__(self)
    utils_.SettingEventsMixin.__init__(self)
    
    utils_.check_setting_name(name)
    self._name = name
    
    self._display_name = utils_.get_processed_display_name(
      display_name, self._name)
    
    self._description = utils_.get_processed_description(
      description, self._display_name)
    
    self._tags = set(tags) if tags is not None else set()
    
    self._setting_attributes = setting_attributes
    self._recurse_setting_attributes = recurse_setting_attributes
    
    self._settings = collections.OrderedDict()
    self._setting_list = []
    
    # Used in `_next()`
    self._settings_iterator = None
  
  @property
  def name(self):
    return self._name
  
  @property
  def display_name(self):
    return self._display_name
  
  @property
  def description(self):
    return self._description
  
  @property
  def tags(self):
    return self._tags
  
  @property
  def setting_attributes(self):
    # Return a copy to prevent modification.
    return dict(self._setting_attributes) if self._setting_attributes is not None else None
  
  @property
  def recurse_setting_attributes(self):
    return self._recurse_setting_attributes
  
  def __str__(self):
    return pgutils.stringify_object(self, self.name)
  
  def __repr__(self):
    return pgutils.reprify_object(self, self.name)
  
  def __getitem__(self, setting_name_or_path):
    """
    Access the setting or group by its name (string).
    
    If a setting is inside a nested group, you can access the setting as
    follows:
      
      settings['main']['file_extension']
    
    As a more compact alternative, you may specify a setting path:
    
      settings['main/file_extension']
    
    If the name or path does not exist, raise `KeyError`.
    """
    if utils_.SETTING_PATH_SEPARATOR in setting_name_or_path:
      return self._get_setting_from_path(setting_name_or_path)
    else:
      try:
        return self._settings[setting_name_or_path]
      except KeyError:
        raise KeyError('setting "{}" not found in group "{}"'.format(
          setting_name_or_path, self.name))
  
  def __contains__(self, setting_name_or_path):
    if utils_.SETTING_PATH_SEPARATOR in setting_name_or_path:
      try:
        self._get_setting_from_path(setting_name_or_path)
      except KeyError:
        return False
      else:
        return True
    else:
      return setting_name_or_path in self._settings
  
  def _get_setting_from_path(self, setting_path):
    setting_path_components = setting_path.split(utils_.SETTING_PATH_SEPARATOR)
    current_group = self
    for group_name in setting_path_components[:-1]:
      if group_name in current_group:
        current_group = current_group._settings[group_name]
      else:
        raise KeyError('group "{}" in path "{}" does not exist'.format(
          group_name, setting_path))
    
    try:
      setting = current_group[setting_path_components[-1]]
    except KeyError:
      raise KeyError('setting "{}" not found in path "{}"'.format(
        setting_path_components[-1], setting_path))
    
    return setting
  
  def __iter__(self):
    """Iterates over child settings or groups.
    
    This method does not iterate over nested groups. Use `walk()` in that case.
    
    By default, the children are iterated in the order they were created or
    added into the group. The order of children can be modified via `reorder()`.
    """
    for setting in self._setting_list:
      yield setting
  
  def __len__(self):
    return len(self._settings)
  
  def __reversed__(self):
    return reversed(self._setting_list)
  
  def get_path(self, relative_path_group=None):
    """
    This is a wrapper method for `setting.utils.get_setting_path()`. Consult the
    method for more information.
    """
    return utils_.get_setting_path(self, relative_path_group)
  
  def add(self, setting_list):
    """
    Add settings to the group.
    
    The order of settings in the list corresponds to the order in which the
    settings are iterated.
    
    `setting_list` is a list that can contain `Setting` objects, `Group`
    instances or dictionaries representing `Setting` objects to be created.
    
    Each dictionary contains (attribute name: value) pairs, where
    `'attribute name'` is a string that represents an argument passed when
    instantiating the setting. The following attributes must always be
    specified:
      * `'type'` - Type of the Setting object to instantiate.
      * `'name'` - Setting name.
    
    The `'name'` attribute must not contain forward slashes (`'/'`) (which are
    used to access settings via paths).
    
    For more attributes, check the documentation of the setting classes. Some
    `Setting` subclasses may require specifying additional required attributes.
    
    Multiple settings with the same name and in different nested groups are
    possible. Each such setting can be accessed like any other:
    
      settings['main/file_extension']
      settings['advanced/file_extension']
    
    Settings created from dictionaries are by default assigned setting
    attributes specified during the initialization of this class. These
    attributes can be overridden by attributes in individual settings.
    """
    for setting in setting_list:
      if isinstance(setting, (settings_.Setting, Group)):
        setting = self._add_setting(setting)
      else:
        setting = self._create_setting(setting)
      
      self._set_as_parent_for_setting(setting)
  
  def _add_setting(self, setting):
    if setting.name in self._settings:
      raise ValueError('{} already exists in {}'.format(setting, self))
    
    if setting == self:
      raise ValueError('cannot add {} as a child of itself'.format(setting))
    
    self._settings[setting.name] = setting
    self._setting_list.append(setting)
    
    return setting
  
  def _create_setting(self, setting_data):
    try:
      setting_type = setting_data['type']
    except KeyError:
      raise TypeError(self._get_missing_required_attributes_message(['type']))
    
    setting_type = settings_.process_setting_type(setting_type)
    
    # Do not modify the original `setting_data` in case it is expected to be
    # reused.
    setting_data_copy = {key: setting_data[key] for key in setting_data if key != 'type'}
    
    try:
      setting_data_copy['name']
    except KeyError:
      raise TypeError(self._get_missing_required_attributes_message(['name']))
    
    if utils_.SETTING_PATH_SEPARATOR in setting_data_copy['name']:
      raise ValueError(
        'setting name "{}" must not contain path separator "{}"'.format(
          setting_data_copy['name'], utils_.SETTING_PATH_SEPARATOR))
    
    if setting_data_copy['name'] in self._settings:
      raise ValueError('setting "{}" already exists'.format(setting_data_copy['name']))
    
    for setting_attribute, setting_attribute_value in self._get_setting_attributes().items():
      if setting_attribute not in setting_data_copy:
        setting_data_copy[setting_attribute] = setting_attribute_value
    
    setting = self._instantiate_setting(setting_type, setting_data_copy)
    
    return setting
  
  def _get_setting_attributes(self):
    setting_attributes = self._setting_attributes
    
    if setting_attributes is None:
      for group_or_parent in reversed(self.parents):
        if not group_or_parent.recurse_setting_attributes:
          break
        
        if group_or_parent.setting_attributes is not None:
          setting_attributes = group_or_parent.setting_attributes
          break
    
    if setting_attributes is None:
      setting_attributes = {}
    
    return setting_attributes
  
  def _instantiate_setting(self, setting_type, setting_data_copy):
    try:
      setting = setting_type(**setting_data_copy)
    except TypeError as e:
      missing_required_arguments = self._get_missing_required_arguments(
        setting_type, setting_data_copy)
      if missing_required_arguments:
        message = self._get_missing_required_attributes_message(missing_required_arguments)
      else:
        message = str(e)
      raise TypeError(message)
    
    self._settings[setting_data_copy['name']] = setting
    self._setting_list.append(setting)
    
    return setting
  
  def _get_missing_required_arguments(self, setting_type, setting_data):
    required_arg_names = self._get_required_argument_names(setting_type.__init__)
    return [arg_name for arg_name in required_arg_names if arg_name not in setting_data]
  
  def _get_required_argument_names(self, func):
    arg_spec = inspect.getargspec(func)
    arg_default_values = arg_spec[3] if arg_spec[3] is not None else []
    num_required_args = len(arg_spec[0]) - len(arg_default_values)
    
    required_args = arg_spec[0][0:num_required_args]
    if required_args[0] == 'self':
      del required_args[0]
    
    return required_args
  
  def _get_missing_required_attributes_message(self, attribute_names):
    return 'missing the following required setting attributes: {}'.format(
      ', '.join(attribute_names))
  
  def get_value(self, setting_name_or_path, default_value=None):
    """
    Return the value of the setting specified by its name or path. If the
    setting does not exist, return `default_value` instead.
    """
    try:
      setting = self[setting_name_or_path]
    except KeyError:
      return default_value
    else:
      return setting.value
  
  def get_attributes(self, setting_attributes):
    """
    Return an ordered dictionary of
    `(setting_name.attribute_name, attribute_value)` key-value pairs given the
    list of `setting_name.attribute_name` elements.
    
    If `attribute_name` is omitted in a list element, the `value` attribute is
    assumed.
    
    If any attribute does not exist, raise `AttributeError`. If any setting does
    not exist, raise `KeyError`. If the key has more than one separator for
    attributes (`setting.utils.SETTING_ATTRIBUTE_SEPARATOR`), raise
    `ValueError`.
    
    Example:
      group.get_attributes([
        'main/file_extension',
        'main/file_extension.display_name'])
    
    returns
      
      {
        'main/file_extension': 'png',
        'main/file_extension.display_name': 'File Extension'
      }
    """
    setting_attributes_and_values = collections.OrderedDict()
    
    for setting_name_and_attribute in setting_attributes:
      setting_name, attribute_name = self._get_setting_and_attribute_names(
        setting_name_and_attribute)
      
      value = getattr(self[setting_name], attribute_name)
      setting_attributes_and_values[setting_name_and_attribute] = value
    
    return setting_attributes_and_values
  
  def get_values(self):
    """
    Return an ordered dictionary of `(setting_name, setting_value)` pairs for
    all settings in this group.
    """
    return collections.OrderedDict([
      (setting.get_path('root'), setting.value) for setting in self.walk()])
  
  def _get_setting_and_attribute_names(self, setting_name_and_attribute):
    parts = setting_name_and_attribute.split(utils_.SETTING_ATTRIBUTE_SEPARATOR)
    if len(parts) == 1:
      setting_name = setting_name_and_attribute
      attribute_name = 'value'
    elif len(parts) == 2:
      setting_name, attribute_name = parts
    else:
      raise ValueError('"{}" cannot have more than one "{}" character'.format(
        setting_name_and_attribute, utils_.SETTING_ATTRIBUTE_SEPARATOR))
    
    return setting_name, attribute_name
  
  def set_values(self, settings_and_values):
    """
    Set values to specified settings via a dictionary of `(setting name, value)`
    key-value pairs.
    
    If any setting does not exist, raise `KeyError`.
    
    Example:
      group.set_values({
        'main/file_extension': 'png',
        'main/output_directory': '/sample/directory',
      })
    """
    for setting_name, value in settings_and_values.items():
      self[setting_name].set_value(value)
  
  def reorder(self, setting_name, new_position):
    """Reorders a child setting to the new position.
    
    `setting_name` is the name of the child setting.
    
    A negative position functions as an n-th to last position (-1 for last, -2
    for second to last, etc.).
      
    Raises:
    * `ValueError` - `setting_name` does not match any child setting.
    """
    try:
      setting = self._settings[setting_name]
    except KeyError:
      raise KeyError('setting "{}" not found'.format(setting_name))
    
    self._setting_list.remove(setting)
    
    if new_position < 0:
      new_position = max(len(self._setting_list) + new_position + 1, 0)
    
    self._setting_list.insert(new_position, setting)
  
  def remove(self, setting_names):
    """
    Remove settings from the group specified by their names.
    
    If any setting does not exist, raise `KeyError`.
    """
    for setting_name in setting_names:
      if setting_name in self._settings:
        setting = self._settings[setting_name]
        del self._settings[setting_name]
        self._setting_list.remove(setting)
      else:
        raise KeyError('setting "{}" not found'.format(setting_name))
  
  def walk(
        self,
        include_setting_func=None,
        include_groups=False,
        include_if_parent_skipped=False,
        walk_callbacks=None):
    """
    Return a generator that walks (iterates over) all settings in the group,
    including settings in nested groups. The generator performs a pre-order
    traversal.
    
    If `include_setting_func` is `None`, iterate over all settings. Otherwise,
    `include_setting_func` is a function that should return `True` if a setting
    should be yielded and `False` if a setting should be skipped. The function
    must accept one positional parameter - the current setting or group.
    
    If `include_if_parent_skipped` is `False`, settings or groups within a
    parent group that does not match `include_setting_func` are skipped,
    `True` otherwise. If `True` and `include_groups` is `True`, the parent group
    will still be ignored by `walk_callbacks`.
    
    If `include_groups` is `True`, yield setting groups as well.
    
    `walk_callbacks` is an `GroupWalkCallbacks` instance that invokes additional
    commands during the walk of the group. By default, the callbacks do nothing.
    For more information, see the `GroupWalkCallbacks` class.
    """
    if include_setting_func is None:
      include_setting_func = pgutils.create_empty_func(return_value=True)
    
    if walk_callbacks is None:
      walk_callbacks = GroupWalkCallbacks()
    
    groups = [self]
    
    while groups:
      try:
        setting_or_group = groups[0]._next()
      except StopIteration:
        if groups[0] != self:
          walk_callbacks.on_end_group_walk(groups[0])
        
        groups.pop(0)
        continue
      
      if isinstance(setting_or_group, Group):
        if include_setting_func(setting_or_group):
          groups.insert(0, setting_or_group)
          
          if include_groups:
            walk_callbacks.on_visit_group(setting_or_group)
            yield setting_or_group
        elif include_if_parent_skipped:
          groups.insert(0, setting_or_group)
          continue
        else:
          continue
      else:
        if include_setting_func(setting_or_group):
          walk_callbacks.on_visit_setting(setting_or_group)
          yield setting_or_group
        else:
          continue
  
  def _next(self):
    """
    Return the next element when iterating the settings. Used by `walk()`.
    """
    if self._settings_iterator is None:
      self._settings_iterator = iter(self._setting_list)
    
    try:
      next_element = next(self._settings_iterator)
    except StopIteration:
      self._settings_iterator = None
      raise StopIteration
    else:
      return next_element
  
  def reset(self):
    """
    Reset all settings in this group. Ignore settings with the `'ignore_reset'`
    tag.
    """
    def _has_ignore_reset_tag(setting):
      return 'ignore_reset' not in setting.tags
    
    for setting in self.walk(include_setting_func=_has_ignore_reset_tag):
      setting.reset()
  
  def load(self, *args, **kwargs):
    """Loads settings in the current group from the specified setting source(s).
    
    See `setting.persistor.Persistor.load()` for information about parameters.
    
    If the `tags` attribute contains `'ignore_load'`, this method will have no
    effect.
    """
    return persistor_.Persistor.load([self], *args, **kwargs)
  
  def save(self, *args, **kwargs):
    """Saves values of settings from the current group to the specified setting
    source(s).
    
    See `setting.persistor.Persistor.save()` for information about parameters.
    
    If the `tags` attribute contains `'ignore_save'`, this method will have no
    effect.
    """
    return persistor_.Persistor.save([self], *args, **kwargs)
  
  def initialize_gui(self, custom_gui=None):
    """
    Initialize GUI for all settings. Ignore settings with the
    `'ignore_initialize_gui'` tag.
    
    Settings that are not provided with a readily available GUI can have their
    GUI initialized using the `custom_gui` dict. `custom_gui` contains
    (setting name, list of arguments to `setting.Setting.set_gui()`) pairs. The
    'enable GUI update?' boolean in the list is optional and defaults to `True`.
    For more information about parameters in the list, see
    `setting.Setting.set_gui()`.
    
    Example:
    
      file_extension_entry = gtk.Entry()
      ...
      main_settings.initialize_gui({
        'file_extension': [SettingGuiTypes.entry, file_extension_entry]
        ...
      })
    """
    
    def _should_not_ignore(setting):
      return 'ignore_initialize_gui' not in setting.tags
    
    if custom_gui is None:
      custom_gui = {}
    
    for setting in self.walk(include_setting_func=_should_not_ignore):
      if setting.get_path('root') not in custom_gui:
        setting.set_gui()
      else:
        set_gui_args = custom_gui[setting.get_path('root')]
        setting.set_gui(*set_gui_args)
  
  def apply_gui_values_to_settings(self):
    """
    Apply GUI element values, entered by the user, to settings.
    Ignore settings with the `'ignore_apply_gui_value_to_setting'` tag.
    
    This method will not have any effect on settings with automatic
    GUI-to-setting value updating.
    
    Raises:
    
    * `SettingValueError` - One or more values are invalid. The exception
    message contains messages from all invalid settings.
    """
    
    def _should_not_ignore(setting):
      return 'ignore_apply_gui_value_to_setting' not in setting.tags
    
    exception_messages = []
    exception_settings = []
    
    for setting in self.walk(include_setting_func=_should_not_ignore):
      try:
        setting.gui.update_setting_value()
      except settings_.SettingValueError as e:
        exception_messages.append(str(e))
        exception_settings.append(e.setting)
    
    if exception_messages:
      exception_message = '\n'.join(exception_messages)
      raise settings_.SettingValueError(
        exception_message,
        setting=exception_settings[0],
        messages=exception_messages,
        settings=exception_settings)
  
  def to_dict(self):
    """Returns a dictionary representing the group, appropriate for saving it
    (e.g. via `Group.save()`).
    
    The dictionary contains (attribute name, attribute value) pairs.
    Specifically, the dictionary contains:
    * `name` attribute
    * all keyword argument names and values passed to `__init__()` that were
      used to instantiate the group.
    
    The list of child settings is not provided by this method.
    """
    group_dict = dict(self._dict_on_init)
    
    if 'tags' in group_dict:
      group_dict['tags'] = list(group_dict['tags'])
    
    if 'name' not in group_dict:
      # This should not happen since `name` is required in `__init__`, but just in case.
      group_dict['name'] = self.name
    
    return group_dict


class GroupWalkCallbacks(object):
  """
  This class defines callbacks called during `Group.walk()`. By default, the
  callbacks do nothing.
  
  `on_visit_setting` is called before the current `Setting` object is yielded.
  `on_visit_group` is called before the current `Group` object is yielded.
  `on_end_group_walk` is called after all children of the current `Group` object
  are visited.
  """
  
  def __init__(self):
    self.on_visit_setting = pgutils.empty_func
    self.on_visit_group = pgutils.empty_func
    self.on_end_group_walk = pgutils.empty_func
