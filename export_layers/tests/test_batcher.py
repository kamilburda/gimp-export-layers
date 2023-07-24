# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import mock
import unittest

from gimp import pdb
import gimpenums

from export_layers import pygimplib as pg

from export_layers.pygimplib.tests import stubs_gimp

from export_layers import actions as actions_
from export_layers import batcher as batcher_
from export_layers import builtin_procedures
from export_layers import settings_main
from export_layers import utils as utils_


class TestBatcherInitialActions(unittest.TestCase):
  
  @classmethod
  def setUpClass(cls):
    cls.image = pdb.gimp_image_new(1, 1, gimpenums.RGB)
  
  @classmethod
  def tearDownClass(cls):
    pdb.gimp_image_delete(cls.image)
  
  def test_add_procedure_added_procedure_is_first_in_action_list(self):
    settings = settings_main.create_settings()
    settings['special/image'].set_value(self.image)
    settings['main/file_extension'].set_value('xcf')
    
    batcher = batcher_.Batcher(
      settings['special/run_mode'].value,
      settings['special/image'].value,
      settings['main/procedures'],
      settings['main/constraints'],
    )
    
    actions_.add(
      settings['main/procedures'],
      builtin_procedures.BUILTIN_PROCEDURES['insert_background_layers'])
    
    batcher.add_procedure(pg.utils.empty_func, [actions_.DEFAULT_PROCEDURES_GROUP])
    
    batcher.run(
      is_preview=True, process_contents=False, process_names=False, process_export=False,
      **utils_.get_settings_for_batcher(settings['main']))
    
    added_action_items = batcher.invoker.list_actions(group=actions_.DEFAULT_PROCEDURES_GROUP)
    
    # Includes built-in procedures added by default
    self.assertEqual(len(added_action_items), 6)
    
    initial_invoker = added_action_items[1]
    self.assertIsInstance(initial_invoker, pg.invoker.Invoker)
    
    actions_in_initial_invoker = initial_invoker.list_actions(
      group=actions_.DEFAULT_PROCEDURES_GROUP)
    self.assertEqual(len(actions_in_initial_invoker), 1)
    self.assertEqual(actions_in_initial_invoker[0], (pg.utils.empty_func, (), {}))


class TestAddActionFromSettings(unittest.TestCase):
  
  def setUp(self):
    self.batcher = batcher_.Batcher(
      initial_run_mode=0,
      input_image=mock.MagicMock(),
      procedures=mock.MagicMock(),
      constraints=mock.MagicMock(),
      overwrite_chooser=mock.MagicMock(),
      progress_updater=mock.MagicMock())
    
    self.invoker = pg.invoker.Invoker()
    
    self.batcher._invoker = self.invoker
    
    self.procedures = actions_.create('procedures')
    
    self.procedure_stub = stubs_gimp.PdbProcedureStub(
      name='file-png-save',
      type_=gimpenums.PLUGIN,
      params=(
        (gimpenums.PDB_INT32, 'run-mode', 'The run mode'),
        (gimpenums.PDB_INT32ARRAY, 'save-options', 'Save options'),
        (gimpenums.PDB_STRING, 'filename', 'Filename to save the image in')),
      return_vals=None,
      blurb='Saves files in PNG file format')
  
  def test_add_action_from_settings(self):
    procedure = actions_.add(
      self.procedures, builtin_procedures.BUILTIN_PROCEDURES['insert_background_layers'])
    
    self.batcher._add_action_from_settings(procedure)
    
    added_action_items = self.invoker.list_actions(group=actions_.DEFAULT_PROCEDURES_GROUP)
    
    self.assertEqual(len(added_action_items), 1)
    self.assertEqual(
      added_action_items[0][1],
      list(procedure['arguments'])
      + [builtin_procedures.BUILTIN_PROCEDURES_FUNCTIONS['insert_background_layers']])
    self.assertEqual(added_action_items[0][2], {})
  
  def test_add_pdb_proc_as_action_without_run_mode(self):
    self.procedure_stub.params = self.procedure_stub.params[1:]
    self._test_add_pdb_proc_as_action(
      self.procedure_stub, [('save-options', ()), ('filename', '')], {})
  
  def test_add_pdb_proc_as_action_with_run_mode(self):
    self._test_add_pdb_proc_as_action(
      self.procedure_stub, [('run-mode', 0), ('save-options', ()), ('filename', '')], {})
  
  def _test_add_pdb_proc_as_action(
        self, pdb_procedure, expected_arg_names_and_values, expected_kwargs):
    procedure = actions_.add(self.procedures, pdb_procedure)
    
    with mock.patch('export_layers.batcher.pdb') as pdb_mock:
      pdb_mock.__getitem__.return_value = pdb_procedure
      
      self.batcher._add_action_from_settings(procedure)
    
    added_action_items = self.invoker.list_actions(group=actions_.DEFAULT_PROCEDURES_GROUP)
    
    added_action_item_names_and_values = [
      (setting.name, setting.value) for setting in added_action_items[0][1][:-1]
    ]
    
    self.assertEqual(len(added_action_items), 1)
    self.assertEqual(added_action_item_names_and_values, added_action_item_names_and_values)
    self.assertEqual(added_action_items[0][1][-1], pdb_procedure)
    self.assertDictEqual(added_action_items[0][2], expected_kwargs)


class TestGetReplacedArgsAndKwargs(unittest.TestCase):
  
  def test_get_replaced_args(self):
    batcher = batcher_.Batcher(
      initial_run_mode=0,
      input_image=mock.MagicMock(),
      procedures=mock.MagicMock(),
      constraints=mock.MagicMock(),
      overwrite_chooser=mock.MagicMock(),
      progress_updater=mock.MagicMock())
    
    invoker = pg.invoker.Invoker()
    image = stubs_gimp.ImageStub()
    layer = stubs_gimp.LayerStub()
    
    batcher._invoker = invoker
    batcher._current_image = image
    batcher._current_raw_item = layer
    
    actions = actions_.create('procedures')
    actions_.add(actions, {
      'name': 'autocrop',
      'type': 'procedure',
      'function': '',
      'enabled': True,
      'display_name': 'Autocrop',
      'action_groups': ['basic'],
      'arguments': [
        {
          'type': 'int',
          'name': 'run_mode',
          'default_value': 0,
        },
        {
          'type': 'placeholder_image',
          'name': 'image',
          'default_value': 'current_image',
        },
        {
          'type': 'placeholder_layer',
          'name': 'layer',
          'default_value': 'current_layer',
        },
        {
          'type': 'int',
          'name': 'offset_x',
          'default_value': 10,
        },
        {
          'type': 'int',
          'name': 'offset_y',
          'default_value': 50,
        },
        {
          'type': 'string',
          'name': 'same_value_as_placeholder_value',
          'default_value': 'current_image',
        },
      ],
    })
    
    replaced_args = batcher._get_replaced_args(actions['autocrop/arguments'])
    
    self.assertListEqual(replaced_args, [0, image, layer, 10, 50, 'current_image'])
