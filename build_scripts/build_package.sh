#!/bin/bash
set -e

echo "Building package"
rm -rf dist/
export BOTO_CONFIG=/dev/null
export CRYPTOGRAPHY_DONT_BUILD_RUST=1
python setup.py sdist bdist_wheel
ls -l dist/
