# -*- coding: utf-8 -*-

"""Functions to display message dialogs."""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import traceback

import pygtk
pygtk.require('2.0')
import gtk

from export_layers import pygimplib as pg

from export_layers import exceptions


def display_message(
      message,
      message_type,
      parent=None,
      buttons=gtk.BUTTONS_OK,
      message_in_text_view=False,
      button_response_id_to_focus=None,
      message_markup=False):
  return pg.gui.display_message(
    message,
    message_type,
    title=pg.config.PLUGIN_TITLE,
    parent=parent,
    buttons=buttons,
    message_in_text_view=message_in_text_view,
    button_response_id_to_focus=button_response_id_to_focus,
    message_markup=message_markup)


def display_failure_message(
      main_message, failure_message, details, parent=None, report_description=None,
      display_details_initially=False):
  if report_description is None:
    report_description = _(
      'If you believe this is an error in the plug-in, you can help fix it'
      ' by sending a report with the text in the details to one of the sites below')
  
  pg.gui.display_alert_message(
    title=pg.config.PLUGIN_TITLE,
    app_name=pg.config.PLUGIN_TITLE,
    parent=parent,
    message_type=gtk.MESSAGE_WARNING,
    message_markup=main_message,
    message_secondary_markup=failure_message,
    details=details,
    display_details_initially=display_details_initially,
    report_uri_list=pg.config.BUG_REPORT_URL_LIST,
    report_description=report_description,
    focus_on_button=True)


def display_processing_failure_message(exception, parent=None):
  display_failure_message(
    _('There was a problem during processing:'),
    failure_message=str(exception),
    details=traceback.format_exc(),
    parent=parent)


def display_invalid_image_failure_message(parent=None):
  display_failure_message(
    _('There was a problem during processing.'
      ' Do not close the image during processing,'
      ' keep it open until the processing is finished successfully.'),
    failure_message='',
    details=traceback.format_exc(),
    parent=parent)


def display_import_export_settings_failure_message(main_message, details, parent=None):
  display_failure_message(
    main_message,
    failure_message='',
    details=details,
    parent=parent,
    report_description=_(
      'If you believe this is an error in the plug-in, you can help fix it'
      ' by sending a report with the file and the text in the details to one of the sites below'))


def get_failing_action_message(action_and_item_or_action_error):
  if isinstance(action_and_item_or_action_error, exceptions.ActionError):
    action, item = action_and_item_or_action_error.action, action_and_item_or_action_error.item
  else:
    action, item = action_and_item_or_action_error
  
  if 'procedure' not in action.tags and 'constraint' not in action.tags:
    raise ValueError('an action must have the "procedure" or "constraint" tag')
  
  if item is not None:
    if 'procedure' in action.tags:
      message_template = _('Failed to apply procedure "{}" on "{}" because:')
    elif 'constraint' in action.tags:
      message_template = _('Failed to apply constraint "{}" on "{}" because:')
  
    return message_template.format(action['display_name'].value, item.orig_name)
  else:
    if 'procedure' in action.tags:
      message_template = _('Failed to apply procedure "{}" because:')
    elif 'constraint' in action.tags:
      message_template = _('Failed to apply constraint "{}" because:')
    
    return message_template.format(action['display_name'].value)
