#!/bin/sh
set -e

echo "Running database migrations..."
alembic upgrade head

# Source is bind-mounted in dev, so the image's baked openapi.json (from the
# Dockerfile build step) can go stale the moment code changes without a
# rebuild. Regenerate it on every start so the committed file — and anything
# the frontend reads from it — never drifts from `API_CONTRACT.md`.
echo "Regenerating openapi.json..."
python -c "import json; from app.main import app; json.dump(app.openapi(), open('openapi.json', 'w'))"

if [ "$APP_ENV" = "production" ]; then
  echo "Starting server (production)..."
  exec uvicorn app.main:app --host 0.0.0.0 --port 8001 --workers 4
else
  echo "Starting server (development, hot reload)..."
  exec uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
fi
