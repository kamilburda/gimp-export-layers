# -*- coding: utf-8 -*-

"""List of built-in and several third-party file formats supported by GIMP.

Each element of the list is a tuple:

  (file format description, file extensions, (optional) file save procedure)

The file save procedure can be used for multiple purposes, such as:
* checking that the corresponding file format plug-in is installed,
* using that save procedure instead of the default save procedure
  (`pdb.gimp_file_save()`, which invokes the correct file save procedure based
  on the file extension of the filename).
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import gimp
from gimp import pdb


def get_default_save_procedure():
  return _save_image_default


def get_save_procedure(file_extension):
  """
  Return the file save procedure for the given file extension. If the file
  extension is invalid or does not have a specific save procedure defined,
  return the default save procedure (as returned by
  `get_default_save_procedure()`).
  """
  if file_extension in file_formats_dict:
    file_format = file_formats_dict[file_extension]
    if file_format.save_procedure_func and file_format.is_installed():
      return file_format.save_procedure_func
  
  return get_default_save_procedure()


def _save_image_default(run_mode, image, layer, filepath, raw_filepath):
  pdb.gimp_file_save(image, layer, filepath, raw_filepath, run_mode=run_mode)


def _create_file_formats(file_formats_params):
  return [_FileFormat(**params) for params in file_formats_params]


def _create_file_formats_dict(file_formats):
  file_formats_dict = {}
  
  for file_format in file_formats:
    for file_extension in file_format.file_extensions:
      if file_extension not in file_formats_dict and file_format.version_check_func():
        file_formats_dict[file_extension] = file_format
  
  return file_formats_dict


class _FileFormat(object):
  
  def __init__(
        self, description, file_extensions, save_procedure_name=None,
        save_procedure_func=None, save_procedure_func_args=None, versions=None,
        **kwargs):
    self.description = description
    self.file_extensions = file_extensions
    
    self.save_procedure_name = save_procedure_name
    
    if save_procedure_func is not None:
      self.save_procedure_func = save_procedure_func
    else:
      self.save_procedure_func = get_default_save_procedure()
    
    if save_procedure_func_args is not None:
      self.save_procedure_func_args = save_procedure_func_args
    else:
      self.save_procedure_func_args = []
    
    self.version_check_func = versions if versions is not None else lambda: True
    
    for name, value in kwargs.items():
      setattr(self, name, value)
  
  def is_builtin(self):
    return not self.save_procedure_name
  
  def is_third_party(self):
    return bool(self.save_procedure_name)
  
  def is_installed(self):
    return (
      self.is_builtin()
      or (self.is_third_party()
          and pdb.gimp_procedural_db_proc_exists(self.save_procedure_name)))


file_formats = _create_file_formats([
  {'description': 'Alias Pix image',
   'file_extensions': ['pix', 'matte', 'mask', 'alpha', 'als']},
  {'description': 'ASCII art',
   'file_extensions': ['txt', 'ansi', 'text'],
   'save_procedure_name': 'file-aa-save',
   'versions': lambda: gimp.version < (2, 9)},
  {'description': 'AutoDesk FLIC animation',
   'file_extensions': ['fli', 'flc']},
  {'description': 'AVIF',
   'file_extensions': ['avif'],
   'versions': lambda: gimp.version >= (2, 10, 22)},
  {'description': 'bzip archive',
   'file_extensions': ['xcf.bz2', 'xcfbz2']},
  {'description': 'C source code',
   'file_extensions': ['c']},
  {'description': 'C source code header',
   'file_extensions': ['h']},
  {'description': 'Colored XHTML',
   'file_extensions': ['xhtml']},
  {'description': 'DDS image',
   'file_extensions': ['dds']},
  {'description': 'DICOM image',
   'file_extensions': ['dcm', 'dicom']},
  {'description': 'Encapsulated PostScript image',
   'file_extensions': ['eps']},
  {'description': 'Flexible Image Transport System',
   'file_extensions': ['fit', 'fits']},
  {'description': 'GIF image',
   'file_extensions': ['gif']},
  {'description': 'GIMP brush',
   'file_extensions': ['gbr']},
  {'description': 'GIMP brush (animated)',
   'file_extensions': ['gih']},
  {'description': 'GIMP pattern',
   'file_extensions': ['pat']},
  {'description': 'GIMP XCF image',
   'file_extensions': ['xcf']},
  {'description': 'gzip archive',
   'file_extensions': ['xcf.gz', 'xcfgz']},
  {'description': 'HEIF/HEIC',
   'file_extensions': ['heic', 'heif'],
   'versions': lambda: gimp.version >= (2, 10, 2)},
  {'description': 'HTML table',
   'file_extensions': ['html', 'htm']},
  {'description': 'JPEG image',
   'file_extensions': ['jpg', 'jpeg', 'jpe']},
  {'description': 'JPEG XL image',
   'file_extensions': ['jxl'],
   'url': 'https://github.com/libjxl/libjxl',
   'versions': lambda: gimp.version >= (2, 10, 32)},
  {'description': 'JPEG XR image',
   'file_extensions': ['jxr'],
   'save_procedure_name': 'file-jxr-save',
   'url': 'https://github.com/chausner/gimp-jxr'},
  {'description': 'JSON metadata',
   'file_extensions': ['json'],
   'save_procedure_func': (
     lambda run_mode, *args: pdb.file_metadata_json_save(*args, run_mode=run_mode)),
   'versions': lambda: gimp.version >= (2, 10),
   'url': 'https://github.com/kamilburda/gimp-metadata-export'},
  {'description': 'KISS CEL',
   'file_extensions': ['cel']},
  {'description': 'Microsoft Windows icon',
   'file_extensions': ['ico']},
  {'description': 'MNG animation',
   'file_extensions': ['mng']},
  {'description': 'OpenRaster',
   'file_extensions': ['ora']},
  {'description': 'OpenEXR image',
   'file_extensions': ['exr'],
   'versions': lambda: gimp.version >= (2, 10)},
  {'description': 'PBM image',
   'file_extensions': ['pbm']},
  {'description': 'PFM image',
   'file_extensions': ['pfm'],
   'versions': lambda: gimp.version >= (2, 10)},
  {'description': 'PGM image',
   'file_extensions': ['pgm']},
  {'description': 'Photoshop image',
   'file_extensions': ['psd']},
  {'description': 'PNG image',
   'file_extensions': ['png']},
  {'description': 'APNG image',
   'file_extensions': ['apng'],
   'save_procedure_name': 'file-apng-save-defaults',
   'save_procedure_func': (
     lambda run_mode, *args: pdb.file_apng_save_defaults(*args, run_mode=run_mode)),
   'url': 'https://sourceforge.net/projects/gimp-apng/'},
  {'description': 'PNM image',
   'file_extensions': ['pnm']},
  {'description': 'Portable Document Format',
   'file_extensions': ['pdf']},
  {'description': 'PostScript document',
   'file_extensions': ['ps']},
  {'description': 'PPM image',
   'file_extensions': ['ppm']},
  {'description': 'Radiance RGBE',
   'file_extensions': ['hdr'],
   'versions': lambda: gimp.version >= (2, 10)},
  {'description': 'Raw image data',
   'file_extensions': ['data', 'raw'],
   'save_procedure_func': (
     lambda run_mode, *args: pdb.file_raw_save(*args, run_mode=run_mode))},
  {'description': 'Silicon Graphics IRIS image',
   'file_extensions': ['sgi', 'rgb', 'rgba', 'bw', 'icon']},
  {'description': 'SUN Rasterfile image',
   'file_extensions': ['im1', 'im8', 'im24', 'im32', 'rs', 'ras']},
  {'description': 'TarGA image',
   'file_extensions': ['tga']},
  {'description': 'TIFF image',
   'file_extensions': ['tif', 'tiff']},
  {'description': 'Valve Texture Format',
   'file_extensions': ['vtf'],
   'save_procedure_name': 'file-vtf-save',
   'url': 'https://github.com/Artfunkel/gimp-vtf'},
  {'description': 'WebP image',
   'file_extensions': ['webp']},
  {'description': 'Windows BMP image',
   'file_extensions': ['bmp']},
  {'description': 'X11 Mouse Cursor',
   'save_procedure_name': 'file-xmc-save',
   'file_extensions': ['xmc'],
   'versions': lambda: gimp.version < (2, 9)},
  {'description': 'X BitMap image',
   'file_extensions': ['xbm', 'bitmap']},
  {'description': 'X PixMap image',
   'file_extensions': ['xpm']},
  {'description': 'X window dump',
   'file_extensions': ['xwd']},
  {'description': 'XML metadata',
   'file_extensions': ['xml'],
   'save_procedure_func': (
     lambda run_mode, *args: pdb.file_metadata_xml_save(*args, run_mode=run_mode)),
   'versions': lambda: gimp.version >= (2, 10),
   'url': 'https://github.com/kamilburda/gimp-metadata-export'},
  {'description': 'xz archive',
   'file_extensions': ['xcf.xz', 'xcfxz'],
   'versions': lambda: gimp.version >= (2, 10)},
  {'description': 'YAML metadata',
   'file_extensions': ['yaml'],
   'save_procedure_func': (
     lambda run_mode, *args: pdb.file_metadata_yaml_save(*args, run_mode=run_mode)),
   'versions': lambda: gimp.version >= (2, 10),
   'url': 'https://github.com/kamilburda/gimp-metadata-export'},
  {'description': 'ZSoft PCX image',
   'file_extensions': ['pcx', 'pcc']},
])

file_formats_dict = _create_file_formats_dict(file_formats)
