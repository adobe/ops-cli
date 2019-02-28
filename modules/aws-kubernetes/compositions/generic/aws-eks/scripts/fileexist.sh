#!/bin/bash
#
# This script calculates the MD5 checksum on a directory
#

# Exit if any of the intermediate steps fail
set -e

# Extract "FILE" argument from the input into
# FILE shell variables.
# jq will ensure that the values are properly quoted
# and escaped for consumption by the shell.
# FILE=$1

eval "$(jq -r '@sh "FILE=\(.file)"')"

EXISTS=0
if [[ -f $FILE ]]; then
   EXISTS=1
fi

# Safely produce a JSON object containing the result value.
# jq will ensure that the value is properly quoted
# and escaped to produce a valid JSON string.
jq -n --arg exists "$EXISTS" '{"exists":$exists}'