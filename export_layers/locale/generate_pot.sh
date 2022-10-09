#!/bin/bash

# This script (re-)generates .pot file from .py files in the entire plug-in.

PROGNAME="$(basename "$0")"

USAGE="$PROGNAME"' PLUGIN_NAME PLUGIN_VERSION DOMAIN_NAME AUTHOR_NAME'

if [ $# -le 4 ]; then
   echo "$PROGNAME: invalid number of arguments"
   echo
   echo "$USAGE"
   exit 1
fi

plugin_name="$1"
plugin_version="$2"
domain_name="$3"
author_name="$4"

package_name=\'"$plugin_name"\'

input_dirpath='../..'
output_filepath='./'"$domain_name"'.pot'

find "$input_dirpath" -type f -iname '*.py' | \
xargs xgettext --language=Python --keyword='_' --keyword='N_' --package-name="$package_name" --package-version="$plugin_version" --copyright-holder="$author_name" --output="$output_filepath" --from-code='UTF-8'

sed -i '
  s/^\("Content-Type: text\/plain; charset\)=CHARSET/\1=UTF-8/
' "$output_filepath"
