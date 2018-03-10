#!/bin/bash

# This script initializes the Export Layers git repository.

gimp_local_dirpath="$HOME"'/.gimp-2.8'
plugin_main_repo_dirname='plug-ins - Export Layers'
plugin_page_branch_name='gh-pages'
repo_url='https://github.com/khalim19/gimp-plugin-export-layers.git'
repo_dirpath="$gimp_local_dirpath"'/'"$plugin_main_repo_dirname"

orig_cwd="$(pwd)"


# Install required programs/packages
# If supported package managers are not available (apt-get, yum), developer has
# to install missing packages manually.

function command_exists()
{
  command -v "$1" > /dev/null 2>&1
  return $?
}

required_packages='git
ruby
ruby-dev
zlib1g-dev
python
python-pip
gimp'

if command_exists 'apt-get'; then
  sudo apt-get install -y $required_packages
elif command_exists 'yum'; then
  sudo yum install -y $required_packages
else
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
pyyaml'

sudo pip install $python_modules


# GIMP initialization

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
ln -s 'resources/git/hooks/commig_msg.py' '.git/hooks/commit-msg'
ln -s 'resources/git/hooks/pre_commit.py' '.git/hooks/pre-commit'

cd 'resources/docs'

echo 'Cloning '"$plugin_page_branch_name"' branch of '"$repo_url"' into '\'"$repo_dirpath"'/resources/docs/'"$plugin_page_branch_name"\'
git clone --branch "$plugin_page_branch_name" -- "$repo_url" "$plugin_page_branch_name"

cd "$plugin_page_branch_name"

echo 'Setting up git hooks for branch '"$plugin_page_branch_name"
ln -s "$repo_dirpath"'/resources/git/hooks/commig_msg.py' '.git/hooks/commit-msg'

bundle install

cd "$orig_cwd"
