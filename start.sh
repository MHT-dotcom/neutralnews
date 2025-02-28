#!/bin/bash
port=${PORT:-5002}
echo "Starting app on port $port"
gunicorn --bind 0.0.0.0:$port app:app --workers 1 --timeout 120