#!/bin/bash

# This script generates a new .po file from the specified .pot file and language.

SCRIPT_NAME="$(basename -- "$0")"

if [ ! -f "$1" ]; then
   echo "$SCRIPT_NAME: '$1': .pot file not found" 1>&2
   exit 1
fi

pot_file="$1"
shift


if [ -z "$1" ]; then
   echo "$SCRIPT_NAME: language not specified" 1>&2
   exit 1
fi

language="$1"
shift

msginit --no-translator --input="$pot_file" --locale="$language" --output-file='./'"$language"'.po'
