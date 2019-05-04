#!/bin/bash
set -e

echo "Freezing requirements.txt"
rm -rf Pipfile* deps
pipenv lock --clear --two --requirements 1>deps
grep '==' deps | sed "s/;\\sextra.*//" > requirements.txt
