#!/bin/bash

# This script runs the Jekyll server locally with GitHub Pages metadata properly disabled.

pages_dirpath='../gh-pages'
config_filepath="$pages_dirpath"'/_config.yml'
local_config_filepath="$pages_dirpath"'/_config_local.yml'

config_entries_to_add='
github: [metadata]'

cleanup () {
  rm -f "$local_config_filepath"
}

trap cleanup SIGINT SIGTERM SIGKILL

cp -f "$config_filepath" "$local_config_filepath"
echo "$config_entries_to_add" >> "$local_config_filepath"

bundle exec jekyll serve --config "$local_config_filepath"
