#!/bin/sh

command_exists()
{
  command -v "$1" > /dev/null 2>&1
  return $?
}

is_user_root()
{
  if [ `id -u` -eq 0 ]; then
    return 0
  else
    return 1
  fi
}

get_gimp_version_major_minor()
{
  if [ -n "$1" ]; then
    gimp_command="$1"
  else
    gimp_command='gimp'
  fi
  
  echo "`"$gimp_command" --version 2>&1 | sed 's/.*version \([0-9][0-9]*\)\.\([0-9][0-9]*\)\..*$/\1.\2/'`"
}

get_python_version_major_minor()
{
  if [ -n "$1" ]; then
    python_command="$1"
  else
    python_command='python'
  fi
  
  echo "`"$python_command" --version 2>&1 | sed 's/.*Python \([0-9][0-9]*\)\.\([0-9][0-9]*\)\..*$/\1.\2/'`"
}

get_user_plugins_dirpath()
{
  gimp_version="`get_gimp_version_major_minor`"
  version_major="`echo "$gimp_version" | cut -d '.' -f1`"
  version_minor="`echo "$gimp_version" | cut -d '.' -f2`"
  
  if [ $version_major -lt 2 ] || { [ $version_major -eq 2 ] && [ $version_minor -le 8 ]; }; then
    echo "$HOME"'/.gimp-'"$version_major"'.'"$version_minor"'/plug-ins'
  else
    echo "$HOME"'/.config/GIMP/'"$version_major"'.'"$version_minor"'/plug-ins'
  fi
}

get_system_plugins_dirpath()
{
  gimp_version="`get_gimp_version_major_minor`"
  version_major="`echo "$gimp_version" | cut -d '.' -f1`"
  
  echo '/usr/lib/gimp/'"$version_major"'.0/plug-ins'
}

get_installation_dirpath()
{
  if [ -n "$1" ]; then
    echo "$1"
  else
    if ! is_user_root; then
      echo "`get_user_plugins_dirpath`"
    else
      echo "`get_system_plugins_dirpath`"
    fi
  fi
}

has_correct_python_version()
{
  if command_exists "$1" && [ "`get_python_version_major_minor "$1"`" = "$REQUIRED_PYTHON_VERSION" ]; then
    return 0
  else
    return 1
  fi
}

has_correct_gimp_version()
{
  gimp_version="`get_gimp_version_major_minor "$1"`"
  version_major="`echo "$gimp_version" | cut -d '.' -f1`"
  version_minor="`echo "$gimp_version" | cut -d '.' -f2`"
  
  if [ $version_major -ge $MIN_REQUIRED_GIMP_VERSION_MAJOR ] && [ $version_minor -ge $MIN_REQUIRED_GIMP_VERSION_MINOR ]; then
    return 0
  else
    return 1
  fi
}

get_python_command_from_pygimp_interp()
{
  sed -n '1 s/^[^=]*=\(.*\)/\1/p' "$1"
}

exit_with_usage()
{
  usage='To install the plug-in system-wide, run this installer with root privileges.

Options:
  -g, --gimp-command [COMMAND] - file path to GIMP command; if this option is specified, -i option must be specified as well
  -i, --install-path [DIRECTORY] - plug-in installation path
  -h, --help - display this help and exit'
  
  echo
  
  if [ -z "$1" ]; then
    echo "$usage"
  else
    echo 'Error: '"$1"
    echo
    echo "$usage"
  fi
  
  exit 1
} 1>&2


script_filename="`basename "$0"`"

gimp_command_default='gimp'
gimp_command=''
installation_dirpath=''

MIN_REQUIRED_GIMP_VERSION_MAJOR=2
MIN_REQUIRED_GIMP_VERSION_MINOR=8
REQUIRED_PYTHON_VERSION='2.7'

python_command='python'
pygimp_interp_filename='pygimp.interp'
pygimp_interp_rel_dirpath='lib/gimp/2.0/interpreters'
pygimp_interp_system_filepath='/usr/'"$pygimp_interp_rel_dirpath"'/'"$pygimp_interp_filename"
CHECK_PYTHON_MANUALLY_MESSAGE="Check if GIMP is correctly installed with Python $REQUIRED_PYTHON_VERSION. You can display the Python version in GIMP by running 'Filter -> Python-Fu -> Console'. If this is not the case, install Python $REQUIRED_PYTHON_VERSION, locate '$pygimp_interp_filename' in your GIMP installation and set the path to the 'python' command there manually.
"

while [ "`echo "$1" | head -c1`" = "-" ] && [ "$1" != "--" ]; do
  case "$1" in
    -g | --gimp-command )
      if [ -n "$2" ]; then
        gimp_command="$2"
        shift
      else
        exit_with_usage "Missing argument to option $1"
      fi;;
    -i | --install-path )
      if [ -n "$2" ]; then
        installation_dirpath="$2"
        shift
      else
        exit_with_usage "Missing argument to option $1"
      fi;;
    -h | --help ) exit_with_usage;;
    * ) [ -n "$1" ] && exit_with_usage "Unknown argument: $1";;
  esac
  
  shift
done

[ "$1" = "--" ] && shift


if [ -z "$gimp_command" ]; then
  gimp_command="$gimp_command_default"
else
  if [ -z "$installation_dirpath" ]; then
    exit_with_usage 'If -g option is specified, -i must be specified as well.'
  fi
fi

if command_exists "$gimp_command"; then
  installation_dirpath="`get_installation_dirpath "$installation_dirpath"`"
else
  exit_with_usage "Could not find path to GIMP command ('$gimp_command'), please specify the correct path using option -g and the plug-in installation path with the -i option."
fi

if ! has_correct_gimp_version "$gimp_command"; then
  exit_with_usage "The specified GIMP installation ('$gimp_command') is not supported. Please install GIMP ${MIN_REQUIRED_GIMP_VERSION_MAJOR}.${MIN_REQUIRED_GIMP_VERSION_MINOR} or later or specify custom path to GIMP with the -g option and the plug-in installation path with the -i option."
fi

if [ "$gimp_command" = "$gimp_command_default" ]; then
  if [ -f "$pygimp_interp_system_filepath" ]; then
    python_command="`get_python_command_from_pygimp_interp "$pygimp_interp_system_filepath"`"
    
    if ! has_correct_python_version "$python_command"; then
      exit_with_usage "Python $REQUIRED_PYTHON_VERSION not installed. Please install Python $REQUIRED_PYTHON_VERSION and modify '$pygimp_interp_system_filepath' to point to Python $REQUIRED_PYTHON_VERSION command before proceeding."
    fi
  else
    echo "Warning: '$pygimp_interp_system_filepath' does not exist. $CHECK_PYTHON_MANUALLY_MESSAGE" 1>&2
  fi
else
  echo "Warning: Could not check for Python $REQUIRED_PYTHON_VERSION installation. $CHECK_PYTHON_MANUALLY_MESSAGE" 1>&2
fi

echo 'Copying files to '"$installation_dirpath"
chmod -R 755 .
rm -f "$script_filename"
mkdir -p "$installation_dirpath"
cp -a . "$installation_dirpath"
