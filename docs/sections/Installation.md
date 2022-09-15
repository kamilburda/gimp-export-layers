Requirements
------------

* GIMP 2.8 or 2.10
* Python 2.7 or later from the 2.7.x series


Windows
-------

### Installer

1. Make sure you have GIMP installed with support for Python scripting.
2. Run the Windows installer and customize plug-in installation path as needed.
   If you have a portable GIMP installation, you will be prompted to specify the path to GIMP and GIMP plug-ins manually.


### Manual installation (ZIP package)

1. Make sure you have GIMP installed with support for Python scripting.
2. Locate the folder containing GIMP plug-ins - open GIMP and go to `Edit → Preferences → Folders → Plug-Ins`.
3. Extract the following files and folders to one of the folders identified in step 2:

       export_layers.py
       export_layers


Linux
-----

### If GIMP is installed via Flatpak or AppImage

The easier way to install any Python-based GIMP plug-in is to use a GIMP installation bundled in Flatpak (which can be downloaded from the [official GIMP page](https://www.gimp.org/downloads/)) or AppImage.

1. Install Python 2.7 if not already.
   Usually by default, Linux distributions offer Python 3, which does not work with GIMP 2.8 or 2.10.
2. Locate the folder containing GIMP plug-ins - open GIMP and go to `Edit → Preferences → Folders → Plug-Ins`.
3. Extract the following files and folders to one of the folders identified in step 2:

       export_layers.py
       export_layers

To check if GIMP recognizes your Python 2.7 installation, open GIMP and run `Filters → Python-Fu → Console`.
The console must display `Python 2.7` or later from the 2.7.x series.
If this is not the case, open `/usr/lib/gimp/2.0/interpreters/pygimp.interp` and change its contents to the following:

    python=[path to Python 2.7 executable]
    /usr/bin/python=[path to Python 2.7 executable]
    :Python:E::py::python:

`[path to Python 2.7 executable]` is usually `/usr/bin/python` or `/usr/bin/python2.7`.


### If GIMP is installed via package manager

This is the less recommended way of installing plug-ins as of recently as certain distributions may have missing packages that are required for successful running of Python GIMP plug-ins (due to these distributions dropping packages dependent on Python 2).

1. Install Python 2.7.
   Usually by default, Linux distributions offer Python 3, which does not work with GIMP 2.8 or 2.10.
2. Install packages enabling the use of Python for GIMP plug-ins.
	 This varies across distributions.
	 For instance, on Arch Linux, you must install the `python2-gimp` package.
3. Locate the folder containing GIMP plug-ins - open GIMP and go to `Edit → Preferences → Folders → Plug-Ins`.
4. Extract the following files and folders to one of the folders identified in step 2:

       export_layers.py
       export_layers

To check if GIMP recognizes your Python 2.7 installation, open GIMP and run `Filters → Python-Fu → Console`.
The console must display `Python 2.7` or later from the 2.7.x series.
If this is not the case, open `/usr/lib/gimp/2.0/interpreters/pygimp.interp` and change its contents to the following:

    python=[path to Python 2.7 executable]
    /usr/bin/python=[path to Python 2.7 executable]
    :Python:E::py::python:

`[path to Python 2.7 executable]` is usually `/usr/bin/python` or `/usr/bin/python2.7`.


macOS
-----

1. Make sure you have Python 2.7 installed.
2. Locate the folder containing GIMP plug-ins - open GIMP and go to `Edit → Preferences → Folders → Plug-Ins`.
3. Extract the following files and folders to one of the folders identified in step 2:

       export_layers.py
       export_layers


Upgrading to 3.3 <a name="Upgrading-from-Earlier-Versions"></a>
----------------

Due to significant changes in version 3.3, make sure you first perform complete reinstall when upgrading from an earlier version:

1. Still using the old version, run Export Layers, select `Settings → Show More Settings`, check `Remove procedures and constraints` and reset settings by pressing the `Reset Settings` button.
2. Close Export Layers.
3. Close GIMP.
4. Remove the `export_layers.py` file and the `export_layers` folder from the installation folder.
   If you used 3.0-RC1, remove the `pygimplib` folder as well.
5. In the folder above `plug-ins`, open `parasiterc` in a text editor and remove the entire line beginning with `(parasite "plug_in_export_layers"`.
6. Run GIMP without Export Layers installed (so that GIMP "forgets" about the plug-in).
7. Install the new version.

You can still upgrade to the newest version if you did not perform steps 5 and 6.
A warning dialog will ask you to reset the settings.
However, calling `pdb.plug_in_export_layers` from the command line will probably result in an execution error due to the mismatch of arguments.
