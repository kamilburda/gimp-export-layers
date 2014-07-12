Export Layers
=============

Export Layers is a GIMP plug-in that exports layers as separate images in almost any file
format supported by GIMP and possibly third-party plug-ins.

Feature Summary
---------------

This plug-in:
* exports layers as separate images in almost any file format supported by GIMP
* uses native dialogs for file format export procedures to adjust file format settings
* uses layer names as filenames for the exported images
* supports layer groups and optionally treats them as directories
* can optionally export only layers whose file extension matches specified file format
* can use file extensions in layer names as file formats
* can use layers with names in [square brackets] as background layers

Requirements
------------

* GIMP 2.8 or later with Python-Fu installed

Installation
------------

From the package, extract the "export_layers.py" file and the "export_layers" directory
to "[home directory]/.gimp-2.8/plug-ins".

Usage
-----

From the main menu, go to "File -> Export Layers...". A dialog appears, allowing
you to specify output directory, file format and various other settings.

To specify file format, type the file extension in the File Format
text field (with or without the leading period). Any file format is supported,
with a few exceptions (more information in Known Issues). File formats provided
by third-party plug-ins should work as well - at the very least,
GIMP DDS Plugin was tested and works correctly.

To export in raw file format (which has no file extension assigned),
type "raw" into the text field. The file extension will remain in the files.

To export layers, press the "Export Layers" button. The main window is hidden
and a small dialog with progress is displayed. For the first layer,
a dialog corresponding to the file format appears, allowing you to adjust file
format settings. Not all file formats have settings, so no dialog may appear.

For subsequent layers, the file export procedure uses the values you
specified in the dialog for the first file. However, some file formats have to
display the dialog for each file (more info in Known Issues).

If you need to stop the export prematurely, press the Stop button. If an error was
encountered (such as invalid file format) or the export was stopped, the main window reappears.

If you want to export the layers with the last values used, you can use the
"File -> Export Layers to" menu entry. The file format dialog will not be displayed -
instead, the last used values will be used.

Settings
--------

**Treat layer groups as directories**

If enabled, layers will be exported to subdirectories corresponding to the layer groups.
If disabled, all layers will be exported to the output directory on the same level
and no subdirectories will be created.

**Ignore invisible layers**

If enabled, invisible layers will not be exported. Visible layers within
invisible layer groups will also not be exported.

**Autocrop layers**

If enabled, layers will be autocropped before being exported.

**Use image size instead of layer size**

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
* *Export only layers matching file format* - Export only layers with file extensions
that match the file format in the "File format" text field.
* *Use as file formats* - Every layer that has a valid file extension will be
exported with that file format. File format dialog will be displayed once
for each file format. For layers with invalid or no file extension,
the file format in the "File format" text field will be used.

**Additional options to "File extensions in layer names"**

- *Always strip file extension* - Strip (remove) file extension from all layer names.
This does not apply to layer names in [square brackets] if "Remove square brackets" is disabled.
- *Strip identical to file format* - Remove file extension from the layer names that
match the file format in the "File format" text field.
- *Never strip file extension* - Don't strip file extension from layer names.

**Layer names in [square brackets]**

* *Treat as normal layers* - Layer names starting with "[" and ending with "]"
will be exported as any other layer.
* *Treat as background layers* - These layers will be used as a background
for all other layers and will not be exported separately.
* *Ignore* - These layers will not be exported (and will not serve as background layers).
* *Ignore other layers* - All other layers will not be exported.

**Additional options to "Layer names in [square brackets]"**

- *Crop to background* - If enabled, layers will be cropped to the size of the
background layers instead of their own size.

**Merge layer groups**

If enabled, each top-level layer group is merged into one layer. The name
of each merged layer is the name of the corresponding top-level layer group.

**Create empty subdirectories**

If enabled, empty subdirectories from empty layers groups are created.

**Ignore layer modes**
Sets the layer mode for each layer to Normal. This is useful for layers with opacity
less than 100% and a layer mode different than Normal or Dissolve, which would
normally be completely invisible if a file format supporting alpha channel is used
(such as PNG).

Known Issues
------------

The following file formats are not working properly with this plug-in:
* colored XHTML (.xhtml) - does not save images at all,
* KISS CEL (.cel) - throws error/warning messages, but saves images anyway.

The following file formats have to display the file format dialog for each layer,
not just the first layer:
* raw (no file extension),
* FLI (.fli, .flc),
* C source (.c),
* HTML (.html, .htm).

In Export Layers To, JPG format always displays the file format dialog for the first layer.

File format dialog is displayed behind the small dialog while exporting.

Only ASCII letters, digits and certain special characters are allowed in filenames.
Other characters are deleted (from filenames only, they still remain in the layer names).

License
-------

This plug-in is licensed under the GNU GPLv3, which can be found on the following page:
http://www.gnu.org/licenses/gpl-3.0.html

Support, Contact
----------------

You can report issues on the following pages:
* http://registry.gimp.org/node/28268
* https://github.com/khalim19/gimp-plugin-export-layers

To ask questions, request new features or simply talk about the plug-in,
go to http://registry.gimp.org/node/28268.
