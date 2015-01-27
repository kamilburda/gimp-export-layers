#-------------------------------------------------------------------------------
#
# This file is part of pygimplib.
#
# Copyright (C) 2014 khalim19 <khalim19@gmail.com>
#
# pygimplib is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pygimplib is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pygimplib.  If not, see <http://www.gnu.org/licenses/>.
#
#-------------------------------------------------------------------------------

"""
This module:
* defines the means to load and save settings:
  * persistently - using a JSON file
  * "session-persistently" (settings persist during one GIMP session) - using the GIMP shelf
"""

#===============================================================================

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division

str = unicode

#===============================================================================

import abc

#===============================================================================

class SettingPresenter(object):
  
  """
  This class wraps a `Setting` object and a GUI element together.
  
  Various GUI elements have different attributes or methods to access their
  properties. This class wraps some of these attributes/methods so that they can
  be accessed with the same name.
  
  Setting presenters can wrap any attribute of a GUI element into their
  `get_value()` and `set_value()` methods. The value does not have to be a
  "direct" value, e.g. the checked state of a checkbox, but also e.g. the label
  of the checkbox.
  
  Attributes:
  
  * `setting (read-only)` - Setting object.
  
  * `element (read-only)` - GUI element object.
  
  * `value_changed_signal` - Object that indicates the type of event to assign
    to the GUI element that changes one of its properties.
  """
  
  __metaclass__ = abc.ABCMeta
  
  def __init__(self, setting, element):
    self._setting = setting
    # FIXME: This is only temporary until the redesign of settings is finished
    self._setting.gui = self
    
    self._element = element
    
    self.value_changed_signal = None
  
  @property
  def setting(self):
    return self._setting
  
  @property
  def element(self):
    return self._element
  
  @abc.abstractmethod
  def get_value(self):
    """
    Return the value of the GUI element.
    """
    
    pass
  
  @abc.abstractmethod
  def set_value(self, value):
    """
    Set the value of the GUI element.
    """
    
    pass
  
  @abc.abstractmethod
  def get_enabled(self):
    """
    Return the enabled/disabled state of the GUI element.
    """
    
    pass
  
  @abc.abstractmethod
  def set_enabled(self, enabled):
    """
    Set the enabled/disabled state of the GUI element.
    """
    
    pass
  
  @abc.abstractmethod
  def get_visible(self):
    """
    Return the visible/invisible state of the GUI element.
    """
    
    pass
  
  @abc.abstractmethod
  def set_visible(self, visible):
    """
    Set the visible/invisible state of the GUI element.
    """
    
    pass
  
  @abc.abstractmethod
  def connect_event(self, event_func, *event_args):
    """
    Assign the specified event handler to the GUI element that is meant to
    change the `value` attribute.
    
    The `value_changed_signal` attribute is used to assign the event handler to
    the GUI element.
    
    Parameters:
    
    * `event_func` - Event handler (function) to assign to the GUI element.
    
    * `*event_args` - Additional arguments to the event handler if needed.
    
    Raises:
    
    * `TypeError` - `value_changed_signal` is None.
    """
    
    pass
  
  @abc.abstractmethod
  def set_tooltip(self):
    """
    Set tooltip text for the GUI element.
    
    `Setting.description` attribute is used as the tooltip.
    """
    
    pass


#-------------------------------------------------------------------------------


class NullSettingPresenter(SettingPresenter):
  
  """
  This class acts as an empty `SettingPresenter` object whose methods do nothing.
  
  `NullSettingPresenter` is attached to `Setting` objects with no
  `SettingPresenter` object specified upon its instantiation.
  """
  
  def __init__(self, setting):
    super(NullSettingPresenter, self).__init__(setting, None)
  
  def get_value(self):
    pass
  
  def set_value(self, value):
    pass
  
  def get_enabled(self):
    pass
  
  def set_enabled(self, enabled):
    pass
  
  def get_visible(self):
    pass
  
  def set_visible(self, visible):
    pass
  
  def connect_event(self, event_func, *event_args):
    pass
  
  def set_tooltip(self):
    pass

