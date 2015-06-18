#-------------------------------------------------------------------------------
#
# This file is part of Export Layers.
#
# Copyright (C) 2013-2015 khalim19 <khalim19@gmail.com>
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
# along with Export Layers.  If not, see <http://www.gnu.org/licenses/>.
#
#-------------------------------------------------------------------------------

#===============================================================================

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division

str = unicode

#===============================================================================

import os

#===============================================================================


# This isn't a unit test, but rather a helper function to test the export to
# all file formats recognized by GIMP (+ GIMP DDS Plugin) at once.

def test_export_layers(layer_exporter, main_settings):
  file_extensions = [
    'data', 'xcf', 'pix', 'matte', 'mask', 'alpha', 'als', 'fli', 'flc',
    'xcf.bz2', 'xcfbz2', 'c', 'h', 'xhtml', 'dds', 'dcm', 'dicom', 'eps',
    'fit', 'fits', 'gif', 'gbr', 'gih', 'pat', 'xcf.gz', 'xcfgz',
    'html', 'htm', 'jpg', 'jpeg', 'jpe', 'cel', 'ico', 'mng', 'ora', 'pbm',
    'pgm', 'psd', 'png', 'pnm', 'pdf', 'ps', 'ppm', 'sgi', 'rgb', 'rgba',
    'bw', 'icon', 'im1', 'im8', 'im24', 'im32', 'rs', 'ras', 'tga', 'tif',
    'tiff', 'bmp', 'xbm', 'bitmap', 'xpm', 'xwd', 'pcx', 'pcc'
  ]
  
  orig_output_directory = main_settings['output_directory'].value
  
  for file_extension in file_extensions:
    main_settings['file_extension'].set_value(file_extension)
    main_settings['output_directory'].set_value(os.path.join(orig_output_directory, file_extension))
    layer_exporter.export_layers()
