# DealFlow360

A deal engine that governs itself. Instead of a plain "quote → invoice" form, DealFlow360
turns a quotation into a governed workflow:

- **Explainable approval routing** — a quote is risk-scored line by line against a
  versioned discount policy, and the engine decides *who* must approve and shows the
  approver *why* (which ceiling was hit, how far over, how much of the order it is).
- **Live negotiation** — a customer portal where the customer can counter-offer; the rep's
  builder updates over SSE with no refresh, and re-applying terms re-runs the engine and
  can push the quote back into approval on its own.
- **Real fulfilment** — multi-warehouse stock splits, backorders and replenishment under
  concurrent load, with optimistic-concurrency conflict handling.
- **Hybrid billing** — one-time and recurring (subscription) lines on the same order,
  invoices/credit notes rendered to PDF, partial and full payments.
- **Policy as data** — catalogue, price lists and discount policy are editable in the admin
  UI as new versions you activate or roll back, no redeploy.
- **Deal-health dashboard** — stalled deals, discount anomalies that explain themselves,
  delivery slippage; role-shaped dashboard layouts.

Multi-tenant: every user, role, customer and configuration row belongs to one organization,
and a principal only ever sees its own org's data.

## Stack

**Frontend** — Next.js (App Router) · TypeScript · Tailwind · shadcn/ui · TanStack Query ·
React Hook Form
**Backend** — FastAPI · SQLAlchemy 2 · Alembic · Pydantic v2 · PostgreSQL · Dramatiq
(Redis) workers · MinIO (S3-compatible object storage) · JWT auth + RBAC

`context/API_CONTRACT.md` is the single source of truth for the wire format; the frontend
types are generated from the backend's OpenAPI schema at build time.

## Run it with Docker

Requires Docker with Compose v2 (BuildKit — the default in recent Docker).

```bash
cp .env.example .env    # local dev values, adjust if you like
docker compose up --build
```

On first start the backend runs migrations, seeds default roles + the admin user, and
regenerates `openapi.json`. Once the containers report healthy:

| Service | URL |
|---|---|
| Frontend | http://localhost:3001 |
| API | http://localhost:8001/api/v1 |
| API docs (Swagger) | http://localhost:8001/api/v1/docs |
| MinIO console | http://localhost:9001 (`minioadmin` / `minioadmin`) |
| Postgres | `localhost:5432` (`postgres` / `postgres`, db `app`) |
| Redis | `localhost:6379` |

Default admin login: `ADMIN_EMAIL` / `ADMIN_PASSWORD` from `.env`
(`admin@example.com` / `admin12345`).

Source directories are bind-mounted, so both frontend and backend hot-reload on edit.

### Seeding demo data

```bash
# default seed (roles + admin) runs automatically on startup
docker compose exec backend python -m app.db.seed

# full demo dataset (org, customers, catalogue, history)
docker compose exec backend python -m app.db.seed --reset --history --demo
```

### Production images

Set `APP_ENV=production` in `.env` and re-run `docker compose up --build` — the same
compose file builds and runs production images (`next build`, `uvicorn --workers 4`).

## Run it without Docker

Backend needs a running Postgres, Redis and MinIO matching the `*_URL` / `MINIO_*` values
in `.env`.

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python -m app.db.seed
uvicorn app.main:app --reload --port 8001
# separate shell — background worker:
dramatiq app.worker.tasks
```

```bash
cd frontend
yarn install
yarn dev
```

## Folder structure

```
.
├── docker-compose.yml         # db · redis · minio · backend · worker · frontend
├── .env.example               # every config value (see .env for local dev)
├── context/                   # design docs — API_CONTRACT.md is the wire spec
├── demo/selenium/             # Selenium scripts that drive the app end-to-end
│
├── backend/
│   ├── Dockerfile
│   ├── docker-entrypoint.sh   # migrate → seed → regen openapi → serve
│   ├── alembic/               # migrations
│   └── app/
│       ├── main.py            # app factory
│       ├── api.py             # router aggregation
│       ├── config/            # env-driven settings, logging
│       ├── core/              # security, deps, CRUD base, pagination, middleware
│       ├── db/                # base, session, seed
│       ├── auth/  users/  roles/  organizations/    # identity & RBAC, multi-tenant
│       ├── customers/  portal/                      # customers + customer-facing portal
│       ├── catalog/  pricing/  policies/  subscriptions/  # configuration (policy as data)
│       ├── quotations/  approvals/  affinity/       # the deal engine + upsell
│       ├── fulfillment/  warehouses/                # stock, splits, backorders
│       ├── billing/                                 # invoices, credit notes, payments
│       ├── dashboard/  events/  meta/               # dashboards, SSE events, enum source
│       ├── jobs/  worker/                           # scheduled jobs + Dramatiq tasks
│
└── frontend/
    ├── Dockerfile
    └── src/
        ├── app/
        │   ├── (auth)/         # login / register
        │   ├── (dashboard)/    # staff app: dashboard, config, customers, quotations,
        │   │                   # approvals, reports, roles, users, workspace
        │   └── (portal)/       # customer portal
        ├── components/
        │   ├── ui/             # shadcn/ui
        │   └── layout/         # sidebar, header, nav, live indicator
        ├── features/           # one folder per domain: api + hooks + components
        │                       # (auth, quotations, approvals, billing, pricing, …)
        └── lib/
            ├── api/            # axios client + generated schema.d.ts
            └── live/           # SSE hooks
```

## The Contract Lock Rule

`context/API_CONTRACT.md` is the single source of truth for every byte that crosses the
network. Don't invent, rename, or retype any field, endpoint, enum member or error code
defined there. If a change is genuinely needed: stop, edit that file, bump the contract
version, regenerate OpenAPI + types (`yarn gen:api`), then resume.
