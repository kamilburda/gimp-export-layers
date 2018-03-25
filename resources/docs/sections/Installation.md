Requirements
------------

* GIMP 2.8 or later
* Python 2.7 or later from the 2.7.x series


Windows
-------

Make sure you installed GIMP with support for Python scripting.

Copy the following files and folders:

    export_layers.py
    export_layers

to

    [your home folder]\.gimp-[GIMP version]\plug-ins

Example of the installation folder: `C:\Users\khalim\.gimp-2.8\plug-ins`


Linux
-----

Copy the following files and folders:

    export_layers.py
    export_layers

to

    [your home folder]/.gimp-[GIMP version]/plug-ins

Example of the installation folder: `/home/khalim/.gimp-2.8/plug-ins`


OS X
----

Copy the following files and folders:

    export_layers.py
    export_layers

to

    [your home folder]/Library/Application Support/GIMP/[GIMP version]/plug-ins

Example of the installation folder:
`/Users/khalim/Library/Application Support/GIMP/2.8/plug-ins`

GIMP for OS X may have Python 2.6 bundled, which will not work with this
plug-in, since Python 2.7 is required.

To check if the correct version of Python is installed, start GIMP and go to
Filters -> Python-Fu -> Console. The console must display "Python 2.7" or later
from the 2.7.x series. If not, install Python 2.7, open
`/Applications/Gimp.app/Contents/Resources/lib/gimp/2.0/interpreters/pygimp.interp`
and change its contents to the following:

    python=/usr/bin/python
    /usr/bin/python=/usr/bin/python
    :Python:E::py::python:


Upgrading to 3.0
----------------

Due to numerous significant changes in version 3.0, make sure you perform a
complete reinstall when upgrading from an earlier version:

1. Reset settings by pressing the "Reset Settings" button.
2. Close GIMP.
3. Remove the `export_layers.py` file and the `export_layers` folder from the
installation folder. If you used 3.0-RC1, remove the `pygimplib` folder as well.
4. In the folder above `plug-ins`, open `parasiterc` in a text editor and remove the entire line beginning with `(parasite "plug_in_export_layers"`.
5. Run GIMP (so that GIMP "forgets" about the plug-in).
6. Install the new version.
