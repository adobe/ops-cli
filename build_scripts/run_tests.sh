#!/bin/bash
set -e

echo "Running tests"
export BOTO_CONFIG=/dev/null
pip install --no-cache-dir -r requirements.txt
nosetests --with-xunit tests/unit
