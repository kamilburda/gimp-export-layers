---
layout: docs_page
title: Release Notes
navbar_active_tab: docs
---

Upcoming Changes
================

Changes to the filename pattern entry:
* Reworked tooltips for each field, now containing usage, details and some examples.
* Explicitly specified tags are no longer sorted alphabetically.
* Changed the default separator and wrapper for the `Tags` field.
* Modified several arguments to use the `%` notation for brevity and consistency.
* Added a field to specify several layer or image attributes - layer width, height, *x*- and *y*-offsets and image width and height.
* Added an option to the number field (such as `[001]`) to disable resetting numbering across layer groups.

Misc. changes:
* From version 3.3 onward, obsolete settings, procedures or constraints are automatically replaced when first starting the plug-in with a newer version.


3.3
===

* **Due to significant changes in 3.3, make sure to perform a [clean reinstall](https://khalim19.github.io/gimp-plugin-export-layers/sections/Installation.html#Upgrading-from-Earlier-Versions).** The plug-in can still function without performing a clean reinstall (a warning dialog will ask you to clear settings), but will likely not be usable from the command line.
* Removed installers for Linux and macOS. The installers were not flexible enough to handle the diversity of available GIMP installers and different installation directories. The manual package is simple enough to install anyway (in some cases, simpler than the installers).
* Added the ability to add any PDB procedures to apply to all layers before export (blur, scale, drop shadows, ...). The argument values of any procedure can be adjusted by clicking the edit button.
* "Operations" are now referred to as "procedures".
* Allowed adding the same procedure or constraint multiple times.
* Allowed editing the name of procedures and constraints.
* Procedures or constraints are now enabled when added.
* Removed "Use image size". Added "Use layer size" having the opposite meaning to the list of custom procedures. This procedure is enabled by default.
* Removed "Treat layer groups as folders". The folder structure is now preserved by default and can be disabled by adding the new "Ignore folder structure" procedure.
* Moved "Only visible layers" to the list of constraints (still disabled by default).
* "Include layers" is now always displayed by default for clarity.
* Flattened menu items for built-in constraints for improved discoverability.
* "Only layers with tags" and "Only layers without tags" now optionally allow including/excluding only specific tags.
* "Insert background layers" and "Insert foreground layers" now allow modifying which tag represents back- and foreground layers, respectively.
* The preview is now displayed always, i.e. even if "Show More Settings" is unchecked. This helps users visualize the export even with the basic setup.
* Upon starting the plug-in, the image preview defaults to the active layer if there is no selection in the layer name preview.
* The image preview will be set to manual update if the update takes too long (currently set to 1 second). The automatic update can be turned on/off using the menu entry available above the image preview.
* Name preview: Renamed "Add tag..." to "Add New Tag...". Creating a new tag now automatically applies that tag to all the currently selected layers.
* Improved handling of long or multi-line in-dialog messages.
* Restored auto-hiding of in-dialog messages and delayed preview updates (the latter saving performance).
* Cleaned up arguments for `pdb.gimp_plugin_export_layers` due to the removal of the three settings visible in the "basic" GUI.
* Performed small adjustments in layout and spacing in the GUI.
* Changed mnemonics of GUI elements to avoid clashes with mnemonics for GTK widgets (such as folder chooser).
* Removed the redundant `Home` page from the documentation for the ZIP package.
* Errors are now logged as early as possible. If the plug-in is not fully initialized yet, the errors are logged into the `export_layers/error.log` file.
* Fixed image preview leaving artifacts when downsizing the image (by dragging panes).
* Fixed the main dialog displaying visually jarring white background for a short moment while initializing.
* Fixed a rare crash in the image preview for nested empty layer groups.


3.2.1
=====

* Added installers for Linux and macOS.
* Pressing the Help button now opens the Documentation subpage rather than the main page of the plug-in.
* Fixed updates to previews not working and info/error messages not disappearing automatically for GIMP 2.10 on Windows.
* Fixed GIMP version checks causing incorrect behavior of progress bars and preventing displaying several file extensions available on certain GIMP versions.

3.2
===

* Added a simple installer for Windows.
* Plug-in dialog now properly inherits the theme set in GIMP 2.10.
* Updated the list of file formats and extensions for GIMP 2.10.
* Error messages no longer disappear automatically after a while.
* Added a small amount of padding in the bottom part of the plug-in dialog.
* Fixed plug-in failing to load for GIMP 2.10 on Windows.
* Fixed a crash when running the plug-in after an upgrade from an early version (up to 3.0-RC1).
* Several minor updates to documentation.

3.1
===

* Created a single release package for GIMP 2.8, 2.9 and 2.10.
* Further decreased width of the file extension entry and filename pattern entry.
* Properly fixed enabled/disabled state of previews.

3.0
===

* Created a separate release for GIMP 2.9.
This release does not contain the smaller progress bar (displayed while exporting) due to the plug-in dialog freezing during the export.
* Tagged layer groups can now be inserted, even if "Include layer groups" constraint is disabled.
* Made "[layer path]" and "[tags]" fields for the filename pattern entry more flexible.
* If a field for the filename pattern entry has several variations for its arguments, the tooltip displays each variation on a separate line.
* File extension entry is now expandable.
* Decreased width of the file extension and filename pattern entries.
* Moved `pygimplib` folder back under `export_layers`.
* Fixed incorrect positioning of layers in the image previews.
* Fixed incorrect layer name in the image preview when a layer is first displayed there.
* Fixed Reset Settings not working for settings persisting during a GIMP session.
* Fixed enabled/disabled state of previews.
* Fixed extra period in export failure messages.


3.0-RC2
=======

* Renamed "filters" to "constraints" to avoid confusion with the concept of image filters.
* Adding a previously enabled and subsequently removed operation or constraint will now be disabled when added back again.
* Moved `pygimplib` folder above the `export_layers` folder.
* Changed user documentation to HTML (more-or-less a copy of the plug-in page).
* Fixed operations being ignored for "Export Layers (repeat)".
* Fixed dialog position resetting after closing the file format dialog.
* Fixed tagged layers (notably foreground and background) not working for indexed images.
* Added French, Russian and Ukrainian translations.

3.0-RC1
=======

Redesign of the basic user interface:
* "Advanced settings" are now referred to as "more settings".
* Merged the "Save Settings" and "Reset Settings" buttons and the "Advanced Settings" expander into one button named "Settings".
* Renamed "Export Layers" button to just "Export".
* Removed "Autocrop layers" from basic settings.
* Added a second progress bar indicating the export progress of the current layer.
* Misc. adjustments of GUI elements (size and spacing).

Major additions and redesign of the "advanced" user interface:
* Added option to rename layers according to a pattern (default: layer name).
* Removed GUI elements for "advanced" settings.
* Added option to add back the "advanced" settings as operations and filters via "Add Operation..." and "Add Filter..." boxes, respectively.
* Added preview displaying layer names to be exported.
* Added image preview of the layer selected in the layer name preview.
* Removed the option to tag layers by renaming layers.
Instead, layers can now be tagged via the layer name preview.
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
* Removed settings not in the lists above as the same functionality can be achieved via additional operations and filters or the filename pattern text entry.

Bug fixes:
* Fixed crash when "Search" or "Recently Used" were selected in the folder chooser.
* Fixed in-dialog messages with special characters not being displayed.
* Fixed "Export Layers (Repeat)" terminating prematurely if the user closed the overwrite dialog during a previous export.

Misc. changes:
* Reduced the number of PDB parameters for "plug-in-export-layers" as a result of the replacement of advanced settings with operations and filters.
* Export can now be stopped by pressing Escape.
* Export is now stopped if the image is closed during the export.
* Tagged layer groups are now also considered by settings dealing with tags.
* Added undo/redo capability to the file extension entry.
* JPEG dialog is no longer displayed in "Export Layers (Repeat)".
* In-dialog informative messages (e.g. "Settings successfully saved") now disappear automatically after a while.


2.5
===

* Added a feature to tag layers as foreground layers.
To use it, type "[foreground]" before the layer name.
* Changed the way background layers are specified.
Instead of enclosing the layer name in square brackets, type "[background]" before the layer name.
If you used background layers, make sure to change the layer names.
* Changed the setting "Layer names in [square brackets]" to "[Tagged] layers" and several other setting values to reflect the addition of foreground layers.
* The main dialog now hides again when a file format dialog is about to be displayed, in order to make sure that the file format dialog is not displayed behind the main dialog.
The main dialog reappears after the file format dialog is closed by the user.
* Consolidated error and warning messages displayed when an error during export or an unhandled exception occurred.
* The plug-in no longer crashes when it doesn't need to for certain errors during export, such as too long filenames.
* The output directory and input directories of imported images are no longer validated.
If the output directory is invalid, a warning message is displayed and the user can try exporting again.
This also avoids needless crashes.
* The plug-in no longer remembers settings in the non-interactive run mode.
This behavior is consistent with other GIMP plug-ins.
* "Export only layers matching file extension" is now applied before tagged layers are processed.
This means that when this setting is selected and back/foreground layers don't have a matching file extension, they will no longer form the back/foreground of the exported layer.


2.4
===

* The "File extension" text field now displays a dropdown list of file formats and associated file extensions (upon clicking or pressing Up/Down keys).
Several third-party formats are also listed, provided that the corresponding plug-ins are installed.
You can still enter a file extension not in the dropdown list in case you use a different file format plug-in.
* Renamed "Export Layers to" to "Export Layers (repeat)".
* Added mnemonics (keyboard shortcuts) to the dialog in "Export Layers (repeat)" and to the overwrite confirmation dialog.
* Fixed crash for input images located in folders that contain accented characters.
* Fixed export of layers with file extensions containing periods (e.g. "xcf.bz2") if files with the same name already exist in the chosen output folder.
* If "Use as file extensions" is selected and layers contain multiple extensions for the same file format (e.g. "jpeg", "jpg" or "jpe" for the JPEG format), the file format dialog is now displayed only once.
* If a layer name is enclosed with multiple pairs of square brackets, only the outermost pair is removed upon the export (e.g. a layer named "[[Background]]" is exported as "[Background].png").
* Removed " copy" suffix from the names of exported layers for formats preserving layer information (e.g. PSD or XCF).
* On Ubuntu, replaced the overlay scrollbar with the classic scrollbar.


2.3
===

* Removed tooltips for settings (except File Extension) due to being redundant.
* Allowed to type in the output directory manually in the directory chooser if the "Location:" label is visible.
* Changed the default value of the file extension strip mode to "Always strip file extension".
* Changed the persistent storage of settings from a custom JSON file to the GIMP's native "parasiterc" file.
This improves compatibility for certain GIMP builds not bundling some less commonly used Python modules.
Users need to re-save settings if they used the "Save Settings" feature.
* The plug-in now logs unhandled errors (exceptions) to the `export_layers/export_layers_error.log` file for official releases.
* Major refactoring of the code dealing with settings to make it easier to create and maintain them.


2.2.2
=====

* Set PNG as the default file format.
* Renamed settings containing the word "directory" to contain "folder".
* Allowed to install the plug-in system-wide (e.g. to `C:\Program Files\GIMP 2\lib\gimp\2.0\plug-ins` on Windows).
* Pressing Enter while the focus is on the "File extension" text field will now export layers.


2.2.1
=====

* Images in RAW format are saved with '.data' file extension instead of '.raw'.
* Image type is now preserved, instead of always using the RGB type.
E.g. if the image is indexed, the exported layers will be indexed as well.
File formats that don't support the an image type (such as indexed) will automatically convert the type as appropriate (the same way the Export menu does).
* Renamed "Use image size instead of layer size" to just "Use image size" for the sake of brevity.


2.2
===

* Changed how the initial output directory in the GUI is determined.
It is now remembered separately for each image currently opened in GIMP.
* Added support for plug-in internationalization and localization.
It is now possible to create translations of the plug-in (see the "Readme for Translators.txt" file in the package).
* Allowed again the following special characters in filenames: ~!@`#$%&=+{}[]
  * They can appear even on Windows (which seems to be the most restrictive of the popular OSs as far as invalid characters go).
The exceptions are '[' at the beginning and ']' at the end of the layer names, which are still removed, since they have a special meaning in the plug-in.
* When "No special handling" is selected, file extension strip mode will no longer default to "Strip identical file extension" (because the setting was always overwritten by its default value and thus did not remember the last used value).
* Misc. code refactoring and cleanup.


2.1
===

* Added support for Unicode characters.
This means you can now use any character in layer names and the output directory, except for most of the special characters.
* Export Layers GUI: Removed the small dialog.
The progress bar and the Stop button are now displayed directly in the main dialog.
* Renamed "File format" to "File extension" since that's what the user actually specifies.
Also, renamed a bunch of options so that they contain "extension" instead of "format".
Because of this, if you use "Save settings", you'll need to re-save them.
* Removed "Remove squared brackets" setting as it served little purpose.
[square brackets] will now always be removed from layer names.
* Added "Ignore layer mode" setting, which sets the layer mode to Normal for each layer.
* When "No special handling" is selected, file extension strip mode now defaults to "Strip identical file extension".
* More special characters are now removed from layer names.
* Removed unnecessary files from the package.
* Fixed a bug that caused the file format dialog to not appear if the user chose Skip in the overwrite dialog for the first file (or the first and subsequent files).
* Fixed filenames and directory names not being made unique properly, hopefully for real this time.
* More code refactoring and cleanup.


2.0
===

Implemented advanced settings, including the following:
* export only layers whose names match the file format
* use file extensions in layer names as file formats 
* use layers with names in [square brackets] as a background for all other layers
* merge each top-level layer group into one layer
* permanently save settings in the Export Layers window to a file

Major code rewrite.
* Split the file into several separate modules.
Written unit tests for most of these modules.
* Implemented API for plug-in settings for easier management.
* Implemented layer filtering, making it relatively easy to filter out layers according to their attributes, such as visibility (including its parents), name, and more.
* Misc. code refactoring and cleanup.

Changes to the GUI:
* Added advanced settings, collapsed by default.
* The main window now hides when the Export Layers button is clicked.
Instead, a small dialog with a progress bar and a Stop button is displayed.
This is to avoid the file format dialog being completely hidden by the main dialog.
The Stop button allows the user to stop the export prematurely.
* Progress bar now updates after each successfully exported (or skipped) layer.
* Added a simple dialog to the Export Layers To menu entry, identical to the small dialog in Export Layers when exporting.
* Overwrite dialog now hides immediately after choosing an option.
* The order of the "Export Layers" and "Cancel" buttons is now the same as in the Export menu.
* Renamed "Choose output directory" to "Save in folder:" to be consistent with the Export menu.
* In the overwrite dialog, renamed "Overwrite" to "Replace" to be consistent with the Export menu.
* Swapped the order of the "Skip" and "Replace" buttons in the overwrite dialog.
* Upon opening the main window, the focus is now set on the File Format field.
* Error messages are now in bold text.
Removed the icon next to the error message as it didn't look good and didn't serve much purpose.
* Added tooltips to most of the settings.
* Added mnemonics (keyboard shortcuts) to the following components in the dialog (use Alt + the key after the underscore to activate the component, e.g. Alt+E for the "Export Layers" button):
  * _Export Layers
  * _Cancel
  * _Advanced Settings
* If the plug-in encounters an unexpected error, an error dialog (with details) is displayed.
* Adjusted spacing, padding and border width of components.

Bug fixes:
* Fixed JPG export of invisible layers.
* Fixed OpenRaster (.ora) export. No idea how it got fixed, though. Most likely it's the same issue as JPG.
* Fixed a bug that prevented the user from exporting layers to a root directory on Windows (e.g. "C:\").
* Layer names can no longer have characters ":" or "\", which could cause problems on Windows.
These will now only be allowed in directory names.
* If "Treat layer groups as directories" setting is enabled and if the names of layers and layer groups have the same name after removing characters not allowed in filenames or directory names, they are now made unique properly.

Misc. changes:
* Layers exported with the "raw" file format will now have the ".raw" file extension added.


1.1
===

Release date: September 08, 2013

* Added "Export Layers to" menu entry, repeating the export with last used settings.


1.0
===

Release date: July 01, 2013

* Initial release.
