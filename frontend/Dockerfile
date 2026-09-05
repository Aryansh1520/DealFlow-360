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

# NEXT_PUBLIC_* values are baked into the bundle at build time
RUN if [ "$APP_ENV" = "production" ]; then yarn build; fi

EXPOSE 3001

CMD ["sh", "-c", "if [ \"$APP_ENV\" = \"production\" ]; then yarn start; else yarn dev; fi"]
