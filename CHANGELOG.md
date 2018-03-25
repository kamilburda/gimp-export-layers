3.0
===

* Tagged layer groups can now be inserted, even if "Include layer groups"
constraint is disabled.
* Made "[layer path]" and "[tags]" fields for the filename pattern entry more
flexible.
* If a field for the filename pattern entry has several variations for its
arguments, the tooltip displays each variation on a separate line.
* File extension entry is now expandable.
* Decreased width of the file extension and filename pattern entries.
* Moved `pygimplib` folder back under `export_layers`.
* Fixed incorrect positioning of layers in the image previews.
* Fixed incorrect layer name in the image preview when a layer is first
displayed there.
* Fixed Reset Settings not working for settings persisting during a GIMP
session.
* Fixed enabled/disabled state of previews.
* Fixed extra period in export failure messages.


3.0-RC2
=======

* Renamed "filters" to "constraints" to avoid confusion with the concept of
image filters.
* Adding a previously enabled and subsequently removed operation or constraint
will now be disabled when added back again.
* Moved `pygimplib` folder above the `export_layers` folder.
* Changed user documentation to HTML (more-or-less a copy of the plug-in page).
* Fixed operations being ignored for "Export Layers (repeat)".
* Fixed dialog position resetting after closing the file format dialog.
* Fixed tagged layers (notably foreground and background) not working for
indexed images.
* Added French, Russian and Ukrainian translations.

3.0-RC1
=======

Redesign of the basic user interface:
* "Advanced settings" are now referred to as "more settings".
* Merged the "Save Settings" and "Reset Settings" buttons and the "Advanced
Settings" expander into one button named "Settings".
* Renamed "Export Layers" button to just "Export".
* Removed "Autocrop layers" from basic settings.
* Added a second progress bar indicating the export progress of the current
layer.
* Misc. adjustments of GUI elements (size and spacing).

Major additions and redesign of the "advanced" user interface:
* Added option to rename layers according to a pattern (default: layer name).
* Removed GUI elements for "advanced" settings.
* Added option to add back the "advanced" settings as operations and filters via
"Add Operation..." and "Add Filter..." boxes, respectively.
* Added preview displaying layer names to be exported.
* Added image preview of the layer selected in the layer name preview.
* Removed the option to tag layers by renaming layers. Instead, layers can now
be tagged via the layer name preview.
* Added the option to add arbitrary tags to layers in the layer name preview.

Changes to settings:
* Renamed "Ignore invisible layers" to "Only visible layers".
* Added the following settings acting as additional operations before export:
  * "Insert background layers"
  * "Insert foreground layers"
  * "Inherit transparency from layer groups"
  * "Ignore layer modes"
  * "Autocrop"
  * "Autocrop background"
  * "Autocrop foreground"
  * "Use file extensions in layer names"
* Added the following settings acting as additional filters of layers:
  * "Include layers" (enabled by default)
  * "Include layer groups"
  * "Include empty layer groups"
  * "Only layers with tags"
  * "Only layers without tags"
  * "Only top-level layers"
  * "Only layers selected in preview"
* Removed settings not in the lists above as the same functionality can be
achieved via additional operations and filters or the filename pattern text
entry.

Bug fixes:
* Fixed crash when "Search" or "Recently Used" were selected in the folder
chooser.
* Fixed in-dialog messages with special characters not being displayed.
* Fixed "Export Layers (Repeat)" terminating prematurely if the user closed the
overwrite dialog during a previous export.

Misc. changes:
* Reduced the number of PDB parameters for "plug-in-export-layers" as a result
of the replacement of advanced settings with operations and filters.
* Export can now be stopped by pressing Escape.
* Export is now stopped if the image is closed during the export.
* Tagged layer groups are now also considered by settings dealing with tags.
* Added undo/redo capability to the file extension entry.
* JPEG dialog is no longer displayed in "Export Layers (Repeat)".
* In-dialog informative messages (e.g. "Settings successfully saved") now
disappear automatically after a while.


2.5
===

* Added a feature to tag layers as foreground layers. To use it, type
"[foreground]" before the layer name.
* Changed the way background layers are specified. Instead of enclosing the
layer name in square brackets, type "[background]" before the layer name. If you
used background layers, make sure to change the layer names.
* Changed the setting "Layer names in [square brackets]" to "[Tagged] layers"
and several other setting values to reflect the addition of foreground layers.
* The main dialog now hides again when a file format dialog is about to be
displayed, in order to make sure that the file format dialog is not displayed
behind the main dialog. The main dialog reappears after the file format dialog
is closed by the user.
* Consolidated error and warning messages displayed when an error during export
or an unhandled exception occurred.
* The plug-in no longer crashes when it doesn't need to for certain errors
during export, such as too long filenames.
* The output directory and input directories of imported images are no longer
validated. If the output directory is invalid, a warning message is displayed
and the user can try exporting again. This also avoids needless crashes.
* The plug-in no longer remembers settings in the non-interactive run mode. This
behavior is consistent with other GIMP plug-ins.
* "Export only layers matching file extension" is now applied before tagged
layers are processed. This means that when this setting is selected and
back/foreground layers don't have a matching file extension, they will no longer
form the back/foreground of the exported layer.


2.4
===

* The "File extension" text field now displays a dropdown list of file formats
and associated file extensions (upon clicking or pressing Up/Down keys). Several
third-party formats are also listed, provided that the corresponding plug-ins
are installed. You can still enter a file extension not in the dropdown list in
case you use a different file format plug-in.
* Renamed "Export Layers to" to "Export Layers (repeat)".
* Added mnemonics (keyboard shortcuts) to the dialog in "Export Layers (repeat)"
and to the overwrite confirmation dialog.
* Fixed crash for input images located in folders that contain accented
characters.
* Fixed export of layers with file extensions containing periods (e.g.
"xcf.bz2") if files with the same name already exist in the chosen output
folder.
* If "Use as file extensions" is selected and layers contain multiple extensions
for the same file format (e.g. "jpeg", "jpg" or "jpe" for the JPEG format), the
file format dialog is now displayed only once.
* If a layer name is enclosed with multiple pairs of square brackets, only the
outermost pair is removed upon the export (e.g. a layer named "[[Background]]"
is exported as "[Background].png").
* Removed " copy" suffix from the names of exported layers for formats
preserving layer information (e.g. PSD or XCF).
* On Ubuntu, replaced the overlay scrollbar with the classic scrollbar.


2.3
===

* Removed tooltips for settings (except File Extension) due to being redundant.
* Allowed to type in the output directory manually in the directory chooser if
the "Location:" label is visible.
* Changed the default value of the file extension strip mode to "Always strip
file extension".
* Changed the persistent storage of settings from a custom JSON file to the
GIMP's native "parasiterc" file. This improves compatibility for certain GIMP
builds not bundling some less commonly used Python modules. Users need to
re-save settings if they used the "Save Settings" feature.
* The plug-in now logs unhandled errors (exceptions) to the `export_layers/export_layers_error.log` file for official releases.
* Major refactoring of the code dealing with settings to make it easier to
create and maintain them.


2.2.2
=====

* Set PNG as the default file format.
* Renamed settings containing the word "directory" to contain "folder".
* Allowed to install the plug-in system-wide (e.g. to
`C:\Program Files\GIMP 2\lib\gimp\2.0\plug-ins` on Windows).
* Pressing Enter while the focus is on the "File extension" text field will now
export layers.


2.2.1
=====

* Images in RAW format are saved with '.data' file extension instead of '.raw'.
* Image type is now preserved, instead of always using the RGB type.
E.g. if the image is indexed, the exported layers will be indexed as well. File
formats that don't support the an image type (such as indexed) will
automatically convert the type as appropriate (the same way the Export menu
does).
* Renamed "Use image size instead of layer size" to just "Use image size" for
the sake of brevity.


2.2
===

* Changed how the initial output directory in the GUI is determined. It is now
remembered separately for each image currently opened in GIMP.
* Added support for plug-in internationalization and localization. It is now
possible to create translations of the plug-in (see the
"Readme for Translators.txt" file in the package).
* Allowed again the following special characters in filenames: ~!@`#$%&=+{}[]
  * They can appear even on Windows (which seems to be the most restrictive
  of the popular OSs as far as invalid characters go). The exceptions are '[' at
  the beginning and ']' at the end of the layer names, which are still removed,
  since they have a special meaning in the plug-in.
* When "No special handling" is selected, file extension strip mode will no
longer default to "Strip identical file extension" (because the setting was
always overwritten by its default value and thus did not remember the last
used value).
* Misc. code refactoring and cleanup.


2.1
===

* Added support for Unicode characters. This means you can now use any character
in layer names and the output directory, except for most of the special
characters.
* Export Layers GUI: Removed the small dialog. The progress bar and the Stop
button are now displayed directly in the main dialog.
* Renamed "File format" to "File extension" since that's what the user actually
specifies. Also, renamed a bunch of options so that they contain "extension"
instead of "format". Because of this, if you use "Save settings", you'll need to
re-save them.
* Removed "Remove squared brackets" setting as it served little purpose.
[square brackets] will now always be removed from layer names.
* Added "Ignore layer mode" setting, which sets the layer mode to Normal for
each layer.
* When "No special handling" is selected, file extension strip mode now defaults
to "Strip identical file extension".
* More special characters are now removed from layer names.
* Removed unnecessary files from the package.
* Fixed a bug that caused the file format dialog to not appear if the user chose
Skip in the overwrite dialog for the first file (or the first and subsequent
files).
* Fixed filenames and directory names not being made unique properly, hopefully
for real this time.
* More code refactoring and cleanup.


2.0
===

Implemented advanced settings, including the following:
* export only layers whose names match the file format
* use file extensions in layer names as file formats 
* use layers with names in [square brackets] as a background for all other
layers
* merge each top-level layer group into one layer
* permanently save settings in the Export Layers window to a file

Major code rewrite.
* Split the file into several separate modules. Written unit tests for most of
these modules.
* Implemented API for plug-in settings for easier management.
* Implemented layer filtering, making it relatively easy to filter out layers
according to their attributes, such as visibility (including its parents),
name, and more.
* Misc. code refactoring and cleanup.

Changes to the GUI:
* Added advanced settings, collapsed by default.
* The main window now hides when the Export Layers button is clicked. Instead,
a small dialog with a progress bar and a Stop button is displayed. This is to
avoid the file format dialog being completely hidden by the main dialog. The
Stop button allows the user to stop the export prematurely.
* Progress bar now updates after each successfully exported (or skipped) layer.
* Added a simple dialog to the Export Layers To menu entry, identical to the
small dialog in Export Layers when exporting.
* Overwrite dialog now hides immediately after choosing an option.
* The order of the "Export Layers" and "Cancel" buttons is now the same as in
the Export menu.
* Renamed "Choose output directory" to "Save in folder:" to be consistent with
the Export menu.
* In the overwrite dialog, renamed "Overwrite" to "Replace" to be consistent
with the Export menu.
* Swapped the order of the "Skip" and "Replace" buttons in the overwrite dialog.
* Upon opening the main window, the focus is now set on the File Format field.
* Error messages are now in bold text. Removed the icon next to the error
message as it didn't look good and didn't serve much purpose.
* Added tooltips to most of the settings.
* Added mnemonics (keyboard shortcuts) to the following components in the dialog
(use Alt + the key after the underscore to activate the component, e.g. Alt+E
for the "Export Layers" button):
  * _Export Layers
  * _Cancel
  * _Advanced Settings
* If the plug-in encounters an unexpected error, an error dialog (with details)
is displayed.
* Adjusted spacing, padding and border width of components.

Bug fixes:
* Fixed JPG export of invisible layers.
* Fixed OpenRaster (.ora) export. No idea how it got fixed, though. Most likely
it's the same issue as JPG.
* Fixed a bug that prevented the user from exporting layers to a root directory
on Windows (e.g. "C:\").
* Layer names can no longer have characters ":" or "\", which could cause
problems on Windows. These will now only be allowed in directory names.
* If "Treat layer groups as directories" setting is enabled and if the names of
layers and layer groups have the same name after removing characters not allowed
in filenames or directory names, they are now made unique properly.

Misc. changes:
* Layers exported with the "raw" file format will now have the ".raw" file
extension added.


1.1
===

Release date: September 08, 2013

* Added "Export Layers to" menu entry, repeating the export with last used
settings.


1.0
===

Release date: July 01, 2013

* Initial release.
