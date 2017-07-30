#!/bin/bash

# This script runs the Jekyll server locally with GitHub Pages metadata properly disabled.

SCRIPT_NAME="${0##*/}"

pages_dirpath='../gh-pages'
config_filepath="$pages_dirpath"'/_config.yml'
local_config_filepath="$pages_dirpath"'/_config_local.yml'

local_config_entries='
github: [metadata]'

cleanup () {
  rm -f "$local_config_filepath"
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

echo "$local_config_entries" > "$local_config_filepath"

bundle exec jekyll serve --config "$config_filepath,$local_config_filepath"
