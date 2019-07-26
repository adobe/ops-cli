#!/bin/bash
set -e

echo "Building package"
rm -rf dist/
export BOTO_CONFIG=/dev/null
python setup.py sdist bdist_wheel
ls -l dist/
