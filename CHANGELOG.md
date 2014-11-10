2.2.1 (November 10, 2014)
------------------------

* Images in RAW format are saved with '.data' file extension instead of '.raw'.
* Image type is now preserved, instead of always using the RGB type.
  E.g. if the image is indexed, the exported layers will be indexed as well.
  File formats that don't support the an image type (such as indexed) will
  automatically convert the type as appropriate (the same way the Export menu does).
* Renamed "Use image size instead of layer size" to just "Use image size" for the sake of brevity.

2.2 (August 15, 2014)
------------------------

* Changed how the initial output directory in the GUI is determined. It is now
  remembered separately for each image currently opened in GIMP.
* Added support for plug-in internationalization and localization. It is now
  possible to create translations of the plug-in (see the
  "Readme for Translators.txt" file in the package).
* Allowed again the following special characters in filenames: ~!@`#$%&=+{}[]
  
  They can appear even on Windows (which seems to be the most restrictive
  of the popular OSs as far as invalid characters go). The exceptions are '[' at
  the beginning and ']' at the end of the layer names, which are still removed,
  since they have a special meaning in the plug-in.
* When "No special handling" is selected, file extension strip mode will no
  longer default to "Strip identical file extension" (because the setting was
  always overwritten by its default value and thus did not remember the last
  used value).
* Misc. code refactoring and cleanup.

2.1 (July 27, 2014)
------------------------

* Added support for Unicode characters. This means you can now use any character
  in layer names and the output directory, except for most of the special characters.
* Export Layers GUI: Removed the small dialog. The progress bar and the Stop button
  are now displayed directly in the main dialog.
* Renamed "File format" to "File extension" since that's what the user actually
  specifies. Also, renamed a bunch of options so that they contain "extension"
  instead of "format". Because of this, if you use "Save settings", you'll need to
  re-save them.
* Removed "Remove squared brackets" setting as it served little purpose.
  [square brackets] will now always be removed from layer names.
* Added "Ignore layer mode" setting, which sets the layer mode to Normal for each layer.
* When "No special handling" is selected, file extension strip mode now defaults to
  "Strip identical file extension".
* More special characters are now removed from layer names.
* Removed unnecessary files from the package.
* Fixed a bug that caused the file format dialog to not appear if the user chose
  Skip in the overwrite dialog for the first file (or the first and subsequent files).
* Fixed filenames and directory names not being made unique properly, hopefully
  for real this time.
* More code refactoring and cleanup.

2.0 (June 27, 2014)
------------------------

Implemented advanced settings, including the following:
* export only layers whose names match the file format
* use file extensions in layer names as file formats 
* use layers with names in [square brackets] as a background for all other layers
* merge each top-level layer group into one layer
* permanently save settings in the Export Layers window to a file

Major code rewrite.
* Split the file into several separate modules. Written unit tests for most of these modules.
* Implemented API for plug-in settings for easier management.
* Implemented layer filtering, making it relatively easy to filter out layers
  according to their attributes, such as visibility (including its parents), name, and more.
* Misc. code refactoring and cleanup.

Changes to the GUI:
* Added advanced settings, collapsed by default.
* The main window now hides when the Export Layers button is clicked. Instead, a small dialog
  with a progress bar and a Stop button is displayed. This is to avoid the file format
  dialog being completely hidden by the main dialog. The Stop button allows the user
  to stop the export prematurely.
* Progress bar now updates after each successfully exported (or skipped) layer.
* Added a simple dialog to the Export Layers To menu entry, identical to the small dialog
  in Export Layers when exporting.
* Overwrite dialog now hides immediately after choosing an option.
* The order of the "Export Layers" and "Cancel" buttons is now the same as in the Export menu.
* Renamed "Chooose output directory" to "Save in folder:" to be consistent with the Export menu.
* In the overwrite dialog, renamed "Overwrite" to "Replace" to be consistent with the Export menu.
* Swapped the order of the "Skip" and "Replace" buttons in the overwrite dialog.
* Upon opening the main window, the focus is now set on the File Format field.
* Error messages are now in bold text. Removed the icon next to the error message
  as it didn't look good and didn't serve much purpose.
* Added tooltips to most of the settings.
* Added mnemonics (keyboard shortcuts) to the following components in the dialog (use Alt + the key after the underscore to activate the component, e.g. Alt+E for the "Export Layers" button):
  - _Export Layers
  - _Cancel
  - _Advanced Settings
* If the plug-in encounters an unexpected error, an error dialog (with details) is displayed.
* Adjusted spacing, padding and border width of components.

Bug fixes:
* Fixed JPG export of invisible layers.
* Fixed OpenRaster (.ora) export. No idea how it got fixed, though. Most likely it's the same issue as JPG.
* Fixed a bug that prevented the user from exporting layers to a root directory on Windows (e.g. "C:\").
* Layer names can no longer have characters ":" or "\", which could cause problems on Windows.
  These will now only be allowed in directory names.
* If "Treat layer groups as directories" setting is enabled and
  if the names of layers and layer groups have the same name after removing characters
  not allowed in filenames or directory names, they are now made unique properly.

Misc. changes:
* Layers exported with the "raw" file format will now have the ".raw" file extension added.

1.1 (September 08, 2013)
------------------------
* Added "Export Layers to" menu entry, repeating the export with last used settings.

1.0 (July 01, 2013)
------------------------
* Initial release.
