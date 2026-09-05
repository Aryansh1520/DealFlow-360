FROM python:3.12-slim

ARG APP_ENV=development
ENV APP_ENV=${APP_ENV} \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Bake a fresh openapi.json into every image build — pure schema introspection,
# no DB/server needed, so it's always exactly in sync with this build's code.
# The frontend image pulls this file via a build-time cross-service context
# (see docker-compose.yml's `additional_contexts` on the frontend service),
# so `API_CONTRACT.md`'s contract version can never drift out of sync again.
RUN python -c "import json; from app.main import app; json.dump(app.openapi(), open('openapi.json', 'w'))"

EXPOSE 8001

CMD ["sh", "/app/docker-entrypoint.sh"]
