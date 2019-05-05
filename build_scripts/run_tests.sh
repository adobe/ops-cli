#!/bin/bash
set -e

echo "Running tests"
export BOTO_CONFIG=/dev/null
pip install --no-cache-dir -r requirements.txt
pip install pytest

pip install -e .
python -m pytest tests
