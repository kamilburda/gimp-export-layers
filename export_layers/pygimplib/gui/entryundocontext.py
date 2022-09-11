# -*- coding: utf-8 -*-

"""Undo context for GTK text entries."""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import collections

import pygtk
pygtk.require('2.0')
import gtk

__all__ = [
  'EntryUndoContext',
]


class EntryUndoContext(object):
  """
  This class adds undo/redo capabilities to a `gtk.Entry` object.
  
  Attributes:
  
  * `undo_enabled` - If `True`, add user actions (insert text, delete text) to
    the undo history.
  """
  
  _ActionData = collections.namedtuple('_ActionData', ['action_type', 'position', 'text'])
  
  _ACTION_TYPES = ['insert', 'delete']
  
  def __init__(self, entry):
    self._entry = entry
    
    self.undo_enabled = True
    
    self._undo_stack = []
    self._redo_stack = []
    
    self._last_action_group = []
    self._last_action_type = None
    
    self._cursor_changed_by_action = False
    
    self._entry.connect('insert-text', self._on_entry_insert_text)
    self._entry.connect('delete-text', self._on_entry_delete_text)
    self._entry.connect('notify::cursor-position', self._on_entry_notify_cursor_position)
    self._entry.connect('key-press-event', self._on_entry_key_press_event)
  
  def undo(self):
    self._undo_redo(
      self._undo_stack,
      self._redo_stack,
      action_handlers={
        'insert': lambda action_data: self._entry.delete_text(
          action_data.position, action_data.position + len(action_data.text)),
        'delete': lambda action_data: self._entry.insert_text(
          action_data.text, action_data.position)},
      action_handlers_get_cursor_position={
        'insert': lambda last_action_data: last_action_data.position,
        'delete': lambda last_action_data: (
          last_action_data.position + len(last_action_data.text))},
      actions_iterator=reversed)
  
  def redo(self):
    self._undo_redo(
      self._redo_stack,
      self._undo_stack,
      action_handlers={
        'insert': lambda action_data: self._entry.insert_text(
          action_data.text, action_data.position),
        'delete': lambda action_data: self._entry.delete_text(
          action_data.position, action_data.position + len(action_data.text))},
      action_handlers_get_cursor_position={
        'insert': lambda last_action_data: (
          last_action_data.position + len(last_action_data.text)),
        'delete': lambda last_action_data: last_action_data.position})
  
  def undo_push(self, undo_push_list):
    """
    Manually add changes to the undo history. The changes are treated as one
    undo group (i.e. a single `undo()` call will undo all specified changes at
    once).
    
    If there are pending changes not yet added to the undo history, they are
    added first (as a separate undo group), and then the changes specified in
    this method.
    
    Calling this method completely removes the redo history.
    
    Parameters:
    
    * `undo_push_list` - List of `(action_type, position, text)` tuples to add
      as one undo action. `action_type` can be 'insert' for text insertion or
      'delete' for text deletion (other values raise `ValueError`). `position`
      is the starting entry cursor position of the changed text. `text` is the
      changed text.
    
    Raises:
    
    * `ValueError` - invalid `action_type`.
    """
    self._redo_stack = []
    
    self._undo_stack_push()
    
    for action_type, position, text in undo_push_list:
      if action_type not in self._ACTION_TYPES:
        raise ValueError('invalid action type "{0}"'.format(action_type))
      self._last_action_group.append(self._ActionData(action_type, position, text))
    
    self._undo_stack_push()
  
  def can_undo(self):
    return bool(self._undo_stack)
  
  def can_redo(self):
    return bool(self._redo_stack)
  
  def _on_entry_insert_text(self, entry, new_text, new_text_length, position):
    if self.undo_enabled and new_text:
      self._on_entry_action(entry.get_position(), new_text, 'insert')
   
  def _on_entry_delete_text(self, entry, start, end):
    if self.undo_enabled:
      text_to_delete = entry.get_text()[start:end]
      if text_to_delete:
        self._on_entry_action(start, text_to_delete, 'delete')
  
  def _on_entry_notify_cursor_position(self, entry, property_spec):
    if self._cursor_changed_by_action:
      self._cursor_changed_by_action = False
    else:
      self._undo_stack_push()
  
  def _on_entry_key_press_event(self, entry, event):
    if (event.state & gtk.accelerator_get_default_mod_mask()) == gtk.gdk.CONTROL_MASK:
      key_name = gtk.gdk.keyval_name(gtk.gdk.keyval_to_lower(event.keyval))
      if key_name == 'z':
        self.undo()
        return True
      elif key_name == 'y':
        self.redo()
        return True
  
  def _on_entry_action(self, position, text, action_type):
    self._redo_stack = []
    
    if self._last_action_type != action_type:
      self._undo_stack_push()
    
    self._last_action_group.append(self._ActionData(action_type, position, text))
    self._last_action_type = action_type
    
    self._cursor_changed_by_action = True
  
  def _undo_redo(
        self,
        stack_to_pop_from,
        stack_to_push_to,
        action_handlers,
        action_handlers_get_cursor_position,
        actions_iterator=None):
    self._undo_stack_push()
    
    if not stack_to_pop_from:
      return
    
    actions = stack_to_pop_from.pop()
    
    if actions_iterator is None:
      action_list = actions
    else:
      action_list = list(actions_iterator(actions))
    
    stack_to_push_to.append(actions)
    
    self.undo_enabled = False
    
    for action in action_list:
      action_handlers[action.action_type](action)
    
    self._entry.set_position(
      action_handlers_get_cursor_position[action_list[-1].action_type](action_list[-1]))
    
    self.undo_enabled = True
  
  def _undo_stack_push(self):
    if self._last_action_group:
      self._undo_stack.append(self._last_action_group)
      self._last_action_group = []
