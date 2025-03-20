#!/bin/bash

# Kill any existing Flask/Python processes
pkill flask || true
pkill python || true

# Wait briefly to ensure processes are terminated
sleep 1

# Default to port 5003 to avoid conflicts with AirPlay Receiver on macOS (port 5000)
port=${PORT:-5003}
echo "Starting development server on port $port"

# Start Flask in development mode
FLASK_RUN_PORT=$port flask run
