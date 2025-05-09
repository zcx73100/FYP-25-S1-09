#!/usr/bin/env bash
set -e

echo "=== DEBUG: PORT is $PORT"
exec gunicorn wsgi:app \
  --bind 0.0.0.0:"$PORT" \
  --workers 1 \
  --log-level debug
