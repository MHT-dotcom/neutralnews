#!/bin/bash
# Script to run the test environment

# Export test environment variables
export FLASK_ENV=development
export FLASK_DEBUG=1
export FLASK_CONFIG=config_test
export TEST_PORT=10001

# Run the test application
python app_test.py
