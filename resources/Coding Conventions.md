Coding Conventions
==================

This document describes coding conventions not obvious from the code itself.


Glossary
--------

Element = module, class, function or variable


Quotes in and Around Strings
----------------------------

Use double quotes everywhere except cases where single quotes or backquotes are
used.

Use single quotes:
* in element names in non-user messages (to be consistent with e.g. Python
  exception messages),
* in any string containing double quotes (to avoid inserting backslashes).

Use backquotes in element names in comments.


Python 3 Compatibility
----------------------

Strive to make Python 2 code as compatible as possible with Python 3.
* At the beginning of each module, import the `__future__` statements and the
  `future.builtins` package from the `future` library.
* Use constructs compatible with both Python 2 and 3 as described in the
  [`future` library documentation]
  (http://python-future.org/compatible_idioms.html),
  with the following exceptions:
  * do not wrap strings in `str` or `bytes` to avoid making the code difficult
    to maintain.


Imports
-------

For local modules, prefer explicit relative imports to absolute imports. For
modules forming a library, this avoids dependency on the application using the
library.

Import whole modules, do not import individual classes, functions or variables.

Do not use wildcard imports. Exceptions to this rule include:
* `from future.builtins import *` to help improve Python 3 compatibility.

Module-level statements should only include imports, docstring and definitions
of classes, functions and global variables/constants. Avoid executing code on
the module level if possible.


Unicode Practices
-----------------

### Unicode for Internal Modules

Always use Unicode strings internally.

### Unicode for External Modules

GIMP uses UTF-8 encoding. That includes the following functions or attributes:
* image name and item name (layer, channel, etc.),
* `PDB_STRING*` parameters to PDB procedures,
* `gimp.get_data()`, used by the GIMP shelf, can apparently handle Unicode (as it
  uses the `pickle` module), but encode/decode with UTF-8 just in case.

GTK uses UTF-8 encoding. Encode strings in UTF-8 for GTK functions as
[GTK may not fully support Unicode in Python 2]
(http://python-gtk-3-tutorial.readthedocs.org/en/latest/unicode.html).


Mixins
------

Mixins can access and modify only those attributes defined in it.

No other classes should directly modify attributes defined in mixins.


GTK
---

When creating a `gtk.TreeView`, `bytes` apparently cannot be used as a column
type for strings due to the usage of the `future` library. Use
`GObject.TYPE_STRING` instead. For consistency, always use `GObject` types for
column types instead of Python types if such `GObject` types exist.
