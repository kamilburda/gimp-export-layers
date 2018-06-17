#!/bin/bash

# This script initializes the Export Layers git repository.

orig_cwd="$(pwd)"

# Install required programs/packages
# If supported package managers are not available (apt-get), developer has to
# install missing packages manually.

function command_exists()
{
  command -v "$1" > /dev/null 2>&1
  return $?
}

if command_exists 'apt-get'; then
  required_packages='git
ruby
ruby-dev
build-essential
patch
zlib1g-dev
liblzma-dev
libgmp-dev
libffi-dev
gcc
python
python-pip
makeself
gimp'

  sudo apt-get install -y $required_packages
else
  required_packages='git
ruby
python27
python-pip
gimp'

  echo 'Make sure the following packages are installed:'
  echo "$required_packages"
  echo ''
  echo -n "If you have all required packages installed, press 'y', otherwise press any key to terminate the script and install the packages manually: "
  read -n 1 key_pressed
  
  echo ''
  
  if [ "${key_pressed,,}" != 'y' ]; then
    echo "Terminating script. Please install packages listed above before running the script." 1>&2
    exit 1
  fi
fi


# Installation of Ruby and Python packages

sudo gem install bundler

python_modules='pathspec
pathlib
requests
mock
parameterized
psutil
pyyaml
pyautogui'

sudo pip install $python_modules


# GIMP initialization

gimp_version_major_minor="$(gimp --version | sed 's/.*version \([0-9][0-9]*.[0-9][0-9]*\).*$/\1/')"

if [ "$gimp_version_major_minor" = "2.8" ]; then
  gimp_local_dirpath="$HOME"'/.gimp-2.8'
elif [[ ! "$gimp_version_major_minor" < "2.9" ]]; then
  gimp_local_dirpath="$HOME"'/.config/GIMP/'"$gimp_version_major_minor"
else
  echo "Unsupported version of GIMP ($gimp_version_major_minor). Please install GIMP version 2.8 or later."
  exit 1
fi

plugin_main_repo_dirname='plug-ins - Export Layers'
plugin_page_branch_name='gh-pages'
repo_url='https://github.com/khalim19/gimp-plugin-export-layers.git'
repo_dirpath="$gimp_local_dirpath"'/'"$plugin_main_repo_dirname"

gimprc_filename='gimprc'
gimprc_filepath="$gimp_local_dirpath"'/'"$gimprc_filename"
system_gimprc_filepath='/etc/gimp/2.0/gimprc'

if [ ! -f "$gimprc_filepath" ]; then
  echo "$gimprc_filename"' does not exist, running GIMP...'
  gimp --no-interface --new-instance --batch-interpreter='python-fu-eval' --batch 'pdb.gimp_quit(0)'
fi

if [ ! -f "$gimprc_filepath" ]; then
  echo "$gimprc_filename"' still does not exist, creating new file'
  plugin_dirpaths_from_system_gimprc="$(grep -oE '\(plug-in-path ".*"\)' "$system_gimprc_filepath" | sed -r 's/\(plug-in-path "(.*)"\)/\1/')"
  
  echo 'Adding repository path to the list of plug-in directories in '"$gimprc_filename"
  echo '(plug-in-path "'"$plugin_dirpaths_from_system_gimprc"':'"$repo_dirpath"'")' > "$gimprc_filepath"
else
  repo_dirpath_in_gimprc="$(grep -oE '\(plug-in-path ".*'"$repo_dirpath"'"\)' "$gimprc_filepath")"
  if [ ! "$repo_dirpath_in_gimprc" ]; then
    echo 'Adding repository path to the list of plug-in directories in '"$gimprc_filename"
    sed -i -r -e 's:(\(plug-in-path ".*)("\)):\1\:'"$repo_dirpath"'\2:' "$gimprc_filepath"
  fi
fi


# Repository initialization

echo 'Cloning master branch of '"$repo_url"' into '\'"$repo_dirpath"\'
git clone --recurse-submodules -- "$repo_url" "$repo_dirpath"

cd "$repo_dirpath"

echo 'Setting up git hooks'
ln -s 'git_hooks/commit_msg.py' '.git/hooks/commit-msg'
ln -s 'git_hooks/pre_commit.py' '.git/hooks/pre-commit'

echo 'Setting up filters to ignore modifications to specific lines'
git config --local 'filter.ignore_config_entries.clean' "sed 's/pygimplib\\.config\\.LOG_MODE = .*/pygimplib\\.config\\.LOG_MODE = pygimplib\\.pglogging\\.LOG_EXCEPTIONS_ONLY/' | sed 's/pygimplib\\.config\\.DEBUG_IMAGE_PROCESSING = .*/pygimplib\\.config\\.DEBUG_IMAGE_PROCESSING = False/'"
git config --local 'filter.ignore_config_entries.smudge' 'cat'

cd 'docs'

echo 'Cloning '"$plugin_page_branch_name"' branch of '"$repo_url"' into '\'"$repo_dirpath"'/docs/'"$plugin_page_branch_name"\'
git clone --branch "$plugin_page_branch_name" -- "$repo_url" "$plugin_page_branch_name"

cd "$plugin_page_branch_name"

echo 'Setting up git hooks for branch '"$plugin_page_branch_name"
ln -s "$repo_dirpath"'/git_hooks/commit_msg.py' '.git/hooks/commit-msg'

bundle install

cd "$orig_cwd"
