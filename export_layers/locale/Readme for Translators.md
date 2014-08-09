Export Layers - Translations
============================

If you want to provide translations for the plug-in, I recommend using
a translation tool such as Poedit (http://poedit.net) for easier usage.

Poedit
------------------------

The following steps apply if you want to use Poedit:

1. Go to https://github.com/khalim19/gimp-plugin-export-layers/tree/master/resources
   and download the .pot file with the appropriate version (e.g. for version 2.2,
   it's `export_layers-2.2.pot`).
2. Open Poedit, select "File -> New from POT/PO file..." and find the downloaded
   .pot file for the plug-in.
3. Set the language of the translation.
4. Translate the strings (by filling in the "Translation" text field for each string).
5. If desired, go to "Catalog -> Properties..." and edit the translation file
   properties. If you don't do this, warning messages may pop up when saving,
   but they should be harmless.
6. When done, save the .po file. An .mo file is generated automatically (in the
   same directory as the .po file).
7. Move and rename the .mo file to
   
        [user directory]/.gimp-2.8/plug-ins/export_layers/locale/[language code]/LC_MESSAGES/export_layers.mo
   
   where `[language code]` is the language code in which you translated the plug-in.
   `[language code]` is a part of the .po file - e.g. for a file named "fr_FR.po",
   the language code is "fr_FR".


Terminal
------------------------

If you don't want to use Poedit, the following steps apply. It is assumed you
are using the terminal on Linux (or Cygwin on Windows).

1. Make sure that `msginit` and `msgfmt` commands are installed on your system.
   If not, install `gettext`:
   
        sudo apt-get install `gettext`
   
2. Go to https://github.com/khalim19/gimp-plugin-export-layers/tree/master/resources
   and download the .pot file with the appropriate version (e.g. for version 2.2,
   it's `export_layers-2.2.pot`).
3. Open up terminal and run
   
        msginit --input=[path to .pot file] --locale=[language code]
   
   where `[path to .pot file]` is the .pot file you downloaded and `[language code]`
   is a two-letter code representing a language.
   A .po file is generated in the same directory as the current working directory.
   
   If in doubt, you can consult the list of available language codes on the following page:
   https://www.gnu.org/software/gettext/manual/html_node/Usual-Language-Codes.html
4. Open up the .po file and translate each string in the `msgid` field to string
   in the corresponding `msgstr` field.
5. When done translating, generate the .mo file as follows:
   
        mkdir -p [path to .mo file]
        msgfmt [path to .po file] --output-file=[path to .mo file]/export_layers.mo
   
   where `[path to .mo file]` is
   
        [user directory]/.gimp-2.8/plug-ins/export_layers/locale/[language code]/LC_MESSAGES
   

Testing Your Translation
------------------------

To test your translation on Linux, run GIMP from the terminal as follows:
   
    export LANG=[language code].UTF-8
    gimp
   
To test your translation on Windows, run GIMP from the Windows command line as follows:
   
    set lang=[language code].UTF-8
    gimp-2.8.exe
   

If the Windows command line does not recognize `gimp-2.8.exe`, specify its full path, e.g.:
   
    C:\Program Files\GIMP 2\bin\gimp-2.8.exe
