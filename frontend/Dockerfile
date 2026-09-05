FROM node:20-alpine

ARG APP_ENV=development
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_APP_NAME
ENV APP_ENV=${APP_ENV} \
    NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL} \
    NEXT_PUBLIC_APP_NAME=${NEXT_PUBLIC_APP_NAME} \
    NEXT_TELEMETRY_DISABLED=1

WORKDIR /app

COPY package.json yarn.lock* ./
RUN yarn install --frozen-lockfile 2>/dev/null || yarn install

COPY . .

# Pull the backend's exact openapi.json straight out of its image (see
# docker-compose.yml's `additional_contexts: backend-schema: service:backend`)
# and regenerate schema.d.ts from it — the image always ships types that match
# whatever backend build it was assembled alongside, never a possibly-stale
# committed file. `--from=backend-schema` requires BuildKit; `docker compose
# build`/`up` enable it automatically.
COPY --from=backend-schema /app/openapi.json ./backend-openapi.json
RUN yarn openapi-typescript ./backend-openapi.json -o src/lib/api/schema.d.ts

# NEXT_PUBLIC_* values are baked into the bundle at build time.
# Run `next build` directly, not `yarn build` — the `build` script re-runs
# openapi-typescript against ../backend/openapi.json, which doesn't exist in
# this image (the schema was already generated from backend-openapi.json above).
RUN if [ "$APP_ENV" = "production" ]; then yarn next build; fi

EXPOSE 3001

CMD ["sh", "/app/docker-entrypoint.sh"]
