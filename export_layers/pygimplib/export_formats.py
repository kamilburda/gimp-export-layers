#-------------------------------------------------------------------------------
#
# This file is part of pygimplib.
#
# Copyright (C) 2014, 2015 khalim19 <khalim19@gmail.com>
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
This module contains a list of built-in and several third-party file export
formats supported by GIMP.

Each element of the list is a tuple:

  (file format description, file extensions, (optional) file save procedure)

The file export procedure can be used for multiple purposes, such as:
* checking that the corresponding file format plug-in is installed,
* using that export procedure instead of the default export procedure.

The default export procedure is `pdb.gimp_file_save`, which invokes the correct
file export procedure based on the file extension of the filename.
"""

#===============================================================================

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division

str = unicode

#===============================================================================

import gimp

#===============================================================================

pdb = gimp.pdb

#===============================================================================


class _ExportFormat(object):
  
  def __init__(self, description, file_extensions, file_export_procedure_name=None,
               file_export_procedure_func=None, file_export_procedure_func_args=None):
    
    def _export_image_default(run_mode, image, layer, filename, raw_filename):
      pdb.gimp_file_save(image, layer, filename, raw_filename, run_mode=run_mode)
    
    self.description = description
    self.file_extensions = file_extensions
    self.file_export_procedure_name = file_export_procedure_name
    
    if file_export_procedure_func is not None:
      self.file_export_procedure_func = file_export_procedure_func
    else:
      self.file_export_procedure_func = _export_image_default
    
    if file_export_procedure_func_args is not None:
      self.file_export_procedure_func_args = file_export_procedure_func_args
    else:
      self.file_export_procedure_func_args = []


def _create_export_formats(export_formats_params):
  return [_ExportFormat(*params) for params in export_formats_params]


def _create_export_formats_dict(export_formats):
  export_formats_dict = {}
  
  for export_format in export_formats:
    for file_extension in export_format.file_extensions:
      # If the same extension appears in multiple formats, only the first format
      # will be accessed by the extension. 
      if file_extension not in export_formats_dict:
        export_formats_dict[file_extension] = export_format
  
  return export_formats_dict


#===============================================================================


export_formats = _create_export_formats([
  ("Alias Pix image", ["pix", "matte", "mask", "alpha", "als"]),
  ("ASCII art", ["txt", "ansi", "text"], "file-aa-save"),
  ("AutoDesk FLIC animation", ["fli", "flc"]),
  ("bzip archive", ["xcf.bz2", "xcfbz2"]),
  ("Colored XHTML", ["xhtml"]),
  ("C source code", ["c"]),
  ("C source code header", ["h"]),
  ("Digital Imaging and Communications in Medicine image", ["dcm", "dicom"]),
  # Plug-in can be found at: https://code.google.com/p/gimp-dds/
  ("DDS image", ["dds"], "file-dds-save"),
  ("Encapsulated PostScript image", ["eps"]),
  ("Flexible Image Transport System", ["fit", "fits"]),
  ("GIF image", ["gif"]),
  ("GIMP brush", ["gbr"]),
  ("GIMP brush (animated)", ["gih"]),
  ("GIMP pattern", ["pat"]),
  ("GIMP XCF image", ["xcf"]),
  ("gzip archive", ["xcf.gz", "xcfgz"]),
  ("HTML table", ["html", "htm"]),
  ("JPEG image", ["jpg", "jpeg", "jpe"]),
  # Plug-in can be found at: http://registry.gimp.org/node/25508
  ("JPEG XR image", ["jxr"], "file-jxr-save"),
  ("KISS CEL", ["cel"]),
  ("Microsoft Windows icon", ["ico"]),
  ("MNG animation", ["mng"]),
  ("OpenRaster", ["ora"]),
  ("PBM image", ["pbm"]),
  ("PGM image", ["pgm"]),
  ("Photoshop image", ["psd"]),
  ("PNG image", ["png"]),
  # Plug-in can be found at: http://registry.gimp.org/node/24394
  ("APNG image", ["apng"], "file-apng-save-defaults",
   lambda run_mode, *args: pdb.file_apng_save_defaults(*args, run_mode=run_mode)),
  ("PNM image", ["pnm"]),
  ("Portable Document Format", ["pdf"]),
  ("PostScript document", ["ps"]),
  ("PPM image", ["ppm"]),
  ("Raw image data", ["raw", "data"], None,
   lambda run_mode, *args: pdb.file_raw_save(*args, run_mode=run_mode)),
  ("Silicon Graphics IRIS image", ["sgi", "rgb", "rgba", "bw", "icon"]),
  ("SUN Rasterfile image", ["im1", "im8", "im24", "im32", "rs", "ras"]),
  ("TarGA image", ["tga"]),
  ("TIFF image", ["tif", "tiff"]),
  # Plug-in can be found at: http://registry.gimp.org/node/24882
  ("Valve Texture Format", ["vtf"], "file-vtf-save"),
  # Plug-in can be found at: http://registry.gimp.org/node/25874
  ("WebP image", ["webp"], "file-webp-save"),
  ("Windows BMP image", ["bmp"]),
  ("X11 Mouse Cursor", ["xmc"], "file-xmc-save"),
  ("X BitMap image", ["xbm", "bitmap"]),
  ("X PixMap image", ["xpm"]),
  ("X window dump", ["xwd"]),
  ("ZSoft PCX image", ["pcx", "pcc"]),
])


export_formats_dict = _create_export_formats_dict(export_formats)

