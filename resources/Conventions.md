Conventions
===========

This document contains conventions to be followed when contributing to
Export Layers.

* [Coding Conventions](#Coding-Conventions)
* [Writing Commit Messages](#Writing-Commit-Messages)


Glossary
--------

Element = module, class, function or variable


Coding Conventions <a name="Coding-Conventions"></a>
------------------

Use PEP8 and PyLint to enforce coding conventions with their respective
configuration files:
* [PEP8 for PyDev](PyDev/org.python.pydev.analysis.yaml)
* [PyLint](PyLint/pylintrc)

Additional conventions that override or complement the conventions in the
aforementioned utilities are specified below.


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


### Naming

Use the following conventions for terms and variables:

| Term             | Variable name | Meaning                               |
|------------------|---------------|---------------------------------------|
| File name        | `filename`    | File basename                         |
| File path        | `filepath`    | Absolute or relative file path        |
| Directory path   | `dirpath`     | Absolute or relative directory path   |


### Imports

Import modules at the beginning of a module.

Use explicit relative imports in modules not used as main modules. For modules
forming a library, this avoids a dependency on applications using the library.

Import whole modules, do not import individual classes, functions or other
objects. Exceptions:
* `from gimp import pdb`

Do not use wildcard imports. Exceptions:
* `from future.builtins import *` to help improve Python 3 compatibility.


### Executing Code

Do not execute code on the module or class level. In particular:
* Do not execute functions from the GIMP API or PDB as they are not fully
initialized and it causes the application to crash.
* Do not call the `_` function to mark module- or class-level strings as
translatable. You need to defer the translation until the strings are used in
the local scope. Define `N_` as a function to mark the strings as translatable
and then use the `_` function in the local scope to perform the actual
translation.

Exceptions to this rule include:
* initializing variables or constants,
* initializing application configuration,
* initializing a package or a library.


### Classes

Mixins can access and modify only those attributes defined in it.

No other classes may directly modify attributes defined in mixins.


### Methods

Use `@classmethod` for methods using class variables only.
Use `@staticmethod` for methods not using instance or class variables and
logically belonging to the class.


### Python 3 Compatibility

Strive to make Python 2 code as compatible as possible with Python 3.
* At the beginning of each module, import the `__future__` statements and the
  `future.builtins` package from the `future` library.
* Use constructs compatible with both Python 2 and 3 as described in the
  [`future` library documentation]
  (http://python-future.org/compatible_idioms.html),
  with the following exceptions:
  * do not wrap strings in `str` or `bytes` to avoid making the code difficult
    to maintain.


### Unicode

Use Unicode strings internally.

Encode/decode Unicode strings when accessing the following external libraries:
* GIMP - use UTF-8 encoding. Encoding applies to:
  * `PDB_STRING*` parameters to PDB procedures,
  * functions and object attributes provided by Python GIMP API.
* GTK - use UTF-8 encoding. Encoding may be necessary as
[GTK may not fully support Unicode in Python 2]
(http://python-gtk-3-tutorial.readthedocs.org/en/latest/unicode.html).


### GTK

When creating a `gtk.TreeView`, `bytes` apparently cannot be used as a column
type for strings due to the usage of the `future` library. Use
`GObject.TYPE_STRING` instead. For consistency, always use `GObject` types for
column types instead of Python types if such `GObject` types exist.


Writing Commit Messages <a name="Writing-Commit-Messages"></a>
-----------------------

This section explains how to write good commit messages. The conventions are
based on the following guidelines:
* [How to Write a Git Commit Message](https://chris.beams.io/posts/git-commit/)
* [Git commit message](https://github.com/joelparkerhenderson/git_commit_message)

Some conventions can be automatically enforced by a
[custom git `commit-msg` hook script](git/hooks/commit_msg.py).
These conventions are marked by a trailing "*". To install the hook script, copy
the script to the `.git/hooks` directory and rename it to `commit-msg`.


### General

* Each commit should change one and one thing only. For example, a bug fix and
refactoring a function result in separate commits.
* Create separate commits for modifying a subtree/submodule and the parent
repository.


### Formatting

Use the following format for commit messages*:

    <scope>: <header>
    
    <body>

* Limit the first line to 70 characters*. Recommended length is 50 characters.
* Do not end the first line with a period*.
* Begin the header with a verb in the imperative.
* Begin the header with a capital letter*.
* Be concise. Limit the message to the first line unless further explanation is
required.
* Wrap the message body in 72 characters*.
* Enclose element names with backquotes.


#### Scope

Scope in the first line is optional, but highly recommended.

Use one of the following types of scope (ordered from the most preferred):
* subtree/submodule name
* package name
* module name
* filename without extension

#### Verbs

The usage of leading verbs in the message header are not restricted, except for
the following verbs, which should only be used in specific circumstances:
* Fix - bug fixes
* Correct - corrections of typos, grammar errors
