#!/bin/bash
set -e

export PORT=${PORT:-8080}

echo "=== Celestial Concierge Unified Starting ==="
echo "Port: $PORT"

mkdir -p /etc/nginx/conf.d
envsubst '${PORT}' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf

echo "Starting FastAPI backend on 127.0.0.1:8000..."
cd /app/backend
python -m uvicorn main:app --host 127.0.0.1 --port 8000 &
UVICORN_PID=$!

echo "Waiting for FastAPI backend to initialize..."
for i in $(seq 1 30); do
    if curl -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
        echo "FastAPI backend is ready!"
        break
    fi
    sleep 1
done

echo "Starting Nginx reverse proxy on port $PORT..."
nginx -g "daemon off;" &
NGINX_PID=$!

trap "kill -TERM $UVICORN_PID $NGINX_PID" SIGINT SIGTERM

wait -n
EXIT_CODE=$?
echo "A service process exited with code $EXIT_CODE. Shutting down container."
kill -TERM $UVICORN_PID $NGINX_PID 2>/dev/null || true
exit $EXIT_CODE
