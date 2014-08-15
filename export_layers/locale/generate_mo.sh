#!/bin/bash

# This script:
# * generates .mo file from the specified .po file
# * moves the .mo file to the appropriate directory.
#
# The language code is determined from the basename of the .po file.

PROGNAME="$(basename "$0")"

PLUGIN_NAME='export_layers'

LOCALE_DIR='.'
LC_MESSAGES_DIR='LC_MESSAGES'

if [ ! -f "$1" ]; then
   echo "$PROGNAME: '$1': file not found" 1>&2
   exit 1
fi

po_file="$1"
shift

language="$(basename "${po_file%.*}")"
output_dir="$LOCALE_DIR"'/'"$language"'/'"$LC_MESSAGES_DIR"

mkdir -p "$output_dir"

msgfmt "$po_file" --output-file="$output_dir"'/'"$PLUGIN_NAME"'.mo'
