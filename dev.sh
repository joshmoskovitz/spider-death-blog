#!/bin/bash
# Local development: starts API server + static file server
# Usage: ./dev.sh

trap 'kill 0' EXIT

echo "Starting API server on :8888..."
CORS_ORIGINS="http://localhost:8080" python server.py &

echo "Starting static site server on :8080..."
python -m http.server 8080 --directory site &

echo ""
echo "  Site:  http://localhost:8080"
echo "  API:   http://localhost:8888"
echo ""
echo "Press Ctrl+C to stop both servers."

wait
