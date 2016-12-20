Coding conventions
==================

This document describes coding conventions not entirely obvious from the code itself.


Glossary
--------

element = module, class, function, variable


Quotes in and around Strings
----------------------------

* Double quotes:
  * everywhere except cases where single quotes are used
* Single quotes:
  * element names in non-user messages (to be consistent with e.g. Python exception messages)
  * any string containing double quotes (to avoid inserting backslashes)
* Backquotes:
  * element names in comments


Mixins
------

Mixins can access and modify only those attributes defined in it.

No other classes should directly modify attributes defined in mixins.


Imports
-------

* use explicit relative imports
  * for library modules, this avoids dependency on the application using the library
* import whole modules, do not import individual classes, functions or variables


Unicode Practices
-----------------

### Unicode Strings in Python 2

Use Python 3 behavior of Unicode strings in Python 2. To achieve this:
* `str()` must return string of type `unicode`, not `str`. Add the following statement to the beginning of each module:
  
      str = unicode

* Use `bytes` for bytes.
* To support Unicode literals, add the following import statement to each module:
    
      from __future__ import unicode_literals

### Unicode for Internal Modules

Always use Unicode strings internally.

### Unicode for External Modules

GIMP uses UTF-8 encoding. That includes the following functions or attributes:
* image name
* item name (layer, channel, etc.)
* PDB parameters - name, description
* `PDB_STRING` arguments to PDB procedures
* `gimp.get_data()`, used by the GIMP shelf can apparently handle Unicode (as it uses the `pickle` module), but encode/decode with UTF-8 just in case.

GTK uses UTF-8 encoding. Encode strings in UTF-8 for GTK functions as [GTK may not fully support Unicode in Python 2](http://python-gtk-3-tutorial.readthedocs.org/en/latest/unicode.html).

`os` module can handle both `str` and `unicode` types.

Argument to `write()` for file-like objects must be encoded in UTF-8.

