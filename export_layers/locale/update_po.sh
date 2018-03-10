#!/bin/bash

# This script updates the specified .po file according to the specified .pot file,
# which could be changed due to the changes in the source code.
# The old version of the .po file is preserved and is named '[filename].po.old'.
#
# Options:
# -r - don't preserve the old .po file

PROGNAME="$(basename "$0")"

preserve_old_po=''

if [ "$1" != '-r' ]; then
   preserve_old_po='1'
else
   shift
fi

if [ ! -f "$1" ]; then
   echo "$PROGNAME: '$1': .po file not found" 1>&2
   exit 1
fi
po_file="$1"
shift

if [ ! -f "$1" ]; then
   echo "$PROGNAME: '$1': .pot file not found" 1>&2
   exit 1
fi
pot_file="$1"
shift


if [ "$preserve_old_po" ]; then
   mv -f "$po_file" "$po_file"'.old'
   msgmerge "$po_file"'.old' "$pot_file" --output-file="$po_file"
else
   msgmerge "$po_file" "$pot_file" --output-file="$po_file"
fi
