# -*- coding: utf-8 -*-
#
# This file is part of Export Layers.
#
# Copyright (C) 2013-2019 khalim19 <khalim19@gmail.com>
#
# Export Layers is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Export Layers is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Export Layers.  If not, see <https://www.gnu.org/licenses/>.

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import inspect
import os
import shutil
import unittest

import gimp
from gimp import pdb

from export_layers import pygimplib
from export_layers.pygimplib import pgfileformats
from export_layers.pygimplib import pgitemtree
from export_layers.pygimplib import pgpath
from export_layers.pygimplib import pgpdb
from export_layers.pygimplib import pgutils

from .. import config
config.init()

from .. import builtin_procedures
from .. import exportlayers
from .. import operations
from .. import settings_plugin

pygimplib.init()


_CURRENT_MODULE_DIRPATH = os.path.dirname(pgutils.get_current_module_filepath())
TEST_IMAGES_DIRPATH = os.path.join(_CURRENT_MODULE_DIRPATH, "test_images")

DEFAULT_EXPECTED_RESULTS_DIRPATH = os.path.join(TEST_IMAGES_DIRPATH, "expected_results")
OUTPUT_DIRPATH = os.path.join(TEST_IMAGES_DIRPATH, "temp_output")
INCORRECT_RESULTS_DIRPATH = os.path.join(TEST_IMAGES_DIRPATH, "incorrect_results")


class TestExportLayersCompareLayerContents(unittest.TestCase):
  
  @classmethod
  def setUpClass(cls):
    pdb.gimp_context_push()
    
    cls.test_image_filepath = os.path.join(
      TEST_IMAGES_DIRPATH, "test_export_layers_contents.xcf")
    cls.test_image = cls._load_image()
    
    cls.output_dirpath = OUTPUT_DIRPATH
    
    if os.path.exists(cls.output_dirpath):
      shutil.rmtree(cls.output_dirpath)
    
    if os.path.exists(INCORRECT_RESULTS_DIRPATH):
      shutil.rmtree(INCORRECT_RESULTS_DIRPATH)
    
    version_specific_expected_results_dirpath = (
      DEFAULT_EXPECTED_RESULTS_DIRPATH
      + "_"
      + "-".join([str(version_number_part) for version_number_part in gimp.version[:2]]))
    
    if os.path.isdir(version_specific_expected_results_dirpath):
      cls.expected_results_root_dirpath = version_specific_expected_results_dirpath
    else:
      cls.expected_results_root_dirpath = DEFAULT_EXPECTED_RESULTS_DIRPATH
    
    # key: path to directory containing expected results
    # value: gimp.Image instance
    cls.expected_images = {}
  
  @classmethod
  def tearDownClass(cls):
    pdb.gimp_image_delete(cls.test_image)
    for image in cls.expected_images.values():
      pdb.gimp_image_delete(image)
    
    pdb.gimp_context_pop()
    pdb.gimp_progress_end()
  
  def setUp(self):
    self.image_with_results = None
  
  def tearDown(self):
    if self.image_with_results is not None:
      pdb.gimp_image_delete(self.image_with_results)
    
    if os.path.exists(self.output_dirpath):
      shutil.rmtree(self.output_dirpath)
  
  def test_default_settings(self):
    self.compare()
  
  def test_use_image_size(self):
    self.compare(
      procedure_names_to_remove=["use_layer_size"],
      expected_results_dirpath=os.path.join(
        self.expected_results_root_dirpath, "use_image_size"))
  
  def test_background(self):
    self.compare(
      procedure_names_to_add={"insert_background_layers": 0},
      expected_results_dirpath=os.path.join(
        self.expected_results_root_dirpath, "background"))
  
  def test_background_autocrop_background(self):
    self.compare(
      procedure_names_to_add={
        "insert_background_layers": 0,
        "autocrop_background": None},
      expected_results_dirpath=os.path.join(
        self.expected_results_root_dirpath, "background"))
  
  def test_background_autocrop_background_use_image_size(self):
    self.compare(
      procedure_names_to_add={
        "insert_background_layers": 0,
        "autocrop_background": None},
      procedure_names_to_remove=["use_layer_size"],
      expected_results_dirpath=os.path.join(
        self.expected_results_root_dirpath,
        "background",
        "autocrop_background-use_image_size"))
  
  def test_foreground(self):
    layer_tree = pgitemtree.LayerTree(
      self.test_image, name=pygimplib.config.SOURCE_PERSISTENT_NAME)
    for layer_elem in layer_tree:
      if "background" in layer_elem.tags:
        layer_elem.remove_tag("background")
        layer_elem.add_tag("foreground")
    
    self.compare(
      procedure_names_to_add={"insert_foreground_layers": 0},
      expected_results_dirpath=os.path.join(
        self.expected_results_root_dirpath, "foreground"))
    
    self._reload_image()
  
  def compare(
        self,
        procedure_names_to_add=None,
        procedure_names_to_remove=None,
        different_results_and_expected_layers=None,
        expected_results_dirpath=None):
    settings = settings_plugin.create_settings()
    settings["special/image"].set_value(self.test_image)
    settings["main/output_directory"].set_value(self.output_dirpath)
    settings["main/file_extension"].set_value("xcf")
    
    if expected_results_dirpath is None:
      expected_results_dirpath = self.expected_results_root_dirpath
    
    if expected_results_dirpath not in self.expected_images:
      self.expected_images[expected_results_dirpath], expected_layers = (
        self._load_layers_from_dirpath(expected_results_dirpath))
    else:
      expected_layers = {
        layer.name: layer
        for layer in self.expected_images[expected_results_dirpath].layers}
    
    self._export(settings, procedure_names_to_add, procedure_names_to_remove)
    
    self.image_with_results, layers = self._load_layers_from_dirpath(self.output_dirpath)
    
    if different_results_and_expected_layers is not None:
      for layer_name, expected_layer_name in different_results_and_expected_layers:
        expected_layers[layer_name] = expected_layers[expected_layer_name]
    
    for layer in layers.values():
      test_case_name = inspect.stack()[1][-3]
      self._compare_layers(
        layer,
        expected_layers[layer.name],
        settings,
        test_case_name,
        expected_results_dirpath)
  
  @staticmethod
  def _export(settings, procedure_names_to_add, procedure_names_to_remove):
    if procedure_names_to_add is None:
      procedure_names_to_add = {}
    
    if procedure_names_to_remove is None:
      procedure_names_to_remove = []
    
    for procedure_name, order in procedure_names_to_add.items():
      operations.add(
        settings["main/procedures"],
        builtin_procedures.BUILTIN_PROCEDURES[procedure_name])
      if order is not None:
        operations.reorder(settings["main/procedures"], procedure_name, order)
    
    for procedure_name in procedure_names_to_remove:
      if procedure_name in settings["main/procedures/added"]:
        operations.remove(settings["main/procedures"], procedure_name)
    
    layer_exporter = exportlayers.LayerExporter(
      settings["special/run_mode"].value,
      settings["special/image"].value,
      settings["main"])
    
    layer_exporter.export()
    
    for procedure_name in procedure_names_to_add:
      operations.remove(settings["main/procedures"], procedure_name)
  
  def _compare_layers(
        self, layer, expected_layer, settings, test_case_name, expected_results_dirpath):
    if not pgpdb.compare_layers([layer, expected_layer]):
      self._save_incorrect_layers(
        layer, expected_layer, settings, test_case_name, expected_results_dirpath)
    
    self.assertEqual(
      pgpdb.compare_layers([layer, expected_layer]),
      True,
      msg=("Layers are not identical:\nprocessed layer: {}\nexpected layer: {}".format(
        layer.name, expected_layer.name)))
  
  def _save_incorrect_layers(
        self, layer, expected_layer, settings, test_case_name, expected_results_dirpath):
    incorrect_layers_dirpath = os.path.join(INCORRECT_RESULTS_DIRPATH, test_case_name)
    pgpath.make_dirs(incorrect_layers_dirpath)
    
    self._copy_incorrect_layer(
      layer, settings, self.output_dirpath, incorrect_layers_dirpath, "_actual")
    self._copy_incorrect_layer(
      expected_layer,
      settings,
      expected_results_dirpath,
      incorrect_layers_dirpath,
      "_expected")
  
  @staticmethod
  def _copy_incorrect_layer(
        layer, settings, layer_dirpath, incorrect_layers_dirpath, filename_suffix):
    layer_input_filename = "{}.{}".format(
      layer.name, settings["main/file_extension"].value)
    layer_output_filename = "{}{}.{}".format(
      layer.name, filename_suffix, settings["main/file_extension"].value)
    
    shutil.copy(
      os.path.join(layer_dirpath, layer_input_filename),
      os.path.join(incorrect_layers_dirpath, layer_output_filename))
  
  @classmethod
  def _load_image(cls):
    return pdb.gimp_file_load(
      cls.test_image_filepath, os.path.basename(cls.test_image_filepath))
  
  @classmethod
  def _reload_image(cls):
    pdb.gimp_image_delete(cls.test_image)
    cls.test_image = cls._load_image()
  
  @classmethod
  def _load_layers_from_dirpath(cls, layers_dirpath):
    return cls._load_layers(cls._list_layer_filepaths(layers_dirpath))
  
  @staticmethod
  def _load_layers(layer_filepaths):
    """
    Load layers from specified file paths into a new image. Return the image and
    a dict with (layer name: gimp.Layer instance) pairs.
    """
    image = pgpdb.load_layers(layer_filepaths, image=None, strip_file_extension=True)
    return image, {layer.name: layer for layer in image.layers}
  
  @staticmethod
  def _list_layer_filepaths(layers_dirpath):
    layer_filepaths = []
    
    for filename in os.listdir(layers_dirpath):
      path = os.path.join(layers_dirpath, filename)
      if os.path.isfile(path):
        layer_filepaths.append(path)
    
    return layer_filepaths


#===============================================================================


def test_export_for_all_file_formats(layer_exporter, export_settings):
  orig_output_dirpath = export_settings["output_directory"].value
  
  for file_format in pgfileformats.file_formats:
    for file_extension in file_format.file_extensions:
      export_settings["file_extension"].set_value(file_extension)
      export_settings["output_directory"].set_value(
        os.path.join(orig_output_dirpath, file_extension))
      try:
        layer_exporter.export()
      except exportlayers.ExportLayersError:
        # Do not stop execution when one file format causes an error.
        continue


def test_add_all_pdb_procedures_as_operations():
  """
  Add all PDB procedures as operations to check if all setting types are
  properly supported.
  """
  procedures = operations.create("all_pdb_procedures")
  
  unused_, procedure_names = pdb.gimp_procedural_db_query("", "", "", "", "", "", "")
  
  for procedure_name in procedure_names:
    operations.add(procedures, pdb[procedure_name])
