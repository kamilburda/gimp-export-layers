Requirements
------------

* GIMP 2.8 or later
* Python 2.7 or later from the 2.7.x series


Installers
----------

### Windows

Simply run the Windows installer and customize plug-in installation path as
needed. If you have a portable GIMP installation, you will be prompted to
specify the path to GIMP and GIMP plug-ins manually.

### Linux

Simply run the installer (which is actually a self-extracting archive) from the terminal or double-clicking on the file in the GUI of your file explorer application if supported.

You can customize the file path to the GIMP executable and the plug-in installation with `-g` and `-i` option, respectively. These options must be specified as follows (do not forget the `--`):

    [installer script].sh -- -g [gimp_filepath] -i [installation_path]

If `-g` is specified, so must be `-i`, otherwise the installation will not proceed.

To install Export Layers system-wide, run the installer with root privileges.


Manual installation (ZIP package)
---------------------------------

### Windows

Make sure you have GIMP installed with support for Python scripting.

Copy the following files and folders:

    export_layers.py
    export_layers

to the folder containing plug-ins depending on your version of GIMP:

* GIMP 2.8: `C:\Users\[your username]\.gimp-2.8\plug-ins`
* GIMP 2.9: `C:\Users\[your username]\AppData\Roaming\GIMP\2.9\plug-ins`
* GIMP 2.10: `C:\Users\[your username]\AppData\Roaming\GIMP\2.10\plug-ins`

If you can't locate the folder, open GIMP, go to "Edit → Preferences → Folders → Plug-Ins" and use one of the listed folders.


### Linux

Copy the following files and folders:

    export_layers.py
    export_layers

to the folder containing plug-ins depending on your version of GIMP:

* GIMP 2.8: `/home/[your username]/.gimp-2.8/plug-ins`
* GIMP 2.9: `/home/[your username]/.config/GIMP/2.9/plug-ins`
* GIMP 2.10: `/home/[your username]/.config/GIMP/2.10/plug-ins`

If you can't locate the folder, open GIMP, go to "Edit → Preferences → Folders → Plug-Ins" and use one of the listed folders.

To check if the correct version of Python is installed, start GIMP and go to
"Filters → Python-Fu → Console". The console must display "Python 2.7" or later
from the 2.7.x series. If not, install Python 2.7, open
`/usr/lib/gimp/2.0/interpreters/pygimp.interp`
and change its contents to the following:

    python=[path to Python 2.7 executable]
    /usr/bin/python=[path to Python 2.7 executable]
    :Python:E::py::python:

`[path to Python 2.7 executable]` is usually `/usr/bin/python` or `/usr/bin/python2.7`.


### macOS

Copy the following files and folders:

    export_layers.py
    export_layers

to the folder containing plug-ins depending on your version of GIMP:

* GIMP 2.8: `/Users/[your username]/Library/Application Support/GIMP/2.8/plug-ins`
* GIMP 2.9: `/Users/[your username]/Library/Application Support/GIMP/2.9/plug-ins`
* GIMP 2.10: `/Users/[your username]/Library/Application Support/GIMP/2.10/plug-ins`

If you can't locate the folder, open GIMP, go to "Edit → Preferences → Folders → Plug-Ins" and use one of the listed folders.

To check if the correct version of Python is installed, start GIMP and go to
"Filters → Python-Fu → Console". The console must display "Python 2.7" or later
from the 2.7.x series. If not, install Python 2.7, open
`/Applications/Gimp.app/Contents/Resources/lib/gimp/2.0/interpreters/pygimp.interp`
and change its contents to the following:

    python=[path to Python 2.7 executable]
    /usr/bin/python=[path to Python 2.7 executable]
    :Python:E::py::python:

`[path to Python 2.7 executable]` is usually `/usr/bin/python` or `/usr/bin/python2.7`.


Upgrading from 2.x to to 3.x
----------------------------

Due to numerous significant changes in version 3.0, make sure you perform a
complete reinstall when upgrading from an earlier version:

1. Reset settings by pressing the "Reset Settings" button.
2. Close GIMP.
3. Remove the `export_layers.py` file and the `export_layers` folder from the
installation folder. If you used 3.0-RC1, remove the `pygimplib` folder as well.
4. In the folder above `plug-ins`, open `parasiterc` in a text editor and remove the entire line beginning with `(parasite "plug_in_export_layers"`.
5. Run GIMP (so that GIMP "forgets" about the plug-in).
6. Install the new version.
