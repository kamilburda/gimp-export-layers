---
layout: docs_page
title: Known Issues
previous_doc_filename: Advanced-Usage.html
previous_doc_title: Advanced Usage
---

Sometimes, after you hit the Export button, it may seem as though nothing
happens. In that case, the file format dialog may be displayed behind GIMP - if
so, simply select the dialog to bring it up.

Several users reported crashes on Windows and OS X when clicking on the menu
entries. If the crashes occur to you, try reinstalling GIMP.

The following file formats are not working properly with this plug-in:
* colored XHTML - does not save images at all.

The following file formats have to display the file format dialog for each layer,
not just the first layer:
* raw,
* FLI,
* C source,
* HTML.

On Windows, the following file formats don't work properly if file paths contain
accented characters:
* DDS,
* OpenRaster,
* X PixMap Image.
