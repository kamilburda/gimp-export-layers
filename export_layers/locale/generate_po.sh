#!/bin/bash

# This script generates a new .po file from the specified .pot file and language.

PROGNAME="$(basename "$0")"

if [ ! -f "$1" ]; then
   echo "$PROGNAME: '$1': .pot file not found" 1>&2
   exit 1
fi

pot_file="$1"
shift


if [ -z "$1" ]; then
   echo "$PROGNAME: language not specified" 1>&2
   exit 1
fi

language="$1"
shift

msginit --no-translator --input="$pot_file" --locale="$language" --output-file='./'"$language"'.po'
