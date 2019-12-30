#!/bin/bash

# This script runs the Jekyll server locally with GitHub Pages metadata properly disabled.

SCRIPT_NAME="${0##*/}"
SCRIPT_DIRECTORY="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

pages_dirpath="$(dirname "$SCRIPT_DIRECTORY")"'/docs/gh-pages'
config_filename='_config.yml'
local_config_filename='_config_local.yml'

local_config_entries='
github: [metadata]'

cleanup () {
  rm -f "$local_config_filename"
}

usage () {
  {
    echo ""
    echo "Usage: $SCRIPT_NAME [OPTIONS]..."
    echo ""
    echo "Options:"
    echo "  -r, --release    build site for release packages without having to run Jekyll server"
    echo "  -h, --help    display this help and exit"
    echo "" 
  } 1>&2
  
  exit 1
}

#-------------------------------------------------------------------------------

# Parse options

while [[ "${1:0:1}" = "-" && "$1" != "--" ]]; do
  case "$1" in
    -r | --release )
      local_config_entries="$local_config_entries"'
is_release_build: true'
    ;;
    -h | --help )
      usage
    ;;
    * )
      [[ "$1" ]] && echo "error: unknown argument: $1"
      usage
    ;;
  esac
  
  shift
  
done

[[ "$1" = "--" ]] && shift

#-------------------------------------------------------------------------------

trap cleanup SIGINT SIGTERM SIGKILL

orig_wd="$(pwd)"
cd "$pages_dirpath"

echo "$local_config_entries" > "$local_config_filename"
bundle exec jekyll serve --config "$config_filename,$local_config_filename"

cd "$orig_wd"
