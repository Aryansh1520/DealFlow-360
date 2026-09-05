#!/bin/sh
set -e

echo "Running database migrations..."
alembic upgrade head

if [ "$APP_ENV" = "production" ]; then
  echo "Starting server (production)..."
  exec uvicorn app.main:app --host 0.0.0.0 --port 8001 --workers 4
else
  echo "Starting server (development, hot reload)..."
  exec uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
fi
