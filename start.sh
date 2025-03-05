#!/bin/bash

# Print environment information for debugging
echo "Starting Neutral News application..."
echo "PORT environment variable: $PORT"
echo "RENDER environment variable: $RENDER"
echo "Python version: $(python --version)"

# If PORT is not set and we're on Render, use default Render port
if [ -z "$PORT" ] && [ -n "$RENDER" ]; then
    export PORT=10000
    echo "Setting default PORT=10000 for Render"
fi

# Start the application with Gunicorn
# Bind to 0.0.0.0 with the PORT from environment
# Use 4 worker processes
echo "Starting Gunicorn on 0.0.0.0:$PORT"
exec gunicorn app:app --bind 0.0.0.0:$PORT --workers=4 --access-logfile=- --error-logfile=-