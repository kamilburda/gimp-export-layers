# -*- coding: utf-8 -*-

"""Widget holding an array of GUI elements.

The widget is used as the default GUI for `setting.ArraySetting` instances.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import collections
import contextlib

import pygtk
pygtk.require('2.0')
import gtk
import gobject

from .. import utils as pgutils

from . import drag_and_drop_context as drag_and_drop_context_

__all__ = [
  'ItemBox',
  'ArrayBox',
  'ItemBoxItem',
]


class ItemBox(gtk.ScrolledWindow):
  """
  This base class defines a scrollable box holding a vertical list of items.
  Each item is an instance of `ItemBoxItem` class or one of its subclasses.
  """
  
  ITEM_SPACING = 4
  VBOX_SPACING = 4
  
  def __init__(self, item_spacing=ITEM_SPACING, *args, **kwargs):
    super().__init__(*args, **kwargs)
    
    self._item_spacing = item_spacing
    
    self._drag_and_drop_context = drag_and_drop_context_.DragAndDropContext()
    self._items = []
    
    self._vbox_items = gtk.VBox(homogeneous=False)
    self._vbox_items.set_spacing(self._item_spacing)
    
    self._vbox = gtk.VBox(homogeneous=False)
    self._vbox.set_spacing(self.VBOX_SPACING)
    self._vbox.pack_start(self._vbox_items, expand=False, fill=False)
    
    self.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    self.add_with_viewport(self._vbox)
    self.get_child().set_shadow_type(gtk.SHADOW_NONE)
  
  @property
  def items(self):
    return self._items
  
  def add_item(self, item):
    self._vbox_items.pack_start(item.widget, expand=False, fill=False)
    
    item.button_remove.connect('clicked', self._on_item_button_remove_clicked, item)
    item.widget.connect('key-press-event', self._on_item_widget_key_press_event, item)
    
    self._setup_drag(item)
    
    self._items.append(item)
    
    return item
  
  def reorder_item(self, item, position):
    new_position = min(max(position, 0), len(self._items) - 1)
    
    self._items.pop(self._get_item_position(item))
    self._items.insert(new_position, item)
    
    self._vbox_items.reorder_child(item.widget, new_position)
    
    return new_position
  
  def remove_item(self, item):
    item_position = self._get_item_position(item)
    if item_position < len(self._items) - 1:
      next_item_position = item_position + 1
      self._items[next_item_position].item_widget.grab_focus()
    
    self._vbox_items.remove(item.widget)
    item.remove_item_widget()
    
    self._items.remove(item)
  
  def clear(self):
    for unused_ in range(len(self._items)):
      self.remove_item(self._items[0])
  
  def _setup_drag(self, item):
    self._drag_and_drop_context.setup_drag(
      item.item_widget,
      self._get_drag_data,
      self._on_drag_data_received,
      [item],
      [item],
      self)
  
  def _get_drag_data(self, dragged_item):
    return str(self._items.index(dragged_item))
  
  def _on_drag_data_received(self, dragged_item_index_str, destination_item):
    dragged_item = self._items[int(dragged_item_index_str)]
    self.reorder_item(dragged_item, self._get_item_position(destination_item))
  
  def _on_item_widget_key_press_event(self, widget, event, item):
    if event.state & gtk.gdk.MOD1_MASK:     # Alt key
      key_name = gtk.gdk.keyval_name(event.keyval)
      if key_name in ['Up', 'KP_Up']:
        self.reorder_item(
          item, self._get_item_position(item) - 1)
      elif key_name in ['Down', 'KP_Down']:
        self.reorder_item(
          item, self._get_item_position(item) + 1)
  
  def _on_item_button_remove_clicked(self, button, item):
    self.remove_item(item)
  
  def _get_item_position(self, item):
    return self._items.index(item)


class ItemBoxItem(object):
  
  _HBOX_BUTTONS_SPACING = 3
  _HBOX_SPACING = 3
  
  def __init__(self, item_widget):
    self._item_widget = item_widget
    
    self._hbox = gtk.HBox(homogeneous=False)
    self._hbox.set_spacing(self._HBOX_SPACING)
    
    self._hbox_indicator_buttons = gtk.HBox(homogeneous=False)
    self._hbox_indicator_buttons.set_spacing(self._HBOX_BUTTONS_SPACING)
    
    self._event_box_indicator_buttons = gtk.EventBox()
    self._event_box_indicator_buttons.add(self._hbox_indicator_buttons)
    
    self._hbox_buttons = gtk.HBox(homogeneous=False)
    self._hbox_buttons.set_spacing(self._HBOX_BUTTONS_SPACING)
    
    self._event_box_buttons = gtk.EventBox()
    self._event_box_buttons.add(self._hbox_buttons)
    
    self._hbox.pack_start(self._event_box_indicator_buttons, expand=False, fill=False)
    self._hbox.pack_start(self._item_widget, expand=True, fill=True)
    self._hbox.pack_start(self._event_box_buttons, expand=False, fill=False)
    
    self._event_box = gtk.EventBox()
    self._event_box.add(self._hbox)
    
    self._has_hbox_buttons_focus = False
    
    self._button_remove = gtk.Button()
    self._setup_item_button(self._button_remove, gtk.STOCK_CLOSE)
    
    self._event_box.connect('enter-notify-event', self._on_event_box_enter_notify_event)
    self._event_box.connect('leave-notify-event', self._on_event_box_leave_notify_event)
    
    self._is_event_box_allocated_size = False
    self._buttons_allocation = None
    self._event_box.connect('size-allocate', self._on_event_box_size_allocate)
    self._event_box_buttons.connect('size-allocate', self._on_event_box_buttons_size_allocate)
    
    self._event_box.show_all()
    
    self._hbox_buttons.set_no_show_all(True)
    self._hbox_indicator_buttons.set_no_show_all(True)
  
  @property
  def widget(self):
    return self._event_box
  
  @property
  def item_widget(self):
    return self._item_widget
  
  @property
  def button_remove(self):
    return self._button_remove
  
  def remove_item_widget(self):
    self._hbox.remove(self._item_widget)
  
  def _setup_item_button(self, button, icon, position=None):
    self._setup_button(button, icon, position, self._hbox_buttons)
  
  def _setup_item_indicator_button(self, button, icon, position=None):
    self._setup_button(button, icon, position, self._hbox_indicator_buttons)
  
  def _setup_button(self, button, icon, position, hbox):
    button.set_relief(gtk.RELIEF_NONE)
    
    button_icon = gtk.image_new_from_pixbuf(button.render_icon(icon, gtk.ICON_SIZE_MENU))
    button.add(button_icon)
    
    hbox.pack_start(button, expand=False, fill=False)
    if position is not None:
      hbox.reorder_child(button, position)
    
    button.show_all()
  
  def _on_event_box_enter_notify_event(self, event_box, event):
    if event.detail != gtk.gdk.NOTIFY_INFERIOR:
      self._hbox_buttons.show()
  
  def _on_event_box_leave_notify_event(self, event_box, event):
    if event.detail != gtk.gdk.NOTIFY_INFERIOR:
      self._hbox_buttons.hide()
  
  def _on_event_box_size_allocate(self, event_box, allocation):
    if not self._is_event_box_allocated_size and self._buttons_allocation is not None:
      self._is_event_box_allocated_size = True
      
      # Assign enough height to the box to make sure it does not resize when showing buttons.
      if self._buttons_allocation.height >= allocation.height:
        self._hbox.set_property('height-request', allocation.height)
  
  def _on_event_box_buttons_size_allocate(self, event_box, allocation):
    # Checking for 1-pixel width and height prevents wrong size from being allocated
    # when parent widgets are resized.
    if self._buttons_allocation is None and allocation.width > 1 and allocation.height > 1:
      self._buttons_allocation = allocation
      
      # Make sure the width allocated to the buttons remains the same even if
      # buttons are hidden. This avoids a problem with unreachable buttons when
      # the horizontal scrollbar is displayed.
      self._event_box_buttons.set_property('width-request', self._buttons_allocation.width)
      
      self._hbox_buttons.hide()


class ArrayBox(ItemBox):
  """
  This class can be used to edit `setting.ArraySetting` instances interactively.
  
  Signals:
  
  * `'array-box-changed'` - An item was added, reordered or removed by the user.
  * `'array-box-item-changed'` - The contents of an item was modified by the
    user. Currently, this signal is not invoked in this widget and can only be
    invoked explicitly by calling `ArrayBox.emit('array-box-item-changed')`.
  """
  
  __gsignals__ = {
    b'array-box-changed': (gobject.SIGNAL_RUN_FIRST, None, ()),
    b'array-box-item-changed': (gobject.SIGNAL_RUN_FIRST, None, ())}
  
  _SIZE_HBOX_SPACING = 6
  
  def __init__(
        self,
        new_item_default_value,
        min_size=0,
        max_size=None,
        item_spacing=ItemBox.ITEM_SPACING,
        max_width=None,
        max_height=None,
        *args,
        **kwargs):
    """
    Parameters:
    
    * `new_item_default_value` - default value for new items.
    
    * `min_size` - minimum number of elements.
    
    * `max_size` - maximum number of elements. If `None`, the number of elements
      is unlimited.
    
    * `item_spacing` - vertical spacing in pixels between items.
    
    * `max_width` - maximum width of the array box before the horizontal
      scrollbar is displayed. The array box will resize automatically until the
      maximum width is reached. If `max_width` is `None`, the width is fixed
      to whatever width is provided by `gtk.ScrolledWindow`. If `max_width` is
      zero or negative, the width is unlimited.
    
    * `max_height` - maximum height of the array box before the vertical
      scrollbar is displayed. For more information, see `max_width`.
    """
    super().__init__(item_spacing=item_spacing, *args, **kwargs)
    
    self._new_item_default_value = new_item_default_value
    self._min_size = min_size if min_size >= 0 else 0
    
    if max_size is None:
      self._max_size = 2**32
    else:
      self._max_size = max_size if max_size >= min_size else min_size
    
    self.max_width = max_width
    self.max_height = max_height
    
    self.on_add_item = pgutils.empty_func
    self.on_reorder_item = pgutils.empty_func
    self.on_remove_item = pgutils.empty_func
    
    self._items_total_width = None
    self._items_total_height = None
    self._items_allocations = {}
    self._locker = _ActionLocker()
    
    self._init_gui()
  
  def _init_gui(self):
    self._size_spin_button = gtk.SpinButton(
      gtk.Adjustment(
        value=0,
        lower=self._min_size,
        upper=self._max_size,
        step_incr=1,
        page_incr=10,
      ),
      digits=0)
    
    self._size_spin_button.set_numeric(True)
    self._size_spin_button.set_value(0)
    
    self._size_spin_button_label = gtk.Label(_('Size'))
    
    self._size_hbox = gtk.HBox()
    self._size_hbox.set_spacing(self._SIZE_HBOX_SPACING)
    self._size_hbox.pack_start(self._size_spin_button_label, expand=False, fill=False)
    self._size_hbox.pack_start(self._size_spin_button, expand=False, fill=False)
    
    self._vbox.pack_start(self._size_hbox, expand=False, fill=False)
    self._vbox.reorder_child(self._size_hbox, 0)
    
    self._size_spin_button.connect(
      'value-changed', self._on_size_spin_button_value_changed)
  
  def add_item(self, item_value=None, index=None):
    if item_value is None:
      item_value = self._new_item_default_value
    
    item_widget = self.on_add_item(item_value, index)
    
    item = _ArrayBoxItem(item_widget)
    
    super().add_item(item)
    
    item.widget.connect('size-allocate', self._on_item_widget_size_allocate, item)
    
    if index is None:
      item.label.set_label(self._get_item_name(len(self._items)))
    
    if index is not None:
      with self._locker.lock_temp('emit_array_box_changed_on_reorder'):
        self.reorder_item(item, index)
    
    if self._locker.is_unlocked('update_spin_button'):
      with self._locker.lock_temp('emit_size_spin_button_value_changed'):
        self._size_spin_button.spin(gtk.SPIN_STEP_FORWARD, increment=1)
    
    return item
  
  def reorder_item(self, item, new_position):
    orig_position = self._get_item_position(item)
    processed_new_position = super().reorder_item(item, new_position)
    
    self.on_reorder_item(orig_position, processed_new_position)
    
    self._rename_item_names(min(orig_position, processed_new_position))
    
    if self._locker.is_unlocked('emit_array_box_changed_on_reorder'):
      self.emit('array-box-changed')
  
  def remove_item(self, item):
    if (self._locker.is_unlocked('prevent_removal_below_min_size')
        and len(self._items) == self._min_size):
      return
    
    if self._locker.is_unlocked('update_spin_button'):
      with self._locker.lock_temp('emit_size_spin_button_value_changed'):
        self._size_spin_button.spin(gtk.SPIN_STEP_BACKWARD, increment=1)
    
    item_position = self._get_item_position(item)
    
    super().remove_item(item)
    
    if item in self._items_allocations:
      self._update_height(-(self._items_allocations[item].height + self._item_spacing))
      del self._items_allocations[item]
    
    self.on_remove_item(item_position)
    
    self._rename_item_names(item_position)
  
  def set_values(self, values):
    self._locker.lock('emit_size_spin_button_value_changed')
    self._locker.lock('prevent_removal_below_min_size')
    
    orig_on_remove_item = self.on_remove_item
    self.on_remove_item = pgutils.empty_func
    
    self.clear()
    
    # This fixes an issue of items being allocated height of 1 when the array
    # size was previously 0.
    self.set_property('height-request', -1)
    
    for index, value in enumerate(values):
      self.add_item(value, index)
    
    self.on_remove_item = orig_on_remove_item
    
    self._size_spin_button.set_value(len(values))
    
    self._locker.unlock('prevent_removal_below_min_size')
    self._locker.unlock('emit_size_spin_button_value_changed')
  
  def _setup_drag(self, item):
    self._drag_and_drop_context.setup_drag(
      # Using the entire item allows dragging only by the label rather than the
      # widget itself. This avoids problems with widgets such as spin buttons
      # that do not behave correctly when reordering and also avoids accidental
      # clicking and modifying the widget by the user.
      item.widget,
      self._get_drag_data,
      self._on_drag_data_received,
      [item],
      [item],
      self)
  
  def _on_size_spin_button_value_changed(self, size_spin_button):
    if self._locker.is_unlocked('emit_size_spin_button_value_changed'):
      self._locker.lock('update_spin_button')
      
      new_size = size_spin_button.get_value_as_int()
      
      if new_size > len(self._items):
        num_elements_to_add = new_size - len(self._items)
        for unused_ in range(num_elements_to_add):
          self.add_item()
      elif new_size < len(self._items):
        num_elements_to_remove = len(self._items) - new_size
        for unused_ in range(num_elements_to_remove):
          self.remove_item(self._items[-1])
      
      self.emit('array-box-changed')
      
      self._locker.unlock('update_spin_button')
  
  def _on_item_button_remove_clicked(self, button, item):
    self._locker.lock('emit_size_spin_button_value_changed')
    
    should_emit_signal = (
      len(self._items) > self._min_size
      or self._locker.is_locked('prevent_removal_below_min_size'))
    
    super()._on_item_button_remove_clicked(button, item)
    
    if should_emit_signal:
      self.emit('array-box-changed')
    
    self._locker.unlock('emit_size_spin_button_value_changed')
  
  def _on_item_widget_size_allocate(self, item_widget, allocation, item):
    if item in self._items_allocations:
      self._update_width(allocation.width - self._items_allocations[item].width)
      self._update_height(allocation.height - self._items_allocations[item].height)
    else:
      self._update_width(allocation.width)
      self._update_height(allocation.height + self._item_spacing)
    
    self._items_allocations[item] = allocation
  
  def _update_width(self, width_diff):
    if self._items_total_width is None:
      self._items_total_width = self.get_allocation().width
    
    if width_diff != 0:
      self._update_dimension(
        width_diff,
        self._items_total_width,
        self.max_width,
        'width-request')
      
      self._items_total_width = self._items_total_width + width_diff
  
  def _update_height(self, height_diff):
    if self._items_total_height is None:
      self._items_total_height = self.get_allocation().height
    
    if height_diff != 0:
      self._update_dimension(
        height_diff,
        self._items_total_height,
        self.max_height,
        'height-request')
      
      self._items_total_height = self._items_total_height + height_diff
  
  def _update_dimension(
        self,
        size_diff,
        total_size,
        max_visible_size,
        dimension_request_property):
    if max_visible_size is None:
      is_max_visible_size_unlimited = True
    else:
      is_max_visible_size_unlimited = max_visible_size <= 0
    
    if not is_max_visible_size_unlimited:
      visible_size = min(total_size, max_visible_size)
    else:
      visible_size = total_size
    
    if (is_max_visible_size_unlimited
        or (visible_size + size_diff <= max_visible_size
            and total_size < max_visible_size)):
      new_size = visible_size + size_diff
    elif total_size >= max_visible_size and size_diff < 0:
      if total_size + size_diff < max_visible_size:
        new_size = total_size + size_diff
      else:
        new_size = max_visible_size
    else:
      new_size = max_visible_size
    
    if max_visible_size is not None:
      self.set_property(dimension_request_property, new_size)
  
  def _rename_item_names(self, start_index):
    for index, item in enumerate(self._items[start_index:]):
      item.label.set_label(self._get_item_name(index + 1 + start_index))
  
  @staticmethod
  def _get_item_name(index):
    return _('Element') + ' ' + str(index)


class _ArrayBoxItem(ItemBoxItem):
  
  def __init__(self, item_widget):
    super().__init__(item_widget)
    
    self._label = gtk.Label()
    self._label.show()
    
    self._hbox.pack_start(self._label, expand=False, fill=False)
    self._hbox.reorder_child(self._label, 0)
  
  @property
  def label(self):
    return self._label


class _ActionLocker(object):
  
  def __init__(self):
    self._tokens = collections.defaultdict(int)
  
  @contextlib.contextmanager
  def lock_temp(self, key):
    self.lock(key)
    try:
      yield
    finally:
      self.unlock(key)
  
  def lock(self, key):
    self._tokens[key] += 1
  
  def unlock(self, key):
    if self._tokens[key] > 0:
      self._tokens[key] -= 1
  
  def is_locked(self, key):
    return self._tokens[key] > 0
  
  def is_unlocked(self, key):
    return self._tokens[key] == 0


gobject.type_register(ArrayBox)
