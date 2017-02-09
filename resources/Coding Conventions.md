Coding Conventions
==================

This document describes coding conventions that may not be obvious from the code
itself.


Glossary
--------

Element = module, class, function or variable


Formatting
----------

### Line length

Maximum line length is:
* 90 characters for code,
* 80 characters for docstrings and comments.


### Spacing

Use a separator (commented line containing "=" characters) for a block of
related functions or classes in a module.

Use two empty lines between a separator and a function or class definition. Use
one empty line between a separator and other statements.


### Indentation

Use 2 spaces for indentation.

Use hanging indents, with indented lines having 2 extra spaces.

For multi-line conditions, align expressions vertically.

For multi-line function and class definitions, loops and `with` statements, use
hanging indents and add 2 spaces after the beginning of the name of the
function/class, first loop variable or the expression after the `with` keyword.
For example:

    def __init__(
          self, name, default_value, display_name=None, description=None,
          error_messages=None):
      with open(
             "/totally/ridiculously/long/path/to/file.txt", "w") as f:
        pass


### Quotes in and Around Strings

Use double quotes everywhere except cases where single quotes or backquotes are
used.

Use single quotes:
* in element names in non-user messages (to be consistent with e.g. Python
  exception messages),
* in any string containing double quotes (to avoid inserting backslashes).

Use backquotes in element names in comments.


Naming
------

Use the following conventions for terms and variables:

| Term             | Variable name | Meaning                               |
|------------------|---------------|---------------------------------------|
| File name        | `filename`    | File basename                         |
| File path        | `filepath`    | Absolute or relative file path        |
| Directory path   | `dirpath`     | Absolute or relative directory path   |


Imports
-------

For local modules, use explicit relative imports. For modules forming a library,
this avoids a dependency on applications using the library.

Import whole modules, do not import individual classes, functions or other
objects. Exceptions:
* `from gimp import pdb`

Do not use wildcard imports. Exceptions:
* `from future.builtins import *` to help improve Python 3 compatibility.


Modules
-------

Module-level statements should only include imports, module docstring and
definitions of classes, functions and global variables/constants. Avoid
executing code on the module level if possible.


Classes
-------

### Mixins

Mixins can access and modify only those attributes defined in it.

No other classes may directly modify attributes defined in mixins.


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


Unicode Practices
-----------------

### Unicode for Internal Modules

Use Unicode strings internally.

### Unicode for External Modules

GIMP uses UTF-8 encoding. That includes the following functions or attributes:
* image name and item name (layer, channel, etc.),
* `PDB_STRING*` parameters to PDB procedures,
* `gimp.get_data()`, used by the GIMP shelf, can apparently handle Unicode
  (as it uses the `pickle` module), but encode/decode with UTF-8 just in case.

GTK uses UTF-8 encoding. Encode strings in UTF-8 for GTK functions as
[GTK may not fully support Unicode in Python 2]
(http://python-gtk-3-tutorial.readthedocs.org/en/latest/unicode.html).


### Methods

Use `@classmethod` for methods using class variables only. Use `@staticmethod` for methods not using instance or class variables and logically belonging to the
class.


GTK
---

When creating a `gtk.TreeView`, `bytes` apparently cannot be used as a column
type for strings due to the usage of the `future` library. Use
`GObject.TYPE_STRING` instead. For consistency, always use `GObject` types for
column types instead of Python types if such `GObject` types exist.
