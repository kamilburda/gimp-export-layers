# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import mock
import unittest

from gimp import pdb
import gimpenums

from export_layers import pygimplib as pg

from export_layers.pygimplib.tests import stubs_gimp

from export_layers import builtin_procedures
from export_layers import exporter as exporter_
from export_layers import actions
from export_layers import settings_main


class TestLayerExporterInitialActions(unittest.TestCase):
  
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
    
    exporter = exporter_.LayerExporter(
      settings['special/run_mode'].value,
      settings['special/image'].value,
      settings['main'])
    
    actions.add(
      settings['main/procedures'],
      builtin_procedures.BUILTIN_PROCEDURES['insert_background_layers'])
    
    exporter.add_procedure(pg.utils.empty_func, [actions.DEFAULT_PROCEDURES_GROUP])
    
    exporter.export(
      is_preview=True, process_contents=False, process_names=False, process_export=False)
    
    added_action_items = exporter.invoker.list_actions(group=actions.DEFAULT_PROCEDURES_GROUP)
    
    # Includes built-in procedures added by default
    self.assertEqual(len(added_action_items), 6)
    
    initial_invoker = added_action_items[1]
    self.assertIsInstance(initial_invoker, pg.invoker.Invoker)
    
    actions_in_initial_invoker = initial_invoker.list_actions(
      group=actions.DEFAULT_PROCEDURES_GROUP)
    self.assertEqual(len(actions_in_initial_invoker), 1)
    self.assertEqual(actions_in_initial_invoker[0], (pg.utils.empty_func, (), {}))


class TestAddActionFromSettings(unittest.TestCase):
  
  def setUp(self):
    self.exporter = exporter_.LayerExporter(
      initial_run_mode=0,
      input_image=mock.MagicMock(),
      export_settings=mock.MagicMock(),
      overwrite_chooser=mock.MagicMock(),
      progress_updater=mock.MagicMock())
    
    self.invoker = pg.invoker.Invoker()
    
    self.exporter._invoker = self.invoker
    
    self.procedures = actions.create('procedures')
    
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
    procedure = actions.add(
      self.procedures, builtin_procedures.BUILTIN_PROCEDURES['insert_background_layers'])
    
    self.exporter._add_action_from_settings(procedure)
    
    added_action_items = self.invoker.list_actions(group=actions.DEFAULT_PROCEDURES_GROUP)
    
    self.assertEqual(len(added_action_items), 1)
    self.assertEqual(added_action_items[0][1], ('background',))
    self.assertEqual(added_action_items[0][2], {})
  
  def test_add_pdb_proc_as_action_without_run_mode(self):
    self.procedure_stub.params = self.procedure_stub.params[1:]
    self._test_add_pdb_proc_as_action(self.procedure_stub, ((), ''), {})
  
  def test_add_pdb_proc_as_action_with_run_mode(self):
    self._test_add_pdb_proc_as_action(
      self.procedure_stub, ((), ''), {'run_mode': gimpenums.RUN_NONINTERACTIVE})
  
  def _test_add_pdb_proc_as_action(self, pdb_procedure, expected_args, expected_kwargs):
    procedure = actions.add(self.procedures, pdb_procedure)
    
    with mock.patch('export_layers.exporter.pdb') as pdb_mock:
      pdb_mock.__getitem__.return_value = pdb_procedure
      
      self.exporter._add_action_from_settings(procedure)
    
    added_action_items = self.invoker.list_actions(group=actions.DEFAULT_PROCEDURES_GROUP)
    
    self.assertEqual(len(added_action_items), 1)
    self.assertEqual(added_action_items[0][1], expected_args)
    self.assertDictEqual(added_action_items[0][2], expected_kwargs)
