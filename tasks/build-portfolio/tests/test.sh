#!/bin/bash
set -e

cd /project

# Install test dependencies
pip install pytest 2>/dev/null || true

# Run the test
python3 /tests/test.py

# The test.py writes the reward
