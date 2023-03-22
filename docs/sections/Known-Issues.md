Known Issues
------------

Sometimes, after you hit the Export button, it may seem as though nothing happens.
In that case, the file format dialog may be displayed behind GIMP - if so, simply select the dialog to bring it up.

The following file formats are not working properly with this plug-in:
* colored XHTML - does not save images at all.

The following file formats require displaying the file format dialog for each layer, not just the first layer:
* raw (works properly for GIMP 2.10 and above),
* FLI,
* C source,
* HTML.

On Windows, the following file formats do not work properly if file paths contain accented characters:
* DDS (works properly for GIMP 2.10.10 and above),
* OpenRaster,
* X PixMap Image.

The image preview is only an approximation of what the exported image will look like and thus is not completely accurate when exporting with certain file formats.
For example, the preview will show a transparent image with no compression artifacts if the JPEG format (which does not support transparency) with low quality is selected.
