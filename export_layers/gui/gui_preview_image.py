# -*- coding: utf-8 -*-
#
# This file is part of Export Layers.
#
# Copyright (C) 2013-2018 khalim19 <khalim19@gmail.com>
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

"""
This module defines a preview widget displaying scaled-down contents of a layer
to be exported.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import array
import traceback

import pygtk
pygtk.require("2.0")
import gtk
import gobject
import pango

import gimp
from gimp import pdb
import gimpenums

from export_layers import pygimplib
from export_layers.pygimplib import pgconstants
from export_layers.pygimplib import pggui
from export_layers.pygimplib import pgpdb

from . import gui_preview_base

#===============================================================================


def display_image_preview_failure_message(details, parent=None):
  pggui.display_error_message(
    title=pygimplib.config.PLUGIN_TITLE,
    app_name=pygimplib.config.PLUGIN_TITLE,
    parent=parent,
    message_type=gtk.MESSAGE_WARNING,
    message_markup=_(
      "There was a problem with updating the image preview."),
    message_secondary_markup=_(
      "If you believe this is an error in the plug-in, you can help fix it "
      "by sending a report with the text in the details to one of the sites below."),
    details=details,
    display_details_initially=False,
    report_uri_list=pygimplib.config.BUG_REPORT_URL_LIST,
    report_description="",
    focus_on_button=True)


class ExportImagePreview(gui_preview_base.ExportPreview):
  
  _BOTTOM_WIDGETS_PADDING = 5
  _IMAGE_PREVIEW_PADDING = 3
  _MAX_PREVIEW_SIZE_PIXELS = 1024
  _PREVIEW_ALPHA_CHECK_SIZE = 4
  
  def __init__(self, layer_exporter, initial_previered_layer_id=None):
    super().__init__()
    
    self._layer_exporter = layer_exporter
    self._initial_previewed_layer_id = initial_previered_layer_id
    
    if not self._layer_exporter.operation_executor.has_matching_operation(
             self._layer_exporter_on_after_insert_layer, "after_insert_layer"):
      self._layer_exporter.operation_executor.add_operation(
        self._layer_exporter_on_after_insert_layer, ["after_insert_layer"])
    
    if not self._layer_exporter.operation_executor.has_matching_operation(
             self._layer_exporter_on_after_create_image_copy, "after_create_image_copy"):
      self._layer_exporter.operation_executor.add_operation(
        self._layer_exporter_on_after_create_image_copy, ["after_create_image_copy"])
    
    self._layer_elem = None
    
    self._preview_pixbuf = None
    self._previous_preview_pixbuf_width = None
    self._previous_preview_pixbuf_height = None
    
    self.draw_checkboard_alpha_background = True
    
    self._is_updating = False
    
    self._preview_width = None
    self._preview_height = None
    self._preview_scaling_factor = None
    
    self._init_gui()
    
    self._preview_alpha_check_color_first, self._preview_alpha_check_color_second = (
      int(hex(shade)[2:] * 4, 16) for shade in gimp.checks_get_shades(gimp.check_type()))
    
    self._placeholder_image_size = gtk.icon_size_lookup(
      self._placeholder_image.get_property("icon-size"))
    
    self._vbox.connect("size-allocate", self._on_vbox_size_allocate)
    
    self._widget = self._vbox
  
  def update(self):
    update_locked = super().update()
    if update_locked:
      return
    
    self.layer_elem = self._set_initial_layer_elem(self.layer_elem)
    if self.layer_elem is None:
      return
    
    if not self._layer_exporter.layer_tree.filter.is_match(self.layer_elem):
      self.layer_elem = None
      return
    
    if not pdb.gimp_item_is_valid(self.layer_elem.item):
      self.clear()
      return
    
    self._is_updating = True
    
    self._placeholder_image.hide()
    self._preview_image.show()
    self._set_layer_name_label(self.layer_elem.name)
    
    # Make sure that the correct size is allocated to the image.
    while gtk.events_pending():
      gtk.main_iteration()
    
    with pgpdb.redirect_messages():
      preview_pixbuf = self._get_in_memory_preview(self.layer_elem.item)
    
    if preview_pixbuf is not None:
      self._preview_image.set_from_pixbuf(preview_pixbuf)
    else:
      self.clear(use_layer_name=True)
    
    self._is_updating = False
  
  def clear(self, use_layer_name=False):
    self.layer_elem = None
    self._preview_image.clear()
    self._preview_image.hide()
    self._show_placeholder_image(use_layer_name)
  
  def set_sensitive(self, sensitive):
    self._widget.set_sensitive(sensitive)
  
  def resize(self, update_when_larger_than_image_size=False):
    """
    Resize the preview if the widget is smaller than the previewed image so that
    the image fits the widget.
    """
    
    if not self._is_updating and self._preview_image.get_mapped():
      self._resize_preview(self._preview_image.get_allocation(), self._preview_pixbuf)
  
  def is_larger_than_image(self):
    """
    Return True if the preview widget is larger than the image. If no image is
    previewed, return False.
    """
    
    allocation = self._preview_image.get_allocation()
    return (
      self._preview_pixbuf is not None
      and allocation.width > self._preview_pixbuf.get_width()
      and allocation.height > self._preview_pixbuf.get_height())
  
  def update_layer_elem(self):
    if (self.layer_elem is not None
        and self._layer_exporter.layer_tree is not None
        and self.layer_elem.item.ID in self._layer_exporter.layer_tree):
      layer_elem = self._layer_exporter.layer_tree[self.layer_elem.item.ID]
      if self._layer_exporter.layer_tree.filter.is_match(layer_elem):
        self.layer_elem = layer_elem
        self._set_layer_name_label(self.layer_elem.name)
  
  @property
  def layer_elem(self):
    return self._layer_elem
  
  @layer_elem.setter
  def layer_elem(self, value):
    self._layer_elem = value
    if value is None:
      self._preview_pixbuf = None
      self._previous_preview_pixbuf_width = None
      self._previous_preview_pixbuf_height = None
  
  @property
  def widget(self):
    return self._widget
  
  def _init_gui(self):
    self._preview_image = gtk.Image()
    self._preview_image.set_no_show_all(True)
    
    self._placeholder_image = gtk.Image()
    self._placeholder_image.set_from_stock(
      gtk.STOCK_DIALOG_QUESTION, gtk.ICON_SIZE_DIALOG)
    self._placeholder_image.set_no_show_all(True)
    
    self._label_layer_name = gtk.Label()
    self._label_layer_name.set_ellipsize(pango.ELLIPSIZE_MIDDLE)
    
    self._vbox = gtk.VBox(homogeneous=False)
    self._vbox.pack_start(
      self._preview_image, expand=True, fill=True, padding=self._IMAGE_PREVIEW_PADDING)
    self._vbox.pack_start(
      self._placeholder_image, expand=True, fill=True,
      padding=self._IMAGE_PREVIEW_PADDING)
    self._vbox.pack_start(
      self._label_layer_name, expand=False, fill=False,
      padding=self._BOTTOM_WIDGETS_PADDING)
    
    self._show_placeholder_image()
  
  def _set_initial_layer_elem(self, layer_elem):
    if layer_elem is None:
      if (self._layer_exporter.layer_tree is not None
          and self._initial_previewed_layer_id in self._layer_exporter.layer_tree):
        layer_elem = self._layer_exporter.layer_tree[self._initial_previewed_layer_id]
        self._initial_previewed_layer_id = None
        return layer_elem
      else:
        self._initial_previewed_layer_id = None
        return None
    else:
      return layer_elem
  
  def _get_in_memory_preview(self, layer):
    self._preview_width, self._preview_height = self._get_preview_size(
      layer.width, layer.height)
    self._preview_scaling_factor = self._preview_width / layer.width
    
    image_preview = self._get_image_preview()
    
    if image_preview is None:
      return None
    
    if not image_preview.layers:
      pdb.gimp_image_delete(image_preview)
      return None
    
    if image_preview.base_type != gimpenums.RGB:
      pdb.gimp_image_convert_rgb(image_preview)
    
    layer_preview = image_preview.layers[0]
    
    if layer_preview.mask is not None:
      layer_preview.remove_mask(gimpenums.MASK_APPLY)
    
    # Recompute the size as the layer may have been resized during the export.
    self._preview_width, self._preview_height = self._get_preview_size(
      layer_preview.width, layer_preview.height)
    
    self._preview_width, self._preview_height, preview_data = _get_preview_data(
      layer_preview, self._preview_width, self._preview_height)
    
    layer_preview_pixbuf = self._get_preview_pixbuf(
      layer_preview, self._preview_width, self._preview_height, preview_data)
    
    pdb.gimp_image_delete(image_preview)
    
    return layer_preview_pixbuf
  
  def _get_image_preview(self):
    layer_tree = self._layer_exporter.layer_tree
    layer_tree_filter = layer_tree.filter if layer_tree is not None else None
    
    with self._layer_exporter.modify_export_settings(
           {"constraints/only_selected_layers": True,
            "selected_layers": {
              self._layer_exporter.image.ID: set([self.layer_elem.item.ID])}},
           self._settings_events_to_temporarily_disable):
      try:
        image_preview = self._layer_exporter.export(
          processing_groups=["layer_contents"],
          layer_tree=layer_tree,
          keep_image_copy=True)
      except Exception:
        display_image_preview_failure_message(
          details=traceback.format_exc(), parent=pggui.get_toplevel_window(self._widget))
        image_preview = None
    
    if layer_tree_filter is not None:
      self._layer_exporter.layer_tree.filter = layer_tree_filter
    
    return image_preview
  
  def _layer_exporter_on_after_create_image_copy(self, image_copy):
    pdb.gimp_image_resize(
      image_copy,
      max(1, int(round(image_copy.width * self._preview_scaling_factor))),
      max(1, int(round(image_copy.height * self._preview_scaling_factor))),
      0, 0)
    
    pdb.gimp_context_set_interpolation(gimpenums.INTERPOLATION_NONE)
  
  def _layer_exporter_on_after_insert_layer(self, image, layer, layer_exporter):
    if not pdb.gimp_item_is_group(layer):
      pdb.gimp_item_transform_scale(
        layer,
        layer.offsets[0] * self._preview_scaling_factor,
        layer.offsets[1] * self._preview_scaling_factor,
        (layer.offsets[0] + layer.width) * self._preview_scaling_factor,
        (layer.offsets[1] + layer.height) * self._preview_scaling_factor)
  
  def _get_preview_pixbuf(self, layer, preview_width, preview_height, preview_data):
    # The following code is largely based on the implementation of
    # `gimp_pixbuf_from_data` from:
    # https://github.com/GNOME/gimp/blob/gimp-2-8/libgimp/gimppixbuf.c
    layer_preview_pixbuf = gtk.gdk.pixbuf_new_from_data(
      preview_data, gtk.gdk.COLORSPACE_RGB, layer.has_alpha, 8, preview_width,
      preview_height, preview_width * layer.bpp)
    
    self._preview_pixbuf = layer_preview_pixbuf
    
    if layer.has_alpha:
      layer_preview_pixbuf = _add_alpha_background_to_pixbuf(
        layer_preview_pixbuf, layer.opacity, self.draw_checkboard_alpha_background,
        self._PREVIEW_ALPHA_CHECK_SIZE,
        self._preview_alpha_check_color_first, self._preview_alpha_check_color_second)
    
    return layer_preview_pixbuf
  
  def _get_preview_size(self, width, height):
    preview_widget_allocation = self._preview_image.get_allocation()
    preview_widget_width = preview_widget_allocation.width
    preview_widget_height = preview_widget_allocation.height
    
    if preview_widget_width > preview_widget_height:
      preview_height = min(preview_widget_height, height, self._MAX_PREVIEW_SIZE_PIXELS)
      preview_width = int(round((preview_height / height) * width))
      
      if preview_width > preview_widget_width:
        preview_width = preview_widget_width
        preview_height = int(round((preview_width / width) * height))
    else:
      preview_width = min(preview_widget_width, width, self._MAX_PREVIEW_SIZE_PIXELS)
      preview_height = int(round((preview_width / width) * height))
      
      if preview_height > preview_widget_height:
        preview_height = preview_widget_height
        preview_width = int(round((preview_height / height) * width))
    
    if preview_width == 0:
      preview_width = 1
    if preview_height == 0:
      preview_height = 1
    
    return preview_width, preview_height
  
  def _resize_preview(self, preview_allocation, preview_pixbuf):
    if preview_pixbuf is None:
      return
    
    if (preview_allocation.width >= preview_pixbuf.get_width()
        and preview_allocation.height >= preview_pixbuf.get_height()):
      return
    
    scaled_preview_width, scaled_preview_height = self._get_preview_size(
      preview_pixbuf.get_width(), preview_pixbuf.get_height())
    
    if (self._previous_preview_pixbuf_width == scaled_preview_width
        and self._previous_preview_pixbuf_height == scaled_preview_height):
      return
    
    scaled_preview_pixbuf = preview_pixbuf.scale_simple(
      scaled_preview_width, scaled_preview_height, gtk.gdk.INTERP_NEAREST)
    
    scaled_preview_pixbuf = _add_alpha_background_to_pixbuf(
      scaled_preview_pixbuf, 100, self.draw_checkboard_alpha_background,
      self._PREVIEW_ALPHA_CHECK_SIZE,
      self._preview_alpha_check_color_first, self._preview_alpha_check_color_second)
    
    self._preview_image.set_from_pixbuf(scaled_preview_pixbuf)
    
    self._previous_preview_pixbuf_width = scaled_preview_width
    self._previous_preview_pixbuf_height = scaled_preview_height
  
  def _on_vbox_size_allocate(self, image_widget, allocation):
    if not self._is_updating and not self._preview_image.get_mapped():
      preview_widget_allocated_width = allocation.width - self._IMAGE_PREVIEW_PADDING * 2
      preview_widget_allocated_height = (
        allocation.height - self._label_layer_name.get_allocation().height
        - self._BOTTOM_WIDGETS_PADDING * 2 - self._IMAGE_PREVIEW_PADDING * 2)
      
      if (preview_widget_allocated_width < self._placeholder_image_size[0]
          or preview_widget_allocated_height < self._placeholder_image_size[1]):
        self._placeholder_image.hide()
      else:
        self._placeholder_image.show()
  
  def _show_placeholder_image(self, use_layer_name=False):
    self._placeholder_image.show()
    if not use_layer_name:
      self._set_layer_name_label(_("No selection"))
  
  def _set_layer_name_label(self, layer_name):
    self._label_layer_name.set_markup(
      "<i>{0}</i>".format(
        gobject.markup_escape_text(
          layer_name.encode(pgconstants.GTK_CHARACTER_ENCODING))))

  
def _add_alpha_background_to_pixbuf(
      pixbuf, opacity, use_checkboard_background=False, check_size=None,
      check_color_first=None, check_color_second=None):
  if use_checkboard_background:
    pixbuf_with_alpha_background = gtk.gdk.Pixbuf(
      gtk.gdk.COLORSPACE_RGB, False, 8,
      pixbuf.get_width(), pixbuf.get_height())
    
    pixbuf.composite_color(
      pixbuf_with_alpha_background, 0, 0,
      pixbuf.get_width(), pixbuf.get_height(),
      0, 0, 1.0, 1.0, gtk.gdk.INTERP_NEAREST,
      int(round((opacity / 100.0) * 255)),
      0, 0, check_size, check_color_first, check_color_second)
  else:
    pixbuf_with_alpha_background = gtk.gdk.Pixbuf(
      gtk.gdk.COLORSPACE_RGB, True, 8,
      pixbuf.get_width(), pixbuf.get_height())
    pixbuf_with_alpha_background.fill(0xffffff00)
    
    pixbuf.composite(
      pixbuf_with_alpha_background, 0, 0,
      pixbuf.get_width(), pixbuf.get_height(),
      0, 0, 1.0, 1.0, gtk.gdk.INTERP_NEAREST,
      int(round((opacity / 100.0) * 255)))
  
  return pixbuf_with_alpha_background

  
def _get_preview_data(layer, preview_width, preview_height):
  actual_preview_width, actual_preview_height, unused_, unused_, preview_data = (
    pdb.gimp_drawable_thumbnail(layer, preview_width, preview_height))
  
  return (
    actual_preview_width, actual_preview_height,
    array.array(b"B", preview_data).tostring())
