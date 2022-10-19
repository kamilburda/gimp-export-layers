#!/bin/bash

# This script:
# * generates .mo file from the specified .po file
# * moves the .mo file to the appropriate directory.
#
# The language code is determined from the basename of the .po file.

SCRIPT_NAME="$(basename -- "$0")"

DOMAIN_NAME='gimp-plugin-export-layers'

LOCALE_DIRPATH='.'
LC_MESSAGES_DIRPATH='LC_MESSAGES'

if [ ! -f "$1" ]; then
   echo "$SCRIPT_NAME: '$1': file not found" 1>&2
   exit 1
fi

if [ ! "$2" ]; then
   echo "$SCRIPT_NAME: missing language" 1>&2
   exit 1
fi

po_file="$1"
language="$2"
shift 2

output_dirpath="$LOCALE_DIRPATH"'/'"$language"'/'"$LC_MESSAGES_DIRPATH"

mkdir -p "$output_dirpath"

msgfmt "$po_file" --output-file="$output_dirpath"'/'"$DOMAIN_NAME"'.mo'
