# -*- coding: utf-8 -*-

"""Preview widget displaying a scaled-down image to be processed."""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import array
import time
import traceback

import pygtk
pygtk.require('2.0')
import gtk
import gobject
import pango

import gimp
from gimp import pdb
import gimpenums

from export_layers import pygimplib as pg

from export_layers import actions
from export_layers import builtin_constraints
from export_layers import exceptions
from export_layers import utils as utils_

from export_layers.gui import messages as messages_
from export_layers.gui import preview_base as preview_base_


class ImagePreview(preview_base_.Preview):
  """
  This class defines a widget displaying a preview of an image to be processed,
  including its name.
  
  Signals:
  
  * `'preview-updated'` - The preview was updated by calling `update()`. This
    signal is not emitted if the update is locked.
    
    Arguments:
    
    * `error` - If `None`, the preview was updated successfully. Otherwise,
      this is an `Exception` object describing the error that occurred during
      the update.
    * `update_duration_seconds` - Duration of the update in seconds as a float.
      The duration only considers the update of the image contents (i.e. does
      not consider the duration of updating the label of the image name).
  """
  
  __gsignals__ = {
    b'preview-updated': (
      gobject.SIGNAL_RUN_FIRST, None, (gobject.TYPE_PYOBJECT, gobject.TYPE_FLOAT)),
  }
  
  _MANUAL_UPDATE_LOCK = '_manual_update'
  
  _WIDGET_SPACING = 5
  _BORDER_WIDTH = 6
  _PREVIEW_ALPHA_CHECK_SIZE = 4
  
  def __init__(self, batcher, settings):
    super().__init__()
    
    self._batcher = batcher
    self._settings = settings
    
    self._item = None
    
    self._preview_pixbuf = None
    self._previous_preview_pixbuf_width = None
    self._previous_preview_pixbuf_height = None
    
    self.draw_checkboard_alpha_background = True
    
    self._is_updating = False
    self._is_preview_image_allocated_size = False
    
    self._preview_width = None
    self._preview_height = None
    self._preview_scaling_factor = None
    
    self._resize_image_action_id = None
    self._merge_items_action_id = None
    self._scale_item_action_id = None
    self._resize_item_action_id = None
    
    self.prepare_image_for_rendering()
    
    self._init_gui()
    
    self._preview_alpha_check_color_first, self._preview_alpha_check_color_second = (
      int(hex(shade)[2:] * 4, 16) for shade in gimp.checks_get_shades(gimp.check_type()))
    
    self.connect('size-allocate', self._on_size_allocate)
    self._preview_image.connect('size-allocate', self._on_preview_image_size_allocate)
    
    self._button_menu.connect('clicked', self._on_button_menu_clicked)
    self._menu_item_update_automatically.connect(
      'toggled', self._on_menu_item_update_automatically_toggled)
    self._button_refresh.connect('clicked', self._on_button_refresh_clicked)
  
  @property
  def item(self):
    return self._item
  
  @item.setter
  def item(self, value):
    self._item = value
    if value is None:
      self._preview_pixbuf = None
      self._previous_preview_pixbuf_width = None
      self._previous_preview_pixbuf_height = None
  
  @property
  def menu_item_update_automatically(self):
    return self._menu_item_update_automatically
  
  def update(self):
    update_locked = super().update()
    if update_locked:
      return
    
    if self.item is None:
      return
    
    if not pdb.gimp_item_is_valid(self.item.raw):
      self.clear()
      return
    
    self._placeholder_image.hide()
    
    if self.item.type != pg.itemtree.TYPE_FOLDER:
      self._is_updating = True
      
      self._folder_image.hide()
      self._preview_image.show()
      self._set_item_name_label(self.item.name)
      
      if self._is_preview_image_allocated_size:
        self._set_contents()
    else:
      self._preview_image.hide()
      self._show_folder_image()
      self._set_item_name_label(self.item.name)
  
  def clear(self, use_item_name=False):
    self.item = None
    self._preview_image.clear()
    self._preview_image.hide()
    self._folder_image.hide()
    self._show_placeholder_image(use_item_name)
  
  def resize(self, update_when_larger_than_image_size=False):
    """
    Resize the preview if the widget is smaller than the previewed image so that
    the image fits the widget.
    """
    if not self._is_updating and self._preview_image.get_mapped():
      self._resize_preview(self._preview_image.get_allocation(), self._preview_pixbuf)
  
  def is_larger_than_image(self):
    """
    Return `True` if the preview widget is larger than the image. If no image is
    previewed, return `False`.
    """
    allocation = self._preview_image.get_allocation()
    return (
      self._preview_pixbuf is not None
      and allocation.width > self._preview_pixbuf.get_width()
      and allocation.height > self._preview_pixbuf.get_height())
  
  def update_item(self, raw_item_id=None):
    if raw_item_id is None:
      if (self.item is not None
          and self._batcher.item_tree is not None
          and self.item.raw.ID in self._batcher.item_tree):
        raw_item_id = self.item.raw.ID
        should_update = True
      else:
        should_update = False
    else:
      should_update = raw_item_id in self._batcher.item_tree
    
    if should_update:
      item = self._batcher.item_tree[raw_item_id]
      if self._batcher.item_tree.filter.is_match(item):
        self.item = item
        self._set_item_name_label(self.item.name)
  
  def prepare_image_for_rendering(
        self, resize_image_action_groups=None, scale_item_action_groups=None):
    """Adds procedures that prepare an image for rendering in the preview.
    
    Specifically, the image to be previewed is resized, scaled and later merged
    into a single layer.
    
    Subsequent calls to this method will remove the previously added procedures.
    
    The optional action groups allow to customize at which point during
    processing the resize and scale procedures are applied. By default, these
    procedures are applied before applying other procedures added by the user.
    """
    if resize_image_action_groups is None:
      resize_image_action_groups = ['before_process_items_contents']
    
    if scale_item_action_groups is None:
      scale_item_action_groups = ['before_process_item_contents']
    
    self._batcher.remove_action(
      self._resize_image_action_id, groups='all', ignore_if_not_exists=True)
    self._resize_image_action_id = self._batcher.add_procedure(
      self._resize_image_for_batcher, resize_image_action_groups, ignore_if_exists=True)
    
    self._batcher.remove_action(
      self._merge_items_action_id, groups='all', ignore_if_not_exists=True)
    self._merge_items_action_id = self._batcher.add_procedure(
      self._merge_items_for_batcher, ['after_process_item_contents'], ignore_if_exists=True)
    
    self._batcher.remove_action(
      self._scale_item_action_id, groups='all', ignore_if_not_exists=True)
    self._scale_item_action_id = self._batcher.add_procedure(
      self._scale_item_for_batcher, scale_item_action_groups, ignore_if_exists=True)
    
    self._batcher.remove_action(
      self._resize_item_action_id, groups='all', ignore_if_not_exists=True)
    self._resize_item_action_id = self._batcher.add_procedure(
      self._resize_item_for_batcher, ['after_process_item_contents'], ignore_if_exists=True)
  
  def _set_contents(self):
    # Sanity check in case `item` changes before `'size-allocate'` is emitted.
    if self.item is None:
      return
    
    start_update_time = time.time()
    
    with pg.pdbutils.redirect_messages():
      preview_pixbuf, error = self._get_in_memory_preview(self.item.raw)
    
    if preview_pixbuf is not None:
      self._preview_image.set_from_pixbuf(preview_pixbuf)
    else:
      self.clear(use_item_name=True)
    
    self.queue_draw()
    
    self._is_updating = False
    
    update_duration_seconds = time.time() - start_update_time
    
    self.emit('preview-updated', error, update_duration_seconds)
  
  def _init_gui(self):
    self._button_menu = gtk.Button()
    self._button_menu.set_relief(gtk.RELIEF_NONE)
    self._button_menu.add(gtk.Arrow(gtk.ARROW_DOWN, gtk.SHADOW_IN))
    
    self._menu_item_update_automatically = gtk.CheckMenuItem(
      _('Update Preview Automatically'))
    self._menu_item_update_automatically.set_active(True)
    
    self._menu_settings = gtk.Menu()
    self._menu_settings.append(self._menu_item_update_automatically)
    self._menu_settings.show_all()
    
    self._button_refresh = gtk.Button()
    self._button_refresh.set_tooltip_text(_('Update Preview'))
    self._button_refresh.set_relief(gtk.RELIEF_NONE)
    self._button_refresh.add(gtk.image_new_from_pixbuf(
      self._button_refresh.render_icon(gtk.STOCK_REFRESH, gtk.ICON_SIZE_MENU)))
    self._button_refresh.show_all()
    self._button_refresh.hide()
    self._button_refresh.set_no_show_all(True)
    
    self._hbox_buttons = gtk.HBox()
    self._hbox_buttons.pack_start(self._button_menu, expand=False, fill=False)
    self._hbox_buttons.pack_start(self._button_refresh, expand=False, fill=False)
    
    self._preview_image = gtk.Image()
    self._preview_image.set_no_show_all(True)
    
    self._placeholder_image = gtk.Image()
    self._placeholder_image.set_from_stock(gtk.STOCK_DIALOG_QUESTION, gtk.ICON_SIZE_DIALOG)
    self._placeholder_image.set_no_show_all(True)
    
    self._folder_image = gtk.Image()
    self._folder_image.set_from_stock(gtk.STOCK_DIRECTORY, gtk.ICON_SIZE_DIALOG)
    self._folder_image.set_no_show_all(True)
    
    self._label_item_name = gtk.Label()
    self._label_item_name.set_ellipsize(pango.ELLIPSIZE_MIDDLE)
    
    self.set_spacing(self._WIDGET_SPACING)
    self.set_border_width(self._BORDER_WIDTH)
    
    self.pack_start(self._hbox_buttons, expand=False, fill=False)
    self.pack_start(self._preview_image, expand=True, fill=True)
    self.pack_start(self._placeholder_image, expand=True, fill=True)
    self.pack_start(self._folder_image, expand=True, fill=True)
    self.pack_start(self._label_item_name, expand=False, fill=False)
    
    self._placeholder_image_size = gtk.icon_size_lookup(
      self._placeholder_image.get_property('icon-size'))
    self._folder_image_size = gtk.icon_size_lookup(
      self._folder_image.get_property('icon-size'))
    
    self._current_placeholder_image = self._placeholder_image
    self._current_placeholder_image_size = self._placeholder_image_size
        
    self._show_placeholder_image()
  
  def _get_in_memory_preview(self, raw_item):
    self._preview_width, self._preview_height = self._get_preview_size(
      raw_item.width, raw_item.height)
    self._preview_scaling_factor = self._preview_width / raw_item.width
    
    image_preview, error = self._get_image_preview()
    
    if image_preview is None or not pdb.gimp_image_is_valid(image_preview):
      return None, error
    
    if not image_preview.layers:
      pg.pdbutils.try_delete_image(image_preview)
      return None, error
    
    if image_preview.base_type != gimpenums.RGB:
      pdb.gimp_image_convert_rgb(image_preview)
    
    raw_item_preview = image_preview.layers[0]
    
    if raw_item_preview.mask is not None:
      raw_item_preview.remove_mask(gimpenums.MASK_APPLY)
    
    # Recompute the size as the item may have been resized during processing.
    self._preview_width, self._preview_height = self._get_preview_size(
      raw_item_preview.width, raw_item_preview.height)
    
    self._preview_width, self._preview_height, preview_data = self._get_preview_data(
      raw_item_preview, self._preview_width, self._preview_height)
    
    raw_item_preview_pixbuf = self._get_preview_pixbuf(
      raw_item_preview, self._preview_width, self._preview_height, preview_data)
    
    pdb.gimp_image_delete(image_preview)
    
    return raw_item_preview_pixbuf, error
  
  def _get_image_preview(self):
    # The processing requires items in their original state as some procedures
    # might depend on their values, which would otherwise produce an image that
    # would not correspond to the real output. We therefore reset items.
    # Also, we need to restore the items' state once the processing is finished
    # so that proper names are displayed in the image preview - the same ones as
    # produced by the name preview, since we assume here that the image preview
    # is updated after the name preview.
    if self._batcher.item_tree is not None:
      for item in self._batcher.item_tree.iter_all():
        item.push_state()
        item.reset()
    
    only_selected_item_constraint_id = self._batcher.add_constraint(
      builtin_constraints.is_item_in_selected_items,
      groups=[actions.DEFAULT_CONSTRAINTS_GROUP],
      args=[[self.item.raw.ID]])
    
    error = None
    
    try:
      image_preview = self._batcher.run(
        keep_image_copy=True,
        item_tree=self._batcher.item_tree,
        is_preview=True,
        process_contents=True,
        process_names=False,
        process_export=False,
        **utils_.get_settings_for_batcher(self._settings['main']))
    except exceptions.BatcherCancelError as e:
      pass
    except exceptions.ActionError as e:
      messages_.display_failure_message(
        messages_.get_failing_action_message(e),
        failure_message=str(e),
        details=traceback.format_exc(),
        parent=pg.gui.get_toplevel_window(self))
      
      error = e
      image_preview = None
    except Exception as e:
      messages_.display_failure_message(
        _('There was a problem with updating the image preview:'),
        failure_message=str(e),
        details=traceback.format_exc(),
        parent=pg.gui.get_toplevel_window(self))
      
      error = e
      image_preview = None
    
    self._batcher.remove_action(
      only_selected_item_constraint_id, [actions.DEFAULT_CONSTRAINTS_GROUP])
    
    if self._batcher.item_tree is not None:
      for item in self._batcher.item_tree.iter_all():
        item.pop_state()
    
    return image_preview, error
  
  def _resize_image_for_batcher(self, batcher, *args, **kwargs):
    image = batcher.current_image
    
    pdb.gimp_image_resize(
      image,
      max(1, int(round(image.width * self._preview_scaling_factor))),
      max(1, int(round(image.height * self._preview_scaling_factor))),
      0,
      0)
    
    pdb.gimp_context_set_interpolation(gimpenums.INTERPOLATION_LINEAR)
  
  def _merge_items_for_batcher(self, batcher, item=None, raw_item=None):
    raw_item_merged = pdb.gimp_image_merge_visible_layers(
      batcher.current_image, gimpenums.EXPAND_AS_NECESSARY)
    
    batcher.current_image.active_layer = raw_item_merged
    batcher.current_raw_item = raw_item_merged
    
  def _scale_item_for_batcher(self, batcher, item=None, raw_item=None):
    if raw_item is None or not pdb.gimp_item_is_valid(raw_item):
      raw_item = batcher.current_raw_item
    
    pdb.gimp_item_transform_scale(
      raw_item,
      raw_item.offsets[0] * self._preview_scaling_factor,
      raw_item.offsets[1] * self._preview_scaling_factor,
      (raw_item.offsets[0] + raw_item.width) * self._preview_scaling_factor,
      (raw_item.offsets[1] + raw_item.height) * self._preview_scaling_factor)
  
  def _resize_item_for_batcher(self, batcher, item=None, raw_item=None):
    pdb.gimp_layer_resize_to_image_size(batcher.current_raw_item)
  
  def _get_preview_pixbuf(self, raw_item, preview_width, preview_height, preview_data):
    # The following code is largely based on the implementation of
    # `gimp_pixbuf_from_data` from:
    # https://github.com/GNOME/gimp/blob/gimp-2-8/libgimp/gimppixbuf.c
    raw_item_preview_pixbuf = gtk.gdk.pixbuf_new_from_data(
      preview_data,
      gtk.gdk.COLORSPACE_RGB,
      raw_item.has_alpha,
      8,
      preview_width,
      preview_height,
      preview_width * raw_item.bpp)
    
    self._preview_pixbuf = raw_item_preview_pixbuf
    
    if raw_item.has_alpha:
      raw_item_preview_pixbuf = self._add_alpha_background_to_pixbuf(
        raw_item_preview_pixbuf,
        raw_item.opacity,
        self.draw_checkboard_alpha_background,
        self._PREVIEW_ALPHA_CHECK_SIZE,
        self._preview_alpha_check_color_first,
        self._preview_alpha_check_color_second)
    
    return raw_item_preview_pixbuf
  
  def _get_preview_size(self, width, height):
    preview_widget_allocation = self._preview_image.get_allocation()
    preview_widget_width = preview_widget_allocation.width
    preview_widget_height = preview_widget_allocation.height
    
    if preview_widget_width > preview_widget_height:
      preview_height = min(preview_widget_height, height)
      preview_width = int(round((preview_height / height) * width))
      
      if preview_width > preview_widget_width:
        preview_width = preview_widget_width
        preview_height = int(round((preview_width / width) * height))
    else:
      preview_width = min(preview_widget_width, width)
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
      scaled_preview_width, scaled_preview_height, gtk.gdk.INTERP_BILINEAR)
    
    scaled_preview_pixbuf = self._add_alpha_background_to_pixbuf(
      scaled_preview_pixbuf,
      100,
      self.draw_checkboard_alpha_background,
      self._PREVIEW_ALPHA_CHECK_SIZE,
      self._preview_alpha_check_color_first,
      self._preview_alpha_check_color_second)
    
    self._preview_image.set_from_pixbuf(scaled_preview_pixbuf)
    self.queue_draw()
    
    self._previous_preview_pixbuf_width = scaled_preview_width
    self._previous_preview_pixbuf_height = scaled_preview_height
  
  def _on_size_allocate(self, preview, allocation):
    if not self._is_updating and not self._preview_image.get_mapped():
      preview_widget_allocated_width = allocation.width - self._BORDER_WIDTH
      preview_widget_allocated_height = (
        allocation.height
        - self._hbox_buttons.get_allocation().height
        - self._WIDGET_SPACING
        - self._label_item_name.get_allocation().height
        - self._WIDGET_SPACING
        - self._BORDER_WIDTH * 2)
      
      if (preview_widget_allocated_width < self._current_placeholder_image_size[0]
          or preview_widget_allocated_height < self._current_placeholder_image_size[1]):
        self._current_placeholder_image.hide()
      else:
        self._current_placeholder_image.show()
  
  def _on_preview_image_size_allocate(self, image, allocation):
    if not self._is_preview_image_allocated_size:
      self._set_contents()
      self._is_preview_image_allocated_size = True
  
  def _show_placeholder_image(self, use_item_name=False):
    self._current_placeholder_image = self._placeholder_image
    self._current_placeholder_image_size = self._placeholder_image_size
    
    self._placeholder_image.show()
    
    if not use_item_name:
      self._set_item_name_label(_('No selection'))
  
  def _show_folder_image(self):
    self._current_placeholder_image = self._folder_image
    self._current_placeholder_image_size = self._folder_image_size
    
    self._folder_image.show()
  
  def _set_item_name_label(self, item_name):
    self._label_item_name.set_markup(
      '<i>{}</i>'.format(gobject.markup_escape_text(pg.utils.safe_encode_gtk(item_name))))
  
  def _on_button_menu_clicked(self, button):
    pg.gui.menu_popup_below_widget(self._menu_settings, button)
  
  def _on_menu_item_update_automatically_toggled(self, menu_item):
    if self._menu_item_update_automatically.get_active():
      self._button_refresh.hide()
      self.lock_update(False, self._MANUAL_UPDATE_LOCK)
      self.update()
    else:
      self._button_refresh.show()
      self.lock_update(True, self._MANUAL_UPDATE_LOCK)
  
  def _on_button_refresh_clicked(self, button):
    if self._MANUAL_UPDATE_LOCK in self._lock_keys:
      self.lock_update(False, self._MANUAL_UPDATE_LOCK)
      self.update()
      self.lock_update(True, self._MANUAL_UPDATE_LOCK)
    else:
      self.update()
  
  @staticmethod
  def _add_alpha_background_to_pixbuf(
        pixbuf,
        opacity,
        use_checkboard_background=False,
        check_size=None,
        check_color_first=None,
        check_color_second=None):
    if use_checkboard_background:
      pixbuf_with_alpha_background = gtk.gdk.Pixbuf(
        gtk.gdk.COLORSPACE_RGB,
        False,
        8,
        pixbuf.get_width(),
        pixbuf.get_height())
      
      pixbuf.composite_color(
        pixbuf_with_alpha_background,
        0,
        0,
        pixbuf.get_width(),
        pixbuf.get_height(),
        0,
        0,
        1.0,
        1.0,
        gtk.gdk.INTERP_NEAREST,
        int(round((opacity / 100.0) * 255)),
        0,
        0,
        check_size,
        check_color_first,
        check_color_second)
    else:
      pixbuf_with_alpha_background = gtk.gdk.Pixbuf(
        gtk.gdk.COLORSPACE_RGB,
        True,
        8,
        pixbuf.get_width(),
        pixbuf.get_height())
      pixbuf_with_alpha_background.fill(0xffffff00)
      
      pixbuf.composite(
        pixbuf_with_alpha_background,
        0,
        0,
        pixbuf.get_width(),
        pixbuf.get_height(),
        0,
        0,
        1.0,
        1.0,
        gtk.gdk.INTERP_NEAREST,
        int(round((opacity / 100.0) * 255)))
    
    return pixbuf_with_alpha_background
  
  @staticmethod
  def _get_preview_data(raw_item, preview_width, preview_height):
    actual_preview_width, actual_preview_height, unused_, unused_, preview_data = (
      pdb.gimp_drawable_thumbnail(raw_item, preview_width, preview_height))
    
    return (
      actual_preview_width,
      actual_preview_height,
      array.array(b'B', preview_data).tostring())


gobject.type_register(ImagePreview)
