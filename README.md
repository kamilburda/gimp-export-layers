Export Layers
=============

This GIMP plug-in exports layers as separate images in any file format supported
by GIMP and third-party plug-ins.

Features:
* uses native dialogs for file formats to adjust export settings
* uses layer names as filenames for the exported images
* can treat layer groups as folders
* can use layers with names in [square brackets] as background layers
* can optionally export only layers whose file extension matches the specified file extension
* can use file extensions in layer names as file formats


Requirements
------------

* GIMP 2.8 or later
* Python 2.7 or later from the 2.7.x series


Installation
------------

**Windows**

Make sure you installed GIMP with support for Python scripting.

Copy the `export_layers.py` file and the `export_layers` folder to
`[your home folder]\.gimp-2.8\plug-ins`.


**Linux**

Copy the `export_layers.py` file and the `export_layers` folder to
`[your home folder]/.gimp-2.8/plug-ins`.

If necessary, make the `export_layers.py` file executable, e.g. from the terminal:

    chmod +x "export_layers.py"


**OS X**

Copy the `export_layers.py` file and the `export_layers` folder to
`[your home folder]/Library/Application Support/GIMP/2.8/plug-ins`.

If necessary, make the `export_layers.py` file executable, e.g. from the terminal:

    chmod +x "export_layers.py"

GIMP for OS X may have Python 2.6 bundled, which will not work with this plug-in,
since Python 2.7 is required.

To check if the correct version of Python is installed, start GIMP and go to
Filters -> Python-Fu -> Console. The console must display "Python 2.7" or later
from the 2.7.x series. If not, install Python 2.7, open
`/Applications/Gimp.app/Contents/Resources/lib/gimp/2.0/interpreters/pygimp.interp`
and change its contents to the following:

    python=/usr/bin/python
    /usr/bin/python=/usr/bin/python
    :Python:E::py::python:


Usage
-----

From the main menu, select "File -> Export Layers...". A dialog appears, allowing
you to specify output folder, file extension and various other settings.

Type or choose your desired file extension in the "File extension" text field.
You can still enter a file extension not in the dropdown list in case you use a
file format plug-in not recognized by this plug-in.

To export layers, press the "Export Layers" button. A dialog corresponding to
the file format appears, allowing you to adjust export settings. Some file
formats don't have dialogs, while some of them display the dialog for each layer
(listed in section Known Issues).

To export layers with the last settings used, you may want to choose
"File -> Export Layers (repeat)".


Settings
--------

**Treat layer groups as folders**

If enabled, layers will be exported to subfolders corresponding to the layer groups.
If disabled, all layers will be exported to the output folder on the same level
and no subfolders will be created.

**Ignore invisible layers**

If enabled, invisible layers will not be exported. Visible layers within
invisible layer groups will also not be exported.

**Autocrop layers**

If enabled, layers will be autocropped before being exported.

**Use image size**

If enabled, layers will be resized (but not scaled) to the image size. This is
useful if you want to keep the size of the image canvas and the layer position
within the image. If layers are partially outside the image canvas,
they will be cut off. If you want to export the entire layer,
leave this setting disabled.

**Save Settings**

Current settings in the Export Layers window are permanently saved to a file.
If you re-open GIMP, the saved settings will be loaded from the file when
Export Layers is first opened.

**Reset Settings**

Settings will be reset to their default values.


Advanced Settings
-----------------

**File extensions in layer names**

* *No special handling* - No special action is performed.
* *Export only layers matching file extension* - Export only layers whose file
extensions match the "File extension" text field.
* *Use as file extensions* - Every layer that has a valid file extension will be
exported using that file extension. File format dialog will be displayed once
for each file extension. For layers with invalid or no file extension,
the extension in the "File extension" text field will be used.

**Additional options to "File extensions in layer names"**

* *Always strip file extension* - Strip (remove) file extension from all layer names.
* *Strip identical file extension* - Remove file extension from the layer names that
match the "File extension" text field.
* *Never strip file extension* - Don't strip file extension from layer names.

**Layer names in [square brackets]**

* *Treat as normal layers* - Layer names starting with "[" and ending with "]"
will be exported as any other layer.
* *Treat as background layers* - These layers will be used as a background
for all other layers and will not be exported separately.
* *Ignore* - These layers will not be exported (and will not serve as background layers).
* *Ignore other layers* - All other layers will not be exported.

**Additional options to "Layer names in [square brackets]"**

* *Crop to background* - If enabled, layers will be cropped to the size of the
background layers instead of their own size.

**Merge layer groups**

If enabled, each top-level layer group is merged into one layer. The name
of each merged layer is the name of the corresponding top-level layer group.

**Create empty subfolders**

If enabled, empty subfolders from empty layers groups are created.

**Ignore layer modes**

If enabled, the layer mode for each layer is set to Normal. This is useful for layers
with opacity less than 100% and a layer mode different than Normal or Dissolve, which
would normally be completely invisible if a file format supporting alpha channel
is used (such as PNG).


Known Issues
------------

Several users reported crashes on Windows and OS X when clicking on the menu
entries or when clicking on the "Advanced Settings" widget. If the crashes
occur to you, try reinstalling GIMP.

On Windows, the file format dialog may be displayed behind the main dialog.

The following file formats are not working properly with this plug-in:
* colored XHTML (.xhtml) - does not save images at all,
* KISS CEL (.cel) - throws error/warning messages, but saves images anyway.

The following file formats have to display the file format dialog for each layer,
not just the first layer:
* RAW,
* FLI (.fli, .flc),
* C source (.c),
* HTML (.html, .htm).

On Windows, the following file formats don't work properly if file paths contain Unicode characters:
* DDS (.dds),
* OpenRaster (.ora),
* X PixMap Image (.xpm).

In "Export Layers (repeat)", JPEG format displays the file format dialog for the first layer.


License
-------

This plug-in is licensed under the [GNU GPLv3](http://www.gnu.org/licenses/gpl-3.0.html).


Translations
------------

If you want to provide translations for the plug-in, see the `Readme for Translators.md`
file in the `export_layers/locale` folder in the package.


Support, Contact
----------------

You can report issues, ask questions or request new features on the [GitHub page](https://github.com/khalim19/gimp-plugin-export-layers/issues) or on the [GIMP Plugin Registry page](http://registry.gimp.org/node/28268).

You can also contact me via email: khalim19 AT gmail DOT com
