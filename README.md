Export Layers
========================

Export Layers is a GIMP plug-in that exports layers as separate images in almost any file
format supported by GIMP and possibly third-party plug-ins.


Feature Summary
------------------------

This plug-in:
* exports layers as separate images in almost any file format supported by GIMP
* uses native dialogs for file format export procedures to adjust file format settings
* uses layer names as filenames for the exported images
* supports layer groups and optionally treats them as directories
* can optionally export only layers whose file extension matches specified file extension
* can use file extensions in layer names as file formats
* can use layers with names in [square brackets] as background layers


Requirements
------------------------

* GIMP 2.8 or later with Python-Fu installed


Installation
------------------------

From the package, extract the "export_layers.py" file and the "export_layers" directory
to "[home directory]/.gimp-2.8/plug-ins".

On Linux, if necessary, enable the executable flag on the "export_layers.py" file,
e.g. from the terminal:

    chmod u+x "export_layers.py"

It should no longer be needed for versions 2.1 and above.


Usage
------------------------

From the main menu, go to "File -> Export Layers...". A dialog appears, allowing
you to specify output directory, file extension and various other settings.

Type in the desired file extension in the "File extension" text field (with or without
the leading period). You can type any file extension supported by GIMP. File formats
provided by third-party plug-ins should work as well - at the very least,
GIMP DDS Plugin was tested and works correctly.

To export in raw file format, type "raw" into the text field. The file extension
will remain in the files.

To export layers, press the "Export Layers" button. For the first layer,
a dialog corresponding to the file format appears, allowing you to adjust file
format settings. Some file formats don't have dialogs.

For subsequent layers, the same settings that you specified in the file format
dialog are applied. However, some file formats have to display the dialog
for each file (more info in Known Issues).

If you need to stop the export prematurely, press the Stop button. If an error was
encountered (such as invalid file extension) or the export was stopped, the main
dialog remains open.

If you want to export the layers with the last values used, you can use the
"File -> Export Layers to" menu entry. The file format dialog will not be displayed -
instead, the last used values will be used.


Settings
------------------------

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
------------------------

**File extensions in layer names**

* *No special handling* - No special action is performed.
* *Export only layers matching file extension* - Export only layers whose file
extensions match the "File extension" text field.
* *Use as file extensions* - Every layer that has a valid file extension will be
exported using that file extension. File format dialog will be displayed once
for each file extension. For layers with invalid or no file extension,
the extension in the "File extension" text field will be used.

**Additional options to "File extensions in layer names"**

- *Always strip file extension* - Strip (remove) file extension from all layer names.
- *Strip identical file extension* - Remove file extension from the layer names that
match the "File extension" text field.
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

If enabled, the layer mode for each layer is set to Normal. This is useful for layers
with opacity less than 100% and a layer mode different than Normal or Dissolve, which
would normally be completely invisible if a file format supporting alpha channel
is used (such as PNG).


Known Issues
------------------------

On Windows, the file format dialog is displayed behind the main dialog.

The following file formats are not working properly with this plug-in:
* colored XHTML (.xhtml) - does not save images at all,
* KISS CEL (.cel) - throws error/warning messages, but saves images anyway.

The following file formats have to display the file format dialog for each layer,
not just the first layer:
* raw,
* FLI (.fli, .flc),
* C source (.c),
* HTML (.html, .htm).

On Windows, the following file formats don't work properly if file paths contain Unicode characters:
* DDS (.dds),
* OpenRaster (.ora),
* X PixMap Image (.xpm).

In Export Layers To, JPG format always displays the file format dialog for the first layer.


License
------------------------

This plug-in is licensed under the GNU GPLv3, which can be found on the following page:
http://www.gnu.org/licenses/gpl-3.0.html


Support, Contact
------------------------

You can report issues on the following pages:
* http://registry.gimp.org/node/28268
* https://github.com/khalim19/gimp-plugin-export-layers

To ask questions, request new features or simply talk about the plug-in,
go to http://registry.gimp.org/node/28268.


Translations
------------------------

If you want to provide translation(s) for the plug-in, I recommend using
a translation tool such as Poedit (http://poedit.net) for easier usage.

The following step apply if you want to use Poedit:

1. Go to https://github.com/khalim19/gimp-plugin-export-layers/tree/master/resources
   and download the .pot file with the appropriate version (e.g. for version 2.2,
   it's "export_layers-2.2.pot").
2. Open Poedit, select "File -> New from POT/PO file..." and find the .pot file
   for the plug-in.
3. Set the language of the translation.
4. Translate the strings (by filling in the "Translation" text field for each string).
5. If desired, go to "Catalog -> Properties..." and edit the translation file
   properties. If you don't do this, warning messages may pop up when saving,
   but they should be harmless.
6. When done, save the .po file. An .mo file is generated automatically (in the
   same directory as the .po file).
7. Move and rename the .mo file to
   
    [user directory]/.gimp-2.8/plug-ins/export_layers/locale/[language code]/LC_MESSAGES/export_layers.mo
   
   where [language code] is the language code in which you translated the plug-in.
   [language code] is a part of the .po file - e.g. for a file named "fr_FR.po",
   the language code is "fr_FR".

If you don't want to use Poedit, the following steps apply:

1. Make sure that "msginit" and "msgfmt" commands are installed on your system.
2. Go to https://github.com/khalim19/gimp-plugin-export-layers/tree/master/resources
   and download the .pot file with the appropriate version (e.g. for version 2.2,
   it's "export_layers-2.2.pot").
3. Open up terminal and run
   
    msginit --input=[path to .pot file] --locale=[language code]
   
   where [path to .pot file] is the .pot file you downloaded and [language code]
   is a two-letter code representing a language.
   A .po file is generated in the same directory as the current working directory.
   
   If in doubt, you can consult the list of available language codes on the following page:
   https://www.gnu.org/software/gettext/manual/html_node/Usual-Language-Codes.html
4. Open up the .po file and translate each string in the "msgid" field to string
   in the corresponding "msgstr" field.
5. When done translating, generate the .mo file:

    msgfmt [path to .po file] --output-file=[path to .mo file]

6. Move and rename the .mo file to
   
    [user directory]/.gimp-2.8/plug-ins/export_layers/locale/[language code]/LC_MESSAGES/export_layers.mo
   

To test your translation, run GIMP from the terminal as follows:
    
    export LANG=[language].UTF-8
    gimp
