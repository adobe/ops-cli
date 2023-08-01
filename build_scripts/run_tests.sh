#!/bin/bash
set -e

echo "Running tests"
export BOTO_CONFIG=/dev/null
export CRYPTOGRAPHY_DONT_BUILD_RUST=1

pip install --no-cache-dir -r requirements.txt
pip install pytest

pip install -e .
python -m pytest tests
