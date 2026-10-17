#!/usr/bin/env bash
set -e

echo "Running NaSCon 26 Automated Test Suites..."
cd backend
python -m pytest tests/ -v
echo "All tests passed successfully!"
