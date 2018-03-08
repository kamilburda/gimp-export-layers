Developing Export Layers
========================

* [Development Setup](#Development-Setup)
* [Creating a Release](#Creating-a-Release)
* [Coding Conventions](#Coding-Conventions)
* [Writing Commit Messages](#Writing-Commit-Messages)
* [Writing Documentation](#Writing-Documentation)


Glossary
--------

Element = module, class, function or variable


Development Setup <a name="Development-Setup"></a>
-----------------

This section explains how to set up development environment for Export Layers.

A Linux distribution is recommended as the environment contains several bash
scripts. For Windows, see [below](#Development-Setup-on-Windows) for options.


### Setting up Repositories

Clone the master branch of the repository to a directory named e.g.
`plug-ins - Export Layers` inside the `.gimp-2.8` directory.

To make GIMP recognize the new directory as a directory containing GIMP
plug-ins, open up GIMP, go to `Edit -> Preferences -> Folders -> Plug-ins`
and add the new directory to the list. GIMP needs to be restarted for changes to
take effect.

Clone the `gh-pages` branch (acting as the
[GitHub page for Export Layers](https://khalim19.github.io/gimp-plugin-export-layers/))
to `resources/docs/gh-pages`. Several scripts depend on this directory
location.

Some scripts require that the GitHub page be run locally. To set up GitHub page
locally:
* Install Ruby language.
* Install `bundler` gem:

      gem install bundler

* Switch to the `gh-pages` directory:

      cd resources/docs/gh-pages
    
* Run `bundle` to install required dependencies:

      bundle install


### Git Hooks <a name="Git-Hooks"></a>

Set up git hooks located in `resources/git/hooks` by creating symbolic
links:
* `resources/git/hooks/commig_msg.py` -> `.git/hooks/commit-msg`
* `resources/git/hooks/pre_commit.py` -> `.git/hooks/pre-commit`

The `commig-msg` hook enforces several
[conventions for commit messages](#Writing-Commit-Messages).

The `pre-commit` hook automatically propagates changes in files in
`resources/docs` to files comprising the end user documentation, such as the
Readme and GitHub pages (located in `resources/docs/gh-pages`). See
[User Documentation](#User-Documentation) for more information.


### Development Setup on Windows <a name="Development-Setup-on-Windows"></a>

To set up the development environment on Windows, use a virtual machine with a
Linux distribution like Ubuntu.

For Windows 10 users, a viable alternative is to use the
[Windows Subsystem for Linux](https://docs.microsoft.com/en-us/windows/wsl/install-win10).
You'll also need to install an X server such as
[Xming](https://sourceforge.net/projects/xming/).
To enable X server on the shell, run `export DISPLAY=:0` before running
GIMP or any Export Layers script requiring non-interactive invocation of GIMP.


Creating a Release <a name="Creating-a-Release"></a>
------------------

To create a release package, simply run `resources/utils/make_package.sh`.
The package will be created in the `resources` directory.


Coding Conventions <a name="Coding-Conventions"></a>
------------------

Use PEP8 and PyLint to enforce coding conventions with their respective
configuration files:
* [PEP8 for PyDev](resources/PyDev/org.python.pydev.analysis.yaml)
* [PyLint](resources/PyLint/pylintrc)

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

Do not execute code on the module or class level. Exceptions to this rule include:
* initializing variables or constants,
* initializing application configuration,
* initializing a package or a library,
* standalone scripts such as test runners, git hooks, etc.

Do not execute functions from the GIMP API or PDB on the module or class level
as they are not fully initialized yet and it causes the application to crash.

Do not call the `_` function to mark module- or class-level strings as
translatable. You need to defer the translation until the strings are used in
the local scope. Define `N_` as a function to mark the strings as translatable
and then use the `_` function in the local scope to perform the actual
translation.


#### Execution in `__main__`

Execution of code inside `__main__` must be enclosed in a function in order to
avoid introducing global variables.
The name of the enclosing function should be `main()`.

Wrong:
    
    if __name__ == "__main__":
      # code

Right:
    
    def main():
      # code
    
    if __name__ == "__main__":
      main()


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
  [`future` library documentation](http://python-future.org/compatible_idioms.html),
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
[GTK may not fully support Unicode in Python 2](http://python-gtk-3-tutorial.readthedocs.org/en/latest/unicode.html).


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

Some conventions are automatically enforced by the git hook
[`commit-msg`](#Git-Hooks).
These conventions are marked by a trailing "*".


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

To indicate a more detailed scope, use ".", e.g. `gui.settings: ...`.


#### Verbs

The usage of leading verbs in the message header are not restricted, except for
the following verbs, which should only be used in specific circumstances:
* Fix - bug fixes
* Correct - corrections of typos, grammar errors


Writing Documentation <a name="Writing-Documentation"></a>
---------------------

### API Documentation

Documentation to modules, classes and functions are written as docstrings
directly in the source code.

### User Documentation <a name="User-Documentation"></a>

To update documentation for end users, modify the "raw" documentation - files
located in `resources/docs` (except files in `gh-pages`).

Do not modify other documentation files outside `resources/docs` as they are
automatically updated by [git hooks](#Git-Hooks) when committing changes to the
files in `resources/docs`.

Any changes propagated to files in `resources/docs/gh-pages` should be
committed and pushed only when a new release is made so that the Export Layers
page contains documentation of the latest official release.
