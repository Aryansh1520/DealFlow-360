#!/bin/sh
set -e

if [ "$APP_ENV" = "production" ]; then
  # The image was already built with the backend's exact schema baked in
  # (see the Dockerfile's `additional_contexts` COPY step) and `yarn build`
  # has already run — never fetch the schema at runtime in production.
  echo "Starting server (production)..."
  exec yarn start
fi

# Dev: source is bind-mounted, so the schema.d.ts baked in at image build time
# can go stale the moment the backend's code changes without an image rebuild.
# Wait for the backend to be up, then regenerate against its live schema on
# every container start — this is what makes `docker compose up` alone keep
# the two sides in sync, no manual `yarn gen:api` required.
BACKEND_HEALTH_URL="${INTERNAL_API_URL%/api/v1}/health"
echo "Waiting for backend at ${BACKEND_HEALTH_URL}..."
attempt=0
until wget -q -O /dev/null "$BACKEND_HEALTH_URL" 2>/dev/null; do
  attempt=$((attempt + 1))
  if [ "$attempt" -ge 60 ]; then
    echo "Backend did not become ready in time — starting anyway with the existing schema.d.ts."
    break
  fi
  sleep 1
done

echo "Regenerating src/lib/api/schema.d.ts from ${INTERNAL_API_URL}/openapi.json..."
yarn openapi-typescript "${INTERNAL_API_URL}/openapi.json" -o src/lib/api/schema.d.ts || \
  echo "Schema regeneration failed — continuing with the existing schema.d.ts."

echo "Starting server (development, hot reload)..."
exec yarn dev
